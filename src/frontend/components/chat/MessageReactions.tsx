import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChatStore } from '../../store/chatStore';

interface Reaction {
  emoji: string;
  count: number;
  userReacted: boolean;
}

interface MessageReactionsProps {
  messageId: string;
  reactions: Reaction[];
  onReactionToggle: (messageId: string, emoji: string) => void;
}

const AVAILABLE_REACTIONS = ['👍', '👎', '❤️', '😂', '🤔', '🎉'];

export const MessageReactions: React.FC<MessageReactionsProps> = ({
  messageId,
  reactions,
  onReactionToggle,
}) => {
  const [showPicker, setShowPicker] = useState(false);
  const [isHovering, setIsHovering] = useState(false);

  const handleReactionClick = useCallback((emoji: string) => {
    onReactionToggle(messageId, emoji);
    setShowPicker(false);
  }, [messageId, onReactionToggle]);

  const handleAddReaction = useCallback(() => {
    setShowPicker(prev => !prev);
  }, []);

  return (
    <div 
      className="relative flex items-center gap-1 mt-1"
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => {
        setIsHovering(false);
        setShowPicker(false);
      }}
    >
      {/* Existing reactions */}
      <div className="flex gap-1">
        {reactions.map(({ emoji, count, userReacted }) => (
          <motion.button
            key={emoji}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => handleReactionClick(emoji)}
            className={`
              flex items-center gap-1 px-2 py-1 rounded-full text-sm
              transition-colors duration-200
              ${
                userReacted
                  ? 'bg-blue-100 dark:bg-blue-900/30 border-2 border-blue-500'
                  : 'bg-gray-100 dark:bg-gray-800 border-2 border-transparent hover:border-gray-300 dark:hover:border-gray-600'
              }
            `}
            aria-label={`React with ${emoji}`}
            role="checkbox"
            aria-checked={userReacted}
          >
            <span className="text-base">{emoji}</span>
            {count > 1 && (
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                {count}
              </span>
            )}
          </motion.button>
        ))}
      </div>

      {/* Add reaction button */}
      <AnimatePresence>
        {(isHovering || showPicker) && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={handleAddReaction}
            className="
              flex items-center justify-center w-7 h-7 rounded-full
              bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700
              border-2 border-transparent hover:border-gray-300 dark:hover:border-gray-600
              transition-colors duration-200
            "
            aria-label="Add reaction"
          >
            <span className="text-lg">+</span>
          </motion.button>
        )}
      </AnimatePresence>

      {/* Reaction picker */}
      <AnimatePresence>
        {showPicker && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.9 }}
            transition={{ duration: 0.15 }}
            className="
              absolute bottom-full left-0 mb-2 z-10
              flex gap-1 p-2 rounded-lg shadow-lg
              bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
            "
            role="menu"
            aria-label="Choose a reaction"
          >
            {AVAILABLE_REACTIONS.map((emoji) => (
              <motion.button
                key={emoji}
                whileHover={{ scale: 1.2 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => handleReactionClick(emoji)}
                className="
                  w-10 h-10 flex items-center justify-center rounded-lg
                  hover:bg-gray-100 dark:hover:bg-gray-700
                  transition-colors duration-150
                "
                aria-label={`React with ${emoji}`}
                role="menuitem"
              >
                <span className="text-2xl">{emoji}</span>
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default MessageReactions;
