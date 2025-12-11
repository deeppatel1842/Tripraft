"""
Trip Dashboard Repository - Phase 20 Extreme Optimization
Single-document pattern for Group Planner achieving 10 total Firestore operations.

Collection: trip_user_dashboards/{user_id}
Contains ALL data a user needs for trip planning in ONE document:
- All trip groups with embedded places, polls, members
- Pending invitations
- Global stats
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from firebase_admin import firestore

try:
    from Group_planner.cache_operations import GroupPlannerCacheOperations
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False

logger = logging.getLogger(__name__)


class TripDashboardRepository:
    """
    Repository for trip user dashboard documents.
    
    Schema: trip_user_dashboards/{user_id}
    {
        "userId": "abc123",
        "lastUpdated": "2025-12-04T10:00:00Z",
        
        "groups": {
            "trip_001": {
                "groupId": "trip_001",
                "name": "Bali Adventure",
                "destination": "Bali, Indonesia",
                "destinationCoordinates": {"latitude": -8.4095, "longitude": 115.1889},
                "tripDates": {"startDate": "2025-03-15", "endDate": "2025-03-22"},
                "budgetRange": {"min": 1500, "max": 3000, "currency": "USD"},
                "createdBy": "abc123",
                "memberCount": 3,
                "members": [...],
                "places": [...],
                "polls": [...],
                "checklist": [...]
            }
        },
        
        "pendingInvitations": [...],
        
        "stats": {
            "activeTrips": 2,
            "upcomingTrips": 1,
            "totalPlacesPlanned": 15
        }
    }
    """
    
    COLLECTION_NAME = 'trip_user_dashboards'
    CACHE_TTL = 3600  # 1 hour
    
    def __init__(self):
        self.db = firestore.client()
        self._cache = GroupPlannerCacheOperations() if CACHE_ENABLED else None
    
    def _get_cache_key(self, user_id: str) -> str:
        return f"trip:dashboard:{user_id}"
    
    def get_dashboard(self, user_id: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Get user's complete trip dashboard in a SINGLE read.
        
        Args:
            user_id: User ID
            use_cache: Whether to use Redis cache
            
        Returns:
            Complete dashboard document or None
        """
        cache_key = self._get_cache_key(user_id)
        
        # Try cache first
        if use_cache and self._cache and self._cache._is_available():
            cached = self._cache.redis_client.get(cache_key)
            if cached:
                logger.debug("[CACHE][+] Trip dashboard hit for user %s", user_id)
                return self._cache._safe_json_loads(cached)
        
        # Single Firestore read
        doc = self.db.collection(self.COLLECTION_NAME).document(user_id).get()
        
        if doc.exists:
            dashboard = doc.to_dict()
            dashboard['userId'] = user_id
            
            # Cache result
            if self._cache and self._cache._is_available():
                self._cache.redis_client.setex(
                    cache_key,
                    self.CACHE_TTL,
                    self._cache._safe_json_dumps(dashboard)
                )
                logger.debug("[CACHE][S] Trip dashboard cached for user %s", user_id)
            
            return dashboard
        
        return None
    
    def create_dashboard(self, user_id: str) -> Dict:
        """Create a new dashboard for a user."""
        now = datetime.utcnow().isoformat()
        
        dashboard = {
            'userId': user_id,
            'lastUpdated': now,
            'groups': {},
            'pendingInvitations': [],
            'stats': {
                'activeTrips': 0,
                'upcomingTrips': 0,
                'totalPlacesPlanned': 0
            }
        }
        
        self.db.collection(self.COLLECTION_NAME).document(user_id).set(dashboard)
        self._invalidate_cache(user_id)
        
        logger.info("Created trip dashboard for user %s", user_id)
        return dashboard
    
    def add_group_to_dashboard(
        self,
        user_id: str,
        group_id: str,
        group_data: Dict
    ) -> bool:
        """
        Add a trip group to user's dashboard.
        
        Args:
            user_id: User ID
            group_id: Group ID
            group_data: Group data to embed
        """
        try:
            dashboard = self.get_dashboard(user_id, use_cache=False)
            if not dashboard:
                dashboard = self.create_dashboard(user_id)
            
            groups = dashboard.get('groups', {})
            groups[group_id] = {
                'groupId': group_id,
                'name': group_data.get('name', 'Untitled Trip'),
                'destination': group_data.get('destination', ''),
                'destinationCoordinates': group_data.get('destinationCoordinates'),
                'tripDates': group_data.get('tripDates'),
                'budgetRange': group_data.get('budgetRange'),
                'createdBy': group_data.get('createdBy', user_id),
                'memberCount': group_data.get('memberCount', 1),
                'members': group_data.get('members', []),
                'places': [],
                'polls': [],
                'checklist': [],
                'lastActivity': datetime.utcnow().isoformat()
            }
            
            # Update stats
            stats = dashboard.get('stats', {})
            stats['activeTrips'] = len(groups)
            
            self.db.collection(self.COLLECTION_NAME).document(user_id).update({
                'groups': groups,
                'stats': stats,
                'lastUpdated': datetime.utcnow().isoformat()
            })
            
            self._invalidate_cache(user_id)
            return True
            
        except Exception as exc:
            logger.error("Failed to add group to dashboard: %s", exc)
            return False
    
    def add_place_to_group(
        self,
        user_id: str,
        group_id: str,
        place_data: Dict
    ) -> bool:
        """Add a place to a trip group."""
        try:
            dashboard = self.get_dashboard(user_id, use_cache=False)
            if not dashboard:
                return False
            
            groups = dashboard.get('groups', {})
            if group_id not in groups:
                return False
            
            group = groups[group_id]
            places = group.get('places', [])
            
            # Add place with coordinates
            places.append({
                'placeId': place_data.get('id') or place_data.get('placeId'),
                'name': place_data.get('name'),
                'coordinates': place_data.get('coordinates'),
                'category': place_data.get('category', 'attraction'),
                'addedBy': user_id,
                'addedAt': datetime.utcnow().isoformat(),
                'votes': 0,
                'status': 'planned'
            })
            
            group['places'] = places
            groups[group_id] = group
            
            # Update stats
            stats = dashboard.get('stats', {})
            stats['totalPlacesPlanned'] = sum(
                len(g.get('places', [])) for g in groups.values()
            )
            
            self.db.collection(self.COLLECTION_NAME).document(user_id).update({
                'groups': groups,
                'stats': stats,
                'lastUpdated': datetime.utcnow().isoformat()
            })
            
            self._invalidate_cache(user_id)
            return True
            
        except Exception as exc:
            logger.error("Failed to add place to group: %s", exc)
            return False
    
    def add_poll_to_group(
        self,
        user_id: str,
        group_id: str,
        poll_data: Dict
    ) -> str:
        """Add a poll to a trip group."""
        try:
            dashboard = self.get_dashboard(user_id, use_cache=False)
            if not dashboard:
                return None
            
            groups = dashboard.get('groups', {})
            if group_id not in groups:
                return None
            
            group = groups[group_id]
            polls = group.get('polls', [])
            
            poll_id = f"poll_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            polls.append({
                'pollId': poll_id,
                'question': poll_data.get('question'),
                'options': [
                    {'id': i + 1, 'text': opt, 'votes': []}
                    for i, opt in enumerate(poll_data.get('options', []))
                ],
                'createdBy': user_id,
                'createdAt': datetime.utcnow().isoformat(),
                'status': 'active'
            })
            
            group['polls'] = polls
            groups[group_id] = group
            
            self.db.collection(self.COLLECTION_NAME).document(user_id).update({
                'groups': groups,
                'lastUpdated': datetime.utcnow().isoformat()
            })
            
            self._invalidate_cache(user_id)
            return poll_id
            
        except Exception as exc:
            logger.error("Failed to add poll: %s", exc)
            return None
    
    def vote_on_poll(
        self,
        user_id: str,
        group_id: str,
        poll_id: str,
        option_id: int
    ) -> bool:
        """Vote on a poll option."""
        try:
            dashboard = self.get_dashboard(user_id, use_cache=False)
            if not dashboard:
                return False
            
            groups = dashboard.get('groups', {})
            if group_id not in groups:
                return False
            
            group = groups[group_id]
            polls = group.get('polls', [])
            
            for poll in polls:
                if poll.get('pollId') == poll_id:
                    # Remove user's previous vote
                    for option in poll.get('options', []):
                        if user_id in option.get('votes', []):
                            option['votes'].remove(user_id)
                    
                    # Add new vote
                    for option in poll.get('options', []):
                        if option.get('id') == option_id:
                            if user_id not in option.get('votes', []):
                                option['votes'].append(user_id)
                            break
                    break
            
            group['polls'] = polls
            groups[group_id] = group
            
            self.db.collection(self.COLLECTION_NAME).document(user_id).update({
                'groups': groups,
                'lastUpdated': datetime.utcnow().isoformat()
            })
            
            self._invalidate_cache(user_id)
            return True
            
        except Exception as exc:
            logger.error("Failed to vote on poll: %s", exc)
            return False
    
    def add_invitation_to_dashboard(
        self,
        user_id: str,
        invitation: Dict
    ) -> bool:
        """Add a pending invitation to user's dashboard."""
        try:
            dashboard = self.get_dashboard(user_id, use_cache=False)
            if not dashboard:
                dashboard = self.create_dashboard(user_id)
            
            invitations = dashboard.get('pendingInvitations', [])
            invitations.append({
                'id': invitation.get('id'),
                'groupId': invitation.get('group_id'),
                'groupName': invitation.get('group_name'),
                'destination': invitation.get('destination', ''),
                'inviterName': invitation.get('inviter_name'),
                'inviterEmail': invitation.get('inviter_email'),
                'createdAt': datetime.utcnow().isoformat()
            })
            
            self.db.collection(self.COLLECTION_NAME).document(user_id).update({
                'pendingInvitations': invitations,
                'lastUpdated': datetime.utcnow().isoformat()
            })
            
            self._invalidate_cache(user_id)
            return True
            
        except Exception as exc:
            logger.error("Failed to add invitation: %s", exc)
            return False
    
    def remove_invitation_from_dashboard(
        self,
        user_id: str,
        invitation_id: str
    ) -> bool:
        """Remove invitation after accept/reject."""
        try:
            dashboard = self.get_dashboard(user_id, use_cache=False)
            if not dashboard:
                return False
            
            invitations = dashboard.get('pendingInvitations', [])
            invitations = [inv for inv in invitations if inv.get('id') != invitation_id]
            
            self.db.collection(self.COLLECTION_NAME).document(user_id).update({
                'pendingInvitations': invitations,
                'lastUpdated': datetime.utcnow().isoformat()
            })
            
            self._invalidate_cache(user_id)
            return True
            
        except Exception as exc:
            logger.error("Failed to remove invitation: %s", exc)
            return False
    
    def update_group_members(
        self,
        group_id: str,
        members: List[Dict],
        affected_users: List[str]
    ) -> int:
        """Update members list in all affected users' dashboards."""
        updated = 0
        
        for user_id in affected_users:
            try:
                dashboard = self.get_dashboard(user_id, use_cache=False)
                if not dashboard:
                    continue
                
                groups = dashboard.get('groups', {})
                if group_id not in groups:
                    continue
                
                groups[group_id]['members'] = members
                groups[group_id]['memberCount'] = len(members)
                
                self.db.collection(self.COLLECTION_NAME).document(user_id).update({
                    'groups': groups,
                    'lastUpdated': datetime.utcnow().isoformat()
                })
                
                self._invalidate_cache(user_id)
                updated += 1
                
            except Exception as exc:
                logger.error("Failed to update members for user %s: %s", user_id, exc)
        
        return updated
    
    def _invalidate_cache(self, user_id: str):
        """Invalidate Redis cache for user."""
        if self._cache and self._cache._is_available():
            cache_key = self._get_cache_key(user_id)
            self._cache.redis_client.delete(cache_key)
            logger.debug("[CACHE][-] Invalidated trip dashboard for user %s", user_id)
