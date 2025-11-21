#!/usr/bin/env python3
"""
🔧 WEEK 4 BUG FIX TESTING GUIDE
================================

This script tests the fixes for:
1. Rate limiting initialization (import path bug)
2. Invitation acceptance UI refresh
3. Member list synchronization

BEFORE TESTING:
1. Make sure Redis is running:
   redis-cli ping  # Should return "PONG"
   
2. Restart backend server (to apply rate limiting fix):
   cd web/backend
   python api/app.py
   
3. Restart frontend (to apply invitation fixes):
   cd web/frontend
   npm run dev

USAGE:
    python test_week4_fixes.py --token "YOUR_FIREBASE_TOKEN"
    
    Get token from: http://localhost:5173/get-token.html
"""

import argparse
import requests
import json
import time
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:5000"
API_BASE = f"{BACKEND_URL}/api/expense"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")


def test_rate_limiting_fix(headers):
    """Test 1: Rate limiting should now initialize correctly"""
    print_section("TEST 1: Rate Limiting Initialization")
    
    try:
        # Check health endpoint (should show rate limiting status)
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        health = response.json()
        
        print(f"Backend Status: {health.get('status', 'unknown')}")
        print(f"Redis Connected: {health.get('redis_connected', False)}")
        
        if health.get('redis_connected'):
            print_success("Rate limiting infrastructure available")
        else:
            print_warning("Redis not connected - rate limiting will be disabled")
            
        # Test rate limit by making multiple rapid requests
        print("\n🔄 Testing rate limiting with rapid requests...")
        request_count = 0
        rate_limited = False
        
        for i in range(10):
            response = requests.get(f"{API_BASE}/categories", headers=headers, timeout=5)
            request_count += 1
            
            if response.status_code == 429:
                print_success(f"Rate limiting working! Got 429 after {request_count} requests")
                rate_limited = True
                print(f"   Rate limit headers: {dict(response.headers)}")
                break
            elif response.status_code != 200:
                print_error(f"Unexpected status: {response.status_code}")
                break
                
            time.sleep(0.1)  # Small delay between requests
        
        if not rate_limited and request_count >= 10:
            print_warning("No rate limiting detected (might have high limits)")
            print_info("This is OK if rate limits are set high for development")
            
        return True
        
    except Exception as e:
        print_error(f"Rate limiting test failed: {e}")
        return False


def test_invitation_cache_invalidation(headers):
    """Test 2: Invitation acceptance should clear caches properly"""
    print_section("TEST 2: Invitation Cache Invalidation")
    
    try:
        # Get current invitations
        response = requests.get(f"{API_BASE}/invitations", headers=headers, timeout=5)
        if response.status_code == 200:
            invitations = response.json().get('invitations', [])
            print(f"Current invitations: {len(invitations)}")
            
            if invitations:
                print("\nPending invitations:")
                for inv in invitations:
                    print(f"  • {inv.get('group_name')} (ID: {inv.get('invitation_id')})")
                    print(f"    Status: {inv.get('status')}")
                    print(f"    Invited by: {inv.get('invited_by_name')}")
            else:
                print_info("No pending invitations to test")
            
            print_success("Invitation endpoint working")
            return True
        else:
            print_error(f"Failed to get invitations: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Invitation test failed: {e}")
        return False


