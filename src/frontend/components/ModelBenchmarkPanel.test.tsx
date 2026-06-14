/**
 * Unit tests for ModelBenchmarkPanel component.
 *
 * Covers:
 * - Initial render: form fields, default providers, run button
 * - Adding / removing providers
 * - Validation: empty prompt, single provider
 * - Run flow: pending state → streaming results → run_complete
 * - History drawer: open/close, fetch, display
 * - Compare: selection, POST, diff panel render
 * - Accessibility: ARIA attributes on key elements
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ModelBenchmarkPanel from './ModelBenchmarkPanel';

// ---------------------------------------------------------------------------
// Mock fetch
// ---------------------------------------------------------------------------

const mockFetch = jest.fn();
global.fetch = mockFetch;

// Helper: build a ReadableStream from NDJSON lines
function makeNDJSONStream(lines: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const chunks = lines.map((l) => encoder.encode(l + '\n'));
  let idx = 0;
  return new ReadableStream({
    pull(controller) {
      if (idx < chunks.length) {
        controller.enqueue(chunks[idx++]);
      } else {
        controller.close();
      }
    },
  });
}

const OPENAI_RESULT = {
  provider_id: 'openai',
  model: 'gpt-4o',
  status: 'success',
  content: 'Paris is the capital.',
  error_message: null,
  latency_ms: 320,
  input_tokens: 20,
  output_tokens: 10,
  total_tokens: 30,
  finish_reason: 'stop',
};

const ANTHROPIC_RESULT = {
  provider_id: 'anthropic',
  model: 'claude-3-5-sonnet-20241022',
  status: 'success',
  content: 'The capital is Paris.',
  error_message: null,
  latency_ms: 510,
  input_tokens: 22,
  output_tokens: 12,
  total_tokens: 34,
  finish_reason: 'end_turn',
};

const COMPLETE_EVENT: object = {
  run_id: 'run-test-001',
  prompt: 'What is the capital of France?',
  system_prompt: null,
  tags: [],
  results: [OPENAI_RESULT, ANTHROPIC_RESULT],
  created_at: '2026-03-26T22:00:00Z',
  total_duration_ms: 510,
};

function makeStreamResponse(providerResults: object[], completeEvent: object) {
  const lines = [
    ...providerResults.map((r) =>
      JSON.stringify({ event: 'provider_result', data: r })
    ),
    JSON.stringify({ event: 'run_complete', data: completeEvent }),
  ];
  return {
    ok: true,
    body: makeNDJSONStream(lines),
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ModelBenchmarkPanel', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  // ── Initial render ────────────────────────────────────────────────────

  describe('initial render', () => {
    it('renders prompt textarea', () => {
      render(<ModelBenchmarkPanel />);
      expect(screen.getByLabelText(/^Prompt$/i)).toBeInTheDocument();
    });

    it('renders system prompt textarea', () => {
      render(<ModelBenchmarkPanel />);
      expect(screen.getByLabelText(/system prompt/i)).toBeInTheDocument();
    });

    it('renders run benchmark button', () => {
      render(<ModelBenchmarkPanel />);
      expect(screen.getByRole('button', { name: /run benchmark/i })).toBeInTheDocument();
    });

    it('renders default two provider rows', () => {
      render(<ModelBenchmarkPanel />);
      // Two provider selects
      const selects = screen.getAllByRole('combobox');
      expect(selects.length).toBeGreaterThanOrEqual(2);
    });

    it('shows add provider button', () => {
      render(<ModelBenchmarkPanel />);
      expect(screen.getByLabelText(/add another provider/i)).toBeInTheDocument();
    });

    it('run button disabled when prompt is empty', () => {
      render(<ModelBenchmarkPanel />);
      const btn = screen.getByRole('button', { name: /run benchmark/i });
      expect(btn).toBeDisabled();
    });

    it('pre-fills prompt from initialPrompt prop', () => {
      render(<ModelBenchmarkPanel initialPrompt="Hello world" />);
      const textarea = screen.getByLabelText(/^Prompt/i) as HTMLTextAreaElement;
      expect(textarea.value).toBe('Hello world');
    });
  });

  // ── Provider management ───────────────────────────────────────────────

  describe('provider management', () => {
    it('adds a third provider row on click', async () => {
      render(<ModelBenchmarkPanel />);
      const addBtn = screen.getByLabelText(/add another provider/i);
      await userEvent.click(addBtn);
      const selects = screen.getAllByRole('combobox');
      // 3 provider selects + 3 model selects = 6
      expect(selects.length).toBeGreaterThanOrEqual(6);
    });

    it('disables add button at 8 providers', async () => {
      render(<ModelBenchmarkPanel />);
      const addBtn = screen.getByLabelText(/add another provider/i);
      for (let i = 0; i < 6; i++) {
        await userEvent.click(addBtn);
      }
      expect(addBtn).toBeDisabled();
    });

    it('remove buttons disabled when only 2 providers remain', () => {
      render(<ModelBenchmarkPanel />);
      const removeBtns = screen.getAllByRole('button', { name: /remove/i });
      removeBtns.forEach((btn) => expect(btn).toBeDisabled());
    });

    it('removes a provider row when remove button clicked (3 providers)', async () => {
      render(<ModelBenchmarkPanel />);
      const addBtn = screen.getByLabelText(/add another provider/i);
      await userEvent.click(addBtn);

      const removeBtns = screen.getAllByRole('button', { name: /remove/i });
      expect(removeBtns.length).toBe(3);
      await userEvent.click(removeBtns[0]);

      const afterRemove = screen.getAllByRole('button', { name: /remove/i });
      expect(afterRemove.length).toBe(2);
    });
  });

  // ── Run flow ──────────────────────────────────────────────────────────

  describe('run benchmark', () => {
    it('calls /benchmark/run/stream on submit', async () => {
      mockFetch.mockResolvedValueOnce(makeStreamResponse([OPENAI_RESULT, ANTHROPIC_RESULT], COMPLETE_EVENT));

      render(<ModelBenchmarkPanel initialPrompt="Capital of France?" />);

      await userEvent.click(screen.getByRole('button', { name: /run benchmark/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/benchmark/run/stream'),
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('displays provider result content after stream completes', async () => {
      mockFetch.mockResolvedValueOnce(makeStreamResponse([OPENAI_RESULT, ANTHROPIC_RESULT], COMPLETE_EVENT));

      render(<ModelBenchmarkPanel initialPrompt="Capital of France?" />);
      await userEvent.click(screen.getByRole('button', { name: /run benchmark/i }));

      await waitFor(() => {
        expect(screen.getByText('Paris is the capital.')).toBeInTheDocument();
      });
    });

    it('shows fastest badge for lowest latency result', async () => {
      mockFetch.mockResolvedValueOnce(makeStreamResponse([OPENAI_RESULT, ANTHROPIC_RESULT], COMPLETE_EVENT));

      render(<ModelBenchmarkPanel initialPrompt="Capital?" />);
      await userEvent.click(screen.getByRole('button', { name: /run benchmark/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/fastest response/i)).toBeInTheDocument();
      });
    });

    it('shows cancel button while running', async () => {
      // Never resolves
      mockFetch.mockReturnValueOnce(new Promise(() => {}));

      render(<ModelBenchmarkPanel initialPrompt="Test" />);
      await userEvent.click(screen.getByRole('button', { name: /run benchmark/i }));

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    it('shows error when fetch fails', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      render(<ModelBenchmarkPanel initialPrompt="Test" />);
      await userEvent.click(screen.getByRole('button', { name: /run benchmark/i }));

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(/network error/i);
      });
    });

    it('calls onRunComplete callback', async () => {
      const onRunComplete = jest.fn();
      mockFetch.mockResolvedValueOnce(makeStreamResponse([OPENAI_RESULT, ANTHROPIC_RESULT], COMPLETE_EVENT));

      render(
        <ModelBenchmarkPanel initialPrompt="Capital?" onRunComplete={onRunComplete} />
      );
      await userEvent.click(screen.getByRole('button', { name: /run benchmark/i }));

      await waitFor(() => {
        expect(onRunComplete).toHaveBeenCalledWith(
          expect.objectContaining({ run_id: 'run-test-001' })
        );
      });
    });
  });

  // ── History drawer ────────────────────────────────────────────────────

  describe('history drawer', () => {
    const HISTORY_ITEMS = [
      {
        run_id: 'hist-1',
        prompt_preview: 'Capital of France?',
        provider_ids: ['openai', 'anthropic'],
        tags: [],
        created_at: '2026-03-26T10:00:00Z',
        total_duration_ms: 500,
        success_count: 2,
        error_count: 0,
      },
    ];

    it('toggles history drawer open on button click', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => HISTORY_ITEMS });

      render(<ModelBenchmarkPanel />);
      await userEvent.click(screen.getByRole('button', { name: /view history/i }));

      expect(screen.getByLabelText(/benchmark run history/i)).toBeInTheDocument();
    });

    it('fetches history from /benchmark/history endpoint', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => HISTORY_ITEMS });

      render(<ModelBenchmarkPanel />);
      await userEvent.click(screen.getByRole('button', { name: /view history/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/benchmark/history'));
      });
    });

    it('displays history items in drawer', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => HISTORY_ITEMS });

      render(<ModelBenchmarkPanel />);
      await userEvent.click(screen.getByRole('button', { name: /view history/i }));

      await waitFor(() => {
        expect(screen.getByText('Capital of France?')).toBeInTheDocument();
      });
    });

    it('shows empty message when no history', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] });

      render(<ModelBenchmarkPanel />);
      await userEvent.click(screen.getByRole('button', { name: /view history/i }));

      await waitFor(() => {
        expect(screen.getByText(/no previous benchmark runs/i)).toBeInTheDocument();
      });
    });

    it('changes button label to Hide History when open', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] });

      render(<ModelBenchmarkPanel />);
      await userEvent.click(screen.getByRole('button', { name: /view history/i }));

      expect(screen.getByRole('button', { name: /hide history/i })).toBeInTheDocument();
    });
  });

  // ── Compare ───────────────────────────────────────────────────────────

  describe('compare mode', () => {
    async function runAndGetCards() {
      mockFetch.mockResolvedValueOnce(
        makeStreamResponse([OPENAI_RESULT, ANTHROPIC_RESULT], COMPLETE_EVENT)
      );
      render(<ModelBenchmarkPanel initialPrompt="Capital?" />);
      await userEvent.click(screen.getByRole('button', { name: /run benchmark/i }));
      await waitFor(() => screen.getByText('Paris is the capital.'));
    }

    it('compare button appears after selecting 2 cards', async () => {
      await runAndGetCards();

      const cards = screen.getAllByRole('button', { name: /result from/i });
      await userEvent.click(cards[0]);
      await userEvent.click(cards[1]);

      expect(screen.getByRole('button', { name: /compare selected/i })).toBeInTheDocument();
    });

    it('calls /benchmark/compare on compare click', async () => {
      const compareResp = {
        provider_a: 'openai:gpt-4o',
        provider_b: 'anthropic:claude-3-5-sonnet-20241022',
        latency_delta_ms: -190,
        token_delta: -4,
        content_similarity: 0.75,
        faster_provider: 'openai:gpt-4o',
        more_concise_provider: 'openai:gpt-4o',
        content_a: 'Paris is the capital.',
        content_b: 'The capital is Paris.',
      };
      mockFetch.mockResolvedValueOnce(
        makeStreamResponse([OPENAI_RESULT, ANTHROPIC_RESULT], COMPLETE_EVENT)
      );
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => compareResp });

      render(<ModelBenchmarkPanel initialPrompt="Capital?" />);
      await userEvent.click(screen.getByRole('button', { name: /run benchmark/i }));
      await waitFor(() => screen.getByText('Paris is the capital.'));

      const cards = screen.getAllByRole('button', { name: /result from/i });
      await userEvent.click(cards[0]);
      await userEvent.click(cards[1]);

      await userEvent.click(screen.getByRole('button', { name: /compare selected/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/benchmark/compare'),
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('renders compare diff panel after comparison', async () => {
      const compareResp = {
        provider_a: 'openai:gpt-4o',
        provider_b: 'anthropic:claude-3-5-sonnet-20241022',
        latency_delta_ms: -190,
        token_delta: -4,
        content_similarity: 0.75,
        faster_provider: 'openai:gpt-4o',
        more_concise_provider: 'openai:gpt-4o',
        content_a: 'Paris is the capital.',
        content_b: 'The capital is Paris.',
      };
      mockFetch
        .mockResolvedValueOnce(
          makeStreamResponse([OPENAI_RESULT, ANTHROPIC_RESULT], COMPLETE_EVENT)
        )
        .mockResolvedValueOnce({ ok: true, json: async () => compareResp });

      render(<ModelBenchmarkPanel initialPrompt="Capital?" />);
      await userEvent.click(screen.getByRole('button', { name: /run benchmark/i }));
      await waitFor(() => screen.getByText('Paris is the capital.'));

      const cards = screen.getAllByRole('button', { name: /result from/i });
      await userEvent.click(cards[0]);
      await userEvent.click(cards[1]);
      await userEvent.click(screen.getByRole('button', { name: /compare selected/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/provider comparison results/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/75.0%/)).toBeInTheDocument(); // similarity
    });
  });

  // ── Accessibility ─────────────────────────────────────────────────────

  describe('accessibility', () => {
    it('prompt textarea has aria-required', () => {
      render(<ModelBenchmarkPanel />);
      const textarea = screen.getByLabelText(/^Prompt/i);
      expect(textarea).toHaveAttribute('aria-required', 'true');
    });

    it('history button has aria-expanded attribute', () => {
      render(<ModelBenchmarkPanel />);
      const btn = screen.getByRole('button', { name: /view history/i });
      expect(btn).toHaveAttribute('aria-expanded', 'false');
    });

    it('history region has aria-controls on toggle button', () => {
      render(<ModelBenchmarkPanel />);
      const btn = screen.getByRole('button', { name: /view history/i });
      expect(btn).toHaveAttribute('aria-controls', 'benchmark-history-drawer');
    });

    it('panel has aria-label', () => {
      render(<ModelBenchmarkPanel />);
      expect(screen.getByLabelText(/model benchmark panel/i)).toBeInTheDocument();
    });
  });
});
