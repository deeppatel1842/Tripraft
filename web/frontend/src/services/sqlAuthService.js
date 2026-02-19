/**
 * SQL Authentication Service
 * Handles authentication against the local SQL backend
 * JWT-based authentication service
 */

import GlobalConfig from '../config/globalConfig';

class SQLAuthService {
  constructor() {
    this.baseUrl = `${GlobalConfig.API_BASE_URL}/expense`;
    this.accessToken = null;
    this.refreshToken = null;
    this.currentUser = null;
    this.authStateListeners = [];
    
    // Refresh lock to prevent concurrent refresh attempts
    this._refreshPromise = null;
    this._isRefreshing = false;
    
    // Load tokens from localStorage on init
    this._loadStoredAuth();
  }

  /**
   * Load stored authentication from localStorage
   */
  _loadStoredAuth() {
    const accessToken = localStorage.getItem('accessToken');
    const refreshToken = localStorage.getItem('refreshToken');
    const userData = localStorage.getItem('currentUser');

    if (accessToken && refreshToken && userData) {
      this.accessToken = accessToken;
      this.refreshToken = refreshToken;
      try {
        this.currentUser = JSON.parse(userData);
      } catch (e) {
        this.currentUser = null;
      }
    }
  }

  /**
   * Save authentication to localStorage
   */
  _saveAuth(accessToken, refreshToken, user) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    this.currentUser = user;

