import React, { useState } from 'react';

const TripForm = ({ onGenerate }) => {
  const [formData, setFormData] = useState({
    city: 'San Diego',
    days: 3,
    pacing: 'M',
    exclude: '',
    require: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
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
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="city" className="form-label">
                City Name
              </label>
              <input
                type="text"
                id="city"
                name="city"
                value={formData.city}
                onChange={handleChange}
                className="form-input"
                required
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

          <div className="form-group">
            <label htmlFor="exclude" className="form-label">
              Types to Exclude <span className="form-optional">(optional)</span>
            </label>
            <input
              type="text"
              id="exclude"
              name="exclude"
              placeholder="museums, parks"
              value={formData.exclude}
              onChange={handleChange}
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="require" className="form-label">
              Places to Require <span className="form-optional">(optional)</span>
            </label>
            <input
              type="text"
              id="require"
              name="require"
              placeholder="Specific places"
              value={formData.require}
              onChange={handleChange}
              className="form-input"
            />
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
