import React from 'react';
import { MapPin, Plus } from 'lucide-react';
import { formatDate } from '../../utils/formatters';

/**
 * Dashboard view when no group is selected.
 *
 * Props: groups, groupsLoading, onSelectGroup, onCreateGroup
 */
export default function GroupSelector({ groups, groupsLoading, onSelectGroup, onCreateGroup }) {
  return (
    <div className="gp-dashboard">
      <div className="gp-dashboard-header">
        <div>
          <h1>Group Planner</h1>
          <p style={{ color: '#71717a', fontSize: 14, margin: '4px 0 0' }}>
            Plan trips together with friends and family.
          </p>
        </div>
        <button className="gp-btn-create" onClick={onCreateGroup}>
          <Plus size={16} /> New Group
        </button>
      </div>

      {groupsLoading ? (
        <div className="gp-loading"><div className="gp-loading-spinner" /> Loading your groups...</div>
      ) : groups.length === 0 ? (
        <div className="gp-empty-agenda">
          No groups yet. Create one to start planning.
        </div>
      ) : (
        <div className="gp-groups-grid">
          {groups.map((g) => (
            <div key={g.id} className="gp-group-card" onClick={() => onSelectGroup(g.id)}>
              <h3 className="gp-group-card-name">{g.name}</h3>
              <p className="gp-group-card-dest"><MapPin size={13} />{g.destination || 'No destination set'}</p>
              <div className="gp-group-card-meta">
                {g.member_count != null && <span>{g.member_count} members</span>}
                {g.start_date && <span>{formatDate(g.start_date)}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
