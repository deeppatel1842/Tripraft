// Purpose: Provides index logic and exports for packages\api-client\src.
import createClient from 'openapi-fetch';
import type { paths } from './generated/schema';
export type { paths, components } from './generated/schema';
export type { ApiEnvelope, AuthUser, HealthStatus, UUID } from '@tripraft/types';

/** Cookie credentials remain in httpOnly cookies; requests are never replayed. */
export function createApiClient(baseUrl = '') {
  const client = createClient<paths>({ baseUrl, credentials: 'include' });
  client.use({
    onRequest({ request }) {
      if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method) && typeof document !== 'undefined') {
        const csrf = document.cookie.split('; ').find((value) => value.startsWith('csrf_token='));
        if (csrf)
          request.headers.set('X-CSRF-Token', decodeURIComponent(csrf.slice('csrf_token='.length)));
      }
      return request;
    },
  });
  return client;
}
