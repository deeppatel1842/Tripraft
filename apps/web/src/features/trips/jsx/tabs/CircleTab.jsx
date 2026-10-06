// Purpose: Renders the Circle Tab interface within apps\web\src\features\trips\jsx\tabs.
import React, { useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useGroupMembers, gpKeys } from '../../../../hooks/useGroupPlannerQuery';
import groupPlannerApi from '../../../../services/groupPlannerApi';
import { useAuth } from '../../../../context/AuthContext';
import { useRevokeAiConsent } from '../../../../hooks/useAiConsentQuery';
import { AI_BOTS } from '../../../scout/aiBots';
import { toArray } from '../../utils/groupPlannerUtils';
import { getInitials } from '../../utils/formatters';


/**
 * Circle tab - group members and roles.
 *
 * Props: groupId, showToast
 */
export default function CircleTab({ groupId, showToast }) {
  const queryClient = useQueryClient();
  const { currentUser } = useAuth();
  const revokeConsent = useRevokeAiConsent(groupId);
  const { data: membersRaw } = useGroupMembers(groupId);
  const members = useMemo(() => toArray(membersRaw, 'members'), [membersRaw]);
  const currentMember = members.find(m => String(m.user_id) === String(currentUser?.uid));
  const canManageRoles = ['creator', 'admin'].includes(currentMember?.role);
  const allMembers = useMemo(() => [...members, ...AI_BOTS], [members]);

  const handleUpdateMemberRole = async (memberId, newRole) => {
    try {
      await groupPlannerApi.updateMemberRole(groupId, memberId, newRole);
      queryClient.invalidateQueries({ queryKey: gpKeys.members(groupId) });
      showToast('Role updated');
    } catch (e) {
      showToast(e?.message || 'Failed to update role', 'error');
    }
  };

  return (
    <div className="gp-view">
      <h2 className="gp-section-title">The Circle.</h2>
      {currentMember && currentMember.role !== 'viewer' && <button className="gp-section-action" disabled={revokeConsent.isPending} onClick={() => revokeConsent.mutate(undefined, {
        onSuccess: () => showToast('AI consent withdrawn and saved AI data deleted'),
        onError: error => showToast(error.message || 'Unable to withdraw AI consent', 'error'),
      })}>{revokeConsent.isPending ? 'Deleting AI data...' : 'Forget my AI data'}</button>}
      <div className="gp-circle-list">
        {allMembers.length === 0 ? (
          <div className="gp-empty-agenda">No members yet.</div>
        ) : (
          allMembers.map((m) => (
            <div key={m.id || m.user_id} className="gp-circle-member">
              <div className="gp-circle-left">
                {m.type === 'ai' ? (
                  <div className="gp-circle-avatar gp-circle-avatar-ai">AI</div>
                ) : m.photo_url || m.avatar ? (
                  <img src={m.photo_url || m.avatar} alt={m.display_name || m.name} className="gp-circle-avatar-img" />
                ) : (
                  <div className="gp-circle-avatar">{getInitials(m.display_name || m.name || m.email || 'U')}</div>
                )}
                <div>
                  <span className="gp-circle-name">
                    {m.display_name || m.name || m.email || 'Unknown'}
                    <span className={'gp-role-badge ' + (m.type === 'ai' ? 'ai' : m.role === 'creator' || m.is_creator ? 'lead' : 'member')}>
                      {m.type === 'ai' ? 'AI Bot' : m.role === 'creator' ? 'Lead' : m.role || 'Member'}
                    </span>
                  </span>
                  <div className="gp-circle-handle">{m.email || 'Partner'}</div>
                </div>
              </div>
              {canManageRoles && m.type !== 'ai' && m.role !== 'creator' && !m.is_creator && (m.user_id || m.id) && (
                <select
                  className="gp-circle-role-select"
                  value={m.role || 'member'}
                  onChange={(e) => handleUpdateMemberRole(m.user_id || m.id, e.target.value)}
                >
                  <option value="admin">Admin</option>
                  <option value="member">Member</option>
                  <option value="viewer">Viewer</option>
                </select>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
