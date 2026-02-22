import React, { useEffect, useState } from 'react';
import { Toast as ToastType } from '../hooks/useToast';
import './Toast.css';

interface ToastProps {
  toast: ToastType;
  onDismiss: (id: string) => void;
}

/**
 * Toast notification component.
 * 
 * Displays temporary notifications with auto-dismiss and manual close.
 * Supports different types (success, error, warning, info).
 */
export const Toast: React.FC<ToastProps> = ({ toast, onDismiss }) => {
  const [isExiting, setIsExiting] = useState(false);
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    if (!toast.duration || toast.duration <= 0) return;

    const interval = 50; // Update every 50ms
    const decrement = (100 * interval) / toast.duration;

    const timer = setInterval(() => {
      setProgress(prev => {
        const next = prev - decrement;
        return next > 0 ? next : 0;
      });
    }, interval);

    return () => clearInterval(timer);
  }, [toast.duration]);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(() => {
      onDismiss(toast.id);
    }, 300); // Match CSS animation duration
  };

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return '✓';
      case 'error':
        return '✕';
      case 'warning':
        return '⚠';
      case 'info':
      default:
        return 'ℹ';
    }
  };

  return (
    <div
      className={`toast toast--${toast.type} ${
        isExiting ? 'toast--exiting' : ''
      }`}
      role="alert"
      aria-live="polite"
    >
      <div className="toast__content">
        <span className="toast__icon">{getIcon()}</span>
        <p className="toast__message">{toast.message}</p>
        <button
          className="toast__close"
          onClick={handleDismiss}
          aria-label="Dismiss notification"
        >
          ×
        </button>
      </div>
      {toast.duration && toast.duration > 0 && (
        <div className="toast__progress">
          <div
            className="toast__progress-bar"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
      {toast.action && (
        <button
          className="toast__action"
          onClick={() => {
            toast.action!.onClick();
            handleDismiss();
          }}
        >
          {toast.action.label}
        </button>
      )}
    </div>
  );
};

interface ToastContainerProps {
  toasts: ToastType[];
  onDismiss: (id: string) => void;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
}

/**
 * Container for rendering multiple toasts.
 */
export const ToastContainer: React.FC<ToastContainerProps> = ({
  toasts,
  onDismiss,
  position = 'top-right',
}) => {
  return (
    <div className={`toast-container toast-container--${position}`}>
      {toasts.map(toast => (
        <Toast key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
};
