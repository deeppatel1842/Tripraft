/**
 * API Client with Enhanced Logging
 * Centralized API communication with request/response logging
 */

import GlobalConfig from '../config/globalConfig';
import apiLogger from './apiLogger';

class APIClient {
  constructor() {
    this.baseURL = GlobalConfig.API_BASE_URL;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  async request(method, endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const startTime = performance.now();

    // Log request
    apiLogger.logRequest(method, url, options.body);

    // Extract body and headers separately to avoid spread issues
    const { body, headers, ...restOptions } = options;

    try {
      const response = await fetch(url, {
        method,
        headers: {
          ...this.defaultHeaders,
          ...headers,
        },
        body: body ? JSON.stringify(body) : undefined,
        ...restOptions,
      });

      const duration = performance.now() - startTime;
      const data = await response.json();

      // Log response
      apiLogger.logResponse(method, url, response.status, data, duration);

      if (!response.ok) {
        throw {
          response: {
            status: response.status,
            data: data,
          },
          message: data.message || 'Request failed',
        };
      }

      return data;
    } catch (error) {
      const duration = performance.now() - startTime;
      apiLogger.logError(method, url, error, duration);
      throw error;
    }
  }

  get(endpoint, options = {}) {
    return this.request('GET', endpoint, options);
  }

  post(endpoint, body, options = {}) {
    return this.request('POST', endpoint, { ...options, body });
  }

  put(endpoint, body, options = {}) {
    return this.request('PUT', endpoint, { ...options, body });
  }

  delete(endpoint, options = {}) {
    return this.request('DELETE', endpoint, options);
  }

  patch(endpoint, body, options = {}) {
    return this.request('PATCH', endpoint, { ...options, body });
  }
}

export default new APIClient();
