# 🚀 Phase 2.8 - React Query, Rate Limiting & Monitoring

**Start Date**: November 19, 2025  
**Status**: 🎯 READY TO START  
**Prerequisites**: Phase 2.7 complete, all bugs fixed  
**Goal**: Enterprise-grade performance, security, and observability

---

## 📋 Overview

Phase 2.8 focuses on three critical production features:
1. **React Query**: Eliminate duplicate API calls, improve caching
2. **Rate Limiting**: Protect expensive operations, improve security
3. **Performance Monitoring**: Real-time observability and metrics

**Expected Impact**:
- 50% reduction in API calls
- Better security against abuse
- Proactive issue detection
- Enterprise-ready architecture

---

## 🎯 Task 1: React Query Implementation (Priority 1)

**Goal**: Prevent duplicate API calls, improve frontend caching  
**Effort**: 4-6 hours  
**Impact**: 50% fewer API calls, better UX

### Problem Statement

**Current Issues** (from logs):
```
Line 172-210: GET /api/expense/invitations called TWICE
  • First call: 6ms (cache hit)
  • Second call: 6ms (cache hit)
  • Reason: React Strict Mode double-mounting components
  • Impact: Unnecessary network requests

Line 285-312: Multiple parallel requests to same group
  • GET /groups/full
  • GET /settlements/group
  • GET /invitations/group
  • Could be combined or deduplicated
```

### Solution: React Query

React Query provides:
- Automatic request deduplication
- Smart caching with background refetching
- Retry logic with exponential backoff
- Optimistic updates (already have, but standardized)
- Stale-while-revalidate pattern

### Implementation Plan

#### Step 1: Install React Query (5 minutes)

```bash
cd web/frontend
npm install @tanstack/react-query @tanstack/react-query-devtools
```

#### Step 2: Setup Query Client (15 minutes)

**File**: `web/frontend/src/queryClient.js` (NEW)
```javascript
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cache settings
      staleTime: 1000 * 60 * 5,        // Data fresh for 5 minutes
      cacheTime: 1000 * 60 * 10,       // Cache for 10 minutes
      
      // Retry settings
      retry: 3,                         // Retry failed requests 3 times
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      
      // Refetch settings
      refetchOnWindowFocus: false,      // Don't refetch on window focus
      refetchOnReconnect: true,         // Refetch on network reconnect
      
      // Error handling
      useErrorBoundary: false,          // Don't throw errors to boundary
    },
    mutations: {
      retry: 1,                          // Retry mutations once
      retryDelay: 1000,
    }
  }
});
```

#### Step 3: Wrap App with QueryClientProvider (10 minutes)

**File**: `web/frontend/src/main.jsx`
```jsx
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from './queryClient';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
        {/* Dev tools only in development */}
        {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
);
```

#### Step 4: Convert API Hooks to React Query (2-3 hours)

**File**: `web/frontend/src/hooks/useExpenseQuery.js` (NEW)

