"""
================================================================================
REAL-TIME SERVER LOG CAPTURE & ANALYSIS
================================================================================
Purpose: Capture live terminal output from Flask server and analyze performance
Features:
  - Real-time log capture from subprocess
  - Parse API requests and responses
  - Track performance metrics
  - Identify slow requests
  - Cache hit/miss analysis
  - Firestore operations tracking
  - Beautiful formatted output

Usage:
  python capture_server_logs.py
  or
  python capture_server_logs.py --analyze --save-report
================================================================================
"""

import subprocess
import sys
import re
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional
import argparse


class LogAnalyzer:
    """Analyze server logs in real-time"""
    
    def __init__(self):
        self.requests = deque(maxlen=100)  # Keep last 100 requests
        self.api_calls = []
        self.performance_metrics = defaultdict(list)
        self.cache_stats = {'hits': 0, 'misses': 0}
        self.firestore_stats = defaultdict(int)
        self.errors = []
        self.start_time = time.time()
    
    def parse_request(self, log_text: str) -> Optional[Dict]:
        """Parse incoming request from log"""
        request_pattern = r'→ INCOMING REQUEST.*?(?:GET|POST|PUT|DELETE|OPTIONS)\s+(/[\w/.-]*)'
        match = re.search(request_pattern, log_text, re.DOTALL)
        if match:
            return {
                'timestamp': datetime.now().isoformat(),
                'endpoint': match.group(1),
                'type': 'request'
            }
        return None
    
    def parse_response(self, log_text: str) -> Optional[Dict]:
        """Parse response from log"""
        response_pattern = r'← RESPONSE.*?Status:\s+(\d+).*?Duration:\s+([\d.]+)\s*ms'
        match = re.search(response_pattern, log_text, re.DOTALL)
        if match:
            status = int(match.group(1))
            duration = float(match.group(2))
            return {
                'timestamp': datetime.now().isoformat(),
                'status': status,
                'duration': duration,
                'type': 'response'
            }
        return None
    
    def parse_cache_event(self, log_text: str) -> Optional[Dict]:
        """Parse cache hit/miss"""
        if '✅ Cache HIT' in log_text:
            self.cache_stats['hits'] += 1
            return {'type': 'cache_hit', 'text': log_text.strip()}
        elif '❌ Cache MISS' in log_text:
            self.cache_stats['misses'] += 1
            return {'type': 'cache_miss', 'text': log_text.strip()}
        return None
    
    def parse_firestore_operation(self, log_text: str) -> Optional[Dict]:
        """Parse Firestore operations"""
        firestore_pattern = r'📊 FIRESTORE API CALLS.*?TOTAL:\s+(\d+)\s+operations'
        match = re.search(firestore_pattern, log_text, re.DOTALL)
        if match:
            ops = int(match.group(1))
            return {
                'timestamp': datetime.now().isoformat(),
                'operations': ops,
                'type': 'firestore'
            }
        return None
    
    def parse_performance(self, log_text: str) -> Optional[Dict]:
        """Parse performance metrics"""
        perf_pattern = r'✅ COMPLETE: (.+?)\s+-\s+([\d.]+)s'
        match = re.search(perf_pattern, log_text)
        if match:
            operation = match.group(1)
            duration = float(match.group(2)) * 1000  # Convert to ms
            self.performance_metrics[operation].append(duration)
            return {
                'operation': operation,
                'duration_ms': duration,
                'type': 'performance'
            }
        return None
    
    def parse_error(self, log_text: str) -> Optional[Dict]:
        """Parse errors"""
        if 'ERROR' in log_text or '❌' in log_text or 'Status: 403' in log_text:
            return {
                'timestamp': datetime.now().isoformat(),
                'message': log_text.strip(),
                'type': 'error'
            }
        return None
    
    def analyze_line(self, line: str):
        """Analyze a single log line"""
        # Try parsing different event types
        self.parse_cache_event(line)
        self.parse_firestore_operation(line)
        self.parse_performance(line)
        if 'ERROR' in line or 'Status: 403' in line:
            self.parse_error(line)
    
    def get_statistics(self) -> Dict:
        """Get aggregated statistics"""
        total_requests = len(self.requests)
        uptime = time.time() - self.start_time
        
        stats = {
            'uptime_seconds': uptime,
            'total_requests': total_requests,
            'cache': {
                'hits': self.cache_stats['hits'],
                'misses': self.cache_stats['misses'],
                'hit_rate': (self.cache_stats['hits'] / 
                           (self.cache_stats['hits'] + self.cache_stats['misses']) * 100
                           if (self.cache_stats['hits'] + self.cache_stats['misses']) > 0 
                           else 0)
            },
            'performance': {}
        }
        
        # Add performance metrics
        for operation, durations in self.performance_metrics.items():
            if durations:
                stats['performance'][operation] = {
                    'avg_ms': sum(durations) / len(durations),
                    'min_ms': min(durations),
                    'max_ms': max(durations),
                    'count': len(durations)
                }
        
        return stats


