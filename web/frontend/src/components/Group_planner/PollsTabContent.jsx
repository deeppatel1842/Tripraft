import React from 'react';
import PollCard from './PollCard';
import './PollsTabContent.css';

export default function PollsTabContent({
  polls,
  currentUserId,
  members,
  onCreatePoll,
  onVotePoll,
  onDeletePoll,
}) {
  console.log('🟢 [POLLS] Tab rendered with polls:', polls);
  console.log('🟢 [POLLS] Members:', members);
  
  return (
    <div className="demo-tab-content">
      <div className="demo-polls-header">
        <button className="demo-polls-create-btn" onClick={onCreatePoll}>
          ✚ Create New Poll
        </button>
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
        {polls && polls.length > 0 ? (
          polls.map((poll) => (
            <PollCard
              key={poll.id}
              poll={poll}
              currentUserId={currentUserId}
              members={members}
              onVote={(option) => onVotePoll(poll.id, option)}
              onDelete={() => onDeletePoll(poll.id)}
            />
          ))
        ) : (
          <div style={{ textAlign: 'center', color: '#9ca3af', padding: '40px 20px' }}>
            <div style={{ fontSize: '48px', marginBottom: '12px' }}>📋</div>
            <div style={{ fontSize: '15px', fontWeight: 500 }}>No polls yet</div>
            <div style={{ fontSize: '13px', marginTop: '8px' }}>Create one to get started!</div>
          </div>
        )}
      </div>
    </div>
  );
}
