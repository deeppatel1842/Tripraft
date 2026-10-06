// Purpose: Regression tests for access, including success and failure behavior.
import React from 'react';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
const mockGet = jest.fn();
jest.mock('@tripraft/api-client', () => ({ createApiClient: () => ({ GET: (...args) => mockGet(...args) }) }));
import { App } from '../src/App';

afterEach(() => { cleanup(); mockGet.mockReset(); });
const identity = is_admin => ({ data: { data: { user: { id: '019af385-ff28-7000-8000-000000000001', email: 'ops@example.test', is_admin } } }, response: { ok: true, status: 200 } });
test('waits for identity before requesting privileged operations', async () => {
  let resolve;
  mockGet.mockImplementation(() => new Promise(done => { resolve = done; }));
  render(<App />);
  expect(screen.getByRole('status')).toHaveTextContent('Checking account');
  expect(mockGet).toHaveBeenCalledTimes(1);
  resolve(identity(false));
  expect(await screen.findByRole('alert')).toHaveTextContent('does not have administrator access');
  expect(mockGet).toHaveBeenCalledTimes(1);
});
test('requires sign-in on rejected authentication and makes no audit request', async () => {
  mockGet.mockResolvedValue({ response: { ok: false, status: 401 } });
  render(<App />);
  expect(await screen.findByRole('link', { name: 'Sign in to TripRaft' })).toHaveAttribute('href', 'http://localhost:5173/login');
  expect(mockGet).toHaveBeenCalledTimes(1);
});
test('renders degraded readiness from a 503 and an honest audit failure', async () => {
  mockGet.mockImplementation(path => Promise.resolve(path.endsWith('/me') ? identity(true) : path.endsWith('/ready') ? { error: { status: 'degraded', timestamp: '2026-10-05', checks: { database: { status: 'unhealthy' } } }, response: { status: 503 } } : { response: { ok: false, status: 500 } }));
  render(<App />);
  expect(await screen.findByText('Status: degraded')).toBeInTheDocument();
  expect(screen.getByText('database: unhealthy')).toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent('Ingestion audit records are unavailable');
  await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(3));
});
