#!/usr/bin/env python3
"""
Ranking Engine for TripRaft Database Pipeline
==============================================
Calculates and applies ranking scores to places based on:
- Tourist priority (45%)
- Traveler experience (25%)
- Tags & categories (15%)
- Duration optimization (10%)
- Cost consideration (5%)
"""

import re
import math
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


class RankingEngine:
    """Ranking calculation engine"""
    
    # Tunable weights
    WEIGHTS = {
        "tourist_priority": 0.45,
        "traveler_experience": 0.25,
        "cost": 0.05,
        "duration": 0.10,
        "tags": 0.15
    }
    
    # Tag boost values
    TAG_BOOSTS = {
        "Landmark": 0.10, "Iconic": 0.10,
        "Theme Park": 0.09, "Family": 0.09,
        "Museum": 0.07, "Art": 0.07, "Culture": 0.07,
        "Viewpoint": 0.07, "Outdoors": 0.07, "Hike": 0.07,
        "Nature": 0.04, "Lake": 0.04,
        "Architecture": 0.05, "Historic": 0.05, "Cinema": 0.05,
        "Food": 0.05, "Food Hall": 0.05, "Market": 0.05, "Shopping": 0.05,
        "Night": 0.03, "Photo Spot": 0.02, "Transit": 0.02,
        "Garden": 0.03, "Coastal": 0.04
    }
    
    DURATION_RE = re.compile(
        r"(?P<a>\d+(\.\d+)?)\s*[–-]\s*(?P<b>\d+(\.\d+)?)\s*(hour|hr|h|minute|min|m)s?",
        re.I
    )
    SINGLE_H_RE = re.compile(r"(?P<a>\d+(\.\d+)?)\s*(hour|hr|h)s?", re.I)
    SINGLE_M_RE = re.compile(r"(?P<a>\d+(\.\d+)?)\s*(minute|min|m)s?", re.I)
    
    def __init__(self):
        self.ranked_count = 0
    
    @staticmethod
    def clamp01(x: float) -> float:
        """Clamp value to [0, 1] range"""
        return max(0.0, min(1.0, float(x)))
    
    def get_rating(self, place: Dict[str, Any], key: str, 
                   default_5_scale: float = 4.0) -> float:
        """Extract and normalize rating (1-5 scale to 0-1)"""
        val = place.get(key)
        try:
            v = float(val)
            return self.clamp01(v / 5.0)
        except Exception:
            return self.clamp01(default_5_scale / 5.0)
    
    def parse_cost_score(self, place: Dict[str, Any]) -> float:
        """Map cost text to 0-1 score (1 = free/cheap)"""
        c = (place.get("cost") or "").lower()
        
        if not c:
            return 0.80
        
        if "free" in c:
            return 0.90 if "parking" in c else 1.00
        
        if "ticket" in c or "paid" in c or "entry" in c:
            return 0.65 if "vary" in c else 0.70
        
        return 0.80
    
    def parse_suggested_duration_minutes(self, text: str) -> Optional[float]:
        """Parse duration text to minutes"""
        if not text:
            return None
        
        t = text.strip()
        
        # Range: "2-3 hours", "90-120 minutes"
        m = self.DURATION_RE.search(t)
        if m:
            a = float(m.group("a"))
            b = float(m.group("b"))
            if "hour" in t.lower() or "hr" in t.lower() or "h" in t.lower():
                return (a + b) / 2.0 * 60.0
            else:
                return (a + b) / 2.0
        
        # Single hour: "2 hours"
        m = self.SINGLE_H_RE.search(t)
        if m:
            return float(m.group("a")) * 60.0
        
        # Single minute: "45 minutes"
        m = self.SINGLE_M_RE.search(t)
        if m:
            return float(m.group("a"))
        
        return None
    
    def duration_score(self, place: Dict[str, Any]) -> float:
        """Calculate duration score (optimal: 90-240 min)"""
        raw = place.get("suggested_duration") or place.get("suggested_duration_minutes")
        minutes = None
        
        if isinstance(raw, (int, float)):
            minutes = float(raw)
        elif isinstance(raw, str):
            minutes = self.parse_suggested_duration_minutes(raw)
        
        if minutes is None:
            return 0.75  # Neutral default
        
        # Bell curve centered at 150 min
        mu = 150.0
        sigma = 120.0
        z = (minutes - mu) / sigma
        score = math.exp(-0.5 * (z ** 2))
        
        return self.clamp01(0.5 * score + 0.25)
    
    def tag_score(self, place: Dict[str, Any]) -> float:
        """Calculate tag-based score"""
        tags = place.get("tags") or []
        if not isinstance(tags, list):
            return 0.0
        
        total = 0.0
        for t in tags:
            if not isinstance(t, str):
                continue
            boost = self.TAG_BOOSTS.get(t.strip(), 0.0)
            total += boost
        
        return self.clamp01(total)
    
    def compute_rank_score(self, place: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """Compute final rank score and components"""
        Rt = self.get_rating(place, "rating_tourist_priority", default_5_scale=4.0)
        Re = self.get_rating(place, "rating_traveler_experience", default_5_scale=4.0)
        C = self.clamp01(self.parse_cost_score(place))
        D = self.clamp01(self.duration_score(place))
        T = self.clamp01(self.tag_score(place))
        
        score = (
            self.WEIGHTS["tourist_priority"] * Rt +
            self.WEIGHTS["traveler_experience"] * Re +
            self.WEIGHTS["cost"] * C +
            self.WEIGHTS["duration"] * D +
            self.WEIGHTS["tags"] * T
        )
        
        score = self.clamp01(score)
        
        components = {
            "Rt": round(Rt, 3),
            "Re": round(Re, 3),
            "C": round(C, 3),
            "D": round(D, 3),
            "T": round(T, 3)
        }
        
        return score, components
    
    def find_place_arrays(self, obj: Any) -> List[List[Dict[str, Any]]]:
        """Find all place arrays in nested structure"""
        found = []
        
        def walk(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k in ("places", "top_places") and isinstance(v, list):
                        if all(isinstance(i, dict) for i in v):
                            found.append(v)
                    else:
                        walk(v)
            elif isinstance(x, list):
                for i in x:
                    walk(i)
        
        walk(obj)
        return found
    
    def add_rankings(self, data: Dict[str, Any]) -> int:
        """Add ranking scores to all places in data structure"""
        arrays = self.find_place_arrays(data)
        ranked_count = 0
        
        for arr in arrays:
            for place in arr:
                score, comps = self.compute_rank_score(place)
                place["rank_score"] = round(score, 4)
                place["_rank_components"] = comps
                ranked_count += 1
            
            # Sort by rank_score descending
            arr.sort(key=lambda p: p.get("rank_score", 0), reverse=True)
        
        self.ranked_count = ranked_count
        logger.info(f"  Ranking engine: Processed {ranked_count} places")
        
        return ranked_count


# Standalone test
if __name__ == "__main__":
    import json
    
    # Test data
    test_place = {
        "name_english": "Test Place",
        "rating_tourist_priority": 4.5,
        "rating_traveler_experience": 4.0,
        "cost": "Free",
        "suggested_duration": "2-3 hours",
        "tags": ["Landmark", "Viewpoint", "Photo Spot"]
    }
    
    engine = RankingEngine()
    score, components = engine.compute_rank_score(test_place)
    
    print(f"Rank Score: {score:.4f}")
    print(f"Components: {json.dumps(components, indent=2)}")
