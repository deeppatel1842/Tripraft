# Feature: Authentication and User Management

## Overview

TripRaft implements a stateless JWT-based authentication system with session tracking, token rotation, and multi-device support. Every protected endpoint requires a valid access token, delivered via httpOnly cookies or Bearer headers.

---

## System Flow

```
                       SIGNUP FLOW
                       ===========

User Browser                    Flask Backend                   Database
     │                               │                             │
     │  POST /api/v1/auth/signup     │                             │
     │  {email, password, name}      │                             │
     │──────────────────────────────>│                             │
     │                               │  SignupSchema validation    │
     │                               │  is_password_strong()       │
     │                               │  (8+ chars, upper, lower,   │
     │                               │   digit, special)           │
     │                               │                             │
     │                               │  Check email uniqueness     │
     │                               │─────────────────────────── >│
     │                               │                             │
     │                               │  hash_password(bcrypt, 12)  │
     │                               │  INSERT INTO users          │
     │                               │─────────────────────────── >│
     │                               │                             │
     │                               │  create_access_token()      │
     │                               │  (15-min TTL, HS256)        │
     │                               │                             │
     │                               │  create_refresh_token()     │
     │                               │  (30-day TTL)               │
     │                               │                             │
     │                               │  INSERT INTO user_sessions  │
     │                               │  (refresh_token, device)    │
     │                               │─────────────────────────── >│
     │                               │                             │
     │  Set-Cookie: access_token     │                             │
     │  (httpOnly, Secure, SameSite) │                             │
     │  Set-Cookie: refresh_token    │                             │
     │  (httpOnly, Secure, SameSite) │                             │
     │  Body: {user, tokens}         │                             │
     │ <─────────────────────────────│                             │


                       LOGIN FLOW
                       ==========

User Browser                    Flask Backend                   Database
     │                               │                             │
     │  POST /api/v1/auth/login      │                             │
     │  {email, password}            │                             │
     │──────────────────────────────>│                             │
     │                               │  LoginSchema validation     │
     │                               │  SELECT user by email       │
     │                               │─────────────────────────── >│
     │                               │                             │
     │                               │  verify_password(bcrypt)    │
     │                               │  constant-time comparison   │
     │                               │                             │
     │                               │  Same token + session       │
     │                               │  creation as signup         │
     │                               │                             │
     │  Set-Cookie: tokens           │                             │
     │  Body: {user, tokens}         │                             │
     │ <─────────────────────────────│                             │


                       TOKEN REFRESH
                       =============

User Browser                    Flask Backend                   Database
     │                               │                             │
     │  POST /api/v1/auth/refresh    │                             │
     │  Cookie: refresh_token        │                             │
     │──────────────────────────────>│                             │
     │                               │  decode_token(type=refresh) │
     │                               │  Check signature + expiry   │
     │                               │                             │
     │                               │  Lookup session by token    │
     │                               │─────────────────────────── >│
     │                               │  Session found + not expired│
     │                               │                             │
     │                               │  ROTATE: new refresh token  │
     │                               │  UPDATE session record      │
     │                               │─────────────────────────── >│
     │                               │                             │
     │                               │  New access + refresh pair  │
     │  Set-Cookie: new tokens       │                             │
     │ <─────────────────────────────│                             │


                       PROTECTED REQUEST
                       =================

User Browser                    Flask Backend                   Database
     │                               │                             │
     │  GET /api/v1/gp/groups        │                             │
     │  Cookie: access_token         │                             │
     │  X-CSRF-Token: {double-submit}│                             │
     │──────────────────────────────>│                             │
     │                               │                             │
     │                          @require_auth                      │
     │                          ┌────────────────────────┐         │
     │                          │ 1. Extract token from  │         │
     │                          │    Cookie or Bearer    │         │
     │                          │ 2. decode_token(access)│         │
     │                          │    verify HS256 sig    │         │
     │                          │    check expiry        │         │
     │                          │ 3. Query user by ID    │──────── >│
     │                          │ 4. Set g.user_id       │         │
     │                          │    Set g.user_email    │         │
     │                          │    Set g.token_payload │         │
     │                          │ 5. Call route handler  │         │
     │                          └────────────────────────┘         │
     │                               │                             │
     │  200 OK {data: [...]}         │                             │
     │ <─────────────────────────────│                             │
```

---

## Components

### Backend

