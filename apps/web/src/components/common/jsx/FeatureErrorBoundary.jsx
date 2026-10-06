// Purpose: Contains feature rendering failures and provides an actionable recovery screen.
import { Component } from 'react';
import { RefreshCw, AlertTriangle } from 'lucide-react';
import '../css/FeatureErrorBoundary.css';

export default class FeatureErrorBoundary extends Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error(`[${this.props.featureName}] Error:`, error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="feb-container">
          <div className="feb-content">
            <AlertTriangle size={40} className="feb-icon" />
            <h3 className="feb-title">
              Something went wrong in {this.props.featureName || 'this section'}
            </h3>
            <p className="feb-message">
              This section encountered an error. The rest of the app still works.
            </p>
            <button className="feb-retry" onClick={this.handleRetry}>
              <RefreshCw size={16} />
              Try Again
            </button>
            {import.meta.env.DEV && this.state.error && (
              <details className="feb-details">
                <summary>Error Details (Dev Only)</summary>
                <pre>{this.state.error.stack}</pre>
              </details>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
