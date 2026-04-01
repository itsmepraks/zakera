/**
 * useStreamingChat.ts
 *
 * React hook for streaming AI chat responses in the Zakera frontend.
 * Connects to the /api/v1/chat/stream SSE endpoint, accumulates tokens
 * as they arrive, and exposes abort / retry controls.
 *
 * Usage:
 *   const { messages, sendMessage, isStreaming, abort, error } = useStreamingChat({
 *     provider: 'openai',
 *     model: 'gpt-4o',
 *     systemPrompt: 'You are a helpful assistant.',
 *   });
 */

import { useCallback, useRef, useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  /** ISO-8601 timestamp */
  timestamp: string;
  /** Present on assistant messages once the stream completes */
  tokenUsage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  /** True while the assistant message is still being streamed */
  isStreaming?: boolean;
  /** Non-null when a message failed to send / stream errored */
  error?: string;
}

export interface UseStreamingChatOptions {
  /** Provider key — must match a key in ModelManager (e.g. "openai", "anthropic", "llama3") */
  provider?: string;
  /** Model ID within the provider */
  model?: string;
  /** System prompt prepended to every conversation */
  systemPrompt?: string;
  /** Max tokens for each completion (default: 2048) */
  maxTokens?: number;
  /** Sampling temperature (default: 0.7) */
  temperature?: number;
  /** Base URL for the Zakera API (default: "") — useful for local dev vs production */
  apiBaseUrl?: string;
  /** Called with each streamed token chunk as it arrives */
  onToken?: (token: string) => void;
  /** Called when a stream completes successfully */
  onComplete?: (message: ChatMessage) => void;
  /** Called on stream error */
  onError?: (error: Error) => void;
}

export interface UseStreamingChatReturn {
  messages: ChatMessage[];
  sendMessage: (content: string) => Promise<void>;
  isStreaming: boolean;
  /** Abort the in-flight stream */
  abort: () => void;
  /** Retry the last failed message */
  retry: () => Promise<void>;
  /** Clear all messages */
  clearHistory: () => void;
  error: string | null;
  /** Token usage totals accumulated across the session */
  sessionTokenUsage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function nowIso(): string {
  return new Date().toISOString();
}

// SSE line format: "data: <json>\n\n"
// Zakera stream events:
//   { type: "token",    content: "…" }
//   { type: "done",     usage: { prompt_tokens, completion_tokens, total_tokens } }
//   { type: "error",    message: "…" }
interface StreamEvent {
  type: 'token' | 'done' | 'error';
  content?: string;
  message?: string;
  usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useStreamingChat(
  options: UseStreamingChatOptions = {}
): UseStreamingChatReturn {
  const {
    provider = 'openai',
    model,
    systemPrompt,
    maxTokens = 2048,
    temperature = 0.7,
    apiBaseUrl = '',
    onToken,
    onComplete,
    onError,
  } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionTokenUsage, setSessionTokenUsage] = useState({
    promptTokens: 0,
    completionTokens: 0,
    totalTokens: 0,
  });

  // Holds the AbortController for the current in-flight request
  const abortControllerRef = useRef<AbortController | null>(null);
  // Cache the last user message content for retry
  const lastUserMessageRef = useRef<string | null>(null);

  // ------------------------------------------------------------------
  // Core: send a message and consume the SSE stream
  // ------------------------------------------------------------------
  const sendMessage = useCallback(
    async (content: string): Promise<void> => {
      if (isStreaming) return; // guard against concurrent calls

      lastUserMessageRef.current = content;
      setError(null);

      // 1. Append the user message immediately
      const userMsg: ChatMessage = {
        id: generateId(),
        role: 'user',
        content,
        timestamp: nowIso(),
      };

      // 2. Append a placeholder assistant message
      const assistantMsgId = generateId();
      const assistantMsgPlaceholder: ChatMessage = {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        timestamp: nowIso(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsgPlaceholder]);
      setIsStreaming(true);

      // 3. Build history for the API (include system prompt if set)
      const historyMessages = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));
      if (systemPrompt && historyMessages[0]?.role !== 'system') {
        historyMessages.unshift({ role: 'system', content: systemPrompt });
      }
      historyMessages.push({ role: 'user', content });

      // 4. Fire the SSE request
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: historyMessages,
            provider,
            model,
            max_tokens: maxTokens,
            temperature,
            stream: true,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const errText = await response.text();
          throw new Error(`API error ${response.status}: ${errText}`);
        }

        if (!response.body) throw new Error('Response body is null');

        // 5. Read SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulated = '';
        let tokenUsage: ChatMessage['tokenUsage'];
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          // Keep the last (potentially incomplete) line in the buffer
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const jsonStr = line.slice('data: '.length).trim();
            if (jsonStr === '[DONE]') break;

            let event: StreamEvent;
            try {
              event = JSON.parse(jsonStr);
            } catch {
              continue;
            }

            if (event.type === 'token' && event.content) {
              accumulated += event.content;
              onToken?.(event.content);
              // Update the assistant placeholder with the new content
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId ? { ...m, content: accumulated } : m
                )
              );
            } else if (event.type === 'done' && event.usage) {
              tokenUsage = {
                promptTokens: event.usage.prompt_tokens,
                completionTokens: event.usage.completion_tokens,
                totalTokens: event.usage.total_tokens,
              };
              setSessionTokenUsage((prev) => ({
                promptTokens: prev.promptTokens + tokenUsage!.promptTokens,
                completionTokens: prev.completionTokens + tokenUsage!.completionTokens,
                totalTokens: prev.totalTokens + tokenUsage!.totalTokens,
              }));
            } else if (event.type === 'error') {
              throw new Error(event.message ?? 'Unknown stream error');
            }
          }
        }

        // 6. Finalise the assistant message
        const finalMsg: ChatMessage = {
          id: assistantMsgId,
          role: 'assistant',
          content: accumulated,
          timestamp: nowIso(),
          isStreaming: false,
          tokenUsage,
        };
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? finalMsg : m))
        );
        onComplete?.(finalMsg);
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          // User-initiated abort — mark the assistant message as done (partial)
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId ? { ...m, isStreaming: false } : m
            )
          );
          return;
        }

        const errMsg = (err as Error).message ?? 'Streaming failed';
        setError(errMsg);
        onError?.(err as Error);
        // Mark the assistant placeholder with the error
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, isStreaming: false, error: errMsg }
              : m
          )
        );
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isStreaming, messages, provider, model, maxTokens, temperature, systemPrompt, apiBaseUrl]
  );

  // ------------------------------------------------------------------
  // Abort
  // ------------------------------------------------------------------
  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  // ------------------------------------------------------------------
  // Retry
  // ------------------------------------------------------------------
  const retry = useCallback(async () => {
    if (lastUserMessageRef.current === null) return;
    // Remove the last assistant message (which may have errored)
    setMessages((prev) => {
      const lastAssistant = [...prev].reverse().findIndex((m) => m.role === 'assistant');
      if (lastAssistant === -1) return prev;
      const idxToRemove = prev.length - 1 - lastAssistant;
      return prev.filter((_, i) => i !== idxToRemove);
    });
    await sendMessage(lastUserMessageRef.current);
  }, [sendMessage]);

  // ------------------------------------------------------------------
  // Clear history
  // ------------------------------------------------------------------
  const clearHistory = useCallback(() => {
    setMessages([]);
    setError(null);
    lastUserMessageRef.current = null;
  }, []);

  return {
    messages,
    sendMessage,
    isStreaming,
    abort,
    retry,
    clearHistory,
    error,
    sessionTokenUsage,
  };
}

export default useStreamingChat;
