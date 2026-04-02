/**
 * Group Planner API Service
 * Connects frontend to the group planner backend (SQL version).
 *
 * All HTTP, auth, timeout, retry, and error handling is delegated to apiClient.
 */

import apiClient from '../utils/apiClient';
import GlobalConfig from '../config/globalConfig';

const BASE = GlobalConfig.ENDPOINTS.GROUP_PLANNER;

class GroupPlannerApiService {
  // No-ops kept for backward compatibility
  setAuthToken() {}
  setCurrentUser() {}

  // =========================================================================
  // AUTHENTICATION
  // =========================================================================

  async verifyAuth() {
    return apiClient.post(`${BASE}/auth/verify`);
  }

  // =========================================================================
  // GROUP OPERATIONS
  // =========================================================================

  async createGroup(groupData) {
    return apiClient.post(`${BASE}/groups`, groupData);
  }

  async getGroup(groupId) {
    return apiClient.get(`${BASE}/groups/${groupId}`);
  }

  async getUserGroups() {
    return apiClient.get(`${BASE}/user/groups`);
  }

  async updateGroup(groupId, updates) {
    return apiClient.put(`${BASE}/groups/${groupId}`, updates);
  }

  async updateItineraryDocument(groupId, content) {
    return apiClient.put(`${BASE}/groups/${groupId}/itinerary-document`, { content });
  }

  async deleteGroup(groupId) {
    return apiClient.delete(`${BASE}/groups/${groupId}`);
  }

  async getGroupMembers(groupId) {
    return apiClient.get(`${BASE}/groups/${groupId}/members`);
  }

  // =========================================================================
  // INVITATION OPERATIONS
  // =========================================================================

  async createInvitation(groupId, email) {
    return apiClient.post(`${BASE}/invitations`, { group_id: groupId, email });
  }

  async acceptInvitation(invitationId) {
    return apiClient.post(`${BASE}/invitations/${invitationId}/accept`);
  }

  async getUserInvitations() {
    return apiClient.get(`${BASE}/user/invitations`);
  }

  async getGroupInvitations(groupId) {
    return apiClient.get(`${BASE}/groups/${groupId}/invitations`);
  }

  async resendInvitation(invitationId) {
    return apiClient.post(`${BASE}/invitations/${invitationId}/resend`);
  }

  async deleteInvitation(invitationId) {
    return apiClient.delete(`${BASE}/invitations/${invitationId}`);
  }

  // =========================================================================
  // POLL OPERATIONS
  // =========================================================================

  async createPoll(groupId, pollData) {
    return apiClient.post(`${BASE}/groups/${groupId}/polls`, pollData);
  }

  async voteOnPoll(groupId, pollId, option) {
    return apiClient.post(`${BASE}/groups/${groupId}/polls/${pollId}/vote`, { option_index: option });
  }

  async deletePoll(groupId, pollId) {
    return apiClient.delete(`${BASE}/groups/${groupId}/polls/${pollId}`);
  }

  // =========================================================================
  // PLACE OPERATIONS
  // =========================================================================

  async getGroupPlaces(groupId) {
    return apiClient.get(`${BASE}/groups/${groupId}/places`);
  }

  async addPlace(groupId, placeNameOrObject) {
    const isObject = typeof placeNameOrObject === 'object';

    let latitude = null;
    let longitude = null;
    if (isObject) {
      if (placeNameOrObject.coordinates) {
        latitude = placeNameOrObject.coordinates.latitude || placeNameOrObject.coordinates.lat;
        longitude = placeNameOrObject.coordinates.longitude || placeNameOrObject.coordinates.lng;
      }
      if (!latitude && placeNameOrObject.latitude) latitude = placeNameOrObject.latitude;
      if (!longitude && placeNameOrObject.longitude) longitude = placeNameOrObject.longitude;
    }

    const placeData = isObject ? {
      placeId: placeNameOrObject.id,
      name: placeNameOrObject.place_name || placeNameOrObject.name || placeNameOrObject.restaurant_name,
      latitude,
      longitude,
      address: placeNameOrObject.address || '',
      category: placeNameOrObject.category || 'attraction',
      description: placeNameOrObject.description || placeNameOrObject.ai_summary || '',
      rating: placeNameOrObject.rating || placeNameOrObject.rating_tourist_priority,
      photo_url: placeNameOrObject.photo_url || (placeNameOrObject.photos?.[0]),
      website: placeNameOrObject.website || ''
    } : { name: placeNameOrObject };

    return apiClient.post(`${BASE}/groups/${groupId}/places`, placeData);
  }

  async voteOnPlace(groupId, placeId) {
    return apiClient.post(`${BASE}/groups/${groupId}/places/${placeId}/vote`, { vote_type: 'up' });
  }

