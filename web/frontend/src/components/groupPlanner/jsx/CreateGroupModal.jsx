/**
 * CreateGroupModal - Modal for creating a new group
 * Features city autocomplete for destination
 */
import React, { useState, useCallback, useEffect, useRef } from 'react';
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
    inviteEmails: '',
    startDate: '',
    endDate: '',
  });
  
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [errors, setErrors] = useState({});
  
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
        inviteEmails: '',
        startDate: '',
        endDate: '',
      });
      setErrors({});
      setSuggestions([]);
    }
  }, [isOpen]);

  // Fetch city autocomplete suggestions
  const fetchSuggestions = useCallback(async (query) => {
    if (!query || query.length < 2) {
      setSuggestions([]);
      return;
    }

    setSearchLoading(true);
    try {
      // API_BASE_URL is http://localhost:5000/api, endpoint is /group-planner/destinations/autocomplete
      const response = await fetch(
        `${GlobalConfig.API_BASE_URL}/group-planner/destinations/autocomplete?q=${encodeURIComponent(query)}&limit=10`,
        { credentials: 'include' }
      );
      
      if (response.ok) {
        const data = await response.json();
        setSuggestions(data.data || data.suggestions || []);
        setShowSuggestions(true);
      } else {
        setSuggestions([]);
      }
    } catch (error) {
      setSuggestions([]);
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
      destinationLat: suggestion.lat || suggestion.latitude,
      destinationLng: suggestion.lng || suggestion.longitude,
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
    
    // Parse invite emails
    const emails = formData.inviteEmails
      .split(',')
      .map(e => e.trim())
      .filter(e => e && e.includes('@'));
    
    onCreateGroup({
      name: formData.name.trim(),
      destination: formData.destination.trim(),
      destination_lat: formData.destinationLat,
      destination_lng: formData.destinationLng,
      destination_type: formData.destinationType,
      start_date: formData.startDate || null,
      end_date: formData.endDate || null,
      invite_emails: emails,
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
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              />
              {searchLoading && (
                <Loader2 className="cgm-input-loader" size={16} />
              )}
            </div>
            {errors.destination && <span className="cgm-error">{errors.destination}</span>}
            
            {/* Suggestions Dropdown */}
            {showSuggestions && suggestions.length > 0 && (
              <div className="cgm-suggestions">
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
              </div>
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

          {/* Invite Friends */}
          <div className="cgm-field">
            <label className="cgm-label">
              <Users size={16} />
              Invite Friends (optional)
            </label>
            <input
              type="text"
              className="cgm-input"
              placeholder="Enter emails separated by commas"
              value={formData.inviteEmails}
              onChange={(e) => setFormData(prev => ({ ...prev, inviteEmails: e.target.value }))}
            />
            <span className="cgm-hint">e.g., friend1@email.com, friend2@email.com</span>
          </div>

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
