// Purpose: Renders the admin console with initialized server-account authorization, readiness and ingestion audit results.
import { useEffect, useState } from 'react';
import { createApiClient, type components } from '@tripraft/api-client';
import type { AuthUser } from '@tripraft/types';
const api = createApiClient(import.meta.env.VITE_API_BASE_URL || '');
type Audit = components['schemas']['AuditData'];
type Health = components['schemas']['Health'];
function isHealth(value: unknown): value is Health {
  if (!value || typeof value !== 'object') return false;
  const health = value as Record<string, unknown>;
  if (typeof health.status !== 'string' || typeof health.timestamp !== 'string') return false;
  if (health.checks !== undefined) {
    if (!health.checks || typeof health.checks !== 'object' || Array.isArray(health.checks))
      return false;
    if (
      !Object.values(health.checks).every(
        (check) =>
          check &&
          typeof check === 'object' &&
          typeof (check as Record<string, unknown>).status === 'string',
      )
    )
      return false;
  }
  return true;
}
export function App() {
  const [account, setAccount] = useState<AuthUser | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [accountError, setAccountError] = useState('');
  const [health, setHealth] = useState<Health | null>(null);
  const [audit, setAudit] = useState<Audit | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api
      .GET('/api/v1/auth/me', { signal: controller.signal })
      .then(({ data, response }) => {
        if (controller.signal.aborted) return;
        if (!response.ok || !data?.data?.user)
          setAccountError(
            response.status === 401
              ? 'Sign in with your TripRaft account to continue.'
              : 'Unable to verify your account.',
          );
        else setAccount(data.data.user);
      })
      .catch(() => {
        if (!controller.signal.aborted) setAccountError('Unable to reach the API.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setInitializing(false);
      });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!account?.is_admin) return;
    const controller = new AbortController();
    setRefreshing(true);
    setErrors([]);
    setHealth(null);
    setAudit(null);
    Promise.allSettled([
      api.GET('/api/health/ready', { signal: controller.signal }),
      api.GET('/api/v1/admin/audit', {
        params: { query: { limit: 25, offset: 0 } },
        signal: controller.signal,
      }),
    ]).then(([healthResult, auditResult]) => {
      if (controller.signal.aborted) return;
      const failures: string[] = [];
      const readiness =
        healthResult.status === 'fulfilled'
          ? healthResult.value.data || healthResult.value.error
          : null;
      if (isHealth(readiness)) setHealth(readiness);
      else failures.push('Readiness check failed.');
      if (auditResult.status === 'fulfilled' && auditResult.value.data?.data)
        setAudit(auditResult.value.data.data);
      else failures.push('Ingestion audit records are unavailable.');
      setErrors(failures);
      setRefreshing(false);
    });
    return () => controller.abort();
  }, [account, revision]);
  return (
    <main>
      <header>
        <p className="eyebrow">TripRaft</p>
        <h1>Operations</h1>
      </header>
      {initializing ? (
        <p role="status">Checking account…</p>
      ) : !account ? (
        <section>
          <p role="alert">{accountError}</p>
          <a href={`${import.meta.env.VITE_WEB_URL || 'http://localhost:5173'}/login`}>
            Sign in to TripRaft
          </a>
        </section>
      ) : !account.is_admin ? (
        <p role="alert">This account does not have administrator access.</p>
      ) : (
        <>
          <div className="toolbar">
            <p>Signed in as {account.email}</p>
            <button disabled={refreshing} onClick={() => setRevision((value) => value + 1)}>
              {refreshing ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
          {errors.map((error) => (
            <p role="alert" key={error}>
              {error}
            </p>
          ))}
          <section>
            <h2>Service readiness</h2>
            {health ? (
              <>
                <p>Status: {health.status}</p>
                <ul>
                  {Object.entries(health.checks || {}).map(([name, check]) => (
                    <li key={name}>
                      {name}: {check.status}
                      {check.note ? ` — ${check.note}` : ''}
                    </li>
                  ))}
                </ul>
                <small>Checked {health.timestamp}</small>
              </>
            ) : (
              <p>{refreshing ? 'Loading…' : 'No readiness result available.'}</p>
            )}
          </section>
          <section>
            <h2>Recent ingestion activity</h2>
            {audit ? (
              <>
                <p>{audit.total} records in total; showing the latest 25.</p>
                {audit.logs.length ? (
                  <div className="scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Time</th>
                          <th>Entity</th>
                          <th>Action</th>
                          <th>Actor</th>
                        </tr>
                      </thead>
                      <tbody>
                        {audit.logs.map((row, index) => (
                          <tr key={String(row.id ?? index)}>
                            <td>{row.created_at || 'Unknown'}</td>
                            <td>{row.entity_type || 'Unknown'}</td>
                            <td>{row.action || 'Unknown'}</td>
                            <td>{row.ingested_by || 'Unknown'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p>No ingestion activity recorded.</p>
                )}
              </>
            ) : (
              <p>{refreshing ? 'Loading…' : 'No audit result available.'}</p>
            )}
          </section>
        </>
      )}
    </main>
  );
}
