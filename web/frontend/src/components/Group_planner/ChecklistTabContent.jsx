import React, { useState } from 'react';
import { User } from 'lucide-react';
import './ChecklistTabContent.css';

/**
 * ChecklistTabContent Component
 * Displays group checklist with add/toggle functionality
 * Matches demo_2.txt design
 */
export default function ChecklistTabContent({
  checklist = [],
  currentUserId,
  onAddChecklistItem,
  onToggleChecklistItem,
  onDeleteChecklistItem,
}) {
  const [newItem, setNewItem] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (newItem.trim() && onAddChecklistItem) {
      onAddChecklistItem(newItem.trim());
      setNewItem('');
    }
  };

  const pendingItems = checklist.filter(item => !item.completed);
  const completedItems = checklist.filter(item => item.completed);

  return (
    <div className="checklist-tab-content">
      <h2 className="checklist-title">Trip Checklist</h2>

      {/* Add New Item Form */}
      <form onSubmit={handleSubmit} className="checklist-form">
        <input
          type="text"
          placeholder="Add a packing item or task (e.g., Book rental car)"
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          className="checklist-input"
          required
        />
        <button type="submit" className="checklist-add-btn">
          Add
        </button>
      </form>

      {/* Pending Items */}
      <div className="checklist-section">
        <h3 className="checklist-section-title">To Do ({pendingItems.length})</h3>
        {pendingItems.length === 0 ? (
          <p className="checklist-empty">Everything is packed! Ready for takeoff.</p>
        ) : (
          pendingItems.map((item) => (
            <div key={item.id} className="checklist-item">
              <label className="checklist-label">
                <input
                  type="checkbox"
                  checked={item.completed}
                  onChange={() => onToggleChecklistItem && onToggleChecklistItem(item.id)}
                  className="checklist-checkbox"
                />
                <span className="checklist-text">{item.item}</span>
              </label>
              <div className="checklist-item-actions">
                <div className="checklist-author">
                  <User className="author-icon" />
                  {item.authorId === currentUserId ? 'You' : item.authorId?.substring(0, 8) + '...'}
                </div>
                <button
                  className="checklist-delete-btn"
                  onClick={() => onDeleteChecklistItem && onDeleteChecklistItem(item.id)}
                  title="Delete item"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Completed Items */}
      <div className="checklist-section checklist-completed-section">
        <h3 className="checklist-section-title">Completed ({completedItems.length})</h3>
        <div className="checklist-completed">
          {completedItems.map((item) => (
            <div key={item.id} className="checklist-item checklist-item-completed">
              <label className="checklist-label">
                <input
                  type="checkbox"
                  checked={item.completed}
                  onChange={() => onToggleChecklistItem && onToggleChecklistItem(item.id)}
                  className="checklist-checkbox"
                />
                <span className="checklist-text">{item.item}</span>
              </label>
              <div className="checklist-item-actions">
                <div className="checklist-author">
                  <User className="author-icon" />
                  {item.authorId === currentUserId ? 'You' : item.authorId?.substring(0, 8) + '...'}
                </div>
                <button
                  className="checklist-delete-btn"
                  onClick={() => onDeleteChecklistItem && onDeleteChecklistItem(item.id)}
                  title="Delete item"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
