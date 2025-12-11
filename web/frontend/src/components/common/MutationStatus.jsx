import React from 'react';
import { Loader2, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import './MutationStatus.css';

/**
 * 🚀 PHASE 17 Week 5: Mutation Status Indicator
 * 
 * Displays the current status of a mutation (pending/success/error).
 * Can be used to show optimistic update status.
 * 
 * @param {Object} props
 * @param {boolean} props.isPending - Mutation is in progress
 * @param {boolean} props.isSuccess - Mutation succeeded
 * @param {boolean} props.isError - Mutation failed
 * @param {Error} props.error - Error object if failed
 * @param {string} props.pendingMessage - Message to show while pending
 * @param {string} props.successMessage - Message to show on success
 * @param {string} props.errorMessage - Message to show on error
 * @param {Function} props.onRetry - Retry callback
 * @param {Function} props.onDismiss - Dismiss callback
 * @param {boolean} props.inline - Render inline vs floating
 */
export function MutationStatus({
  isPending,
  isSuccess,
  isError,
  error,
  pendingMessage = 'Saving...',
  successMessage = 'Saved!',
  errorMessage = 'Failed to save',
  onRetry,
  onDismiss,
  inline = false,
}) {
  if (!isPending && !isSuccess && !isError) {
    return null;
  }

  const className = `mutation-status ${inline ? 'inline' : 'floating'} ${
    isPending ? 'pending' : isSuccess ? 'success' : 'error'
  }`;

  return (
    <div className={className}>
      {isPending && (
        <>
          <Loader2 size={16} className="spinning" />
          <span>{pendingMessage}</span>
        </>
      )}
      
      {isSuccess && (
        <>
          <CheckCircle size={16} />
          <span>{successMessage}</span>
          {onDismiss && (
            <button className="dismiss-btn" onClick={onDismiss}>×</button>
          )}
        </>
      )}
      
      {isError && (
        <>
          <XCircle size={16} />
          <span>{errorMessage}</span>
          {error?.message && (
            <span className="error-detail">{error.message}</span>
          )}
          {onRetry && (
            <button className="retry-btn" onClick={onRetry}>Retry</button>
          )}
          {onDismiss && (
            <button className="dismiss-btn" onClick={onDismiss}>×</button>
          )}
        </>
      )}
    </div>
  );
}

/**
 * Hook to manage mutation status display
 * Auto-dismisses success message after delay
 */
export function useMutationStatus(mutation, options = {}) {
  const {
    successAutoDismiss = 3000,
    pendingMessage,
    successMessage,
    errorMessage,
  } = options;

  const [dismissed, setDismissed] = React.useState(false);

  // Auto-dismiss on success
  React.useEffect(() => {
    if (mutation.isSuccess && successAutoDismiss) {
      const timer = setTimeout(() => {
        setDismissed(true);
      }, successAutoDismiss);
      return () => clearTimeout(timer);
    }
  }, [mutation.isSuccess, successAutoDismiss]);

  // Reset dismissed state when mutation resets
  React.useEffect(() => {
    if (mutation.isIdle) {
      setDismissed(false);
    }
  }, [mutation.isIdle]);

  const show = !dismissed && (mutation.isPending || mutation.isSuccess || mutation.isError);

  return {
    show,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess && !dismissed,
    isError: mutation.isError,
    error: mutation.error,
    pendingMessage,
    successMessage,
    errorMessage,
    onDismiss: () => setDismissed(true),
    onRetry: mutation.isError ? () => mutation.reset() : undefined,
  };
}

/**
 * Optimistic Update Indicator
 * Shows when an item is pending confirmation from server
 */
export function OptimisticIndicator({ isOptimistic }) {
  if (!isOptimistic) return null;

  return (
    <span className="optimistic-indicator" title="Saving...">
      <Loader2 size={12} className="spinning" />
    </span>
  );
}

/**
 * Offline Indicator
 * Shows when the app is offline
 */
export function OfflineIndicator({ isOnline }) {
  if (isOnline) return null;

  return (
    <div className="offline-indicator">
      <AlertTriangle size={16} />
      <span>You're offline. Changes will sync when you're back online.</span>
    </div>
  );
}

export default MutationStatus;