```javascript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import expenseApi from '../services/expenseApi';

// Query Keys (centralized for easy invalidation)
export const queryKeys = {
  userProfile: ['user', 'profile'],
  userGroups: ['user', 'groups'],
  userExpenses: (personal = true) => ['user', 'expenses', { personal }],
  group: (groupId) => ['group', groupId],
  groupFull: (groupId) => ['group', groupId, 'full'],
  groupMembers: (groupId) => ['group', groupId, 'members'],
  groupBalances: (groupId) => ['group', groupId, 'balances'],
  groupExpenses: (groupId) => ['group', groupId, 'expenses'],
  groupSettlements: (groupId) => ['group', groupId, 'settlements'],
  invitations: ['invitations'],
  groupInvitations: (groupId) => ['invitations', 'group', groupId],
};

// User Groups Query
export const useUserGroupsQuery = () => {
  return useQuery({
    queryKey: queryKeys.userGroups,
    queryFn: async () => {
      const response = await expenseApi.getUserGroups();
      return response.groups || [];
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

// Full Group Data Query (combines multiple endpoints)
export const useGroupFullQuery = (groupId) => {
  return useQuery({
    queryKey: queryKeys.groupFull(groupId),
    queryFn: async () => {
      const response = await expenseApi.getGroupFull(groupId);
      return response;
    },
    enabled: !!groupId, // Only run when groupId exists
    staleTime: 1000 * 30, // 30 seconds (balances change frequently)
  });
};

// Group Settlements Query
export const useGroupSettlementsQuery = (groupId) => {
  return useQuery({
    queryKey: queryKeys.groupSettlements(groupId),
    queryFn: async () => {
      const response = await expenseApi.getGroupSettlements(groupId);
      return response.settlements || [];
    },
    enabled: !!groupId,
    staleTime: 1000 * 60, // 1 minute
  });
};

// Pending Invitations Query
export const usePendingInvitationsQuery = () => {
  return useQuery({
    queryKey: queryKeys.invitations,
    queryFn: async () => {
      const response = await expenseApi.getPendingInvitations();
      return response.invitations || [];
    },
    staleTime: 1000 * 30, // 30 seconds
  });
};

// Create Settlement Mutation
export const useCreateSettlementMutation = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (settlementData) => expenseApi.createSettlement(settlementData),
    onSuccess: (data, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: queryKeys.groupSettlements(variables.group_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.groupFull(variables.group_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.groupBalances(variables.group_id) });
    },
  });
};

// Create Expense Mutation
export const useCreateExpenseMutation = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (expenseData) => expenseApi.createExpense(expenseData),
    onSuccess: (data, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: queryKeys.groupExpenses(variables.group_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.groupFull(variables.group_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.groupBalances(variables.group_id) });
    },
  });
};

// Accept Invitation Mutation
export const useAcceptInvitationMutation = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (invitationId) => expenseApi.acceptInvitation(invitationId),
    onSuccess: () => {
      // Invalidate invitations and groups
      queryClient.invalidateQueries({ queryKey: queryKeys.invitations });
      queryClient.invalidateQueries({ queryKey: queryKeys.userGroups });
    },
  });
};
```

#### Step 5: Update Components (1-2 hours)

**Example: ExpenseManager.jsx**
```jsx
// BEFORE:
const { groups, loading, reload } = useUserGroups();

// AFTER:
import { useUserGroupsQuery } from '../../hooks/useExpenseQuery';

const { data: groups = [], isLoading, refetch } = useUserGroupsQuery();
```

**Example: PendingInvitations.jsx**
```jsx
// BEFORE:
const [invitations, setInvitations] = useState([]);
const [loading, setLoading] = useState(true);

useEffect(() => {
  loadPendingInvitations();
}, []);

// AFTER:
import { usePendingInvitationsQuery, useAcceptInvitationMutation } from '../../hooks/useExpenseQuery';

const { data: invitations = [], isLoading } = usePendingInvitationsQuery();
const acceptMutation = useAcceptInvitationMutation();

const handleAccept = (invitationId) => {
  acceptMutation.mutate(invitationId);
};
```

### Expected Results

**Before React Query**:
```
Invitation endpoint called: 2 times
Group full endpoint called: Multiple times on re-render
No automatic retry on failure
Manual cache invalidation needed
```

**After React Query**:
```
Invitation endpoint called: 1 time (deduplicated)
Group full endpoint: Cached for 30s, background refetch
Automatic retry: 3 attempts with exponential backoff
Smart cache invalidation: Automatic on mutations
```

**Performance Impact**:
- API calls: -50% (deduplication)
- Perceived load time: -30% (cache hits)
- Error resilience: +300% (retry logic)
- Code complexity: -20% (less manual state management)

---

## 🔒 Task 2: Rate Limiting (Priority 2)

**Goal**: Protect expensive operations and improve security  
**Effort**: 2 hours (SIMPLIFIED)  
**Impact**: Better security, cost protection

### Problem Statement

**Current Vulnerabilities**:
- No rate limiting on expensive operations
- Anyone can spam create expense/settlement endpoints
- No protection against brute force
- Could lead to high Firebase costs

### Solution: Flask-Limiter (Minimal Approach)

**Philosophy**: Keep it simple, reuse existing Redis

