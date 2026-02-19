/**
 * Group Planner API Service
 * Connects frontend to the group planner backend (SQL version)
 * Pattern: Follows expenseApi.js for consistency
 * Uses SQL JWT auth via sqlAuthService
 */

import GlobalConfig from '../config/globalConfig';
import sqlAuthService from './sqlAuthService';

class GroupPlannerApiService {
  constructor() {
    // Use v2 SQL-based API endpoint
    this.baseUrl = `${GlobalConfig.API_BASE_URL}/v2/group-planner`;
    this.authToken = null;
    this.currentUser = null;
  }

  setAuthToken(token) {
    this.authToken = token;
  }

  setCurrentUser(user) {
    this.currentUser = user;
  }

  async getFreshToken() {
    // SQL JWT auth service
    try {
      const token = await sqlAuthService.getIdToken(true);
      if (token) {
        this.authToken = token;
        localStorage.setItem('groupPlannerToken', token);
        return token;
      }
    } catch (error) {
      // token refresh failed silently
    }
    
    if (this.authToken) {
      return this.authToken;
    }
    
    const storedToken = localStorage.getItem('groupPlannerToken');
    if (storedToken) {
      this.authToken = storedToken;
      return storedToken;
    }
    
    return null;
  }

  async getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };
    
    const token = await this.getFreshToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
  }

  async handleResponse(response) {
    const data = await response.json();
    
    if (!response.ok) {
      let errorMsg = data.message || data.error || `API Error: ${response.status}`;
      
      // More user-friendly error messages
      if (response.status === 409) {
        errorMsg = 'This place already exists in your trip. Please add a different place.';
      } else if (response.status === 400) {
        errorMsg = data.message || 'Invalid request. Please check your input.';
      } else if (response.status === 401) {
        errorMsg = 'Your session has expired. Please log in again.';
      }
      
      throw new Error(errorMsg);
    }
    
    return data;
  }

  /**
   * Centralized fetch wrapper.
   * Sends credentials (httpOnly cookies) along with every request and
   * attaches the Authorization header for backward compatibility.
   */
  async request(url, options = {}) {
    const headers = options.headers || await this.getHeaders();
    return fetch(url, {
      ...options,
      headers,
      credentials: 'include',
    });
  }

  // =========================================================================
  // PHASE 1: AUTHENTICATION
  // =========================================================================

  async verifyAuth() {
    const headers = await this.getHeaders();
    
    const response = await this.request(`${this.baseUrl}/auth/verify`, {
      method: 'POST',
      headers,
    });

    return this.handleResponse(response);
  }

  // =========================================================================
  // PHASE 2: GROUP OPERATIONS (Coming Soon)
  // =========================================================================

  async createGroup(groupData) {
    const response = await this.request(`${this.baseUrl}/groups`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(groupData)
    });
    return this.handleResponse(response);
  }

  async getGroup(groupId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async getUserGroups() {
    const response = await this.request(`${this.baseUrl}/user/groups`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async updateGroup(groupId, updates) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify(updates)
    });
    return this.handleResponse(response);
  }

  async updateItineraryDocument(groupId, content) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/itinerary-document`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify({ content })
    });
    return this.handleResponse(response);
  }

  async deleteGroup(groupId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async getGroupMembers(groupId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/members`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // PHASE 2B: INVITATION OPERATIONS
  // =========================================================================

  async createInvitation(groupId, email) {
    const response = await this.request(`${this.baseUrl}/invitations`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({ group_id: groupId, email })
    });
    return this.handleResponse(response);
  }

  async acceptInvitation(invitationId) {
    const response = await this.request(`${this.baseUrl}/invitations/${invitationId}/accept`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async getUserInvitations() {
    const response = await this.request(`${this.baseUrl}/user/invitations`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async getGroupInvitations(groupId) {
    // Get all invitations for a specific group
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/invitations`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async resendInvitation(invitationId) {
    const response = await this.request(`${this.baseUrl}/invitations/${invitationId}/resend`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async deleteInvitation(invitationId) {
    // Delete/cancel an invitation
    const response = await this.request(`${this.baseUrl}/invitations/${invitationId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // PHASE 2C: POLL OPERATIONS
  // =========================================================================

  async createPoll(groupId, pollData) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/polls`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(pollData)
    });
    return this.handleResponse(response);
  }

  async voteOnPoll(groupId, pollId, option) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/polls/${pollId}/vote`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({ option_index: option })
    });
    return this.handleResponse(response);
  }

  async deletePoll(groupId, pollId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/polls/${pollId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // PHASE 2D: PLACE OPERATIONS
  // =========================================================================

  async getGroupPlaces(groupId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/places`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async addPlace(groupId, placeNameOrObject) {
    // Handle both string (legacy) and object (new) formats
    const isObject = typeof placeNameOrObject === 'object';
    
    // Extract coordinates from various formats
    let latitude = null;
    let longitude = null;
    if (isObject) {
      if (placeNameOrObject.coordinates) {
        latitude = placeNameOrObject.coordinates.latitude || placeNameOrObject.coordinates.lat;
        longitude = placeNameOrObject.coordinates.longitude || placeNameOrObject.coordinates.lng;
      }
      if (!latitude && placeNameOrObject.latitude) {
        latitude = placeNameOrObject.latitude;
      }
      if (!longitude && placeNameOrObject.longitude) {
        longitude = placeNameOrObject.longitude;
      }
    }
    
    const placeData = isObject ? {
      placeId: placeNameOrObject.id,
      name: placeNameOrObject.place_name || placeNameOrObject.name || placeNameOrObject.restaurant_name,
      latitude: latitude,
      longitude: longitude,
      address: placeNameOrObject.address || '',
      category: placeNameOrObject.category || 'attraction',
      description: placeNameOrObject.description || placeNameOrObject.ai_summary || '',
      rating: placeNameOrObject.rating || placeNameOrObject.rating_tourist_priority,
      photo_url: placeNameOrObject.photo_url || (placeNameOrObject.photos?.[0]),
      website: placeNameOrObject.website || ''
    } : {
      name: placeNameOrObject
    };
    
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/places`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(placeData)
    });
    return this.handleResponse(response);
  }

  async voteOnPlace(groupId, placeId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/places/${placeId}/vote`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({ vote_type: 'up' })
    });
    return this.handleResponse(response);
  }

  async deletePlace(groupId, placeId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/places/${placeId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async updatePlaceRemarks(groupId, placeId, remarks) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/places/${placeId}/remarks`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify({ remarks })
    });
    return this.handleResponse(response);
  }

  async updatePlaceDetails(groupId, placeId, details) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/places/${placeId}`, {
      method: 'PATCH',
      headers: await this.getHeaders(),
      body: JSON.stringify(details)
    });
    return this.handleResponse(response);
  }

  // Alias for updatePlaceDetails
  async updatePlace(groupId, placeId, details) {
    return this.updatePlaceDetails(groupId, placeId, details);
  }

  // =========================================================================
  // EXPENSE GROUP OPERATIONS
  // =========================================================================

  async getExpenseSummary(groupId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/expense-summary`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async linkExpenseGroup(groupId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/link-expense`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async unlinkExpenseGroup(groupId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/unlink-expense`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // EVENTS OPERATIONS (Ticketmaster Integration)
  // =========================================================================

  async getDestinationEvents(destination, options = {}) {
    const params = new URLSearchParams({
      destination: destination,
      limit: options.limit || 20,
      ...(options.startDate && { start_date: options.startDate }),
      ...(options.endDate && { end_date: options.endDate }),
      ...(options.category && { category: options.category })
    });
    
    const response = await this.request(`${this.baseUrl}/events?${params}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // PHASE 2E: CHECKLIST OPERATIONS
  // =========================================================================

  async addChecklistItem(groupId, itemText) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/checklist`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({ text: itemText })
    });
    return this.handleResponse(response);
  }

  async toggleChecklistItem(groupId, itemId) {
    const response = await this.request(`${this.baseUrl}/checklist/${itemId}/toggle`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({ group_id: groupId })
    });
    return this.handleResponse(response);
  }

  async deleteChecklistItem(groupId, itemId) {
    const response = await this.request(`${this.baseUrl}/checklist/${itemId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async updateChecklistItem(groupId, itemId, updates) {
    const response = await this.request(`${this.baseUrl}/checklist/${itemId}`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify(updates)
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // ADDITIONAL OPERATIONS (merged from groupPlannerService.js)
  // =========================================================================

  async removeMember(groupId, userId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/members/${userId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async getGroupPolls(groupId) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/polls`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async updateBudget(groupId, budget) {
    const response = await this.request(`${this.baseUrl}/groups/${groupId}/budget`, {
      method: 'PATCH',
      headers: await this.getHeaders(),
      body: JSON.stringify({ estimated_budget: budget })
    });
    return this.handleResponse(response);
  }

  async getInvitationDetails(invitationId) {
    const response = await this.request(`${this.baseUrl}/invitations/${invitationId}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * No-op cache clear. The old groupPlannerService.js had an in-memory cache;
   * this class relies on React Query for caching. Kept for backward compat
   * (called by AuthContext on logout).
   */
  clearAllCache() {
    // No-op: caching is handled by React Query, not in-memory maps.
  }

  clearCache() { this.clearAllCache(); }
  invalidateCache() { this.clearAllCache(); }
}

const groupPlannerApi = new GroupPlannerApiService();
export default groupPlannerApi;
