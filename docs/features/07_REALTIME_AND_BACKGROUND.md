# Feature: Real-time Communication and Background Processing

## Overview

TripRaft uses Flask-SocketIO for real-time WebSocket communication and Celery with Redis for background task processing. This document covers both systems and how they integrate.

---

## Real-time (WebSocket) Architecture

### Connection Flow

```
Browser                          Flask-SocketIO Server          Redis
   │                                    │                         │
   │  WSS handshake                     │                         │
   │  ?token={access_token}             │                         │
   │═══════════════════════════════════>│                         │
   │                                    │                         │
   │                                    │  Verify JWT from        │
   │                                    │  handshake query param  │
   │                                    │                         │
   │                                    │  Set ws_user_id on      │
   │                                    │  socket session         │
   │                                    │                         │
   │  ack: connected                    │                         │
   │<═══════════════════════════════════│                         │
   │                                    │                         │
   │  emit: join_group                  │                         │
   │  {group_id: "abc-123"}             │                         │
   │═══════════════════════════════════>│                         │
   │                                    │                         │
   │                                    │  Verify membership      │
   │                                    │  (DB query)             │
   │                                    │                         │
   │                                    │  join_room('group:abc') │
   │                                    │                         │
   │                                    │  Track online status    │
   │                                    │──────────────────────── >│
   │                                    │                         │
   │  emit: presence:update             │                         │
   │  {online_members: [A, B]}          │                         │
   │<═══════════════════════════════════│  (to all in room)       │
   │                                    │                         │
   │  --- ONGOING EVENTS ---            │                         │
   │                                    │                         │
   │  When any user in group sends      │                         │
   │  a chat message via REST API:      │                         │
   │                                    │                         │
   │  Server emits to room:             │                         │
   │  chat:message {message_dict}       │                         │
   │<═══════════════════════════════════│                         │
   │                                    │                         │
   │  Frontend QueryClient              │                         │
   │  .invalidateQueries(['chat', id])  │                         │
   │  UI updates instantly              │                         │
```

### Event Catalog

| Event | Direction | When | Payload |
|-------|-----------|------|---------|
| `join_group` | Client → Server | Component mount | `{group_id}` |
| `leave_group` | Client → Server | Component unmount | `{group_id}` |
| `presence:update` | Server → Client | Join/leave | `{online_members: [{id, name}]}` |
| `chat:message` | Server → Client | New message sent | `{message_dict}` |
| `chat:typing` | Both | Typing indicator | `{user_id, typing: bool}` |
| `place:added` | Server → Client | Place created in group | `{place_dict}` |
| `place:voted` | Server → Client | Vote cast on place | `{place_id, vote_count}` |
| `poll:voted` | Server → Client | Vote cast on poll | `{poll_id, results}` |
| `checklist:toggled` | Server → Client | Checklist item toggled | `{item_id, is_completed}` |
| `itinerary:updated` | Server → Client | Itinerary doc changed | `{version, content}` |
| `member:joined` | Server → Client | New member accepted invite | `{member_dict}` |
| `member:left` | Server → Client | Member left group | `{user_id}` |
| `expense:created` | Server → Client | Expense added to group | `{expense_dict}` |
| `settlement:created` | Server → Client | Settlement recorded | `{settlement_dict}` |

### Frontend Socket Hooks

| Hook | File | Purpose |
|------|------|---------|
| `useGroupSocket` | `src/hooks/useGroupSocket.js` | Group events: place, poll, checklist, member, itinerary |
| `useChatSocket` | `src/hooks/useChatSocket.js` | Chat events: message, typing, read receipts |

Socket events trigger TanStack Query cache invalidation, causing affected components to re-render with fresh data. No manual state updates needed.

---

## Background Processing (Celery)

### Architecture

```
┌──────────────┐     ┌─────────────┐     ┌───────────────────┐
│  Flask App   │     │   Redis     │     │  Celery Workers   │
│              │     │   Broker    │     │                   │
│  .delay()    │────>│  Queue      │────>│  Execute task     │
│              │     │             │     │  Return result    │
└──────────────┘     └─────────────┘     └───────────────────┘
                            │
                            │
                     ┌──────▼──────┐
                     │ Celery Beat │
                     │ (Scheduler) │
                     │             │
                     │ Periodic    │
                     │ tasks on    │
                     │ cron        │
                     └─────────────┘
```

### Task Modules

#### Email Tasks (`app/workers/tasks/email_tasks.py`)

