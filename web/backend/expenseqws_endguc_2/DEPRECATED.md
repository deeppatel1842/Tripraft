# ⚠️ DEPRECATED: expense_engine_2

## Status: LEGACY CODE - DO NOT USE FOR NEW DEVELOPMENT

**Date Deprecated:** November 25, 2025  
**Replacement:** `expense_engine` (new repository-pattern architecture)

---

## Why Deprecated?

The `expense_engine_2` codebase has been replaced by the new `expense_engine` which provides:

✅ **Enterprise Architecture:**
- Clean repository-service-controller pattern
- Proper separation of concerns
- Type-safe models with Pydantic validation
- Comprehensive test coverage (103 tests)

✅ **Security:**
- RBAC middleware with real Firestore checks
- Compliance-grade audit logging
- Comprehensive Firestore security rules
- JWT authentication

✅ **Performance:**
- Incremental balance calculations (no expensive scans)
- Real-time Firestore listeners
- Optimistic UI updates with rollback
- Smart caching patterns (Phase 5)

✅ **Maintainability:**
- Zero hardcoded values
- Consistent error handling
- Comprehensive documentation
- Professional naming conventions

---

## Migration Status

| Component | Old (expense_engine_2) | New (expense_engine) | Status |
|-----------|------------------------|----------------------|--------|
| Models | Embedded in service.py | Pydantic models | ✅ Complete |
| Data Access | firebase_operations.py | Repository layer | ✅ Complete |
| Business Logic | service.py (2744 lines) | Service layer | ✅ Complete |
| API Routes | Monolithic | Modular blueprints | ✅ Complete |
| Security | Basic auth | RBAC + Audit | ✅ Complete |
| Real-time | Polling | Firestore listeners | ✅ Complete |
| Tests | Limited | 103 backend, ~55 frontend | ✅ Complete |
| Caching | Basic Redis | Smart invalidation | 🔄 Phase 5 |

---

## For Developers

### If You're Working on Old Code

**DO NOT:**
- ❌ Make new features in `expense_engine_2`
- ❌ Copy code from `expense_engine_2` to new code
- ❌ Import from `expense_engine_2` in new modules

**DO:**
- ✅ Use the new `expense_engine` for all work
- ✅ Port old features to new architecture
- ✅ Follow the migration guide in `EXPENSE_ENGINE_MIGRATION_COMPLETE_PLAN.md`

### If You Find a Bug in expense_engine_2

1. Check if it's already fixed in `expense_engine`
2. If yes, prioritize migrating that functionality
3. If no, fix it in `expense_engine` using proper patterns
4. Document the fix in the migration plan

---

## Files in This Directory

### Core Files (DEPRECATED)
- `service.py` - Monolithic service layer (2744 lines) → Replaced by `expense_engine/services/*`
- `firebase_operations.py` - Direct Firestore ops → Replaced by `expense_engine/repositories/*`
- `enums.py` - Business enums → Replaced by `expense_engine/constants.py`
- `validators.py` - Input validation → Replaced by Pydantic models
- `email_service.py` - Email sending → Replaced by `expense_engine/workers/email_worker.py`

### Supporting Files
- `idempotency.py` - Idempotency keys (still useful reference)
- `firestore_counter.py` - Distributed counters (still useful reference)
- `docs/` - Old documentation (superseded by new docs)

---

## Timeline

- **Created:** 2024 (exact date unknown)
- **Active Development:** 2024-2025
- **Deprecation:** November 25, 2025
- **Planned Removal:** Q2 2026 (after 6 months of no active usage)

---

## Questions?

See the new architecture documentation:
- `expense_engine/EXPENSE_ENGINE_MIGRATION_COMPLETE_PLAN.md`
- `expense_engine/README.md`
- `EXPENSE_ENGINE_MIGRATION_PLAN.md` (root directory)

Contact the development team for migration assistance.
