import React from 'react';
import './UserAvatar.css';

const UserAvatar = ({ user, size = 'medium', showName = false, onClick }) => {
  // Get initials from display name or email
  const getInitials = () => {
    if (user?.displayName) {
      const names = user.displayName.split(' ');
      if (names.length >= 2) {
        return `${names[0][0]}${names[1][0]}`.toUpperCase();
      }
      return user.displayName.substring(0, 2).toUpperCase();
    }
    
    if (user?.email) {
      return user.email.substring(0, 2).toUpperCase();
    }
    
    return 'U';
  };

  // Get display name
  const getDisplayName = () => {
    if (user?.displayName) {
      return user.displayName;
    }
    
    if (user?.email) {
      return user.email.split('@')[0];
    }
    
    return 'User';
  };

  // Get first name only
  const getFirstName = () => {
    if (user?.displayName) {
      const names = user.displayName.split(' ');
      return names[0];
    }
    
    if (user?.email) {
      return user.email.split('@')[0];
    }
    
    return 'User';
  };

  const sizeClass = `avatar-${size}`;
  const hasPhoto = user?.photoURL;

  return (
    <div className={`user-avatar-container ${onClick ? 'clickable' : ''}`} onClick={onClick}>
      <div className={`user-avatar ${sizeClass}`}>
        {hasPhoto ? (
          <img src={user.photoURL} alt={getDisplayName()} className="avatar-image" />
        ) : (
          <div className="avatar-initials">{getInitials()}</div>
        )}
      </div>
      {showName && (
        <span className="user-name-display">Hi, {getFirstName()}</span>
      )}
    </div>
  );
};

export default UserAvatar;
