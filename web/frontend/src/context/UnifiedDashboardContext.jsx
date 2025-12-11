/**
 * Unified Dashboard Context - Phase 20
 * 
 * Single context for BOTH Expense Engine and Group Planner
 * Target: 10 total Firestore operations per session
 * 
 * Architecture:
 * - 1 READ on login (unified dashboard)
 * - 1 WRITE per mutation (batched)
 * - 0 ops on refresh (from cache)
 */

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';

// API Configuration
const API_BASE = process.env.REACT_APP_API_URL || '';
const EXPENSE_API = `${API_BASE}/api/expense/v2`;
const GROUP_PLANNER_API = `${API_BASE}/api/group-planner/v2`;

// Cache keys
const CACHE_KEYS = {
  EXPENSE_DASHBOARD: 'expense_dashboard_v2',
  GROUP_PLANNER_DASHBOARD: 'group_planner_dashboard_v2',
  PLACES_CACHE: 'places_cache_v2',
  LAST_SYNC: 'dashboard_last_sync',
};

// Cache TTL
const CACHE_TTL = 10 * 60 * 1000; // 10 minutes
const PLACES_CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours

const UnifiedDashboardContext = createContext(null);

export const useUnifiedDashboard = () => {
  const context = useContext(UnifiedDashboardContext);
  if (!context) {
    throw new Error('useUnifiedDashboard must be used within UnifiedDashboardProvider');
  }
  return context;
};