#### Step 1: Install Flask-Limiter (2 minutes)

```bash
cd web/backend
pip install Flask-Limiter
pip freeze > requirements.txt
```

#### Step 2: Create Rate Limiter (20 minutes)

**File**: `web/backend/expense_engine/middleware/__init__.py` (NEW - 5 lines)
```python
"""Middleware for rate limiting and security"""
from .rate_limiter import create_rate_limiter

__all__ = ['create_rate_limiter']
```

**File**: `web/backend/expense_engine/middleware/rate_limiter.py` (NEW - 60 lines)

```python
"""
Rate Limiting Middleware
Phase 2.8: Protect expensive operations and improve security
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from ..cache_operations import CacheOperations
from flask import request, g
import logging

logger = logging.getLogger(__name__)


def get_user_id():
    """Get user ID from request context for per-user rate limiting"""
    # Try to get from Flask g context (set by auth decorator)
    if hasattr(g, 'user_id'):
        return g.user_id
    
    # Fallback to IP address
    return get_remote_address()


class RateLimitConfig:
    """Rate limit rules for different operations"""
    
    # Global limits
    GLOBAL_LIMIT = "1000 per hour"
    
    # Read operations (cheap)
    READ_LIMIT = "100 per minute"
    
    # Write operations (moderate)
    CREATE_EXPENSE = "20 per minute"
    UPDATE_EXPENSE = "30 per minute"
    CREATE_GROUP = "10 per minute"
    
    # Expensive operations (strict)
    DELETE_EXPENSE = "10 per minute"
    CREATE_SETTLEMENT = "10 per minute"
    DELETE_GROUP = "5 per minute"
    
    # Auth operations (very strict)
    LOGIN_ATTEMPT = "5 per minute"
    SIGNUP_ATTEMPT = "3 per minute"
    
    # Invitation operations
    SEND_INVITATION = "10 per minute"
    ACCEPT_INVITATION = "20 per minute"


def create_rate_limiter(app, redis_client):
    """
    Create and configure rate limiter
    
    Args:
        app: Flask app instance
        redis_client: Redis client for rate limit storage
        
    Returns:
        Configured Limiter instance
    """
    limiter = Limiter(
        app=app,
        key_func=get_user_id,
        default_limits=[RateLimitConfig.GLOBAL_LIMIT],
        storage_uri=f"redis://{redis_client.connection_pool.connection_kwargs['host']}:"
                   f"{redis_client.connection_pool.connection_kwargs['port']}/1",
        strategy="fixed-window",  # or "moving-window" for more accuracy
        headers_enabled=True,      # Return rate limit info in headers
    )
    
    logger.info("✅ Rate limiter initialized")
    logger.info(f"   Global limit: {RateLimitConfig.GLOBAL_LIMIT}")
    logger.info(f"   Storage: Redis (database 1)")
    
    return limiter


def rate_limit_error_handler(e):
    """Custom error handler for rate limit exceeded"""
    logger.warning(f"⚠️  Rate limit exceeded: {request.remote_addr} → {request.path}")
    
    return {
        'success': False,
        'error': 'rate_limit_exceeded',
        'message': 'Too many requests. Please try again later.',
        'retry_after': e.description  # Seconds until limit resets
    }, 429
```

#### Step 3: Apply Rate Limits to Routes (1-2 hours)

**File**: `web/backend/expense_engine/routes/__init__.py`

```python
from flask_limiter import Limiter
from ..middleware.rate_limiter import create_rate_limiter, RateLimitConfig, rate_limit_error_handler

# Create limiter (initialized in app factory)
limiter = None

def init_rate_limiter(app, redis_client):
    """Initialize rate limiter with app"""
    global limiter
    limiter = create_rate_limiter(app, redis_client)
    limiter.init_app(app)
    
    # Register error handler
    app.errorhandler(429)(rate_limit_error_handler)
    
    return limiter
```

**File**: `web/backend/expense_engine/routes/expense_routes.py`

