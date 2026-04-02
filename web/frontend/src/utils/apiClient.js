/**
 * API Client — Production-grade HTTP client
 * Single source for all backend communication.
 *
 * - Auth interceptor: auto-attaches JWT from sqlAuthService
 * - Credentials: sends httpOnly cookies on every request
 * - Timeout: configurable via GlobalConfig.API_TIMEOUT
 * - AbortController: accepts external signal for caller-driven cancellation
 * - Retry: 5xx responses on GET-only, exponential backoff, max 2 retries
 * - Errors: throws Error instances with status/message/errors/data properties
 */

import GlobalConfig from '../config/globalConfig';
import sqlAuthService from '../services/sqlAuthService';
import apiLogger from './apiLogger';

class APIClient {
  constructor() {
    this.baseURL = GlobalConfig.API_BASE_URL;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
    this.maxRetries = GlobalConfig.API_MAX_RETRIES || 2;
    this.timeout = GlobalConfig.API_TIMEOUT || 30000;
  }

  _getCookie(name) {
    const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }

  async request(method, endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const startTime = performance.now();

    apiLogger.logRequest(method, url, options.body);

    const { body, headers, signal: externalSignal, ...restOptions } = options;

    // Auth interceptor: get fresh token from sqlAuthService
    const authHeaders = {};
    try {
      const token = await sqlAuthService.getIdToken();
      if (token) {
        authHeaders['Authorization'] = `Bearer ${token}`;
      }
    } catch (_) {
      // No token available, proceed unauthenticated
    }

    // CSRF double-submit: read csrf_token cookie and send as header on mutating requests
    const csrfHeaders = {};
    if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
      const csrfToken = this._getCookie('csrf_token');
      if (csrfToken) {
        csrfHeaders['X-CSRF-Token'] = csrfToken;
      }
    }

    const maxAttempts = method === 'GET' ? this.maxRetries + 1 : 1;
    let lastError;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      // Fresh AbortController per attempt (timeout resets on retry)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      // Link caller's signal if provided
      if (externalSignal) {
        if (externalSignal.aborted) {
          clearTimeout(timeoutId);
          controller.abort();
        } else {
          externalSignal.addEventListener('abort', () => {
            clearTimeout(timeoutId);
            controller.abort();
          }, { once: true });
        }
      }

      try {
        const isFormData = body instanceof FormData;
        const mergedHeaders = {
          ...(isFormData ? {} : this.defaultHeaders),
          ...authHeaders,
          ...csrfHeaders,
          ...headers,
        };

        const response = await fetch(url, {
          method,
          headers: mergedHeaders,
          body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
          credentials: 'include',
          signal: controller.signal,
          ...restOptions,
        });

        clearTimeout(timeoutId);

        const duration = performance.now() - startTime;
        const data = await response.json();
        apiLogger.logResponse(method, url, response.status, data, duration);

        if (!response.ok) {
          // Retry on 5xx for GET requests
          if (response.status >= 500 && method === 'GET' && attempt < maxAttempts) {
            const delay = Math.pow(2, attempt - 1) * GlobalConfig.RETRY_BACKOFF_BASE_MS;
            await new Promise(r => setTimeout(r, delay));
            continue;
          }

          // On 401, attempt a token refresh and retry once
          if (response.status === 401 && !options._retried401) {
            const refreshResult = await sqlAuthService.refreshAccessToken();
            if (refreshResult.success) {
              return this.request(method, endpoint, { ...options, _retried401: true });
            }
          }

          const error = new Error(data.message || `Request failed with status ${response.status}`);
          error.status = response.status;
          error.errors = data.errors || null;
          error.data = data;
          throw error;
        }

        return data;
      } catch (error) {
        clearTimeout(timeoutId);

        // Already a formatted API error — rethrow
        if (error.status) {
          throw error;
        }

        // AbortError from timeout or caller signal
        if (error.name === 'AbortError') {
          const abortError = new Error(
            externalSignal?.aborted ? 'Request aborted' : 'Request timed out'
          );
          abortError.status = 0;
          throw abortError;
        }

        // Network error — retry on GET
        const duration = performance.now() - startTime;
        apiLogger.logError(method, url, error, duration);
        lastError = error;

        if (method === 'GET' && attempt < maxAttempts) {
          const delay = Math.pow(2, attempt - 1) * GlobalConfig.RETRY_BACKOFF_BASE_MS;
          await new Promise(r => setTimeout(r, delay));
          continue;
        }
      }
    }

    // All retries exhausted
    const networkError = new Error(lastError?.message || 'Network error');
    networkError.status = 0;
    throw networkError;
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
