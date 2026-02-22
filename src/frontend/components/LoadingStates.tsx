/**
 * Loading States Components
 * 
 * Provides various loading indicators and skeleton loaders.
 */

import React from 'react';

// Skeleton loader for messages
export const MessageSkeleton: React.FC = () => {
  return (
    <div className="message-skeleton">
      <div className="skeleton-avatar" />
      <div className="skeleton-content">
        <div className="skeleton-line skeleton-line-long" />
        <div className="skeleton-line skeleton-line-medium" />
        <div className="skeleton-line skeleton-line-short" />
      </div>
    </div>
  );
};

// Spinner loader
export const Spinner: React.FC<{ size?: 'small' | 'medium' | 'large' }> = ({ 
  size = 'medium' 
}) => {
  return (
    <div className={`spinner spinner-${size}`} role="status" aria-label="Loading">
      <div className="spinner-circle" />
    </div>
  );
};

// Progress bar
export const ProgressBar: React.FC<{ 
  progress: number; 
  label?: string;
  showPercentage?: boolean;
}> = ({ progress, label, showPercentage = true }) => {
  const percentage = Math.min(Math.max(progress, 0), 100);

  return (
    <div className="progress-bar-container">
      {label && <div className="progress-label">{label}</div>}
      <div className="progress-bar">
        <div 
          className="progress-bar-fill" 
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      {showPercentage && (
        <div className="progress-percentage">{percentage.toFixed(0)}%</div>
      )}
    </div>
  );
};

// Shimmer effect wrapper
export const Shimmer: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="shimmer-wrapper">
      {children}
      <div className="shimmer" />
    </div>
  );
};
