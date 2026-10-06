// Purpose: Provides ai Consent Api logic and exports for apps\web\src\services.
/**
 * AI Consent API Service
 * REST endpoints for Scout consent management.
 */

import apiClient from '../utils/apiClient';
import GlobalConfig from '../config/globalConfig';

const BASE = GlobalConfig.ENDPOINTS.GROUP_PLANNER;

class AiConsentApiService {
  /**
   * Get current user's consent status for a group.
   * @param {string} groupId
   * @returns {Promise<{data: {allowed: boolean, needs_prompt: boolean, consented_member_count: number}}>}
   */
  async getConsent(groupId) {
    return apiClient.get(`${BASE}/groups/${groupId}/ai/consent`);
  }

  /**
   * Grant or decline consent.
   * @param {string} groupId
   * @param {object} payload - { granted: boolean }
   */
  async submitConsent(groupId, { granted }) {
    return apiClient.post(`${BASE}/groups/${groupId}/ai/consent`, {
      action: granted ? 'grant' : 'decline',
    });
  }

  /**
   * Revoke consent and delete preference data ("forget me").
   * @param {string} groupId
   */
  async revokeConsent(groupId) {
    return apiClient.delete(`${BASE}/groups/${groupId}/ai/consent`);
  }
}

const aiConsentApi = new AiConsentApiService();
export default aiConsentApi;
