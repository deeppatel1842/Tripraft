/**
 * Group Planner Context
 * Manages group planner state globally.
 * Provides access to selected group, groups list across the app.
 *
 * NOTE: Currently not consumed by any component. GroupPlannerPage
 * manages its own local state. This context is reserved for when
 * cross-component state sharing is needed (e.g., sidebar badges,
 * notification counts, multi-page group planner flows).
 */

import React, { createContext, useContext, useState, useCallback } from 'react';

const GroupPlannerContext = createContext(null);

export const useGroupPlanner = () => {
  const context = useContext(GroupPlannerContext);
  if (!context) {
    throw new Error('useGroupPlanner must be used within GroupPlannerProvider');
  }
  return context;
};

export const GroupPlannerProvider = ({ children }) => {
  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [groups, setGroups] = useState([]);
  const [currentTrip, setCurrentTrip] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Select a group/trip
  const selectGroup = useCallback((groupId) => {
    setSelectedGroupId(groupId);
    const group = groups.find(g => g.id === groupId);
    if (group) {
      setCurrentTrip(group);
    }
  }, [groups]);

  // Update groups list
  const updateGroups = useCallback((newGroups) => {
    setGroups(newGroups);
  }, []);

  // Add a new group
  const addGroup = useCallback((group) => {
    setGroups(prev => [...prev, group]);
  }, []);

  // Remove a group
  const removeGroup = useCallback((groupId) => {
    setGroups(prev => prev.filter(g => g.id !== groupId));
    if (selectedGroupId === groupId) {
      setSelectedGroupId(null);
      setCurrentTrip(null);
    }
  }, [selectedGroupId]);

  // Update a specific group
  const updateGroup = useCallback((groupId, updates) => {
    setGroups(prev => prev.map(g => 
      g.id === groupId ? { ...g, ...updates } : g
    ));
    if (selectedGroupId === groupId && currentTrip) {
      setCurrentTrip(prev => ({ ...prev, ...updates }));
    }
  }, [selectedGroupId, currentTrip]);

  // Clear all state (for logout)
  const clearState = useCallback(() => {
    setSelectedGroupId(null);
    setGroups([]);
    setCurrentTrip(null);
  }, []);

  const value = {
    // State
    selectedGroupId,
    groups,
    currentTrip,
    isLoading,
    
    // Actions
    selectGroup,
    updateGroups,
    addGroup,
    removeGroup,
    updateGroup,
    clearState,
    setIsLoading,
    setCurrentTrip,
  };

  return (
    <GroupPlannerContext.Provider value={value}>
      {children}
    </GroupPlannerContext.Provider>
  );
};

export default GroupPlannerContext;
