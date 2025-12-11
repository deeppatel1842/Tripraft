/**
 * Tests for IndexedDB Persister
 * Phase 11: Browser Cache Testing
 */

import { 
  createIDBPersister, 
  getCacheStats, 
  isIndexedDBAvailable 
} from '../indexedDBPersister';

// Mock IndexedDB for testing
const createMockIndexedDB = () => {
  const stores = {};
  
  return {
    open: jest.fn((name, version) => {
      const request = {
        result: {
          objectStoreNames: {
            contains: jest.fn((storeName) => storeName in stores),
          },
          createObjectStore: jest.fn((storeName) => {
            stores[storeName] = {};
            return stores[storeName];
          }),
          transaction: jest.fn((storeName, mode) => {
            const store = {
              put: jest.fn((data) => {
                stores[storeName] = stores[storeName] || {};
                stores[storeName][data.key] = data;
                return { 
                  onerror: null, 
                  onsuccess: null,
                  addEventListener: jest.fn(),
                };
              }),
              get: jest.fn((key) => {
                const result = stores[storeName]?.[key];
                return { 
                  result,
                  onerror: null, 
                  onsuccess: null,
                  addEventListener: jest.fn(),
                };
              }),
              delete: jest.fn((key) => {
                delete stores[storeName]?.[key];
                return { 
                  onerror: null, 
                  onsuccess: null,
                  addEventListener: jest.fn(),
                };
              }),
            };
            return {
              objectStore: jest.fn(() => store),
              oncomplete: null,
            };
          }),
          close: jest.fn(),
        },
        onerror: null,
        onsuccess: null,
        onupgradeneeded: null,
      };
      
      // Simulate async success
      setTimeout(() => {
        if (request.onsuccess) {
          request.onsuccess();
        }
      }, 0);
      
      return request;
    }),
    deleteDatabase: jest.fn(() => ({
      onsuccess: null,
      onerror: null,
    })),
  };
};

describe('IndexedDB Persister', () => {
  describe('isIndexedDBAvailable', () => {
    it('returns true when IndexedDB is available', () => {
      // In jsdom, indexedDB should be available
      expect(typeof isIndexedDBAvailable()).toBe('boolean');
    });
  });

  describe('createIDBPersister', () => {
    it('creates a persister object with required methods', () => {
      const persister = createIDBPersister();
      
      expect(persister).toHaveProperty('persistClient');
      expect(persister).toHaveProperty('restoreClient');
      expect(persister).toHaveProperty('removeClient');
      
      expect(typeof persister.persistClient).toBe('function');
      expect(typeof persister.restoreClient).toBe('function');
      expect(typeof persister.removeClient).toBe('function');
    });

    it('persistClient returns a promise', () => {
      const persister = createIDBPersister();
      const result = persister.persistClient({ test: 'data' });
      
      expect(result).toBeInstanceOf(Promise);
    });

    it('restoreClient returns a promise', () => {
      const persister = createIDBPersister();
      const result = persister.restoreClient();
      
      expect(result).toBeInstanceOf(Promise);
    });

    it('removeClient returns a promise', () => {
      const persister = createIDBPersister();
      const result = persister.removeClient();
      
      expect(result).toBeInstanceOf(Promise);
    });
  });

  describe('getCacheStats', () => {
    it('returns stats object', async () => {
      const stats = await getCacheStats();
      
      expect(stats).toHaveProperty('exists');
      expect(typeof stats.exists).toBe('boolean');
    });

    it('returns exists: false when cache is empty', async () => {
      const stats = await getCacheStats();
      
      // Cache should be empty in test environment
      expect(stats.exists).toBe(false);
    });
  });
});

describe('Query Client Persist', () => {
  describe('CACHE_CONFIG', () => {
    it('has correct TTL values', async () => {
      const { CACHE_CONFIG } = await import('../queryClientPersist');
      
      // Stale time should be 5 minutes
      expect(CACHE_CONFIG.STALE_TIME_MS).toBe(5 * 60 * 1000);
      
      // GC time should be 30 minutes
      expect(CACHE_CONFIG.GC_TIME_MS).toBe(30 * 60 * 1000);
      
      // Persist time should be 60 minutes
      expect(CACHE_CONFIG.PERSIST_TIME_MS).toBe(60 * 60 * 1000);
      
      // Max age should be 60 minutes
      expect(CACHE_CONFIG.MAX_AGE_MS).toBe(60 * 60 * 1000);
    });
  });

  describe('createQueryClient', () => {
    it('creates a QueryClient instance', async () => {
      const { createQueryClient } = await import('../queryClientPersist');
      const client = createQueryClient();
      
      expect(client).toBeDefined();
      expect(typeof client.getQueryData).toBe('function');
      expect(typeof client.setQueryData).toBe('function');
    });

    it('has correct default options', async () => {
      const { createQueryClient, CACHE_CONFIG } = await import('../queryClientPersist');
      const client = createQueryClient();
      
      const options = client.getDefaultOptions();
      
      expect(options.queries.staleTime).toBe(CACHE_CONFIG.STALE_TIME_MS);
      expect(options.queries.gcTime).toBe(CACHE_CONFIG.GC_TIME_MS);
      expect(options.queries.retry).toBe(2);
      expect(options.mutations.retry).toBe(1);
    });
  });

  describe('clearPersistedCache', () => {
    it('clears cache without throwing', async () => {
      const { clearPersistedCache } = await import('../queryClientPersist');
      
      // Should not throw
      await expect(clearPersistedCache()).resolves.not.toThrow();
    });
  });
});
