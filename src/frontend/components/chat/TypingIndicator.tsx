import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface TypingIndicatorProps {
  isTyping: boolean;
  userName?: string;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ 
  isTyping, 
  userName = 'AI' 
}) => {
  const [dots, setDots] = useState(1);

  useEffect(() => {
    if (!isTyping) return;

    const interval = setInterval(() => {
      setDots(prev => (prev % 3) + 1);
    }, 500);

    return () => clearInterval(interval);
  }, [isTyping]);

  return (
    <AnimatePresence>
      {isTyping && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-500 dark:text-gray-400"
          role="status"
          aria-live="polite"
          aria-label={`${userName} is typing`}
        >
          <div className="flex gap-1">
            {[1, 2, 3].map((dot) => (
              <motion.div
                key={dot}
                className="w-2 h-2 rounded-full bg-blue-500 dark:bg-blue-400"
                animate={{
                  scale: dots >= dot ? [1, 1.3, 1] : 1,
                  opacity: dots >= dot ? [0.5, 1, 0.5] : 0.3,
                }}
                transition={{
                  duration: 0.6,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
              />
            ))}
          </div>
          <span className="font-medium">{userName} is thinking...</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default TypingIndicator;