| File | Purpose |
|------|---------|
| `app/api/v1/auth.py` | 14 auth endpoints (signup, login, logout, refresh, profile, verify-email, etc.) |
| `app/api/v1/users.py` | Legacy user endpoints (parallel to auth.py for backward compatibility) |
| `app/services/auth_service.py` | AuthService: signup, login, refresh, logout, change_password, verify_email |
| `app/services/user_service.py` | UserService: get_user, update_profile, search_users |
| `app/domain/users/models.py` | User, UserSession, AuditLog SQLAlchemy models |
| `app/domain/users/repository.py` | UserRepository, UserSessionRepository (data access layer) |
| `app/infrastructure/auth/jwt.py` | create_access_token, create_refresh_token, verify_token, cookie helpers |
| `app/infrastructure/auth/password.py` | hash_password (bcrypt 12), verify_password, is_password_strong |
| `app/infrastructure/auth/decorators.py` | @require_auth, @optional_auth, @require_refresh_token, @require_group_role |
| `app/schemas/auth.py` | SignupSchema, LoginSchema, ChangePasswordSchema, CheckEmailSchema |
| `app/schemas/users.py` | Pydantic: UserRegisterRequest, UserLoginRequest, AuthResponse, TokenResponse |

### Frontend

| File | Purpose |
|------|---------|
| `src/context/AuthContext.jsx` | AuthProvider context: currentUser, signIn, signOut, token refresh on activity |
| `src/components/auth/jsx/AuthPage.jsx` | Tab switcher between Login and Signup views |
| `src/components/auth/jsx/Login.jsx` | Login form with drag-to-confirm slider, QR code display |
| `src/components/auth/jsx/Signup.jsx` | Registration form with terms agreement |
| `src/components/auth/jsx/ProtectedRoute.jsx` | Route wrapper that redirects unauthenticated users to /login |
| `src/components/auth/jsx/InactivityTracker.jsx` | 15-min inactivity auto-logout (mouse, keyboard, focus events) |
| `src/services/sqlAuthService.js` | Auth backend abstraction: login, register, refreshToken, getIdToken |
| `src/utils/apiClient.js` | HTTP client: auto-attaches JWT, CSRF headers, exponential backoff retries |

---

## Security Measures

| Measure | Implementation |
|---------|---------------|
| Password hashing | bcrypt with 12 work factor rounds |
| Password validation | 8+ chars, uppercase, lowercase, digit, special character |
| Token storage | httpOnly, Secure, SameSite cookies (not localStorage) |
| CSRF protection | Double-submit pattern (X-CSRF-Token header on mutations) |
| Token expiry | Access: 15 min, Refresh: 30 days |
| Token rotation | Refresh token rotated on every /refresh call |
| Session tracking | Each device/login tracked in user_sessions table |
| Logout all | DELETE all sessions = invalidate all devices |
| Inactivity logout | 15-min frontend timer, clears tokens and redirects |
| Constant-time compare | bcrypt.checkpw prevents timing attacks |
| Rate limiting | Login/signup endpoints rate-limited per IP and per user |

---

## Database Models

```
users
├── id (UUIDv7, PK)
├── email (String 255, unique, indexed)
├── password_hash (String 255)
├── display_name (String 100)
├── is_verified (Boolean)
├── created_at (DateTime, UTC)
└── updated_at (DateTime, UTC)

user_sessions
├── id (UUIDv7, PK)
├── user_id (FK → users.id)
├── refresh_token (String, indexed)
├── device_info (String)
├── ip_address (String)
├── expires_at (DateTime)
├── created_at (DateTime)
└── last_used_at (DateTime)

audit_log
├── id (UUIDv7, PK)
├── user_id (FK → users.id)
├── action (String: login, logout, password_change, etc.)
├── ip_address (String)
├── user_agent (String)
└── created_at (DateTime)
```

---

## API Endpoints

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|-----------|-------------|
| POST | `/auth/signup` | None | 5/min per IP | Create account |
| POST | `/auth/login` | None | 10/min per IP | Authenticate |
| POST | `/auth/logout` | Required | Standard | Invalidate current session |
| POST | `/auth/logout-all` | Required | Standard | Invalidate all sessions |
| POST | `/auth/refresh` | Refresh token | Standard | Rotate tokens |
| GET | `/auth/me` | Required | Standard | Get current user |
| PUT | `/auth/me` | Required | Standard | Update profile |
| POST | `/auth/change-password` | Required | 3/min | Change password |
| GET | `/auth/check-email` | None | 10/min | Check if email registered |
| POST | `/auth/verify-email` | None | Standard | Verify email with token |
| POST | `/auth/resend-verification` | Required | 3/min | Resend verification email |
