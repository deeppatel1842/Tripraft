/**
 * Authentication Context
 * Manages user authentication state globally with Firebase
 * Provides secure access to user data across the app
 */

import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import authService from '../firebase/authService';
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
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const userCreationAttempted = useRef(new Set());

  useEffect(() => {
    let unsubscribe;
    
    // Listen to Firebase auth state changes
    unsubscribe = authService.onAuthStateChanged(async (firebaseUser) => {
      try {
        if (firebaseUser) {
          // Force reload to get latest user data including displayName
          await firebaseUser.reload();
          
          // User is signed in
          const token = await firebaseUser.getIdToken();
          
          // Set token for expense API
          expenseApi.setAuthToken(token);
          
          // Create user object with profile data
          const userData = {
            uid: firebaseUser.uid,
            email: firebaseUser.email,
            displayName: firebaseUser.displayName || '',
            photoURL: firebaseUser.photoURL || '',
            emailVerified: firebaseUser.emailVerified,
            token: token
          };
          
          // CRITICAL: Save token to localStorage for API requests
          localStorage.setItem('token', token);
          console.log('✅ Token saved to localStorage (length:', token.length, 'chars)');
          
          // Try to create/update user in expense database (only once per user session)
          if (!userCreationAttempted.current.has(firebaseUser.uid)) {
            userCreationAttempted.current.add(firebaseUser.uid);
            try {
              await expenseApi.createUser({
                uid: firebaseUser.uid,
                email: firebaseUser.email,
                username: firebaseUser.displayName || firebaseUser.email.split('@')[0],
                display_name: firebaseUser.displayName,
                profile_picture: firebaseUser.photoURL
              });
            } catch (err) {
              // User might already exist or Firestore might not be enabled yet
              // Don't throw - user auth is still valid
              console.log('ℹ️  User profile sync skipped:', err.message);
            }
          }
          
          setCurrentUser(userData);
        } else {
          // User is signed out
          console.log('🚪 User signed out - clearing token from localStorage');
          localStorage.removeItem('token');
          expenseApi.setAuthToken(null);
          setCurrentUser(null);
        }
      } catch (err) {
        console.error('Error in auth state change:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    });

    return () => unsubscribe();
  }, []);

  // Sign in with email and password
  const signIn = async (email, password) => {
    console.log('\n' + '='.repeat(60));
    console.log('🔐 SIGN IN REQUESTED');
    console.log('='.repeat(60));
    console.log('📧 Email:', email);
    
    try {
      setError(null);
      setLoading(true);
      
      console.log('🔍 Calling authService.signInWithEmail...');
      const result = await authService.signInWithEmail(email, password);
      
      if (!result.success) {
        console.log('❌ Sign in failed:', result.message);
        throw new Error(result.message || 'Failed to sign in');
      }
      
      console.log('✅ Sign in successful!');
      console.log('='.repeat(60) + '\n');
      return { success: true, user: result.user };
    } catch (err) {
      console.log('❌ Sign in error:', err.message);
      console.log('='.repeat(60) + '\n');
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

  // Sign in with Google (uses redirect, no popup warnings)
  const signInWithGoogle = async () => {
    try {
      setError(null);
      // Redirect method doesn't return immediately
      const result = await authService.signInWithGoogle();
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to sign in with Google');
      }
      
      // User will be redirected, then come back and auth state will update
      return { success: true, redirecting: result.redirecting };
    } catch (err) {
      setError(err.message);
      setLoading(false);
      return { success: false, error: err.message };
    }
  };

  // Sign out
  const signOut = async () => {
    try {
      setError(null);
      
      // Clear all caches to prevent data leaks between users
      console.log('🔐 Clearing all caches on logout...');
      try {
        const groupPlannerService = (await import('../services/groupPlannerService')).default;
        groupPlannerService.clearAllCache();
      } catch (cacheError) {
        console.warn('Failed to clear group planner cache:', cacheError);
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
      const user = authService.getCurrentUser();
      
      if (!user) {
        throw new Error('No user signed in');
      }
      
      // Update Firebase profile
      await authService.auth.updateProfile(user, updates);
      
      // Update local state
      setCurrentUser(prev => ({
        ...prev,
        displayName: updates.displayName || prev.displayName,
        photoURL: updates.photoURL || prev.photoURL
      }));
      
      // Update in expense database
      if (currentUser) {
        await expenseApi.updateUser(currentUser.uid, {
          display_name: updates.displayName,
          profile_picture: updates.photoURL
        });
      }
      
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
