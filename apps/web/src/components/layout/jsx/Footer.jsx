// Purpose: Renders the Footer interface within apps\web\src\components\layout\jsx.
import React from 'react';
import { Link } from 'react-router-dom';
import GlobalConfig from '../../../config/globalConfig';
import '../css/Footer.css';

const Footer = () => {
  const appName = GlobalConfig.APP_NAME;

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
              <li><Link to="/trip-planner">Trip Planner</Link></li>
              <li><Link to="/pricing">Pricing</Link></li>
            </ul>
          </div>
          
          <div className="footer-section">
            <h4 className="footer-heading">Company</h4>
            <ul className="footer-links">
              <li><Link to="/about">About Us</Link></li>
              <li><Link to="/contact">Contact</Link></li>
            </ul>
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
