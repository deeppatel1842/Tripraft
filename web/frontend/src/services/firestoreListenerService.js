/**
 * Firestore Real-Time Listener Service
 * 
 * Provides real-time updates for Group Planner using Firestore client SDK.
 * 
 * Benefits:
 * - Zero API calls - Direct Firestore connection
 * - Instant updates - ~50-100ms latency
 * - Free reads - Snapshot listeners don't count
 * - Auto reconnection - Built into Firebase SDK
 * - Offline support - Works with Firebase cache
 * 
 * Architecture:
 * - Listens to travel_groups/{groupId} for group changes
 * - Listens to group_members collection for membership changes
 * - Automatically updates React state via callbacks
 */

import { getFirestore, doc, collection, onSnapshot, query, where } from 'firebase/firestore';
import { getAuth } from 'firebase/auth';
import { app } from '../firebase/authService';

class FirestoreListenerService {
  constructor() {
    this.db = null;
    this.auth = null;
    this.listeners = new Map(); // Track active listeners for cleanup
    this.initialized = false;
  }

  /**
   * Initialize Firestore connection
   */
  initialize() {
    if (this.initialized) {
      console.log('ℹ️ [FIRESTORE] Already initialized');
      return;
    }

    try {
      this.auth = getAuth(app);
      this.db = getFirestore(app);
      this.initialized = true;
      
      const currentUser = this.auth.currentUser;
      console.log('✅ [FIRESTORE] Listener service initialized');
      console.log('📡 [FIRESTORE] Direct connection to Firestore established (authenticated)');
      console.log('👤 [FIRESTORE] Current user:', currentUser ? {
        uid: currentUser.uid,
        email: currentUser.email,
        emailVerified: currentUser.emailVerified
      } : 'NOT AUTHENTICATED');
      
      if (!currentUser) {
        console.warn('⚠️ [FIRESTORE] WARNING: No user authenticated! Listeners may fail.');
      }
    } catch (error) {
      console.error('❌ [FIRESTORE] Initialization failed:', error);
      throw error;
    }
  }

