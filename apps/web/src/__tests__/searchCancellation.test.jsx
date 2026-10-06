// Purpose: Regression tests for search Cancellation, including success and failure behavior.
import React, { useState } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
jest.mock('../services/placeSearchService', () => ({ getAutocompleteSuggestions: jest.fn() }));
jest.mock('../features/discover/jsx/SearchSuggestions', () => ({
  __esModule: true,
  default: ({ suggestions }) => <div>{suggestions.map(s => <span key={s.name}>{s.name}</span>)}</div>,
}));
import { getAutocompleteSuggestions } from '../services/placeSearchService';
import SearchBar from '../features/discover/jsx/SearchBar';

function Search() {
  const [value, setValue] = useState('');
  return <SearchBar value={value} onChange={setValue} onSearch={jest.fn()} />;
}
beforeEach(() => jest.useFakeTimers());
afterEach(() => jest.useRealTimers());

it('ignores an old response received before the next query debounce fires', async () => {
  let resolve;
  getAutocompleteSuggestions.mockReturnValue(new Promise(r => { resolve = r; }));
  render(<Search />);
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Paris' } });
  act(() => jest.advanceTimersByTime(300));
  const signal = getAutocompleteSuggestions.mock.calls[0][2].signal;
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Tokyo' } });
  expect(signal.aborted).toBe(true);
  await act(async () => resolve([{ name: 'Stale Paris' }]));
  expect(screen.queryByText('Stale Paris')).not.toBeInTheDocument();
});

it('cancels a pending debounce when the user clears the search', () => {
  render(<Search />);
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Paris' } });
  fireEvent.click(screen.getByRole('button', { name: 'Clear search' }));
  act(() => jest.advanceTimersByTime(300));
  expect(getAutocompleteSuggestions).not.toHaveBeenCalled();
  expect(screen.getByRole('textbox')).toHaveValue('');
});
