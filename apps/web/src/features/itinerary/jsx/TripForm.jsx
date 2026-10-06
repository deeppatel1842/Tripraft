// Purpose: Renders the Trip Form interface within apps\web\src\features\itinerary\jsx.
import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import DestinationAutocomplete from '../../../components/common/jsx/DestinationAutocomplete';

const TripForm = ({ onGenerate }) => {
  const [searchParams] = useSearchParams();
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    city: searchParams.get('destination') || '',
    days: 3,
    pacing: 'M'
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Handle destination autocomplete selection
  const handleDestinationChange = (value) => {
    setFormData(prev => ({
      ...prev,
      city: value
    }));
  };

  const handleDestinationSelect = (suggestion) => {
    // Use just the city name for trip planner
    setFormData(prev => ({
      ...prev,
      city: suggestion.name
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.city.trim()) {
      setError('Please enter a destination');
      return;
    }
    setError('');
    onGenerate(formData);
  };

  return (
    <div className="trip-form-section">
      <div className="trip-form-header">
        <h1 className="trip-form-main-title">AI-Generated Itinerary</h1>
        <p className="trip-form-subtitle">Let's give you a plan, our AI will make it beautiful</p>
      </div>
      
      <div className="trip-form-container">
        <form onSubmit={handleSubmit} className="trip-form">
          {error && <p role="alert">{error}</p>}
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="city" className="form-label">
                Destination
              </label>
              <DestinationAutocomplete
                id="city"
                name="city"
                value={formData.city}
                onChange={handleDestinationChange}
                onSelect={handleDestinationSelect}
                placeholder="Enter city name (e.g., Paris, Tokyo, New York)"
                allowedTypes={['city']}
                variant="tripPlanner"
                className="trip-form-autocomplete"
              />
            </div>

          <div className="form-group">
            <label htmlFor="days" className="form-label">
              Number of Days
            </label>
            <input
              type="number"
              id="days"
              name="days"
              min="1"
              max="14"
              value={formData.days}
              onChange={handleChange}
              className="form-input"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="pacing" className="form-label">
              Pacing
            </label>
            <select
              id="pacing"
              name="pacing"
              value={formData.pacing}
              onChange={handleChange}
              className="form-input"
            >
              <option value="R">Relaxed</option>
              <option value="M">Moderate</option>
              <option value="P">Packed</option>
            </select>
          </div>



          <div className="form-group form-submit-group">
            <button type="submit" className="form-submit-btn">
              <i className="fas fa-magic"></i>
              Generate Plan
            </button>
          </div>
        </div>
      </form>
      </div>
    </div>
  );
};

export default TripForm;
