import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Calendar, Users } from 'lucide-react';
import { formatDateLocal } from '../../../utils/timezoneUtils';
import '../css/SidebarComponent.css';

// Group icon with initials from group name
function GroupIcon({ name }) {
  const getInitials = (name) => {
    if (!name) return '?';
    const words = name.split(' ').filter(w => w.length > 0);
    if (words.length >= 2) {
      return (words[0][0] + words[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  const getColorFromName = (name) => {
    const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f97316', '#10b981', '#3b82f6'];
    const hash = (name || 'default').split('').reduce((a, b) => a + b.charCodeAt(0), 0);
    return colors[hash % colors.length];
  };

  const initials = getInitials(name);
  const bgColor = getColorFromName(name);

  return (
    <div className="sc-group-icon" style={{ backgroundColor: bgColor }}>
      {initials}
    </div>
  );
}

export default function SidebarComponent({
  groups,
  selectedGroupId,
  onSelectGroup,
  onCreateGroup,
  onDeleteGroup,
  currentUserId,
}) {
  const groupsArray = Object.values(groups || {});
  const [expandedGroupId, setExpandedGroupId] = useState(null);
  const sidebarRef = useRef(null);

  // Close delete dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (expandedGroupId && sidebarRef.current && !event.target.closest('.sc-options-menu') && !event.target.closest('.sc-group-options-btn')) {
        setExpandedGroupId(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [expandedGroupId]);

  // Helper function to format date
  const formatDate = (dateString) => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      return formatDateLocal(date, { month: 'short', day: 'numeric', year: '2-digit' });
    } catch (error) {
      return '';
    }
  };

  // Format trip date range
  const formatTripDates = (startDate, endDate) => {
    if (!startDate) return '';
    const start = new Date(startDate);
    const startStr = start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    if (!endDate) return startStr;
    const end = new Date(endDate);
    const endStr = end.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    return `${startStr} - ${endStr}`;
  };

  return (
    <aside className="sc-sidebar" ref={sidebarRef}>
      {/* Create button at top */}
      <button className="sc-create-btn" onClick={onCreateGroup}>
        ✚ Create New Group
      </button>

      <div className="sc-section-title">Your Groups</div>
      
      <div className="sc-group-list">
        {groupsArray && Object.keys(groups).length > 0 ? (
          groupsArray.map((group) => {
            // Group ID can be either 'id' or 'group_id'
            const groupId = group.id || group.group_id;
            const isExpanded = expandedGroupId === groupId;
            
            // Get creator info for avatar - handle both array and object formats
            
            return (
              <div key={groupId} className="sc-group-container">
                <div
                  className={`sc-group-btn ${selectedGroupId === groupId ? 'sc-group-btn-active' : ''}`}
                  onClick={() => onSelectGroup(groupId)}
                  title={group.name}
                >
                  {/* Group Icon with Initials */}
                  <GroupIcon name={group.name} />
                  <div className="sc-group-info">
                    <div className="sc-group-name">{group.name}</div>
                    <div className="sc-group-meta">
                      {group.destination && (
                        <div className="sc-group-destination">
                          <MapPin size={10} className="sc-meta-icon" />
                          {group.destination}
                        </div>
                      )}
                      {(group.start_date || group.end_date) && (
                        <div className="sc-group-dates">
                          <Calendar size={10} className="sc-meta-icon" />
                          {formatTripDates(group.start_date, group.end_date)}
                        </div>
                      )}
                      {group.created_at && !group.start_date && (
                        <div className="sc-group-date">
                          Created: {formatDate(group.created_at)}
                        </div>
                      )}
                    </div>
                  </div>
                  <button
                    className="sc-group-options-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setExpandedGroupId(isExpanded ? null : groupId);
                    }}
                    title="Options"
                  >
                    ⋮
                  </button>
                </div>
                
                {/* Options menu */}
                {isExpanded && (
                  <div className="sc-options-menu">
                    <button
                      className="sc-delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (onDeleteGroup) {
                          onDeleteGroup(groupId);
                        }
                        setExpandedGroupId(null);
                      }}
                    >
                      🗑 Delete Group
                    </button>
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <div className="sc-empty-state">
            No groups yet
          </div>
        )}
      </div>
    </aside>
  );
}
