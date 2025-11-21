/**
 * Expense Management API Service
 * Connects frontend to the expense backend with multi-currency support
 */

import GlobalConfig from '../config/globalConfig';
import authService from '../firebase/authService';

class ExpenseApiService {
  constructor() {
    this.baseUrl = `${GlobalConfig.API_BASE_URL}/expense`;
    this.authToken = null;
    this.currentUser = null;
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
   * Create or update user profile
   */
  async createUser(userData) {
    const response = await fetch(`${this.baseUrl}/user/profile`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({
        username: userData.email.split('@')[0], // Generate username from email
        display_name: userData.displayName || '',
        profile_picture: userData.photoURL || null
      })
    });
    return this.handleResponse(response);
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
   * Get user's groups
   * @param {boolean} summaryMode - If true, returns minimal data (90% faster, 5 Firestore reads instead of 50+)
   * @param {boolean} bypassCache - If true, force fresh data from backend
   */
  async getUserGroups(summaryMode = true, bypassCache = false) {
    const mode = summaryMode ? 'summary' : 'full';
    const url = bypassCache 
      ? `${this.baseUrl}/groups?mode=${mode}&_t=${Date.now()}`
      : `${this.baseUrl}/groups?mode=${mode}`;
      
    const response = await fetch(url, {
      headers: await this.getHeaders(),
      cache: 'no-store'
    });
    return this.handleResponse(response);
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
   * Get pending invitations for current user (homepage list)
   */
  async getPendingInvitations() {
    const response = await fetch(`${this.baseUrl}/invitations`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get pending invitations for a group
   */
  async getGroupInvitations(groupId, timestamp = null) {
    // Add timestamp parameter to bypass cache
    const url = timestamp 
      ? `${this.baseUrl}/invitations/group/${groupId}?_t=${timestamp}`
      : `${this.baseUrl}/invitations/group/${groupId}`;
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
   * Get user expenses (for current authenticated user)
   * @param {Object} params - Query parameters
   * @param {boolean} params.personal_only - If true, return only personal expenses (no group expenses)
   */
  async getUserExpenses(params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    const url = queryParams 
      ? `${this.baseUrl}/expenses/user?${queryParams}`
      : `${this.baseUrl}/expenses/user`;
    
    const response = await fetch(url, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
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
}

// Create singleton instance
const expenseApi = new ExpenseApiService();

export default expenseApi;
