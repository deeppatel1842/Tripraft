/**
 * SearchComponent Example - Using Client-Side Search
 * 
 * This component demonstrates how to use the new client-side search approach:
 * - Loads all data once (1 Firebase read)
 * - All searches are instant (0 reads)
 * - Perfect for autocomplete and instant search
 */

import React, { useState, useMemo } from 'react';
import useClientSideSearch from '../hooks/useClientSideSearch';

const SearchComponent = () => {
  const [query, setQuery] = useState('');
  const { search, autocomplete, isLoading, error, data } =
    useClientSideSearch();

  // Get autocomplete suggestions as user types (instant, 0 reads)
  const suggestions = useMemo(
    () => (query.length >= 2 ? autocomplete(query, 10) : []),
    [query, autocomplete]
  );

  const handleSearch = (e) => {
    const value = e.target.value;
    setQuery(value);
  };

  if (isLoading) {
    return (
      <div className="p-4">
        <p className="text-gray-600">📥 Loading places data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <p className="text-red-600">❌ Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-4">🔍 Smart Place Search</h1>
        <p className="text-gray-600 mb-4">
          Loaded {data?.countries.length} countries, {data?.cities.length}{' '}
          cities, {data?.places.length} places - Now searching is instant (0 Firebase reads)!
        </p>

        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={handleSearch}
            placeholder="Search places, cities, countries... (e.g., 'taj mahal', 'agra', 'india')"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
          />

          {/* Autocomplete dropdown */}
          {suggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
              {suggestions.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => setQuery(item.name)}
                  className="w-full text-left px-4 py-2 hover:bg-gray-100 flex justify-between items-center border-b last:border-b-0"
                >
                  <span>
                    <span className="font-medium">{item.name}</span>
                    <span className="text-gray-500 text-sm ml-2">
                      {item._category === 'place'
                        ? `📍 Place in ${item.city}, ${item.country}`
                        : item._category === 'city'
                        ? `🏙️ City in ${item.country}`
                        : `🌍 Country`}
                    </span>
                  </span>
                  {item.rank_score && (
                    <span className="text-xs text-gray-400">
                      ⭐ {item.rank_score}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Stats */}
      {query.length >= 2 && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-900">
            ⚡ <strong>Zero Firebase reads!</strong> Found {suggestions.length}{' '}
            instant suggestions for "{query}"
          </p>
        </div>
      )}

      {/* Results */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Results</h2>
        {suggestions.length > 0 ? (
          <div className="grid gap-3">
            {suggestions.map((item, idx) => (
              <div
                key={idx}
                className="p-3 border border-gray-200 rounded-lg hover:shadow-md transition"
              >
                <div className="flex justify-between items-start mb-1">
                  <h3 className="font-semibold text-lg">{item.name}</h3>
                  <span className="text-xs font-medium px-2 py-1 bg-gray-100 rounded">
                    {item._category}
                  </span>
                </div>

                {item._category === 'place' && (
                  <div className="text-sm text-gray-600">
                    <p>
                      📍 {item.city}, {item.state}, {item.country}
                    </p>
                    {item.rank_score && (
                      <p>
                        ⭐ Rank: <strong>{item.rank_score}</strong>
                      </p>
                    )}
                  </div>
                )}

                {item._category === 'city' && (
                  <div className="text-sm text-gray-600">
                    <p>
                      🏙️ {item.state}, {item.country}
                    </p>
                    <p>{item.place_count} top places</p>
                  </div>
                )}

                {item._category === 'country' && (
                  <div className="text-sm text-gray-600">
                    <p>🌍 {item.code}</p>
                    <p>{item.place_count} places, {item.state_count} states</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : query.length >= 2 ? (
          <p className="text-gray-500">No results found</p>
        ) : (
          <p className="text-gray-400 italic">Type at least 2 characters to search</p>
        )}
      </div>

      {/* Performance info */}
      <div className="mt-8 p-4 bg-gray-50 rounded-lg text-sm text-gray-600">
        <h3 className="font-semibold mb-2">📊 Performance</h3>
        <ul className="space-y-1">
          <li>✅ Initial load: 1 Firebase read + data cached</li>
          <li>✅ Every search: 0 Firebase reads</li>
          <li>✅ Autocomplete: &lt;50ms response time</li>
          <li>✅ Works offline with cached data</li>
          <li>✅ Cache valid for 24 hours</li>
        </ul>
      </div>
    </div>
  );
};

export default SearchComponent;
