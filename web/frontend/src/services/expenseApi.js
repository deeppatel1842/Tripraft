/**
 * Expense Management API Service
 * Updated to use new /api/expense/* backend endpoints
 * All endpoints follow REST conventions and return {success, ...data}
 */

import GlobalConfig from '../config/globalConfig';

class ExpenseApiService {
  constructor() {
    this.baseUrl = `${GlobalConfig.API_BASE_URL}/expense`;
    this.authToken = null;
    this.currentUser = null;
    // Phase 18.5: Request deduplication map
    this.pendingRequests = new Map();
  }

  /**
   * Phase 18.5: Deduplicate concurrent requests to the same endpoint
   * Prevents multiple parallel requests for the same data
   * @param {string} key - Unique key for the request (e.g., "getUserGroups:1:20")
   * @param {Function} requestFn - Async function that makes the actual request
   * @returns {Promise} - Shared promise for all callers
   */
  async deduplicateRequest(key, requestFn) {
    // If request is already in flight, return the existing promise
    if (this.pendingRequests.has(key)) {
      console.log(`🔄 [API] Deduplicating request: ${key}`);
      return this.pendingRequests.get(key);
    }
    
    // Create new request and store the promise
    const promise = requestFn().finally(() => {
      // Remove from pending when complete (success or error)
      this.pendingRequests.delete(key);
    });
    
    this.pendingRequests.set(key, promise);
    return promise;
  }

  /**
   * Set authentication token and user
   */
  setAuthToken(token) {
    this.authToken = token;
  }

  /**
   * Set current user (needed for token refresh)
   */
  setCurrentUser(user) {
    this.currentUser = user;
  }

  /**
   * Get fresh token (refreshes if needed)
   */
  async getFreshToken() {
    // First try to get token from current user object (can refresh)
    if (this.currentUser) {
      try {
        // Force refresh token to ensure it's valid
        const token = await this.currentUser.getIdToken(true);
        this.authToken = token;
        // Save to localStorage as well
        localStorage.setItem('token', token);
        return token;
      } catch (error) {
        console.error('Error refreshing token:', error);
      }
    }
    
    // Fallback to stored token in memory
    if (this.authToken) {
      return this.authToken;
    }
    
    // Fallback to localStorage (for page refreshes)
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      console.log('📦 Using token from localStorage (length:', storedToken.length, 'chars)');
      this.authToken = storedToken;
      return storedToken;
    }
    
