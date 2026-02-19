import React from 'react';

const ModeToggle = ({ mode, onToggle }) => {
  return (
    <div className="mode-toggle">
      <span>Personal</span>
      <label className="toggle-switch">
        <input 
          type="checkbox" 
          checked={mode === 'group'}
          onChange={onToggle}
        />
        <span className="slider"></span>
      </label>
      <span>Group</span>
    </div>
  );
};

export default ModeToggle;
