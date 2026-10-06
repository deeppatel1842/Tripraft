// Purpose: Renders the Create Group Modal interface within apps\web\src\features\trips\jsx.
/**
 * CreateGroupModal - Modal for creating a new group
 * Features city autocomplete for destination
 */
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X, MapPin, Users, Calendar, Loader2 } from 'lucide-react';
import GlobalConfig from '../../../config/globalConfig';
import '../css/CreateGroupModal.css';

export default function CreateGroupModal({
  isOpen,
  onClose,
  onCreateGroup,
  isLoading = false,
}) {
  const [formData, setFormData] = useState({
    name: '',
    destination: '',
    destinationLat: null,
    destinationLng: null,
    destinationType: null,
    startDate: '',
    endDate: '',
  });
  
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 });
  
  const debounceRef = useRef(null);
  const destinationInputRef = useRef(null);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setFormData({
        name: '',
        destination: '',
        destinationLat: null,
        destinationLng: null,
        destinationType: null,
            startDate: '',
        endDate: '',
      });
      setErrors({});
      setSuggestions([]);
    }
  }, [isOpen]);

  const suggestionsRef = useRef(null);

  // Track input position for dropdown portal positioning
  useEffect(() => {
    const updatePosition = () => {
      if (destinationInputRef.current) {
        const rect = destinationInputRef.current.getBoundingClientRect();
        setDropdownPosition({
          top: rect.bottom + 4,
          left: rect.left,
          width: rect.width,
        });
      }
    };

    if (showSuggestions) {
      updatePosition();
      window.addEventListener('scroll', updatePosition);
      window.addEventListener('resize', updatePosition);
      
      // Close dropdown when clicking outside (but not on suggestions portal)
      const handleClickOutside = (e) => {
        if (
          destinationInputRef.current && !destinationInputRef.current.contains(e.target) &&
          suggestionsRef.current && !suggestionsRef.current.contains(e.target)
        ) {
          setShowSuggestions(false);
        }
      };
      document.addEventListener('mousedown', handleClickOutside);
      
      return () => {
        window.removeEventListener('scroll', updatePosition);
        window.removeEventListener('resize', updatePosition);
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [showSuggestions]);

  // Fetch city autocomplete suggestions
  const fetchSuggestions = useCallback(async (query) => {
    if (!query || query.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    setSearchLoading(true);
    try {
      const { default: apiClient } = await import('../../../utils/apiClient');
      const data = await apiClient.get(
        `${GlobalConfig.ENDPOINTS.GROUP_PLANNER}/destinations/autocomplete?q=${encodeURIComponent(query)}&limit=10`
      );
      const results = data.data || data.suggestions || [];
      setSuggestions(results);
      setShowSuggestions(results.length > 0);
    } catch (error) {
      setSuggestions([]);
      setShowSuggestions(false);
    } finally {
      setSearchLoading(false);
    }
  }, []);

  const handleDestinationChange = (e) => {
    const value = e.target.value;
    setFormData(prev => ({
      ...prev,
      destination: value,
      destinationLat: null,
      destinationLng: null,
      destinationType: null,
    }));
    
    // Debounce API calls
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    
    debounceRef.current = setTimeout(() => {
      fetchSuggestions(value);
    }, 300);
  };

  const handleSelectSuggestion = (suggestion) => {
    setFormData(prev => ({
      ...prev,
      destination: suggestion.display_name || suggestion.name,
      destinationLat: suggestion.lat ?? suggestion.latitude,
      destinationLng: suggestion.lng ?? suggestion.longitude,
      destinationType: suggestion.type || 'city',
    }));
    setSuggestions([]);
    setShowSuggestions(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Validate
    const newErrors = {};
    if (!formData.name.trim()) {
      newErrors.name = 'Group name is required';
    }
    if (!formData.destination.trim()) {
      newErrors.destination = 'Destination is required';
    }
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    
    onCreateGroup({
      name: formData.name.trim(),
      destination: formData.destination.trim(),
      destination_lat: formData.destinationLat,
      destination_lng: formData.destinationLng,
      destination_type: formData.destinationType,
      start_date: formData.startDate || null,
      end_date: formData.endDate || null,
    });
  };

  if (!isOpen) return null;

  return (
    <div className="cgm-overlay" onClick={onClose}>
      <div className="cgm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="cgm-header">
          <h2 className="cgm-title">Create New Group</h2>
          <button className="cgm-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="cgm-form">
          {/* Group Name */}
          <div className="cgm-field">
            <label className="cgm-label">
              <Users size={16} />
              Group Name *
            </label>
            <input
              type="text"
              className={`cgm-input ${errors.name ? 'cgm-input-error' : ''}`}
              placeholder="e.g., Summer Vacation 2026"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              autoFocus
            />
            {errors.name && <span className="cgm-error">{errors.name}</span>}
          </div>

          {/* Destination with Autocomplete */}
          <div className="cgm-field cgm-field-relative">
            <label className="cgm-label">
              <MapPin size={16} />
              Destination *
            </label>
            <div className="cgm-input-wrapper">
              <input
                ref={destinationInputRef}
                type="text"
                className={`cgm-input ${errors.destination ? 'cgm-input-error' : ''}`}
                placeholder="Search for a city..."
                value={formData.destination}
                onChange={handleDestinationChange}
                onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                autoComplete="off"
              />
              {searchLoading && (
                <Loader2 className="cgm-input-loader" size={16} />
              )}
            </div>
            {errors.destination && <span className="cgm-error">{errors.destination}</span>}
            
            {/* Suggestions Dropdown - Rendered via Portal to avoid modal overflow clipping */}
            {showSuggestions && suggestions.length > 0 && createPortal(
              <div 
                ref={suggestionsRef}
                className="cgm-suggestions"
                style={{
                  position: 'fixed',
                  top: `${dropdownPosition.top}px`,
                  left: `${dropdownPosition.left}px`,
                  width: `${dropdownPosition.width}px`,
                  zIndex: 9999,
                }}
              >
                {suggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    className="cgm-suggestion-item"
                    onClick={() => handleSelectSuggestion(suggestion)}
                  >
                    <MapPin size={14} className="cgm-suggestion-icon" />
                    <div className="cgm-suggestion-text">
                      <span className="cgm-suggestion-name">
                        {suggestion.display_name || suggestion.name}
                      </span>
                      {suggestion.country && (
                        <span className="cgm-suggestion-country">
                          {suggestion.country}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>,
              document.body
            )}
          </div>

          {/* Dates */}
          <div className="cgm-field-row">
            <div className="cgm-field">
              <label className="cgm-label">
                <Calendar size={16} />
                Start Date
              </label>
              <input
                type="date"
                className="cgm-input"
                value={formData.startDate}
                onChange={(e) => setFormData(prev => ({ ...prev, startDate: e.target.value }))}
              />
            </div>
            <div className="cgm-field">
              <label className="cgm-label">
                <Calendar size={16} />
                End Date
              </label>
              <input
                type="date"
                className="cgm-input"
                value={formData.endDate}
                onChange={(e) => setFormData(prev => ({ ...prev, endDate: e.target.value }))}
              />
            </div>
          </div>

          <p className="cgm-hint">Invite friends from the group workspace after creating your group.</p>

          {/* Submit */}
          <div className="cgm-actions">
            <button type="button" className="cgm-cancel-btn" onClick={onClose}>
              Cancel
            </button>
            <button 
              type="submit" 
              className="cgm-submit-btn"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="cgm-btn-loader" size={16} />
                  Creating...
                </>
              ) : (
                'Create Group'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
