// Purpose: Sends web API requests with cookie credentials, CSRF headers, response handling and cancellation.
/** Cookie-authenticated HTTP requests with GET-only retries. */
import GlobalConfig from '../config/globalConfig';
import sqlAuthService from '../services/sqlAuthService';
import apiLogger from './apiLogger';

export class APIClient {
  constructor() {
    this.baseURL = GlobalConfig.API_BASE_URL;
    this.maxRetries = GlobalConfig.API_MAX_RETRIES ?? 2;
    this.timeout = GlobalConfig.API_TIMEOUT || 30000;
  }

  _getCookie(name) {
    const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }

  async request(method, endpoint, options = {}) {
    const url = this.baseURL + endpoint;
    const { body, headers, signal: externalSignal, timeout = this.timeout,
      responseType = 'json', _retried401, ...fetchOptions } = options;
    const authHeaders = {};
    const token = await sqlAuthService.getIdToken();
    if (token) authHeaders.Authorization = 'Bearer ' + token;
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      const csrfToken = this._getCookie('csrf_token');
      if (csrfToken) authHeaders['X-CSRF-Token'] = csrfToken;
    }
    const attempts = method === 'GET' ? this.maxRetries + 1 : 1;
    let lastError;
    for (let attempt = 1; attempt <= attempts; attempt++) {
      const controller = new AbortController();
      const abort = () => controller.abort();
      if (externalSignal?.aborted) abort();
      externalSignal?.addEventListener('abort', abort, { once: true });
      const timer = setTimeout(abort, timeout);
      try {
        const multipart = typeof FormData !== 'undefined' && body instanceof FormData;
        const response = await fetch(url, {
          ...fetchOptions, method, credentials: 'include', signal: controller.signal,
          headers: { ...(multipart ? {} : { 'Content-Type': 'application/json' }), ...authHeaders, ...headers },
          body: body == null ? undefined : (multipart ? body : JSON.stringify(body)),
        });
        let data;
        if (response.ok && responseType === 'blob') {
          data = await response.blob();
        } else {
          const text = response.status === 204 || method === 'HEAD' ? '' : await response.text();
          if (!text.trim()) data = null;
          else if ((response.headers.get('content-type') || '').includes('json')) {
            try { data = JSON.parse(text); }
            catch {
              if (response.ok) throw Object.assign(new Error('The server returned invalid JSON'), { status: 502 });
              data = { message: 'Request failed with status ' + response.status };
            }
          } else data = { message: response.ok ? text : 'Request failed with status ' + response.status };
        }
        if (!response.ok) {
          if (response.status >= 500 && method === 'GET' && attempt < attempts) {
            lastError = Object.assign(new Error(data?.message || 'Server error'), { status: response.status });
          } else if (response.status === 401 && !_retried401) {
            const refreshed = await sqlAuthService.refreshAccessToken();
            if (refreshed.success) return this.request(method, endpoint, { ...options, _retried401: true });
            throw Object.assign(new Error(data?.message || 'Please sign in again'), { status: 401, data });
          } else {
            throw Object.assign(new Error(data?.error?.message || data?.message || (typeof data?.error === 'string' ? data.error : null) || 'Request failed with status ' + response.status), {
              status: response.status, errors: data?.errors || null, data,
            });
          }
        } else return data;
      } catch (error) {
        if (controller.signal.aborted) {
          throw Object.assign(new Error(externalSignal?.aborted ? 'Request aborted' : 'Request timed out'), { status: 0 });
        }
        if (error.status) throw error;
        lastError = error;
        apiLogger.logError(method, url, error);
        if (method !== 'GET' || attempt === attempts) throw Object.assign(error, { status: 0 });
      } finally {
        clearTimeout(timer);
        externalSignal?.removeEventListener('abort', abort);
      }
      if (externalSignal?.aborted) throw Object.assign(new Error('Request aborted'), { status: 0 });
      await new Promise(resolve => setTimeout(resolve, 2 ** (attempt - 1) * (GlobalConfig.RETRY_BACKOFF_BASE_MS || 500)));
    }
    throw lastError || new Error('Network error');
  }
  get(endpoint, options = {}) { return this.request('GET', endpoint, options); }
  post(endpoint, body, options = {}) { return this.request('POST', endpoint, { ...options, body }); }
  put(endpoint, body, options = {}) { return this.request('PUT', endpoint, { ...options, body }); }
  delete(endpoint, options = {}) { return this.request('DELETE', endpoint, options); }
  patch(endpoint, body, options = {}) { return this.request('PATCH', endpoint, { ...options, body }); }
}
export default new APIClient();
