import React, { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';
import '../css/EditChecklistModal.css';

export default function EditChecklistModal({
  isOpen,
  onClose,
  onSave,
  item,
  isLoading = false,
}) {
  const [text, setText] = useState('');
  const [priority, setPriority] = useState('medium');
  const [dueDate, setDueDate] = useState('');

  useEffect(() => {
    if (item) {
      setText(item.label || item.text || item.item || '');
      setPriority(item.priority || 'medium');
      setDueDate(item.due_date || '');
    }
  }, [item]);

  const handleSave = () => {
    if (!text.trim()) return;
    
    onSave({
      id: item?.id,
      text: text.trim(),
      priority,
      due_date: dueDate || null,
    });
  };

  if (!isOpen) return null;

  return (
    <div className="ecm-overlay" onClick={onClose}>
      <div className="ecm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ecm-header">
          <h2 className="ecm-title">
            {item ? 'Edit Checklist Item' : 'Add Checklist Item'}
          </h2>
          <button className="ecm-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="ecm-body">
          <div className="ecm-field">
            <label className="ecm-label">Task</label>
            <input
              type="text"
              className="ecm-input"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Enter task description..."
              autoFocus
            />
          </div>

          <div className="ecm-row">
            <div className="ecm-field ecm-field-half">
              <label className="ecm-label">Priority</label>
              <select
                className="ecm-select"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>

            <div className="ecm-field ecm-field-half">
              <label className="ecm-label">Due Date</label>
              <input
                type="date"
                className="ecm-input"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="ecm-footer">
          <button className="ecm-btn ecm-btn-cancel" onClick={onClose}>
            Cancel
          </button>
          <button
            className="ecm-btn ecm-btn-save"
            onClick={handleSave}
            disabled={isLoading || !text.trim()}
          >
            <Save size={14} />
            {isLoading ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
