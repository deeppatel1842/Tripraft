# Phase 1 -- Security & Infrastructure Upgrade

Before we add any new features, the platform needs to be able to handle real users at scale. This phase is about swapping out development-grade infrastructure for production-grade infrastructure.

---

## Why This Comes First

```mermaid
flowchart TD
    A[Current State] --> B{Can we add AI?}
    B -->|Not safely| C[SQLite can't handle<br/>concurrent writes well]
    B -->|Not safely| D[No monitoring means<br/>we won't know when things break]
    B -->|Not safely| E[No auto-scaling means<br/>one viral moment kills us]
    
    C --> F[Fix infrastructure first]
    D --> F
    E --> F
    F --> G[Then build features on solid ground]
```

---

## Database Migration: SQLite to PostgreSQL

### Why

SQLite is great for development. It's a single file, no setup, instant. But it has hard limits:

- **No concurrent writes**: One write at a time. A group of 10 people all adding expenses simultaneously? Queued.
- **No user-level permissions**: Anyone with file access has full access.
- **No replication**: Can't have read replicas for performance.
- **File locking on NFS**: Breaks in some container environments.

### Migration Plan

```mermaid
flowchart TD
    A[Phase 1: Dual-write] --> B[Phase 2: Read from PostgreSQL]
    B --> C[Phase 3: Drop SQLite]
    
    A --> A1[Write to both SQLite + PostgreSQL]
    A --> A2[Read from SQLite still]
    A --> A3[Validate data matches]
    
    B --> B1[Flip reads to PostgreSQL]
    B --> B2[SQLite becomes backup only]
    B --> B3[Performance testing]
    
    C --> C1[Remove SQLite code paths]
    C --> C2[PostgreSQL is sole database]
    C --> C3[Full feature set: JSONB, full-text search, etc.]
```

### Schema Changes

The SQLAlchemy ORM we already use makes this relatively painless. The models don't change -- just the connection string.

But we'd want to take advantage of PostgreSQL features:

| Feature | SQLite | PostgreSQL | Benefit |
|---------|--------|------------|---------|
| JSONB columns | No | Yes | Store flexible data (preferences, metadata) |
| Full-text search | Basic | Built-in with ranking | Better place search |
| Array columns | No | Yes | Tags, categories without join tables |
| Concurrent writes | Limited | Unlimited | Multi-user real-time |
| Connection pooling | N/A | PgBouncer | Handle 1000+ connections |
| Replication | No | Built-in | Read replicas, backups |

### Travel Database

The `travel_data_complete.db` (16,830 places) also needs migration. Options:

1. **Migrate to PostgreSQL table**: Same DB, simpler architecture
2. **Move to Elasticsearch**: Better for fuzzy search and geo queries
3. **Keep as read-only SQLite**: It works fine for reads, low priority

Recommendation: Option 1 first (simplicity), Option 2 later when search volume justifies it.

### Estimated Effort

| Task | Time | Risk |
|------|------|------|
| Set up PostgreSQL (Supabase/Neon free tier) | 1 day | Low |
| Update SQLAlchemy connection config | 2 hours | Low |
| Run Alembic migrations on PostgreSQL | 1 day | Medium |
| Data migration script | 2 days | Medium |
| Dual-write testing | 3 days | Medium |
| Cutover and validation | 1 day | High |
| **Total** | **~8 days** | |

---

## Hosting & Deployment

### Current Setup

```mermaid
graph LR
    A[Developer Laptop] -->|docker-compose up| B[Flask + Redis<br/>localhost]
    C[Vercel] -->|static hosting| D[Frontend<br/>tripraft.vercel.app]
```

### Target Setup

```mermaid
graph TD
    subgraph "CDN Layer"
        A[Cloudflare / Vercel Edge]
    end
    
    subgraph "Frontend"
        B[Vercel<br/>React App]
    end
    
    subgraph "Backend"
        C[Railway / Render<br/>Flask API]
        D[Auto-scaling<br/>2-8 instances]
    end
    
    subgraph "Data Layer"
        E[Supabase / Neon<br/>PostgreSQL]
        F[Redis Cloud<br/>Cache + Rate Limits]
        G[S3 / R2<br/>User uploads]
    end
    
    subgraph "Services"
        H[Resend<br/>Email]
        I[Sentry<br/>Error tracking]
        J[PostHog<br/>Analytics]
    end
    
    A --> B
    B --> C
    C --> D
    C --> E
    C --> F
    C --> G
    C --> H
    C --> I
    C --> J
```

### Platform Comparison

