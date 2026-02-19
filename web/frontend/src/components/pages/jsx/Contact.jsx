import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import Header from '../../layout/jsx/Header';
import Footer from '../../layout/jsx/Footer';
import '../css/Contact.css';

const Contact = () => {
  const { currentUser, signOut } = useAuth();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: ''
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleLogout = async () => {
    try {
      await signOut();
      navigate('/');
    } catch (error) {
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      // Simulate form submission - replace with actual backend call
      
      // Simulate delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setSubmitted(true);
      setFormData({
        name: '',
        email: '',
        subject: '',
        message: ''
      });
      
      // Reset success message after 5 seconds
      setTimeout(() => setSubmitted(false), 5000);
    } catch (error) {
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="contact-page">
      <Header 
        isAuthenticated={!!currentUser}
        user={currentUser}
        onLogout={handleLogout}
      />

      {/* Hero Section */}
      <section className="contact-hero">
        <div className="contact-hero-content">
          <h1>Get In Touch</h1>
          <p className="contact-subtitle">We'd love to hear from you</p>
          <p className="contact-description">
            Have questions, suggestions, or feedback? Let's connect and make Tripraft even better together.
          </p>
        </div>
      </section>

      {/* Contact Content */}
      <section className="contact-section">
        <div className="container">
          <div className="contact-grid">
            {/* Contact Form */}
            <div className="contact-form-wrapper reveal">
              <div className="form-container">
                <h2>Send us a Message</h2>
                
                {submitted && (
                  <div className="success-message">
                    <i className="fas fa-check-circle"></i>
                    <p>Thank you! We'll get back to you soon.</p>
                  </div>
                )}

                <form onSubmit={handleSubmit} className={submitted ? 'hidden' : ''}>
                  <div className="form-group">
                    <label htmlFor="name">Name</label>
                    <input
                      type="text"
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      placeholder="Your name"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      placeholder="your@email.com"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="subject">Subject</label>
                    <input
                      type="text"
                      id="subject"
                      name="subject"
                      value={formData.subject}
                      onChange={handleInputChange}
                      placeholder="How can we help?"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="message">Message</label>
                    <textarea
                      id="message"
                      name="message"
                      value={formData.message}
                      onChange={handleInputChange}
                      placeholder="Tell us more about your inquiry..."
                      rows="6"
                      required
                    ></textarea>
                  </div>

                  <button 
                    type="submit" 
                    className="submit-button"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <i className="fas fa-spinner fa-spin"></i>
                        Sending...
                      </>
                    ) : (
                      <>
                        <i className="fas fa-paper-plane"></i>
                        Send Message
                      </>
                    )}
                  </button>
                </form>
              </div>
            </div>

            {/* Contact Info */}
            <div className="contact-info-wrapper reveal">
              <div className="info-container">
                <h2>Contact Information</h2>

                <div className="info-card">
                  <div className="info-icon">
                    <i className="fas fa-map-marker-alt"></i>
                  </div>
                  <div className="info-content">
                    <h3>Address</h3>
                    <p>123 Travel Street</p>
                    <p>San Francisco, CA 94102</p>
                    <p>United States</p>
                  </div>
                </div>

                <div className="info-card">
                  <div className="info-icon">
                    <i className="fas fa-phone"></i>
                  </div>
                  <div className="info-content">
                    <h3>Phone</h3>
                    <p>+1 (555) 123-4567</p>
                    <p className="text-muted">Mon-Fri, 9AM-6PM PST</p>
                  </div>
                </div>

                <div className="info-card">
                  <div className="info-icon">
                    <i className="fas fa-envelope"></i>
                  </div>
                  <div className="info-content">
                    <h3>Email</h3>
                    <p>hello@tripraft.com</p>
                    <p className="text-muted">We'll respond within 24 hours</p>
                  </div>
                </div>

                <div className="info-card">
                  <div className="info-icon">
                    <i className="fas fa-clock"></i>
                  </div>
                  <div className="info-content">
                    <h3>Business Hours</h3>
                    <p>Monday - Friday: 9:00 AM - 6:00 PM</p>
                    <p>Saturday - Sunday: Closed</p>
                  </div>
                </div>

                {/* Social Links */}
                <div className="social-links">
                  <h3>Follow Us</h3>
                  <div className="social-buttons">
                    <a href="#" className="social-button" aria-label="Twitter">
                      <i className="fab fa-twitter"></i>
                    </a>
                    <a href="#" className="social-button" aria-label="Facebook">
                      <i className="fab fa-facebook"></i>
                    </a>
                    <a href="#" className="social-button" aria-label="Instagram">
                      <i className="fab fa-instagram"></i>
                    </a>
                    <a href="#" className="social-button" aria-label="LinkedIn">
                      <i className="fab fa-linkedin"></i>
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="faq-section reveal">
        <div className="container">
          <h2 className="section-title">Frequently Asked Questions</h2>
          
          <div className="faq-grid">
            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                How do I create an account?
              </h3>
              <p>
                Visit our signup page and enter your email address. You'll receive a verification link 
                to complete your account setup in just a few minutes.
              </p>
            </div>

            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                Is Tripraft free to use?
              </h3>
              <p>
                Yes! Tripraft offers a free plan with essential features. We also offer premium 
                plans with advanced features and priority support.
              </p>
            </div>

            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                How do I invite friends to my trip?
              </h3>
              <p>
                Once you create a trip, click "Invite Members" and enter your friends' email addresses. 
                They'll receive an invitation and can join your trip planning.
              </p>
            </div>

            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                Can I export my itinerary?
              </h3>
              <p>
                Absolutely! You can export your complete itinerary as a PDF or share it directly with 
                your travel companions via email.
              </p>
            </div>

            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                How secure is my data?
              </h3>
              <p>
                We use enterprise-grade encryption and comply with GDPR and other privacy standards. 
                Your data is always protected and never shared with third parties.
              </p>
            </div>

            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                What support options are available?
              </h3>
              <p>
                We offer email support for all users, live chat for premium members, and comprehensive 
                help documentation available 24/7.
              </p>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Contact;
