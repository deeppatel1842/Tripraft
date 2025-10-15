import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import GlobalConfig from '../../config/globalConfig';
import '../css/Header.css';

const Header = ({ onLoginClick, onSignUpClick, isAuthenticated, user, onLogout }) => {
  const [appName, setAppName] = useState(GlobalConfig.APP_NAME);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    // Load app name from config (could be from backend API)
    setAppName(GlobalConfig.APP_NAME);
  }, []);

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  return (
    <header className="header">
      <div className="container">
        <div className="header-content">
          <Link to="/" className="logo" onClick={closeMobileMenu}>
            <i className="fas fa-paper-plane"></i>
            <span>{appName}</span>
          </Link>
          
          <button className="mobile-menu-toggle" onClick={toggleMobileMenu}>
            <i className={`fas ${isMobileMenuOpen ? 'fa-times' : 'fa-bars'}`}></i>
          </button>
          
          <nav className={`nav-menu ${isMobileMenuOpen ? 'mobile-open' : ''}`}>
            <Link to="/#features" className="nav-link" onClick={closeMobileMenu}>Features</Link>
            <Link to="/places" className="nav-link" onClick={closeMobileMenu}>Places</Link>
            <Link to="/trip-planner" className="nav-link" onClick={closeMobileMenu}>AI Planner</Link>
            <Link to="/group-trip" className="nav-link" onClick={closeMobileMenu}>Group Planner</Link>
            <Link to="/expenses" className="nav-link" onClick={closeMobileMenu}>Expense Management</Link>
            <Link to="/#pricing" className="nav-link" onClick={closeMobileMenu}>Pricing</Link>
            <Link to="/#contact" className="nav-link" onClick={closeMobileMenu}>Contact</Link>
            
            {/* Mobile Auth Buttons */}
            <div className="mobile-auth-buttons">
              {isAuthenticated ? (
                <>
                  <span className="user-name-mobile">Hi, {user?.name || user?.email}</span>
                  <button className="btn-logout" onClick={() => { onLogout(); closeMobileMenu(); }}>
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <button className="btn-login-mobile" onClick={() => { onLoginClick(); closeMobileMenu(); }}>
                    Log In
                  </button>
                  <button className="btn-signup" onClick={() => { onSignUpClick(); closeMobileMenu(); }}>
                    Sign Up
                  </button>
                </>
              )}
            </div>
          </nav>
          
          <div className="auth-buttons desktop-auth">
            {isAuthenticated ? (
              <>
                <span className="user-name">Hi, {user?.name || user?.email}</span>
                <button className="btn-logout" onClick={onLogout}>
                  Logout
                </button>
              </>
            ) : (
              <>
                <button className="btn-login" onClick={onLoginClick}>
                  Log In
                </button>
                <button className="btn-signup" onClick={onSignUpClick}>
                  Sign Up
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
