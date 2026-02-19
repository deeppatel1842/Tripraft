import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import Header from '../../layout/jsx/Header';
import Footer from '../../layout/jsx/Footer';
import TripMap from '../../tripPlanner/jsx/TripMap';
import TripPlanCard from '../../tripPlanner/jsx/TripPlanCard';
import TripTips from '../../tripPlanner/jsx/TripTips';
import Checklist from '../../tripPlanner/jsx/Checklist';
import TripForm from '../../tripPlanner/jsx/TripForm';
import tripPlannerService from '../../../services/tripPlannerService';
import '../../tripPlanner/css/TripPlanner.css';

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
      setGeneratingStep(`Analyzing destination: ${formData.city}...`);
      
      // Call Trip Planner API via service
      const data = await tripPlannerService.generateTrip({
        city: formData.city,
        days: parseInt(formData.days),
        pacing: formData.pacing,
        exclude: formData.exclude || '',
        require: formData.require || ''
      });
      
      if (data.success && data.itinerary && data.itinerary.length > 0) {
        // Transform the new API format to component format
        const transformedItinerary = data.itinerary.map(day => ({
          day: day.day,
          title: day.title || `Day ${day.day}`,
          stops: (day.stops || []).map(stop => ({
            arrivalTime: stop.arrivalTime,
            name: stop.name,
            icon: stop.icon || 'mapPin',
            color: stop.color || 'text-purple-600',
            hours: stop.hours,
            visitDuration: stop.visitDuration,
            suggestedDuration: stop.suggestedDuration,
            travelToNext: stop.travelToNext,
            lunch: stop.lunch || false,
            endOfDay: stop.endOfDay || false,
            coords: stop.place_data?.coordinates 
              ? [stop.place_data.coordinates.latitude, stop.place_data.coordinates.longitude]
              : null,
            // Pass the full place_data for the ItineraryStop component
            place_data: stop.place_data || {}
          }))
        }));

        const formattedPlan = {
          title: data.title || `${formData.city.toUpperCase()} EXPLORER`,
          city: data.city,
          airport: data.airport,
          pacing: data.pacing,
          itinerary: transformedItinerary,
          highRankedPlaces: (data.highRankedPlaces || []).map(place => ({
            id: place.id,
            name: place.name,
            rating: place.rating || (place.rank_score ? place.rank_score * 5 : 4),
            reviewCount: place.reviewCount || 0,
            rank_score: place.rank_score,
            tags: place.tags || [],
            photo: place.photo,
            suggested_duration: place.suggested_duration,
            coordinates: place.coordinates,
            description: place.description,
            place_tip: place.place_tip,
            website: place.website,
            coords: place.coordinates 
              ? [place.coordinates.latitude, place.coordinates.longitude]
              : null
          })),
          specialPlaces: data.specialPlaces || { early_morning: [], late_night: [] }
        };

        setPlans([formattedPlan]);
        setGeneratingStep('Trip plan ready!');
      } else {
        throw new Error(data.error || 'No valid itinerary data received');
      }

    } catch (error) {
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
