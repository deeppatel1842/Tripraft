// Purpose: Renders the Pricing interface within apps\web\src\pages.
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/layout/jsx/Header';
import Footer from '../components/layout/jsx/Footer';
import './styles/Pricing.css';

export default function Pricing() {
  const { currentUser, signOut } = useAuth();
  const navigate = useNavigate();
  return <div className="pricing-page">
    <Header isAuthenticated={!!currentUser} user={currentUser} onLogout={async () => { await signOut(); navigate('/'); }} />
    <main>
      <section className="pricing-hero"><div className="container">
        <h1>Plan together with TripRaft</h1>
        <p>TripRaft is currently free during beta. Paid subscriptions are not available.</p>
      </div></section>
      <section className="pricing-section"><div className="container"><div className="pricing-grid">
        <article className="pricing-card"><h2>Free beta</h2><p>Explore the current travel planning tools.</p>
          <ul><li>Day-by-day itineraries and place search</li><li>Group planning, chat, polls and checklists</li><li>Expense tracking, settlements and PDF export</li></ul>
          <button className="plan-cta" onClick={() => navigate(currentUser ? '/group-planner' : '/signup')}>{currentUser ? 'Open group planner' : 'Get started'}</button>
        </article>
        <article className="pricing-card"><h2>Future plans</h2><p>Pricing and paid features will be announced when subscriptions are ready.</p><p>There is no checkout or free trial to activate.</p></article>
      </div></div></section>
    </main><Footer />
  </div>;
}
