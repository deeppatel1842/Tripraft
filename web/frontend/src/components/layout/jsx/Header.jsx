import React, { useEffect, useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import GlobalConfig from '../../../config/globalConfig';
import UserAvatar from '../../common/jsx/UserAvatar';
import '../css/Header.css';

const Header = ({ onLoginClick, onSignUpClick, isAuthenticated, user, onLogout }) => {
  const [appName, setAppName] = useState(GlobalConfig.APP_NAME);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const menuRef = useRef(null);
  const toggleRef = useRef(null);

  useEffect(() => {
    // Load app name from config (could be from backend API)
    setAppName(GlobalConfig.APP_NAME);
  }, []);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        isMobileMenuOpen &&
        menuRef.current &&
        !menuRef.current.contains(event.target) &&
        toggleRef.current &&
        !toggleRef.current.contains(event.target)
      ) {
        setIsMobileMenuOpen(false);
      }
    };

    // Close menu on escape key
    const handleEscape = (event) => {
      if (event.key === 'Escape' && isMobileMenuOpen) {
        setIsMobileMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    // Prevent body scroll when menu is open
    if (isMobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isMobileMenuOpen]);

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
          
          <button 
            ref={toggleRef}
            className="mobile-menu-toggle" 
            onClick={toggleMobileMenu}
            aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={isMobileMenuOpen}
          >
            <i className={`fas ${isMobileMenuOpen ? 'fa-times' : 'fa-bars'}`}></i>
          </button>
          
          <nav ref={menuRef} className={`nav-menu ${isMobileMenuOpen ? 'mobile-open' : ''}`}>
            <Link to="/#features" className="nav-link" onClick={closeMobileMenu}>Features</Link>
            <Link to="/places" className="nav-link" onClick={closeMobileMenu}>Places</Link>
            <Link to="/trip-planner" className="nav-link" onClick={closeMobileMenu}>AI Planner</Link>
            <Link to="/group-planner" className="nav-link" onClick={closeMobileMenu}>Group Planner</Link>
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
