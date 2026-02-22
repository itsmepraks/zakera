import React, { Component, ReactNode } from 'react';
import './ErrorBoundary.css';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  resetKeys?: Array<string | number>;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  errorCount: number;
}

/**
 * Error Boundary component for graceful error handling.
 * 
 * Catches React errors in child components and displays a fallback UI.
 * Supports error recovery, logging, and retry mechanisms.
 * 
 * @example
 * <ErrorBoundary onError={logErrorToService}>
 *   <MyComponent />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    const { onError } = this.props;
    const { errorCount } = this.state;

    this.setState({
      error,
      errorInfo,
      errorCount: errorCount + 1,
    });

    // Log error to monitoring service
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    if (onError) {
      onError(error, errorInfo);
    }

    // Report to error tracking service (e.g., Sentry)
    if (process.env.NODE_ENV === 'production') {
      this.reportError(error, errorInfo);
    }
  }

  componentDidUpdate(prevProps: Props) {
    const { resetKeys } = this.props;
    const { hasError } = this.state;

    if (hasError && resetKeys && prevProps.resetKeys) {
      const hasResetKeyChanged = resetKeys.some(
        (key, index) => key !== prevProps.resetKeys![index]
      );

      if (hasResetKeyChanged) {
        this.reset();
      }
    }
  }

  reportError = (error: Error, errorInfo: React.ErrorInfo) => {
    // TODO: Integrate with error tracking service (Sentry, Rollbar, etc.)
    fetch('/api/v1/monitoring/errors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: {
          message: error.message,
          stack: error.stack,
          name: error.name,
        },
        errorInfo: {
          componentStack: errorInfo.componentStack,
        },
        metadata: {
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString(),
          url: window.location.href,
        },
      }),
    }).catch(console.error);
  };

  reset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    const { hasError, error, errorInfo, errorCount } = this.state;
    const { children, fallback } = this.props;

    if (hasError) {
      // Use custom fallback if provided
      if (fallback) {
        return fallback;
      }

      // Too many errors - show critical error
      if (errorCount >= 3) {
        return (
          <div className="error-boundary error-boundary--critical">
            <div className="error-boundary__content">
              <h1 className="error-boundary__title">⚠️ Critical Error</h1>
              <p className="error-boundary__message">
                Multiple errors occurred. Please refresh the page.
              </p>
              <button
                className="error-boundary__button error-boundary__button--primary"
                onClick={() => window.location.reload()}
              >
                Refresh Page
              </button>
            </div>
          </div>
        );
      }

      // Default error UI
      return (
        <div className="error-boundary">
          <div className="error-boundary__content">
            <h1 className="error-boundary__title">😕 Something went wrong</h1>
            <p className="error-boundary__message">
              We're sorry, but something unexpected happened. You can try again or
              contact support if the problem persists.
            </p>

            {process.env.NODE_ENV === 'development' && error && (
              <details className="error-boundary__details">
                <summary>Error Details (Development Only)</summary>
                <div className="error-boundary__stack">
                  <strong>{error.toString()}</strong>
                  <pre>{errorInfo?.componentStack}</pre>
                </div>
              </details>
            )}

            <div className="error-boundary__actions">
              <button
                className="error-boundary__button error-boundary__button--primary"
                onClick={this.reset}
              >
                Try Again
              </button>
              <button
                className="error-boundary__button error-boundary__button--secondary"
                onClick={() => window.location.reload()}
              >
                Refresh Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return children;
  }
}

/**
 * Higher-order component for wrapping components with error boundary.
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<Props, 'children'>
) {
  return (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );
}