| Platform | Free Tier | Scaling | Cost at 10K MAU | Docker Support | Best For |
|----------|-----------|---------|-----------------|----------------|----------|
| Railway | $5/mo credit | Auto | ~$25/mo | Yes | Backend + DB |
| Render | 750 hrs/mo | Manual/Auto | ~$25/mo | Yes | Simple deploys |
| Fly.io | 3 shared VMs | Auto | ~$20/mo | Yes | Global edge |
| Heroku | None anymore | Manual | ~$50/mo | Via buildpacks | Ecosystem |

**Recommendation**: Railway for backend (Docker support, good free tier, easy PostgreSQL add-on) + Vercel for frontend (already configured).

---

## Monitoring & Observability

### What We Need to Track

```mermaid
flowchart TD
    A[Monitoring Stack] --> B[Error Tracking<br/>Sentry]
    A --> C[Performance<br/>Response times, DB queries]
    A --> D[Uptime<br/>Is the API responding?]
    A --> E[Analytics<br/>User behavior]
    A --> F[Logs<br/>Structured, searchable]
    
    B --> B1[Capture every unhandled exception]
    B --> B2[Alert on error rate spikes]
    
    C --> C1[p50, p95, p99 latencies]
    C --> C2[Slow query detection]
    
    D --> D1[Health check endpoint]
    D --> D2[Alert if down > 1 min]
    
    E --> E1[Feature usage tracking]
    E --> E2[Conversion funnel]
    
    F --> F1[Centralized log aggregation]
    F --> F2[Search by user_id, request_id]
```

### Tool Selection

| Need | Tool | Cost | Why |
|------|------|------|-----|
| Error tracking | Sentry | Free (5K events/mo) | Industry standard, amazing stack traces |
| Analytics | PostHog | Free (1M events/mo) | Open source, feature flags included |
| Uptime monitoring | UptimeRobot | Free (50 monitors) | Simple, reliable, SMS alerts |
| Log aggregation | Better Stack | Free (1GB/mo) | Beautiful UI, structured log support |
| Performance | Sentry Performance | Included | Same tool, one integration |

Total monitoring cost at launch: **$0/month**

---

## CI/CD Pipeline

```mermaid
flowchart LR
    A[Push to GitHub] --> B[GitHub Actions]
    B --> C[Run Tests]
    B --> D[Lint & Type Check]
    C --> E{Tests Pass?}
    D --> E
    E -->|Yes| F[Build Docker Image]
    E -->|No| G[Block Merge]
    F --> H[Push to Registry]
    H --> I[Deploy to Staging]
    I --> J[Smoke Tests]
    J --> K{Pass?}
    K -->|Yes| L[Deploy to Production]
    K -->|No| M[Rollback]
```

We need:
1. **GitHub Actions workflow** for CI
2. **Automated tests** (currently minimal -- need to write them)
3. **Staging environment** (same as production but separate database)
4. **One-click rollback** (previous Docker image tag)

### Test Coverage Targets

| Layer | Current | Target | Priority |
|-------|---------|--------|----------|
| API routes | ~10% | 80% | High |
| Service layer | ~5% | 90% | High |
| Frontend components | 0% | 60% | Medium |
| Integration tests | 0% | 70% | Medium |
| E2E tests | 0% | 40% | Low (for now) |

---

## Security Hardening (Phase 2)

What we've done (Phase 0/1B) is the baseline. Production security adds:

| Feature | Status | Implementation |
|---------|--------|---------------|
| HTTPS everywhere | Handled by platform (Railway/Vercel) | Automatic |
| Content Security Policy | Not yet | Flask-Talisman middleware |
| SQL injection protection | Done (SQLAlchemy ORM) | Existing |
| XSS protection | Done (httpOnly cookies) | Existing |
| CSRF protection | Not yet | Flask-WTF or custom token |
| Secrets management | Environment variables | Move to vault if needed |
| Dependency scanning | Not yet | Dependabot or Snyk |
| Penetration testing | Not yet | After launch, periodic |

---

## Timeline

```mermaid
gantt
    title Phase 1: Infrastructure
    dateFormat YYYY-MM-DD
    
    section Database
    PostgreSQL setup          :a1, 2026-03-01, 2d
    Schema migration          :a2, after a1, 3d
    Data migration            :a3, after a2, 3d
    Dual-write validation     :a4, after a3, 4d
    
    section Hosting
    Railway backend setup     :b1, 2026-03-01, 2d
    Environment config        :b2, after b1, 1d
    DNS and SSL               :b3, after b2, 1d
    
    section Monitoring
    Sentry integration        :c1, after b3, 1d
    PostHog integration       :c2, after c1, 1d
    UptimeRobot setup         :c3, after c2, 1d
    
    section CI/CD
    GitHub Actions pipeline   :d1, after a4, 2d
    Staging environment       :d2, after d1, 2d
    
    section Testing
    Write API tests           :e1, 2026-03-01, 10d
    Write integration tests   :e2, after e1, 7d
```

**Estimated total: 3-4 weeks** with one developer working on it alongside other tasks.
