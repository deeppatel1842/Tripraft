// Purpose: Provides authenticated account state, initialization, profile updates, and logout cache cleanup.
/**
 * Authentication Context
 * Manages user authentication state globally with SQL backend
 * Provides secure access to user data across the app
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import authService from '../services/sqlAuthService';
import { clearPersistedCache } from '../lib/queryClientPersist';
import expenseApi from '../services/expenseApi';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const queryClient = useQueryClient();
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
            is_admin: Boolean(user.is_admin),
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

  // InactivityTracker owns the warning and logout timer.

  // Sign in with email and password
  const signIn = useCallback(async (email, password) => {
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
          is_admin: Boolean(result.user.is_admin),
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
  }, []);

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
  const signOut = useCallback(async () => {
    try {
      setError(null);
      await authService.signOut();
    } finally {
      // Clear ALL cached server state (in-memory React Query cache)
      queryClient.clear();

      // Clear the persisted cache to prevent data leaks between users.
      await clearPersistedCache();

      setCurrentUser(null);
    }
  }, [queryClient]);

  // Update user profile
  const updateProfile = async (updates) => {
    try {
      setError(null);
      
      if (!currentUser) {
        throw new Error('No user signed in');
      }
      
      // Update in SQL database via expense API
      await expenseApi.updateUser({
        display_name: updates.displayName,
        profile_picture: updates.photoURL
      });
      
      // Update local state
      setCurrentUser(prev => ({
        ...prev,
        displayName: updates.displayName ?? prev.displayName,
        photoURL: updates.photoURL ?? prev.photoURL
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
    
    const displayName = String(currentUser.displayName ?? '').trim();
    if (displayName) {
      const names = displayName.split(/\s+/);
      if (names.length >= 2) {
        return `${names[0]?.[0] || ''}${names[1]?.[0] || ''}`.toUpperCase();
      }
      return displayName.substring(0, 2).toUpperCase();
    }
    
    return String(currentUser.email ?? '').trim().substring(0, 2).toUpperCase();
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
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
