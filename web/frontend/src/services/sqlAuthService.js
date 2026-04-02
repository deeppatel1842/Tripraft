/**
 * SQL Authentication Service
 * Handles authentication against the local SQL backend
 * JWT-based authentication service
 */

import GlobalConfig from '../config/globalConfig';

class SQLAuthService {
  constructor() {
    this.baseUrl = `${GlobalConfig.API_BASE_URL}${GlobalConfig.ENDPOINTS.AUTH}`;
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
   * Load stored user profile from localStorage.
   * Tokens are handled by httpOnly cookies -- never stored in localStorage.
   */
  _loadStoredAuth() {
    // Migrate: remove any tokens previously stored in localStorage
    localStorage.removeItem(GlobalConfig.STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(GlobalConfig.STORAGE_KEYS.REFRESH_TOKEN);

    const userData = localStorage.getItem(GlobalConfig.STORAGE_KEYS.CURRENT_USER);
    if (userData) {
      try {
        this.currentUser = JSON.parse(userData);
        // Tokens are now in httpOnly cookies; set flag so we attempt validation
        this.accessToken = '__cookie__';
      } catch (e) {
        this.currentUser = null;
      }
    }
  }

  /**
   * Save user profile to localStorage.
   * Tokens live in httpOnly cookies set by the backend -- never in localStorage.
   */
  _saveAuth(accessToken, refreshToken, user) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    this.currentUser = user;

    // Only store non-sensitive user profile data
    localStorage.setItem(GlobalConfig.STORAGE_KEYS.CURRENT_USER, JSON.stringify(user));
  }

  /**
   * Clear authentication state
   */
  _clearAuth() {
    this.accessToken = null;
    this.refreshToken = null;
    this.currentUser = null;

    localStorage.removeItem(GlobalConfig.STORAGE_KEYS.CURRENT_USER);
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

      const payload = data.data || data;

      // Save auth and notify listeners
      this._saveAuth(payload.access_token, payload.refresh_token, payload.user);
      this._notifyAuthStateChange(this._createUserObject(payload.user, payload.access_token));

      return {
        success: true,
        user: this._createUserObject(payload.user, payload.access_token),
        token: payload.access_token
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

      const payload = data.data || data;

      // Save auth and notify listeners
      this._saveAuth(payload.access_token, payload.refresh_token, payload.user);
      this._notifyAuthStateChange(this._createUserObject(payload.user, payload.access_token));

      return {
        success: true,
        user: this._createUserObject(payload.user, payload.access_token),
        token: payload.access_token
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
      // Call backend to clear httpOnly auth cookies
      await fetch(`${this.baseUrl}/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      }).catch(() => {});

      this._clearAuth();
      this._notifyAuthStateChange(null);
      return { success: true };
    } catch (error) {
      this._clearAuth();
      this._notifyAuthStateChange(null);
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
    // In cookie mode, refresh token is in httpOnly cookie -- allow the request
    if (!this.refreshToken && this.accessToken !== '__cookie__') {
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
        
        // Update in-memory token reference (actual tokens in httpOnly cookies)
        const payload = data.data || data;
        this.accessToken = payload.access_token;
        
        if (payload.refresh_token) {
          this.refreshToken = payload.refresh_token;
        }

        return {
          success: true,
          token: payload.access_token
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
      const headers = { 'Content-Type': 'application/json' };
      if (this.accessToken && this.accessToken !== '__cookie__') {
        headers['Authorization'] = `Bearer ${this.accessToken}`;
      }

      const response = await fetch(`${this.baseUrl}/me`, {
        method: 'GET',
        credentials: 'include',
        headers,
      });

      if (!response.ok) {
        // Try to refresh token if 401
        if (response.status === 401) {
          const refreshResult = await this.refreshAccessToken();
          if (refreshResult.success) {
            // Retry with new token
            const retryHeaders = { 'Content-Type': 'application/json' };
            if (this.accessToken && this.accessToken !== '__cookie__') {
              retryHeaders['Authorization'] = `Bearer ${this.accessToken}`;
            }
            const retryResponse = await fetch(`${this.baseUrl}/me`, {
              method: 'GET',
              credentials: 'include',
              headers: retryHeaders,
            });
            if (retryResponse.ok) {
              const retryData = await retryResponse.json();
              const retryPayload = retryData.data || retryData;
              return this._createUserObject(retryPayload.user, this.accessToken);
            }
          }
        }
        return null;
      }

      const data = await response.json();
      const payload = data.data || data;
      return this._createUserObject(payload.user, this.accessToken);
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
    // Cookie-mode: real token is in httpOnly cookie, not accessible to JS
    if (!this.accessToken || this.accessToken === '__cookie__') {
      return null;
    }
    try {
      const payload = JSON.parse(atob(this.accessToken.split('.')[1]));
      const now = Math.floor(Date.now() / 1000);
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
          if (result.success) return result.token;
        }
        if (!this.accessToken || this.accessToken === '__cookie__') return null;
        return this.accessToken;
      }
    };
  }

  /**
   * Verify token with backend (no-op for SQL auth since token is already from backend)
   */
  async verifyWithBackend(idToken) {
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (idToken && idToken !== '__cookie__') {
        headers['Authorization'] = `Bearer ${idToken}`;
      }
      const response = await fetch(`${this.baseUrl}/me`, {
        method: 'GET',
        credentials: 'include',
        headers,
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
