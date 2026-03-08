/**
 * Message Reactions Component
 * 
 * Allows users to react to messages with emojis and provide feedback
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  ReactionType,
  ReactionCount,
  REACTION_EMOJIS,
  REACTION_LABELS,
  REACTION_COLORS,
} from '../../types/reactions';
import './MessageReactions.css';

interface MessageReactionsProps {
  messageId: string;
  reactions: ReactionCount[];
  onReact: (messageId: string, reactionType: ReactionType) => void;
  onFeedback: (messageId: string, feedbackType: 'positive' | 'negative', text?: string) => void;
  compact?: boolean;
  disabled?: boolean;
}

export const MessageReactions: React.FC<MessageReactionsProps> = ({
  messageId,
  reactions,
  onReact,
  onFeedback,
  compact = false,
  disabled = false,
}) => {
  const [showPicker, setShowPicker] = useState(false);
  const [showFeedbackForm, setShowFeedbackForm] = useState(false);
  const [feedbackType, setFeedbackType] = useState<'positive' | 'negative' | null>(null);
  const [feedbackText, setFeedbackText] = useState('');
  const pickerRef = useRef<HTMLDivElement>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);

  // All available reactions
  const allReactions: ReactionType[] = [
    'thumbs_up',
    'thumbs_down',
    'heart',
    'fire',
    'thinking',
    'check',
    'star',
    'celebrate',
  ];

  // Quick reactions (shown inline)
  const quickReactions: ReactionType[] = ['thumbs_up', 'thumbs_down', 'heart'];

  // Get reaction counts
  const getReactionCount = (type: ReactionType): ReactionCount | undefined => {
    return reactions.find((r) => r.type === type);
  };

  // Handle reaction click
  const handleReactionClick = (type: ReactionType) => {
    if (!disabled) {
      onReact(messageId, type);
      setShowPicker(false);
    }
  };

  // Handle feedback submission
  const handleFeedbackSubmit = () => {
    if (feedbackType && !disabled) {
      onFeedback(messageId, feedbackType, feedbackText.trim() || undefined);
      setShowFeedbackForm(false);
      setFeedbackType(null);
      setFeedbackText('');

      // Also add thumbs up/down reaction
      const reactionType: ReactionType =
        feedbackType === 'positive' ? 'thumbs_up' : 'thumbs_down';
      handleReactionClick(reactionType);
    }
  };

  // Handle feedback button click
  const handleFeedbackClick = (type: 'positive' | 'negative') => {
    if (!disabled) {
      setFeedbackType(type);
      setShowFeedbackForm(true);
      setShowPicker(false);
    }
  };

  // Close picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setShowPicker(false);
      }
      if (feedbackRef.current && !feedbackRef.current.contains(event.target as Node)) {
        setShowFeedbackForm(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Get total reaction count
  const totalReactions = reactions.reduce((sum, r) => sum + r.count, 0);

  return (
    <div className={`message-reactions-container ${compact ? 'compact' : ''}`}>
      {/* Existing reactions */}
      <div className="existing-reactions">
        {reactions
          .filter((r) => r.count > 0)
          .map((reaction) => (
            <button
              key={reaction.type}
              className={`reaction-bubble ${reaction.user_reacted ? 'user-reacted' : ''}`}
              onClick={() => handleReactionClick(reaction.type)}
              disabled={disabled}
              title={REACTION_LABELS[reaction.type]}
              style={{
                borderColor: reaction.user_reacted ? REACTION_COLORS[reaction.type] : undefined,
              }}
            >
              <span className="reaction-emoji">{REACTION_EMOJIS[reaction.type]}</span>
              <span className="reaction-count">{reaction.count}</span>
            </button>
          ))}
      </div>

      {/* Action buttons */}
      <div className="reaction-actions">
        {/* Quick reaction buttons (inline) */}
        {!compact && (
          <div className="quick-reactions">
            {quickReactions.map((type) => {
              const reactionData = getReactionCount(type);
              const hasReacted = reactionData?.user_reacted || false;

              return (
                <button
                  key={type}
                  className={`quick-reaction-btn ${hasReacted ? 'reacted' : ''}`}
                  onClick={() => handleReactionClick(type)}
                  disabled={disabled}
                  title={REACTION_LABELS[type]}
                  style={{
                    color: hasReacted ? REACTION_COLORS[type] : undefined,
                  }}
                >
                  {REACTION_EMOJIS[type]}
                </button>
              );
            })}
          </div>
        )}

        {/* More reactions button */}
        <div className="more-reactions-wrapper" ref={pickerRef}>
          <button
            className="more-reactions-btn"
            onClick={() => setShowPicker(!showPicker)}
            disabled={disabled}
            title="More reactions"
          >
            {compact ? '😊+' : '➕'}
          </button>

          {/* Reaction picker */}
          {showPicker && (
            <div className="reaction-picker">
              <div className="picker-header">
                <span>Choose a reaction</span>
                <button
                  className="picker-close"
                  onClick={() => setShowPicker(false)}
                  aria-label="Close"
                >
                  ✕
                </button>
              </div>
              <div className="picker-grid">
                {allReactions.map((type) => {
                  const reactionData = getReactionCount(type);
                  const hasReacted = reactionData?.user_reacted || false;

                  return (
                    <button
                      key={type}
                      className={`picker-reaction ${hasReacted ? 'active' : ''}`}
                      onClick={() => handleReactionClick(type)}
                      title={REACTION_LABELS[type]}
                      style={{
                        backgroundColor: hasReacted
                          ? `${REACTION_COLORS[type]}20`
                          : undefined,
                        borderColor: hasReacted ? REACTION_COLORS[type] : undefined,
                      }}
                    >
                      <span className="picker-emoji">{REACTION_EMOJIS[type]}</span>
                      <span className="picker-label">{REACTION_LABELS[type]}</span>
                      {reactionData && reactionData.count > 0 && (
                        <span className="picker-count">{reactionData.count}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Feedback button */}
        {!compact && (
          <div className="feedback-wrapper" ref={feedbackRef}>
            <button
              className="feedback-btn"
              onClick={() => setShowFeedbackForm(!showFeedbackForm)}
              disabled={disabled}
              title="Provide feedback"
            >
              💬
            </button>

            {/* Feedback form */}
            {showFeedbackForm && (
              <div className="feedback-form">
                <div className="feedback-header">
                  <span>How was this response?</span>
                  <button
                    className="feedback-close"
                    onClick={() => setShowFeedbackForm(false)}
                    aria-label="Close"
                  >
                    ✕
                  </button>
                </div>

                <div className="feedback-buttons">
                  <button
                    className={`feedback-option ${feedbackType === 'positive' ? 'active' : ''}`}
                    onClick={() => handleFeedbackClick('positive')}
                  >
                    <span className="feedback-icon">👍</span>
                    <span>Helpful</span>
                  </button>
                  <button
                    className={`feedback-option ${feedbackType === 'negative' ? 'active' : ''}`}
                    onClick={() => handleFeedbackClick('negative')}
                  >
                    <span className="feedback-icon">👎</span>
                    <span>Not Helpful</span>
                  </button>
                </div>

                {feedbackType && (
                  <div className="feedback-details">
                    <textarea
                      className="feedback-textarea"
                      placeholder="Tell us more (optional)"
                      value={feedbackText}
                      onChange={(e) => setFeedbackText(e.target.value)}
                      maxLength={500}
                      rows={3}
                    />
                    <div className="feedback-actions">
                      <span className="char-count">
                        {feedbackText.length}/500
                      </span>
                      <button className="submit-feedback-btn" onClick={handleFeedbackSubmit}>
                        Submit Feedback
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Reaction summary (compact mode) */}
      {compact && totalReactions > 0 && (
        <div className="reaction-summary" title={`${totalReactions} reactions`}>
          <span className="summary-icon">😊</span>
          <span className="summary-count">{totalReactions}</span>
        </div>
      )}
    </div>
  );
};

export default MessageReactions;
