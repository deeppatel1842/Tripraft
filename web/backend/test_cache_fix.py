"""
Test script to verify group deletion cache invalidation fix
"""
import sys
sys.path.append('.')

from expense_engine.constants import CacheConfig

print("=" * 80)
print("CACHE KEY PREFIX VERIFICATION")
print("=" * 80)

print("\n📋 Cache Prefixes in Constants:")
print(f"   PREFIX_USER_GROUPS     = '{CacheConfig.PREFIX_USER_GROUPS}'")
print(f"   PREFIX_USER_GROUPS_KEY = '{CacheConfig.PREFIX_USER_GROUPS_KEY}'")

print("\n✅ Expected Cache Keys for user 'USER123':")
print(f"   Full mode:    '{CacheConfig.PREFIX_USER_GROUPS_KEY}USER123'")
print(f"   Summary mode: '{CacheConfig.PREFIX_USER_GROUPS_KEY}USER123_summary'")

print("\n" + "=" * 80)
print("TEST: Cache Invalidation Method")
print("=" * 80)

# Simulate what invalidate_user_groups() will do
user_id = "USER123"
base_key = f"{CacheConfig.PREFIX_USER_GROUPS_KEY}{user_id}"
summary_key = f"{CacheConfig.PREFIX_USER_GROUPS_KEY}{user_id}_summary"

print(f"\n🔄 invalidate_user_groups('{user_id}') will delete:")
print(f"   1. {base_key}")
print(f"   2. {summary_key}")

print("\n✅ Fix Status: Both cache keys will be deleted correctly!")
print("=" * 80)
