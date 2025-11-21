import { QueryClient } from '@tanstack/react-query';

// Create a QueryClient with optimized configuration
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cache data for 5 minutes by default
      staleTime: 5 * 60 * 1000,
      
      // Keep data in cache for 10 minutes
      gcTime: 10 * 60 * 1000,
      
      // Retry failed requests 2 times
      retry: 2,
      
      // Exponential backoff for retries
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      
      // Refetch on window focus for real-time data
      refetchOnWindowFocus: true,
      
      // Don't refetch on mount if data is fresh
      refetchOnMount: false,
      
      // Enable request deduplication
      refetchOnReconnect: true,
    },
    mutations: {
      // Retry failed mutations once
      retry: 1,
    },
  },
});
