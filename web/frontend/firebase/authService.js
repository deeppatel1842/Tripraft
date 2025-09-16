// /**
//  * Firebase authentication service
//  */
// import {
//   signInWithEmailAndPassword,
//   createUserWithEmailAndPassword,
//   signInWithPopup,
//   GoogleAuthProvider,
//   OAuthProvider,
//   signOut,
//   onAuthStateChanged,
//   updateProfile
// } from 'firebase/auth';
// import { auth } from './config';

// class AuthService {
//   constructor() {
//     this.auth = auth;
//     this.googleProvider = new GoogleAuthProvider();
//     this.appleProvider = new OAuthProvider('apple.com');
    
//     // Configure providers
//     this.googleProvider.setCustomParameters({
//       prompt: 'select_account'
//     });
//   }

//   // Email/Password Authentication
//   async signInWithEmail(email, password) {
//     try {
//       const result = await signInWithEmailAndPassword(this.auth, email, password);
//       return {
//         success: true,
//         user: result.user,
//         token: await result.user.getIdToken()
//       };
//     } catch (error) {
//       return {
//         success: false,
//         error: error.code,
//         message: error.message
//       };
//     }
//   }

//   async signUpWithEmail(email, password, displayName = '') {
//     try {
//       const result = await createUserWithEmailAndPassword(this.auth, email, password);
      
//       // Update display name if provided
//       if (displayName) {
//         await updateProfile(result.user, { displayName });
//       }
      
//       return {
//         success: true,
//         user: result.user,
//         token: await result.user.getIdToken()
//       };
//     } catch (error) {
//       return {
//         success: false,
//         error: error.code,
//         message: error.message
//       };
//     }
//   }

//   // Google Authentication
//   async signInWithGoogle() {
//     try {
//       const result = await signInWithPopup(this.auth, this.googleProvider);
//       return {
//         success: true,
//         user: result.user,
//         token: await result.user.getIdToken()
//       };
//     } catch (error) {
//       return {
//         success: false,
//         error: error.code,
//         message: error.message
//       };
//     }
//   }

//   // Apple Authentication
//   async signInWithApple() {
//     try {
//       const result = await signInWithPopup(this.auth, this.appleProvider);
//       return {
//         success: true,
//         user: result.user,
//         token: await result.user.getIdToken()
//       };
//     } catch (error) {
//       return {
//         success: false,
//         error: error.code,
//         message: error.message
//       };
//     }
//   }

//   // Sign Out
//   async signOut() {
//     try {
//       await signOut(this.auth);
//       return { success: true };
//     } catch (error) {
//       return {
//         success: false,
//         error: error.code,
//         message: error.message
//       };
//     }
//   }

//   // Get current user
//   getCurrentUser() {
//     return this.auth.currentUser;
//   }

//   // Listen to auth state changes
//   onAuthStateChanged(callback) {
//     return onAuthStateChanged(this.auth, callback);
//   }

//   // Get ID token
//   async getIdToken() {
//     const user = this.getCurrentUser();
//     if (user) {
//       return await user.getIdToken();
//     }
//     return null;
//   }

//   // Verify token with backend
//   async verifyWithBackend(idToken) {
//     try {
//       const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/auth/verify`, {
//         method: 'POST',
//         headers: {
//           'Content-Type': 'application/json',
//         },
//         body: JSON.stringify({ idToken }),
//       });

//       const data = await response.json();
      
//       if (response.ok) {
//         return {
//           success: true,
//           user: data.user
//         };
//       } else {
//         return {
//           success: false,
//           error: data.error
//         };
//       }
//     } catch (error) {
//       return {
//         success: false,
//         error: 'Network error'
//       };
//     }
//   }
// }

// export const authService = new AuthService();
// export default authService;


/**
 * Firebase authentication service (frontend)
 * - Uses VITE_API_BASE_URL from root .env if set
 * - Falls back to relative /api prefix so Vite proxy works in dev
 */
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  OAuthProvider,
  signOut,
  onAuthStateChanged,
  updateProfile
} from 'firebase/auth';
import { auth } from './config';

class AuthService {
  constructor() {
    this.auth = auth;
    this.googleProvider = new GoogleAuthProvider();
    this.appleProvider = new OAuthProvider('apple.com');

    this.googleProvider.setCustomParameters({ prompt: 'select_account' });

    const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
    // backend verification endpoint; uses /api prefix by default for proxy
    this.verifyUrl = base ? `${base}/api/auth/verify` : '/api/auth/verify';
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

  // Apple Authentication
  async signInWithApple() {
    try {
      const result = await signInWithPopup(this.auth, this.appleProvider);
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

  // Verify token with backend (POST /api/auth/verify)
  async verifyWithBackend(idToken) {
    if (!idToken) {
      return { success: false, error: 'missing idToken' };
    }

    try {
      const response = await fetch(this.verifyUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idToken })
      });

      const text = await response.text();
      let data;
      try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }

      if (!response.ok) {
        return { success: false, error: data.error || data };
      }

      // backend should return user info
      return { success: true, user: data };
    } catch (error) {
      return { success: false, error: 'Network error' };
    }
  }
}

export const authService = new AuthService();
export default authService;