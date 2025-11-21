import React, { useState } from 'react';
import Login from './Login';
import Signup from './Signup';

const AuthPage = () => {
  const [showLogin, setShowLogin] = useState(true);

  const handleLogin = (credentials) => {
    console.log('Login with:', credentials);
    // Add your login logic here
    // Example: call your backend API
    // fetch('/api/login', { method: 'POST', body: JSON.stringify(credentials) })
  };

  const handleSignup = (userData) => {
    console.log('Signup with:', userData);
    // Add your signup logic here
    // Example: call your backend API
    // fetch('/api/signup', { method: 'POST', body: JSON.stringify(userData) })
  };

  return (
    <>
      {showLogin ? (
        <Login 
          onSwitchToSignup={() => setShowLogin(false)}
          onLogin={handleLogin}
        />
      ) : (
        <Signup 
          onSwitchToLogin={() => setShowLogin(true)}
          onSignup={handleSignup}
        />
      )}
    </>
  );
};

export default AuthPage;