  async deletePlace(groupId, placeId) {
    return apiClient.delete(`${BASE}/groups/${groupId}/places/${placeId}`);
  }

  async updatePlaceRemarks(groupId, placeId, remarks) {
    return apiClient.put(`${BASE}/groups/${groupId}/places/${placeId}/remarks`, { remarks });
  }

  async updatePlaceDetails(groupId, placeId, details) {
    return apiClient.patch(`${BASE}/groups/${groupId}/places/${placeId}`, details);
  }

  async updatePlace(groupId, placeId, details) {
    return this.updatePlaceDetails(groupId, placeId, details);
  }

  // =========================================================================
  // EXPENSE GROUP OPERATIONS
  // =========================================================================

  async getExpenseSummary(groupId) {
    return apiClient.get(`${BASE}/groups/${groupId}/expense-summary`);
  }

  async linkExpenseGroup(groupId) {
    return apiClient.post(`${BASE}/groups/${groupId}/link-expense`);
  }

  async unlinkExpenseGroup(groupId) {
    return apiClient.post(`${BASE}/groups/${groupId}/unlink-expense`);
  }

  // =========================================================================
  // EVENTS OPERATIONS
  // =========================================================================

  async getDestinationEvents(destination, options = {}) {
    const params = new URLSearchParams({
      destination,
      limit: options.limit || GlobalConfig.EVENTS_DEFAULT_LIMIT,
      ...(options.startDate && { start_date: options.startDate }),
      ...(options.endDate && { end_date: options.endDate }),
      ...(options.category && { category: options.category })
    });
    return apiClient.get(`${BASE}/events?${params}`);
  }

  // =========================================================================
  // CHECKLIST OPERATIONS
  // =========================================================================

  async addChecklistItem(groupId, itemText) {
    return apiClient.post(`${BASE}/groups/${groupId}/checklist`, { text: itemText });
  }

  async toggleChecklistItem(groupId, itemId) {
    return apiClient.post(`${BASE}/checklist/${itemId}/toggle`, { group_id: groupId });
  }

  async deleteChecklistItem(groupId, itemId) {
    return apiClient.delete(`${BASE}/checklist/${itemId}`);
  }

  async updateChecklistItem(groupId, itemId, updates) {
    return apiClient.put(`${BASE}/checklist/${itemId}`, updates);
  }

  // =========================================================================
  // ADDITIONAL OPERATIONS
  // =========================================================================

  async removeMember(groupId, userId) {
    return apiClient.delete(`${BASE}/groups/${groupId}/members/${userId}`);
  }

  async updateMemberRole(groupId, memberId, role) {
    return apiClient.patch(`${BASE}/groups/${groupId}/members/${memberId}/role`, { role });
  }

  async leaveGroup(groupId) {
    return apiClient.post(`${BASE}/groups/${groupId}/leave`);
  }

  async getGroupPolls(groupId) {
    return apiClient.get(`${BASE}/groups/${groupId}/polls`);
  }

  async updateBudget(groupId, budget) {
    return apiClient.patch(`${BASE}/groups/${groupId}/budget`, { estimated_budget: budget });
  }

  async getInvitationDetails(invitationId) {
    return apiClient.get(`${BASE}/invitations/${invitationId}`);
  }

  // =========================================================================
  // CHECKLIST LIST
  // =========================================================================

  async getGroupChecklist(groupId) {
    return apiClient.get(`${BASE}/groups/${groupId}/checklist?per_page=100`);
  }

  // =========================================================================
  // ACTIVITIES
  // =========================================================================

  async getGroupActivities(groupId) {
    return apiClient.get(`${BASE}/groups/${groupId}/activities?per_page=50`);
  }

  // =========================================================================
  // VAULT (PDF / FILE UPLOAD)
  // =========================================================================

  async getVaultFiles(groupId) {
    return apiClient.get(`${BASE}/groups/${groupId}/vault`);
  }

  async uploadVaultFile(groupId, file) {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`${BASE}/groups/${groupId}/vault`, formData);
  }

  async deleteVaultFile(groupId, docId) {
    return apiClient.delete(`${BASE}/groups/${groupId}/vault/${docId}`);
  }

  // =========================================================================
  // DESTINATION LIBRARY (from places search DB)
  // =========================================================================

  async searchDestinationPlaces(destination, limit = 30) {
    const params = new URLSearchParams({ q: destination, limit, sort_by: 'rank_score', sort_order: 'desc' });
    return apiClient.get(`/v1/places/search?${params}`);
  }

  // =========================================================================
  // AI CREW AGENT
  // =========================================================================

  async confirmCrewAction(groupId, payload) {
    return apiClient.post(`${BASE}/groups/${groupId}/ai/confirm`, payload);
  }

}

const groupPlannerApi = new GroupPlannerApiService();
export default groupPlannerApi;
