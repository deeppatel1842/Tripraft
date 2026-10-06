// Purpose: Regression tests for p3 Behavior, including success and failure behavior.
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
jest.mock('../services/sqlAuthService', () => ({ __esModule: true, default: { onAuthStateChanged: jest.fn() } }));
jest.mock('../services/expenseApi', () => ({ __esModule: true, default: {} }));
jest.mock('../lib/queryClientPersist', () => ({ clearPersistedCache: jest.fn() }));
jest.mock('../features/trips/hooks/useMapRenderer', () => ({ __esModule: true, default: jest.fn() }));
import auth from '../services/sqlAuthService';
import { AuthProvider, useAuth } from '../context/AuthContext';
import useLeaflet from '../features/trips/hooks/useMapRenderer';
import MapPanel from '../features/trips/jsx/map/MapPanel';
import { CrewQuestionCard } from '../features/scout/CrewCards';
import { formatDate, formatFileSize } from '../features/trips/utils/formatters';

afterEach(() => { delete window.L; });

it.each([null, undefined, '', 'not-a-date', new Date(NaN)])('formats absent/invalid dates without throwing or displaying Invalid Date: %s', value => {
  expect(formatDate(value)).toBe('');
});
it.each([new Date(2026, 9, 5), new Date(2026, 9, 5).getTime()])('formats Date objects and timestamps: %s', value => {
  expect(formatDate(value)).toBe('Oct 5, 2026');
});
it.each([[-50, '0 B'], [0, '0 B'], [1024, '1.0 KB']])('formats file size %s as %s', (value, expected) => {
  expect(formatFileSize(value)).toBe(expected);
});

function Initials() {
  const { getUserInitials, loading } = useAuth();
  return <output data-testid="initials">{loading ? 'loading' : getUserInitials()}</output>;
}
it.each([
  [{ displayName: '   ', email: 'alice@example.test' }, 'AL'],
  [{ displayName: '   ', email: null }, ''],
  [{ displayName: 123, email: null }, '12'],
  [{ displayName: '  Alice   Smith  ', email: null }, 'AS'],
])('handles profile initials for %j', async (profile, expected) => {
  auth.onAuthStateChanged.mockImplementation(callback => {
    callback({ uid: 'user-uuid', ...profile, getIdToken: async () => null });
    return () => {};
  });
  const client = new QueryClient();
  render(<QueryClientProvider client={client}><AuthProvider><Initials /></AuthProvider></QueryClientProvider>);
  await waitFor(() => expect(screen.getByTestId('initials').textContent).toBe(expected));
  client.clear();
});

it('resets custom answer mode and text when the Crew question changes', () => {
  const props = { onAnswer: jest.fn(), question: 'Where?', options: [] };
  const { rerender } = render(<CrewQuestionCard {...props} />);
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Old answer' } });
  rerender(<CrewQuestionCard {...props} question="When?" options={['Today']} />);
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Custom' }));
  expect(screen.getByRole('textbox')).toHaveValue('');
});
it('opens custom answer input on a later Crew step without preset choices', () => {
  const onAnswer = jest.fn();
  render(<CrewQuestionCard onAnswer={onAnswer} allFields={[
    { field: 'day', question: 'When?', options: ['Today'] },
    { field: 'place', question: 'Where?', options: [] },
  ]} />);
  fireEvent.click(screen.getByRole('button', { name: 'Today' }));
  expect(screen.getByRole('textbox')).toBeInTheDocument();
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Paris' } });
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter' });
  expect(onAnswer).toHaveBeenCalledWith('__crew_fields__:' + JSON.stringify({ day: 'Today', place: 'Paris' }));
});

const mapProps = {
  group: { id: 'group-uuid', destination_lat: 5, destination_lng: 5 }, places: [],
  filteredLibrary: [], activeTab: 'itinerary', mapDay: 'all', uniqueDates: [],
  dayNumbers: Array.from({ length: 14 }, (_, i) => i + 1), onMapDayChange: jest.fn(),
};
it('exposes and selects all days of a trip longer than five days', () => {
  useLeaflet.mockReturnValue(false);
  render(<MapPanel {...mapProps} />);
  fireEvent.click(screen.getByRole('button', { name: 'Day 14' }));
  expect(mapProps.onMapDayChange).toHaveBeenCalledWith('14');
});
it('re-centers an existing map when the destination changes to zero coordinates', () => {
  useLeaflet.mockReturnValue(true);
  const map = { remove: jest.fn(), setView: jest.fn(), fitBounds: jest.fn() };
  const layers = { clearLayers: jest.fn() };
  window.L = {
    map: jest.fn(() => map), tileLayer: () => ({ addTo: jest.fn() }),
    layerGroup: () => ({ addTo: () => layers }),
  };
  const { rerender } = render(<MapPanel {...mapProps} />);
  rerender(<MapPanel {...mapProps} group={{ ...mapProps.group, destination_lat: 0, destination_lng: 0 }} />);
  expect(map.setView).toHaveBeenLastCalledWith([0, 0], expect.any(Number));
});
