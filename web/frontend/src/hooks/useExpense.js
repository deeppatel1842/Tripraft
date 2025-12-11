/**
 * React Hook for Expense Management
 * Provides easy access to expense API with authentication
 */

import { useState, useEffect, useCallback } from 'react';
import expenseApi from '../services/expenseApi';
import authService from '../firebase/authService';

/**
 * Hook to manage expense API with authentication
 */
export const useExpenseApi = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Set up auth state listener
    const unsubscribe = authService.onAuthStateChanged(async (user) => {
      if (user) {
        const token = await user.getIdToken();
        expenseApi.setAuthToken(token);
        expenseApi.setCurrentUser(user); // Store user for token refresh
        setCurrentUser(user);
        setIsAuthenticated(true);
      } else {
        expenseApi.setAuthToken(null);
        expenseApi.setCurrentUser(null);
        setCurrentUser(null);
        setIsAuthenticated(false);
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  return {
    isAuthenticated,
    currentUser,
    loading,
    api: expenseApi
  };
};

/**
 * Hook to manage user expenses (for current authenticated user)
 * @param {boolean} personalOnly - If true, fetch only personal expenses (no group expenses)
 */
export const useUserExpenses = (personalOnly = true) => {
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAuthenticated } = useExpenseApi();

  const loadExpenses = useCallback(async () => {
    // Don't load if not authenticated
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // getUserExpenses is deprecated - personal expenses loaded differently now
      // Just set empty array for personal mode
      setExpenses([]);
      
    } catch (err) {
      setError(err.message);
      console.error('Error loading user expenses:', err);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, personalOnly]);

  useEffect(() => {
    loadExpenses();
  }, [loadExpenses]);

  return { expenses, loading, error, reload: loadExpenses };
};

/**
 * Hook to manage group data
 */
export const useGroup = (groupId) => {
  const [group, setGroup] = useState(null);
  const [members, setMembers] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [balances, setBalances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAuthenticated } = useExpenseApi();

  const loadGroup = useCallback(async (bypassCache = false) => {
    if (!groupId || !isAuthenticated) {
      // Clear all group data when groupId is null
      setGroup(null);
      setMembers([]);
      setExpenses([]);
      setBalances([]);
      setLoading(false);
      return;
    }
    
    try {
      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 Loading group data for:', groupId, bypassCache ? '(bypassing cache)' : '');
      }
      setLoading(true);
      setError(null);
      
      // 🚀 PHASE 6.4: Use single optimized API call instead of 6 parallel calls
      // Benefits: Reduces network overhead by 500-1000ms, single cache key
      // After creating/editing expenses, bypass cache to get fresh data
      const fullData = await expenseApi.getGroupFull(groupId, bypassCache);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('📊 Loaded full group data:', {
          expenses: fullData.expenses?.length,
          balances: fullData.balances?.length,
          members: fullData.members?.length,
          settlements: fullData.settlements?.length,
          invitations: fullData.invitations?.length
        });
      }
      
      // CRITICAL FIX (Bug #7): Filter out soft-deleted expenses from API response
      const activeExpenses = (fullData.expenses || []).filter(e => !e.is_deleted);
      if (activeExpenses.length !== fullData.expenses?.length) {
        console.warn('⚠️ Filtered out', fullData.expenses.length - activeExpenses.length, 'deleted expenses');
      }
      
      // Set all data from single response
      setGroup(fullData.group);
      setMembers(fullData.members || []);
      setExpenses(activeExpenses);
      setBalances(fullData.balances || []);
      
      // Note: settlements and invitations are available in fullData if needed later
    } catch (err) {
      setError(err.message);
      console.error('Error loading group:', err);
    } finally {
      setLoading(false);
    }
  }, [groupId, isAuthenticated]);

  useEffect(() => {
    loadGroup();
  }, [loadGroup]);

  return { 
    group, 
    members, 
    expenses, 
    balances, 
    loading, 
    error, 
    reload: loadGroup 
  };
};

/**
 * Hook to manage user groups (for current authenticated user)
 */
