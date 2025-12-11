"""
Group Planner Batched Write Service - Phase 20
Every mutation = 1 Firestore operation using batch writes.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from firebase_admin import firestore

try:
    from Group_planner.cache_operations import GroupPlannerCacheOperations
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False

from Group_planner.repositories.trip_dashboard_repository import TripDashboardRepository

logger = logging.getLogger(__name__)


class GroupPlannerBatchedService:
    """
    Service for batched Firestore operations.
    
    Every mutation is a SINGLE batch commit = 1 Firestore operation.
    """
    
    def __init__(self):
        self.db = firestore.client()
        self.dashboard_repo = TripDashboardRepository()
        self._cache = GroupPlannerCacheOperations() if CACHE_ENABLED else None
    
    def create_group_batched(
        self,
        name: str,
        created_by: str,
        creator_display_name: str,
        creator_email: str = '',
        destination: str = '',
        destination_coordinates: Dict = None,
        trip_dates: Dict = None,
        budget_range: Dict = None,
        description: str = ''
    ) -> Dict:
        """
        Create a trip group with SINGLE batch write.
        
        Writes to:
        - travel_groups/{group_id}
        - group_members/{group_id}_{user_id}
        
        Then updates dashboard (separate write).
        
        Returns:
            Created group data
        """
        batch = self.db.batch()
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        # Generate ID
        group_id = f"trip_{uuid.uuid4().hex[:12]}"
        
        # 1. Group document
        group_data = {
            'group_id': group_id,
            'name': name,
            'description': description,
            'destination': destination,
            'destination_coordinates': destination_coordinates,
            'trip_dates': trip_dates,
            'budget_range': budget_range,
            'created_by': created_by,
            'created_at': now,
            'updated_at': now,
            'members': [created_by],
            'member_details': [{
                'user_id': created_by,
                'email': creator_email,
                'display_name': creator_display_name,
                'role': 'creator',
                'is_creator': True,
                'joined_at': now_iso
            }],
            'member_count': 1,
            'places_count': 0,
            'polls_count': 0
        }
        group_ref = self.db.collection('travel_groups').document(group_id)
        batch.set(group_ref, group_data)
        
        # 2. Member document
        member_data = {
            'group_id': group_id,
            'user_id': created_by,
            'email': creator_email,
            'display_name': creator_display_name,
            'role': 'creator',
            'is_creator': True,
            'joined_at': now
        }
        member_ref = self.db.collection('group_members').document(f"{group_id}_{created_by}")
        batch.set(member_ref, member_data)
        
        # COMMIT = 1 Firestore operation
        batch.commit()
        logger.info("[BATCHED] Created group %s with 1 batch commit", group_id)
        
        # Update dashboard
        self.dashboard_repo.add_group_to_dashboard(
            user_id=created_by,
            group_id=group_id,
            group_data={
                'name': name,
                'destination': destination,
                'destinationCoordinates': destination_coordinates,
                'tripDates': trip_dates,
                'budgetRange': budget_range,
                'createdBy': created_by,
                'memberCount': 1,
                'members': [{
                    'userId': created_by,
                    'displayName': creator_display_name,
                    'email': creator_email,
                    'role': 'creator'
                }]
            }
        )
        
        # Invalidate cache
        if self._cache and self._cache._is_available():
            self._cache.invalidate_user_groups(created_by)
        
        return {
            'group_id': group_id,
            'name': name,
            'destination': destination,
            'destination_coordinates': destination_coordinates,
            'trip_dates': trip_dates,
            'budget_range': budget_range,
            'created_by': created_by,
            'created_at': now_iso,
            'members': [created_by],
            'member_count': 1
        }
    
    def accept_invitation_batched(
        self,
        invitation_id: str,
        invitation_data: Dict,
        accepter_id: str,
        accepter_display_name: str,
        accepter_email: str = ''
    ) -> Dict:
        """
        Accept invitation with SINGLE batch write.
        
        Writes to:
        - group_invitations/{id}
        - travel_groups/{gid} (update members)
        - group_members/{gid}_{uid}
        """
        batch = self.db.batch()
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        group_id = invitation_data.get('group_id')
        
        # 1. Update invitation
        inv_ref = self.db.collection('group_invitations').document(invitation_id)
        batch.update(inv_ref, {
            'status': 'accepted',
            'accepted_at': now,
            'accepted_by': accepter_id
        })
        
        # 2. Add to group
        group_ref = self.db.collection('travel_groups').document(group_id)
        batch.update(group_ref, {
            'members': firestore.ArrayUnion([accepter_id]),
            'member_details': firestore.ArrayUnion([{
                'user_id': accepter_id,
                'email': accepter_email,
                'display_name': accepter_display_name,
                'role': 'member',
                'is_creator': False,
                'joined_at': now_iso
            }]),
            'member_count': firestore.Increment(1),
            'updated_at': now
        })
        
        # 3. Create member doc
        member_ref = self.db.collection('group_members').document(f"{group_id}_{accepter_id}")
        batch.set(member_ref, {
            'group_id': group_id,
            'user_id': accepter_id,
            'email': accepter_email,
            'display_name': accepter_display_name,
            'role': 'member',
            'joined_at': now
        })
        
        # COMMIT
        batch.commit()
        logger.info("[BATCHED] Accepted invitation %s with 1 batch commit", invitation_id)
        
        # Update dashboards
        self.dashboard_repo.remove_invitation_from_dashboard(accepter_id, invitation_id)
        self.dashboard_repo.add_group_to_dashboard(
            user_id=accepter_id,
            group_id=group_id,
            group_data={
                'name': invitation_data.get('group_name', 'Unknown'),
                'destination': invitation_data.get('destination', ''),
                'destinationCoordinates': invitation_data.get('destination_coordinates'),
                'createdBy': invitation_data.get('created_by'),
                'memberCount': invitation_data.get('member_count', 1) + 1,
                'members': invitation_data.get('existing_members', []) + [{
                    'userId': accepter_id,
                    'displayName': accepter_display_name,
                    'email': accepter_email,
                    'role': 'member'
                }]
            }
        )
        
        # Invalidate caches
        if self._cache and self._cache._is_available():
            self._cache.invalidate_user_groups(accepter_id)
            self._cache.invalidate_user_invitations(accepter_id)
            self._cache.invalidate_group(group_id)
        
        return {
            'group_id': group_id,
            'invitation_id': invitation_id
        }
    
    def send_invitation_batched(
        self,
        group_id: str,
        group_name: str,
        destination: str,
        inviter_id: str,
        inviter_name: str,
        invitee_email: str,
        invitee_user_id: str = None
    ) -> Dict:
        """
        Send invitation with SINGLE write.
        """
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        invitation_id = f"inv_{uuid.uuid4().hex[:12]}"
        
        invitation_data = {
            'invitation_id': invitation_id,
            'group_id': group_id,
            'group_name': group_name,
            'destination': destination,
            'inviter_id': inviter_id,
            'inviter_name': inviter_name,
            'invited_email': invitee_email,
            'invited_user_id': invitee_user_id,
            'status': 'pending',
            'created_at': now,
            'expires_at': datetime.utcnow().replace(day=datetime.utcnow().day + 7)
        }
        
        # Single write
        self.db.collection('group_invitations').document(invitation_id).set(invitation_data)
        logger.info("[BATCHED] Created invitation %s with 1 write", invitation_id)
        
        # Update invitee's dashboard if registered
        if invitee_user_id:
            self.dashboard_repo.add_invitation_to_dashboard(
                user_id=invitee_user_id,
                invitation={
                    'id': invitation_id,
                    'group_id': group_id,
                    'group_name': group_name,
                    'destination': destination,
                    'inviter_name': inviter_name
                }
            )
        
        return {
            'invitation_id': invitation_id,
            'group_id': group_id,
            'invited_email': invitee_email,
            'status': 'pending',
            'created_at': now_iso
        }
    
    def add_place_batched(
        self,
        group_id: str,
        place_data: Dict,
        added_by: str,
        group_members: List[str] = None
    ) -> Dict:
        """
        Add place to trip with SINGLE write.
        """
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        place_id = place_data.get('id') or f"place_{uuid.uuid4().hex[:8]}"
        
        place_doc = {
            'place_id': place_id,
            'group_id': group_id,
            'name': place_data.get('name'),
            'coordinates': place_data.get('coordinates'),
            'category': place_data.get('category', 'attraction'),
            'added_by': added_by,
            'added_at': now,
            'votes': 0,
            'status': 'planned',
            'notes': place_data.get('notes', ''),
            'photos': place_data.get('photos')
        }
        
        # Single write
        self.db.collection('travel_places').document(place_id).set(place_doc)
        logger.info("[BATCHED] Added place %s with 1 write", place_id)
        
        # Update all members' dashboards
        for member_id in (group_members or [added_by]):
            self.dashboard_repo.add_place_to_group(
                user_id=member_id,
                group_id=group_id,
                place_data={
                    'placeId': place_id,
                    'name': place_data.get('name'),
                    'coordinates': place_data.get('coordinates'),
                    'category': place_data.get('category', 'attraction')
                }
            )
        
        # Update group places count
        self.db.collection('travel_groups').document(group_id).update({
            'places_count': firestore.Increment(1),
            'updated_at': now
        })
        
        return {
            'place_id': place_id,
            'group_id': group_id,
            'name': place_data.get('name'),
            'coordinates': place_data.get('coordinates'),
            'added_at': now_iso
        }
    
    def create_poll_batched(
        self,
        group_id: str,
        question: str,
        options: List[str],
        created_by: str,
        group_members: List[str] = None
    ) -> Dict:
        """
        Create poll with SINGLE write.
        """
        now = datetime.utcnow()
        now_iso = now.isoformat()
        
        poll_id = f"poll_{uuid.uuid4().hex[:8]}"
        
        poll_doc = {
            'poll_id': poll_id,
            'group_id': group_id,
            'question': question,
            'options': [
                {'id': i + 1, 'text': opt, 'votes': []}
                for i, opt in enumerate(options)
            ],
            'created_by': created_by,
            'created_at': now,
            'status': 'active'
        }
        
        # Single write
        self.db.collection('travel_polls').document(poll_id).set(poll_doc)
        logger.info("[BATCHED] Created poll %s with 1 write", poll_id)
        
        # Update dashboards
        for member_id in (group_members or [created_by]):
            self.dashboard_repo.add_poll_to_group(
                user_id=member_id,
                group_id=group_id,
                poll_data={
                    'question': question,
                    'options': options
                }
            )
        
        return {
            'poll_id': poll_id,
            'group_id': group_id,
            'question': question,
            'created_at': now_iso
        }
    
    def vote_on_poll_batched(
        self,
        poll_id: str,
        group_id: str,
        option_id: int,
        voter_id: str
    ) -> Dict:
        """
        Vote on poll with SINGLE write.
        """
        # Get current poll to update votes
        poll_ref = self.db.collection('travel_polls').document(poll_id)
        poll_doc = poll_ref.get()
        
        if not poll_doc.exists:
            raise ValueError("Poll not found")
        
        poll_data = poll_doc.to_dict()
        options = poll_data.get('options', [])
        
        # Update votes
        for option in options:
            # Remove previous vote
            if voter_id in option.get('votes', []):
                option['votes'].remove(voter_id)
            # Add new vote
            if option.get('id') == option_id:
                option['votes'].append(voter_id)
        
        # Single write
        poll_ref.update({
            'options': options,
            'updated_at': datetime.utcnow()
        })
        logger.info("[BATCHED] Voted on poll %s with 1 write", poll_id)
        
        return {
            'poll_id': poll_id,
            'voted_option': option_id,
            'success': True
        }
