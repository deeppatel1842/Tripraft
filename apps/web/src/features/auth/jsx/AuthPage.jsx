// Purpose: Renders the Auth Page interface within apps\web\src\features\auth\jsx.
import React, { useState } from 'react';
import Login from './Login';
import Signup from './Signup';

const AuthPage = () => {
  const [showLogin, setShowLogin] = useState(true);

  return (
    <>
      {showLogin ? (
        <Login 
          onSwitchToSignup={() => setShowLogin(false)}
        />
      ) : (
        <Signup 
          onSwitchToLogin={() => setShowLogin(true)}
        />
      )}
    </>
  );
};

export default AuthPage;
