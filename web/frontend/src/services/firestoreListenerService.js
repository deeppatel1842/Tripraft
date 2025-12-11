/**
 * Expense Group Firestore Listener Service (Legacy)
 * 
 * NOTE: This is a simplified listener for the GroupPlannerContext to display
 * expense groups. For full expense management features, use expenseFirestoreListener.js
 * 
 * Collections:
 * - expense_groups (Expense Management - NOT Group Planner's travel_groups)
 * - expense_group_members (Expense Management memberships)
 * 
 * Group Planner (travel_groups, travel_places, travel_polls) uses API calls,
 * not Firestore listeners.
 * 
 * Benefits:
 * - Zero API calls - Direct Firestore connection
 * - Instant updates - ~50-100ms latency
 * - Free reads - Snapshot listeners don't count
 * - Auto reconnection - Built into Firebase SDK
 * - Offline support - Works with Firebase cache
 */

import { getFirestore, doc, collection, onSnapshot, query, where } from 'firebase/firestore';
import { getAuth } from 'firebase/auth';
import { app } from '../firebase/authService';

class ExpenseGroupListenerService {
  constructor() {
    this.db = null;
    this.auth = null;
    this.listeners = new Map(); // Track active listeners for cleanup
    this.deletedGroups = new Set(); // Track groups being deleted to suppress permission errors
    this.initialized = false;
  }

