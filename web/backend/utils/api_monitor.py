"""
API Call Monitoring Utility

This module provides comprehensive tracking and analytics for API calls,
helping you understand usage patterns and cache effectiveness.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

class APICallMonitor:
    def __init__(self, log_file: str = "./api_calls.log"):
        self.log_file = Path(log_file)
        self.session_stats = {
            "geocode": [],
            "places": [],
            "cities": [],
            "cache_hits": 0,
            "cache_misses": 0,
            "session_start": datetime.now().isoformat()
        }
    
    def log_api_call(self, api_type: str, endpoint: str, cache_hit: bool = False):
        """Log an API call"""
        call_info = {
            "timestamp": datetime.now().isoformat(),
            "type": api_type,
            "endpoint": endpoint,
            "cached": cache_hit
        }
        
        if cache_hit:
            self.session_stats["cache_hits"] += 1
        else:
            self.session_stats["cache_misses"] += 1
            self.session_stats[api_type].append(call_info)
        
        # Append to log file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(call_info) + "\n")
    
    def get_session_summary(self) -> Dict:
        """Get summary of current session"""
        total_api_calls = sum(len(self.session_stats[k]) for k in ["geocode", "places", "cities"])
        
        return {
            "session_start": self.session_stats["session_start"],
            "total_api_calls": total_api_calls,
            "cache_hits": self.session_stats["cache_hits"],
            "cache_misses": self.session_stats["cache_misses"],
            "cache_hit_rate": f"{(self.session_stats['cache_hits'] / (self.session_stats['cache_hits'] + total_api_calls) * 100):.1f}%" if (self.session_stats['cache_hits'] + total_api_calls) > 0 else "0%",
            "breakdown": {
                "geocode_calls": len(self.session_stats["geocode"]),
                "places_calls": len(self.session_stats["places"]),
                "cities_calls": len(self.session_stats["cities"])
            }
        }
    
    def estimate_cost_savings(self, cost_per_call: float = 0.032) -> Dict:
        """
        Estimate cost savings from caching
        Default: $0.032 per Places API call (typical cost)
        """
        avoided_calls = self.session_stats["cache_hits"]
        total_calls = sum(len(self.session_stats[k]) for k in ["geocode", "places", "cities"])
        
        savings = avoided_calls * cost_per_call
        potential_cost = (total_calls + avoided_calls) * cost_per_call
        actual_cost = total_calls * cost_per_call
        
        return {
            "avoided_api_calls": avoided_calls,
            "estimated_savings": f"${savings:.2f}",
            "actual_cost": f"${actual_cost:.2f}",
            "potential_cost_without_cache": f"${potential_cost:.2f}",
            "savings_percentage": f"{(savings / potential_cost * 100):.1f}%" if potential_cost > 0 else "0%"
        }
    
    def analyze_log_file(self, days: int = 7) -> Dict:
        """Analyze historical API call patterns"""
        if not self.log_file.exists():
            return {"error": "No log file found"}
        
        calls_by_type = {"geocode": 0, "places": 0, "cities": 0}
        calls_by_hour = {}
        
        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    call = json.loads(line)
                    if not call.get("cached"):
                        call_type = call.get("type", "unknown")
                        calls_by_type[call_type] = calls_by_type.get(call_type, 0) + 1
                        
                        # Extract hour
                        hour = call["timestamp"].split("T")[1][:2]
                        calls_by_hour[hour] = calls_by_hour.get(hour, 0) + 1
                except:
                    continue
        
        return {
            "total_calls_logged": sum(calls_by_type.values()),
            "calls_by_type": calls_by_type,
            "peak_hour": max(calls_by_hour.items(), key=lambda x: x[1])[0] if calls_by_hour else "N/A",
            "calls_by_hour": calls_by_hour
        }

# Global monitor instance
monitor = APICallMonitor()

def get_monitor():
    """Get the global monitor instance"""
    return monitor
