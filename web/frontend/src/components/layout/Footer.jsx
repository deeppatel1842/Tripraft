import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import GlobalConfig from '../../config/globalConfig';
import '../css/Footer.css';

const Footer = () => {
  const [appName, setAppName] = useState(GlobalConfig.APP_NAME);

  useEffect(() => {
    setAppName(GlobalConfig.APP_NAME);
  }, []);

  const scrollToSection = (sectionId) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <footer id="contact" className="footer">
      <div className="container">
        <div className="footer-grid">
          <div className="footer-section">
            <h3 className="footer-title">
              <i className="fas fa-paper-plane"></i>
              {appName}
            </h3>
            <p className="footer-description">Your journey, simplified.</p>
          </div>
          
          <div className="footer-section">
            <h4 className="footer-heading">Product</h4>
            <ul className="footer-links">
              <li><a href="#features" onClick={(e) => { e.preventDefault(); scrollToSection('features'); }}>Features</a></li>
              <li><Link to="/pricing">Pricing</Link></li>
              <li><a href="#" onClick={(e) => e.preventDefault()}>Updates</a></li>
            </ul>
          </div>
          
          <div className="footer-section">
            <h4 className="footer-heading">Company</h4>
            <ul className="footer-links">
              <li><Link to="/about">About Us</Link></li>
              <li><a href="#" onClick={(e) => e.preventDefault()}>Careers</a></li>
              <li><Link to="/contact">Contact</Link></li>
            </ul>
          </div>
          
          <div className="footer-section">
            <h4 className="footer-heading">Follow Us</h4>
            <div className="social-links">
              <a href="#" className="social-link" aria-label="Facebook" onClick={(e) => e.preventDefault()}>
                <i className="fab fa-facebook fa-lg"></i>
              </a>
              <a href="#" className="social-link" aria-label="Twitter" onClick={(e) => e.preventDefault()}>
                <i className="fab fa-twitter fa-lg"></i>
              </a>
              <a href="#" className="social-link" aria-label="Instagram" onClick={(e) => e.preventDefault()}>
                <i className="fab fa-instagram fa-lg"></i>
              </a>
            </div>
          </div>
        </div>
        
        <div className="footer-bottom">
          <p>&copy; {new Date().getFullYear()} {appName}. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
