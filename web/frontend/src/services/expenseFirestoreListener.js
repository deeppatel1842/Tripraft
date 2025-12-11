/**
 * Firestore Real-Time Listener Service for Expense Manager
 * 
 * Phase 4: Enhanced with expense, balance, and settlement listeners
 * 
 * Provides real-time updates for Expense Manager using Firestore client SDK.
 * Separate from Group Planner listeners to avoid collection conflicts.
 * 
 * Benefits:
 * - Zero API calls - Direct Firestore connection
 * - Instant updates - ~50-100ms latency
 * - Free reads - Snapshot listeners don't count towards quota
 * - Auto reconnection - Built into Firebase SDK
 * - Offline support - Works with Firebase cache
 * 
 * Collections Monitored:
 * - expense_groups - Group documents
 * - expense_group_members - Membership changes
 * - expense_expenses - Expense transactions
 * - expense_group_balances - Balance updates
 * - expense_settlements - Settlement records
 * - expense_invitations - Invitation updates
 */

import { 
  getFirestore, 
  doc, 
  collection, 
  onSnapshot, 
  query, 
  where, 
  orderBy, 
  limit,
  Timestamp 
} from 'firebase/firestore';
import { getAuth } from 'firebase/auth';
import { app } from '../firebase/authService';

class ExpenseFirestoreListener {
  constructor() {
    this.db = null;
    this.auth = null;
    this.listeners = new Map(); // Track active listeners for cleanup
    this.deletedGroups = new Set(); // Track groups being deleted to suppress permission errors
    this.initialized = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second
  }

  /**
   * Initialize Firestore connection
   */
  initialize() {
    if (this.initialized) {
      console.log('ℹ️ [EXPENSE-FIRESTORE] Already initialized');
      return;
    }

    try {
      this.auth = getAuth(app);
      this.db = getFirestore(app);
      this.initialized = true;
      
      const currentUser = this.auth.currentUser;
      console.log('✅ [EXPENSE-FIRESTORE] Listener service initialized');
      console.log('📡 [EXPENSE-FIRESTORE] Direct connection to Firestore established');
      console.log('👤 [EXPENSE-FIRESTORE] Current user:', currentUser ? {
        uid: currentUser.uid,
        email: currentUser.email
      } : 'NOT AUTHENTICATED');
      
      if (!currentUser) {
        console.warn('⚠️ [EXPENSE-FIRESTORE] WARNING: No user authenticated! Listeners may fail.');
      }
    } catch (error) {
      console.error('❌ [EXPENSE-FIRESTORE] Initialization failed:', error);
      throw error;
    }
  }