    console.warn('⚠️ No token available - user may need to sign in');
    return null;
  }

  /**
   * Get authentication headers with fresh token
   */
  async getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };
    
    // Always get fresh token before making request
    const token = await this.getFreshToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
  }

  /**
   * Handle API response
   */
  async handleResponse(response) {
    const data = await response.json();
    
    if (!response.ok) {
      // Use the more detailed message if available, otherwise use error
      throw new Error(data.message || data.error || `API Error: ${response.status}`);
    }
    
    return data;
  }

  // =========================================================================
  // USER OPERATIONS
  // =========================================================================

  /**
   * User creation is handled by the authentication system
   * This is a no-op for backward compatibility
   */
  async createUser(userData) {
    // Silently succeed - auth system handles user creation
    return { success: true, message: 'User creation handled by auth system' };
  }

  /**
   * Get current user profile
   */
  async getUser() {
    const response = await fetch(`${this.baseUrl}/user/profile`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Update user profile
   */
  async updateUser(updates) {
    const response = await fetch(`${this.baseUrl}/user/profile`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify(updates)
    });
    return this.handleResponse(response);
  }

  /**
   * Get user's groups - NEW API ENDPOINT
   * GET /api/expense/user/groups
   * Phase 18.5: Uses request deduplication to prevent parallel calls
   */
  async getUserGroups(page = 1, limit = 20) {
    const key = `getUserGroups:${page}:${limit}`;
    return this.deduplicateRequest(key, async () => {
      const response = await fetch(`${this.baseUrl}/user/groups?page=${page}&limit=${limit}`, {
        headers: await this.getHeaders(),
        cache: 'no-store'
      });
      return this.handleResponse(response);
    });
  }

  /**
   * Search for users
   */
  async searchUsers(query) {
    const response = await fetch(`${this.baseUrl}/user/search?q=${encodeURIComponent(query)}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // GROUP OPERATIONS
  // =========================================================================

  /**
   * Create a new group
   */
  async createGroup(groupData) {
    const response = await fetch(`${this.baseUrl}/groups`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(groupData)
    });
    return this.handleResponse(response);
  }

  /**
   * Get group by ID
   */
  async getGroup(groupId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * 🚀 PHASE 6.2: Get ALL group data in ONE optimized API call
   * Returns: group details, members, expenses, balances, settlements, invitations
   * 
   * Benefits:
   * - Reduces 6 API calls → 1 API call
   * - Reduces network overhead by ~500-1000ms
   * - Single cache key (20min TTL)
   * - Atomic data consistency
   * 
   * Performance:
   * - First load: ~8-12 Firestore reads
   * - Cached: 0 reads, <5ms response
   * 
   * @param {string} groupId - Group ID
   * @param {boolean} bypassCache - If true, force fresh data (use ?_t parameter)
   */
  async getGroupFull(groupId, bypassCache = false) {
    const url = bypassCache
      ? `${this.baseUrl}/groups/${groupId}/full?_t=${Date.now()}`
      : `${this.baseUrl}/groups/${groupId}/full`;
    
    const response = await fetch(url, {
      headers: await this.getHeaders(),
      cache: 'no-store' // Disable browser caching
    });
    return this.handleResponse(response);
  }

  /**
   * Update group
   */
  async updateGroup(groupId, updates) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify(updates)
    });
    return this.handleResponse(response);
  }

  /**
   * Delete group
   */
  async deleteGroup(groupId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get group members
   */
  async getGroupMembers(groupId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/members`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Add member to group
   */
  async addGroupMember(groupId, memberData) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/members`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(memberData)
    });
    return this.handleResponse(response);
  }

  /**
   * Remove member from group
   */
  async removeGroupMember(groupId, userId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/members/${userId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // INVITATION OPERATIONS
  // =========================================================================

  /**
   * Send group invitation
   */
  async sendInvitation(invitationData) {
    const response = await fetch(`${this.baseUrl}/invitations`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(invitationData)
    });
    return this.handleResponse(response);
  }

  /**
   * Get invitation details (no auth required)
   */
  async getInvitationDetails(invitationId) {
    const response = await fetch(`${this.baseUrl}/invitations/${invitationId}/details`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    return this.handleResponse(response);
  }

  /**
   * Accept invitation
   */
  async acceptInvitation(invitationId) {
    const response = await fetch(`${this.baseUrl}/invitations/${invitationId}/accept`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Decline invitation
   */
  async declineInvitation(invitationId) {
    const response = await fetch(`${this.baseUrl}/invitations/${invitationId}/reject`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get pending invitations for current user - NEW API ENDPOINT
   * GET /api/expense/invitations/user
   */
  async getPendingInvitations(status = 'pending', page = 1, limit = 20) {
    const response = await fetch(`${this.baseUrl}/invitations/user?status=${status}&page=${page}&limit=${limit}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get invitations for a group
   * @param {string} groupId - Group ID
   * @param {boolean} includeAll - If true, include declined and accepted invitations
   * @param {number} timestamp - Optional timestamp to bypass cache
   */
  async getGroupInvitations(groupId, includeAll = true, timestamp = null) {
    const params = new URLSearchParams();
    // Include all invitations by default so owner can see declined ones
    params.append('include_all', includeAll.toString());
    if (timestamp) {
      params.append('_t', timestamp);
    }
    const url = `${this.baseUrl}/invitations/group/${groupId}?${params.toString()}`;
    const response = await fetch(url, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // EXPENSE OPERATIONS
  // =========================================================================

  /**
   * Create an expense (supports any currency: USD, EUR, INR, etc.)
   */
  async createExpense(expenseData) {
    const response = await fetch(`${this.baseUrl}/expenses`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(expenseData)
    });
    return this.handleResponse(response);
  }

  /**
   * Get expense by ID
   */
  async getExpense(expenseId) {
    const response = await fetch(`${this.baseUrl}/expenses/${expenseId}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Update expense
   */
  async updateExpense(expenseId, updates) {
    const response = await fetch(`${this.baseUrl}/expenses/${expenseId}`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify(updates)
    });
    return this.handleResponse(response);
  }

  /**
   * Delete expense
   */
  async deleteExpense(expenseId) {
    const response = await fetch(`${this.baseUrl}/expenses/${expenseId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get group expenses
   */
  async getGroupExpenses(groupId, params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    const url = queryParams 
      ? `${this.baseUrl}/expenses/group/${groupId}?${queryParams}`
      : `${this.baseUrl}/expenses/group/${groupId}`;
    
    const response = await fetch(url, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get user expenses (backward compatibility)
   * Returns empty array - use getGroupExpenses() for actual data
   */
  async getUserExpenses(params = {}) {
    // Return empty for backward compatibility
    return { success: true, expenses: [], data: [] };
  }

  /**
   * Get expense splits
   */
  async getExpenseSplits(expenseId) {
    const response = await fetch(`${this.baseUrl}/expenses/${expenseId}/splits`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get expense edit history (Phase 12)
   * Returns list of changes made to an expense
   */
  async getExpenseHistory(expenseId) {
    const response = await fetch(`${this.baseUrl}/expenses/${expenseId}/history`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get group audit log (Phase 12)
   * Returns all expense changes in a group
   */
  async getGroupAuditLog(groupId, limit = 50, offset = 0) {
    const params = new URLSearchParams({ limit, offset });
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/audit-log?${params}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // SETTLEMENT OPERATIONS
  // =========================================================================

  /**
   * Create settlement
   */
  async createSettlement(settlementData) {
    const response = await fetch(`${this.baseUrl}/settlements`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(settlementData)
    });
    return this.handleResponse(response);
  }

  /**
   * Get settlement by ID
   */
  async getSettlement(settlementId) {
    const response = await fetch(`${this.baseUrl}/settlements/${settlementId}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Confirm settlement
   */
  async confirmSettlement(settlementId) {
    const response = await fetch(`${this.baseUrl}/settlements/${settlementId}/confirm`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Cancel settlement
   */
  async cancelSettlement(settlementId) {
    const response = await fetch(`${this.baseUrl}/settlements/${settlementId}/cancel`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get settlements for a group (alias for getGroupSettlements)
   */
  async getSettlements(groupId, status = null) {
    return this.getGroupSettlements(groupId, status);
  }

  /**
   * Get group settlements
   */
  async getGroupSettlements(groupId, status = null) {
    const url = status 
      ? `${this.baseUrl}/settlements/group/${groupId}?status=${status}`
      : `${this.baseUrl}/settlements/group/${groupId}`;
    
    const response = await fetch(url, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get user settlements
   */
  async getUserSettlements(uid, status = null) {
    const url = status 
      ? `${this.baseUrl}/settlements/user/${uid}?status=${status}`
      : `${this.baseUrl}/settlements/user/${uid}`;
    
    const response = await fetch(url, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // BALANCE OPERATIONS
  // =========================================================================

  /**
   * Get group balances
   */
  async getGroupBalances(groupId) {
    const response = await fetch(`${this.baseUrl}/balances/group/${groupId}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get user balances
   */
  async getUserBalances(uid) {
    const response = await fetch(`${this.baseUrl}/balances/user/${uid}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get balance between two users
   */
  async getUserBalance(uid, groupId) {
    const response = await fetch(`${this.baseUrl}/balances/user/${uid}/group/${groupId}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Calculate simplified debts
   */
  async getSimplifiedDebts(groupId) {
    const response = await fetch(`${this.baseUrl}/balances/group/${groupId}/simplified`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Recalculate group balances
   */
  async recalculateBalances(groupId) {
    const response = await fetch(`${this.baseUrl}/balances/group/${groupId}/recalculate`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // ANALYTICS OPERATIONS
  // =========================================================================

  /**
   * Get group analytics
   */
  async getGroupAnalytics(groupId) {
    const response = await fetch(`${this.baseUrl}/analytics/group/${groupId}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get user analytics
   */
  async getUserAnalytics(uid) {
    const response = await fetch(`${this.baseUrl}/analytics/user/${uid}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get expense trends
   */
  async getExpenseTrends(groupId, period = 'month') {
    const response = await fetch(`${this.baseUrl}/analytics/group/${groupId}/trends?period=${period}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // PHASE 16: ULTRA-UNIFIED API - Mega Bootstrap
  // =========================================================================

  /**
   * Get EVERYTHING in one API call
   * 
   * Replaces multiple calls:
   * - getUserGroups()
   * - getPendingInvitations()
   * - getGroupFull()
   * - getGroupSettlements()
   * 
   * Performance:
   * - Reduces 10+ API calls to 1
   * - Cold cache: ~600-1000ms
  /**
   * 🚀 MEGA BOOTSTRAP - Single API call for all dashboard data
   * Phase 18.5: Uses request deduplication to prevent parallel calls
   * 
   * @param {Object} options
   * @param {string} options.activeGroupId - Include full data for this group
   * @param {number} options.recentExpensesLimit - Max recent expenses (default 20)
   * @param {boolean} options.bypassCache - Force fresh data
   * @returns {Promise<Object>} Complete dashboard + group data
   */
  async getMegaBootstrap(options = {}) {
    const key = `getMegaBootstrap:${options.activeGroupId || 'dashboard'}:${options.bypassCache || false}`;
    
    return this.deduplicateRequest(key, async () => {
      const params = new URLSearchParams();
      
      if (options.activeGroupId) {
        params.append('active_group_id', options.activeGroupId);
      }
      if (options.recentExpensesLimit) {
        params.append('recent_expenses_limit', options.recentExpensesLimit);
      }
      if (options.bypassCache) {
        params.append('bypass_cache', 'true');
      }
      
      const url = `${this.baseUrl}/mega-bootstrap?${params.toString()}`;
      const response = await fetch(url, {
        headers: await this.getHeaders(),
        cache: 'no-store'
      });
      return this.handleResponse(response);
    });
  }

  // =========================================================================
  // PHASE 21: EXTREME API - 10 Total Operations Mode
  // =========================================================================
  
  /**
   * Extreme API Mode Flag
   * When true, mutations use /api/expense/extreme/* endpoints
   * which achieve 0 Firestore reads per operation (cache-only)
   */
  extremeMode = true;
  
  /**
   * Get extreme API base URL
   */
  get extremeUrl() {
    return `${GlobalConfig.API_BASE_URL}/expense/extreme`;
  }
  
  /**
   * Enable/disable extreme mode
   */
  setExtremeMode(enabled) {
    this.extremeMode = enabled;
    console.log(`🚀 Extreme API mode: ${enabled ? 'ENABLED' : 'DISABLED'}`);
  }
  
  /**
   * Get extreme dashboard - THE ONLY READ OPERATION NEEDED
   * Returns all groups, balances, recent expenses, invitations
   * 
   * @param {boolean} forceRefresh - Force refresh from Firestore (bypass cache)
   * @returns {Promise<Object>} Complete user dashboard
   */
  async getExtremeDashboard(forceRefresh = false) {
    const params = forceRefresh ? '?force_refresh=true' : '';
    const response = await fetch(`${this.extremeUrl}/dashboard${params}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }
  
  // ---------------------------------------------------------------------------
  // EXTREME GROUP OPERATIONS - 0 reads, 1 write each
  // ---------------------------------------------------------------------------
  
  /**
   * Create group via extreme API (0 reads, 1 batch write)
   */
  async createGroupExtreme(groupData) {
    const response = await fetch(`${this.extremeUrl}/groups`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(groupData)
    });
    return this.handleResponse(response);
  }
  
  /**
   * Add member to group via extreme API (0 reads, 1 batch write)
   */
  async addMemberExtreme(groupId, memberData) {
    const response = await fetch(`${this.extremeUrl}/groups/${groupId}/members`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(memberData)
    });
    return this.handleResponse(response);
  }
  
  /**
   * Remove member from group via extreme API (0 reads, 1 batch write)
   */
  async removeMemberExtreme(groupId, memberId) {
    const response = await fetch(`${this.extremeUrl}/groups/${groupId}/members/${memberId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }
  
  /**
   * Update group via extreme API (0 reads, 1 batch write)
   */
  async updateGroupExtreme(groupId, updates) {
    const response = await fetch(`${this.extremeUrl}/groups/${groupId}`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify(updates)
    });
    return this.handleResponse(response);
  }
  
  // ---------------------------------------------------------------------------
  // EXTREME EXPENSE OPERATIONS - 0 reads, 1 write each
  // ---------------------------------------------------------------------------
  
  /**
   * Create expense via extreme API (0 reads, 1 batch write)
   */
  async createExpenseExtreme(expenseData) {
    const response = await fetch(`${this.extremeUrl}/expenses`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(expenseData)
    });
    return this.handleResponse(response);
  }
  
  /**
   * Update expense via extreme API (0 reads, 1 batch write)
   */
  async updateExpenseExtreme(expenseId, updates) {
    const response = await fetch(`${this.extremeUrl}/expenses/${expenseId}`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify(updates)
    });
    return this.handleResponse(response);
  }
  
  /**
   * Delete expense via extreme API (0 reads, 1 batch write)
   */
  async deleteExpenseExtreme(expenseId, groupId) {
    const response = await fetch(`${this.extremeUrl}/expenses/${expenseId}?group_id=${groupId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }
  
  // ---------------------------------------------------------------------------
  // EXTREME SETTLEMENT OPERATIONS - 0 reads, 1 write each
  // ---------------------------------------------------------------------------
  
  /**
   * Create settlement via extreme API (0 reads, 1 batch write)
   */
  async createSettlementExtreme(settlementData) {
    const response = await fetch(`${this.extremeUrl}/settlements`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(settlementData)
    });
    return this.handleResponse(response);
  }
  
  /**
   * Delete settlement via extreme API (0 reads, 1 batch write)
   */
  async deleteSettlementExtreme(settlementId, groupId) {
    const response = await fetch(`${this.extremeUrl}/settlements/${settlementId}?group_id=${groupId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }
  
  // ---------------------------------------------------------------------------
  // EXTREME INVITATION OPERATIONS - 0 reads, 1 write each
  // ---------------------------------------------------------------------------
  
  /**
   * Accept invitation via extreme API (0 reads, 1 batch write)
   */
  async acceptInvitationExtreme(invitationId) {
    const response = await fetch(`${this.extremeUrl}/invitations/${invitationId}/accept`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }
  
  /**
   * Decline invitation via extreme API (0 reads, 1 batch write)
   */
  async declineInvitationExtreme(invitationId) {
    const response = await fetch(`${this.extremeUrl}/invitations/${invitationId}/decline`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }
  
  // ---------------------------------------------------------------------------
  // EXTREME UTILITY
  // ---------------------------------------------------------------------------
  
  /**
   * Force sync dashboard (1 read, 0 writes)
   * Use this to refresh cache from Firestore
   */
  async syncDashboard() {
    const response = await fetch(`${this.extremeUrl}/sync`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }
  
  /**
   * Check extreme API health
   */
  async extremeHealth() {
    const response = await fetch(`${this.extremeUrl}/health`);
    return this.handleResponse(response);
  }
}

// Create singleton instance
const expenseApi = new ExpenseApiService();

export default expenseApi;