  /**
   * Initialize Firestore connection
   */
  initialize() {
    if (this.initialized) {
      console.log('ℹ️ [EXPENSE-GROUP-LISTENER] Already initialized');
      return;
    }

    try {
      this.auth = getAuth(app);
      this.db = getFirestore(app);
      this.initialized = true;
      
      const currentUser = this.auth.currentUser;
      console.log('✅ [EXPENSE-GROUP-LISTENER] Listener service initialized');
      console.log('📡 [EXPENSE-GROUP-LISTENER] Direct connection to Firestore established');
      console.log('👤 [EXPENSE-GROUP-LISTENER] Current user:', currentUser ? {
        uid: currentUser.uid,
        email: currentUser.email,
        emailVerified: currentUser.emailVerified
      } : 'NOT AUTHENTICATED');
      
      if (!currentUser) {
        console.warn('⚠️ [EXPENSE-GROUP-LISTENER] WARNING: No user authenticated! Listeners may fail.');
      }
    } catch (error) {
      console.error('❌ [EXPENSE-GROUP-LISTENER] Initialization failed:', error);
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
      console.log('🔄 [EXPENSE-GROUP-LISTENER] Replacing existing user groups listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [EXPENSE-GROUP-LISTENER] Setting up listener for user groups:', userId);

    try {
      // Query for groups where user is a member
      const membersRef = collection(this.db, 'expense_group_members');
      const q = query(membersRef, where('user_id', '==', userId));

      const unsubscribe = onSnapshot(
        q,
        async (snapshot) => {
          console.log('🔔 [EXPENSE-GROUP-LISTENER] User groups snapshot received');
          console.log('📊 [EXPENSE-GROUP-LISTENER] Members found:', snapshot.size);

          // Get all group IDs where user is an active member
          const groupIds = [];
          snapshot.forEach(doc => {
            const data = doc.data();
            // Only include active members
            if (data.group_id && data.is_active !== false) {
              groupIds.push(data.group_id);
            }
          });

          console.log('📋 [EXPENSE-GROUP-LISTENER] User is member of groups:', groupIds);

          // Now fetch the actual group documents
          if (groupIds.length > 0) {
            // Set up listeners for each group
            const groupsData = {};
            const groupListeners = [];

            for (const groupId of groupIds) {
              const groupRef = doc(this.db, 'expense_groups', groupId);
              
              const groupUnsubscribe = onSnapshot(
                groupRef,
                (groupDoc) => {
                  if (groupDoc.exists()) {
                    const data = groupDoc.data();
                    
                    // Skip inactive (deleted) groups
                    if (data.is_active === false) {
                      // Remove from groupsData if it was previously there
                      if (groupsData[groupId]) {
                        delete groupsData[groupId];
                        onUpdate({...groupsData});
                        console.log('🗑️ [EXPENSE-GROUP-LISTENER] Group removed (deleted):', groupId);
                      }
                      return;
                    }
                    
                    groupsData[groupId] = {
                      ...data,
                      id: groupDoc.id,
                      group_id: groupDoc.id, // Backend expects group_id
                    };
                    
                    // Call update callback with current groups data
                    onUpdate(groupsData);
                    console.log('✅ [EXPENSE-GROUP-LISTENER] Group updated:', groupId);
                  }
                },
                (error) => {
                  console.error('❌ [EXPENSE-GROUP-LISTENER] Group listener error:', error);
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
            console.log('ℹ️ [EXPENSE-GROUP-LISTENER] User is not a member of any groups');
            onUpdate({});
          }
        },
        (error) => {
          console.error('❌ [EXPENSE-GROUP-LISTENER] User groups listener error:', error);
          if (onError) onError(error);
        }
      );

      this.listeners.set(listenerKey, unsubscribe);
      return unsubscribe;

    } catch (error) {
      console.error('❌ [EXPENSE-GROUP-LISTENER] Failed to set up user groups listener:', error);
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
      console.log('🔄 [EXPENSE-GROUP-LISTENER] Replacing existing group listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [EXPENSE-GROUP-LISTENER] Setting up listener for group:', groupId);

    try {
      const groupRef = doc(this.db, 'expense_groups', groupId);

      const unsubscribe = onSnapshot(
        groupRef,
        (snapshot) => {
          if (snapshot.exists()) {
            console.log('🔔 [EXPENSE-GROUP-LISTENER] Group snapshot received:', groupId);
            const data = snapshot.data();
            const groupData = {
              ...data,
              id: snapshot.id,
              group_id: snapshot.id,
            };
            onUpdate(groupData);
            console.log('✅ [EXPENSE-GROUP-LISTENER] Group data updated:', {
              places: data.places?.length || 0,
              polls: data.polls?.length || 0,
              checklist: data.checklist?.length || 0,
              members: data.members?.length || 0,
            });
          } else {
            console.log('⚠️ [EXPENSE-GROUP-LISTENER] Group not found:', groupId);
            if (onError) onError(new Error('Group not found'));
          }
        },
        (error) => {
          // Silently ignore permission errors for groups being deleted
          if (error.code === 'permission-denied' && this.deletedGroups.has(groupId)) {
            console.log(`ℹ️ [EXPENSE-GROUP-LISTENER] Ignoring permission error for deleted group ${groupId}`);
            return;
          }
          console.error('❌ [EXPENSE-GROUP-LISTENER] Group listener error:', error);
          if (onError) onError(error);
        }
      );

      this.listeners.set(listenerKey, unsubscribe);
      return unsubscribe;

    } catch (error) {
      console.error('❌ [EXPENSE-GROUP-LISTENER] Failed to set up group listener:', error);
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
      console.log('🔥 [EXPENSE-GROUP-LISTENER] Stopping user groups listener:', userId);
      this.listeners.get(listenerKey)();
      this.listeners.delete(listenerKey);
    }
  }

  /**
   * Stop listening to a specific group
   * @param {string} groupId - Group ID to stop listening to
   * @param {boolean} isDeleting - Whether the group is being deleted (suppresses future permission errors)
   */
  stopListeningToGroup(groupId, isDeleting = false) {
    const listenerKey = `group_${groupId}`;
    
    // Track that this group is being deleted to suppress future permission errors
    if (isDeleting) {
      this.deletedGroups.add(groupId);
      console.log('🔥 [EXPENSE-GROUP-LISTENER] Marked group as deleted to suppress permission errors:', groupId);
      
      // Clean up deletedGroups after 30 seconds to prevent memory leak
      setTimeout(() => {
        this.deletedGroups.delete(groupId);
      }, 30000);
    }
    
    if (this.listeners.has(listenerKey)) {
      console.log('🔥 [EXPENSE-GROUP-LISTENER] Stopping group listener:', groupId);
      this.listeners.get(listenerKey)();
      this.listeners.delete(listenerKey);
    }
  }
  
  /**
   * Check if a group is being deleted (used to suppress permission errors)
   */
  isGroupDeleted(groupId) {
    return this.deletedGroups.has(groupId);
  }

  /**
   * Clean up all active listeners
   */
  cleanup() {
    console.log('🧹 [EXPENSE-GROUP-LISTENER] Cleaning up all listeners');
    console.log('📊 [EXPENSE-GROUP-LISTENER] Active listeners:', this.listeners.size);
    
    this.listeners.forEach((unsubscribe, key) => {
      console.log('🔥 [EXPENSE-GROUP-LISTENER] Stopping listener:', key);
      unsubscribe();
    });
    
    this.listeners.clear();
    console.log('✅ [EXPENSE-GROUP-LISTENER] All listeners stopped');
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

// Export singleton instance (kept as firestoreListenerService for backward compatibility)
const firestoreListenerService = new ExpenseGroupListenerService();
export default firestoreListenerService;