    localStorage.setItem('accessToken', accessToken);
    localStorage.setItem('refreshToken', refreshToken);
    localStorage.setItem('currentUser', JSON.stringify(user));
    // Keep legacy 'token' key for compatibility with existing code
    localStorage.setItem('token', accessToken);
  }

  /**
   * Clear authentication from localStorage
   */
  _clearAuth() {
    this.accessToken = null;
    this.refreshToken = null;
    this.currentUser = null;

    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('token');
  }

  /**
   * Notify all auth state listeners
   */
  _notifyAuthStateChange(user) {
    this.authStateListeners.forEach(callback => {
      try {
        callback(user);
      } catch (err) {
        // auth state listener error handled silently
      }
    });
  }

  /**
   * Sign up with email and password
   */
  async signUpWithEmail(email, password, displayName = '') {
    try {
      const response = await fetch(`${this.baseUrl}/signup`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          display_name: displayName || email.split('@')[0]
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error || 'signup_failed',
          message: data.message || data.error || 'Failed to create account'
        };
      }

      // Save auth and notify listeners
      this._saveAuth(data.access_token, data.refresh_token, data.user);
      this._notifyAuthStateChange(this._createUserObject(data.user, data.access_token));

      return {
        success: true,
        user: this._createUserObject(data.user, data.access_token),
        token: data.access_token
      };
    } catch (error) {
      return {
        success: false,
        error: 'network_error',
        message: error.message || 'Network error during signup'
      };
    }
  }

  /**
   * Sign in with email and password
   */
  async signInWithEmail(email, password) {
    try {
      const response = await fetch(`${this.baseUrl}/login`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error || 'auth_failed',
          message: data.message || data.error || 'Invalid email or password'
        };
      }

      // Save auth and notify listeners
      this._saveAuth(data.access_token, data.refresh_token, data.user);
      this._notifyAuthStateChange(this._createUserObject(data.user, data.access_token));

      return {
        success: true,
        user: this._createUserObject(data.user, data.access_token),
        token: data.access_token
      };
    } catch (error) {
      return {
        success: false,
        error: 'network_error',
        message: error.message || 'Network error during sign in'
      };
    }
  }

  /**
   * Sign out
   */
  async signOut() {
    try {
      // Clear local auth
      this._clearAuth();
      this._notifyAuthStateChange(null);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: 'signout_error',
        message: error.message
      };
    }
  }

  /**
   * Refresh access token using refresh token
   * Uses a lock to prevent concurrent refresh attempts (race condition fix)
   */
  async refreshAccessToken() {
    if (!this.refreshToken) {
      return { success: false, error: 'no_refresh_token' };
    }

    // If already refreshing, wait for the existing refresh to complete
    if (this._isRefreshing && this._refreshPromise) {
      return this._refreshPromise;
    }

    // Set the lock
    this._isRefreshing = true;
    
    this._refreshPromise = (async () => {
      try {
        const response = await fetch(`${this.baseUrl}/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });

        const data = await response.json();

        if (!response.ok) {
          // Only clear auth if this was the first refresh attempt
          // Don't logout if another refresh already succeeded
          if (this._isRefreshing) {
            this._clearAuth();
            this._notifyAuthStateChange(null);
          }
          return {
            success: false,
            error: data.error || 'refresh_failed',
            message: data.message || 'Failed to refresh token'
          };
        }
        
        // Update tokens
        this.accessToken = data.access_token;
        localStorage.setItem('accessToken', data.access_token);
        localStorage.setItem('token', data.access_token);
        
        // Update refresh token if a new one was provided
        if (data.refresh_token) {
          this.refreshToken = data.refresh_token;
          localStorage.setItem('refreshToken', data.refresh_token);
        }

        return {
          success: true,
          token: data.access_token
        };
      } catch (error) {
        return {
          success: false,
          error: 'network_error',
          message: error.message
        };
      } finally {
        // Release the lock
        this._isRefreshing = false;
        this._refreshPromise = null;
      }
    })();

    return this._refreshPromise;
  }

  /**
   * Get current user profile from backend
   */
  async getCurrentUserFromBackend() {
    if (!this.accessToken) {
      return null;
    }

    try {
      const response = await fetch(`${this.baseUrl}/me`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.accessToken}`
        },
      });

      if (!response.ok) {
        // Try to refresh token if 401
        if (response.status === 401) {
          const refreshResult = await this.refreshAccessToken();
          if (refreshResult.success) {
            // Retry with new token
            const retryResponse = await fetch(`${this.baseUrl}/me`, {
              method: 'GET',
              credentials: 'include',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.accessToken}`
              },
            });
            if (retryResponse.ok) {
              const data = await retryResponse.json();
              return this._createUserObject(data.user, this.accessToken);
            }
          }
        }
        return null;
      }

      const data = await response.json();
      return this._createUserObject(data.user, this.accessToken);
    } catch (error) {
      return null;
    }
  }

  /**
   * Get current user (from memory)
   */
  getCurrentUser() {
    if (!this.currentUser || !this.accessToken) {
      return null;
    }
    return this._createUserObject(this.currentUser, this.accessToken);
  }

  /**
   * Get current ID token (access token)
   */
  async getIdToken() {
    // Check if token might be expired (JWT tokens expire)
    if (this.accessToken) {
      try {
        // Try to decode token and check expiry
        const payload = JSON.parse(atob(this.accessToken.split('.')[1]));
        const now = Math.floor(Date.now() / 1000);
        
        // If token expires in less than 60 seconds, refresh it
        if (payload.exp && payload.exp - now < 60) {
          const result = await this.refreshAccessToken();
          if (result.success) {
            return result.token;
          }
        }
      } catch (e) {
        // If we can't decode token, just return it
      }
      return this.accessToken;
    }
    return null;
  }

  /**
   * Listen to auth state changes
   * Auth state change listener
   */
  onAuthStateChanged(callback) {
    // Add listener
    this.authStateListeners.push(callback);

    // Immediately call with current state
    // Use setTimeout to ensure async execution
    setTimeout(async () => {
      if (this.accessToken && this.currentUser) {
        // Verify token is still valid
        const user = await this.getCurrentUserFromBackend();
        if (user) {
          callback(user);
        } else {
          // Token invalid, clear auth
          this._clearAuth();
          callback(null);
        }
      } else {
        callback(null);
      }
    }, 0);

    // Return unsubscribe function
    return () => {
      const index = this.authStateListeners.indexOf(callback);
      if (index > -1) {
        this.authStateListeners.splice(index, 1);
      }
    };
  }

  /**
   * Create a user object compatible with the existing app structure
   */
  _createUserObject(userData, token) {
    return {
      uid: String(userData.id), // String for compatibility
      id: userData.id,
      email: userData.email,
      displayName: userData.display_name || userData.email.split('@')[0],
      photoURL: userData.profile_picture || '',
      emailVerified: true, // SQL users are verified
      
      // Method to get token
      getIdToken: async (forceRefresh = false) => {
        if (forceRefresh) {
          const result = await this.refreshAccessToken();
          return result.success ? result.token : this.accessToken;
        }
        return this.accessToken;
      }
    };
  }

  /**
   * Verify token with backend (no-op for SQL auth since token is already from backend)
   */
  async verifyWithBackend(idToken) {
    // For SQL auth, the token IS from the backend, so just verify it's valid
    try {
      const response = await fetch(`${this.baseUrl}/me`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`
        },
      });

      if (response.ok) {
        const data = await response.json();
        return { success: true, user: data.user };
      }

      return { success: false, error: 'Invalid token' };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
}

const sqlAuthService = new SQLAuthService();
export default sqlAuthService;