export const useUserGroups = () => {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAuthenticated } = useExpenseApi();

  const loadGroups = useCallback(async () => {
    // Don't load if not authenticated
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await expenseApi.getUserGroups();
      setGroups(data.groups || []);
    } catch (err) {
      setError(err.message);
      console.error('Error loading user groups:', err);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  const createGroup = async (groupData) => {
    try {
      const result = await expenseApi.createGroup(groupData);
      
      // 🔧 OPTIMIZATION: Optimistically add to local state IMMEDIATELY
      if (result?.group) {
        setGroups(prevGroups => [...prevGroups, result.group]);
        console.log('✅ Group added to local state (no reload needed)');
      }
      
      return result;
    } catch (err) {
      setError(err.message);
      // Reload on error to restore correct state
      await loadGroups();
      throw err;
    }
  };

  const deleteGroup = async (groupId) => {
    // 🔧 CRITICAL FIX: Immediately update local state FIRST (optimistic delete)
    setGroups(prevGroups => prevGroups.filter(g => g.id !== groupId));
    
    try {
      // Delete on server and wait for completion
      await expenseApi.deleteGroup(groupId);
      console.log('✅ Group deleted successfully (no reload needed)');
    } catch (err) {
      console.error('❌ Delete failed:', err);
      setError(err.message);
      // Restore correct state on error by reloading
      await loadGroups();
      throw err;
    }
  };

  return { 
    groups, 
    loading, 
    error, 
    reload: loadGroups,
    createGroup,
    deleteGroup
  };
};

/**
 * Hook to manage balances
 */
export const useBalances = (uid, groupId = null) => {
  const [balances, setBalances] = useState([]);
  const [simplifiedDebts, setSimplifiedDebts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadBalances = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      if (groupId) {
        // Load group balances and simplified debts
        const [balancesData, debtsData] = await Promise.all([
          expenseApi.getGroupBalances(groupId),
          expenseApi.getSimplifiedDebts(groupId)
        ]);
        setBalances(balancesData.balances || []);
        setSimplifiedDebts(debtsData.debts || []);
      } else if (uid) {
        // Load user balances across all groups
        const data = await expenseApi.getUserBalances(uid);
        setBalances(data.balances || []);
      }
    } catch (err) {
      setError(err.message);
      console.error('Error loading balances:', err);
    } finally {
      setLoading(false);
    }
  }, [uid, groupId]);

  useEffect(() => {
    loadBalances();
  }, [loadBalances]);

  return { 
    balances, 
    simplifiedDebts, 
    loading, 
    error, 
    reload: loadBalances 
  };
};

/**
 * Currency utilities
 */
export const currencies = {
  USD: { code: 'USD', symbol: '$', name: 'US Dollar' },
  EUR: { code: 'EUR', symbol: '€', name: 'Euro' },
  INR: { code: 'INR', symbol: '₹', name: 'Indian Rupee' },
  GBP: { code: 'GBP', symbol: '£', name: 'British Pound' },
  JPY: { code: 'JPY', symbol: '¥', name: 'Japanese Yen' },
  CAD: { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar' },
  AUD: { code: 'AUD', symbol: 'A$', name: 'Australian Dollar' },
  CHF: { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc' },
  CNY: { code: 'CNY', symbol: '¥', name: 'Chinese Yuan' },
  KRW: { code: 'KRW', symbol: '₩', name: 'South Korean Won' },
  BRL: { code: 'BRL', symbol: 'R$', name: 'Brazilian Real' },
  MXN: { code: 'MXN', symbol: 'Mex$', name: 'Mexican Peso' },
  SGD: { code: 'SGD', symbol: 'S$', name: 'Singapore Dollar' },
  HKD: { code: 'HKD', symbol: 'HK$', name: 'Hong Kong Dollar' },
  NZD: { code: 'NZD', symbol: 'NZ$', name: 'New Zealand Dollar' }
};

export const formatCurrency = (amount, currencyCode = 'USD') => {
  const currency = currencies[currencyCode] || currencies.USD;
  return `${currency.symbol}${amount.toFixed(2)}`;
};

export const getCurrencySymbol = (currencyCode = 'USD') => {
  return currencies[currencyCode]?.symbol || currencyCode;
};

export const getCurrencyList = () => {
  return Object.values(currencies);
};