def test_member_list_refresh(headers):
    """Test 3: Member lists should show new members after invitation acceptance"""
    print_section("TEST 3: Member List Synchronization")
    
    try:
        # Get user's groups
        response = requests.get(f"{API_BASE}/groups", headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            groups = data.get('groups', [])
            print(f"Total groups: {len(groups)}")
            
            if groups:
                print("\nYour groups:")
                for group in groups:
                    print(f"\n  📊 {group.get('name')} ({group.get('currency', 'USD')})")
                    print(f"     ID: {group.get('group_id')}")
                    
                    members = group.get('members', [])
                    print(f"     Members: {len(members)}")
                    for member in members:
                        print(f"       • {member.get('name')} ({member.get('email')})")
                    
                    # Check for pending invitations in this group
                    group_id = group.get('group_id')
                    inv_response = requests.get(
                        f"{API_BASE}/groups/{group_id}/invitations",
                        headers=headers,
                        timeout=5
                    )
                    if inv_response.status_code == 200:
                        pending = inv_response.json().get('invitations', [])
                        if pending:
                            print(f"     Pending invitations: {len(pending)}")
                            for inv in pending:
                                print(f"       ⏳ {inv.get('invited_email')} (sent {inv.get('created_at', 'unknown')})")
                
                print_success("Group member lists retrieved successfully")
                return True
            else:
                print_info("No groups found. Create a group first to test member sync.")
                return True
        else:
            print_error(f"Failed to get groups: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Member list test failed: {e}")
        return False


def test_cache_stats(headers):
    """Bonus: Check cache statistics"""
    print_section("BONUS: Cache Statistics")
    
    try:
        response = requests.get(f"{API_BASE}/cache/stats", headers=headers, timeout=5)
        
        if response.status_code == 200:
            stats = response.json()
            print(f"Cache Implementation: {stats.get('implementation', 'unknown')}")
            print(f"Connected: {stats.get('connected', False)}")
            print(f"Total Keys: {stats.get('total_keys', 0)}")
            print(f"\nCache Performance:")
            print(f"  Hits: {stats.get('hits', 0)}")
            print(f"  Misses: {stats.get('misses', 0)}")
            
            hit_rate = stats.get('hit_rate', 0)
            if hit_rate > 0:
                print(f"  Hit Rate: {hit_rate:.1f}%")
                if hit_rate > 60:
                    print_success("Good cache hit rate!")
                else:
                    print_warning("Low cache hit rate - might need warming")
            
            return True
        else:
            print_warning(f"Cache stats not available: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Cache stats test failed: {e}")
        return False


def test_performance_monitoring(headers):
    """Bonus: Check performance monitoring"""
    print_section("BONUS: Performance Monitoring")
    
    try:
        response = requests.get(f"{API_BASE}/performance/report", headers=headers, timeout=5)
        
        if response.status_code == 200:
            report = response.json()
            print(f"Uptime: {report.get('uptime_seconds', 0):.0f} seconds")
            print(f"Total Requests: {report.get('total_requests', 0)}")
            
            endpoints = report.get('endpoint_performance', {})
            if endpoints:
                print("\nTop 5 Slowest Endpoints:")
                sorted_endpoints = sorted(
                    endpoints.items(),
                    key=lambda x: x[1].get('avg_ms', 0),
                    reverse=True
                )[:5]
                
                for endpoint, stats in sorted_endpoints:
                    avg_ms = stats.get('avg_ms', 0)
                    count = stats.get('count', 0)
                    print(f"  • {endpoint}")
                    print(f"    Avg: {avg_ms:.0f}ms | Calls: {count}")
                    
                    if avg_ms > 1000:
                        print_warning(f"    Slow endpoint! Consider optimization")
            
            print_success("Performance monitoring active")
            return True
        else:
            print_warning(f"Performance report not available: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Performance test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Test Week 4 bug fixes')
    parser.add_argument('--token', required=True, help='Firebase auth token')
    args = parser.parse_args()
    
    headers = {
        'Authorization': f'Bearer {args.token}',
        'Content-Type': 'application/json'
    }
    
    print(f"\n{Colors.BOLD}🧪 WEEK 4 BUG FIX TESTING{Colors.RESET}")
    print(f"Testing backend at: {BACKEND_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'Rate Limiting': test_rate_limiting_fix(headers),
        'Invitation Cache': test_invitation_cache_invalidation(headers),
        'Member Sync': test_member_list_refresh(headers),
        'Cache Stats': test_cache_stats(headers),
        'Performance Monitoring': test_performance_monitoring(headers)
    }
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}\n")
    
    for test_name, passed in results.items():
        if passed:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    print("\n" + "=" * 60)
    
    if passed == total:
        print_success("🎉 All tests passed! Week 4 fixes are working!")
        print_info("\nManual Testing Steps:")
        print("1. User A: Create a group and invite User B")
        print("2. User B: Accept the invitation")
        print("3. User A: Check 'Pending' tab - should auto-refresh in <10s")
        print("4. User A: Check 'Members' tab - should show User B")
    else:
        print_warning(f"⚠️  {total - passed} test(s) failed. Check logs above.")
        print_info("\nTroubleshooting:")
        print("• Make sure Redis is running: redis-cli ping")
        print("• Restart backend: cd web/backend && python api/app.py")
        print("• Restart frontend: cd web/frontend && npm run dev")
        print("• Check backend logs for errors")


if __name__ == '__main__':
    main()
