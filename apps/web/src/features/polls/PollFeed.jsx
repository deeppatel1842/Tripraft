// Purpose: Renders poll choices, vote counts and voter panels using state and handlers supplied by chat.
import React from 'react';
import { Check, Trash2 } from 'lucide-react';
import { formatRelativeTime } from '../trips/utils/formatters';

export default function PollFeed({ polls, members, uidStr, handleVotePoll, handleDeletePoll, expandedVoters, setExpandedVoters }) {
  return <>
        {polls.map((poll) => {
          const totalVotes = poll.voted_by ? poll.voted_by.length : 0;
          return (
            <div key={'poll-' + poll.id} className="gp-poll-chat-wrap">
              <div className="gp-poll-avatar-badge">POLL</div>
              <div className="gp-poll-card-v2">
                <div className="gp-poll-card-v2-top">
                  <span className="gp-poll-card-v2-question">{poll.name}</span>
                  <div className="gp-poll-card-v2-meta">
                    <span className="gp-poll-card-v2-votes">{totalVotes} vote{totalVotes !== 1 ? 's' : ''}</span>
                    {poll.is_multiple_choice && <span className="gp-poll-card-v2-multi">Multi</span>}
                  </div>
                </div>
                <div className="gp-poll-card-v2-options">
                  {(poll.options || []).map((opt, oi) => {
                    const count = poll.votes?.[opt] || 0;
                    const pct = totalVotes > 0 ? Math.round((count / totalVotes) * 100) : 0;
                    const voters = poll.votes_detail?.[opt] || [];
                    const myVote = voters.some((v) => String(v) === uidStr);
                    return (
                      <div key={oi} className={'gp-poll-opt-v2' + (myVote ? ' voted' : '')} onClick={() => handleVotePoll(poll.id, oi)}>
                        <div className="gp-poll-opt-v2-bar" style={{ width: pct + '%' }} />
                        <div className="gp-poll-opt-v2-content">
                          <span className="gp-poll-opt-v2-text">
                            {myVote && <Check size={12} style={{ marginRight: 4 }} />}
                            {opt}
                          </span>
                          <span className="gp-poll-opt-v2-pct">{count > 0 ? pct + '%' : ''}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="gp-poll-card-v2-footer">
                  <div className="gp-poll-card-v2-author">
                    {poll.created_by_name && <span>by {poll.created_by_name}</span>}
                    <span className="gp-poll-card-v2-time">{formatRelativeTime(poll.created_at)}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button className="gp-poll-view-btn" onClick={() => setExpandedVoters(expandedVoters === poll.id ? null : poll.id)}>View Voters</button>
                    <button className="gp-itinerary-edit-btn" onClick={() => handleDeletePoll(poll.id)} title="Delete poll"><Trash2 size={11} /></button>
                  </div>
                </div>
                {expandedVoters === poll.id && (
                  <div className="gp-poll-voters-panel">
                    {(poll.options || []).map((opt, oi) => {
                      const voters = poll.votes_detail?.[opt] || [];
                      if (voters.length === 0) return null;
                      const voterNames = voters.map((vid) => {
                        const m = members.find((mb) => String(mb.id) === String(vid) || String(mb.user_id) === String(vid));
                        return m ? (m.display_name || m.name || m.email) : null;
                      }).filter(Boolean);
                      return (
                        <div key={oi} className="gp-poll-voters-row">
                          <span className="gp-poll-voters-opt-label">{opt}</span>
                          <div className="gp-poll-voters-names">
                            {voterNames.map((name, ni) => <span key={ni} className="gp-poll-voter-chip-v2">{name}</span>)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          );
        })}

  </>;
}
