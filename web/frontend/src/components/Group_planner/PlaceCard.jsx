import React, { useState } from 'react';
import './PlaceCard.css';

export default function PlaceCard({ place, currentUserId, onVote, onDelete, onUpdateRemark }) {
  const [editingRemark, setEditingRemark] = useState(false);
  const [remarkText, setRemarkText] = useState(place.remarks || '');
  
  // Handle both array (new) and object (legacy) vote formats
  const votes = Array.isArray(place.votes) ? place.votes : [];
  const hasVoted = votes.includes(currentUserId);

  return (
    <div className="plc-card">
      <div className="plc-header">
        <div className="plc-name">{place.name}</div>
        <div className="plc-buttons">
          <button className={`plc-btn-vote ${hasVoted ? 'plc-btn-voted' : ''}`} onClick={onVote}>
            👍 <span>{votes.length}</span>
          </button>
          <button className="plc-btn-remark" onClick={() => setEditingRemark(!editingRemark)}>
            ✎
          </button>
          <button className="plc-btn-delete" onClick={onDelete}>
            🗑
          </button>
        </div>
      </div>
      <div className="plc-remark-section">
        {!editingRemark ? (
          <div className={place.remarks ? 'plc-remark-text' : 'plc-remark-text plc-remark-empty'}>
            {place.remarks || 'No remarks yet.'}
          </div>
        ) : (
          <div className="plc-remark-edit">
            <textarea
              className="plc-textarea"
              rows="2"
              placeholder="Add a remark..."
              value={remarkText}
              onChange={(e) => setRemarkText(e.target.value)}
            />
            <div className="plc-button-group">
              <button className="plc-btn-cancel" onClick={() => setEditingRemark(false)}>
                Cancel
              </button>
              <button
                className="plc-btn-save"
                onClick={() => {
                  onUpdateRemark(remarkText);
                  setEditingRemark(false);
                }}
              >
                Save
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