```python
from . import limiter
from ..middleware.rate_limiter import RateLimitConfig

@expense_routes_bp.route('/expenses', methods=['POST'])
@limiter.limit(RateLimitConfig.CREATE_EXPENSE)
@require_auth
def create_expense():
    """Create new expense (rate limited: 20/minute)"""
    # ... existing code

@expense_routes_bp.route('/expenses/<expense_id>', methods=['DELETE'])
@limiter.limit(RateLimitConfig.DELETE_EXPENSE)
@require_auth
def delete_expense(expense_id):
    """Delete expense (rate limited: 10/minute)"""
    # ... existing code
```

**File**: `web/backend/expense_engine/routes/settlement_routes.py`

```python
@settlement_bp.route('/settlements', methods=['POST'])
@limiter.limit(RateLimitConfig.CREATE_SETTLEMENT)
@require_auth
def create_settlement():
    """Create settlement (rate limited: 10/minute)"""
    # ... existing code
```

#### Step 4: Add Security Headers (30 minutes)

**File**: `web/backend/expense_engine/middleware/security_headers.py` (NEW)

```python
"""
Security Headers Middleware
Phase 2.8: Add security headers to all responses
"""

from flask import make_response

def add_security_headers(response):
    """Add security headers to response"""
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Control referrer information
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy (CSP)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline';"
    )
    
    # HSTS (only in production)
    # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response
```

### Expected Results

**Before Rate Limiting**:
```
User creates 100 expenses in 10 seconds: ✅ Allowed
Attacker spams delete endpoint: ✅ Allowed
High Firebase costs from abuse: ❌ Problem
```

**After Rate Limiting**:
```
User creates 20 expenses/minute: ✅ Allowed
User creates 21st expense: ❌ 429 (retry after 60s)
Attacker spam: ❌ Blocked at 10 requests
Firebase costs protected: ✅ Safe
```

---

## 📊 Task 3: Performance Monitoring Dashboard (Priority 3)

**Goal**: Real-time observability and proactive issue detection  
**Effort**: 6-8 hours  
**Impact**: 10x faster debugging, proactive monitoring

### Implementation

#### Step 1: Create Monitoring Module (1-2 hours)

**File**: `web/backend/expense_engine/monitoring/__init__.py`
**File**: `web/backend/expense_engine/monitoring/metrics_collector.py`
**File**: `web/backend/expense_engine/monitoring/performance_tracker.py`

#### Step 2: Add Performance Dashboard Endpoint (2-3 hours)

**Endpoint**: `GET /api/expense/admin/performance/dashboard`

Returns:
- API endpoint timing (p50, p95, p99)
- Cache hit rates by key type
- Firestore operation counts
- Error rates by endpoint
- Rate limit statistics

#### Step 3: Frontend Dashboard Component (3-4 hours)

Real-time metrics dashboard showing:
- Live API performance charts
- Cache performance graphs
- Error rate trends
- Cost projections

---

## 📅 Implementation Timeline

### Day 1: React Query (6 hours)
- [x] Install React Query
- [ ] Setup query client
- [ ] Create query hooks
- [ ] Update 3-4 components
- [ ] Test deduplication

### Day 2: Rate Limiting (4 hours)
- [ ] Install Flask-Limiter
- [ ] Create rate limit config
- [ ] Apply to expensive routes
- [ ] Add security headers
- [ ] Test rate limits

### Day 3: Monitoring (8 hours)
- [ ] Create monitoring module
- [ ] Add metrics collector
- [ ] Create dashboard endpoint
- [ ] Build frontend dashboard
- [ ] Test and deploy

---

## 🎯 Success Metrics

### React Query Targets:
- ✅ API calls reduced by 50%
- ✅ Cache hit rate >80%
- ✅ Automatic retry on failures
- ✅ No more duplicate calls

### Rate Limiting Targets:
- ✅ All expensive endpoints protected
- ✅ 429 responses for abuse
- ✅ Security headers on all responses
- ✅ Cost protection active

### Monitoring Targets:
- ✅ Real-time performance metrics
- ✅ Cache performance visible
- ✅ Error tracking active
- ✅ Cost monitoring working

---

**Status**: 🎯 **READY TO START PHASE 2.8**

**Next Action**: Install React Query and begin implementation
