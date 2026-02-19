/**
 * EditItineraryModal - Modal for editing itinerary item date and notes
 */
import React, { useState, useEffect } from 'react';
import { X, Calendar, FileText, Clock } from 'lucide-react';
import '../css/EditItineraryModal.css';

export default function EditItineraryModal({
  isOpen,
  onClose,
  onSave,
  item,
  isLoading = false,
}) {
  const [formData, setFormData] = useState({
    date: '',
    time: '',
    duration: '',
    notes: '',
  });

  // Reset form when modal opens with item data
  useEffect(() => {
    if (isOpen && item) {
      setFormData({
        date: item.date || '',
        time: item.time || '',
        duration: item.duration || '1 hr',
        notes: item.notes || item.remarks || '',
      });
    }
  }, [isOpen, item]);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    onSave({
      id: item.id,
      date: formData.date || null,
      time: formData.time || null,
      duration: formData.duration,
      notes: formData.notes,
    });
  };

  if (!isOpen) return null;

  return (
    <div className="eim-overlay" onClick={onClose}>
      <div className="eim-modal" onClick={(e) => e.stopPropagation()}>
        <div className="eim-header">
          <h2 className="eim-title">Edit {item?.name || 'Place'}</h2>
          <button className="eim-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="eim-form">
          {/* Date */}
          <div className="eim-field">
            <label className="eim-label">
              <Calendar size={16} />
              Date
            </label>
            <input
              type="date"
              className="eim-input"
              value={formData.date}
              onChange={(e) => setFormData(prev => ({ ...prev, date: e.target.value }))}
            />
          </div>

          {/* Time */}
          <div className="eim-field">
            <label className="eim-label">
              <Clock size={16} />
              Time
            </label>
            <input
              type="time"
              className="eim-input"
              value={formData.time}
              onChange={(e) => setFormData(prev => ({ ...prev, time: e.target.value }))}
            />
          </div>

          {/* Duration */}
          <div className="eim-field">
            <label className="eim-label">
              <Clock size={16} />
              Duration
            </label>
            <select
              className="eim-input"
              value={formData.duration}
              onChange={(e) => setFormData(prev => ({ ...prev, duration: e.target.value }))}
            >
              <option value="30 min">30 minutes</option>
              <option value="1 hr">1 hour</option>
              <option value="1.5 hrs">1.5 hours</option>
              <option value="2 hrs">2 hours</option>
              <option value="3 hrs">3 hours</option>
              <option value="Half day">Half day</option>
              <option value="Full day">Full day</option>
            </select>
          </div>

          {/* Notes */}
          <div className="eim-field">
            <label className="eim-label">
              <FileText size={16} />
              Notes
            </label>
            <textarea
              className="eim-textarea"
              placeholder="Add any notes about this place..."
              value={formData.notes}
              onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
              rows={4}
            />
          </div>

          <div className="eim-actions">
            <button type="button" className="eim-cancel-btn" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="eim-save-btn" disabled={isLoading}>
              {isLoading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
