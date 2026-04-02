/**
 * Chat API Service
 * REST endpoints for group chat messaging.
 * Uses apiClient for auth, retry, and error handling.
 */

import apiClient from '../utils/apiClient';
import GlobalConfig from '../config/globalConfig';

const BASE = GlobalConfig.ENDPOINTS.GROUP_PLANNER;

class ChatApiService {
  /**
   * Get messages with cursor pagination.
   * @param {number} groupId
   * @param {object} opts - { beforeId, limit }
   */
  async getMessages(groupId, { beforeId, limit = 50 } = {}) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (beforeId) params.set('before_id', String(beforeId));
    return apiClient.get(`${BASE}/groups/${groupId}/messages?${params}`);
  }

  /**
   * Send a message.
   * @param {number} groupId
   * @param {object} payload - { content, type?, metadata_json?, parent_message_id? }
   */
  async sendMessage(groupId, payload) {
    return apiClient.post(`${BASE}/groups/${groupId}/messages`, payload);
  }

  /**
   * Soft-delete a message.
   * @param {number} messageId
   */
  async deleteMessage(messageId) {
    return apiClient.delete(`${BASE}/messages/${messageId}`);
  }

  /**
   * Mark messages as read up to messageId.
   * @param {number} groupId
   * @param {number} messageId
   */
  async markRead(groupId, messageId) {
    return apiClient.post(`${BASE}/groups/${groupId}/messages/read`, {
      last_read_message_id: messageId,
    });
  }

  /**
   * Get unread count for the current user.
   * @param {number} groupId
   */
  async getUnreadCount(groupId) {
    return apiClient.get(`${BASE}/groups/${groupId}/unread-count`);
  }
}

const chatApi = new ChatApiService();
export default chatApi;
