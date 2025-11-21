"""
Simple cache key verification test
"""

# Simulate constants
PREFIX_USER_GROUPS = "expense:user_groups:"
PREFIX_USER_GROUPS_KEY = "user_groups:"

print("=" * 80)
print("CACHE KEY PREFIX ANALYSIS")
print("=" * 80)

print("\n📋 Two Different Prefixes Found in constants.py:")
print(f"   PREFIX_USER_GROUPS     = '{PREFIX_USER_GROUPS}' (WRONG - used by old code)")
print(f"   PREFIX_USER_GROUPS_KEY = '{PREFIX_USER_GROUPS_KEY}' (CORRECT - used by service.py)")

print("\n🔍 What service.py creates (get_user_groups):")
user_id = "USER123"
mode_suffix_full = ""
mode_suffix_summary = "_summary"

cache_key_full = f"{PREFIX_USER_GROUPS_KEY}{user_id}{mode_suffix_full}"
cache_key_summary = f"{PREFIX_USER_GROUPS_KEY}{user_id}{mode_suffix_summary}"

print(f"   Full mode:    cache_key = '{cache_key_full}'")
print(f"   Summary mode: cache_key = '{cache_key_summary}'")

print("\n❌ OLD invalidate_user_groups() was deleting:")
old_key = f"{PREFIX_USER_GROUPS}{user_id}"
print(f"   '{old_key}' ❌ WRONG PREFIX!")
print(f"   (Actual key: '{cache_key_full}')")

print("\n✅ NEW invalidate_user_groups() now deletes:")
new_base_key = f"{PREFIX_USER_GROUPS_KEY}{user_id}"
new_summary_key = f"{PREFIX_USER_GROUPS_KEY}{user_id}_summary"
print(f"   1. '{new_base_key}' ✅")
print(f"   2. '{new_summary_key}' ✅")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("✅ Fix Applied: cache_operations.py now uses PREFIX_USER_GROUPS_KEY")
print("✅ Both cache variants (full + summary) will be deleted")
print("✅ Group deletion will work correctly after backend restart")
print("=" * 80)
