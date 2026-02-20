/**
 * LoadingStates Component
 * 
 * Provides skeleton loaders and loading indicators for better UX.
 */

import React from 'react';
import './LoadingStates.css';

interface MessageSkeletonProps {
  count?: number;
}

export const MessageSkeleton: React.FC<MessageSkeletonProps> = ({ count = 1 }) => {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="message-skeleton" aria-label="Loading message">
          <div className="skeleton-avatar" />
          <div className="skeleton-content">
            <div className="skeleton-header" />
            <div className="skeleton-text" />
            <div className="skeleton-text short" />
          </div>
        </div>
      ))}
    </>
  );
};

interface SpinnerProps {
  size?: 'small' | 'medium' | 'large';
  message?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({ 
  size = 'medium',
  message 
}) => {
  return (
    <div className="spinner-container" role="status">
      <div className={`spinner spinner-${size}`}>
        <div className="spinner-circle" />
      </div>
      {message && (
        <p className="spinner-message">{message}</p>
      )}
    </div>
  );
};

interface ProgressBarProps {
  progress: number;
  message?: string;
  showPercentage?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  message,
  showPercentage = true
}) => {
  return (
    <div className="progress-container" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
      {message && (
        <div className="progress-header">
          <span className="progress-message">{message}</span>
          {showPercentage && (
            <span className="progress-percentage">{progress}%</span>
          )}
        </div>
      )}
      <div className="progress-bar">
        <div 
          className="progress-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
};

export default { MessageSkeleton, Spinner, ProgressBar };
