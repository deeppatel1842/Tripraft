/**
 * CreateChecklistModal - Modal for adding a new checklist item
 * Simple form with item text input
 */
import React, { useState, useEffect, useRef } from 'react';
import { X, CheckSquare } from 'lucide-react';
import '../css/CreateChecklistModal.css';

export default function CreateChecklistModal({
  isOpen,
  onClose,
  onAddItem,
  isLoading = false,
}) {
  const [itemText, setItemText] = useState('');
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  // Reset form and focus when modal opens
  useEffect(() => {
    if (isOpen) {
      setItemText('');
      setError('');
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    
    if (!itemText.trim()) {
      setError('Please enter an item');
      return;
    }
    
    onAddItem(itemText.trim());
  };

  // Handle Enter key to submit
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="ccm-overlay" onClick={onClose}>
      <div className="ccm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ccm-header">
          <div className="ccm-header-title">
            <CheckSquare size={20} className="ccm-header-icon" />
            <h2 className="ccm-title">Add Checklist Item</h2>
          </div>
          <button className="ccm-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="ccm-form">
          {/* Item Text */}
          <div className="ccm-field">
            <label className="ccm-label">What needs to be done?</label>
            <input
              ref={inputRef}
              type="text"
              className="ccm-input"
              placeholder="e.g., Book hotel room, Buy travel insurance..."
              value={itemText}
              onChange={(e) => setItemText(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </div>

          {/* Quick suggestions */}
          <div className="ccm-suggestions">
            <span className="ccm-suggestions-label">Quick add:</span>
            <div className="ccm-suggestion-chips">
              {['Book flights', 'Reserve hotel', 'Get travel insurance', 'Pack bags', 'Confirm reservations'].map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  className="ccm-suggestion-chip"
                  onClick={() => setItemText(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="ccm-error">{error}</div>
          )}

          {/* Actions */}
          <div className="ccm-actions">
            <button type="button" className="ccm-cancel-btn" onClick={onClose}>
              Cancel
            </button>
            <button 
              type="submit" 
              className="ccm-submit-btn"
              disabled={isLoading}
            >
              {isLoading ? 'Adding...' : 'Add Item'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
