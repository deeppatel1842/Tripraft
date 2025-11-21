import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Header from '../layout/Header';
import Footer from '../layout/Footer';
import TripMap from '../tripPlanner/TripMap';
import TripPlanCard from '../tripPlanner/TripPlanCard';
import TripTips from '../tripPlanner/TripTips';
import Checklist from '../tripPlanner/Checklist';
import TripForm from '../tripPlanner/TripForm';
import '../css/TripPlanner.css';

const TripPlanner = () => {
  const { currentUser, signOut } = useAuth();
  const [plans, setPlans] = useState([]);
  const [activeTab, setActiveTab] = useState('plans');
  const [isLoading, setIsLoading] = useState(false);
  const [generatingStep, setGeneratingStep] = useState('');
  const [isMapScriptLoaded, setMapScriptLoaded] = useState(false);

  useEffect(() => {
    if (!document.getElementById('leaflet-css')) {
      const link = document.createElement('link');
      link.id = 'leaflet-css';
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      link.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
      link.crossOrigin = '';
      document.head.appendChild(link);
    }

    const onScriptLoad = () => {
      setTimeout(() => setMapScriptLoaded(true), 100);
    };

    if (window.L && typeof window.L.map === 'function') {
      onScriptLoad();
      return;
    }

    let script = document.getElementById('leaflet-js');
    if (!script) {
      script = document.createElement('script');
      script.id = 'leaflet-js';
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
      script.crossOrigin = '';
      document.body.appendChild(script);
    }

    script.addEventListener('load', onScriptLoad);

    return () => {
      if (script) {
        script.removeEventListener('load', onScriptLoad);
      }
    };
  }, []);

  const handleGenerate = async (formData) => {
    setIsLoading(true);
    setPlans([]);
    setGeneratingStep('Initializing trip planner...');

    try {
      // Parse exclude and require fields
      const excludeTypes = formData.exclude 
        ? formData.exclude.split(',').map(t => t.trim()).filter(t => t)
        : [];
      const requirePlaces = formData.require 
        ? formData.require.split(',').map(t => t.trim()).filter(t => t)
        : [];

      // Prepare API request
      const requestData = {
        city: formData.city,
        num_days: parseInt(formData.days),
        pacing: formData.pacing,
        exclude_types: excludeTypes,
        require_places: requirePlaces
      };

      setGeneratingStep(`Analyzing destination: ${formData.city}...`);
      
      // Call backend API
      const response = await fetch('http://localhost:5000/api/trip/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate trip');
      }

      const data = await response.json();
      
      console.log('Backend response:', data); // Debug log
      
      // Handle both old format (itinerary) and new format (itineraries)
      const hasNewFormat = data.success && data.itineraries;
      const hasOldFormat = data.success && data.itinerary;
      
      if (hasNewFormat || hasOldFormat) {
        // Transform a single itinerary array
        const transformItinerary = (itinerary) => {
          const transformed = itinerary.map(day => ({
            day: day.day,
            title: day.theme || `Day ${day.day}`,
            stops: (day.activities || []).map(activity => {
              const iconAndColor = getIconAndColorForPlace(activity.place_obj);
              return {
                arrivalTime: activity.start_time,
                name: activity.place_name,
                icon: iconAndColor.icon,
                color: iconAndColor.color,
                hours: activity.opening_hours,
                visitDuration: `~${activity.visit_duration_mins} minutes`,
                travelToNext: activity.travel_to_next_mins || null,
                lunch: activity.needs_lunch_break || false,
                endOfDay: activity.is_last || false,
                coords: activity.place_obj?.location 
                  ? [activity.place_obj.location.latitude, activity.place_obj.location.longitude]
                  : null,
                website: activity.website,
                placeObj: activity.place_obj
              };
            })
          }));

          // Mark last stop of each day as end of day
          transformed.forEach(day => {
            if (day.stops.length > 0) {
              day.stops[day.stops.length - 1].endOfDay = true;
            }
          });

          return transformed;
        };

        const formattedPlans = [];

        // Handle new format with both itineraries
        if (hasNewFormat) {
          // Add city-focused itinerary
          if (data.itineraries.city_focused && data.itineraries.city_focused.length > 0) {
            formattedPlans.push({
              title: `${data.city.toUpperCase()} EXPLORER`,
              airport: data.airport,
              itinerary: transformItinerary(data.itineraries.city_focused),
              highRankedPlaces: (data.other_top_places || []).map(place => ({
                name: place.name,
                rating: place.rating,
                reviewCount: place.review_count || 0,
                coords: place.location?.latitude && place.location?.longitude 
                  ? [place.location.latitude, place.location.longitude]
                  : null
              })),
              specialPlaces: data.special_places
            });
          }

          // Add day trip itinerary
          if (data.itineraries.with_day_trip && data.itineraries.with_day_trip.length > 0) {
            formattedPlans.push({
              title: `${data.city.toUpperCase()} & BEYOND (WITH DAY TRIP)`,
              airport: data.airport,
              itinerary: transformItinerary(data.itineraries.with_day_trip),
              highRankedPlaces: (data.other_top_places || []).map(place => ({
                name: place.name,
                rating: place.rating,
                reviewCount: place.review_count || 0,
                coords: place.location?.latitude && place.location?.longitude 
                  ? [place.location.latitude, place.location.longitude]
                  : null
              })),
              specialPlaces: data.special_places
            });
          }
        } 
        // Handle old format with single itinerary
        else if (hasOldFormat) {
          formattedPlans.push({
            title: `${data.city.toUpperCase()} EXPLORER`,
            airport: data.airport,
            itinerary: transformItinerary(data.itinerary),
            highRankedPlaces: (data.other_top_places || []).map(place => ({
              name: place.name,
              rating: place.rating,
              reviewCount: place.review_count || 0,
              coords: place.location?.latitude && place.location?.longitude 
                ? [place.location.latitude, place.location.longitude]
                : null
            })),
            specialPlaces: data.special_places
          });
        }

        if (formattedPlans.length === 0) {
          throw new Error('No valid itinerary data received from server');
        }

        setPlans(formattedPlans);
        setGeneratingStep('Trip plan ready!');
      } else {
        console.error('Invalid response structure:', data);
        throw new Error('Invalid response from server');
      }

    } catch (error) {
      console.error('Error generating trip:', error);
      setGeneratingStep(`Error: ${error.message}`);
      alert(`Failed to generate trip: ${error.message}`);
    } finally {
      setTimeout(() => {
        setIsLoading(false);
      }, 1000);
    }
  };

  // Helper function to determine icon and color based on place types
  const getIconAndColorForPlace = (placeObj) => {
    if (!placeObj || !placeObj.types || placeObj.types.length === 0) {
      return { icon: 'mapPin', color: 'text-purple-600' }; // default
    }
    
    const types = placeObj.types;
    
    if (types.includes('restaurant') || types.includes('cafe')) 
      return { icon: 'utensils', color: 'text-red-600' };
    if (types.includes('museum') || types.includes('art_gallery')) 
      return { icon: 'museum', color: 'text-indigo-600' };
    if (types.includes('park') || types.includes('natural_feature') || types.includes('state_park')) 
      return { icon: 'leaf', color: 'text-green-600' };
    if (types.includes('shopping_mall') || types.includes('store')) 
      return { icon: 'shoppingBag', color: 'text-blue-600' };
    if (types.includes('beach')) 
      return { icon: 'sun', color: 'text-orange-600' };
    if (types.includes('amusement_park')) 
      return { icon: 'star', color: 'text-pink-600' };
    if (types.includes('aquarium') || types.includes('zoo')) 
      return { icon: 'fish', color: 'text-cyan-500' };
    if (types.includes('night_club') || types.includes('bar')) 
      return { icon: 'moon', color: 'text-indigo-700' };
    if (types.includes('airport')) 
      return { icon: 'plane', color: 'text-gray-600' };
    if (types.includes('church') || types.includes('place_of_worship')) 
      return { icon: 'landmark', color: 'text-amber-700' };
    if (types.includes('garden')) 
      return { icon: 'leaf', color: 'text-emerald-600' };
    if (types.includes('monument') || types.includes('historical_landmark')) 
      return { icon: 'landmark', color: 'text-amber-600' };
    if (types.includes('tourist_attraction')) 
      return { icon: 'mapPin', color: 'text-yellow-600' };
    
    return { icon: 'mapPin', color: 'text-purple-600' }; // fallback default
  };

  const TabContent = () => {
    if (isLoading) {
      return (
        <div className="generating-plan">
          <div className="spinner"></div>
          <h2 className="generating-title">Crafting Your Adventure...</h2>
          <p className="generating-step">{generatingStep}</p>
        </div>
      );
    }

    switch (activeTab) {
      case 'plans':
        return (
          <div>
            {isMapScriptLoaded ? (
              <TripMap plans={plans} />
            ) : (
              <div className="map-loading">
                <div className="map-spinner"></div>
                <p className="map-loading-text">Loading Map...</p>
              </div>
            )}
            
            {/* Visual Cards Only */}
            <div className="trip-plans-grid">
              {plans.map((plan, index) => (
                <TripPlanCard key={index} plan={plan} />
              ))}
            </div>
            
            <div className="ai-disclaimer-text">
              <p>AI-Generated Content: This itinerary was created by AI. Please verify all details, timings, and availability before your trip.</p>
            </div>
          </div>
        );
      case 'tips':
        return <TripTips />;
      case 'checklist':
        return <Checklist />;
      default:
        return null;
    }
  };

  return (
    <div className="trip-planner">
      <Header 
        isAuthenticated={!!currentUser}
        user={currentUser}
        onLogout={signOut}
      />
      <main className="trip-planner-main">
        <TripForm onGenerate={handleGenerate} />
        {!isLoading && plans.length > 0 && (
          <div className="tab-navigation">
            <nav className="tab-nav">
              <button
                onClick={() => setActiveTab('plans')}
                className={`tab-button ${activeTab === 'plans' ? 'active' : ''}`}
              >
                <i className="fas fa-map-marked-alt"></i>
                <span>Trip Plans</span>
              </button>
              <button
                onClick={() => setActiveTab('tips')}
                className={`tab-button ${activeTab === 'tips' ? 'active' : ''}`}
              >
                <i className="fas fa-lightbulb"></i>
                <span>Trip Tips</span>
              </button>
              <button
                onClick={() => setActiveTab('checklist')}
                className={`tab-button ${activeTab === 'checklist' ? 'active' : ''}`}
              >
                <i className="fas fa-clipboard-check"></i>
                <span>Checklist</span>
              </button>
            </nav>
          </div>
        )}
        {plans.length > 0 && <TabContent />}
      </main>
      <Footer />
    </div>
  );
};

export default TripPlanner;
