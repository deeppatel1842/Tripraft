import React, { useState } from 'react';
// import UserAvatar from '../common/UserAvatar';
import './SidebarComponent.css';

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
  
  console.log('🟣 [SIDEBAR] Groups received:', groups);
  console.log('🟣 [SIDEBAR] Groups array:', groupsArray);

  // Helper function to format date
  const formatDate = (dateString) => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
    } catch (error) {
      return '';
    }
  };

  return (
    <aside className="sc-sidebar">
      <div className="sc-brand">TripRaft</div>
      
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
            
            // Get creator info for avatar
            const creator = group.member_details?.find(m => m.is_creator);
            const creatorUser = creator ? {
              displayName: creator.display_name,
              email: creator.email,
              photoURL: creator.photoURL || null
            } : null;
            
            console.log('🟣 [SIDEBAR] Rendering group:', { groupId, name: group.name, creator: creatorUser });
            
            return (
              <div key={groupId} className="sc-group-container">
                <div
                  className={`sc-group-btn ${selectedGroupId === groupId ? 'sc-group-btn-active' : ''}`}
                  onClick={() => onSelectGroup(groupId)}
                  title={group.name}
                >
                  {/* {creatorUser && (
                    <UserAvatar user={creatorUser} size="small" />
                  )} */}
                  <div className="sc-group-info">
                    <div className="sc-group-name">{group.name}</div>
                    <div className="sc-group-meta">
                      {group.destination && (
                        <div className="sc-group-destination">{group.destination}</div>
                      )}
                      {group.created_at && (
                        <div className="sc-group-date">Created: {formatDate(group.created_at)}</div>
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
