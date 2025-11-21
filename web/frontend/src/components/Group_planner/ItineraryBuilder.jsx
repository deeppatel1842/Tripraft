import React, { useMemo, useState } from 'react';
import { Edit2 } from 'lucide-react';
import './ItineraryBuilder.css';

/**
 * ItineraryBuilder Component
 * Simple card-based itinerary grouped by day
 * Shows welcome screen when no plans exist
 */
export default function ItineraryBuilder({
  places = [],
  currentUserId,
  groupName = 'Trip Group',
  onUpdatePlaceDetails,
  onDeletePlace,
}) {
  const [editingPlaceId, setEditingPlaceId] = useState(null);
  const [editForm, setEditForm] = useState({
    date: '',
    name: '',
    duration: '',
    notes: ''
  });

  const formatDateHeader = (dateStr) => {
    if (!dateStr) return 'Date Not Set';
    // Parse date as local date (YYYY-MM-DD) to avoid timezone shifts
    const [year, month, day] = dateStr.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    const dayName = date.toLocaleDateString('en-US', { weekday: 'long' });
    const formattedDate = date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    });
    return `${dayName}, ${formattedDate}`;
  };

  const handleEditClick = (place) => {
    setEditingPlaceId(place.id);
    setEditForm({
      date: place.visit_date || '',
      name: place.name || '',
      duration: place.suggested_duration || '',
      notes: place.remarks || ''
    });
  };

  const handleFieldChange = (field, value) => {
    setEditForm({ ...editForm, [field]: value });
  };

  const handleSave = async () => {
    if (onUpdatePlaceDetails) {
      try {
        const updates = {
          visit_date: editForm.date,
          suggested_duration: editForm.duration,
          remarks: editForm.notes
        };
        await onUpdatePlaceDetails(editingPlaceId, updates);
        setEditingPlaceId(null);
      } catch (error) {
        console.error('Error saving place:', error);
      }
    }
  };

  const handleCancel = () => {
    setEditingPlaceId(null);
  };

  const handleDelete = async (placeId, placeName) => {
    if (onDeletePlace) {
      try {
        await onDeletePlace(placeId);
      } catch (error) {
        console.error('Error deleting place:', error);
      }
    }
  };

  // Sort places by date (earliest first)
  const sortedPlaces = useMemo(() => {
    return [...places].sort((a, b) => {
      // Places without dates go to the end
      if (!a.visit_date) return 1;
      if (!b.visit_date) return -1;
      
      // Compare dates
      return new Date(a.visit_date) - new Date(b.visit_date);
    });
  }, [places]);

  return (
    <div className="itinerary-builder">
      {places.length === 0 ? (
        // Welcome Screen when no places exist
        <div className="itinerary-welcome-screen">
          <h1 className="welcome-title">Trip Itinerary</h1>
          <p className="welcome-subtitle">Your day-by-day travel plan</p>
          <div className="welcome-empty-state">
            <h3>No places added yet</h3>
            <p>Add places in the Travel Plan tab to build your itinerary</p>
          </div>
        </div>
      ) : (
        // Itinerary Timeline - Show all places
        <div className="itinerary-content">
          <h2 className="itinerary-title">Trip Timeline</h2>
          <div className="itinerary-places-list">
            {sortedPlaces.map((item) => (
              <div key={item.id} className="itinerary-place-card">
                {editingPlaceId === item.id ? (
                  // Edit Mode
                  <div className="place-edit-form">
                    <div className="edit-header">
                      <label 
                        className="date-label-clickable"
                        onClick={(e) => {
                          if (e.target.tagName !== 'INPUT') {
                            document.getElementById(`date-input-${item.id}`)?.showPicker();
                          }
                        }}
                      >
                        Date:
                        <input
                          type="date"
                          value={editForm.date}
                          onChange={(e) => handleFieldChange('date', e.target.value)}
                          className="edit-date-input"
                          id={`date-input-${item.id}`}
                        />
                      </label>
                    </div>
                    
                    <div className="edit-row">
                      <label>
                        Place Name:
                        <input
                          type="text"
                          value={editForm.name}
                          onChange={(e) => setEditForm({...editForm, name: e.target.value})}
                          className="edit-name-input"
                          disabled
                          title="Place name cannot be changed here"
                        />
                      </label>
                      <label>
                        Duration:
                        <input
                          type="text"
                          value={editForm.duration}
                          onChange={(e) => handleFieldChange('duration', e.target.value)}
                          className="edit-duration-input"
                          placeholder="e.g., 2 hours"
                        />
                      </label>
                    </div>

                    <label>
                      Notes:
                      <textarea
                        value={editForm.notes}
                        onChange={(e) => handleFieldChange('notes', e.target.value)}
                        className="edit-notes-textarea"
                        rows={3}
                        placeholder="Add notes about this place..."
                      />
                    </label>

                    <div className="edit-actions">
                      <button className="btn-save" onClick={handleSave}>
                        Save
                      </button>
                      <button className="btn-cancel" onClick={handleCancel}>
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  // View Mode
                  <>
                    <div className="place-card-header">
                      <span className="place-date-day">{formatDateHeader(item.visit_date)}</span>
                      <div className="place-actions">
                        <button
                          className="edit-place-btn"
                          title="Edit Place"
                          onClick={() => handleEditClick(item)}
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          className="delete-place-btn"
                          title="Delete Place"
                          onClick={() => handleDelete(item.id, item.name)}
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            <line x1="10" y1="11" x2="10" y2="17"></line>
                            <line x1="14" y1="11" x2="14" y2="17"></line>
                          </svg>
                        </button>
                      </div>
                    </div>
                    
                    <div className="place-card-divider"></div>
                    
                    <div className="place-info-row">
                      <span className="place-name">{item.name}</span>
                      <span className="place-duration">⏱️ {item.suggested_duration || 'N/A'}</span>
                    </div>
                    
                    <div className="place-notes">
                      📝 {item.remarks || 'N/A'}
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
