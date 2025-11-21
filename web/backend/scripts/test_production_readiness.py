"""
Production Readiness Test Suite
Comprehensive testing for all production changes
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from typing import Dict, List, Tuple
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)


class TestResult:
    """Test result container"""
    def __init__(self, name: str, passed: bool, message: str = "", duration: float = 0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration


class ProductionTestSuite:
    """Comprehensive test suite for production readiness"""
    
    def __init__(self, api_base_url: str = "http://localhost:5000"):
        self.api_base_url = api_base_url
        self.results: List[TestResult] = []
        self.token = None
    
    def print_header(self, text: str):
        """Print styled header"""
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}{text}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    def print_result(self, result: TestResult):
        """Print test result"""
        status = f"{Fore.GREEN}✅ PASS" if result.passed else f"{Fore.RED}❌ FAIL"
        print(f"{status}{Style.RESET_ALL} {result.name} ({result.duration:.2f}ms)")
        if result.message:
            print(f"   {Fore.YELLOW}→ {result.message}{Style.RESET_ALL}")
    
    def run_test(self, name: str, test_func) -> TestResult:
        """Run a single test"""
        start = time.time()
        try:
            passed, message = test_func()
            duration = (time.time() - start) * 1000
            result = TestResult(name, passed, message, duration)
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = TestResult(name, False, f"Exception: {str(e)}", duration)
        
        self.results.append(result)
        self.print_result(result)
        return result
    
    # =========================================================================
    # FILE EXISTENCE TESTS
    # =========================================================================
    
    def test_production_config_exists(self) -> Tuple[bool, str]:
        """Check if production_config.py exists"""
        path = Path(__file__).parent.parent / "expense_engine" / "production_config.py"
        exists = path.exists()
        return exists, f"Path: {path}"
    
    def test_logging_utils_exists(self) -> Tuple[bool, str]:
        """Check if logging_utils.py exists"""
        path = Path(__file__).parent.parent / "expense_engine" / "logging_utils.py"
        exists = path.exists()
        return exists, f"Path: {path}"
    
    def test_rate_limiter_exists(self) -> Tuple[bool, str]:
        """Check if rate_limiter.py exists"""
        path = Path(__file__).parent.parent / "expense_engine" / "rate_limiter.py"
        exists = path.exists()
        return exists, f"Path: {path}"
    
    def test_pagination_exists(self) -> Tuple[bool, str]:
        """Check if pagination.py exists"""
        path = Path(__file__).parent.parent / "expense_engine" / "pagination.py"
        exists = path.exists()
        return exists, f"Path: {path}"
    
    # =========================================================================
    # IMPORT TESTS
    # =========================================================================
    
    def test_import_production_config(self) -> Tuple[bool, str]:
        """Test importing production_config"""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from expense_engine.config.production_config import (
                AuthConfig, CacheConfig, RateLimitConfig,
                PaginationConfig, SecurityConfig
            )
            return True, "All config classes imported successfully"
        except Exception as e:
            return False, f"Import failed: {str(e)}"
    
    def test_import_logging_utils(self) -> Tuple[bool, str]:
        """Test importing logging_utils"""
        try:
            from expense_engine.utils.logging_utils import ProductionLogger, get_logger
            logger = get_logger(__name__)
            return True, "ProductionLogger initialized"
        except Exception as e:
            return False, f"Import failed: {str(e)}"
    
    def test_import_rate_limiter(self) -> Tuple[bool, str]:
        """Test importing rate_limiter"""
        try:
            from expense_engine.utils.rate_limiter import RateLimiter, rate_limit
            return True, "RateLimiter imported"
        except Exception as e:
            return False, f"Import failed: {str(e)}"
    
    def test_import_pagination(self) -> Tuple[bool, str]:
        """Test importing pagination"""
        try:
            from expense_engine.utils.pagination import PaginationParams, PaginatedResponse
            params = PaginationParams(page=1, page_size=50)
            assert params.offset == 0
            assert params.limit == 50
            return True, "Pagination working correctly"
        except Exception as e:
            return False, f"Import/test failed: {str(e)}"
    
    # =========================================================================
    # LOGGING TESTS
    # =========================================================================
    
    def test_logging_sanitization(self) -> Tuple[bool, str]:
        """Test data sanitization in logging"""
        try:
            from expense_engine.utils.logging_utils import ProductionLogger
            
            logger = ProductionLogger(__name__)
            
            # Test data with sensitive fields
            test_data = {
                'user_id': 'test_user_123',
                'email': 'test@example.com',
                'password': 'secret123',
                'token': 'abc123',
                'amount': 100
            }
            
            sanitized = logger.sanitize_data(test_data)
            
            # Check sanitization
            assert sanitized['password'] == '[REDACTED]', "Password not sanitized"
            assert sanitized['token'] == '[REDACTED]', "Token not sanitized"
            assert '*' in sanitized['email'], "Email not masked"
            assert sanitized['amount'] == 100, "Amount should not be sanitized"
            
            return True, "Data sanitization working correctly"
        except Exception as e:
            return False, f"Sanitization test failed: {str(e)}"
    
    def test_logging_hash_id(self) -> Tuple[bool, str]:
        """Test user ID hashing"""
        try:
            from expense_engine.utils.logging_utils import ProductionLogger
            
            user_id = "iJol3n5TFrVHdH79hS32WLCI2EK2"
            hashed = ProductionLogger.hash_id(user_id)
            
            # Should show first 8 chars + hash
            assert len(hashed) > len(user_id[:8]), "Hash too short"
            assert '***' in hashed, "Hash format incorrect"
            
            return True, f"ID hashed: {user_id[:8]}... → {hashed}"
        except Exception as e:
            return False, f"Hash test failed: {str(e)}"
    
    # =========================================================================
    # RATE LIMITING TESTS
    # =========================================================================
    
    def test_rate_limiter_memory_mode(self) -> Tuple[bool, str]:
        """Test rate limiter in memory mode"""
        try:
            from expense_engine.utils.rate_limiter import RateLimiter
            
            limiter = RateLimiter(redis_client=None)  # Memory mode
            
            # Test rate limit
            allowed, info = limiter.check_limit(max_calls=3, window_seconds=10, identifier="test_user")
            assert allowed, "First request should be allowed"
            assert info['remaining'] == 2, "Remaining should be 2"
            
            # Make 2 more requests
            limiter.check_limit(max_calls=3, window_seconds=10, identifier="test_user")
            limiter.check_limit(max_calls=3, window_seconds=10, identifier="test_user")
            
            # 4th request should be blocked
            allowed, info = limiter.check_limit(max_calls=3, window_seconds=10, identifier="test_user")
            assert not allowed, "4th request should be blocked"
            
            return True, "Rate limiting working correctly"
        except Exception as e:
            return False, f"Rate limit test failed: {str(e)}"
    
    # =========================================================================
    # PAGINATION TESTS
    # =========================================================================
    
    def test_pagination_params(self) -> Tuple[bool, str]:
        """Test pagination parameter validation"""
        try:
            from expense_engine.utils.pagination import PaginationParams
            from expense_engine.config.production_config import PaginationConfig
            
            # Test valid params
            params = PaginationParams(page=2, page_size=50)
            assert params.page == 2
            assert params.page_size == 50
            assert params.offset == 50
            assert params.limit == 50
            
            # Test page size clamping
            params_large = PaginationParams(page=1, page_size=1000)
            assert params_large.page_size == PaginationConfig.MAX_PAGE_SIZE
            
            params_small = PaginationParams(page=1, page_size=5)
            assert params_small.page_size == PaginationConfig.MIN_PAGE_SIZE
            
            return True, "Pagination validation working"
        except Exception as e:
            return False, f"Pagination test failed: {str(e)}"
    
    def test_paginated_response(self) -> Tuple[bool, str]:
        """Test paginated response structure"""
        try:
            from expense_engine.utils.pagination import PaginationParams, PaginatedResponse
            
            items = list(range(1, 101))  # 100 items
            params = PaginationParams(page=2, page_size=25)
            
            response = PaginatedResponse(
                items=items[params.offset:params.offset+params.limit],
                total=len(items),
                pagination=params
            )
            
            assert response.total == 100
            assert response.total_pages == 4
            assert response.has_next == True
            assert response.has_prev == True
            assert response.next_page == 3
            assert response.prev_page == 1
            
            return True, "Paginated response structure correct"
        except Exception as e:
            return False, f"Response test failed: {str(e)}"
    
    # =========================================================================
    # CONFIGURATION TESTS
    # =========================================================================
    
    def test_config_values(self) -> Tuple[bool, str]:
        """Test configuration default values"""
        try:
            from expense_engine.config.production_config import (
                CacheConfig, RateLimitConfig, PaginationConfig,
                SecurityConfig, PerformanceConfig
            )
            
            # Test cache TTLs
            assert CacheConfig.TTL_USER > 0
            assert CacheConfig.TTL_GROUP > 0
            
            # Test rate limits
            assert RateLimitConfig.AUTH_MAX_CALLS > 0
            assert RateLimitConfig.API_MAX_CALLS > 0
            
            # Test pagination
            assert PaginationConfig.MAX_PAGE_SIZE <= 100
            assert PaginationConfig.MIN_PAGE_SIZE >= 1
            
            # Test security
            assert SecurityConfig.HASH_ALGORITHM == 'sha256'
            assert len(SecurityConfig.SENSITIVE_FIELDS) > 0
            
            return True, "All config values valid"
        except Exception as e:
            return False, f"Config test failed: {str(e)}"
    
    # =========================================================================
    # SECURITY TESTS
    # =========================================================================
    
    def test_no_credential_leaks(self) -> Tuple[bool, str]:
        """Check for credential leaks in code"""
        try:
            backend_path = Path(__file__).parent.parent / "expense_engine"
            
            dangerous_patterns = [
                (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
                (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
                (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
            ]
            
            issues = []
            for py_file in backend_path.glob('*.py'):
                content = py_file.read_text()
                for pattern, description in dangerous_patterns:
                    import re
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append(f"{py_file.name}: {description}")
            
            if issues:
                return False, f"Security issues found: {', '.join(issues)}"
            
            return True, "No credential leaks detected"
        except Exception as e:
            return False, f"Security scan failed: {str(e)}"
    
    # =========================================================================
    # CLEANUP SCRIPT TEST
    # =========================================================================
    
    def test_cleanup_script_exists(self) -> Tuple[bool, str]:
        """Check if cleanup script exists"""
        path = Path(__file__).parent / "cleanup_logs.py"
        exists = path.exists()
        
        if exists:
            # Check if it's executable
            content = path.read_text()
            has_main = "if __name__ == '__main__':" in content
            has_argparse = "import argparse" in content
            
            if not has_main:
                return False, "Script missing main entry point"
            if not has_argparse:
                return False, "Script missing argparse"
            
            return True, "Cleanup script ready to use"
        
        return False, f"Script not found at {path}"
    
    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    
    def run_all(self):
        """Run all tests"""
        self.print_header("PRODUCTION READINESS TEST SUITE")
        
        # File Existence Tests
        self.print_header("1. File Existence Tests")
        self.run_test("Production Config File", self.test_production_config_exists)
        self.run_test("Logging Utils File", self.test_logging_utils_exists)
        self.run_test("Rate Limiter File", self.test_rate_limiter_exists)
        self.run_test("Pagination File", self.test_pagination_exists)
        self.run_test("Cleanup Script File", self.test_cleanup_script_exists)
        
        # Import Tests
        self.print_header("2. Import Tests")
        self.run_test("Import Production Config", self.test_import_production_config)
        self.run_test("Import Logging Utils", self.test_import_logging_utils)
        self.run_test("Import Rate Limiter", self.test_import_rate_limiter)
        self.run_test("Import Pagination", self.test_import_pagination)
        
        # Functionality Tests
        self.print_header("3. Logging Tests")
        self.run_test("Data Sanitization", self.test_logging_sanitization)
        self.run_test("User ID Hashing", self.test_logging_hash_id)
        
        self.print_header("4. Rate Limiting Tests")
        self.run_test("Rate Limiter (Memory Mode)", self.test_rate_limiter_memory_mode)
        
        self.print_header("5. Pagination Tests")
        self.run_test("Pagination Parameters", self.test_pagination_params)
        self.run_test("Paginated Response", self.test_paginated_response)
        
        self.print_header("6. Configuration Tests")
        self.run_test("Config Values", self.test_config_values)
        
        self.print_header("7. Security Tests")
        self.run_test("No Credential Leaks", self.test_no_credential_leaks)
        
        # Print Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        pass_rate = (passed / len(self.results)) * 100 if self.results else 0
        
        self.print_header("TEST SUMMARY")
        print(f"Total Tests: {len(self.results)}")
        print(f"{Fore.GREEN}Passed: {passed}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {failed}{Style.RESET_ALL}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        if failed > 0:
            print(f"\n{Fore.RED}❌ TESTS FAILED{Style.RESET_ALL}")
            print("\nFailed Tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  • {result.name}: {result.message}")
            sys.exit(1)
        else:
            print(f"\n{Fore.GREEN}✅ ALL TESTS PASSED{Style.RESET_ALL}")
            print("\n🚀 System is production-ready!")
            sys.exit(0)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test production readiness')
    parser.add_argument('--api-url', default='http://localhost:5000',
                       help='API base URL')
    
    args = parser.parse_args()
    
    suite = ProductionTestSuite(api_base_url=args.api_url)
    suite.run_all()


if __name__ == '__main__':
    main()
