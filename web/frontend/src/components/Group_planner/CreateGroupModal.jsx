import React, { useState } from 'react';

export default function CreateGroupModal({ isOpen, onClose, onSubmit }) {
  const [groupName, setGroupName] = useState('');
  const [destination, setDestination] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!groupName.trim() || !destination.trim()) {
      console.error('All fields are required');
      return;
    }
    setLoading(true);
    try {
      await onSubmit({ name: groupName, destination });
      setGroupName('');
      setDestination('');
      onClose();
    } catch (error) {
      console.error('Error creating group:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className={`demo-modal ${isOpen ? 'show' : ''}`} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="demo-dialog">
        <header>
          <strong>Create New Group</strong>
          <button className="demo-close" onClick={onClose}>×</button>
        </header>
        <div className="demo-body">
          <div className="demo-field">
            <input
              type="text"
              className="demo-input"
              placeholder="Group name (e.g., Tokyo Trip 2025)"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            />
          </div>
          <div className="demo-field" style={{ marginTop: '12px' }}>
            <input
              type="text"
              className="demo-input"
              placeholder="Destination (e.g., Tokyo, Japan)"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            />
          </div>
        </div>
        <div className="demo-foot">
          <button className="demo-ghost" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button className="demo-primary" onClick={handleSubmit} disabled={loading}>
            {loading ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
}
