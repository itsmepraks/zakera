import React from 'react';
import './LoadingSkeleton.css';

interface LoadingSkeletonProps {
  count?: number;
}

/**
 * Loading skeleton for chat messages.
 * Provides visual feedback while messages are loading.
 */
export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  count = 3
}) => {
  return (
    <div className="loading-skeleton-container">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="skeleton-message">
          <div className="skeleton-avatar"></div>
          <div className="skeleton-content">
            <div className="skeleton-header"></div>
            <div className="skeleton-text line-1"></div>
            <div className="skeleton-text line-2"></div>
            <div className="skeleton-text line-3"></div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default LoadingSkeleton;