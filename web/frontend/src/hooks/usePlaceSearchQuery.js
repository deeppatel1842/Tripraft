import { useQuery } from '@tanstack/react-query';
import { searchPlaces, getPlaceDetails, getStats } from '../services/placeSearchService';

// Cache key factory
export const placeKeys = {
  all:     ['places'],
  search:  (params) => [...placeKeys.all, 'search', params],
  detail:  (id) => [...placeKeys.all, 'detail', id],
  stats:   () => [...placeKeys.all, 'stats'],
};

export function usePlaceSearch(query, options = {}) {
  return useQuery({
    queryKey: placeKeys.search({ query, ...options }),
    queryFn: () => searchPlaces(query, options),
    enabled: !!query && query.length >= 2,
    staleTime: 5 * 60_000,
    placeholderData: (prev) => prev,
  });
}

export function usePlaceDetail(placeId) {
  return useQuery({
    queryKey: placeKeys.detail(placeId),
    queryFn: () => getPlaceDetails(placeId),
    enabled: !!placeId,
    staleTime: 10 * 60_000,
  });
}

export function usePlaceStats() {
  return useQuery({
    queryKey: placeKeys.stats(),
    queryFn: getStats,
    staleTime: Infinity,
  });
}
