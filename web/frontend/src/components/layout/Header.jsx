import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import GlobalConfig from '../../config/globalConfig';
import UserAvatar from '../common/UserAvatar';
import '../css/Header.css';

const Header = ({ onLoginClick, onSignUpClick, isAuthenticated, user, onLogout }) => {
  const [appName, setAppName] = useState(GlobalConfig.APP_NAME);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

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

  const handleLoginClick = () => {
    closeMobileMenu();
    if (onLoginClick) {
      onLoginClick();
    } else {
      navigate('/login');
    }
  };

  const handleSignUpClick = () => {
    closeMobileMenu();
    if (onSignUpClick) {
      onSignUpClick();
    } else {
      navigate('/signup');
    }
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
            <Link to="/pricing" className="nav-link" onClick={closeMobileMenu}>Pricing</Link>
            <Link to="/about" className="nav-link" onClick={closeMobileMenu}>About</Link>
            <Link to="/contact" className="nav-link" onClick={closeMobileMenu}>Contact</Link>
           
            
            {/* Mobile Auth Buttons */}
            <div className="mobile-auth-buttons">
              {isAuthenticated ? (
                <div className="user-profile-mobile">
                  <UserAvatar user={user} size="medium" showName={true} />
                  <button className="btn-logout-mobile" onClick={() => { onLogout(); closeMobileMenu(); }}>
                    <i className="fas fa-sign-out-alt"></i> Logout
                  </button>
                </div>
              ) : (
                <>
                  <button className="btn-login-mobile" onClick={handleLoginClick}>
                    Log In
                  </button>
                  <button className="btn-signup" onClick={handleSignUpClick}>
                    Sign Up
                  </button>
                </>
              )}
            </div>
          </nav>
          
          <div className="auth-buttons desktop-auth">
            {isAuthenticated ? (
              <div className="user-profile-desktop">
                <UserAvatar user={user} size="medium" showName={true} />
                <button className="btn-logout" onClick={onLogout}>
                  <i className="fas fa-sign-out-alt"></i> Logout
                </button>
              </div>
            ) : (
              <>
                <button className="btn-login" onClick={handleLoginClick}>
                  Log In
                </button>
                <button className="btn-signup" onClick={handleSignUpClick}>
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