export const UnifiedDashboardProvider = ({ children }) => {
  const { user, getIdToken } = useAuth();
  
  // State
  const [expenseDashboard, setExpenseDashboard] = useState(null);
  const [groupPlannerDashboard, setGroupPlannerDashboard] = useState(null);
  const [placesCache, setPlacesCache] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [operationCount, setOperationCount] = useState({ reads: 0, writes: 0 });
  
  // Refs for tracking
  const lastFetchRef = useRef(null);
  const pendingUpdatesRef = useRef([]);
  const syncTimeoutRef = useRef(null);

  // ============================================================
  // CACHE UTILITIES
  // ============================================================
  
  const getFromCache = useCallback((key) => {
    try {
      const cached = localStorage.getItem(key);
      if (!cached) return null;
      
      const { data, timestamp } = JSON.parse(cached);
      const ttl = key.includes('places') ? PLACES_CACHE_TTL : CACHE_TTL;
      
      if (Date.now() - timestamp > ttl) {
        localStorage.removeItem(key);
        return null;
      }
      
      return data;
    } catch {
      return null;
    }
  }, []);
  
  const setInCache = useCallback((key, data) => {
    try {
      localStorage.setItem(key, JSON.stringify({
        data,
        timestamp: Date.now()
      }));
    } catch (e) {
      console.warn('Cache write failed:', e);
    }
  }, []);
  
  const clearCache = useCallback(() => {
    Object.values(CACHE_KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
  }, []);

  // ============================================================
  // API HELPERS
  // ============================================================
  
  const fetchWithAuth = useCallback(async (url, options = {}) => {
    const token = await getIdToken();
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers
      }
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(error.error || 'Request failed');
    }
    
    const result = await response.json();
    
    // Track operations
    if (result.operations) {
      setOperationCount(prev => ({
        reads: prev.reads + (result.operations.reads || 0),
        writes: prev.writes + (result.operations.writes || 0)
      }));
    }
    
    return result;
  }, [getIdToken]);

  // ============================================================
  // LOAD DASHBOARDS - 1 READ EACH (2 TOTAL)
  // ============================================================
  
  const loadExpenseDashboard = useCallback(async (forceRefresh = false) => {
    // Check cache first
    if (!forceRefresh) {
      const cached = getFromCache(CACHE_KEYS.EXPENSE_DASHBOARD);
      if (cached) {
        setExpenseDashboard(cached);
        return cached;
      }
    }
    
    try {
      const result = await fetchWithAuth(`${EXPENSE_API}/dashboard`);
      const dashboard = result.data;
      
      setExpenseDashboard(dashboard);
      setInCache(CACHE_KEYS.EXPENSE_DASHBOARD, dashboard);
      
      return dashboard;
    } catch (err) {
      console.error('Load expense dashboard error:', err);
      setError(err.message);
      throw err;
    }
  }, [fetchWithAuth, getFromCache, setInCache]);
  
  const loadGroupPlannerDashboard = useCallback(async (forceRefresh = false) => {
    // Check cache first
    if (!forceRefresh) {
      const cached = getFromCache(CACHE_KEYS.GROUP_PLANNER_DASHBOARD);
      if (cached) {
        setGroupPlannerDashboard(cached);
        return cached;
      }
    }
    
    try {
      const result = await fetchWithAuth(`${GROUP_PLANNER_API}/dashboard`);
      const dashboard = result.data;
      
      setGroupPlannerDashboard(dashboard);
      setInCache(CACHE_KEYS.GROUP_PLANNER_DASHBOARD, dashboard);
      
      return dashboard;
    } catch (err) {
      console.error('Load group planner dashboard error:', err);
      setError(err.message);
      throw err;
    }
  }, [fetchWithAuth, getFromCache, setInCache]);
  
  const loadAllDashboards = useCallback(async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        loadExpenseDashboard(forceRefresh),
        loadGroupPlannerDashboard(forceRefresh)
      ]);
      
      lastFetchRef.current = Date.now();
    } catch (err) {
      // Individual errors already handled
    } finally {
      setLoading(false);
    }
  }, [loadExpenseDashboard, loadGroupPlannerDashboard]);

  // ============================================================
  // EXPENSE ENGINE MUTATIONS - 1 WRITE EACH
  // ============================================================
  
  const createExpense = useCallback(async (expenseData) => {
    try {
      const result = await fetchWithAuth(`${EXPENSE_API}/expenses`, {
        method: 'POST',
        body: JSON.stringify(expenseData)
      });
      
      // Optimistic update
      setExpenseDashboard(prev => {
        if (!prev) return prev;
        const updated = { ...prev };
        const groupId = expenseData.groupId;
        
        if (updated.groups?.[groupId]) {
          updated.groups[groupId].expenses = [
            ...(updated.groups[groupId].expenses || []),
            result.data
          ];
        }
        
        setInCache(CACHE_KEYS.EXPENSE_DASHBOARD, updated);
        return updated;
      });
      
      return result.data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [fetchWithAuth, setInCache]);
  
  const createSettlement = useCallback(async (settlementData) => {
    try {
      const result = await fetchWithAuth(`${EXPENSE_API}/settlements`, {
        method: 'POST',
        body: JSON.stringify(settlementData)
      });
      
      // Optimistic update
      setExpenseDashboard(prev => {
        if (!prev) return prev;
        const updated = { ...prev };
        const groupId = settlementData.groupId;
        
        if (updated.groups?.[groupId]) {
          updated.groups[groupId].settlements = [
            ...(updated.groups[groupId].settlements || []),
            result.data
          ];
        }
        
        setInCache(CACHE_KEYS.EXPENSE_DASHBOARD, updated);
        return updated;
      });
      
      return result.data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [fetchWithAuth, setInCache]);
  
  const acceptExpenseInvitation = useCallback(async (invitationId, invitationData) => {
    try {
      const result = await fetchWithAuth(`${EXPENSE_API}/invitations/${invitationId}/accept`, {
        method: 'POST',
        body: JSON.stringify(invitationData)
      });
      
      // Optimistic update - remove from invitations, add to groups
      setExpenseDashboard(prev => {
        if (!prev) return prev;
        const updated = { ...prev };
        
        // Remove invitation
        updated.invitations = (updated.invitations || []).filter(
          inv => inv.id !== invitationId
        );
        
        // Add group
        if (result.data?.group) {
          updated.groups = {
            ...updated.groups,
            [result.data.group.groupId]: result.data.group
          };
        }
        
        setInCache(CACHE_KEYS.EXPENSE_DASHBOARD, updated);
        return updated;
      });
      
      return result.data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [fetchWithAuth, setInCache]);

  // ============================================================
  // GROUP PLANNER MUTATIONS - 1 WRITE EACH
  // ============================================================
  
  const createTripGroup = useCallback(async (groupData) => {
    try {
      const result = await fetchWithAuth(`${GROUP_PLANNER_API}/groups`, {
        method: 'POST',
        body: JSON.stringify(groupData)
      });
      
      // Optimistic update
      setGroupPlannerDashboard(prev => {
        if (!prev) return prev;
        const updated = { ...prev };
        
        updated.groups = {
          ...updated.groups,
          [result.data.group_id]: result.data
        };
        
        setInCache(CACHE_KEYS.GROUP_PLANNER_DASHBOARD, updated);
        return updated;
      });
      
      return result.data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [fetchWithAuth, setInCache]);
  
  const sendTripInvitation = useCallback(async (invitationData) => {
    try {
      const result = await fetchWithAuth(`${GROUP_PLANNER_API}/invitations`, {
        method: 'POST',
        body: JSON.stringify(invitationData)
      });
      
      return result.data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [fetchWithAuth]);
  
  const acceptTripInvitation = useCallback(async (invitationId, invitationData) => {
    try {
      const result = await fetchWithAuth(`${GROUP_PLANNER_API}/invitations/${invitationId}/accept`, {
        method: 'POST',
        body: JSON.stringify(invitationData)
      });
      
      // Optimistic update
      setGroupPlannerDashboard(prev => {
        if (!prev) return prev;
        const updated = { ...prev };
        
        // Remove invitation
        updated.invitations = (updated.invitations || []).filter(
          inv => inv.id !== invitationId
        );
        
        // Add group
        if (result.data?.group_id) {
          updated.groups = {
            ...updated.groups,
            [result.data.group_id]: {
              ...invitationData,
              group_id: result.data.group_id
            }
          };
        }
        
        setInCache(CACHE_KEYS.GROUP_PLANNER_DASHBOARD, updated);
        return updated;
      });
      
      return result.data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [fetchWithAuth, setInCache]);
  
  const addPlaceToGroup = useCallback(async (groupId, placeData) => {
    try {
      const result = await fetchWithAuth(`${GROUP_PLANNER_API}/groups/${groupId}/places`, {
        method: 'POST',
        body: JSON.stringify(placeData)
      });
      
      // Optimistic update
      setGroupPlannerDashboard(prev => {
        if (!prev) return prev;
        const updated = { ...prev };
        
        if (updated.groups?.[groupId]) {
          updated.groups[groupId].places = [
            ...(updated.groups[groupId].places || []),
            result.data
          ];
        }
        
        setInCache(CACHE_KEYS.GROUP_PLANNER_DASHBOARD, updated);
        return updated;
      });
      
      return result.data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [fetchWithAuth, setInCache]);
  
  const createPoll = useCallback(async (groupId, pollData) => {
    try {
      const result = await fetchWithAuth(`${GROUP_PLANNER_API}/groups/${groupId}/polls`, {
        method: 'POST',
        body: JSON.stringify(pollData)
      });
      
      // Optimistic update
      setGroupPlannerDashboard(prev => {
        if (!prev) return prev;
        const updated = { ...prev };
        
        if (updated.groups?.[groupId]) {
          updated.groups[groupId].polls = [
            ...(updated.groups[groupId].polls || []),
            result.data
          ];
        }
        
        setInCache(CACHE_KEYS.GROUP_PLANNER_DASHBOARD, updated);
        return updated;
      });
      
      return result.data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [fetchWithAuth, setInCache]);

  // ============================================================
  // PLACES ENGINE - 0 ops (cached) or 1 READ
  // ============================================================
  
  const searchPlaces = useCallback(async (destination, category = null) => {
    const cacheKey = `${destination}_${category || 'all'}`;
    
    // Check local cache
    if (placesCache[cacheKey]) {
      return { places: placesCache[cacheKey], fromCache: true };
    }
    
    // Check localStorage
    const storageKey = `${CACHE_KEYS.PLACES_CACHE}_${cacheKey}`;
    const cached = getFromCache(storageKey);
    if (cached) {
      setPlacesCache(prev => ({ ...prev, [cacheKey]: cached }));
      return { places: cached, fromCache: true };
    }
    
    try {
      const params = new URLSearchParams({ destination });
      if (category) params.append('category', category);
      
      const result = await fetchWithAuth(`${GROUP_PLANNER_API}/places/search?${params}`);
      const places = result.data;
      
      // Cache in memory and localStorage
      setPlacesCache(prev => ({ ...prev, [cacheKey]: places }));
      setInCache(storageKey, places);
      
      return { places, fromCache: result.from_cache };
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [placesCache, fetchWithAuth, getFromCache, setInCache]);
  
  const getNearbyPlaces = useCallback(async (lat, lng, radiusKm = 10, category = null) => {
    const cacheKey = `nearby_${lat.toFixed(4)}_${lng.toFixed(4)}_${radiusKm}_${category || 'all'}`;
    
    // Check local cache
    if (placesCache[cacheKey]) {
      return { places: placesCache[cacheKey], fromCache: true };
    }
    
    try {
      const params = new URLSearchParams({
        lat: lat.toString(),
        lng: lng.toString(),
        radius: radiusKm.toString()
      });
      if (category) params.append('category', category);
      
      const result = await fetchWithAuth(`${GROUP_PLANNER_API}/places/nearby?${params}`);
      const places = result.data;
      
      // Cache in memory
      setPlacesCache(prev => ({ ...prev, [cacheKey]: places }));
      
      return { places, fromCache: result.from_cache };
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [placesCache, fetchWithAuth]);

  // ============================================================
  // DERIVED DATA
  // ============================================================
  
  const expenseGroups = expenseDashboard?.groups 
    ? Object.values(expenseDashboard.groups) 
    : [];
  
  const tripGroups = groupPlannerDashboard?.groups 
    ? Object.values(groupPlannerDashboard.groups) 
    : [];
  
  const expenseInvitations = expenseDashboard?.invitations || [];
  const tripInvitations = groupPlannerDashboard?.invitations || [];
  
  const totalBalance = expenseDashboard?.totalBalance || 0;

  // ============================================================
  // LIFECYCLE
  // ============================================================
  
  useEffect(() => {
    if (user) {
      loadAllDashboards();
    } else {
      setExpenseDashboard(null);
      setGroupPlannerDashboard(null);
      setOperationCount({ reads: 0, writes: 0 });
    }
  }, [user, loadAllDashboards]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (syncTimeoutRef.current) {
        clearTimeout(syncTimeoutRef.current);
      }
    };
  }, []);

  // ============================================================
  // CONTEXT VALUE
  // ============================================================
  
  const value = {
    // State
    expenseDashboard,
    groupPlannerDashboard,
    loading,
    error,
    operationCount,
    
    // Derived data
    expenseGroups,
    tripGroups,
    expenseInvitations,
    tripInvitations,
    totalBalance,
    
    // Dashboard loading
    loadAllDashboards,
    loadExpenseDashboard,
    loadGroupPlannerDashboard,
    refreshDashboards: () => loadAllDashboards(true),
    
    // Expense mutations
    createExpense,
    createSettlement,
    acceptExpenseInvitation,
    
    // Group Planner mutations
    createTripGroup,
    sendTripInvitation,
    acceptTripInvitation,
    addPlaceToGroup,
    createPoll,
    
    // Places
    searchPlaces,
    getNearbyPlaces,
    placesCache,
    
    // Utilities
    clearCache,
    resetOperationCount: () => setOperationCount({ reads: 0, writes: 0 })
  };
  
  return (
    <UnifiedDashboardContext.Provider value={value}>
      {children}
    </UnifiedDashboardContext.Provider>
  );
};

export default UnifiedDashboardContext;
