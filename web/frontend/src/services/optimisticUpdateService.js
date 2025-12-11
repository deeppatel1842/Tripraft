/**
 * Optimistic Update Service
 * =========================
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
 * 
 * Phase 4 Enhancements:
 * - Expense-specific helpers
 * - Retry logic with backoff
 * - Conflict detection for real-time updates
 * - Queue management for sequential operations
 */

class OptimisticUpdateService {
  constructor() {
    this.pendingUpdates = new Map(); // Track in-flight requests
    this.rollbackCallbacks = new Map(); // Store rollback functions
    this.operationQueue = []; // Queue for sequential operations
    this.processingQueue = false;
    this.maxRetries = 3;
    this.retryDelay = 1000;
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
   * @param {object} options - Additional options { retry: boolean, retryCount: number }
   * @returns {Promise} Resolves when API call completes
   */
  async execute({
    id,
    optimisticUpdate,
    apiCall,
    onSuccess,
    onError,
    rollback,
    options = {}
  }) {
    const { retry = true, retryCount = 0 } = options;
    console.log(`[OPTIMISTIC] Starting optimistic update: ${id}`);

    try {
      // Step 1: Update UI immediately (only on first attempt)
      const startTime = performance.now();
      let optimisticResult = null;
      
      if (retryCount === 0) {
        optimisticResult = optimisticUpdate();
        console.log(`[OPTIMISTIC] UI updated instantly in ${(performance.now() - startTime).toFixed(1)}ms`);

        // Store rollback callback
        this.rollbackCallbacks.set(id, { rollback, optimisticResult });
      }

      // Mark as pending
      this.pendingUpdates.set(id, { startTime, retryCount });

      // Step 2: Call API in background
      console.log(`[OPTIMISTIC] Calling API for: ${id}`);
      const apiStartTime = performance.now();
      const result = await apiCall();
      const apiDuration = (performance.now() - apiStartTime).toFixed(0);
      console.log(`[OPTIMISTIC] API completed in ${apiDuration}ms`);

      // Step 3: Success - Replace optimistic with real data
      this.pendingUpdates.delete(id);
      this.rollbackCallbacks.delete(id);
      
      if (onSuccess) {
        onSuccess(result);
      }

      const totalDuration = (performance.now() - startTime).toFixed(0);
      console.log(`[OPTIMISTIC] Total operation: ${totalDuration}ms (UI instant, API ${apiDuration}ms)`);
      
      return result;

    } catch (error) {
      console.error(`[OPTIMISTIC] Error in ${id}:`, error);

      // Check if we should retry
      if (retry && retryCount < this.maxRetries && this._isRetryableError(error)) {
        console.log(`[OPTIMISTIC] Retrying ${id} (attempt ${retryCount + 1}/${this.maxRetries})`);
        await this._delay(this.retryDelay * Math.pow(2, retryCount));
        
        return this.execute({
          id,
          optimisticUpdate: () => {}, // Don't re-apply optimistic update on retry
          apiCall,
          onSuccess,
          onError,
          rollback,
          options: { retry, retryCount: retryCount + 1 }
        });
      }

      // Step 4: Error - Rollback UI changes
      const rollbackData = this.rollbackCallbacks.get(id);
      if (rollbackData && rollbackData.rollback) {
        console.log(`[OPTIMISTIC] Rolling back UI changes for: ${id}`);
        rollbackData.rollback(rollbackData.optimisticResult);
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

  // ===========================================================================
  // EXPENSE-SPECIFIC HELPERS
  // ===========================================================================

  /**
   * Optimistic expense creation
   * 
   * @param {object} expenseData - Expense data to create
   * @param {function} updateState - Function to update local state with new expense
   * @param {function} apiCall - API function to create expense
   * @param {object} callbacks - { onSuccess, onError }
   * @returns {Promise}
   */
  async createExpense(expenseData, updateState, apiCall, callbacks = {}) {
    const tempId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const optimisticExpense = {
      ...expenseData,
      id: tempId,
      expense_id: tempId,
      _optimistic: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    return this.execute({
      id: `create_expense_${tempId}`,
      optimisticUpdate: () => {
        updateState(prev => [optimisticExpense, ...prev]);
        return tempId;
      },
      apiCall,
      onSuccess: (result) => {
        // Replace optimistic expense with real one
        updateState(prev => prev.map(e => 
          e.id === tempId ? { ...result, _optimistic: false } : e
        ));
        if (callbacks.onSuccess) callbacks.onSuccess(result);
      },
      onError: callbacks.onError,
      rollback: (tempId) => {
        updateState(prev => prev.filter(e => e.id !== tempId));
      }
    });
  }

  /**
   * Optimistic expense update
   * 
   * @param {string} expenseId - Expense ID to update
   * @param {object} updates - Fields to update
   * @param {function} updateState - Function to update local state
   * @param {function} apiCall - API function to update expense
   * @param {object} callbacks - { onSuccess, onError }
   * @returns {Promise}
   */
  async updateExpense(expenseId, updates, updateState, apiCall, callbacks = {}) {
    let previousExpense = null;

    return this.execute({
      id: `update_expense_${expenseId}`,
      optimisticUpdate: () => {
        updateState(prev => {
          const idx = prev.findIndex(e => e.expense_id === expenseId || e.id === expenseId);
          if (idx !== -1) {
            previousExpense = { ...prev[idx] };
            const updated = [...prev];
            updated[idx] = { ...updated[idx], ...updates, _optimistic: true, updated_at: new Date().toISOString() };
            return updated;
          }
          return prev;
        });
        return previousExpense;
      },
      apiCall,
      onSuccess: (result) => {
        updateState(prev => prev.map(e => 
          (e.expense_id === expenseId || e.id === expenseId) 
            ? { ...result, _optimistic: false } 
            : e
        ));
        if (callbacks.onSuccess) callbacks.onSuccess(result);
      },
      onError: callbacks.onError,
      rollback: (previousExpense) => {
        if (previousExpense) {
          updateState(prev => prev.map(e => 
            (e.expense_id === expenseId || e.id === expenseId) ? previousExpense : e
          ));
        }
      }
    });
  }

  /**
   * Optimistic expense deletion
   * 
   * @param {string} expenseId - Expense ID to delete
   * @param {function} updateState - Function to update local state
   * @param {function} apiCall - API function to delete expense
   * @param {object} callbacks - { onSuccess, onError }
   * @returns {Promise}
   */
  async deleteExpense(expenseId, updateState, apiCall, callbacks = {}) {
    let deletedExpense = null;
    let deletedIndex = -1;

    return this.execute({
      id: `delete_expense_${expenseId}`,
      optimisticUpdate: () => {
        updateState(prev => {
          deletedIndex = prev.findIndex(e => e.expense_id === expenseId || e.id === expenseId);
          if (deletedIndex !== -1) {
            deletedExpense = prev[deletedIndex];
            return prev.filter(e => e.expense_id !== expenseId && e.id !== expenseId);
          }
          return prev;
        });
        return { expense: deletedExpense, index: deletedIndex };
      },
      apiCall,
      onSuccess: callbacks.onSuccess,
      onError: callbacks.onError,
      rollback: ({ expense, index }) => {
        if (expense && index !== -1) {
          updateState(prev => {
            const updated = [...prev];
            updated.splice(index, 0, expense);
            return updated;
          });
        }
      }
    });
  }

  /**
   * Optimistic settlement creation
   * 
   * @param {object} settlementData - Settlement data
   * @param {function} updateState - Function to update local state
   * @param {function} apiCall - API function to create settlement
   * @param {object} callbacks - { onSuccess, onError }
   * @returns {Promise}
   */
  async createSettlement(settlementData, updateState, apiCall, callbacks = {}) {
    const tempId = `temp_settlement_${Date.now()}`;
    const optimisticSettlement = {
      ...settlementData,
      id: tempId,
      settlement_id: tempId,
      _optimistic: true,
      status: 'pending',
      created_at: new Date().toISOString(),
    };

    return this.execute({
      id: `create_settlement_${tempId}`,
      optimisticUpdate: () => {
        updateState(prev => [optimisticSettlement, ...prev]);
        return tempId;
      },
      apiCall,
      onSuccess: (result) => {
        updateState(prev => prev.map(s => 
          s.id === tempId ? { ...result, _optimistic: false } : s
        ));
        if (callbacks.onSuccess) callbacks.onSuccess(result);
      },
      onError: callbacks.onError,
      rollback: (tempId) => {
        updateState(prev => prev.filter(s => s.id !== tempId));
      }
    });
  }

  // ===========================================================================
  // QUEUE MANAGEMENT
  // ===========================================================================

  /**
   * Queue an operation for sequential execution
   * Useful when operations must be executed in order
   */
  async queue(operation) {
    return new Promise((resolve, reject) => {
      this.operationQueue.push({ operation, resolve, reject });
      this._processQueue();
    });
  }

  async _processQueue() {
    if (this.processingQueue || this.operationQueue.length === 0) {
      return;
    }

    this.processingQueue = true;

    while (this.operationQueue.length > 0) {
      const { operation, resolve, reject } = this.operationQueue.shift();
      try {
        const result = await operation();
        resolve(result);
      } catch (error) {
        reject(error);
      }
    }

    this.processingQueue = false;
  }

  // ===========================================================================
  // CONFLICT DETECTION
  // ===========================================================================

  /**
   * Check if an operation conflicts with pending updates
   * 
   * @param {string} entityType - Type of entity (expense, settlement, etc.)
   * @param {string} entityId - Entity ID
   * @returns {boolean} True if there's a conflict
   */
  hasConflict(entityType, entityId) {
    const conflictPatterns = [
      `create_${entityType}_${entityId}`,
      `update_${entityType}_${entityId}`,
      `delete_${entityType}_${entityId}`,
    ];

    for (const [key] of this.pendingUpdates) {
      if (conflictPatterns.some(pattern => key.includes(entityId))) {
        return true;
      }
    }
    return false;
  }

  /**
   * Wait for a specific entity's pending operations to complete
   * 
   * @param {string} entityId - Entity ID to wait for
   * @param {number} timeout - Max wait time in ms
   * @returns {Promise}
   */
  async waitForEntity(entityId, timeout = 5000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      let hasPending = false;
      for (const [key] of this.pendingUpdates) {
        if (key.includes(entityId)) {
          hasPending = true;
          break;
        }
      }
      
      if (!hasPending) return;
      await this._delay(100);
    }
    
    console.warn(`[OPTIMISTIC] Timeout waiting for entity: ${entityId}`);
  }

  // ===========================================================================
  // UTILITY METHODS
  // ===========================================================================

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
   * Get statistics about pending operations
   */
  getStats() {
    return {
      pendingCount: this.pendingUpdates.size,
      pendingOperations: Array.from(this.pendingUpdates.keys()),
      queueLength: this.operationQueue.length,
      processingQueue: this.processingQueue
    };
  }

  /**
   * Cancel a pending operation (does not stop API call, just clears tracking)
   */
  cancel(id) {
    console.log(`[OPTIMISTIC] Canceling operation: ${id}`);
    this.pendingUpdates.delete(id);
    this.rollbackCallbacks.delete(id);
  }

  /**
   * Clear all pending operations
   */
  clearAll() {
    console.log('[OPTIMISTIC] Clearing all pending operations');
    this.pendingUpdates.clear();
    this.rollbackCallbacks.clear();
    this.operationQueue = [];
    this.processingQueue = false;
  }

  /**
   * Check if an error is retryable
   */
  _isRetryableError(error) {
    // Network errors
    if (error.message?.includes('network') || error.message?.includes('Network')) {
      return true;
    }
    // Rate limiting
    if (error.status === 429) {
      return true;
    }
    // Server errors (5xx)
    if (error.status >= 500 && error.status < 600) {
      return true;
    }
    // Timeout errors
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      return true;
    }
    return false;
  }

  /**
   * Delay helper for retry logic
   */
  _delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Export singleton instance
const optimisticUpdateService = new OptimisticUpdateService();
export default optimisticUpdateService;
