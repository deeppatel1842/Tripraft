/**
 * IndexedDB Persister for React Query
 * Phase 11: Browser Cache Implementation
 * 
 * Provides persistent storage using IndexedDB (50MB+ capacity)
 * Much larger than localStorage (5MB limit)
 */

const DB_NAME = 'TripRaftQueryCache';
const STORE_NAME = 'queryCache';
const DB_VERSION = 1;

/**
 * Open IndexedDB database
 * @returns {Promise<IDBDatabase>}
 */
const openDatabase = () => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onerror = () => {
      reject(new Error('Failed to open IndexedDB'));
    };
    
    request.onsuccess = () => {
      resolve(request.result);
    };
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      // Create object store if it doesn't exist
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'key' });
      }
    };
  });
};

/**
 * Create an IndexedDB persister for React Query
 * Compatible with @tanstack/react-query-persist-client
 * 
 * @returns {Object} Persister object with persistClient and restoreClient methods
 */
export const createIDBPersister = () => {
  return {
    persistClient: async (client) => {
      try {
        const db = await openDatabase();
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        
        // Store the serialized client state
        const data = {
          key: 'reactQueryClient',
          value: JSON.stringify(client),
          timestamp: Date.now(),
        };
        
        return new Promise((resolve, reject) => {
          const request = store.put(data);
          
          request.onerror = () => {
            reject(new Error('Failed to persist to IndexedDB'));
          };
          
          request.onsuccess = () => {
            resolve();
          };
          
          transaction.oncomplete = () => {
            db.close();
          };
        });
      } catch (error) {
        // Silently fail - cache is optional
        if (process.env.NODE_ENV === 'development') {
          // eslint-disable-next-line no-console
          console.warn('[IDBPersister] Failed to persist:', error);
        }
      }
    },
    
    restoreClient: async () => {
      try {
        const db = await openDatabase();
        const transaction = db.transaction(STORE_NAME, 'readonly');
        const store = transaction.objectStore(STORE_NAME);
        
        return new Promise((resolve, reject) => {
          const request = store.get('reactQueryClient');
          
          request.onerror = () => {
            resolve(undefined);
          };
          
          request.onsuccess = () => {
            const result = request.result;
            
            if (result && result.value) {
              try {
                resolve(JSON.parse(result.value));
              } catch {
                resolve(undefined);
              }
            } else {
              resolve(undefined);
            }
          };
          
          transaction.oncomplete = () => {
            db.close();
          };
        });
      } catch (error) {
        // Silently fail - return undefined to use fresh data
        if (process.env.NODE_ENV === 'development') {
          // eslint-disable-next-line no-console
          console.warn('[IDBPersister] Failed to restore:', error);
        }
        return undefined;
      }
    },
    
    removeClient: async () => {
      try {
        const db = await openDatabase();
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        const store = transaction.objectStore(STORE_NAME);
        
        return new Promise((resolve, reject) => {
          const request = store.delete('reactQueryClient');
          
          request.onerror = () => {
            reject(new Error('Failed to remove from IndexedDB'));
          };
          
          request.onsuccess = () => {
            resolve();
          };
          
          transaction.oncomplete = () => {
            db.close();
          };
        });
      } catch (error) {
        // Silently fail
        if (process.env.NODE_ENV === 'development') {
          // eslint-disable-next-line no-console
          console.warn('[IDBPersister] Failed to remove:', error);
        }
      }
    },
  };
};

/**
 * Get cache statistics
 * @returns {Promise<Object>} Cache statistics
 */
export const getCacheStats = async () => {
  try {
    const db = await openDatabase();
    const transaction = db.transaction(STORE_NAME, 'readonly');
    const store = transaction.objectStore(STORE_NAME);
    
    return new Promise((resolve) => {
      const request = store.get('reactQueryClient');
      
      request.onsuccess = () => {
        const result = request.result;
        
        if (result) {
          const dataSize = new Blob([result.value]).size;
          resolve({
            exists: true,
            sizeBytes: dataSize,
            sizeKB: Math.round(dataSize / 1024),
            timestamp: result.timestamp,
            age: Date.now() - result.timestamp,
            ageMinutes: Math.round((Date.now() - result.timestamp) / 60000),
          });
        } else {
          resolve({
            exists: false,
            sizeBytes: 0,
            sizeKB: 0,
            timestamp: null,
            age: null,
            ageMinutes: null,
          });
        }
      };
      
      request.onerror = () => {
        resolve({ exists: false, error: true });
      };
      
      transaction.oncomplete = () => {
        db.close();
      };
    });
  } catch (error) {
    return { exists: false, error: true };
  }
};

/**
 * Check if IndexedDB is available
 * @returns {boolean}
 */
export const isIndexedDBAvailable = () => {
  try {
    return typeof window !== 'undefined' && 
      'indexedDB' in window && 
      window.indexedDB !== null;
  } catch {
    return false;
  }
};
