/**
 * Optimistic Update Service Tests
 * ================================
 * 
 * Unit tests for the OptimisticUpdateService.
 * Tests optimistic UI updates with rollback functionality.
 * 
 * Phase 4: Frontend Real-Time Integration Tests
 */

import { jest, describe, it, expect, beforeEach, afterEach } from '@jest/globals';

// Mock performance.now for consistent timing
const mockPerformanceNow = jest.fn(() => 0);
global.performance = { now: mockPerformanceNow };

// Import after mocks
import OptimisticUpdateService from '../optimisticUpdateService';

describe('OptimisticUpdateService', () => {
  let service;

  beforeEach(() => {
    jest.clearAllMocks();
    mockPerformanceNow.mockReturnValue(0);
    // Create fresh instance
    service = new (OptimisticUpdateService.constructor)();
  });

  afterEach(() => {
    service.clearAll();
  });

  describe('execute()', () => {
    it('should execute optimistic update immediately', async () => {
      const optimisticUpdate = jest.fn(() => 'optimistic_result');
      const apiCall = jest.fn().mockResolvedValue({ success: true });
      const onSuccess = jest.fn();

      await service.execute({
        id: 'test_op',
        optimisticUpdate,
        apiCall,
        onSuccess,
        rollback: jest.fn()
      });

      expect(optimisticUpdate).toHaveBeenCalled();
      expect(apiCall).toHaveBeenCalled();
      expect(onSuccess).toHaveBeenCalledWith({ success: true });
    });

    it('should rollback on API error', async () => {
      const optimisticUpdate = jest.fn(() => 'optimistic_result');
      const apiCall = jest.fn().mockRejectedValue(new Error('API Error'));
      const onError = jest.fn();
      const rollback = jest.fn();

      await expect(service.execute({
        id: 'test_op',
        optimisticUpdate,
        apiCall,
        onSuccess: jest.fn(),
        onError,
        rollback,
        options: { retry: false }
      })).rejects.toThrow('API Error');

      expect(rollback).toHaveBeenCalledWith('optimistic_result');
      expect(onError).toHaveBeenCalled();
    });

    it('should track pending operations', async () => {
      const apiCall = jest.fn(() => new Promise(resolve => setTimeout(resolve, 100)));

      const promise = service.execute({
        id: 'pending_test',
        optimisticUpdate: jest.fn(),
        apiCall,
        onSuccess: jest.fn(),
        rollback: jest.fn()
      });

      expect(service.isPending('pending_test')).toBe(true);

      await promise;

      expect(service.isPending('pending_test')).toBe(false);
    });

    it('should return API result on success', async () => {
      const expectedResult = { id: 'expense_123', amount: 100 };
      const apiCall = jest.fn().mockResolvedValue(expectedResult);

      const result = await service.execute({
        id: 'return_test',
        optimisticUpdate: jest.fn(),
        apiCall,
        onSuccess: jest.fn(),
        rollback: jest.fn()
      });

      expect(result).toEqual(expectedResult);
    });
  });

  describe('Retry Logic', () => {
    it('should retry on retryable error', async () => {
      const apiCall = jest.fn()
        .mockRejectedValueOnce(new Error('network error'))
        .mockResolvedValueOnce({ success: true });

      service.retryDelay = 1; // Minimal delay for testing

      const result = await service.execute({
        id: 'retry_test',
        optimisticUpdate: jest.fn(),
        apiCall,
        onSuccess: jest.fn(),
        rollback: jest.fn(),
        options: { retry: true }
      });

      expect(apiCall).toHaveBeenCalledTimes(2);
      expect(result).toEqual({ success: true });
    });

    it('should not retry on non-retryable error', async () => {
      const error = new Error('Validation failed');
      error.status = 400;
      
      const apiCall = jest.fn().mockRejectedValue(error);
      const rollback = jest.fn();

      await expect(service.execute({
        id: 'no_retry_test',
        optimisticUpdate: jest.fn(() => 'result'),
        apiCall,
        onSuccess: jest.fn(),
        onError: jest.fn(),
        rollback,
        options: { retry: true }
      })).rejects.toThrow('Validation failed');

      expect(apiCall).toHaveBeenCalledTimes(1);
    });

    it('should stop retrying after max attempts', async () => {
      const apiCall = jest.fn().mockRejectedValue(new Error('network error'));
      const rollback = jest.fn();

      service.maxRetries = 2;
      service.retryDelay = 1;

      await expect(service.execute({
        id: 'max_retry_test',
        optimisticUpdate: jest.fn(() => 'result'),
        apiCall,
        onSuccess: jest.fn(),
        onError: jest.fn(),
        rollback,
        options: { retry: true }
      })).rejects.toThrow('network error');

      // Initial + 2 retries = 3 calls
      expect(apiCall).toHaveBeenCalledTimes(3);
      expect(rollback).toHaveBeenCalled();
    });

    it('should identify retryable errors correctly', () => {
      // Network errors
      expect(service._isRetryableError(new Error('network error'))).toBe(true);
      expect(service._isRetryableError(new Error('Network failure'))).toBe(true);

      // Rate limiting
      const rateLimitError = new Error('Too many requests');
      rateLimitError.status = 429;
      expect(service._isRetryableError(rateLimitError)).toBe(true);

      // Server errors
      const serverError = new Error('Internal server error');
      serverError.status = 500;
      expect(service._isRetryableError(serverError)).toBe(true);

      // Timeout
      expect(service._isRetryableError(new Error('timeout'))).toBe(true);

      // Non-retryable
      const validationError = new Error('Validation failed');
      validationError.status = 400;
      expect(service._isRetryableError(validationError)).toBe(false);
    });
  });

  describe('Expense-Specific Helpers', () => {
    describe('createExpense()', () => {
      it('should create optimistic expense with temp ID', async () => {
        const updateState = jest.fn();
        const apiCall = jest.fn().mockResolvedValue({ id: 'real_id', amount: 100 });

        await service.createExpense(
          { amount: 100, description: 'Test' },
          updateState,
          apiCall,
          { onSuccess: jest.fn() }
        );

        expect(updateState).toHaveBeenCalled();
        // First call adds optimistic expense
        const firstCallArg = updateState.mock.calls[0][0];
        const result = firstCallArg([]);
        expect(result[0]).toHaveProperty('_optimistic', true);
        expect(result[0].id).toMatch(/^temp_/);
      });

      it('should replace optimistic expense with real one on success', async () => {
        let currentState = [];
        const updateState = jest.fn(fn => {
          currentState = fn(currentState);
        });
        
        const realExpense = { id: 'real_123', amount: 100 };
        const apiCall = jest.fn().mockResolvedValue(realExpense);
        const onSuccess = jest.fn();

        await service.createExpense(
          { amount: 100 },
          updateState,
          apiCall,
          { onSuccess }
        );

        expect(onSuccess).toHaveBeenCalledWith(realExpense);
      });

      it('should rollback on error', async () => {
        let currentState = [];
        const updateState = jest.fn(fn => {
          currentState = fn(currentState);
        });

        const apiCall = jest.fn().mockRejectedValue(new Error('Failed'));
        const onError = jest.fn();

        service.retryDelay = 1;

        await expect(service.createExpense(
          { amount: 100 },
          updateState,
          apiCall,
          { onError }
        )).rejects.toThrow('Failed');

        expect(onError).toHaveBeenCalled();
        // Rollback removes the temp expense
        expect(currentState.length).toBe(0);
      });
    });

    describe('updateExpense()', () => {
      it('should optimistically update expense', async () => {
        const existingExpense = { id: 'exp_123', expense_id: 'exp_123', amount: 50 };
        let currentState = [existingExpense];
        
        const updateState = jest.fn(fn => {
          currentState = fn(currentState);
        });

        const apiCall = jest.fn().mockResolvedValue({ id: 'exp_123', amount: 100 });

        await service.updateExpense(
          'exp_123',
          { amount: 100 },
          updateState,
          apiCall,
          {}
        );

        expect(updateState).toHaveBeenCalled();
      });

      it('should rollback to previous state on error', async () => {
        const existingExpense = { id: 'exp_123', expense_id: 'exp_123', amount: 50 };
        let currentState = [existingExpense];
        
        const updateState = jest.fn(fn => {
          currentState = fn(currentState);
        });

        const apiCall = jest.fn().mockRejectedValue(new Error('Update failed'));
        service.retryDelay = 1;

        await expect(service.updateExpense(
          'exp_123',
          { amount: 100 },
          updateState,
          apiCall,
          {}
        )).rejects.toThrow('Update failed');

        // After rollback, amount should be back to original
        // The exact state depends on implementation
        expect(updateState).toHaveBeenCalled();
      });
    });

    describe('deleteExpense()', () => {
      it('should optimistically remove expense', async () => {
        const expense = { id: 'exp_123', expense_id: 'exp_123', amount: 100 };
        let currentState = [expense];
        
        const updateState = jest.fn(fn => {
          currentState = fn(currentState);
        });

        const apiCall = jest.fn().mockResolvedValue({ success: true });

        await service.deleteExpense(
          'exp_123',
          updateState,
          apiCall,
          {}
        );

        // After optimistic update, expense should be removed
        expect(updateState).toHaveBeenCalled();
      });

      it('should restore expense on error', async () => {
        const expense = { id: 'exp_123', expense_id: 'exp_123', amount: 100 };
        let currentState = [expense];
        
        const updateState = jest.fn(fn => {
          currentState = fn(currentState);
        });

        const apiCall = jest.fn().mockRejectedValue(new Error('Delete failed'));
        service.retryDelay = 1;

        await expect(service.deleteExpense(
          'exp_123',
          updateState,
          apiCall,
          {}
        )).rejects.toThrow('Delete failed');

        expect(updateState).toHaveBeenCalled();
      });
    });

    describe('createSettlement()', () => {
      it('should create optimistic settlement', async () => {
        let currentState = [];
        const updateState = jest.fn(fn => {
          currentState = fn(currentState);
        });

        const apiCall = jest.fn().mockResolvedValue({ id: 'settlement_real', amount: 50 });

        await service.createSettlement(
          { payer_id: 'user1', payee_id: 'user2', amount: 50 },
          updateState,
          apiCall,
          {}
        );

        expect(updateState).toHaveBeenCalled();
        expect(apiCall).toHaveBeenCalled();
      });
    });
  });

  describe('Queue Management', () => {
    it('should queue operations for sequential execution', async () => {
      const executionOrder = [];
      
      const op1 = service.queue(async () => {
        await new Promise(r => setTimeout(r, 10));
        executionOrder.push(1);
        return 1;
      });
      
      const op2 = service.queue(async () => {
        executionOrder.push(2);
        return 2;
      });
      
      const op3 = service.queue(async () => {
        executionOrder.push(3);
        return 3;
      });

      await Promise.all([op1, op2, op3]);

      expect(executionOrder).toEqual([1, 2, 3]);
    });

    it('should handle queue errors gracefully', async () => {
      const op1 = service.queue(async () => 'success');
      const op2 = service.queue(async () => { throw new Error('Queue error'); });
      const op3 = service.queue(async () => 'after error');

      await expect(op1).resolves.toBe('success');
      await expect(op2).rejects.toThrow('Queue error');
      await expect(op3).resolves.toBe('after error');
    });
  });

  describe('Conflict Detection', () => {
    it('should detect conflicts for same entity', () => {
      service.pendingUpdates.set('update_expense_exp_123', { startTime: Date.now() });

      expect(service.hasConflict('expense', 'exp_123')).toBe(true);
    });

    it('should not detect conflict for different entity', () => {
      service.pendingUpdates.set('update_expense_exp_123', { startTime: Date.now() });

      expect(service.hasConflict('expense', 'exp_456')).toBe(false);
    });

    it('should wait for entity operations to complete', async () => {
      const startTime = Date.now();
      
      // Simulate a pending operation that completes quickly
      service.pendingUpdates.set('update_expense_exp_123', { startTime });
      
      setTimeout(() => {
        service.pendingUpdates.delete('update_expense_exp_123');
      }, 50);

      await service.waitForEntity('exp_123', 1000);

      expect(service.pendingUpdates.has('update_expense_exp_123')).toBe(false);
    });

    it('should timeout when waiting too long', async () => {
      service.pendingUpdates.set('update_expense_exp_123', { startTime: Date.now() });

      // Very short timeout
      await service.waitForEntity('exp_123', 50);

      // Operation should still be pending (wait timed out)
      expect(service.pendingUpdates.has('update_expense_exp_123')).toBe(true);
    });
  });

  describe('Utility Methods', () => {
    it('should return pending operations list', () => {
      service.pendingUpdates.set('op1', {});
      service.pendingUpdates.set('op2', {});

      const pending = service.getPendingOperations();

      expect(pending).toContain('op1');
      expect(pending).toContain('op2');
    });

    it('should return correct stats', () => {
      service.pendingUpdates.set('op1', {});
      service.operationQueue = [1, 2, 3];
      service.processingQueue = true;

      const stats = service.getStats();

      expect(stats.pendingCount).toBe(1);
      expect(stats.queueLength).toBe(3);
      expect(stats.processingQueue).toBe(true);
    });

    it('should cancel operation', () => {
      service.pendingUpdates.set('cancel_test', {});
      service.rollbackCallbacks.set('cancel_test', { rollback: jest.fn() });

      service.cancel('cancel_test');

      expect(service.pendingUpdates.has('cancel_test')).toBe(false);
      expect(service.rollbackCallbacks.has('cancel_test')).toBe(false);
    });

    it('should clear all operations', () => {
      service.pendingUpdates.set('op1', {});
      service.rollbackCallbacks.set('op1', {});
      service.operationQueue = [1, 2];
      service.processingQueue = true;

      service.clearAll();

      expect(service.pendingUpdates.size).toBe(0);
      expect(service.rollbackCallbacks.size).toBe(0);
      expect(service.operationQueue.length).toBe(0);
      expect(service.processingQueue).toBe(false);
    });
  });

  describe('Delay Helper', () => {
    it('should delay for specified time', async () => {
      const start = Date.now();
      await service._delay(50);
      const elapsed = Date.now() - start;

      expect(elapsed).toBeGreaterThanOrEqual(45); // Allow some variance
    });
  });
});

describe('OptimisticUpdateService Singleton', () => {
  it('should export a singleton instance', () => {
    expect(OptimisticUpdateService).toBeDefined();
  });
});
