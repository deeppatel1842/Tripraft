/**
 * Group Planner API Service
 * Connects frontend to the group planner backend
 * Pattern: Follows expenseApi.js for consistency
 */

import GlobalConfig from '../config/globalConfig';

class GroupPlannerApiService {
  constructor() {
    this.baseUrl = `${GlobalConfig.API_BASE_URL}/group-planner`;
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
    if (this.currentUser) {
      try {
        const token = await this.currentUser.getIdToken(true);
        this.authToken = token;
        localStorage.setItem('groupPlannerToken', token);
        return token;
      } catch (error) {
        console.error('Error refreshing token:', error);
      }
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
      throw new Error(data.message || data.error || `API Error: ${response.status}`);
    }
    
    return data;
  }

  // =========================================================================
  // PHASE 1: AUTHENTICATION
  // =========================================================================

  async verifyAuth() {
    const headers = await this.getHeaders();
    
    const response = await fetch(`${this.baseUrl}/auth/verify`, {
      method: 'POST',
      headers,
    });

    return this.handleResponse(response);
  }

  // =========================================================================
  // PHASE 2: GROUP OPERATIONS (Coming Soon)
  // =========================================================================

  async createGroup(groupData) {
    const response = await fetch(`${this.baseUrl}/groups`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(groupData)
    });
    return this.handleResponse(response);
  }

  async getGroup(groupId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async getUserGroups() {
    const response = await fetch(`${this.baseUrl}/user/groups`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async updateGroup(groupId, updates) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify(updates)
    });
    return this.handleResponse(response);
  }

  async deleteGroup(groupId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // PHASE 2B: INVITATION OPERATIONS
  // =========================================================================

  async createInvitation(groupId, email) {
    const response = await fetch(`${this.baseUrl}/invitations`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({ group_id: groupId, email })
    });
    return this.handleResponse(response);
  }

  async acceptInvitation(invitationId) {
    const response = await fetch(`${this.baseUrl}/invitations/${invitationId}/accept`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async getUserInvitations() {
    const response = await fetch(`${this.baseUrl}/user/invitations`, {
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async resendInvitation(invitationId) {
    const response = await fetch(`${this.baseUrl}/invitations/${invitationId}/resend`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // PHASE 2C: POLL OPERATIONS
  // =========================================================================

  async createPoll(groupId, pollData) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/polls`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify(pollData)
    });
    return this.handleResponse(response);
  }

  async voteOnPoll(groupId, pollId, option) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/polls/${pollId}/vote`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({ option })
    });
    return this.handleResponse(response);
  }

  async deletePoll(groupId, pollId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/polls/${pollId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // PHASE 2D: PLACE OPERATIONS
  // =========================================================================

  async addPlace(groupId, placeName) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/places`, {
      method: 'POST',
      headers: await this.getHeaders(),
      body: JSON.stringify({ name: placeName })
    });
    return this.handleResponse(response);
  }

  async voteOnPlace(groupId, placeId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/places/${placeId}/vote`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async deletePlace(groupId, placeId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/places/${placeId}`, {
      method: 'DELETE',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async updatePlaceRemarks(groupId, placeId, remarks) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/places/${placeId}/remarks`, {
      method: 'PUT',
      headers: await this.getHeaders(),
      body: JSON.stringify({ remarks })
    });
    return this.handleResponse(response);
  }

  // =========================================================================
  // EXPENSE GROUP OPERATIONS
  // =========================================================================

  async linkExpenseGroup(groupId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/link-expense`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }

  async unlinkExpenseGroup(groupId) {
    const response = await fetch(`${this.baseUrl}/groups/${groupId}/unlink-expense`, {
      method: 'POST',
      headers: await this.getHeaders()
    });
    return this.handleResponse(response);
  }
}

const groupPlannerApi = new GroupPlannerApiService();
export default groupPlannerApi;
