// Purpose: Renders the Contact interface within apps\web\src\pages.
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Header from '../components/layout/jsx/Header';
import Footer from '../components/layout/jsx/Footer';
import './styles/Contact.css';

export default function Contact() {
  const { currentUser, signOut } = useAuth();
  const navigate = useNavigate();
  const email = import.meta.env.VITE_SUPPORT_EMAIL || '';
  const contactAvailable = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  return <div className="contact-page">
    <Header isAuthenticated={!!currentUser} user={currentUser} onLogout={async () => { await signOut(); navigate('/'); }} />
    <main><section className="contact-hero"><div className="contact-hero-content"><h1>Get in touch</h1>
      <p className="contact-description">{contactAvailable ? 'Send us your questions or feedback by email.' : 'Support contact details will be available here when support opens.'}</p>
      {contactAvailable && <a className="submit-button" href={'mailto:' + email}>{email}</a>}
    </div></section>
    <section className="faq-section"><div className="container"><h2>Using TripRaft</h2>
      <div className="faq-grid"><article className="faq-card"><h3>Create an account</h3><p>Enter your name, email and password on the <Link to="/signup">signup page</Link>.</p></article>
      <article className="faq-card"><h3>Invite friends</h3><p>Open your group and use Invite Friend to invite members by email.</p><Link to="/group-planner">Open group planner</Link></article>
      <article className="faq-card"><h3>Beta access</h3><p>TripRaft is currently free during beta. Paid subscriptions are not available.</p><Link to="/pricing">View availability</Link></article></div>
    </div></section></main><Footer />
  </div>;
}
