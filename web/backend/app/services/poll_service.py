"""
Poll Service for Group Planner
Handles all poll/voting operations using local SQL database
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.domain.group_planner.models import (GroupActivity, Poll, PollVote,
                                             TravelGroup, TripMember)
from app.infrastructure.db.connection import get_db_session

logger = logging.getLogger(__name__)


class PollService:
    """Service for poll operations using SQL database"""
    
    @staticmethod
    def create_poll(
        group_id: int,
        user_id: int,
        name: str,
        options: List[str],
        is_multiple_choice: bool = False,
        expires_at: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a poll in a group
        
        Args:
            group_id: Group ID
            user_id: User creating the poll
            name: Poll question/name
            options: List of options
            is_multiple_choice: Allow multiple votes
            expires_at: Optional expiration datetime
            
        Returns:
            Tuple of (success, poll_data/error)
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
                
                # Validate options
                if not options or len(options) < 2:
                    return False, {'error': 'Poll must have at least 2 options'}
                
                # Parse expires_at
                parsed_expires_at = None
                if expires_at:
                    try:
                        parsed_expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    except:
                        pass
                
                # Create poll
                poll = Poll(
                    group_id=group_id,
                    name=name.strip(),
                    options=options,
                    is_multiple_choice=is_multiple_choice,
                    expires_at=parsed_expires_at,
                    created_by=user_id
                )
                session.add(poll)
                session.flush()
                
                # Update group timestamp
                group = session.query(TravelGroup).get(group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                # Log activity
                activity = GroupActivity(
                    group_id=group_id,
                    user_id=user_id,
                    action='poll_created',
                    entity_type='poll',
                    entity_id=poll.id,
                    details={'name': name}
                )
                session.add(activity)
                
                session.commit()
                session.refresh(poll)
                
                logger.info(f"Poll created: {poll.id} in group {group_id}")
                
                return True, {'poll': poll.to_dict()}
                
        except Exception as e:
            logger.error(f"Create poll error: {str(e)}")
            return False, {'error': 'Failed to create poll'}
    
    @staticmethod
    def get_polls(group_id: int, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all polls for a group
        
        Args:
            group_id: Group ID
            user_id: Requesting user ID
            
        Returns:
            Tuple of (success, polls_list/error)
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
                
                polls = session.query(Poll).filter(
                    Poll.group_id == group_id,
                    Poll.is_deleted == False
                ).order_by(Poll.created_at.desc()).all()
                
                return True, {'polls': [p.to_dict() for p in polls]}
                
        except Exception as e:
            logger.error(f"Get polls error: {str(e)}")
            return False, {'error': 'Failed to get polls'}
    
    @staticmethod
    def vote_poll(
        group_id: int,
        poll_id: int,
        user_id: int,
        option: str = None,
        option_index: int = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Vote on a poll option
        
        Args:
            group_id: Group ID
            poll_id: Poll ID
            user_id: User voting
            option: Selected option (name)
            option_index: Selected option (index) - alternative to option
            
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
                
                # Get poll
                poll = session.query(Poll).filter(
                    Poll.id == poll_id,
                    Poll.group_id == group_id,
                    Poll.is_deleted == False
                ).first()
                
                if not poll:
                    return False, {'error': 'Poll not found'}
                
                # Resolve option from index if needed
                if option is None and option_index is not None:
                    # Ensure option_index is an integer
                    try:
                        option_index = int(option_index)
                    except (ValueError, TypeError):
                        return False, {'error': 'Invalid option index format'}
                    
                    if 0 <= option_index < len(poll.options):
                        option = poll.options[option_index]
                    else:
                        return False, {'error': 'Invalid option index'}
                
                # Validate option
                if option not in poll.options:
                    return False, {'error': 'Invalid poll option'}
                
                # Check if poll is expired
                if poll.expires_at:
                    # Handle both datetime and string formats
                    expires_at = poll.expires_at
                    if isinstance(expires_at, str):
                        try:
                            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            expires_at = None
                    
                    if expires_at and expires_at < datetime.now(timezone.utc):
                        return False, {'error': 'Poll has expired'}
                
                # Remove previous votes if not multiple choice
                if not poll.is_multiple_choice:
                    previous_votes = session.query(PollVote).filter(
                        PollVote.poll_id == poll_id,
                        PollVote.user_id == user_id
                    ).all()
                    for pv in previous_votes:
                        session.delete(pv)
                
                # Check if already voted for this option
                existing_vote = session.query(PollVote).filter(
                    PollVote.poll_id == poll_id,
                    PollVote.user_id == user_id,
                    PollVote.option == option
                ).first()
                
                if existing_vote:
                    # Toggle off if already voted
                    session.delete(existing_vote)
                else:
                    # Add vote
                    vote = PollVote(
                        poll_id=poll_id,
                        user_id=user_id,
                        option=option
                    )
                    session.add(vote)
                
                # Update group timestamp
                group = session.query(TravelGroup).get(group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                session.commit()
                session.refresh(poll)
                
                # Get updated poll data
                poll_data = poll.to_dict()
                
                logger.info(f"Vote recorded for poll {poll_id} by user {user_id}")
                
                return True, {
                    'poll_id': str(poll_id),
                    'votes': poll_data['votes'],
                    'user_vote': option
                }
                
        except Exception as e:
            logger.error(f"Vote poll error: {str(e)}")
            return False, {'error': 'Failed to vote on poll'}
    
    @staticmethod
    def delete_poll(
        group_id: int,
        poll_id: int,
        user_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete a poll (creator only, soft delete)
        
        Args:
            group_id: Group ID
            poll_id: Poll ID
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
                
                # Get poll
                poll = session.query(Poll).filter(
                    Poll.id == poll_id,
                    Poll.group_id == group_id,
                    Poll.is_deleted == False
                ).first()
                
                if not poll:
                    return False, {'error': 'Poll not found'}
                
                # Only creator can delete
                if poll.created_by != user_id:
                    return False, {'error': 'Only the poll creator can delete it'}
                
                # Soft delete
                poll.is_deleted = True
                
                # Update group timestamp
                group = session.query(TravelGroup).get(group_id)
                if group:
                    group.updated_at = datetime.now(timezone.utc)
                
                # Log activity
                activity = GroupActivity(
                    group_id=group_id,
                    user_id=user_id,
                    action='poll_deleted',
                    entity_type='poll',
                    entity_id=poll_id,
                    details={'name': poll.name}
                )
                session.add(activity)
                
                session.commit()
                
                logger.info(f"Poll deleted: {poll_id}")
                
                return True, {'message': 'Poll deleted successfully'}
                
        except Exception as e:
            logger.error(f"Delete poll error: {str(e)}")
            return False, {'error': 'Failed to delete poll'}


# Singleton instance
poll_service = PollService()