  /**
   * Handle listener errors with exponential backoff reconnection
   */
  _handleListenerError(error, listenerKey, reconnectFn) {
    // Extract groupId from listenerKey to check if group was deleted
    const groupIdMatch = listenerKey.match(/_([a-zA-Z0-9]+)$/);
    const groupId = groupIdMatch ? groupIdMatch[1] : null;
    
    // Silently ignore permission errors for deleted groups
    if (error.code === 'permission-denied' && groupId && this.deletedGroups.has(groupId)) {
      console.log(`ℹ️ [EXPENSE-FIRESTORE] Ignoring permission error for deleted group ${groupId}`);
      return;
    }
    
    console.error(`❌ [EXPENSE-FIRESTORE] Listener error for ${listenerKey}:`, error);
    
    // Check if it's a permission error (shouldn't reconnect)
    if (error.code === 'permission-denied') {
      console.warn('🔒 [EXPENSE-FIRESTORE] Permission denied - group may have been deleted or user removed');
      return;
    }
    
    // Exponential backoff reconnection
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      console.log(`🔄 [EXPENSE-FIRESTORE] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      
      setTimeout(() => {
        if (reconnectFn) {
          reconnectFn();
        }
      }, delay);
    } else {
      console.error('❌ [EXPENSE-FIRESTORE] Max reconnection attempts reached');
    }
  }

  /**
   * Reset reconnection state on successful connection
   */
  _resetReconnectState() {
    this.reconnectAttempts = 0;
    this.reconnectDelay = 1000;
  }

  /**
   * Listen to user's expense groups list in real-time
   * 
   * @param {string} userId - Current user ID
   * @param {function} onUpdate - Callback when groups change
   * @param {function} onError - Error callback
   * @returns {function} Unsubscribe function
   */
  listenToUserExpenseGroups(userId, onUpdate, onError) {
    if (!this.initialized) this.initialize();

    const listenerKey = `expense_user_groups_${userId}`;
    
    // Clean up existing listener if any
    if (this.listeners.has(listenerKey)) {
      console.log('🔄 [EXPENSE-FIRESTORE] Replacing existing user groups listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [EXPENSE-FIRESTORE] Setting up listener for user expense groups:', userId);

    try {
      // Query for groups where user is a member (using expense_group_members collection)
      const membersRef = collection(this.db, 'expense_group_members');
      const q = query(
        membersRef, 
        where('user_id', '==', userId),
        where('is_active', '==', true)
      );

      const unsubscribe = onSnapshot(
        q,
        async (snapshot) => {
          console.log('🔔 [EXPENSE-FIRESTORE] User expense groups snapshot received');
          console.log('📊 [EXPENSE-FIRESTORE] Memberships found:', snapshot.size);

          // Get all group IDs where user is a member
          const groupIds = [];
          snapshot.forEach(doc => {
            const data = doc.data();
            if (data.group_id) {
              groupIds.push(data.group_id);
              console.log('   - Member of group:', data.group_id, `(role: ${data.role || 'member'})`);
            }
          });

          console.log('📋 [EXPENSE-FIRESTORE] User is member of', groupIds.length, 'expense groups');

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
                    groupsData[groupId] = {
                      ...data,
                      id: groupDoc.id,
                      group_id: groupDoc.id,
                    };
                    
                    // Call update callback with current groups data
                    onUpdate(groupsData);
                    console.log('✅ [EXPENSE-FIRESTORE] Expense group updated:', groupId, '-', data.name);
                  } else {
                    console.warn('⚠️ [EXPENSE-FIRESTORE] Group document not found:', groupId);
                    // Remove from groupsData if it was deleted
                    delete groupsData[groupId];
                    onUpdate(groupsData);
                  }
                },
                (error) => {
                  console.error('❌ [EXPENSE-FIRESTORE] Group listener error:', error);
                  if (onError) onError(error);
                }
              );

              groupListeners.push(groupUnsubscribe);
            }

            // Store composite unsubscribe function
            const compositeUnsubscribe = () => {
              console.log('🛑 [EXPENSE-FIRESTORE] Unsubscribing from', groupListeners.length, 'group listeners');
              groupListeners.forEach(unsub => unsub());
              unsubscribe();
            };

            this.listeners.set(listenerKey, compositeUnsubscribe);
            return compositeUnsubscribe;

          } else {
            // No groups - user is not a member of any groups
            console.log('ℹ️ [EXPENSE-FIRESTORE] User is not a member of any expense groups');
            onUpdate({});
            
            this.listeners.set(listenerKey, unsubscribe);
            return unsubscribe;
          }
        },
        (error) => {
          console.error('❌ [EXPENSE-FIRESTORE] Listener error:', error);
          if (onError) onError(error);
        }
      );

      return unsubscribe;

    } catch (error) {
      console.error('❌ [EXPENSE-FIRESTORE] Failed to set up listener:', error);
      if (onError) onError(error);
      return () => {}; // Return no-op unsubscribe
    }
  }

  /**
   * Listen to a specific expense group's details in real-time
   * 
   * @param {string} groupId - Group ID to listen to
   * @param {function} onUpdate - Callback when group changes
   * @param {function} onError - Error callback
   * @returns {function} Unsubscribe function
   */
  listenToExpenseGroup(groupId, onUpdate, onError) {
    if (!this.initialized) this.initialize();

    const listenerKey = `expense_group_${groupId}`;
    
    // Clean up existing listener if any
    if (this.listeners.has(listenerKey)) {
      console.log('🔄 [EXPENSE-FIRESTORE] Replacing existing group detail listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [EXPENSE-FIRESTORE] Setting up listener for expense group:', groupId);

    try {
      const groupRef = doc(this.db, 'expense_groups', groupId);

      const unsubscribe = onSnapshot(
        groupRef,
        (docSnapshot) => {
          if (docSnapshot.exists()) {
            const data = docSnapshot.data();
            console.log('🔔 [EXPENSE-FIRESTORE] Expense group updated:', groupId, '-', data.name);
            console.log('   Members:', data.members?.length || 0);
            console.log('   Expenses:', data.expense_count || 0);
            
            onUpdate({
              ...data,
              id: docSnapshot.id,
              group_id: docSnapshot.id,
            });
          } else {
            console.warn('⚠️ [EXPENSE-FIRESTORE] Group not found:', groupId);
            onUpdate(null);
          }
        },
        (error) => {
          console.error('❌ [EXPENSE-FIRESTORE] Group listener error:', error);
          if (onError) onError(error);
        }
      );

      this.listeners.set(listenerKey, unsubscribe);
      return unsubscribe;

    } catch (error) {
      console.error('❌ [EXPENSE-FIRESTORE] Failed to set up group listener:', error);
      if (onError) onError(error);
      return () => {};
    }
  }

  /**
   * Listen to group members changes in real-time
   * 
   * @param {string} groupId - Group ID
   * @param {function} onUpdate - Callback with array of members
   * @param {function} onError - Error callback
   * @returns {function} Unsubscribe function
   */
  listenToGroupMembers(groupId, onUpdate, onError) {
    if (!this.initialized) this.initialize();

    const listenerKey = `expense_group_members_${groupId}`;
    
    if (this.listeners.has(listenerKey)) {
      console.log('🔄 [EXPENSE-FIRESTORE] Replacing existing members listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [EXPENSE-FIRESTORE] Setting up listener for group members:', groupId);

    try {
      const membersRef = collection(this.db, 'expense_group_members');
      const q = query(
        membersRef,
        where('group_id', '==', groupId),
        where('is_active', '==', true)
      );

      const unsubscribe = onSnapshot(
        q,
        (snapshot) => {
          console.log('🔔 [EXPENSE-FIRESTORE] Group members snapshot received');
          console.log('📊 [EXPENSE-FIRESTORE] Active members:', snapshot.size);

          const members = [];
          snapshot.forEach(doc => {
            const data = doc.data();
            members.push({
              ...data,
              id: doc.id,
            });
          });

          console.log('✅ [EXPENSE-FIRESTORE] Members updated:', members.map(m => m.user_id));
          this._resetReconnectState();
          onUpdate(members);
        },
        (error) => {
          console.error('❌ [EXPENSE-FIRESTORE] Members listener error:', error);
          if (onError) onError(error);
        }
      );

      this.listeners.set(listenerKey, unsubscribe);
      return unsubscribe;

    } catch (error) {
      console.error('❌ [EXPENSE-FIRESTORE] Failed to set up members listener:', error);
      if (onError) onError(error);
      return () => {};
    }
  }

  // ===========================================================================
  // PHASE 4: NEW LISTENERS FOR EXPENSES, BALANCES, SETTLEMENTS
  // ===========================================================================

  /**
   * Listen to group expenses in real-time
   * 
   * @param {string} groupId - Group ID
   * @param {function} onUpdate - Callback with array of expenses
   * @param {function} onError - Error callback
   * @param {number} pageSize - Number of expenses to fetch (default 50)
   * @returns {function} Unsubscribe function
   */
  listenToGroupExpenses(groupId, onUpdate, onError, pageSize = 50) {
    if (!this.initialized) this.initialize();

    const listenerKey = `expense_expenses_${groupId}`;
    
    if (this.listeners.has(listenerKey)) {
      console.log('🔄 [EXPENSE-FIRESTORE] Replacing existing expenses listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [EXPENSE-FIRESTORE] Setting up listener for group expenses:', groupId);

    try {
      const expensesRef = collection(this.db, 'expense_expenses');
      const q = query(
        expensesRef,
        where('group_id', '==', groupId),
        where('is_deleted', '==', false),
        orderBy('expense_date', 'desc'),
        limit(pageSize)
      );

      const unsubscribe = onSnapshot(
        q,
        (snapshot) => {
          console.log('🔔 [EXPENSE-FIRESTORE] Expenses snapshot received');
          console.log('📊 [EXPENSE-FIRESTORE] Expenses count:', snapshot.size);

          const expenses = [];
          snapshot.forEach(doc => {
            const data = doc.data();
            expenses.push({
              ...data,
              id: doc.id,
              expense_id: doc.id,
              // Convert Firestore timestamps to JS dates
              expense_date: data.expense_date?.toDate?.() || data.expense_date,
              created_at: data.created_at?.toDate?.() || data.created_at,
              updated_at: data.updated_at?.toDate?.() || data.updated_at,
            });
          });

          console.log('✅ [EXPENSE-FIRESTORE] Expenses updated for group:', groupId);
          this._resetReconnectState();
          onUpdate(expenses);
        },
        (error) => {
          this._handleListenerError(error, listenerKey, () => {
            this.listenToGroupExpenses(groupId, onUpdate, onError, pageSize);
          });
          if (onError) onError(error);
        }
      );

      this.listeners.set(listenerKey, unsubscribe);
      return unsubscribe;

    } catch (error) {
      console.error('❌ [EXPENSE-FIRESTORE] Failed to set up expenses listener:', error);
      if (onError) onError(error);
      return () => {};
    }
  }

  /**
   * Listen to group balances in real-time
   * 
   * @param {string} groupId - Group ID (also the balance document ID)
   * @param {function} onUpdate - Callback with balance data
   * @param {function} onError - Error callback
   * @returns {function} Unsubscribe function
   */
  listenToGroupBalances(groupId, onUpdate, onError) {
    if (!this.initialized) this.initialize();

    const listenerKey = `expense_balances_${groupId}`;
    
    if (this.listeners.has(listenerKey)) {
      console.log('🔄 [EXPENSE-FIRESTORE] Replacing existing balances listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [EXPENSE-FIRESTORE] Setting up listener for group balances:', groupId);

    try {
      // Balance document ID is the same as group ID
      const balanceRef = doc(this.db, 'expense_group_balances', groupId);

      const unsubscribe = onSnapshot(
        balanceRef,
        (docSnapshot) => {
          if (docSnapshot.exists()) {
            const data = docSnapshot.data();
            console.log('🔔 [EXPENSE-FIRESTORE] Balances updated for group:', groupId);
            console.log('💰 [EXPENSE-FIRESTORE] Balance entries:', Object.keys(data.balances || {}).length);
            
            this._resetReconnectState();
            onUpdate({
              ...data,
              id: docSnapshot.id,
              group_id: groupId,
              last_updated: data.last_updated?.toDate?.() || data.last_updated,
            });
          } else {
            console.log('ℹ️ [EXPENSE-FIRESTORE] No balance document for group:', groupId);
            onUpdate(null);
          }
        },
        (error) => {
          this._handleListenerError(error, listenerKey, () => {
            this.listenToGroupBalances(groupId, onUpdate, onError);
          });
          if (onError) onError(error);
        }
      );

      this.listeners.set(listenerKey, unsubscribe);
      return unsubscribe;

    } catch (error) {
      console.error('❌ [EXPENSE-FIRESTORE] Failed to set up balances listener:', error);
      if (onError) onError(error);
      return () => {};
    }
  }

  /**
   * Listen to group settlements in real-time
   * 
   * @param {string} groupId - Group ID
   * @param {function} onUpdate - Callback with array of settlements
   * @param {function} onError - Error callback
   * @param {number} pageSize - Number of settlements to fetch (default 50)
   * @returns {function} Unsubscribe function
   */
  listenToGroupSettlements(groupId, onUpdate, onError, pageSize = 50) {
    if (!this.initialized) this.initialize();

    const listenerKey = `expense_settlements_${groupId}`;
    
    if (this.listeners.has(listenerKey)) {
      console.log('🔄 [EXPENSE-FIRESTORE] Replacing existing settlements listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [EXPENSE-FIRESTORE] Setting up listener for group settlements:', groupId);

    try {
      const settlementsRef = collection(this.db, 'expense_settlements');
      const q = query(
        settlementsRef,
        where('group_id', '==', groupId),
        orderBy('created_at', 'desc'),
        limit(pageSize)
      );

      const unsubscribe = onSnapshot(
        q,
        (snapshot) => {
          console.log('🔔 [EXPENSE-FIRESTORE] Settlements snapshot received');
          console.log('📊 [EXPENSE-FIRESTORE] Settlements count:', snapshot.size);

          const settlements = [];
          snapshot.forEach(doc => {
            const data = doc.data();
            settlements.push({
              ...data,
              id: doc.id,
              settlement_id: doc.id,
              created_at: data.created_at?.toDate?.() || data.created_at,
              updated_at: data.updated_at?.toDate?.() || data.updated_at,
              settled_at: data.settled_at?.toDate?.() || data.settled_at,
            });
          });

          console.log('✅ [EXPENSE-FIRESTORE] Settlements updated for group:', groupId);
          this._resetReconnectState();
          onUpdate(settlements);
        },
        (error) => {
          this._handleListenerError(error, listenerKey, () => {
            this.listenToGroupSettlements(groupId, onUpdate, onError, pageSize);
          });
          if (onError) onError(error);
        }
      );

      this.listeners.set(listenerKey, unsubscribe);
      return unsubscribe;

    } catch (error) {
      console.error('❌ [EXPENSE-FIRESTORE] Failed to set up settlements listener:', error);
      if (onError) onError(error);
      return () => {};
    }
  }

  /**
   * Listen to user's pending invitations in real-time
   * 
   * @param {string} userEmail - User's email address
   * @param {function} onUpdate - Callback with array of invitations
   * @param {function} onError - Error callback
   * @returns {function} Unsubscribe function
   */
  listenToUserInvitations(userEmail, onUpdate, onError) {
    if (!this.initialized) this.initialize();

    const listenerKey = `expense_invitations_${userEmail}`;
    
    if (this.listeners.has(listenerKey)) {
      console.log('🔄 [EXPENSE-FIRESTORE] Replacing existing invitations listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [EXPENSE-FIRESTORE] Setting up listener for user invitations:', userEmail);

    try {
      const invitationsRef = collection(this.db, 'expense_invitations');
      const q = query(
        invitationsRef,
        where('email', '==', userEmail),
        where('status', '==', 'pending')
      );

      const unsubscribe = onSnapshot(
        q,
        (snapshot) => {
          console.log('🔔 [EXPENSE-FIRESTORE] Invitations snapshot received');
          console.log('📊 [EXPENSE-FIRESTORE] Pending invitations:', snapshot.size);

          const invitations = [];
          snapshot.forEach(doc => {
            const data = doc.data();
            invitations.push({
              ...data,
              id: doc.id,
              invitation_id: doc.id,
              created_at: data.created_at?.toDate?.() || data.created_at,
              expires_at: data.expires_at?.toDate?.() || data.expires_at,
            });
          });

          console.log('✅ [EXPENSE-FIRESTORE] Invitations updated for user:', userEmail);
          this._resetReconnectState();
          onUpdate(invitations);
        },
        (error) => {
          this._handleListenerError(error, listenerKey, () => {
            this.listenToUserInvitations(userEmail, onUpdate, onError);
          });
          if (onError) onError(error);
        }
      );

      this.listeners.set(listenerKey, unsubscribe);
      return unsubscribe;

    } catch (error) {
      console.error('❌ [EXPENSE-FIRESTORE] Failed to set up invitations listener:', error);
      if (onError) onError(error);
      return () => {};
    }
  }

  /**
   * Listen to group's invitations in real-time (for sender/group owner)
   * 
   * Phase 17 Bug Fix: Sender now sees when invitations are accepted/declined
   * 
   * @param {string} groupId - Group ID
   * @param {function} onUpdate - Callback with array of invitations
   * @param {function} onError - Error callback
   * @returns {function} Unsubscribe function
   */
  listenToGroupInvitations(groupId, onUpdate, onError) {
    if (!this.initialized) this.initialize();

    const listenerKey = `expense_group_invitations_${groupId}`;
    
    if (this.listeners.has(listenerKey)) {
      console.log('🔄 [EXPENSE-FIRESTORE] Replacing existing group invitations listener');
      this.listeners.get(listenerKey)();
    }

    console.log('🎧 [EXPENSE-FIRESTORE] Setting up listener for group invitations:', groupId);

    try {
      const invitationsRef = collection(this.db, 'expense_invitations');
      const q = query(
        invitationsRef,
        where('group_id', '==', groupId)
      );

      const unsubscribe = onSnapshot(
        q,
        (snapshot) => {
          console.log('🔔 [EXPENSE-FIRESTORE] Group invitations snapshot received');
          console.log('📊 [EXPENSE-FIRESTORE] Total invitations for group:', snapshot.size);

          const invitations = [];
          snapshot.forEach(doc => {
            const data = doc.data();
            invitations.push({
              ...data,
              id: doc.id,
              invitation_id: doc.id,
              created_at: data.created_at?.toDate?.() || data.created_at,
              expires_at: data.expires_at?.toDate?.() || data.expires_at,
              updated_at: data.updated_at?.toDate?.() || data.updated_at,
            });
          });

          console.log('✅ [EXPENSE-FIRESTORE] Group invitations updated:', groupId, 
            '- pending:', invitations.filter(i => i.status === 'pending').length,
            '- accepted:', invitations.filter(i => i.status === 'accepted').length);
          this._resetReconnectState();
          onUpdate(invitations);
        },
        (error) => {
          this._handleListenerError(error, listenerKey, () => {
            this.listenToGroupInvitations(groupId, onUpdate, onError);
          });
          if (onError) onError(error);
        }
      );

      this.listeners.set(listenerKey, unsubscribe);
      return unsubscribe;

    } catch (error) {
      console.error('❌ [EXPENSE-FIRESTORE] Failed to set up group invitations listener:', error);
      if (onError) onError(error);
      return () => {};
    }
  }

  /**
   * Set up all listeners for a group (convenience method)
   * 
   * @param {string} groupId - Group ID
   * @param {object} callbacks - Object with onGroupUpdate, onMembersUpdate, onExpensesUpdate, onBalancesUpdate, onSettlementsUpdate
   * @param {function} onError - Error callback
   * @returns {function} Unsubscribe all function
   */
  listenToGroupComplete(groupId, callbacks, onError) {
    if (!this.initialized) this.initialize();

    console.log('🎧 [EXPENSE-FIRESTORE] Setting up complete listener suite for group:', groupId);

    const unsubscribers = [];

    // Group details
    if (callbacks.onGroupUpdate) {
      unsubscribers.push(
        this.listenToExpenseGroup(groupId, callbacks.onGroupUpdate, onError)
      );
    }

    // Members
    if (callbacks.onMembersUpdate) {
      unsubscribers.push(
        this.listenToGroupMembers(groupId, callbacks.onMembersUpdate, onError)
      );
    }

    // Expenses
    if (callbacks.onExpensesUpdate) {
      unsubscribers.push(
        this.listenToGroupExpenses(groupId, callbacks.onExpensesUpdate, onError)
      );
    }

    // Balances
    if (callbacks.onBalancesUpdate) {
      unsubscribers.push(
        this.listenToGroupBalances(groupId, callbacks.onBalancesUpdate, onError)
      );
    }

    // Settlements
    if (callbacks.onSettlementsUpdate) {
      unsubscribers.push(
        this.listenToGroupSettlements(groupId, callbacks.onSettlementsUpdate, onError)
      );
    }

    // Invitations (Phase 17 Bug Fix: For sender to see acceptance/decline)
    if (callbacks.onInvitationsUpdate) {
      unsubscribers.push(
        this.listenToGroupInvitations(groupId, callbacks.onInvitationsUpdate, onError)
      );
    }

    console.log(`✅ [EXPENSE-FIRESTORE] Set up ${unsubscribers.length} listeners for group:`, groupId);

    // Return composite unsubscribe function
    return () => {
      console.log(`🛑 [EXPENSE-FIRESTORE] Unsubscribing from ${unsubscribers.length} group listeners`);
      unsubscribers.forEach(unsub => {
        if (typeof unsub === 'function') unsub();
      });
    };
  }

  /**
   * Get listener statistics
   * @returns {object} Statistics about active listeners
   */
  getStats() {
    return {
      initialized: this.initialized,
      activeListeners: this.listeners.size,
      listenerKeys: Array.from(this.listeners.keys()),
      reconnectAttempts: this.reconnectAttempts
    };
  }

  /**
   * Clean up all active listeners
   */
  cleanup() {
    console.log('🧹 [EXPENSE-FIRESTORE] Cleaning up', this.listeners.size, 'listeners');
    this.listeners.forEach((unsubscribe, key) => {
      console.log('   Unsubscribing:', key);
      unsubscribe();
    });
    this.listeners.clear();
    this.reconnectAttempts = 0;
  }

  /**
   * Unsubscribe from a specific listener
   */
  unsubscribe(listenerKey) {
    if (this.listeners.has(listenerKey)) {
      console.log('🛑 [EXPENSE-FIRESTORE] Unsubscribing from:', listenerKey);
      this.listeners.get(listenerKey)();
      this.listeners.delete(listenerKey);
    }
  }

  /**
   * Unsubscribe from all listeners for a specific group
   * Call this BEFORE deleting a group to avoid permission errors
   * @param {string} groupId - The group ID to unsubscribe from
   * @param {boolean} isDeleting - Whether the group is being deleted (suppresses future permission errors)
   */
  unsubscribeFromGroup(groupId, isDeleting = false) {
    console.log('🧹 [EXPENSE-FIRESTORE] Cleaning up all listeners for group:', groupId);
    
    // Track that this group is being deleted to suppress future permission errors
    if (isDeleting) {
      this.deletedGroups.add(groupId);
      console.log('   Marked group as deleted to suppress permission errors');
      
      // Clean up deletedGroups after 30 seconds to prevent memory leak
      setTimeout(() => {
        this.deletedGroups.delete(groupId);
      }, 30000);
    }
    
    const groupListenerKeys = [
      `expense_expenses_${groupId}`,
      `expense_group_invitations_${groupId}`,
      `expense_settlements_${groupId}`,
      `expense_balances_${groupId}`,
      `expense_group_members_${groupId}`,
      `expense_group_${groupId}`
    ];

    let unsubscribedCount = 0;
    groupListenerKeys.forEach(key => {
      if (this.listeners.has(key)) {
        console.log('   Unsubscribing:', key);
        this.listeners.get(key)();
        this.listeners.delete(key);
        unsubscribedCount++;
      }
    });

    console.log(`🧹 [EXPENSE-FIRESTORE] Unsubscribed from ${unsubscribedCount} listeners for group ${groupId}`);
    return unsubscribedCount;
  }
}

// Export singleton instance
const expenseFirestoreListener = new ExpenseFirestoreListener();
export default expenseFirestoreListener;
