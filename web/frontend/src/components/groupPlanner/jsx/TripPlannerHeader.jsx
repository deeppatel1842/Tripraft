import React from 'react';
import { MapPin, UserPlus, Calendar, Crown } from 'lucide-react';
import '../css/TripPlannerHeader.css';

export default function TripPlannerHeader({
  tripName = 'Seattle Tech Trip',
  tripEmoji = '',
  destination = '',
  startDate = 'Oct 12',
  endDate = 'Oct 15',
  duration = '4 Days',
  createdAt = null,
  members = [],
  pendingCount = 0,
  currentUser = null,
  onPendingClick,
  onInviteClick,
  onMembersClick,
}) {
  const getInitials = (name) => {
    if (!name) return '?';
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const formatCreatedDate = (date) => {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <header className="tph-header">
      <div className="tph-left">
        <div className="tph-trip-info">
          <h1 className="tph-trip-name">{tripName} {tripEmoji}</h1>
          <div className="tph-trip-meta">
            {destination && (
              <span className="tph-trip-destination">
                <MapPin size={14} />
                {destination}
              </span>
            )}
            {(startDate || endDate) && (
              <span className="tph-trip-dates">
                <Calendar size={14} />
                {startDate} - {endDate} {duration && `• ${duration}`}
              </span>
            )}
            {createdAt && (
              <span className="tph-trip-created">
                Created {formatCreatedDate(createdAt)}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="tph-right">
        {pendingCount > 0 && (
          <button className="tph-pending-btn" onClick={onPendingClick}>
            <span className="tph-pending-pulse">
              <span className="tph-pending-ping"></span>
              <span className="tph-pending-dot"></span>
            </span>
            {pendingCount} Pending
          </button>
        )}

        <div className="tph-divider-small"></div>

        <div 
          className="tph-members" 
          onClick={onMembersClick}
          title="Click to view all members"
          style={{ cursor: onMembersClick ? 'pointer' : 'default' }}
        >
          {/* Show all members with owner badge for creator */}
          {members.slice(0, 5).map((member, index) => (
            <div
              key={member.id || index}
              className={`tph-member-avatar ${member.isCreator ? 'tph-member-owner' : ''}`}
              title={`${member.displayName || member.email}${member.isCreator ? ' (Owner)' : ''}`}
            >
              {member.photoURL ? (
                <img src={member.photoURL} alt="" />
              ) : (
                getInitials(member.displayName || member.email)
              )}
              {member.isCreator && (
                <div className="tph-owner-badge" title="Trip Owner">
                  <Crown size={10} />
                </div>
              )}
            </div>
          ))}
          {members.length > 5 && (
            <div className="tph-member-avatar tph-member-more">
              +{members.length - 5}
            </div>
          )}
        </div>

        <button className="tph-invite-btn" onClick={onInviteClick}>
          <UserPlus className="tph-invite-icon" />
          Invite
        </button>
      </div>
    </header>
  );
}
