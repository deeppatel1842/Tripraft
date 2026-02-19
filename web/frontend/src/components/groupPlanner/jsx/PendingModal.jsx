import React from 'react';
import { X } from 'lucide-react';
import '../css/PendingModal.css';

const DEMO_PENDING = [
  {
    id: 1,
    name: 'David Chen',
    email: 'david.chen@example.com',
    avatar: 'https://i.pravatar.cc/100?img=5',
  },
  {
    id: 2,
    name: 'Alicia Keys',
    email: 'alicia@music.com',
    avatar: 'https://i.pravatar.cc/100?img=9',
  },
];

export default function PendingModal({
  isOpen,
  onClose,
  pendingRequests = DEMO_PENDING,
  invitedBy = 'Deep Patel',
  onAccept,
  onReject,
}) {
  if (!isOpen) return null;

  const getInitials = (name) => {
    if (!name) return '?';
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="pm-overlay" onClick={onClose}>
      <div className="pm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="pm-header">
          <h3 className="pm-title">
            <span className="pm-dot"></span>
            Pending Requests
          </h3>
          <button className="pm-close-btn" onClick={onClose}>
            <X className="pm-close-icon" />
          </button>
        </div>

        <div className="pm-content">
          {pendingRequests.map((request, index) => (
            <React.Fragment key={request.id}>
              {index > 0 && <div className="pm-divider"></div>}
              <div className="pm-request">
                <div className="pm-avatar">
                  {request.avatar ? (
                    <img src={request.avatar} alt={request.name} />
                  ) : (
                    getInitials(request.name)
                  )}
                </div>
                <div className="pm-info">
                  <p className="pm-name">{request.name}</p>
                  <p className="pm-email">{request.email}</p>
                  <div className="pm-actions">
                    <button
                      className="pm-accept-btn"
                      onClick={() => onAccept && onAccept(request.id)}
                    >
                      Accept
                    </button>
                    <button
                      className="pm-reject-btn"
                      onClick={() => onReject && onReject(request.id)}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            </React.Fragment>
          ))}

          {pendingRequests.length === 0 && (
            <div className="pm-empty">No pending requests</div>
          )}
        </div>

        <div className="pm-footer">
          Invited by {invitedBy}
        </div>
      </div>
    </div>
  );
}
