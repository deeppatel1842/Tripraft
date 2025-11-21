/**
 * Firebase authentication service - Email/Password Only
 */
import { initializeApp } from 'firebase/app';
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
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

// Export app instance for other Firebase services (Firestore, Storage, etc.)
export { app };

class AuthService {
  constructor() {
    this.auth = auth;
  }

  // Email/Password Authentication
  async signInWithEmail(email, password) {
    console.log('\n' + '='.repeat(60));
    console.log('🔐 FIREBASE SIGN IN WITH EMAIL');
    console.log('='.repeat(60));
    console.log('📧 Email:', email);
    
    try {
      console.log('🔍 Calling Firebase signInWithEmailAndPassword...');
      const result = await signInWithEmailAndPassword(this.auth, email, password);
      console.log('✅ Firebase authentication successful!');
      console.log('👤 User ID:', result.user.uid);
      console.log('📧 Email:', result.user.email);
      console.log('✉️ Email Verified:', result.user.emailVerified);
      
      const token = await result.user.getIdToken();
      console.log('🎟️ Token obtained (length:', token.length, 'chars)');
      console.log('='.repeat(60) + '\n');
      
      return {
        success: true,
        user: result.user,
        token: token
      };
    } catch (error) {
      console.log('❌ Firebase authentication failed!');
      console.log('❌ Error code:', error.code);
      console.log('❌ Error message:', error.message);
      console.log('='.repeat(60) + '\n');
      
      return {
        success: false,
        error: error.code,
        message: error.message
      };
    }
  }

  async signUpWithEmail(email, password, displayName = '') {
    console.log('\n' + '='.repeat(60));
    console.log('📝 FIREBASE SIGN UP WITH EMAIL');
    console.log('='.repeat(60));
    console.log('📧 Email:', email);
    console.log('👤 Display Name:', displayName || 'Not provided');
    
    try {
      console.log('🔍 Creating user account...');
      const result = await createUserWithEmailAndPassword(this.auth, email, password);
      console.log('✅ Account created successfully!');
      console.log('👤 User ID:', result.user.uid);
      
      // Update display name if provided
      if (displayName) {
        console.log('📝 Updating display name...');
        await updateProfile(result.user, { displayName });
        console.log('✅ Display name updated!');
        
        // Reload user to get updated data
        await result.user.reload();
        console.log('🔄 User data reloaded with display name:', result.user.displayName);
      }
      
      const token = await result.user.getIdToken();
      console.log('🎟️ Token obtained (length:', token.length, 'chars)');
      console.log('='.repeat(60) + '\n');
      
      return {
        success: true,
        user: result.user,
        token: token
      };
    } catch (error) {
      console.log('❌ Sign up failed!');
      console.log('❌ Error code:', error.code);
      console.log('❌ Error message:', error.message);
      console.log('='.repeat(60) + '\n');
      
      return {
        success: false,
        error: error.code,
        message: error.message
      };
    }
  }

  // Sign Out
  async signOut() {
    console.log('\n' + '='.repeat(60));
    console.log('� SIGNING OUT');
    console.log('='.repeat(60));
    
    try {
      await signOut(this.auth);
      console.log('✅ Sign out successful!');
      console.log('='.repeat(60) + '\n');
      return { success: true };
    } catch (error) {
      console.log('❌ Sign out failed!');
      console.log('❌ Error:', error.message);
      console.log('='.repeat(60) + '\n');
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