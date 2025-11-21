"""
Admin API Access Guide & Testing Script
Run this to test all admin endpoints and get access instructions
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5001"
API_PREFIX = "/api/expense"

def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_public_endpoints():
    """Test endpoints that don't require authentication"""
    print_section("🌐 PUBLIC ENDPOINTS (No Auth Required)")
    
    endpoints = [
        ("Health Check", f"{API_PREFIX}/health", "GET"),
        ("Categories", f"{API_PREFIX}/categories", "GET"),
        ("Split Types", f"{API_PREFIX}/split-types", "GET"),
    ]
    
    for name, endpoint, method in endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            print(f"\n📍 {name}")
            print(f"   URL: {url}")
            print(f"   Method: {method}")
            
            response = requests.get(url, timeout=5)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS")
                
                # Show sample of response
                if isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    print(f"   Response keys: {keys}")
                elif isinstance(data, list):
                    print(f"   Response items: {len(data)}")
            else:
                print(f"   ❌ FAILED: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

def test_authenticated_endpoints(token):
    """Test endpoints that require authentication"""
    print_section("🔒 AUTHENTICATED ENDPOINTS (Require Firebase Token)")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    endpoints = [
        ("User Profile", f"{API_PREFIX}/user", "GET"),
        ("User Groups", f"{API_PREFIX}/groups", "GET"),
        ("User Invitations", f"{API_PREFIX}/invitations", "GET"),
    ]
    
    for name, endpoint, method in endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            print(f"\n📍 {name}")
            print(f"   URL: {url}")
            print(f"   Method: {method}")
            
            response = requests.get(url, headers=headers, timeout=5)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS")
                
                # Show sample of response
                if isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    print(f"   Response keys: {keys}")
            elif response.status_code == 401:
                print(f"   ⚠️  UNAUTHORIZED: Invalid or expired token")
            else:
                print(f"   ❌ FAILED: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

def test_performance_endpoints(token):
    """Test performance monitoring endpoints"""
    print_section("📊 PERFORMANCE MONITORING ENDPOINTS")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    endpoints = [
        ("Performance Report", f"{API_PREFIX}/performance/report?date={today}", "GET"),
        ("Slow Operations", f"{API_PREFIX}/performance/slow-operations", "GET"),
        ("Firestore Costs", f"{API_PREFIX}/performance/costs?date={today}", "GET"),
    ]
    
    for name, endpoint, method in endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            print(f"\n📍 {name}")
            print(f"   URL: {url}")
            print(f"   Method: {method}")
            
            response = requests.get(url, headers=headers, timeout=5)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS")
                
                # Show sample of response
                if 'report' in data:
                    report = data['report']
                    print(f"   📈 API Calls: {report.get('api_calls_count', 0)}")
                    print(f"   ⚡ Avg Response: {report.get('avg_response_time_ms', 0):.0f}ms")
                elif 'slow_operations' in data:
                    slow_ops = data['slow_operations']
                    print(f"   🐌 Slow Operations: {len(slow_ops)}")
                elif 'costs' in data:
                    costs = data['costs']
                    print(f"   💰 Reads: {costs.get('reads', 0)}")
                    print(f"   💰 Writes: {costs.get('writes', 0)}")
                    print(f"   💰 Cost: ${costs.get('total_cost_usd', 0):.4f}")
                    
            elif response.status_code == 401:
                print(f"   ⚠️  UNAUTHORIZED: Invalid or expired token")
            else:
                print(f"   ❌ FAILED: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

def print_instructions():
    """Print instructions for getting authentication token"""
    print_section("🔑 HOW TO GET FIREBASE AUTHENTICATION TOKEN")
    
    print("""
📋 STEP-BY-STEP GUIDE:

1️⃣  OPEN YOUR BROWSER CONSOLE
    - Open your TripRaft frontend (http://localhost:3000)
    - Press F12 or Right-click → Inspect
    - Go to Console tab

2️⃣  GET YOUR TOKEN (Run this in console):
    
    // Copy and paste this code:
    firebase.auth().currentUser.getIdToken().then(token => {
        console.log('TOKEN:', token);
        navigator.clipboard.writeText(token);
        alert('Token copied to clipboard!');
    });

3️⃣  USE THE TOKEN
    - Token is automatically copied to clipboard
    - Paste it when running this script with --token parameter
    - Or set as environment variable: export FIREBASE_TOKEN="your_token_here"

4️⃣  RUN WITH TOKEN:
    
    python admin_api_guide.py --token "your_token_here"

⚠️  TOKEN EXPIRATION:
    - Firebase tokens expire after 1 hour
    - If you get 401 errors, get a new token using step 2

💡 ALTERNATIVE - Using Postman/Insomnia:
    1. Add header: Authorization: Bearer YOUR_TOKEN_HERE
    2. Make requests to http://localhost:5001/api/expense/*

🔗 ADMIN ENDPOINTS:
    
    PUBLIC (No token needed):
    ✅ GET  /api/expense/health              - System health
    ✅ GET  /api/expense/categories          - Expense categories
    ✅ GET  /api/expense/split-types         - Split types
    
    AUTHENTICATED (Token required):
    🔒 GET  /api/expense/user                - Your profile
    🔒 GET  /api/expense/groups              - Your groups
    🔒 GET  /api/expense/invitations         - Your invitations
    
    PERFORMANCE MONITORING (Token required):
    📊 GET  /api/expense/performance/report           - Daily performance report
    📊 GET  /api/expense/performance/slow-operations  - Slow API calls (>1s)
    📊 GET  /api/expense/performance/costs            - Firestore usage & costs
    
    CACHE MANAGEMENT (Token required):
    🗑️  DELETE /api/expense/cache/<key>              - Clear specific cache
    🗑️  POST   /api/expense/cache/clear-all          - Clear all caches
    📋 GET    /api/expense/cache/stats               - Cache statistics
    """)

def main():
    """Main test function"""
    import sys
    
    print("\n" + "="*80)
    print("  🎯 TRIPRAFT ADMIN API ACCESS GUIDE")
    print("="*80)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        print(f"\n✅ Server is running at {BASE_URL}")
        print(f"   Status: {response.json().get('status', 'unknown')}")
    except Exception as e:
        print(f"\n❌ Server not running at {BASE_URL}")
        print(f"   Error: {e}")
        print(f"\n💡 Start the server first:")
        print(f"   cd web/backend")
        print(f"   python run.py")
        return
    
    # Test public endpoints
    test_public_endpoints()
    
    # Check for token
    token = None
    if len(sys.argv) > 2 and sys.argv[1] == '--token':
        token = sys.argv[2]
    elif '--token' in sys.argv:
        idx = sys.argv.index('--token')
        if idx + 1 < len(sys.argv):
            token = sys.argv[idx + 1]
    
    if token:
        print(f"\n🔑 Using provided token: {token[:20]}...")
        test_authenticated_endpoints(token)
        test_performance_endpoints(token)
    else:
        print("\n⚠️  No token provided - skipping authenticated endpoints")
        print_instructions()
    
    print("\n" + "="*80)
    print("  ✅ TESTING COMPLETE")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
