/**
 * Authentication Context
 * Manages user authentication state globally with SQL backend
 * Provides secure access to user data across the app
 */

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import authService from '../services/sqlAuthService';
import expenseApi from '../services/expenseApi';

const INACTIVITY_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    // Return safe defaults during HMR context re-creation
    return { currentUser: null, loading: true, error: null, signOut: () => Promise.resolve() };
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const queryClient = useQueryClient();
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const userCreationAttempted = useRef(new Set());
  const inactivityTimerRef = useRef(null);
  const [inactivityMessage, setInactivityMessage] = useState(null);

  useEffect(() => {
    let unsubscribe;
    
    // Listen to SQL auth state changes
    unsubscribe = authService.onAuthStateChanged(async (user) => {
      try {
        if (user) {
          // User is signed in
          const token = await user.getIdToken();
          
          // Create user object with profile data
          const userData = {
            uid: user.uid,
            email: user.email,
            displayName: user.displayName || '',
            photoURL: user.photoURL || '',
            emailVerified: user.emailVerified,
            token: token,
            // Keep reference to user object for token refresh
            _sqlUser: user
          };
          
          setCurrentUser(userData);
        } else {
          // User is signed out
          setCurrentUser(null);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    });

    return () => unsubscribe();
  }, []);

  // Inactivity auto-logout: sign out after 15 minutes of no activity
  useEffect(() => {
    if (!currentUser) {
      clearTimeout(inactivityTimerRef.current);
      return;
    }

    const resetTimer = () => {
      clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = setTimeout(async () => {
        await authService.signOut();
        queryClient.clear();
        try {
          if (window.indexedDB) {
            window.indexedDB.deleteDatabase('react-query-offline-cache');
          }
        } catch (_) {}
        setCurrentUser(null);
        setInactivityMessage('For your security, you were logged out due to 15 minutes of inactivity.');
      }, INACTIVITY_TIMEOUT_MS);
    };

    // Throttle activity resets to once per 30s to avoid excessive timer clears
    let lastReset = Date.now();
    const onActivity = () => {
      const now = Date.now();
      if (now - lastReset > 30000) {
        lastReset = now;
        resetTimer();
      }
    };

    const events = ['mousemove', 'keydown', 'click', 'touchstart', 'scroll'];
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    resetTimer();

    return () => {
      clearTimeout(inactivityTimerRef.current);
      events.forEach((e) => window.removeEventListener(e, onActivity));
    };
  }, [currentUser, queryClient]);

  // Sign in with email and password
  const signIn = async (email, password) => {
    try {
      setError(null);
      setLoading(true);
      
      const result = await authService.signInWithEmail(email, password);
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to sign in');
      }

      // Set currentUser directly so it's available before navigate() fires.
      // The async onAuthStateChanged listener would set it too late.
      if (result.user) {
        const token = await result.user.getIdToken();
        setCurrentUser({
          uid: result.user.uid,
          email: result.user.email,
          displayName: result.user.displayName || '',
          photoURL: result.user.photoURL || '',
          emailVerified: result.user.emailVerified,
          token,
          _sqlUser: result.user,
        });
      }
      
      return { success: true, user: result.user };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  // Sign up with email and password
  const signUp = async (email, password, displayName) => {
    try {
      setError(null);
      setLoading(true);
      const result = await authService.signUpWithEmail(email, password, displayName);
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to sign up');
      }
      
      return { success: true, user: result.user };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  // Sign out
  const signOut = async () => {
    try {
      setError(null);
      await authService.signOut();
    } finally {
      // Clear ALL cached server state (in-memory React Query cache)
      queryClient.clear();

      // Clear IndexedDB persisted cache to prevent data leaks between users
      try {
        if (window.indexedDB) {
          window.indexedDB.deleteDatabase('react-query-offline-cache');
        }
      } catch (_) { /* IndexedDB may be unavailable */ }

      setCurrentUser(null);
    }
  };

  // Update user profile
  const updateProfile = async (updates) => {
    try {
      setError(null);
      
      if (!currentUser) {
        throw new Error('No user signed in');
      }
      
      // Update in SQL database via expense API
      await expenseApi.updateUser(currentUser.uid, {
        display_name: updates.displayName,
        profile_picture: updates.photoURL
      });
      
      // Update local state
      setCurrentUser(prev => ({
        ...prev,
        displayName: updates.displayName || prev.displayName,
        photoURL: updates.photoURL || prev.photoURL
      }));
      
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  // Get user initials for avatar
  const getUserInitials = () => {
    if (!currentUser) return '';
    
    if (currentUser.displayName) {
      const names = currentUser.displayName.split(' ');
      if (names.length >= 2) {
        return `${names[0][0]}${names[1][0]}`.toUpperCase();
      }
      return currentUser.displayName.substring(0, 2).toUpperCase();
    }
    
    return currentUser.email.substring(0, 2).toUpperCase();
  };

  const value = {
    currentUser,
    loading,
    error,
    signIn,
    signUp,
    signOut,
    updateProfile,
    getUserInitials,
    isAuthenticated: !!currentUser,
    inactivityMessage,
    clearInactivityMessage: () => setInactivityMessage(null),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
