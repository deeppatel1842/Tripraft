import React, { useState } from 'react';
import './PollCard.css';

export default function PollCard({ poll, currentUserId, members = [], onVote, onDelete }) {
  const [expandedVoters, setExpandedVoters] = useState(null);
  const hasVoted = poll.voted_by?.includes(currentUserId);
  const totalVotes = Object.values(poll.votes || {}).reduce((a, b) => a + b, 0);
  const pollOptions = Object.entries(poll.votes || {});
  const colors = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'];

  // Get voter details from votes_detail in poll
  const votes_detail = poll.votes_detail || {};
  
  // Find which option the current user voted for
  let userVotedOption = null;
  Object.keys(votes_detail).forEach(option => {
    const voterIds = votes_detail[option] || [];
    if (voterIds.includes(currentUserId)) {
      userVotedOption = option;
    }
  });
  
  // Create a map of user IDs to member details for quick lookup
  const memberMap = {};
  members.forEach(member => {
    const userId = member.id || member.user_id || member.uid;
    memberMap[userId] = {
      id: userId,
      name: member.display_name || member.email?.split('@')[0] || 'Unknown User',
      email: member.email
    };
  });
  
  // Build votersByOption from votes_detail
  const votersByOption = {};
  Object.keys(votes_detail).forEach(option => {
    const voterIds = votes_detail[option] || [];
    votersByOption[option] = voterIds.map(userId => {
      const member = memberMap[userId];
      return {
        id: userId,
        name: userId === currentUserId ? 'You' : (member?.name || 'Unknown User'),
        email: member?.email
      };
    });
  });

  return (
    <div className="pc-container">
      <div className="pc-header">
        <h3 className="pc-title">{poll.name}</h3>
        <button
          onClick={onDelete}
          className="pc-delete-btn"
          title="Delete poll"
        >
          ✕
        </button>
      </div>

      <div className="pc-options">
        {pollOptions.map(([option, count], index) => {
          const percentage = totalVotes > 0 ? (count / totalVotes) * 100 : 0;
          const bgColor = colors[index % colors.length];
          const voters = votersByOption[option] || [];

          return (
            <div key={option} className="pc-option-item">
              <div className="pc-option-header">
                <span className="pc-option-text">{option}</span>
                <span className="pc-vote-count">{count}</span>
              </div>
              <div className="pc-bar-wrapper">
                <div 
                  className="pc-bar-fill"
                  style={{
                    width: `${percentage}%`,
                    backgroundColor: bgColor,
                  }}
                />
              </div>
              <div className="pc-percentage">{Math.round(percentage)}%</div>
              
              {voters.length > 0 && (
                <div className="pc-voters-container">
                  <button
                    className="pc-voters-btn"
                    onClick={() => setExpandedVoters(expandedVoters === option ? null : option)}
                    style={{ color: bgColor }}
                  >
                    {voters.length} voted {expandedVoters === option ? '▼' : '▶'}
                  </button>
                  {expandedVoters === option && (
                    <div className="pc-voters-list">
                      {voters.map((voter) => (
                        <div key={voter.id} className="pc-voter-item">
                          <div className="pc-voter-avatar" style={{ backgroundColor: bgColor }}>
                            {voter.name.charAt(0).toUpperCase()}
                          </div>
                          <span className="pc-voter-name">{voter.name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="pc-actions">
        <div className="pc-vote-buttons">
          {pollOptions.map(([option], index) => {
            const bgColor = colors[index % colors.length];
            const isUserVote = option === userVotedOption;
            return (
              <button
                key={option}
                className={`pc-vote-btn ${isUserVote ? 'pc-vote-btn-selected' : ''}`}
                onClick={() => onVote(option)}
                style={{
                  borderColor: bgColor,
                  color: isUserVote ? '#fff' : bgColor,
                  backgroundColor: isUserVote ? bgColor : 'transparent',
                  fontWeight: isUserVote ? '600' : '500'
                }}
                title={isUserVote ? `Your vote (click to change)` : `Vote for ${option}`}
              >
                {isUserVote && '✓ '}
                {option.split(' ')[0]}
              </button>
            );
          })}
        </div>
        {hasVoted && (
          <div className="pc-voted-hint" style={{ marginTop: '8px', fontSize: '12px', color: '#6b7280', textAlign: 'center' }}>
            Click any option to change your vote
          </div>
        )}
      </div>

      <div className="pc-footer">
        <span className="pc-total-votes">{totalVotes} total {totalVotes === 1 ? 'vote' : 'votes'}</span>
      </div>
    </div>
  );
}
