/**
 * Error Boundary Component
 * 
 * Catches JavaScript errors anywhere in the component tree and displays
 * a fallback UI instead of crashing the entire application.
 * 
 * Features:
 * - Graceful error recovery
 * - Error logging and reporting
 * - User-friendly error messages
 * - Retry mechanism
 * - Development mode with stack traces
 * 
 * Usage:
 *   <ErrorBoundary fallback={<ErrorFallback />}>
 *     <YourComponent />
 *   </ErrorBoundary>
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to monitoring service
    this.logErrorToService(error, errorInfo);

    // Update state with error details
    this.setState({
      error,
      errorInfo,
    });

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);
  }

  logErrorToService(error: Error, errorInfo: ErrorInfo): void {
    // In production, send to error tracking service (Sentry, etc.)
    if (process.env.NODE_ENV === 'production') {
      // Example: Sentry.captureException(error, { extra: errorInfo });
      console.error('Error caught by boundary:', error, errorInfo);
    } else {
      console.error('Error caught by boundary:', error, errorInfo);
    }
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback } = this.props;

    if (hasError) {
      // Use custom fallback if provided
      if (fallback) {
        return fallback;
      }

      // Default fallback UI
      return (
        <ErrorFallbackUI
          error={error}
          errorInfo={errorInfo}
          onReset={this.handleReset}
        />
      );
    }

    return children;
  }
}

interface ErrorFallbackProps {
  error: Error | null;
  errorInfo: ErrorInfo | null;
  onReset: () => void;
}

const ErrorFallbackUI: React.FC<ErrorFallbackProps> = ({ error, errorInfo, onReset }) => {
  const isDevelopment = process.env.NODE_ENV === 'development';

  return (
    <div className="error-boundary-container">
      <div className="error-boundary-content">
        <div className="error-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
            <path d="M12 8v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            <circle cx="12" cy="16" r="0.5" fill="currentColor" />
          </svg>
        </div>

        <h1 className="error-title">Oops! Something went wrong</h1>
        
        <p className="error-description">
          We encountered an unexpected error. Don't worry, your data is safe.
        </p>

        {isDevelopment && error && (
          <div className="error-details">
            <h3>Error Details (Development Mode)</h3>
            <pre className="error-message">{error.toString()}</pre>
            {errorInfo && (
              <details className="error-stack">
                <summary>Stack Trace</summary>
                <pre>{errorInfo.componentStack}</pre>
              </details>
            )}
          </div>
        )}

        <div className="error-actions">
          <button className="btn-primary" onClick={onReset}>
            Try Again
          </button>
          <button className="btn-secondary" onClick={() => window.location.reload()}>
            Reload Page
          </button>
          <button className="btn-secondary" onClick={() => window.location.href = '/'}>
            Go Home
          </button>
        </div>

        <div className="error-support">
          <p>
            If this problem persists, please{' '}
            <a href="mailto:support@zakera.app">contact support</a> or{' '}
            <a href="https://github.com/itsmepraks/zakera/issues">report an issue</a>.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ErrorBoundary;
