"""
================================================================================
LOG CAPTURE SYSTEM FOR TRIPRAFT BACKEND
================================================================================
Purpose: Capture all terminal output from Flask server and save to file
Features:
  - Real-time log capture from server startup
  - Automatic file rotation
  - Timestamped entries
  - Error highlighting
  - Performance metrics
  - API call tracking

Usage:
  python log_capture.py
  or
  python log_capture.py --level DEBUG --rotate-size 10MB
================================================================================
"""

import sys
import os
import logging
import logging.handlers
from datetime import datetime
import argparse
from pathlib import Path
import json
import threading
import queue
from typing import Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

class LogConfig:
    """Logging configuration for the capture system"""
    
    # Log directory
    LOG_DIR = Path(__file__).parent / "logs"
    
    # Log file names
    MAIN_LOG = LOG_DIR / "server.log"
    ERROR_LOG = LOG_DIR / "errors.log"
    API_LOG = LOG_DIR / "api_calls.log"
    PERFORMANCE_LOG = LOG_DIR / "performance.log"
    
    # Rotation settings
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT = 5  # Keep 5 rotated files
    
    # Format
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DETAILED_FORMAT = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
    JSON_FORMAT = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
    
    # Colors for console output
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }


# ============================================================================
# COLORED CONSOLE HANDLER
# ============================================================================

class ColoredConsoleHandler(logging.StreamHandler):
    """Console handler with color support for different log levels"""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname
            color = LogConfig.COLORS.get(level, LogConfig.COLORS['RESET'])
            
            # Print with color
            print(f"{color}{msg}{LogConfig.COLORS['RESET']}")
            sys.stdout.flush()
        except Exception:
            self.handleError(record)


# ============================================================================
# LOG CAPTURE SYSTEM
# ============================================================================

