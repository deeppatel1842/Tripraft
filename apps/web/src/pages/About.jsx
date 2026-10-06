// Purpose: Renders the About interface within apps\web\src\pages.
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/layout/jsx/Header';
import Footer from '../components/layout/jsx/Footer';
import './styles/About.css';

const About = () => {
  const { currentUser, signOut } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Scroll Animation Logic
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

    const elementsToReveal = document.querySelectorAll('.reveal');
    elementsToReveal.forEach(el => observer.observe(el));

    return () => {
      observer.disconnect();
    };
  }, []);

  const handleLogout = async () => {
    try {
      await signOut();
      navigate('/');
    } catch (error) {
    }
  };

  const teamMembers = [
    {
      id: 1,
      name: 'Deep Patel',
      role: 'Founder & CEO',
      bio: 'Travel enthusiast with 5+ years in tech startups',
      icon: '👨‍💻'
    },
  ];

  return (
    <div className="about-page">
      <Header 
        isAuthenticated={!!currentUser}
        user={currentUser}
        onLogout={handleLogout}
      />

      {/* Hero Section */}
      <section className="about-hero reveal">
        <div className="about-hero-content">
          <h1>About Tripraft</h1>
          <p className="about-subtitle">Your journey, simplified</p>
          <p className="about-description">
            We're on a mission to make travel planning effortless, enjoyable, and unforgettable. 
            Whether you're planning a solo adventure or a group trip, Tripraft is here to help.
          </p>
        </div>
      </section>

      {/* Mission & Vision */}
      <section className="about-section reveal">
        <div className="about-container">
          <div className="mission-vision-grid">
            <div className="mission-card">
              <div className="card-icon">
               <i className="fa-solid fa-bullseye"></i>
              </div>
              <h2>Our Mission</h2>
              <p>
                To empower travelers with intelligent tools that transform trip planning 
                from a tedious chore into an exciting adventure. We believe every journey 
                should be memorable from start to finish.
              </p>
            </div>

            <div className="vision-card">
              <div className="card-icon">
                <i className="fas fa-eye"></i>
              </div>
              <h2>Our Vision</h2>
              <p>
                A world where travel planning is intuitive, social, and intelligent. 
                We envision a platform that brings friends together and creates unforgettable 
                shared experiences around the globe.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="about-section about-features-section reveal">
        <div className="about-container">
          <h2 className="about-section-title">Why Choose Tripraft?</h2>
          <div className="about-features-grid">
            <div className="about-feature-card reveal">
              <div className="about-feature-icon">
                <i className="fas fa-map"></i>
              </div>
              <h3>Smart Planning</h3>
              <p>AI-powered recommendations based on your preferences and budget</p>
            </div>

            <div className="about-feature-card reveal">
              <div className="about-feature-icon">
                <i className="fas fa-users"></i>
              </div>
              <h3>Group Coordination</h3>
              <p>Easy collaboration with friends and seamless expense splitting</p>
            </div>

            <div className="about-feature-card reveal">
              <div className="about-feature-icon">
                <i className="fas fa-chart-pie"></i>
              </div>
              <h3>Expense Management</h3>
              <p>Track and split expenses automatically among trip members</p>
            </div>

            <div className="about-feature-card reveal">
              <div className="about-feature-icon">
                <i className="fas fa-globe"></i>
              </div>
              <h3>Destination Explorer</h3>
              <p>Discover hidden gems and must-visit locations around the world</p>
            </div>

            <div className="about-feature-card reveal">
              <div className="about-feature-icon">
                <i className="fas fa-calendar-check"></i>
              </div>
              <h3>Itinerary Builder</h3>
              <p>Create detailed day-by-day plans with activities and reservations</p>
            </div>

            <div className="about-feature-card reveal">
              <div className="about-feature-icon">
                <i className="fas fa-lock"></i>
              </div>
              <h3>Secure & Private</h3>
              <p>Your travel data is encrypted and protected with enterprise security</p>
            </div>
          </div>
        </div>
      </section>

      {/* Team Section */}
      <section className="about-section about-team-section reveal">
        <div className="about-container">
          <h2 className="about-section-title">Meet Our Team</h2>
          <div className="about-team-grid">
            {teamMembers.map((member) => (
              <div 
                key={member.id}
                className="about-team-card reveal"
              >
                <div className="about-team-avatar">{member.icon}</div>
                <h3>{member.name}</h3>
                <p className="about-team-role">{member.role}</p>
                <p className="about-team-bio">{member.bio}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="about-section stats-section reveal">
        <div className="about-container">
          <div className="stats-grid">
            <div className="stat-card reveal">
              <h3>50K+</h3>
              <p>Active Travelers</p>
            </div>

            <div className="stat-card reveal">
              <h3>150+</h3>
              <p>Destinations</p>
            </div>

            <div className="stat-card reveal">
              <h3>$10M+</h3>
              <p>Expenses Managed</p>
            </div>

            <div className="stat-card reveal">
              <h3>4.8★</h3>
              <p>Average Rating</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="about-cta reveal">
        <div className="cta-content">
          <h2>Ready to Plan Your Next Adventure?</h2>
          <p>Join thousands of travelers who are already using Tripraft</p>
          <button className="cta-button" onClick={() => navigate('/')}>
            <i className="fas fa-arrow-right"></i> Start Planning
          </button>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default About;
