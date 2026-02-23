import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Copy, RefreshCw, Edit2, Trash2, MoreVertical } from 'lucide-react';

interface MessageActionsProps {
  messageId: string;
  content: string;
  onCopy?: () => void;
  onRegenerate?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  canEdit?: boolean;
  canDelete?: boolean;
}

export const MessageActions: React.FC<MessageActionsProps> = ({
  messageId,
  content,
  onCopy,
  onRegenerate,
  onEdit,
  onDelete,
  canEdit = false,
  canDelete = false,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      onCopy?.();
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [content, onCopy]);

  const handleRegenerate = useCallback(() => {
    onRegenerate?.();
    setShowMenu(false);
  }, [onRegenerate]);

  const handleEdit = useCallback(() => {
    onEdit?.();
    setShowMenu(false);
  }, [onEdit]);

  const handleDelete = useCallback(() => {
    if (window.confirm('Are you sure you want to delete this message?')) {
      onDelete?.();
      setShowMenu(false);
    }
  }, [onDelete]);

  const actions = [
    {
      icon: Copy,
      label: copied ? 'Copied!' : 'Copy',
      onClick: handleCopy,
      show: true,
      className: copied ? 'text-green-600 dark:text-green-400' : '',
    },
    {
      icon: RefreshCw,
      label: 'Regenerate',
      onClick: handleRegenerate,
      show: !!onRegenerate,
    },
    {
      icon: Edit2,
      label: 'Edit',
      onClick: handleEdit,
      show: canEdit && !!onEdit,
    },
    {
      icon: Trash2,
      label: 'Delete',
      onClick: handleDelete,
      show: canDelete && !!onDelete,
      className: 'text-red-600 dark:text-red-400',
    },
  ].filter(action => action.show);

  return (
    <div className="relative">
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setShowMenu(prev => !prev)}
        className="
          p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800
          text-gray-500 dark:text-gray-400
          transition-colors duration-150
        "
        aria-label="Message actions"
        aria-expanded={showMenu}
        aria-haspopup="menu"
      >
        <MoreVertical className="w-4 h-4" />
      </motion.button>

      <AnimatePresence>
        {showMenu && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowMenu(false)}
              className="fixed inset-0 z-40"
            />

            {/* Menu */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              transition={{ duration: 0.1 }}
              className="
                absolute right-0 top-full mt-1 z-50
                min-w-[160px] py-1 rounded-lg shadow-lg
                bg-white dark:bg-gray-800 
                border border-gray-200 dark:border-gray-700
              "
              role="menu"
            >
              {actions.map(({ icon: Icon, label, onClick, className }) => (
                <button
                  key={label}
                  onClick={onClick}
                  className={`
                    w-full flex items-center gap-2 px-4 py-2
                    text-sm text-left
                    hover:bg-gray-100 dark:hover:bg-gray-700
                    transition-colors duration-150
                    ${className || 'text-gray-700 dark:text-gray-300'}
                  `}
                  role="menuitem"
                >
                  <Icon className="w-4 h-4" />
                  <span>{label}</span>
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default MessageActions;
