"""
Phase 1 & 2 Import Test
Validates all expense_engine core and middleware imports
"""

def test_phase_1_core():
    """Test Phase 1: Core foundation imports"""
    print("=" * 60)
    print("PHASE 1: Core Foundation")
    print("=" * 60)
    
    # Config
    from expense_engine.config import (
        config,
        firestore_collections,
        redis_config,
        rate_limit_config,
        business_rules,
        security_config
    )
    print("✅ Config module")
    print(f"   - Firestore: {firestore_collections.GROUPS}")
    print(f"   - Redis: {redis_config.HOST}:{redis_config.PORT}")
    print(f"   - Rate limits: {rate_limit_config.READS_PER_MINUTE} reads/min")
    
    # Constants
    from expense_engine.constants import (
        SplitType,
        Currency,
        GroupRole,
        Permission,
        check_permission
    )
    print("✅ Constants module")
    print(f"   - Split types: {[s.value for s in SplitType]}")
    print(f"   - Roles: {[r.value for r in GroupRole]}")
    print(f"   - Owner can delete group: {check_permission(GroupRole.OWNER, Permission.DELETE_GROUP)}")
    print(f"   - Member can delete group: {check_permission(GroupRole.MEMBER, Permission.DELETE_GROUP)}")
    
    # Exceptions
    from expense_engine.exceptions import (
        ExpenseEngineError,
        UnauthorizedError,
        ForbiddenError,
        RateLimitExceededError
    )
    print("✅ Exceptions module")
    print(f"   - Base error: {ExpenseEngineError.__name__}")
    print(f"   - Auth errors: {UnauthorizedError.__name__}, {ForbiddenError.__name__}")
    print(f"   - Rate limit: {RateLimitExceededError.__name__}")
    
    print("\n✅ Phase 1: PASSED\n")


def test_phase_2_middleware():
    """Test Phase 2: Security & Auth middleware imports"""
    print("=" * 60)
    print("PHASE 2: Security & Auth")
    print("=" * 60)
    
    # Auth middleware
    from expense_engine.middleware import (
        require_auth,
        optional_auth,
        require_group_member,
        get_current_user
    )
    print("✅ Auth middleware")
    print(f"   - Decorators: @require_auth, @optional_auth, @require_group_member")
    print(f"   - Helpers: get_current_user()")
    
    # RBAC middleware
    from expense_engine.middleware import (
        require_permission,
        require_role,
        require_owner,
        require_admin
    )
    print("✅ RBAC middleware")
    print(f"   - Permission checks: @require_permission, @require_role")
    print(f"   - Convenience: @require_owner, @require_admin")
    
    # Rate limiter
    from expense_engine.middleware import (
        RateLimiter,
        rate_limit_read,
        rate_limit_write
    )
    print("✅ Rate limiter")
    print(f"   - Class: {RateLimiter.__name__}")
    print(f"   - Decorators: @rate_limit_read, @rate_limit_write")
    
    print("\n✅ Phase 2: PASSED\n")


def test_collection_isolation():
    """Verify expense collections don't conflict with travel planner"""
    print("=" * 60)
    print("COLLECTION ISOLATION CHECK")
    print("=" * 60)
    
    from expense_engine.config import firestore_collections
    
    expense_collections = [
        firestore_collections.GROUPS,
        firestore_collections.GROUP_MEMBERS,
        firestore_collections.INVITATIONS,
        firestore_collections.EXPENSES,
        firestore_collections.SETTLEMENTS,
        firestore_collections.GROUP_BALANCES,
        firestore_collections.ACTIVITIES
    ]
    
    print("Expense Engine Collections:")
    for col in expense_collections:
        print(f"   - {col}")
        assert col.startswith("expense_"), f"Collection {col} must start with 'expense_'"
    
    print("\n✅ All collections use 'expense_' prefix")
    print("✅ No conflicts with 'travel_' collections")
    print()


if __name__ == "__main__":
    try:
        test_phase_1_core()
        test_phase_2_middleware()
        test_collection_isolation()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED")
        print("=" * 60)
        print("\nExpense Engine Phase 1 & 2 are ready!")
        print("Next: Phase 3 - Data Models (Pydantic)")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