  /**
   * Listen to user's groups list in real-time
   * 
   * @param {string} userId - Current user ID
   * @param {function} onUpdate - Callback when groups change
   * @param {function} onError - Error callback
   * @returns {function} Unsubscribe function
   */
  listenToUserGroups(userId, onUpdate, onError) {
    if (!this.initialized) this.initialize();

    const listenerKey = `user_groups_${userId}`;
    
    // Clean up existing listener if any
    if (this.listeners.has(listenerKey)) {
      console.log('🔄 [FIRESTORE] Replacing existing user groups listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [FIRESTORE] Setting up listener for user groups:', userId);

    try {
      // Query for groups where user is a member
      const membersRef = collection(this.db, 'group_members');
      const q = query(membersRef, where('user_id', '==', userId));

      const unsubscribe = onSnapshot(
        q,
        async (snapshot) => {
          console.log('🔔 [FIRESTORE] User groups snapshot received');
          console.log('📊 [FIRESTORE] Members found:', snapshot.size);

          // Get all group IDs where user is a member
          const groupIds = [];
          snapshot.forEach(doc => {
            const data = doc.data();
            if (data.group_id) {
              groupIds.push(data.group_id);
            }
          });

          console.log('📋 [FIRESTORE] User is member of groups:', groupIds);

          // Now fetch the actual group documents
          if (groupIds.length > 0) {
            // Set up listeners for each group
            const groupsData = {};
            const groupListeners = [];

            for (const groupId of groupIds) {
              const groupRef = doc(this.db, 'travel_groups', groupId);
              
              const groupUnsubscribe = onSnapshot(
                groupRef,
                (groupDoc) => {
                  if (groupDoc.exists()) {
                    const data = groupDoc.data();
                    groupsData[groupId] = {
                      ...data,
                      id: groupDoc.id,
                      group_id: groupDoc.id, // Backend expects group_id
                    };
                    
                    // Call update callback with current groups data
                    onUpdate(groupsData);
                    console.log('✅ [FIRESTORE] Group updated:', groupId);
                  }
                },
                (error) => {
                  console.error('❌ [FIRESTORE] Group listener error:', error);
                  if (onError) onError(error);
                }
              );

              groupListeners.push(groupUnsubscribe);
            }

            // Store composite unsubscribe function
            const compositeUnsubscribe = () => {
              groupListeners.forEach(unsub => unsub());
              unsubscribe();
            };

            this.listeners.set(listenerKey, compositeUnsubscribe);
            return compositeUnsubscribe;

          } else {
            // No groups - user is not a member of any groups
            console.log('ℹ️ [FIRESTORE] User is not a member of any groups');
            onUpdate({});
          }
        },
        (error) => {
          console.error('❌ [FIRESTORE] User groups listener error:', error);
          if (onError) onError(error);
        }
      );

      this.listeners.set(listenerKey, unsubscribe);
      return unsubscribe;

    } catch (error) {
      console.error('❌ [FIRESTORE] Failed to set up user groups listener:', error);
      if (onError) onError(error);
      return () => {}; // Return no-op unsubscribe
    }
  }

  /**
   * Listen to a specific group in real-time
   * 
   * @param {string} groupId - Group ID to listen to
   * @param {function} onUpdate - Callback when group changes
   * @param {function} onError - Error callback
   * @returns {function} Unsubscribe function
   */
  listenToGroup(groupId, onUpdate, onError) {
    if (!this.initialized) this.initialize();

    const listenerKey = `group_${groupId}`;
    
    // Clean up existing listener if any
    if (this.listeners.has(listenerKey)) {
      console.log('🔄 [FIRESTORE] Replacing existing group listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [FIRESTORE] Setting up listener for group:', groupId);

    try {
      const groupRef = doc(this.db, 'travel_groups', groupId);

      const unsubscribe = onSnapshot(
        groupRef,
        (snapshot) => {
          if (snapshot.exists()) {
            console.log('🔔 [FIRESTORE] Group snapshot received:', groupId);
            const data = snapshot.data();
            const groupData = {
              ...data,
              id: snapshot.id,
              group_id: snapshot.id,
            };
            onUpdate(groupData);
            console.log('✅ [FIRESTORE] Group data updated:', {
              places: data.places?.length || 0,
              polls: data.polls?.length || 0,
              checklist: data.checklist?.length || 0,
              members: data.members?.length || 0,
            });
          } else {
            console.log('⚠️ [FIRESTORE] Group not found:', groupId);
            if (onError) onError(new Error('Group not found'));
          }
        },
        (error) => {
          console.error('❌ [FIRESTORE] Group listener error:', error);
          if (onError) onError(error);
        }
      );

      this.listeners.set(listenerKey, unsubscribe);
      return unsubscribe;

    } catch (error) {
      console.error('❌ [FIRESTORE] Failed to set up group listener:', error);
      if (onError) onError(error);
      return () => {}; // Return no-op unsubscribe
    }
  }

  /**
   * Stop listening to user groups
   */
  stopListeningToUserGroups(userId) {
    const listenerKey = `user_groups_${userId}`;
    if (this.listeners.has(listenerKey)) {
      console.log('🔥 [FIRESTORE] Stopping user groups listener:', userId);
      this.listeners.get(listenerKey)();
      this.listeners.delete(listenerKey);
    }
  }

  /**
   * Stop listening to a specific group
   */
  stopListeningToGroup(groupId) {
    const listenerKey = `group_${groupId}`;
    if (this.listeners.has(listenerKey)) {
      console.log('🔥 [FIRESTORE] Stopping group listener:', groupId);
      this.listeners.get(listenerKey)();
      this.listeners.delete(listenerKey);
    }
  }

  /**
   * Clean up all active listeners
   */
  cleanup() {
    console.log('🧹 [FIRESTORE] Cleaning up all listeners');
    console.log('📊 [FIRESTORE] Active listeners:', this.listeners.size);
    
    this.listeners.forEach((unsubscribe, key) => {
      console.log('🔥 [FIRESTORE] Stopping listener:', key);
      unsubscribe();
    });
    
    this.listeners.clear();
    console.log('✅ [FIRESTORE] All listeners stopped');
  }

  /**
   * Get number of active listeners
   */
  getActiveListenerCount() {
    return this.listeners.size;
  }

  /**
   * Check if a listener is active
   */
  isListening(key) {
    return this.listeners.has(key);
  }
}

// Export singleton instance
const firestoreListenerService = new FirestoreListenerService();
export default firestoreListenerService;
