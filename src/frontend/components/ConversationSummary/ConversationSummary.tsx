/**
 * Conversation Summary Component
 * 
 * Generates and displays AI-powered summaries of conversations
 */

import React, { useState } from 'react';
import './ConversationSummary.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface ConversationSummaryProps {
  messages: Message[];
  conversationId: string;
  onClose?: () => void;
  autoGenerate?: boolean;
}

interface SummaryData {
  brief: string;
  key_points: string[];
  topics: string[];
  action_items: string[];
  message_count: number;
  duration: string;
  models_used: string[];
}

export const ConversationSummary: React.FC<ConversationSummaryProps> = ({
  messages,
  conversationId,
  onClose,
  autoGenerate = false,
}) => {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summaryType, setSummaryType] = useState<'brief' | 'detailed' | 'bullet'>('brief');

  // Generate summary
  const generateSummary = async () => {
    setLoading(true);
    setError(null);

    try {
      // In production, this would call an API endpoint
      // For now, we'll simulate the summary generation
      await new Promise((resolve) => setTimeout(resolve, 2000));

      // Extract topics from messages (simple keyword extraction)
      const topics = extractTopics(messages);
      const actionItems = extractActionItems(messages);
      const duration = calculateDuration(messages);

      const mockSummary: SummaryData = {
        brief: generateBriefSummary(messages),
        key_points: extractKeyPoints(messages),
        topics,
        action_items: actionItems,
        message_count: messages.length,
        duration,
        models_used: ['gpt-4-turbo'], // Would come from actual data
      };

      setSummary(mockSummary);
    } catch (err) {
      setError('Failed to generate summary. Please try again.');
      console.error('Summary generation error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Auto-generate on mount if requested
  React.useEffect(() => {
    if (autoGenerate && messages.length > 0) {
      generateSummary();
    }
  }, [autoGenerate, messages.length]);

  // Helper: Extract topics from messages
  const extractTopics = (msgs: Message[]): string[] => {
    const text = msgs.map((m) => m.content).join(' ').toLowerCase();
    const commonTopics = [
      'code', 'python', 'javascript', 'react', 'api', 'database',
      'performance', 'security', 'testing', 'deployment', 'architecture',
    ];
    return commonTopics.filter((topic) => text.includes(topic));
  };

  // Helper: Extract action items
  const extractActionItems = (msgs: Message[]): string[] => {
    const items: string[] = [];
    const actionKeywords = ['should', 'need to', 'must', 'todo', 'action', 'next step'];

    msgs.forEach((msg) => {
      if (msg.role === 'assistant') {
        const sentences = msg.content.split(/[.!?]\s+/);
        sentences.forEach((sentence) => {
          if (actionKeywords.some((keyword) => sentence.toLowerCase().includes(keyword))) {
            items.push(sentence.trim());
          }
        });
      }
    });

    return items.slice(0, 5);
  };

  // Helper: Extract key points
  const extractKeyPoints = (msgs: Message[]): string[] => {
    const points: string[] = [];
    const assistantMessages = msgs.filter((m) => m.role === 'assistant');

    assistantMessages.forEach((msg, idx) => {
      if (idx < 5) {
        const firstSentence = msg.content.split(/[.!?]/)[0];
        if (firstSentence && firstSentence.length > 20) {
          points.push(firstSentence.trim());
        }
      }
    });

    return points.length > 0 ? points : ['No key points extracted'];
  };

  // Helper: Generate brief summary
  const generateBriefSummary = (msgs: Message[]): string => {
    if (msgs.length === 0) return 'No messages to summarize.';
    
    const userMsgs = msgs.filter((m) => m.role === 'user').length;
    const aiMsgs = msgs.filter((m) => m.role === 'assistant').length;
    const topics = extractTopics(msgs);

    return `This conversation contains ${msgs.length} messages (${userMsgs} from you, ${aiMsgs} AI responses)${topics.length > 0 ? ` discussing ${topics.slice(0, 3).join(', ')}` : ''}.`;
  };

  // Helper: Calculate duration
  const calculateDuration = (msgs: Message[]): string => {
    if (msgs.length < 2) return 'N/A';

    const first = new Date(msgs[0].timestamp);
    const last = new Date(msgs[msgs.length - 1].timestamp);
    const diffMinutes = Math.floor((last.getTime() - first.getTime()) / (1000 * 60));

    if (diffMinutes < 60) return `${diffMinutes} minutes`;
    const hours = Math.floor(diffMinutes / 60);
    const minutes = diffMinutes % 60;
    return `${hours}h ${minutes}m`;
  };

  // Copy summary to clipboard
  const copySummary = () => {
    if (!summary) return;

    const text = `
CONVERSATION SUMMARY
====================

${summary.brief}

KEY POINTS:
${summary.key_points.map((p, i) => `${i + 1}. ${p}`).join('\n')}

${summary.topics.length > 0 ? `\nTOPICS: ${summary.topics.join(', ')}` : ''}

${summary.action_items.length > 0 ? `\nACTION ITEMS:\n${summary.action_items.map((a, i) => `${i + 1}. ${a}`).join('\n')}` : ''}

METADATA:
- Messages: ${summary.message_count}
- Duration: ${summary.duration}
- Models: ${summary.models_used.join(', ')}
    `.trim();

    navigator.clipboard.writeText(text);
  };

  return (
    <div className="conversation-summary-container">
      <div className="summary-header">
        <div className="header-content">
          <h3>📝 Conversation Summary</h3>
          {summary && (
            <div className="summary-meta">
              <span>{summary.message_count} messages</span>
              <span>•</span>
              <span>{summary.duration}</span>
            </div>
          )}
        </div>
        {onClose && (
          <button className="close-summary-btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        )}
      </div>

      <div className="summary-content">
        {!summary && !loading && (
          <div className="summary-empty">
            <span className="empty-icon">📋</span>
            <p>Generate an AI-powered summary of this conversation</p>
            <button className="generate-btn" onClick={generateSummary} disabled={messages.length === 0}>
              Generate Summary
            </button>
          </div>
        )}

        {loading && (
          <div className="summary-loading">
            <div className="loading-spinner" />
            <p>Analyzing conversation and generating summary...</p>
          </div>
        )}

        {error && (
          <div className="summary-error">
            <span className="error-icon">❌</span>
            <p>{error}</p>
            <button className="retry-btn" onClick={generateSummary}>
              Try Again
            </button>
          </div>
        )}

        {summary && !loading && (
          <div className="summary-data">
            {/* Summary type selector */}
            <div className="summary-type-selector">
              <button
                className={`type-btn ${summaryType === 'brief' ? 'active' : ''}`}
                onClick={() => setSummaryType('brief')}
              >
                Brief
              </button>
              <button
                className={`type-btn ${summaryType === 'detailed' ? 'active' : ''}`}
                onClick={() => setSummaryType('detailed')}
              >
                Detailed
              </button>
              <button
                className={`type-btn ${summaryType === 'bullet' ? 'active' : ''}`}
                onClick={() => setSummaryType('bullet')}
              >
                Bullets
              </button>
            </div>

            {/* Brief summary */}
            {summaryType === 'brief' && (
              <div className="summary-section">
                <p className="summary-brief">{summary.brief}</p>
              </div>
            )}

            {/* Detailed summary */}
            {summaryType === 'detailed' && (
              <>
                <div className="summary-section">
                  <h4>Overview</h4>
                  <p>{summary.brief}</p>
                </div>

                <div className="summary-section">
                  <h4>Key Points</h4>
                  <ul className="key-points-list">
                    {summary.key_points.map((point, idx) => (
                      <li key={idx}>{point}</li>
                    ))}
                  </ul>
                </div>

                {summary.topics.length > 0 && (
                  <div className="summary-section">
                    <h4>Topics Discussed</h4>
                    <div className="topics-tags">
                      {summary.topics.map((topic) => (
                        <span key={topic} className="topic-tag">
                          #{topic}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {summary.action_items.length > 0 && (
                  <div className="summary-section">
                    <h4>Action Items</h4>
                    <ul className="action-items-list">
                      {summary.action_items.map((item, idx) => (
                        <li key={idx}>
                          <input type="checkbox" id={`action-${idx}`} />
                          <label htmlFor={`action-${idx}`}>{item}</label>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}

            {/* Bullet summary */}
            {summaryType === 'bullet' && (
              <div className="summary-section">
                <ul className="bullet-summary-list">
                  {summary.key_points.map((point, idx) => (
                    <li key={idx}>• {point}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Actions */}
            <div className="summary-actions">
              <button className="summary-action-btn" onClick={copySummary}>
                📋 Copy
              </button>
              <button className="summary-action-btn" onClick={generateSummary}>
                🔄 Regenerate
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConversationSummary;
