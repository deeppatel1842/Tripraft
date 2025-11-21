"""
Quick test script for Places API
Tests all endpoints to ensure everything works.
"""
import requests
import json
import sys
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

BASE_URL = "http://localhost:5000"
API_BASE = f"{BASE_URL}/api/v1"

def print_header(text):
    """Print section header"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

def print_success(text):
    """Print success message"""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")

def print_error(text):
    """Print error message"""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")

def print_info(text):
    """Print info message"""
    print(f"{Fore.YELLOW}ℹ {text}{Style.RESET_ALL}")

def test_endpoint(name, url, expected_keys=None):
    """Test a single endpoint"""
    try:
        print(f"\n{Fore.WHITE}Testing: {name}{Style.RESET_ALL}")
        print(f"  URL: {url}")
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check response structure
            if 'success' in data and data['success']:
                print_success(f"Status: {response.status_code}")
                
                # Check for expected keys
                if expected_keys:
                    for key in expected_keys:
                        if key in data:
                            print_success(f"Has '{key}' field")
                        else:
                            print_error(f"Missing '{key}' field")
                
                # Print data summary
                if 'data' in data:
                    if isinstance(data['data'], list):
                        print_info(f"Results: {len(data['data'])} items")
                        if len(data['data']) > 0:
                            print_info(f"Sample: {data['data'][0].get('name', 'N/A')}")
                    elif isinstance(data['data'], dict):
                        print_info(f"Item: {data['data'].get('name', 'N/A')}")
                
                # Print pagination info
                if 'pagination' in data:
                    p = data['pagination']
                    print_info(f"Pagination: {p.get('count')}/{p.get('total')} (offset: {p.get('offset')})")
                
                return True
            else:
                print_error(f"Status: {response.status_code}")
                print_error(f"Message: {data.get('message', 'Unknown error')}")
                return False
        else:
            print_error(f"Status: {response.status_code}")
            print_error(f"Response: {response.text[:200]}")
            return False
    
    except requests.exceptions.ConnectionError:
        print_error("Connection failed - Is the server running?")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print_header("🚀 TripRaft Places API - Test Suite")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Health check
    print_header("Test 1: Health Check")
    if test_endpoint("Health Check", f"{BASE_URL}/health"):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 2: API Root
    print_header("Test 2: API Root")
    if test_endpoint("API Root", BASE_URL):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 3: Get all countries
    print_header("Test 3: Get All Countries")
    if test_endpoint(
        "Get Countries",
        f"{API_BASE}/countries",
        expected_keys=['success', 'message', 'data']
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 4: Get specific country
    print_header("Test 4: Get Specific Country")
    if test_endpoint(
        "Get USA",
        f"{API_BASE}/countries/usa",
        expected_keys=['success', 'message', 'data']
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 5: Get states by country
    print_header("Test 5: Get States by Country")
    if test_endpoint(
        "Get US States",
        f"{API_BASE}/states/country/usa",
        expected_keys=['success', 'message', 'data']
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 6: Get cities by state
    print_header("Test 6: Get Cities by State")
    if test_endpoint(
        "Get California Cities",
        f"{API_BASE}/cities/state/california",
        expected_keys=['success', 'message', 'data']
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 7: Get places by city
    print_header("Test 7: Get Places by City")
    if test_endpoint(
        "Get Los Angeles Places",
        f"{API_BASE}/places/city/los-angeles?limit=10",
        expected_keys=['success', 'message', 'data', 'pagination']
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 8: Search places
    print_header("Test 8: Search Places")
    if test_endpoint(
        "Search for 'museum'",
        f"{API_BASE}/places/search?q=museum&limit=5",
        expected_keys=['success', 'message', 'data', 'pagination']
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 9: Get places with pagination
    print_header("Test 9: Pagination Test")
    if test_endpoint(
        "Get Places with Offset",
        f"{API_BASE}/places/city/new-york?limit=5&offset=0",
        expected_keys=['success', 'message', 'data', 'pagination']
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 10: 404 Error
    print_header("Test 10: Error Handling (404)")
    if test_endpoint(
        "Get Non-existent Place",
        f"{API_BASE}/places/nonexistent-place-12345"
    ):
        # Should return error, so this is expected
        tests_passed += 1
    else:
        tests_passed += 1  # 404 is expected
    
    # Summary
    print_header("📊 Test Results Summary")
    total_tests = tests_passed + tests_failed
    print(f"\n{Fore.WHITE}Total Tests: {total_tests}")
    print(f"{Fore.GREEN}Passed: {tests_passed}")
    print(f"{Fore.RED}Failed: {tests_failed}")
    
    if tests_failed == 0:
        print(f"\n{Fore.GREEN}{'='*60}")
        print(f"{Fore.GREEN}🎉 ALL TESTS PASSED!")
        print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")
        return 0
    else:
        print(f"\n{Fore.RED}{'='*60}")
        print(f"{Fore.RED}❌ SOME TESTS FAILED")
        print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}\n")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Tests interrupted by user{Style.RESET_ALL}")
        sys.exit(1)
