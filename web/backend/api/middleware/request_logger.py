"""
API Request Logger Middleware
Logs all incoming requests and outgoing responses with colors and timing
"""
import time
import logging
from flask import request, g
from functools import wraps

logger = logging.getLogger(__name__)

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def log_request():
    """Log incoming request"""
    g.start_time = time.time()
    
    # Skip health check spam
    if request.path == '/health':
        return
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}→ INCOMING REQUEST{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.GREEN}{request.method}{Colors.END} {request.path}")
    
    if request.query_string:
        print(f"{Colors.CYAN}Query:{Colors.END} {request.query_string.decode('utf-8')}")
    
    # Safely try to read JSON body
    if request.method in ['POST', 'PUT', 'PATCH']:
        try:
            # Check if there's actually content
            if request.content_length and request.content_length > 0:
                json_data = request.get_json(silent=True)
                if json_data:
                    print(f"{Colors.CYAN}Body:{Colors.END} {json_data}")
                else:
                    print(f"{Colors.CYAN}Body:{Colors.END} (empty or non-JSON)")
            else:
                print(f"{Colors.CYAN}Body:{Colors.END} (no content)")
        except Exception as e:
            print(f"{Colors.CYAN}Body:{Colors.END} (failed to parse: {e})")
    
    print(f"{Colors.CYAN}Origin:{Colors.END} {request.headers.get('Origin', 'N/A')}")
    print(f"{Colors.CYAN}User-Agent:{Colors.END} {request.headers.get('User-Agent', 'N/A')[:80]}")

def log_response(response):
    """Log outgoing response"""
    # Skip health check spam
    if request.path == '/health':
        return response
    
    duration = (time.time() - g.start_time) * 1000  # Convert to ms
    
    status_color = Colors.GREEN if response.status_code < 400 else Colors.RED
    
    print(f"\n{Colors.BOLD}{status_color}← RESPONSE{Colors.END}")
    print(f"{Colors.BOLD}Status:{Colors.END} {status_color}{response.status_code}{Colors.END}")
    print(f"{Colors.BOLD}Duration:{Colors.END} {Colors.YELLOW}{duration:.2f}ms{Colors.END}")
    
    # Try to show response data (if JSON)
    try:
        if response.is_json:
            data = response.get_json()
            if isinstance(data, dict):
                if 'success' in data:
                    print(f"{Colors.BOLD}Success:{Colors.END} {data['success']}")
                if 'message' in data:
                    print(f"{Colors.BOLD}Message:{Colors.END} {data['message']}")
                if 'data' in data and isinstance(data['data'], (list, dict)):
                    data_info = data['data']
                    if isinstance(data_info, list):
                        print(f"{Colors.BOLD}Data Count:{Colors.END} {len(data_info)}")
                    elif isinstance(data_info, dict):
                        print(f"{Colors.BOLD}Data Keys:{Colors.END} {list(data_info.keys())}")
    except Exception:
        pass
    
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")
    
    return response

def init_request_logger(app):
    """Initialize request logging"""
    app.before_request(log_request)
    app.after_request(log_response)
    
    logger.info(f"{Colors.GREEN}Request logger initialized{Colors.END}")