| Task | Trigger | Retry |
|------|---------|-------|
| `send_invitation_email` | Group/expense invitation created | 3x, backoff 60-600s |
| `send_verification_email` | User signup | 3x |
| `send_password_reset_email` | Password reset request | 3x |
| `send_expense_notification` | Expense created/modified | 3x |

#### Notification Tasks (`app/workers/tasks/notification_tasks.py`)

| Task | Trigger | Retry |
|------|---------|-------|
| `send_group_notification` | Group activity (member join, etc.) | 2x |
| `send_user_notification` | User-specific event | 2x |

#### AI Tasks (`app/workers/tasks/ai_tasks.py`)

| Task | Trigger | Retry |
|------|---------|-------|
| `process_scout_mention` | @scout in chat message | 2x, circuit breaker |
| `generate_chat_summary` | Manual or periodic | 1x |
| `cleanup_agent_logs` | Beat schedule (every 7 days) | 1x |

#### Crew Tasks (`app/workers/tasks/crew_tasks.py`)

| Task | Trigger | Retry |
|------|---------|-------|
| `process_crew_mention` | @crew in chat message | 2x |

#### Chat Tasks (`app/workers/tasks/chat_tasks.py`)

| Task | Trigger | Retry |
|------|---------|-------|
| `archive_old_messages` | Beat schedule or manual | 1x |
| `process_ai_mention` | Chat message with @mention | 2x |

#### Cleanup Tasks (`app/workers/tasks/cleanup_tasks.py`)

| Task | Trigger | Retry |
|------|---------|-------|
| `cleanup_expired_sessions` | Beat schedule (every 1 hour) | 1x |
| `archive_soft_deleted_records` | Beat schedule (every 24 hours) | 1x |

#### Analytics Tasks (`app/workers/tasks/analytics_tasks.py`)

| Task | Trigger | Retry |
|------|---------|-------|
| `warmup_search_cache` | Beat schedule (every 6 hours) | 1x |
| `aggregate_daily_metrics` | Beat schedule (every 24 hours) | 1x |

### Beat Schedule (5 Periodic Jobs)

| Job | Interval | Purpose |
|-----|----------|---------|
| Search cache warmup | Every 6 hours | Pre-populate Redis with popular search queries |
| Session cleanup | Every 1 hour | Delete expired user sessions from DB |
| Daily metrics | Every 24 hours | Aggregate daily stats (active users, expenses, etc.) |
| Soft-delete archival | Every 24 hours | Move 30-day-old soft-deleted records to archive |
| Agent log purge | Every 7 days | Delete old AI agent execution logs |

### Task Configuration

```
Broker:           Redis (config.CELERY_BROKER_URL)
Backend:          Redis (config.CELERY_RESULT_BACKEND)
Serializer:       JSON
Soft timeout:     120 seconds
Hard timeout:     180 seconds
Max retries:      3 (default)
Retry backoff:    Exponential (60s → 120s → 600s max)
Worker recycling: Every 1000 tasks (prevent memory leaks)
Dead letters:     redis:celery:dead_letters (failed after all retries)
Prefetch:         4 tasks per worker
```

---

## Components

### Backend (Real-time)

| File | Purpose |
|------|---------|
| `app/infrastructure/realtime/socketio_ext.py` | Flask-SocketIO instance, event handlers, auth handshake |
| `app/infrastructure/realtime/events.py` | Event type string constants |

### Backend (Celery)

| File | Purpose |
|------|---------|
| `app/workers/celery_app.py` | Celery instance, broker config, dead-letter handling |
| `app/workers/schedules.py` | CELERY_BEAT_SCHEDULE (5 periodic tasks) |
| `app/workers/tasks/email_tasks.py` | Email sending tasks |
| `app/workers/tasks/notification_tasks.py` | Notification tasks |
| `app/workers/tasks/ai_tasks.py` | Scout agent + summary + log cleanup |
| `app/workers/tasks/crew_tasks.py` | Crew agent execution |
| `app/workers/tasks/chat_tasks.py` | Chat archival + AI mention processing |
| `app/workers/tasks/cleanup_tasks.py` | Session + record cleanup |
| `app/workers/tasks/analytics_tasks.py` | Cache warmup + metrics |

### Frontend (Real-time)

| File | Purpose |
|------|---------|
| `src/hooks/useGroupSocket.js` | Group event subscription + cache invalidation |
| `src/hooks/useChatSocket.js` | Chat event subscription + message rendering |
