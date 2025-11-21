import React from 'react';

export default function TabNavigation({ activeTab, onTabChange, tabs, counts = {} }) {
  const tabLabels = {
    plan: 'Travel Plan',
    itinerary: 'Itinerary',
    album: 'Album',
    polls: 'Polls',
    checklist: 'Checklist',
    members: 'Members',
    pending: 'Pending'
  };

  return (
    <nav className="demo-tabs">
      {tabs.map((tab) => (
        <button
          key={tab}
          className={`demo-tab ${activeTab === tab ? 'active' : ''}`}
          onClick={() => onTabChange(tab)}
        >
          {tabLabels[tab] || tab}
          {counts[tab] !== undefined && (
            <span className="demo-badge">{counts[tab]}</span>
          )}
        </button>
      ))}
    </nav>
  );
}
