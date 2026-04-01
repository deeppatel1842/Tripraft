import React, { useMemo } from 'react';
import { useGroupActivities, useGroupPolls, useGroupMembers } from '../../../../hooks/useGroupPlannerQuery';
import { toArray } from '../../utils/groupPlannerUtils';
import { formatRelativeTime, formatActivityMessage } from '../../utils/formatters';

/**
 * Pulse tab - activity feed and poll summaries.
 *
 * Props: groupId
 */
export default function PulseTab({ groupId }) {
  const { data: activitiesRaw } = useGroupActivities(groupId);
  const { data: pollsRaw } = useGroupPolls(groupId);
  const { data: membersRaw } = useGroupMembers(groupId);

  const activities = useMemo(() => toArray(activitiesRaw, 'activities'), [activitiesRaw]);
  const polls = useMemo(() => toArray(pollsRaw, 'polls'), [pollsRaw]);
  const members = useMemo(() => toArray(membersRaw, 'members'), [membersRaw]);

  return (
    <div className="gp-view">
      <h2 className="gp-section-title">Pulse.</h2>

      {polls.length > 0 && polls.map((poll) => {
        const totalVotes = poll.voted_by ? poll.voted_by.length : 0;
        const voterNames = (poll.voted_by || []).map((vid) => {
          const m = members.find((mb) => String(mb.id) === String(vid) || String(mb.user_id) === String(vid));
          return m ? (m.display_name || m.name || m.email) : null;
        }).filter(Boolean);
        return (
          <div key={'pulse-poll-' + poll.id} className="gp-pulse-item">
            <p className="gp-pulse-text">
              {totalVotes > 0 ? (
                <><strong>{voterNames.join(', ')}</strong> voted in <strong>{poll.name}</strong></>
              ) : (
                <>Poll created: <strong>{poll.name}</strong></>
              )}
            </p>
            <p className="gp-pulse-time">{formatRelativeTime(poll.created_at)}</p>
          </div>
        );
      })}

      <h3 className="gp-pulse-subheading">Activity</h3>
      <div className="gp-pulse-feed">
        {activities.length === 0 && polls.length === 0 ? (
          <div className="gp-empty-agenda">No activity yet. Actions by group members will appear here.</div>
        ) : (
          activities.map((a, i) => (
            <div key={a.id || i} className="gp-pulse-item">
              <p className="gp-pulse-text">
                {a.user_name && <strong>{a.user_name}: </strong>}
                {formatActivityMessage(a)}
              </p>
              <p className="gp-pulse-time">{formatRelativeTime(a.created_at)}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
