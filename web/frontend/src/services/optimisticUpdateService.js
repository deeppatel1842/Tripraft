/**
 * Optimistic Update Service
 * 
 * Provides instant UI updates with background API calls and automatic rollback.
 * Based on Expense Engine's proven optimistic update pattern.
 * 
 * Pattern:
 * 1. Update UI immediately (optimistic state)
 * 2. Show subtle loading indicator
 * 3. Call API in background
 * 4. On success: Replace optimistic with real data
 * 5. On error: Rollback optimistic update + show error
 * 
 * Benefits:
 * - 0ms perceived latency
 * - Instant feedback for user actions
 * - Graceful error handling with rollback
 * - Professional UX like native apps
 */

class OptimisticUpdateService {
  constructor() {
    this.pendingUpdates = new Map(); // Track in-flight requests
    this.rollbackCallbacks = new Map(); // Store rollback functions
  }

  /**
   * Execute an optimistic update
   * 
   * @param {string} id - Unique ID for this operation
   * @param {function} optimisticUpdate - Function to update UI immediately
   * @param {function} apiCall - Async function for backend API call
   * @param {function} onSuccess - Callback when API succeeds (receives API response)
   * @param {function} onError - Callback when API fails (receives error)
   * @param {function} rollback - Function to revert UI changes on error
   * @returns {Promise} Resolves when API call completes
   */
  async execute({
    id,
    optimisticUpdate,
    apiCall,
    onSuccess,
    onError,
    rollback
  }) {
    console.log(`⚡ [OPTIMISTIC] Starting optimistic update: ${id}`);

    try {
      // Step 1: Update UI immediately
      const startTime = performance.now();
      const optimisticResult = optimisticUpdate();
      console.log(`✅ [OPTIMISTIC] UI updated instantly in ${(performance.now() - startTime).toFixed(1)}ms`);

      // Store rollback callback
      this.rollbackCallbacks.set(id, { rollback, optimisticResult });

      // Mark as pending
      this.pendingUpdates.set(id, true);

      // Step 2: Call API in background
      console.log(`🌐 [OPTIMISTIC] Calling API for: ${id}`);
      const apiStartTime = performance.now();
      const result = await apiCall();
      const apiDuration = (performance.now() - apiStartTime).toFixed(0);
      console.log(`✅ [OPTIMISTIC] API completed in ${apiDuration}ms`);

      // Step 3: Success - Replace optimistic with real data
      this.pendingUpdates.delete(id);
      this.rollbackCallbacks.delete(id);
      
      if (onSuccess) {
        onSuccess(result);
      }

      const totalDuration = (performance.now() - startTime).toFixed(0);
      console.log(`✅ [OPTIMISTIC] Total operation: ${totalDuration}ms (UI instant, API ${apiDuration}ms)`);
      
      return result;

    } catch (error) {
      console.error(`❌ [OPTIMISTIC] Error in ${id}:`, error);

      // Step 4: Error - Rollback UI changes
      const rollbackData = this.rollbackCallbacks.get(id);
      if (rollbackData && rollback) {
        console.log(`🔄 [OPTIMISTIC] Rolling back UI changes for: ${id}`);
        rollback(rollbackData.optimisticResult);
      }

      this.pendingUpdates.delete(id);
      this.rollbackCallbacks.delete(id);

      // Call error handler
      if (onError) {
        onError(error);
      }

      throw error;
    }
  }

  /**
   * Check if an operation is pending
   */
  isPending(id) {
    return this.pendingUpdates.has(id);
  }

  /**
   * Get all pending operation IDs
   */
  getPendingOperations() {
    return Array.from(this.pendingUpdates.keys());
  }

  /**
   * Cancel a pending operation (does not stop API call, just clears tracking)
   */
  cancel(id) {
    console.log(`🚫 [OPTIMISTIC] Canceling operation: ${id}`);
    this.pendingUpdates.delete(id);
    this.rollbackCallbacks.delete(id);
  }

  /**
   * Clear all pending operations
   */
  clearAll() {
    console.log('🧹 [OPTIMISTIC] Clearing all pending operations');
    this.pendingUpdates.clear();
    this.rollbackCallbacks.clear();
  }
}

// Export singleton instance
const optimisticUpdateService = new OptimisticUpdateService();
export default optimisticUpdateService;
