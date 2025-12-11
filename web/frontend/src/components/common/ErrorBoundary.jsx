import React, { Component } from 'react';
import { RefreshCw, AlertTriangle, Home } from 'lucide-react';
import './ErrorBoundary.css';

/**
 * 🚀 PHASE 17 Week 4: Error Boundary Component
 * 
 * Catches JavaScript errors in child components and displays a fallback UI.
 * Features:
 * - Retry button to attempt recovery
 * - Home button to navigate away
 * - Shows cached data if available (graceful degradation)
 * - Logs errors for debugging
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null,
      retryCount: 0
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render shows the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details for debugging
    console.error('🚨 ErrorBoundary caught an error:', error);
    console.error('Component stack:', errorInfo.componentStack);
    
    this.setState({ errorInfo });
    
    // Report to error tracking service (if configured)
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleRetry = () => {
    const { retryCount } = this.state;
    const maxRetries = this.props.maxRetries || 3;
    
    if (retryCount < maxRetries) {
      console.log(`🔄 Retry attempt ${retryCount + 1}/${maxRetries}`);
      this.setState({ 
        hasError: false, 
        error: null, 
        errorInfo: null,
        retryCount: retryCount + 1
      });
      
      // Call onRetry callback if provided
      if (this.props.onRetry) {
        this.props.onRetry();
      }
    } else {
      console.warn('❌ Max retries reached');
    }
  };

  handleGoHome = () => {
    // Reset state and navigate home
    this.setState({ 
      hasError: false, 
      error: null, 
      errorInfo: null,
      retryCount: 0
    });
    
    if (this.props.onGoHome) {
      this.props.onGoHome();
    } else {
      // Default: reload page
      window.location.href = '/';
    }
  };

  render() {
    const { hasError, error, retryCount } = this.state;
    const { children, fallback, cachedData, maxRetries = 3 } = this.props;
    
    if (hasError) {
      // Custom fallback provided
      if (fallback) {
        return fallback;
      }
      
      const canRetry = retryCount < maxRetries;
      
      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <AlertTriangle size={48} className="error-icon" />
            <h2>Something went wrong</h2>
            <p className="error-message">
              {error?.message || 'An unexpected error occurred'}
            </p>
            
            {/* Show cached data if available */}
            {cachedData && (
              <div className="cached-data-notice">
                <p>📦 Showing cached data (may be outdated)</p>
              </div>
            )}
            
            <div className="error-actions">
              {canRetry && (
                <button 
                  className="btn-retry" 
                  onClick={this.handleRetry}
                >
                  <RefreshCw size={18} />
                  Try Again ({maxRetries - retryCount} left)
                </button>
              )}
              
              <button 
                className="btn-home" 
                onClick={this.handleGoHome}
              >
                <Home size={18} />
                Go to Dashboard
              </button>
            </div>
            
            {/* Debug info in development */}
            {process.env.NODE_ENV === 'development' && (
              <details className="error-details">
                <summary>Error Details (Dev Only)</summary>
                <pre>{error?.stack}</pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return children;
  }
}

/**
 * Hook-based error boundary wrapper for functional components
 * Usage: <QueryErrorBoundary queryResult={queryResult}>...</QueryErrorBoundary>
 */
export function QueryErrorBoundary({ 
  queryResult, 
  children, 
  loadingComponent,
  errorMessage = 'Failed to load data'
}) {
  const { data, error, isLoading, isError, refetch } = queryResult;
  
  if (isLoading && !data) {
    return loadingComponent || (
      <div className="query-loading">
        <RefreshCw size={24} className="spinning" />
        <p>Loading...</p>
      </div>
    );
  }
  
  if (isError) {
    return (
      <div className="query-error">
        <AlertTriangle size={32} className="error-icon" />
        <p>{errorMessage}</p>
        <p className="error-detail">{error?.message}</p>
        <button className="btn-retry" onClick={() => refetch()}>
          <RefreshCw size={16} />
          Retry
        </button>
        
        {/* Show stale data if available */}
        {data && (
          <div className="stale-data-container">
            <p className="stale-notice">📦 Showing cached data:</p>
            {children}
          </div>
        )}
      </div>
    );
  }
  
  return children;
}

export default ErrorBoundary;
