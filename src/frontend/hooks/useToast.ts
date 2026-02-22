/**
 * Toast Hook
 * 
 * Provides toast notification functionality.
 * 
 * Features:
 * - Show toast notifications
 * - Multiple types (success, error, warning, info)
 * - Auto-dismiss
 * - Queue management
 * - Action buttons
 * 
 * Usage:
 *   const { showToast } = useToast();
 *   
 *   showToast({
 *     type: 'success',
 *     message: 'Operation completed',
 *     duration: 3000,
 *   });
 */

import { useContext } from 'react';
import { ToastContext, Toast } from '../contexts/ToastContext';

export const useToast = () => {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }

  return context;
};

export type { Toast };
