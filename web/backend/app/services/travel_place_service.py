"""
Place Service for Group Planner
Handles all place/destination operations using unified SQL database (pateldeep.db)


"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.domain.group_planner.models import (GroupActivity, Place, PlaceVote,
                                             TravelGroup, TripMember)
from app.domain.users.models import User
from app.infrastructure.db.connection import get_db_session

logger = logging.getLogger(__name__)


class PlaceService:
    """Service for place operations using SQL database"""
    
    @staticmethod
    def add_place(
        group_id: int,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        address: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        category: Optional[str] = None,
        visit_date: Optional[str] = None,
        suggested_duration: Optional[str] = None,
        photo_url: Optional[str] = None,
        website: Optional[str] = None,
        rating: Optional[float] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Add a place to the group's trip plan
        
        Args:
            group_id: Group ID
            user_id: User adding the place
            name: Place name
            description: Optional description
            address: Optional address
            latitude: Optional latitude
            longitude: Optional longitude
            category: Optional category
            visit_date: Optional planned visit date
            suggested_duration: Optional suggested duration
            photo_url: Optional photo URL
            website: Optional website URL
            rating: Optional rating
            
        Returns:
            Tuple of (success, place_data/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Check if place already exists (case-insensitive)
                existing = session.query(Place).filter(
                    Place.group_id == group_id,
                    Place.name.ilike(name.strip()),
                    Place.is_deleted == False
                ).first()
                
                if existing:
                    return False, {
                        'error': 'This place is already added to your list',
                        'code': 'PLACE_ALREADY_EXISTS'
                    }
                
                # Parse visit date
                parsed_visit_date = None
                if visit_date:
                    try:
                        parsed_visit_date = datetime.fromisoformat(visit_date.replace('Z', '+00:00')).date()
                    except:
                        pass
                
                # Create place
                place = Place(
                    group_id=group_id,
                    name=name.strip(),
                    description=description.strip() if description else None,
                    address=address.strip() if address else None,
                    latitude=latitude,
                    longitude=longitude,
                    category=category,
                    visit_date=parsed_visit_date,
                    suggested_duration=suggested_duration,
                    photo_url=photo_url,
                    website=website,
                    rating=rating,
                    added_by=user_id
                )
                session.add(place)
                session.flush()
                
                # Update group timestamp
                group = session.query(TravelGroup).get(group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                # Log activity
                activity = GroupActivity(
                    group_id=group_id,
                    user_id=user_id,
                    action='place_added',
                    entity_type='place',
                    entity_id=place.id,
                    details={'name': name}
                )
                session.add(activity)
                
                session.commit()
                session.refresh(place)
                
                logger.info(f"Place added: {place.id} to group {group_id}")
                
                return True, {'place': place.to_dict()}
                
        except Exception as e:
            logger.error(f"Add place error: {str(e)}")
            return False, {'error': 'Failed to add place'}
    
    @staticmethod
    def get_places(group_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all places for a group
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, places_list/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                places = session.query(Place).filter(
                    Place.group_id == group_id,
                    Place.is_deleted == False
                ).order_by(Place.created_at.desc()).all()
                
                return True, {'places': [p.to_dict() for p in places]}
                
        except Exception as e:
            logger.error(f"Get places error: {str(e)}")
            return False, {'error': 'Failed to get places'}
    
    @staticmethod
    def vote_place(
        group_id: int,
        place_id: int,
        user_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Toggle vote on a place
        
        Args:
            group_id: Group ID
            place_id: Place ID
            user_id: User voting
            
        Returns:
            Tuple of (success, vote_data/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Get place
                place = session.query(Place).filter(
                    Place.id == place_id,
                    Place.group_id == group_id,
                    Place.is_deleted == False
                ).first()
                
                if not place:
                    return False, {'error': 'Place not found'}
                
                # Check existing vote
                existing_vote = session.query(PlaceVote).filter(
                    PlaceVote.place_id == place_id,
                    PlaceVote.user_id == user_id
                ).first()
                
                if existing_vote:
                    # Remove vote
                    session.delete(existing_vote)
                    user_voted = False
                    action = 'removed'
                else:
                    # Add vote
                    vote = PlaceVote(
                        place_id=place_id,
                        user_id=user_id
                    )
                    session.add(vote)
                    user_voted = True
                    action = 'added'
                
                # Update group timestamp
                group = session.query(TravelGroup).get(group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                session.refresh(place)
                
                # Get updated votes
                votes = [v.user_id for v in place.votes]
                
                logger.info(f"Vote {action} for place {place_id} by user {user_id}")
                
                return True, {
                    'place_id': str(place_id),
                    'votes': votes,
                    'user_voted': user_voted
                }
                
        except Exception as e:
            logger.error(f"Vote place error: {str(e)}")
            return False, {'error': 'Failed to vote on place'}
    
    @staticmethod
    def update_place(
        group_id: int,
        place_id: int,
        user_id: int,
        visit_date: Optional[str] = None,
        suggested_duration: Optional[str] = None,
        remarks: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update place details
        
        Args:
            group_id: Group ID
            place_id: Place ID
            user_id: User updating
            visit_date: Optional new visit date
            suggested_duration: Optional new duration
            remarks: Optional new remarks
            
        Returns:
            Tuple of (success, place_data/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Get place
                place = session.query(Place).filter(
                    Place.id == place_id,
                    Place.group_id == group_id,
                    Place.is_deleted == False
                ).first()
                
                if not place:
                    return False, {'error': 'Place not found'}
                
                # Update fields
                if visit_date is not None:
                    try:
                        place.visit_date = datetime.fromisoformat(visit_date.replace('Z', '+00:00')).date()
                    except:
                        place.visit_date = None
                
                if suggested_duration is not None:
                    place.suggested_duration = suggested_duration
                
                if remarks is not None:
                    place.remarks = remarks
                
                place.updated_at = datetime.now(timezone.utc)
                
                # Update group timestamp
                group = session.query(TravelGroup).get(group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                session.refresh(place)
                
                logger.info(f"Place updated: {place_id}")
                
                return True, {'place': place.to_dict()}
                
        except Exception as e:
            logger.error(f"Update place error: {str(e)}")
            return False, {'error': 'Failed to update place'}
    
    @staticmethod
    def update_remarks(
        group_id: int,
        place_id: int,
        user_id: int,
        remarks: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update place remarks
        
        Args:
            group_id: Group ID
            place_id: Place ID
            user_id: User updating
            remarks: New remarks
            
        Returns:
            Tuple of (success, data/error)
        """
        return PlaceService.update_place(
            group_id=group_id,
            place_id=place_id,
            user_id=user_id,
            remarks=remarks
        )
    
    @staticmethod
    def delete_place(
        group_id: int,
        place_id: int,
        user_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete a place (soft delete)
        
        Args:
            group_id: Group ID
            place_id: Place ID
            user_id: User deleting
            
        Returns:
            Tuple of (success, message/error)
        """
        try:
            with get_db_session() as session:
                # Check membership
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True
                ).first()
                
                if not member:
                    return False, {'error': 'Not a member of this group'}
                
                # Get place
                place = session.query(Place).filter(
                    Place.id == place_id,
                    Place.group_id == group_id,
                    Place.is_deleted == False
                ).first()
                
                if not place:
                    return False, {'error': 'Place not found'}
                
                # Soft delete
                place.is_deleted = True
                place.updated_at = datetime.now(timezone.utc)
                
                # Update group timestamp
                group = session.query(TravelGroup).get(group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                # Log activity
                activity = GroupActivity(
                    group_id=group_id,
                    user_id=user_id,
                    action='place_deleted',
                    entity_type='place',
                    entity_id=place_id,
                    details={'name': place.name}
                )
                session.add(activity)
                
                session.commit()
                
                logger.info(f"Place deleted: {place_id}")
                
                return True, {'message': 'Place deleted successfully'}
                
        except Exception as e:
            logger.error(f"Delete place error: {str(e)}")
            return False, {'error': 'Failed to delete place'}


# Singleton instance
place_service = PlaceService()
