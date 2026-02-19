import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import Header from '../../layout/jsx/Header';
import Footer from '../../layout/jsx/Footer';
import AnimatedBackground from '../../common/jsx/AnimatedBackground';
import '../css/HomePage.css';

const HomePage = () => {
  const [destination, setDestination] = useState('');
  const navigate = useNavigate();
  const { currentUser, signOut } = useAuth();

  useEffect(() => {
    // Scroll Animation Logic (Intersection Observer)
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1
    });

    const elementsToReveal = document.querySelectorAll('.reveal, .hp-reveal');
    elementsToReveal.forEach(el => observer.observe(el));

    return () => {
      elementsToReveal.forEach(el => observer.unobserve(el));
    };
  }, []);

  const handleGenerateTrip = (e) => {
    e.preventDefault();
    navigate('/trip-planner');
  };

  const handleLogout = async () => {
    try {
      await signOut();
      navigate('/');
    } catch (error) {
    }
  };

  return (
    <div className="home-page">
      <Header 
        isAuthenticated={!!currentUser} 
        user={currentUser} 
        onLogout={handleLogout} 
      />
      <main className="main-content">
        {/* Hero Section */}
        <section className="hero-section">
          <div className="hero-container">
            {/* Left Side - Content */}
            <div className="hero-content">
              <h1 className="hero-title hero-title-anim">
                Craft Your Next Adventure with AI
              </h1>
              <p className="hero-subtitle hero-subtitle-anim">
                Get a personalized, day-by-day itinerary in seconds, tailored to your style and budget.
              </p>
              <div className="hero-form-container hero-form-anim">
                <form onSubmit={handleGenerateTrip} className="hero-form">
                  <i className="fas fa-plane form-icon"></i>
                  <input
                    type="text"
                    placeholder="Where do you want to go? e.g., 'A week in Rome for a history lover'"
                    className="form-input"
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
                  />
                  <button type="submit" className="form-button">
                    Generate My Trip
                  </button>
                </form>
              </div>
            </div>

            {/* Right Side - Animated Background Loop */}
            <div className="hero-animation-wrapper">
              <AnimatedBackground />
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="hp-features-section">
          <div className="hp-container">
            <h2 className="hp-section-title hp-reveal">All the Tools You Need in One Place</h2>
            <p className="hp-section-subtitle hp-reveal">
              From intelligent planning to collaborative tools, we've got your entire trip covered.
            </p>
            <div className="hp-features-grid">
              <div className="hp-feature-card hp-reveal">
                <div className="hp-feature-icon">
                  <i className="fas fa-robot"></i>
                </div>
                <h3 className="hp-feature-title">AI Trip Planner</h3>
                <p className="hp-feature-description">
                  Get a personalized itinerary in seconds. Just tell us your preferences and let our AI do the magic.
                </p>
                <Link to="/trip-planner" className="hp-feature-link">
                  Generate Plan <i className="fas fa-arrow-right"></i>
                </Link>
              </div>
              
              <div className="hp-feature-card hp-reveal" style={{transitionDelay: '0.1s'}}>
                <div className="hp-feature-icon">
                  <i className="fas fa-map-marked-alt"></i>
                </div>
                <h3 className="hp-feature-title">Places Explorer</h3>
                <p className="hp-feature-description">
                  Discover top-rated destinations and attractions around the globe. Explore before you go!
                </p>
                <Link to="/places" className="hp-feature-link">
                  Explore Places <i className="fas fa-arrow-right"></i>
                </Link>
              </div>
              
              <div className="hp-feature-card hp-reveal" style={{transitionDelay: '0.2s'}}>
                <div className="hp-feature-icon">
                  <i className="fas fa-users"></i>
                </div>
                <h3 className="hp-feature-title">Group Trip Planner</h3>
                <p className="hp-feature-description">
                  Collaborate with friends, suggest ideas, and vote on destinations to plan the perfect group getaway.
                </p>
                <Link to="/group-planner" className="hp-feature-link">
                  Plan Together <i className="fas fa-arrow-right"></i>
                </Link>
              </div>
              
              <div className="hp-feature-card hp-reveal" style={{transitionDelay: '0.3s'}}>
                <div className="hp-feature-icon">
                  <i className="fas fa-wallet"></i>
                </div>
                <h3 className="hp-feature-title">Expense Management</h3>
                <p className="hp-feature-description">
                  Track spending, split bills, and manage your budget effortlessly. No more awkward money talks.
                </p>
                <Link to="/expenses" className="hp-feature-link">
                  Manage Expenses <i className="fas fa-arrow-right"></i>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* AI Planner Section */}
        <section id="ai-planner" className="ai-planner-section">
          <div className="container">
            <div className="ai-planner-content">
              <div className="ai-planner-text reveal">
                <span className="section-badge">MEET YOUR AI TRAVEL AGENT</span>
                <h2 className="section-title">Craft Your Dream Trip with AI</h2>
                <p className="section-description">
                  Tired of endless research? Describe your perfect vacation—interests, budget, and travel style—and our AI will generate a custom day-by-day itinerary complete with bookings and recommendations.
                </p>
                <div className="ai-prompt-box">
                  <textarea
                    rows="4"
                    className="ai-textarea"
                    placeholder="e.g., 'A 7-day romantic getaway in Italy for a couple who loves history, food, and wine. Budget is around $3000.'"
                  ></textarea>
                  <Link to="/trip-planner" className="ai-generate-btn">Generate My Plan</Link>
                </div>
              </div>
              <div className="ai-planner-image reveal">
                <img
                  src="https://placehold.co/600x450/e0e7ff/4c1d95?text=AI+Itinerary+Mockup"
                  alt="AI Itinerary Mockup"
                  className="mockup-image"
                />
              </div>
            </div>
          </div>
        </section>

        {/* Group Trip Section */}
        <section className="group-trip-section">
          <div className="container">
            <div className="group-trip-content">
              <div className="group-trip-image reveal">
                <img
                  src="https://placehold.co/600x500/c7d2fe/5b21b6?text=Group+Collaboration+UI"
                  alt="Group Collaboration UI"
                  className="mockup-image"
                />
              </div>
              <div className="group-trip-text reveal">
                <span className="section-badge">PLANNING TOGETHER, MADE EASY</span>
                <h2 className="section-title">The Ultimate Group Trip Experience</h2>
                <p className="section-description">
                  No more messy group chats. Our collaborative platform lets everyone contribute ideas, share links, and vote on the final plan. Democracy in travel planning is finally here!
                </p>
                <div className="voting-examples">
                  <div className="vote-item">
                    <div className="vote-info">
                      <p className="vote-title">Hotel Option: The Grand Budapest</p>
                      <p className="vote-author">Suggested by: Anna</p>
                    </div>
                    <div className="vote-actions">
                      <span className="vote-count">12 Votes</span>
                      <button className="vote-btn vote-btn-active">
                        <i className="fas fa-check"></i>
                      </button>
                    </div>
                  </div>
                  <div className="vote-item">
                    <div className="vote-info">
                      <p className="vote-title">Activity: Hiking in the Alps</p>
                      <p className="vote-author">Suggested by: Mark</p>
                    </div>
                    <div className="vote-actions">
                      <span className="vote-count">8 Votes</span>
                      <button className="vote-btn">
                        <i className="fas fa-check"></i>
                      </button>
                    </div>
                  </div>
                </div>
                <button className="cta-button">Start a Group Plan</button>
              </div>
            </div>
          </div>
        </section>

        {/* Expense Management Section */}
        <section className="expense-section">
          <div className="container text-center">
            <h2 className="section-title reveal">Travel More, Worry Less About Money</h2>
            <p className="section-subtitle reveal">
              Our integrated expense tracker helps you stay on budget. Add expenses on the go, see who paid for what, and settle up with a single click.
            </p>
            <div className="expense-box reveal">
              <div className="expense-stats">
                <div className="expense-stat">
                  <p className="stat-label">Trip Budget</p>
                  <p className="stat-value stat-budget">$2,500.00</p>
                </div>
                <div className="stat-divider"></div>
                <div className="expense-stat">
                  <p className="stat-label">Total Spent</p>
                  <p className="stat-value stat-spent">$1,845.50</p>
                </div>
                <div className="stat-divider"></div>
                <div className="expense-stat">
                  <p className="stat-label">You Owe Mark</p>
                  <p className="stat-value stat-owe">$52.75</p>
                </div>
              </div>
              <Link to="/expenses" className="expense-cta-btn">
                Manage Expenses
              </Link>
            </div>
          </div>
        </section>

        {/* Pricing Section */}
        <section id="pricing" className="pricing-section">
          <div className="container text-center">
            <h2 className="section-title reveal">Find the Perfect Plan for Your Journey</h2>
            <p className="section-subtitle reveal">
              Choose a plan that fits your travel style, from a simple weekend trip to a full-scale world tour.
            </p>
            <div className="pricing-grid">
              <div className="pricing-card reveal">
                <div className="pricing-content">
                  <h3 className="pricing-title">Free Plan</h3>
                  <p className="pricing-description">Perfect for a quick trip or weekend getaway.</p>
                  <div className="pricing-price">
                    <span className="price-amount">$0</span>
                    <span className="price-period">/month</span>
                  </div>
                  <ul className="pricing-features">
                    <li>
                      <i className="fas fa-check-circle"></i> Up to 3 Trips
                    </li>
                    <li>
                      <i className="fas fa-check-circle"></i> Basic AI Itinerary Planning
                    </li>
                    <li>
                      <i className="fas fa-check-circle"></i> Limited Collaboration Features
                    </li>
                    <li>
                      <i className="fas fa-check-circle"></i> Ad-Supported Experience
                    </li>
                  </ul>
                </div>
                <button className="pricing-btn pricing-btn-free">Get Started for Free</button>
              </div>

              <div className="pricing-card pricing-card-pro reveal" style={{transitionDelay: '0.1s'}}>
                <div className="pricing-content">
                  <h3 className="pricing-title">Plus</h3>
                  <p className="pricing-description">For regular travelers & friends   </p>
                  <div className="pricing-price">
                    <span className="price-amount">$4.99</span>
                    <span className="price-period">/month</span>
                  </div>
                  <ul className="pricing-features">
                    <li>
                      <i className="fas fa-check-circle"></i> Unlimited Expenses Per Day
                    </li>
                    <li>
                      <i className="fas fa-check-circle"></i> 100 AI Messages Per Day
                    </li>
                    <li>
                      <i className="fas fa-check-circle"></i> Unlimited Places Searches
                    </li>
                    <li>
                      <i className="fas fa-check-circle"></i> No Ads, Ever
                    </li>
                  </ul>
                </div>
                <button className="pricing-btn pricing-btn-pro">Get Started</button>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default HomePage;
