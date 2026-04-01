/**
 * SearchErrorBoundary - Error boundary configured for the place search feature.
 * Wraps the generic ErrorBoundary with search-specific retry behaviour.
 */

import React from 'react';
import ErrorBoundary from '../../common/jsx/ErrorBoundary';

const SearchErrorBoundary = ({ children }) => (
  <ErrorBoundary maxRetries={3}>
    {children}
  </ErrorBoundary>
);

export default SearchErrorBoundary;
