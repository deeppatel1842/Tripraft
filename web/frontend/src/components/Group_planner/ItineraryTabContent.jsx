import React, { useState, useEffect } from 'react';
import ItineraryBuilder from './ItineraryBuilder';
import './ItineraryTabContent.css';

/**
 * Itinerary Tab Content
 * Wrapper for the ItineraryBuilder component
 * Provides toggle between Timeline and Document view
 */
export default function ItineraryTabContent({
  groupName = 'Trip Group',
  destination = 'Destination',
  places = [],
  currentUserId,
  onUpdatePlaceRemark,
  onUpdatePlaceDetails,
  onUpdateItineraryDocument,
  onDeletePlace,
  savedDocument = '',
}) {
  const [viewMode, setViewMode] = useState('timeline'); // 'timeline' or 'document'
  
  // All hooks must be at the top level - no conditional hooks
  const [editingPlaceId, setEditingPlaceId] = useState(null);
  const [editText, setEditText] = useState('');
  const [lastSaved, setLastSaved] = useState(new Date());
  const [documentContent, setDocumentContent] = useState(savedDocument);
  const [documentSaveTimer, setDocumentSaveTimer] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  // Initialize document content when savedDocument changes (on group switch)
  useEffect(() => {
    setDocumentContent(savedDocument || '');
  }, [savedDocument]);

  // Auto-save indicator
  useEffect(() => {
    const timer = setInterval(() => {
      setLastSaved(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleEditClick = (place) => {
    setEditingPlaceId(place.id);
    setEditText(place.remarks || '');
  };

  const handleSaveEdit = async (placeId) => {
    if (onUpdatePlaceRemark) {
      try {
        await onUpdatePlaceRemark(placeId, editText);
        setEditingPlaceId(null);
        setLastSaved(new Date());
      } catch (error) {
        console.error('Error saving itinerary:', error);
      }
    }
  };

  const handleCancelEdit = () => {
    setEditingPlaceId(null);
    setEditText('');
  };

  const getTimeAgo = () => {
    const seconds = Math.floor((new Date() - lastSaved) / 1000);
    if (seconds < 5) return 'Just now';
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    return 'Recently';
  };

  // Auto-save document with debounce
  const handleDocumentChange = (e) => {
    const content = e.target.value;
    setDocumentContent(content);
    setIsSaving(true);

    // Clear existing timer
    if (documentSaveTimer) {
      clearTimeout(documentSaveTimer);
    }

    // Set new timer
    const timer = setTimeout(async () => {
      if (onUpdateItineraryDocument) {
        console.log('Auto-saving document...');
        try {
          await onUpdateItineraryDocument(content);
          setLastSaved(new Date());
          setIsSaving(false);
        } catch (error) {
          console.error('Failed to save document:', error);
          setIsSaving(false);
        }
      }
    }, 1500); // 1.5 second debounce for longer text

    setDocumentSaveTimer(timer);
  };

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (documentSaveTimer) {
        clearTimeout(documentSaveTimer);
      }
    };
  }, [documentSaveTimer]);

  return (
    <div className="itinerary-wrapper">
      {/* View Toggle - Always visible */}
      <div className="itinerary-view-toggle">
        <button
          className={`toggle-btn ${viewMode === 'timeline' ? 'active' : ''}`}
          onClick={() => setViewMode('timeline')}
        >
          📅 Timeline View
        </button>
        <button
          className={`toggle-btn ${viewMode === 'document' ? 'active' : ''}`}
          onClick={() => setViewMode('document')}
        >
          📄 Document View
        </button>
      </div>

      {/* Render Timeline View */}
      {viewMode === 'timeline' && (
        <ItineraryBuilder
          places={places}
          currentUserId={currentUserId}
          groupName={groupName}
          onUpdatePlaceDetails={onUpdatePlaceDetails}
          onDeletePlace={onDeletePlace}
        />
      )}

      {/* Render Document View - Editable Word Document */}
      {viewMode === 'document' && (
        <div className="document-editor-container">
          <div className="document-header">
            <h1 className="document-title">{groupName} - Travel Itinerary</h1>
            <div className={`auto-save-indicator ${isSaving ? 'saving' : ''}`}>
              <span className="save-icon">{isSaving ? '⏳' : '💾'}</span>
              <span className="save-text">{isSaving ? 'Saving...' : `Saved ${getTimeAgo()}`}</span>
            </div>
          </div>
          
          <div className="document-content">
            <textarea
              className="document-textarea"
              value={documentContent}
              onChange={handleDocumentChange}
              placeholder="Start writing your itinerary document here...

You can add:
- Trip overview and highlights
- Accommodation details
- Transportation information
- Budget breakdown
- Packing list
- Emergency contacts
- Any other travel notes

This is your personal travel document!"
              rows={20}
            />
          </div>
        </div>
      )}
    </div>
  );
}
