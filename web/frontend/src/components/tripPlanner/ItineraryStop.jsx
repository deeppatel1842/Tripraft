import React from 'react';
import Icon from './Icon';

const ItineraryStop = ({ stop, isLast }) => {
  return (
    <li className="stop-item">
      <div className="stop-container">
        {!isLast && <span className="stop-connector" />}
        <div className="stop-content">
          <div className="stop-icon-wrapper">
            <span className="stop-icon">
              <Icon name={stop.icon || 'mapPin'} className={stop.color || 'text-purple-600'} />
            </span>
          </div>
          <div className="stop-details">
            <div className="stop-header">
              <p className="stop-name">{stop.name}</p>
              <p className="stop-time">{stop.arrivalTime}</p>
            </div>
            <div className="stop-info">
              <div className="info-item">
                <Icon name="clock" />
                <span>Hours: {stop.hours}</span>
              </div>
              <div className="info-item">
                <Icon name="hourglass" />
                <span>Visit: {stop.visitDuration}</span>
              </div>
              {stop.lunch && (
                <div className="info-item lunch-break">
                  <Icon name="utensils" />
                  <span>Lunch Break (~60 minutes)</span>
                </div>
              )}
              {stop.travelToNext && (
                <div className="info-item travel-info">
                  <Icon name="car" />
                  <span>Travel: {stop.travelToNext} to next stop</span>
                </div>
              )}
              {stop.endOfDay && (
                <div className="info-item end-of-day">
                  <Icon name="moon" />
                  <span>End of day</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </li>
  );
};

export default ItineraryStop;
