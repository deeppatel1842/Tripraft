/**
 * Error Handler — Centralized status-code-to-message mapping
 *
 * Used by apiClient (throws structured errors) and consumed by
 * Toast components or any UI that needs user-friendly error text.
 */

const STATUS_MESSAGES = {
  0:   'Network error. Check your connection and try again.',
  400: 'Invalid request. Please check your input.',
  401: 'Session expired. Please log in again.',
  403: 'You do not have permission to perform this action.',
  404: 'The requested resource was not found.',
  409: 'This resource already exists or conflicts with another.',
  422: 'Please fix the validation errors and try again.',
  429: 'Too many requests. Please slow down and try again.',
  500: 'Something went wrong on our end. Please try again.',
  502: 'External service is temporarily unavailable.',
  503: 'Service is temporarily unavailable. Please try again later.',
};

/**
 * Get a user-friendly message for an API error.
 * @param {Error} error - Error thrown by apiClient (has .status, .message, .errors, .data)
 * @returns {{ message: string, fieldErrors: Object|null, shouldRedirect: boolean }}
 */
export function parseApiError(error) {
  const status = error.status || 0;
  const message = error.message || STATUS_MESSAGES[status] || STATUS_MESSAGES[0];
  const fieldErrors = error.errors || null;
  const shouldRedirect = status === 401;

  return { message, fieldErrors, shouldRedirect };
}

/**
 * Get a generic status-code message (for cases where the server message is missing).
 * @param {number} status
 * @returns {string}
 */
export function getStatusMessage(status) {
  return STATUS_MESSAGES[status] || STATUS_MESSAGES[0];
}

export default { parseApiError, getStatusMessage };
