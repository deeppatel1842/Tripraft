# Purpose: Place Service for Group Planner Handles all place/destination operations using unified SQL database (pateldeep.db).
"""
Place Service for Group Planner
Handles all place/destination operations using unified SQL database (pateldeep.db)


"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.trips.models import (GroupActivity, Place, PlaceVote,
                                             TravelGroup, TripMember)
from app.auth.models import User
from app.core.db.connection import get_db_session
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)


class PlaceValidationError(ValueError):
    """A client-supplied place field cannot be safely persisted."""


class PlaceService:
    """Service for place operations using SQL database"""
    
    @staticmethod
    def add_place(
        group_id: str,
        user_id: str,
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
            from app.core.sanitize import sanitize_text
            name = sanitize_text(name)
            if description:
                description = sanitize_text(description)
            if address:
                address = sanitize_text(address)

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
                
                parsed_visit_date = PlaceService._parse_visit_date(visit_date)
                
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
                group = session.get(TravelGroup, group_id)
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
                
                # Notify group members
                try:
                    from app.notifications.services.notification_service import \
                        notification_service
                    notification_service.notify_group_members(
                        group_id=group_id,
                        exclude_user_id=user_id,
                        type='place_added',
                        title=f'New place added: {name}',
                        data={'place_id': place.id, 'place_name': name}
                    )
                except Exception:
                    pass
                
                # Real-time broadcast
                try:
                    from app.trips.realtime.events import \
                        emit_to_group
                    emit_to_group(group_id, 'place:added', {'place': place.to_dict(), 'user_id': user_id})
                except Exception:
                    pass
                
                return True, {'place': place.to_dict()}
                
        except PlaceValidationError as exc:
            logger.info('Rejected invalid place input: %s', exc)
            return False, {'error': str(exc)}
        except Exception as e:
            logger.error(f"Add place error: {str(e)}")
            return False, {'error': 'Failed to add place'}

    @staticmethod
    def _parse_visit_date(value: Optional[str]):
        """Parse an ISO date or reject it; an empty update explicitly clears it."""
        if value is None or value == '':
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        except (AttributeError, TypeError, ValueError):
            raise PlaceValidationError('visit_date must be an ISO-8601 date')
    
    @staticmethod
    def get_places(group_id: str, user_id: str, page: int = 1, per_page: int = 20,
                   q: Optional[str] = None, category: Optional[str] = None,
                   visit_date_from: Optional[str] = None, visit_date_to: Optional[str] = None,
                   sort_by: str = 'created_at', sort_order: str = 'desc') -> Tuple[bool, Dict[str, Any]]:
        """
        Get places for a group (paginated, filterable, sortable)
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
                
                base_query = session.query(Place).filter(
                    Place.group_id == group_id,
                    Place.is_deleted == False
                )
                
                # Apply filters
                if q:
                    search_term = f"%{q}%"
                    base_query = base_query.filter(
                        (Place.name.ilike(search_term)) |
                        (Place.description.ilike(search_term)) |
                        (Place.address.ilike(search_term))
                    )
                if category:
                    base_query = base_query.filter(Place.category == category)
                if visit_date_from:
                    try:
                        base_query = base_query.filter(Place.visit_date >= visit_date_from)
                    except (ValueError, AttributeError):
                        pass
                if visit_date_to:
                    try:
                        base_query = base_query.filter(Place.visit_date <= visit_date_to)
                    except (ValueError, AttributeError):
                        pass
                
                total = base_query.count()
                
                # Apply sorting
                sort_col = {
                    'name': Place.name,
                    'visit_date': Place.visit_date,
                    'created_at': Place.created_at,
                    'rating': Place.rating,
                }.get(sort_by, Place.created_at)
                
                order_fn = sort_col.asc() if sort_order == 'asc' else sort_col.desc()
                
                places = base_query.options(
                    joinedload(Place.votes),
                    joinedload(Place.adder)
                ).order_by(
                    order_fn
                ).offset((page - 1) * per_page).limit(per_page).all()
                
                return True, {
                    'places': [p.to_dict() for p in places],
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'total_pages': max(1, -(-total // per_page))
                    }
                }
                
        except Exception as e:
            logger.error(f"Get places error: {str(e)}")
            return False, {'error': 'Failed to get places'}
    
    @staticmethod
    def vote_place(
        group_id: str,
        place_id: str,
        user_id: str
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
                group = session.get(TravelGroup, group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                session.refresh(place)
                
                # Get updated votes
                votes = [v.user_id for v in place.votes]
                
                logger.info(f"Vote {action} for place {place_id} by user {user_id}")
                
                # Real-time broadcast
                try:
                    from app.trips.realtime.events import \
                        emit_to_group
                    emit_to_group(group_id, 'place:voted', {
                        'place_id': place_id, 'votes': votes,
                        'user_id': user_id, 'action': action
                    })
                except Exception:
                    pass
                
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
        group_id: str,
        place_id: str,
        user_id: str,
        visit_date: Optional[str] = None,
        suggested_duration: Optional[str] = None,
        remarks: Optional[str] = None,
        expected_updated_at: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Update place details with optimistic locking.
        
        Args:
            group_id: Group ID
            place_id: Place ID
            user_id: User updating
            visit_date: Optional new visit date
            suggested_duration: Optional new duration
            remarks: Optional new remarks
            expected_updated_at: If provided, ISO timestamp to check against (409 on mismatch)
            
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
                
                # Optimistic locking: reject if updated_at mismatch
                if expected_updated_at is not None and place.updated_at:
                    try:
                        expected_dt = datetime.fromisoformat(expected_updated_at.replace('Z', '+00:00'))
                        if place.updated_at.replace(tzinfo=None) != expected_dt.replace(tzinfo=None):
                            return False, {
                                'error': 'Conflict: place was modified by another user',
                                'status': 409,
                                'current_updated_at': place.updated_at.isoformat()
                            }
                    except (ValueError, AttributeError):
                        pass
                
                # Update fields
                if visit_date is not None:
                    place.visit_date = PlaceService._parse_visit_date(visit_date)
                
                if suggested_duration is not None:
                    place.suggested_duration = suggested_duration
                
                if remarks is not None:
                    place.remarks = remarks
                
                # Handle suggested_time from kwargs
                suggested_time = kwargs.get('suggested_time')
                if suggested_time is not None:
                    place.suggested_time = suggested_time or None
                
                place.updated_at = datetime.now(timezone.utc)
                
                # Update group timestamp
                group = session.get(TravelGroup, group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                session.refresh(place)
                
                logger.info(f"Place updated: {place_id}")
                
                return True, {'place': place.to_dict()}
                
        except PlaceValidationError as exc:
            logger.info('Rejected invalid place update: %s', exc)
            return False, {'error': str(exc)}
        except Exception as e:
            logger.error(f"Update place error: {str(e)}")
            return False, {'error': 'Failed to update place'}
    
    @staticmethod
    def update_remarks(
        group_id: str,
        place_id: str,
        user_id: str,
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
        group_id: str,
        place_id: str,
        user_id: str
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
                group = session.get(TravelGroup, group_id)
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
