/**
 * React Hook for Group Planner Authentication
 * Provides authentication state and user information
 * 
 * Pattern: Similar to useExpenseApi from Expense Manager
 * Ensures user is authenticated before allowing group operations
 */

import { useState, useEffect, useCallback } from 'react';
import authService from '../firebase/authService';

/**
 * Hook to manage Group Planner authentication
 * 
 * Returns:
 * - isAuthenticated: boolean - User is logged in
 * - currentUser: object - Firebase user object with uid, email, displayName
 * - loading: boolean - Initial auth state is being determined
 * - error: string - Auth error message if any
 * - getToken: function - Get fresh ID token for API calls
 */
export const useGroupPlannerAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Get fresh auth token for API requests
   */
  const getToken = useCallback(async () => {
    try {
      if (!currentUser) {
        console.warn('⚠️ [AUTH] No current user - cannot get token');
        return null;
      }
      
      const token = await currentUser.getIdToken(true); // Force refresh
      console.log('🎟️ [AUTH] Got fresh token, length:', token.length);
      return token;
    } catch (err) {
      console.error('❌ [AUTH] Failed to get token:', err.message);
      setError(err.message);
      return null;
    }
  }, [currentUser]);

  /**
   * Set up auth state listener
   */
  useEffect(() => {
    console.log('🔐 [AUTH] Setting up auth state listener...');
    
    const unsubscribe = authService.onAuthStateChanged(async (user) => {
      if (user) {
        console.log('✅ [AUTH] User authenticated');
        console.log('👤 [AUTH] User ID:', user.uid);
        console.log('📧 [AUTH] Email:', user.email);
        console.log('📛 [AUTH] Display Name:', user.displayName);
        
        setCurrentUser(user);
        setIsAuthenticated(true);
        setError(null);
      } else {
        console.log('❌ [AUTH] User not authenticated');
        setCurrentUser(null);
        setIsAuthenticated(false);
        setError(null);
      }
      setLoading(false);
    });

    return () => {
      console.log('🔐 [AUTH] Cleaning up auth state listener');
      unsubscribe();
    };
  }, []);

  /**
   * Logout function
   */
  const logout = useCallback(async () => {
    try {
      console.log('🚪 [AUTH] Logging out user...');
      await authService.signOut();
      setCurrentUser(null);
      setIsAuthenticated(false);
      setError(null);
      console.log('✅ [AUTH] User logged out successfully');
    } catch (err) {
      console.error('❌ [AUTH] Logout failed:', err.message);
      setError(err.message);
      throw err;
    }
  }, []);

  return {
    isAuthenticated,
    currentUser,
    loading,
    error,
    getToken,
    logout,
    userId: currentUser?.uid || null,
    userEmail: currentUser?.email || null,
    userDisplayName: currentUser?.displayName || null
  };
};

export default useGroupPlannerAuth;
