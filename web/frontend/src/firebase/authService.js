/**
 * Firebase authentication service
 */
import { initializeApp } from 'firebase/app';
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  OAuthProvider,
  signOut,
  onAuthStateChanged,
  updateProfile
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

googleProvider.setCustomParameters({
  prompt: 'select_account'
});

class AuthService {
  constructor() {
    this.auth = auth;
    this.googleProvider = googleProvider;
  }

  // Email/Password Authentication
  async signInWithEmail(email, password) {
    try {
      const result = await signInWithEmailAndPassword(this.auth, email, password);
      return {
        success: true,
        user: result.user,
        token: await result.user.getIdToken()
      };
    } catch (error) {
      return {
        success: false,
        error: error.code,
        message: error.message
      };
    }
  }

  async signUpWithEmail(email, password, displayName = '') {
    try {
      const result = await createUserWithEmailAndPassword(this.auth, email, password);
      
      // Update display name if provided
      if (displayName) {
        await updateProfile(result.user, { displayName });
      }
      
      return {
        success: true,
        user: result.user,
        token: await result.user.getIdToken()
      };
    } catch (error) {
      return {
        success: false,
        error: error.code,
        message: error.message
      };
    }
  }

  // Google Authentication
  async signInWithGoogle() {
    try {
      const result = await signInWithPopup(this.auth, this.googleProvider);
      return {
        success: true,
        user: result.user,
        token: await result.user.getIdToken()
      };
    } catch (error) {
      return {
        success: false,
        error: error.code,
        message: error.message
      };
    }
  }


  // Sign Out
  async signOut() {
    try {
      await signOut(this.auth);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.code,
        message: error.message
      };
    }
  }

  // Get current user
  getCurrentUser() {
    return this.auth.currentUser;
  }

  // Listen to auth state changes
  onAuthStateChanged(callback) {
    return onAuthStateChanged(this.auth, callback);
  }

  // Get ID token
  async getIdToken() {
    const user = this.getCurrentUser();
    if (user) {
      return await user.getIdToken();
    }
    return null;
  }

  // Verify token with backend
  async verifyWithBackend(idToken) {
    const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
    const url = apiBase ? `${apiBase}/api/auth/verify` : '/api/auth/verify';

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ idToken }),
      });

      const text = await response.text();
      let data = null;
      try {
        data = text ? JSON.parse(text) : null;
      } catch (err) {
        // non-JSON response (HTML error page, empty, etc.)
        console.error('verifyWithBackend: non-JSON response', { url, status: response.status, text });
        return { success: false, error: `Server returned non-JSON response (status ${response.status})`, detail: text };
      }

      if (response.ok) {
        // backend returns { success: true, user }
        return { success: true, user: data.user || data };
      }

      // not ok - return backend-provided error if present
      const errMsg = (data && (data.error || data.message)) || `Server error ${response.status}`;
      console.error('verifyWithBackend failed', { url, status: response.status, body: data });
      return { success: false, error: errMsg, status: response.status, body: data };
    } catch (error) {
      console.error('verifyWithBackend network error', { url, error });
      return { success: false, error: 'Network error', detail: String(error) };
    }
  }
}

const authService = new AuthService();
export default authService;