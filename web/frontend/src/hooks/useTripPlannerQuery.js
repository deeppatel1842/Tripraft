import { useQuery, useMutation } from '@tanstack/react-query';
import tripPlannerService from '../services/tripPlannerService';

// Cache key factory
export const tripKeys = {
  all:       ['trip-planner'],
  cities:    (query) => [...tripKeys.all, 'cities', query],
  cityList:  (options) => [...tripKeys.all, 'city-list', options],
  pacing:    () => [...tripKeys.all, 'pacing'],
  trip:      (params) => [...tripKeys.all, 'trip', params],
};

export function useCitySearch(query, limit = 10) {
  return useQuery({
    queryKey: tripKeys.cities(query),
    queryFn: () => tripPlannerService.searchCities(query, limit),
    enabled: !!query && query.length >= 2,
    staleTime: 5 * 60_000,
    placeholderData: (prev) => prev,
  });
}

export function useCities(options = {}) {
  return useQuery({
    queryKey: tripKeys.cityList(options),
    queryFn: () => tripPlannerService.getCities(options),
    staleTime: 10 * 60_000,
  });
}

export function usePacingOptions() {
  return useQuery({
    queryKey: tripKeys.pacing(),
    queryFn: () => tripPlannerService.getPacingOptions(),
    staleTime: Infinity,
  });
}

export function useGenerateTrip() {
  return useMutation({
    mutationFn: (params) => tripPlannerService.generateTrip(params),
  });
}