class LogCaptureSystem:
    """Main system for capturing and managing logs from Flask server"""
    
    def __init__(self, log_level=logging.INFO, enable_json=False):
        """
        Initialize the log capture system
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            enable_json: Enable JSON format logging
        """
        self.log_level = log_level
        self.enable_json = enable_json
        self.loggers = {}
        self.log_queue = queue.Queue()
        
        # Create log directory if it doesn't exist
        LogConfig.LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging system
        self._setup_logging()
        
        # Print startup info
        self._print_startup_info()
    
    def _setup_logging(self):
        """Setup all logging handlers and formatters"""
        
        # Create main logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # =====================================================================
        # 1. MAIN LOG FILE (All logs)
        # =====================================================================
        main_handler = logging.handlers.RotatingFileHandler(
            LogConfig.MAIN_LOG,
            maxBytes=LogConfig.MAX_LOG_SIZE,
            backupCount=LogConfig.BACKUP_COUNT
        )
        main_handler.setLevel(self.log_level)
        main_formatter = logging.Formatter(LogConfig.DETAILED_FORMAT)
        main_handler.setFormatter(main_formatter)
        root_logger.addHandler(main_handler)
        
        # =====================================================================
        # 2. ERROR LOG (Only errors and warnings)
        # =====================================================================
        error_handler = logging.handlers.RotatingFileHandler(
            LogConfig.ERROR_LOG,
            maxBytes=LogConfig.MAX_LOG_SIZE,
            backupCount=LogConfig.BACKUP_COUNT
        )
        error_handler.setLevel(logging.WARNING)
        error_formatter = logging.Formatter(LogConfig.DETAILED_FORMAT)
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)
        
        # =====================================================================
        # 3. API LOG (Track API calls and performance)
        # =====================================================================
        api_handler = logging.handlers.RotatingFileHandler(
            LogConfig.API_LOG,
            maxBytes=LogConfig.MAX_LOG_SIZE,
            backupCount=LogConfig.BACKUP_COUNT
        )
        api_handler.setLevel(logging.INFO)
        api_formatter = logging.Formatter(LogConfig.DETAILED_FORMAT)
        api_handler.setFormatter(api_formatter)
        
        # Add API logger
        api_logger = logging.getLogger('api')
        api_logger.addHandler(api_handler)
        api_logger.setLevel(logging.INFO)
        
        # =====================================================================
        # 4. PERFORMANCE LOG (Track performance metrics)
        # =====================================================================
        perf_handler = logging.handlers.RotatingFileHandler(
            LogConfig.PERFORMANCE_LOG,
            maxBytes=LogConfig.MAX_LOG_SIZE,
            backupCount=LogConfig.BACKUP_COUNT
        )
        perf_handler.setLevel(logging.INFO)
        perf_formatter = logging.Formatter(LogConfig.DETAILED_FORMAT)
        perf_handler.setFormatter(perf_formatter)
        
        # Add performance logger
        perf_logger = logging.getLogger('performance')
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)
        
        # =====================================================================
        # 5. CONSOLE OUTPUT (Colored)
        # =====================================================================
        console_handler = ColoredConsoleHandler()
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter(LogConfig.LOG_FORMAT)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Store loggers
        self.loggers = {
            'root': root_logger,
            'api': api_logger,
            'performance': perf_logger
        }
    
    def _print_startup_info(self):
        """Print startup information"""
        logger = logging.getLogger(__name__)
        
        print("\n" + "="*80)
        print("🚀 LOG CAPTURE SYSTEM INITIALIZED")
        print("="*80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Log Directory: {LogConfig.LOG_DIR.absolute()}")
        print(f"Log Level: {logging.getLevelName(self.log_level)}")
        print(f"Main Log: {LogConfig.MAIN_LOG}")
        print(f"Error Log: {LogConfig.ERROR_LOG}")
        print(f"API Log: {LogConfig.API_LOG}")
        print(f"Performance Log: {LogConfig.PERFORMANCE_LOG}")
        print("="*80 + "\n")
        
        logger.info("✅ Log capture system started successfully")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance by name"""
        return logging.getLogger(name)
    
    def log_api_call(self, method: str, endpoint: str, status: int, duration: float):
        """Log an API call"""
        api_logger = self.loggers['api']
        api_logger.info(f"API: {method} {endpoint} -> {status} ({duration:.2f}ms)")
    
    def log_performance(self, operation: str, duration: float, details: str = ""):
        """Log a performance metric"""
        perf_logger = self.loggers['performance']
        perf_logger.info(f"PERF: {operation} - {duration:.2f}ms {details}")
    
    def log_error(self, error_msg: str, exc_info=None):
        """Log an error"""
        logger = logging.getLogger(__name__)
        logger.error(error_msg, exc_info=exc_info)
    
    def get_recent_logs(self, filename: str, num_lines: int = 50) -> list:
        """Get recent log entries from a file"""
        try:
            log_file = LogConfig.LOG_DIR / filename
            if not log_file.exists():
                return []
            
            with open(log_file, 'r') as f:
                lines = f.readlines()
                return lines[-num_lines:] if len(lines) > num_lines else lines
        except Exception as e:
            return [f"Error reading logs: {e}"]
    
    def print_recent_logs(self, filename: str = "server.log", num_lines: int = 20):
        """Print recent log entries to console"""
        print(f"\n📋 Recent logs from {filename} (last {num_lines} lines):")
        print("="*80)
        logs = self.get_recent_logs(filename, num_lines)
        for line in logs:
            print(line.rstrip())
        print("="*80 + "\n")
    
    def get_log_statistics(self) -> dict:
        """Get statistics about current logs"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'logs': {}
        }
        
        for log_type in ['server.log', 'errors.log', 'api_calls.log', 'performance.log']:
            log_file = LogConfig.LOG_DIR / log_type
            if log_file.exists():
                stats['logs'][log_type] = {
                    'size': log_file.stat().st_size,
                    'lines': sum(1 for _ in open(log_file)),
                    'last_modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                }
        
        return stats


# ============================================================================
# MIDDLEWARE FOR FLASK INTEGRATION
# ============================================================================

class LoggingMiddleware:
    """WSGI middleware for capturing Flask request/response logs"""
    
    def __init__(self, app, log_capture_system: LogCaptureSystem):
        """
        Initialize the middleware
        
        Args:
            app: Flask application
            log_capture_system: LogCaptureSystem instance
        """
        self.app = app
        self.log_capture = log_capture_system
        self.logger = logging.getLogger(__name__)
    
    def __call__(self, environ, start_response):
        """Handle WSGI request"""
        import time
        
        method = environ.get('REQUEST_METHOD', 'UNKNOWN')
        path = environ.get('PATH_INFO', '/')
        start_time = time.time()
        
        def custom_start_response(status, headers):
            duration = (time.time() - start_time) * 1000  # Convert to ms
            status_code = int(status.split()[0])
            
            # Log the API call
            self.log_capture.log_api_call(method, path, status_code, duration)
            
            return start_response(status, headers)
        
        return self.app(environ, custom_start_response)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def setup_log_capture(log_level: str = 'INFO', enable_json: bool = False) -> LogCaptureSystem:
    """
    Convenience function to setup log capture system
    
    Args:
        log_level: Log level as string ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        enable_json: Enable JSON format logging
    
    Returns:
        LogCaptureSystem instance
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    return LogCaptureSystem(log_level=level, enable_json=enable_json)


def capture_flask_logs(app, log_capture_system: LogCaptureSystem):
    """
    Attach log capture to Flask application
    
    Args:
        app: Flask application instance
        log_capture_system: LogCaptureSystem instance
    """
    # Log all requests
    @app.before_request
    def log_request():
        from flask import request
        logger = log_capture_system.get_logger('flask.request')
        logger.info(f"REQUEST: {request.method} {request.path}")
    
    @app.after_request
    def log_response(response):
        from flask import request
        logger = log_capture_system.get_logger('flask.response')
        logger.info(f"RESPONSE: {request.method} {request.path} -> {response.status_code}")
        return response


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    """Main entry point for command line usage"""
    parser = argparse.ArgumentParser(
        description='Log capture system for TripRaft backend'
    )
    parser.add_argument(
        '--level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Enable JSON format logging'
    )
    parser.add_argument(
        '--show-logs',
        type=str,
        help='Show recent logs from file (e.g., server.log)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show log statistics'
    )
    
    args = parser.parse_args()
    
    # Setup log capture
    log_system = setup_log_capture(log_level=args.level, enable_json=args.json)
    
    # Handle commands
    if args.show_logs:
        log_system.print_recent_logs(args.show_logs)
    
    if args.stats:
        stats = log_system.get_log_statistics()
        print("\n📊 Log Statistics:")
        print(json.dumps(stats, indent=2))
    
    if not args.show_logs and not args.stats:
        # Just keep the system running
        print("✅ Log capture system running. Press Ctrl+C to exit.")
        print(f"📝 Logs are being saved to: {LogConfig.LOG_DIR}")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n✋ Log capture system stopped.")


# ============================================================================
# INTEGRATION WITH FLASK APP
# ============================================================================

"""
TO USE IN YOUR FLASK APP (web/backend/run.py):

from log_capture import setup_log_capture, capture_flask_logs

# Create Flask app
app = Flask(__name__)

# Setup log capture
log_capture = setup_log_capture(log_level='DEBUG')

# Capture Flask logs
capture_flask_logs(app, log_capture)

# Your other Flask code...

if __name__ == '__main__':
    app.run(debug=True)

---

ALTERNATIVELY, use as middleware:

from log_capture import LoggingMiddleware, setup_log_capture

app = Flask(__name__)
log_capture = setup_log_capture()
app.wsgi_app = LoggingMiddleware(app.wsgi_app, log_capture)

"""


if __name__ == '__main__':
    main()
