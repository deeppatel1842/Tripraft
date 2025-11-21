import React from 'react';
import UserAvatar from '../common/UserAvatar';
import './MembersTabContent.css';

export default function MembersTabContent({ members, currentUserId, onDeleteMember }) {
  // Ensure members is an array
  const membersList = Array.isArray(members) ? members : [];
  
  console.log('🟢 [MEMBERS] Tab rendered with members:', membersList);
  
  // Debug: Check first member structure
  if (membersList.length > 0) {
    const firstMember = membersList[0];
    console.log('🔍 [MEMBERS] First member data:', {
      display_name: firstMember.display_name,
      displayName: firstMember.displayName,
      email: firstMember.email,
      user_id: firstMember.user_id,
      uid: firstMember.uid,
      id: firstMember.id,
      avatar_url: firstMember.avatar_url,
      photoURL: firstMember.photoURL,
      is_creator: firstMember.is_creator,
      role: firstMember.role,
      allKeys: Object.keys(firstMember)
    });
  }
  
  // Check if current user is the creator/owner of the group
  const currentMember = membersList?.find(m => (m.uid || m.user_id || m.id) === currentUserId);
  const currentUserIsOwner = currentMember?.is_creator === true || currentMember?.role === 'creator';
  
  console.log('🔐 [MEMBERS] Current user is owner:', currentUserIsOwner, 'currentMember:', currentMember);

  return (
    <div className="mtc-container">
      <div className="mtc-list">
        {membersList && membersList.length > 0 ? (
          membersList.map((member) => {
            const memberId = member.uid || member.user_id || member.id;
            // Map backend snake_case to camelCase for UserAvatar
            const memberUser = {
              displayName: member.display_name || member.displayName,
              email: member.email,
              photoURL: member.avatar_url || member.photoURL || null
            };
            
            // Show remove button ONLY if:
            // 1. Current user is the owner
            // 2. This is NOT the owner's own card
            const showRemoveButton = currentUserIsOwner && memberId !== currentUserId;
            
            return (
              <div key={memberId} className="mtc-member-card">
                <div className="mtc-member-left">
                  <UserAvatar user={memberUser} size="large" />
                  <div className="mtc-member-info">
                    <div className="mtc-member-name">
                      {member.display_name || member.email || 'Unknown User'}
                      {memberId === currentUserId && (
                        <span className="mtc-badge-you">YOU</span>
                      )}
                      {(member.is_creator === true || member.role === 'creator') && (
                        <span className="mtc-badge-owner">OWNER</span>
                      )}
                    </div>
                    <div className="mtc-member-email">{member.email || 'No email'}</div>
                  </div>
                </div>
                
                {showRemoveButton && (
                  <button
                    onClick={() => onDeleteMember && onDeleteMember(memberId)}
                    className="mtc-remove-btn"
                    title="Remove member"
                  >
                    🗑 Remove
                  </button>
                )}
              </div>
            );
          })
        ) : (
          <div className="mtc-empty">
            <div className="mtc-empty-icon">👥</div>
            <div className="mtc-empty-text">No members yet</div>
          </div>
        )}
      </div>
    </div>
  );
}
