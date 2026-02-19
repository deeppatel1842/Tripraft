/**
 * Authentication Context
 * Manages user authentication state globally with SQL backend
 * Provides secure access to user data across the app
 */

import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import authService from '../services/sqlAuthService';
import expenseApi from '../services/expenseApi';

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
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const userCreationAttempted = useRef(new Set());

  useEffect(() => {
    let unsubscribe;
    
    // Listen to SQL auth state changes
    unsubscribe = authService.onAuthStateChanged(async (user) => {
      try {
        if (user) {
          // User is signed in
          const token = await user.getIdToken();
          
          // Set token for expense API
          expenseApi.setAuthToken(token);
          
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
          
          // CRITICAL: Save token to localStorage for API requests
          localStorage.setItem('token', token);
          
          // User is already created in SQL database during signup/login
          // No need for separate user creation call
          
          setCurrentUser(userData);
        } else {
          // User is signed out
          localStorage.removeItem('token');
          expenseApi.setAuthToken(null);
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

  // Sign in with email and password
  const signIn = async (email, password) => {
    try {
      setError(null);
      setLoading(true);
      
      const result = await authService.signInWithEmail(email, password);
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to sign in');
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
      
      // Clear all caches to prevent data leaks between users
      try {
        const groupPlannerApi = (await import('../services/groupPlannerApi')).default;
        groupPlannerApi.clearAllCache();
      } catch (cacheError) {
        // Silently fail cache clear
      }
      
      await authService.signOut();
      setCurrentUser(null);
      expenseApi.setAuthToken(null);
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
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
    isAuthenticated: !!currentUser
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
