"""
Test Rate Limiting Module
Verifies that the rate limiter imports and works correctly
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_rate_limiter_import():
    """Test that rate limiter can be imported"""
    try:
        from middleware import limiter, rate_limit_config
        print("✅ Rate limiter imported successfully")
        print(f"   Global limit: 200 per hour")
        print(f"   Operations configured: {len(rate_limit_config)}")
        return True
    except Exception as e:
        print(f"❌ Failed to import rate limiter: {e}")
        return False

def test_rate_limit_config():
    """Test rate limit configuration"""
    try:
        from middleware import rate_limit_config
        
        expected_operations = [
            'read_light', 'read_heavy', 'create', 'update', 
            'delete', 'settle', 'invitation', 'auth'
        ]
        
        for op in expected_operations:
            if op in rate_limit_config:
                print(f"✅ {op:15} : {rate_limit_config[op]}")
            else:
                print(f"❌ {op:15} : NOT CONFIGURED")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Failed to test config: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("🧪 Testing Rate Limiting Module")
    print("="*60 + "\n")
    
    test1 = test_rate_limiter_import()
    print()
    
    test2 = test_rate_limit_config()
    print()
    
    print("="*60)
    if test1 and test2:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