class ServerLogCapture:
    """Capture logs from running Flask server"""
    
    def __init__(self, server_command: str = "python run.py", 
                 cwd: str = None):
        """
        Initialize the log capture system
        
        Args:
            server_command: Command to run the server
            cwd: Working directory (backend folder)
        """
        self.server_command = server_command
        self.cwd = cwd or Path(__file__).parent
        self.analyzer = LogAnalyzer()
        self.log_file = Path(__file__).parent / "logs" / "captured_logs.txt"
        self.report_file = Path(__file__).parent / "logs" / "log_analysis.json"
        self.process = None
        self.is_running = False
        
        # Create logs directory
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def start_server(self):
        """Start the Flask server and capture logs"""
        print("\n" + "="*80)
        print("🚀 STARTING SERVER LOG CAPTURE")
        print("="*80)
        print(f"Command: {self.server_command}")
        print(f"Working Directory: {self.cwd}")
        print(f"Capturing to: {self.log_file}")
        print("="*80 + "\n")
        
        try:
            # Start server process with UTF-8 encoding
            self.process = subprocess.Popen(
                self.server_command,
                shell=True,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            self.is_running = True
            self._capture_output()
        
        except Exception as e:
            print(f"❌ Error starting server: {e}")
            self.is_running = False
    
    def _capture_output(self):
        """Capture and process server output"""
        buffer = ""
        line_count = 0
        
        # Set stdout to UTF-8
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        
        try:
            with open(self.log_file, 'w', encoding='utf-8', errors='replace') as f:
                f.write(f"Log Capture Started: {datetime.now().isoformat()}\n")
                f.write("="*80 + "\n\n")
            
            for line in self.process.stdout:
                if not line:
                    continue
                
                # Print to console with formatting
                self._print_formatted_line(line)
                
                # Save to file with UTF-8 encoding
                with open(self.log_file, 'a', encoding='utf-8', errors='replace') as f:
                    f.write(line)
                
                # Analyze
                buffer += line
                self.analyzer.analyze_line(line)
                line_count += 1
                
                # Print stats every 50 lines
                if line_count % 50 == 0:
                    self._print_statistics()
                
                # Check for complete requests/responses
                if "← RESPONSE" in line:
                    buffer = ""
        
        except KeyboardInterrupt:
            print("\n\n✋ Log capture stopped by user")
            self._print_final_report()
        except Exception as e:
            print(f"\n❌ Error capturing logs: {e}")
        finally:
            self.is_running = False
            if self.process:
                self.process.terminate()
    
    def _print_formatted_line(self, line: str):
        """Print line with color coding"""
        # Color codes
        colors = {
            'INFO': '\033[32m',      # Green
            'WARNING': '\033[33m',   # Yellow
            'ERROR': '\033[31m',     # Red
            'SUCCESS': '\033[32m',   # Green (checkmark)
            'FAILURE': '\033[31m',   # Red (X mark)
            'RESET': '\033[0m'
        }
        
        # Determine color based on content
        if '✅' in line or 'Cache HIT' in line or 'SUCCESS' in line:
            color = colors['SUCCESS']
        elif '❌' in line or 'Cache MISS' in line or 'ERROR' in line or '403' in line:
            color = colors['FAILURE']
        elif '⚠️' in line or 'WARNING' in line:
            color = colors['WARNING']
        elif '→' in line or '←' in line or '📊' in line or '🚀' in line:
            color = colors['INFO']
        else:
            color = ''
        
        # Print with color
        if color:
            print(f"{color}{line.rstrip()}{colors['RESET']}")
        else:
            print(line.rstrip())
    
    def _print_statistics(self):
        """Print current statistics"""
        stats = self.analyzer.get_statistics()
        
        print("\n" + "="*80)
        print("📊 CURRENT STATISTICS")
        print("="*80)
        print(f"Uptime: {stats['uptime_seconds']:.1f}s")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Cache Hit Rate: {stats['cache']['hit_rate']:.1f}% ({stats['cache']['hits']} hits, {stats['cache']['misses']} misses)")
        
        if stats['performance']:
            print("\nPerformance Metrics:")
            for op, metrics in sorted(stats['performance'].items()):
                print(f"  {op}:")
                print(f"    Avg: {metrics['avg_ms']:.2f}ms")
                print(f"    Min: {metrics['min_ms']:.2f}ms")
                print(f"    Max: {metrics['max_ms']:.2f}ms")
                print(f"    Count: {metrics['count']}")
        
        print("="*80 + "\n")
    
    def _print_final_report(self):
        """Print final analysis report"""
        stats = self.analyzer.get_statistics()
        
        print("\n" + "="*80)
        print("✅ FINAL ANALYSIS REPORT")
        print("="*80)
        print(f"Total Uptime: {stats['uptime_seconds']:.1f} seconds")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"\n🎯 Cache Performance:")
        print(f"  ✅ Cache Hits: {stats['cache']['hits']}")
        print(f"  ❌ Cache Misses: {stats['cache']['misses']}")
        print(f"  📈 Hit Rate: {stats['cache']['hit_rate']:.1f}%")
        
        if stats['performance']:
            print(f"\n⚡ Performance Metrics:")
            for op, metrics in sorted(stats['performance'].items()):
                print(f"\n  {op}:")
                print(f"    Average: {metrics['avg_ms']:.2f}ms")
                print(f"    Fastest: {metrics['min_ms']:.2f}ms")
                print(f"    Slowest: {metrics['max_ms']:.2f}ms")
                print(f"    Calls: {metrics['count']}")
                
                # Performance rating
                avg = metrics['avg_ms']
                if avg < 100:
                    rating = "🟢 Excellent"
                elif avg < 500:
                    rating = "🟡 Good"
                elif avg < 1000:
                    rating = "🟠 Fair"
                else:
                    rating = "🔴 Slow"
                print(f"    Rating: {rating}")
        
        print("\n" + "="*80)
        
        # Save report to file
        self._save_report(stats)
    
    def _save_report(self, stats: Dict):
        """Save analysis report to JSON file"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'statistics': stats,
            'log_file': str(self.log_file)
        }
        
        with open(self.report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Report saved to: {self.report_file}")


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Capture and analyze Flask server logs'
    )
    parser.add_argument(
        '--server-cmd',
        default='python run.py',
        help='Command to run the server'
    )
    parser.add_argument(
        '--cwd',
        default=None,
        help='Working directory (backend folder)'
    )
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Show analysis during capture'
    )
    parser.add_argument(
        '--save-report',
        action='store_true',
        help='Save final report to file'
    )
    
    args = parser.parse_args()
    
    # Create capture system
    capture = ServerLogCapture(
        server_command=args.server_cmd,
        cwd=args.cwd
    )
    
    # Start capturing
    try:
        capture.start_server()
    except KeyboardInterrupt:
        print("\n\n✋ Capture interrupted by user")


if __name__ == '__main__':
    main()
