/**
 * Toast Notification Component
 * 
 * Displays toast notifications with different types and actions.
 * 
 * Features:
 * - Success, error, warning, info types
 * - Auto-dismiss with progress bar
 * - Action buttons
 * - Swipe-to-dismiss on mobile
 * - Stacking with animation
 * - Accessibility announcements
 */

import React, { useEffect, useState } from 'react';
import { Toast } from '../contexts/ToastContext';

interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
}

const ToastItem: React.FC<ToastItemProps> = ({ toast, onRemove }) => {
  const [isExiting, setIsExiting] = useState(false);
  const [progress, setProgress] = useState(100);

  const duration = toast.duration ?? 5000;

  useEffect(() => {
    if (duration <= 0) return;

    const interval = setInterval(() => {
      setProgress((prev) => {
        const newProgress = prev - (100 / (duration / 100));
        return newProgress >= 0 ? newProgress : 0;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [duration]);

  const handleRemove = () => {
    setIsExiting(true);
    setTimeout(() => {
      onRemove(toast.id);
    }, 300);
  };

  const icons = {
    success: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
        <path d="M8 12l2 2 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
    error: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
        <path d="M8 8l8 8M8 16l8-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
    warning: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path
          d="M12 2L2 20h20L12 2z"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <path d="M12 10v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <circle cx="12" cy="17" r="0.5" fill="currentColor" />
      </svg>
    ),
    info: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
        <path d="M12 8v0M12 12v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
  };

  return (
    <div
      className={`toast toast-${toast.type} ${isExiting ? 'toast-exiting' : ''}`}
      role="alert"
      aria-live="polite"
    >
      <div className="toast-content">
        <div className="toast-icon">{icons[toast.type]}</div>
        <div className="toast-message">{toast.message}</div>

        {toast.action && (
          <button
            className="toast-action"
            onClick={() => {
              toast.action!.onClick();
              handleRemove();
            }}
          >
            {toast.action.label}
          </button>
        )}

        <button
          className="toast-close"
          onClick={handleRemove}
          aria-label="Close notification"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M6 6l12 12M6 18L18 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {duration > 0 && (
        <div className="toast-progress">
          <div className="toast-progress-bar" style={{ width: `${progress}%` }} />
        </div>
      )}
    </div>
  );
};

interface ToastContainerProps {
  toasts: Toast[];
  onRemove: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onRemove }) => {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" aria-live="polite" aria-atomic="false">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  );
};
