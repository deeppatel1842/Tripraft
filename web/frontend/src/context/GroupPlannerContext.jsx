/**
 * Group Planner React Context
 * Global state management for group planning application
 * 
 * Features:
 * - Centralized state management
 * - Cache-aware operations
 * - Professional error handling
 * - Automatic cache invalidation
 */

import React, { createContext, useState, useCallback, useEffect, useRef } from 'react';
import groupPlannerService from '../services/groupPlannerService';
import groupPlannerApi from '../services/groupPlannerApi';
import authService from '../firebase/authService';
import firestoreListenerService from '../services/firestoreListenerService';
import optimisticUpdateService from '../services/optimisticUpdateService';

/**
 * Create the Group Planner Context
 */
export const GroupPlannerContext = createContext();

/**
 * Group Planner Provider Component
 * Wraps the application to provide group planning state and operations
 */
export const GroupPlannerProvider = ({ children }) => {
  // =========================================================================
  // STATE
  // =========================================================================

  // Groups data
  const [groups, setGroups] = useState({});
  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [groupsLoading, setGroupsLoading] = useState(false);
  const [groupsError, setGroupsError] = useState(null);

  // Places data
  const [places, setPlaces] = useState({});
  const [placesLoading, setPlacesLoading] = useState(false);
  const [placesError, setPlacesError] = useState(null);

  // Polls data
  const [polls, setPolls] = useState({});
  const [pollsLoading, setPollsLoading] = useState(false);
  const [pollsError, setPollsError] = useState(null);

  // Members data
  const [members, setMembers] = useState({});
  const [membersLoading, setMembersLoading] = useState(false);
  const [membersError, setMembersError] = useState(null);

  // Invitations data
  const [invitations, setInvitations] = useState([]);
  const [invitationsLoading, setInvitationsLoading] = useState(false);
  const [invitationsError, setInvitationsError] = useState(null);

  // UI state
  const [ui, setUi] = useState({
    showCreateGroupModal: false,
    showInviteModal: false,
    showPollModal: false,
    selectedTab: 'plan',
  });

  // Real-time sync state (polling-based)
  const [isListenerActive, setIsListenerActive] = useState(false);
  
  // Authentication state
  const [currentUser, setCurrentUser] = useState(null);

  // =========================================================================
  // SELECTORS
  // =========================================================================

  const selectedGroup = selectedGroupId ? groups[selectedGroupId] : null;
  const selectedGroupPlaces = selectedGroupId ? places[selectedGroupId] || [] : [];
  const selectedGroupPolls = selectedGroupId ? polls[selectedGroupId] || [] : [];
  const selectedGroupMembers = selectedGroupId ? members[selectedGroupId] || [] : [];

  // 🔐 CRITICAL: Reset ALL state when user changes (prevents cross-user data leaks)
  useEffect(() => {
    const unsubscribe = authService.onAuthStateChanged((user) => {
      console.log('🔐 [CONTEXT] Auth state changed, user:', user?.email || 'none');
      
      if (!user) {
        // User logged out - clear ALL state
        console.log('🗑️ [CONTEXT] Clearing all state (user logged out)');
        setCurrentUser(null);
        setGroups({});
        setSelectedGroupId(null);
        setPlaces({});
        setPolls({});
        setMembers({});
        setInvitations([]);
        setGroupsError(null);
        setPlacesError(null);
        setPollsError(null);
        setMembersError(null);
        setInvitationsError(null);
        
        // Clear cache
        groupPlannerService.clearAllCache();
        
        // 🔑 CRITICAL: Clear stored token to prevent old user's token being used
        localStorage.removeItem('groupPlannerToken');
        console.log('🗑️ [CONTEXT] Cleared stored groupPlannerToken');
      } else {
        // User logged in - set current user and listeners will be triggered
        console.log('✅ [CONTEXT] User logged in, ready to load data:', user.email);
        setCurrentUser(user);
        localStorage.removeItem('groupPlannerToken');
        console.log('🗑️ [CONTEXT] Cleared old groupPlannerToken for new user');
      }
    });
    
    return () => unsubscribe();
  }, []);

  // Debug: Monitor groups state changes
  useEffect(() => {
    console.log('🔵 [CONTEXT] Groups state changed:', groups);
    console.log('🔵 [CONTEXT] Groups count:', Object.keys(groups).length);
  }, [groups]);

  // 🔥 PHASE 2: Real-time updates via polling (Firestore client access not configured)
  // =========================================================================
  // GROUP OPERATIONS
  // =========================================================================

  /**
   * Load all user groups from backend
   */
  const loadGroups = useCallback(async () => {
    console.log('🟡 [CONTEXT] loadGroups called');
    setGroupsLoading(true);
    setGroupsError(null);
    
    try {
      const response = await groupPlannerService.getGroups();
      console.log('🟡 [CONTEXT] getGroups response:', response);
      console.log('🟡 [CONTEXT] Response type:', typeof response, 'Is array:', Array.isArray(response));
      
      // Service returns array directly, not {success, data} object
      const groupsArray = Array.isArray(response) ? response : 
                         (response.data && Array.isArray(response.data)) ? response.data :
                         (response.groups && Array.isArray(response.groups)) ? response.groups : [];
      
      console.log('🟡 [CONTEXT] Processing groups array:', groupsArray);
      
      if (groupsArray.length > 0) {
        const groupsData = {};
        groupsArray.forEach(group => {
          const groupId = group.group_id || group.id;
          console.log('🟡 [CONTEXT] Adding group:', { groupId, name: group.name });
          groupsData[groupId] = group;
        });
        
        console.log('🟡 [CONTEXT] Final groupsData object:', groupsData);
        console.log('🟡 [CONTEXT] Calling setGroups with:', groupsData);
        setGroups(groupsData);
        console.log('✅ [CONTEXT] setGroups called, groups count:', Object.keys(groupsData).length);
      } else {
        console.log('ℹ️ [CONTEXT] No groups found, setting empty object');
        setGroups({});
      }
    } catch (error) {
      console.error('❌ [CONTEXT] Error loading groups:', error);
      setGroupsError(error.message);
    } finally {
      setGroupsLoading(false);
    }
  }, []);

  // 🔥 PHASE 2: Real-time updates via Firestore listeners
  // Listen to user's groups in real-time (triggered when user authenticates)
  useEffect(() => {
    if (!currentUser) {
      console.log('ℹ️ [REALTIME] No user logged in, skipping listeners');
      setIsListenerActive(false);
      return;
    }

    console.log('🎧 [REALTIME] Setting up Firestore listeners for user:', currentUser.uid);
    setIsListenerActive(true);

    // Listen to all user groups in real-time
    const unsubscribe = firestoreListenerService.listenToUserGroups(
      currentUser.uid,
      (groupsData) => {
        console.log('🔔 [REALTIME] Groups updated from Firestore');
        console.log('📊 [REALTIME] Groups count:', Object.keys(groupsData).length);
        setGroups(groupsData);
      },
      (error) => {
        console.error('❌ [REALTIME] Listener error:', error);
        setGroupsError(error.message);
      }
    );

    return () => {
      console.log('🔥 [REALTIME] Cleaning up Firestore listeners');
      unsubscribe();
      setIsListenerActive(false);
    };
  }, [currentUser]); // Re-run when currentUser changes

  // Listen to selected group for detailed updates (places, polls, checklist)
  useEffect(() => {
    if (!selectedGroupId) {
      console.log('ℹ️ [REALTIME] No group selected, no detail listener');
      return;
    }

    console.log('🎧 [REALTIME] Setting up detailed listener for group:', selectedGroupId);

    const unsubscribe = firestoreListenerService.listenToGroup(
      selectedGroupId,
      (groupData) => {
        console.log('🔔 [REALTIME] Selected group updated from Firestore');
        console.log('📦 [REALTIME] Group data keys:', Object.keys(groupData));
        console.log('👥 [REALTIME] member_details:', groupData.member_details);
        
        // CRITICAL: Preserve enriched member_details from API if Firestore data has incomplete member_details
        setGroups(prev => {
          const existingGroup = prev[selectedGroupId];
          
          // If existing group has enriched member_details with emails, keep them
          if (existingGroup?.member_details && groupData.member_details) {
            const existingHasEmails = existingGroup.member_details.some(m => m.email);
            const newHasEmails = groupData.member_details.some(m => m.email);
            
            if (existingHasEmails && !newHasEmails) {
              console.log('⚠️ [REALTIME] Preserving enriched member_details (Firestore data missing emails)');
              groupData.member_details = existingGroup.member_details;
            }
          }
          
          return {
            ...prev,
            [selectedGroupId]: groupData
          };
        });

        // Update extracted data (places, polls, etc.)
        if (groupData.places) {
          setPlaces(prev => ({ ...prev, [selectedGroupId]: groupData.places }));
        }
        if (groupData.polls) {
          setPolls(prev => ({ ...prev, [selectedGroupId]: groupData.polls }));
        }
        // FIX: Use member_details (not members) - that's what the group document stores
        if (groupData.member_details) {
          console.log('✅ [REALTIME] Updating members state with', groupData.member_details.length, 'members');
          setMembers(prev => ({ ...prev, [selectedGroupId]: groupData.member_details }));
        } else {
          console.warn('⚠️ [REALTIME] No member_details in group data!');
        }
      },
      (error) => {
        console.error('❌ [REALTIME] Selected group listener error:', error);
      }
    );

    return () => {
      console.log('🔥 [REALTIME] Stopping detailed group listener');
      unsubscribe();
    };
  }, [selectedGroupId]); // Re-run when selected group changes

  /**
   * Create new group via API
   */
  const createGroup = useCallback(async (name, description = '', options = {}) => {
    console.log('🟡 [CONTEXT] createGroup called with:', { name, description, options });
    
    try {
      const response = await groupPlannerService.createGroup({
        name,
        destination: description,
        description: options.description || ''
      });
      
      if (response.success && response.data) {
        const newGroup = response.data;
        const groupId = newGroup.group_id || newGroup.id;
        
        console.log('✅ [CONTEXT] Group created:', groupId);
        
        // Update state with new group
        setGroups(prev => ({
          ...prev,
          [groupId]: newGroup
        }));
        
        // Initialize empty arrays for the group
        setPlaces(prev => ({
          ...prev,
          [groupId]: newGroup.places || []
        }));
        
        setPolls(prev => ({
          ...prev,
          [groupId]: newGroup.polls || []
        }));
        
        setMembers(prev => ({
          ...prev,
          [groupId]: newGroup.member_details || []
        }));
        
        // Select the new group
        setSelectedGroupId(groupId);
        
        return newGroup;
      }
    } catch (error) {
      console.error('❌ [CONTEXT] Error creating group:', error);
      throw error;
    }
  }, []);

  /**
   * Select a group
   */
  const selectGroup = useCallback((groupId) => {
    setSelectedGroupId(groupId);
    setUi(prev => ({ ...prev, selectedTab: 'plan' }));
  }, []);

  /**
   * Delete group with optimistic update (Phase 3)
   */
  const deleteGroup = useCallback(async (groupId) => {
    try {
      console.log('⚡ [CONTEXT] Deleting group optimistically:', groupId);
      
      // CRITICAL: Stop Firestore listeners BEFORE deletion to prevent permission errors
      console.log('🧹 [CONTEXT] Stopping Firestore listeners for group:', groupId);
      firestoreListenerService.stopListeningToGroup(groupId);
      
      // ⚡ PHASE 3: Optimistic delete
      await optimisticUpdateService.execute({
        id: `delete-group-${groupId}`,
        
        // Step 1: Remove from UI immediately
        optimisticUpdate: () => {
          // Remove from state
          setGroups(prev => {
            const updated = { ...prev };
            delete updated[groupId];
            return updated;
          });

          // Clear other data for this group
          setPlaces(prev => {
            const updated = { ...prev };
            delete updated[groupId];
            return updated;
          });

          setPolls(prev => {
            const updated = { ...prev };
            delete updated[groupId];
            return updated;
          });

          setMembers(prev => {
            const updated = { ...prev };
            delete updated[groupId];
            return updated;
          });

          // Select another group if current was deleted
          if (selectedGroupId === groupId) {
            const remainingGroups = Object.keys(groups).filter(id => id !== groupId);
            setSelectedGroupId(remainingGroups.length > 0 ? remainingGroups[0] : null);
          }
        },
        
        // Step 2: Send to backend
        apiCall: async () => {
          await groupPlannerService.deleteGroup(groupId);
        },
        
        // Step 3: Success callback (already optimistically updated)
        onSuccess: () => {
          console.log('✅ [CONTEXT] Group deleted from backend:', groupId);
        },
        
        // Step 4: Error callback - restore group
        onError: (error) => {
          console.error('❌ [CONTEXT] Failed to delete group, restoring:', error);
          // Reload groups to restore state
          loadGroups();
        }
      });

      return true;
    } catch (error) {
      console.error('Error deleting group:', error);
      setGroupsError(error.message);
      throw error;
    }
  }, [groups, selectedGroupId, loadGroups]);

  // =========================================================================
  // PLACE OPERATIONS
  // =========================================================================

  /**
   * Load places for group
   */
  const loadPlaces = useCallback(async (groupId) => {
    try {
      setPlacesLoading(true);
      setPlacesError(null);

      const placesList = await groupPlannerService.getGroupPlaces(groupId);

      setPlaces(prev => ({
        ...prev,
        [groupId]: placesList,
      }));
    } catch (error) {
      console.error(`Error loading places for group ${groupId}:`, error);
      setPlacesError(error.message);
    } finally {
      setPlacesLoading(false);
    }
  }, []);

  /**
   * Add place to group
   */
  const addPlace = useCallback(async (groupId, placeName) => {
    try {
      // Check if place already exists
      const currentGroup = groups[groupId];
      const existingPlaces = currentGroup?.places || [];
      const duplicate = existingPlaces.find(p => 
        p.name.toLowerCase().trim() === placeName.toLowerCase().trim()
      );

      if (duplicate) {
        console.log('⚠️ [CONTEXT] Place already exists:', placeName);
        throw new Error('DUPLICATE_PLACE');
      }

      console.log('➕ [CONTEXT] Adding place:', placeName);
      
      // ⚡ PHASE 3: Optimistic update for instant UI feedback
      const tempId = `temp-${Date.now()}`;
      const tempPlace = {
        id: tempId,
        place_id: tempId,
        name: placeName,
        votes: [],
        vote_count: 0,
        _optimistic: true // Mark as optimistic
      };

      const result = await optimisticUpdateService.execute({
        id: `add-place-${groupId}-${tempId}`,
        
        // Step 1: Update UI immediately
        optimisticUpdate: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                places: [...(group.places || []), tempPlace]
              }
            };
          });
          return tempPlace;
        },
        
        // Step 2: Call API in background
        apiCall: async () => {
          return await groupPlannerService.addPlace(groupId, placeName);
        },
        
        // Step 3: Success - Real-time listener will update with real data
        onSuccess: (newPlace) => {
          console.log('✅ [CONTEXT] Place added successfully, real-time listener will update');
          // Firestore listener will replace optimistic data automatically
        },
        
        // Step 4: Error - Rollback optimistic update
        onError: (error) => {
          console.error('❌ [CONTEXT] Failed to add place, rolling back');
          setPlacesError(error.message);
        },
        
        // Rollback function
        rollback: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                places: (group.places || []).filter(p => p.id !== tempId)
              }
            };
          });
        }
      });

      return result;
    } catch (error) {
      console.error('❌ [CONTEXT] Error adding place:', error);
      setPlacesError(error.message);
      throw error;
    }
  }, [groups, loadGroups, isListenerActive]);

  /**
   * Delete place
   */
  const deletePlace = useCallback(async (groupId, placeId) => {
    try {
      console.log('🗑️ [CONTEXT] Deleting place:', placeId);

      // ⚡ PHASE 3: Optimistic delete with instant UI feedback
      let deletedPlace = null;
      
      await optimisticUpdateService.execute({
        id: `delete-place-${groupId}-${placeId}`,
        
        // Step 1: Remove from UI immediately
        optimisticUpdate: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            const places = group.places || [];
            deletedPlace = places.find(p => p.id === placeId || p.place_id === placeId);
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                places: places.filter(p => p.id !== placeId && p.place_id !== placeId)
              }
            };
          });
          return deletedPlace;
        },
        
        // Step 2: Call API in background
        apiCall: async () => {
          return await groupPlannerService.deletePlace(groupId, placeId);
        },
        
        // Step 3: Success - Listener will confirm deletion
        onSuccess: () => {
          console.log('✅ [CONTEXT] Place deleted successfully');
        },
        
        // Step 4: Error - Restore deleted place
        onError: (error) => {
          console.error('❌ [CONTEXT] Delete failed, restoring place');
          setPlacesError(error.message);
        },
        
        // Rollback function - restore place
        rollback: () => {
          if (deletedPlace) {
            setGroups(prev => {
              const group = prev[groupId];
              if (!group) return prev;
              
              return {
                ...prev,
                [groupId]: {
                  ...group,
                  places: [...(group.places || []), deletedPlace]
                }
              };
            });
          }
        }
      });
    } catch (error) {
      console.error('❌ [CONTEXT] Error deleting place:', error);
      setPlacesError(error.message);
      throw error;
    }
  }, [loadGroups, isListenerActive]);

  /**
   * Vote on place (toggle)
   */
  const voteOnPlace = useCallback(async (groupId, placeId) => {
    try {
      console.log('👍 [CONTEXT] Voting on place:', placeId);
      const currentAuthUser = authService.getCurrentUser();
      const userId = currentAuthUser?.uid;
      
      if (!userId) {
        throw new Error('User not authenticated');
      }

      // ⚡ PHASE 3: Optimistic vote toggle
      await optimisticUpdateService.execute({
        id: `vote-place-${groupId}-${placeId}`,
        
        // Step 1: Toggle vote immediately in UI
        optimisticUpdate: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            const places = group.places || [];
            const place = places.find(p => p.id === placeId || p.place_id === placeId);
            if (!place) return prev;
            
            // Toggle vote
            const votes = Array.isArray(place.votes) ? place.votes : [];
            const hasVoted = votes.includes(userId);
            const newVotes = hasVoted 
              ? votes.filter(id => id !== userId)
              : [...votes, userId];
            
            const updatedPlaces = places.map(p => 
              (p.id === placeId || p.place_id === placeId)
                ? { ...p, votes: newVotes, vote_count: newVotes.length }
                : p
            );
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                places: updatedPlaces
              }
            };
          });
          return true;
        },
        
        // Step 2: Call API in background
        apiCall: async () => {
          return await groupPlannerService.voteOnPlace(groupId, placeId);
        },
        
        // Step 3: Success - Listener will update with real data
        onSuccess: () => {
          console.log('✅ [CONTEXT] Vote registered successfully');
        },
        
        // Step 4: Error - Rollback vote
        onError: (error) => {
          console.error('❌ [CONTEXT] Vote failed, rolling back');
          setPlacesError(error.message);
        },
        
        // Rollback function - toggle back
        rollback: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            const places = group.places || [];
            const place = places.find(p => p.id === placeId || p.place_id === placeId);
            if (!place) return prev;
            
            // Toggle back
            const votes = Array.isArray(place.votes) ? place.votes : [];
            const hasVoted = votes.includes(userId);
            const newVotes = hasVoted 
              ? votes.filter(id => id !== userId)
              : [...votes, userId];
            
            const updatedPlaces = places.map(p => 
              (p.id === placeId || p.place_id === placeId)
                ? { ...p, votes: newVotes, vote_count: newVotes.length }
                : p
            );
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                places: updatedPlaces
              }
            };
          });
        }
      });
    } catch (error) {
      console.error('Error voting on place:', error);
      setPlacesError(error.message);
      throw error;
    }
  }, [loadGroups]);

  /**
   * Add place remark/notes
   */
  const addPlaceRemark = useCallback(async (groupId, placeId, remarks) => {
    try {
      console.log('📝 [CONTEXT] Updating place remark:', placeId);
      
      // ⚡ PHASE 3: Optimistic remark update
      await optimisticUpdateService.execute({
        id: `update-remark-${groupId}-${placeId}`,
        
        // Step 1: Update UI immediately
        optimisticUpdate: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            const places = group.places || [];
            const updatedPlaces = places.map(p =>
              (p.id === placeId || p.place_id === placeId)
                ? { ...p, remarks: remarks }
                : p
            );
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                places: updatedPlaces
              }
            };
          });
          return remarks;
        },
        
        // Step 2: Call API in background
        apiCall: async () => {
          return await groupPlannerService.addPlaceRemark(groupId, placeId, remarks);
        },
        
        // Step 3: Success
        onSuccess: () => {
          console.log('✅ [CONTEXT] Remark updated successfully');
        },
        
        // Step 4: Error - Rollback
        onError: (error) => {
          console.error('❌ [CONTEXT] Remark update failed');
          setPlacesError(error.message);
        },
        
        // Rollback function - restore old remark
        rollback: () => {
          // Firestore listener will restore correct value
          console.log('🔄 [CONTEXT] Rolling back remark update');
        }
      });
    } catch (error) {
      console.error('❌ [CONTEXT] Error updating place remark:', error);
      setPlacesError(error.message);
      throw error;
    }
  }, [loadGroups, isListenerActive]);

  /**
   * Update place details (date, duration, coordinates)
   */
  const updatePlaceDetails = useCallback(async (groupId, placeId, details) => {
    try {
      console.log('🔧 [CONTEXT] Updating place details:', placeId);
      
      // ⚡ PHASE 3: Optimistic details update
      await optimisticUpdateService.execute({
        id: `update-details-${groupId}-${placeId}`,
        
        // Step 1: Update UI immediately
        optimisticUpdate: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            const places = group.places || [];
            const updatedPlaces = places.map(p =>
              (p.id === placeId || p.place_id === placeId)
                ? { ...p, ...details }
                : p
            );
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                places: updatedPlaces
              }
            };
          });
          return details;
        },
        
        // Step 2: Call API in background
        apiCall: async () => {
          return await groupPlannerService.updatePlaceDetails(groupId, placeId, details);
        },
        
        // Step 3: Success
        onSuccess: () => {
          console.log('✅ [CONTEXT] Place details updated successfully');
        },
        
        // Step 4: Error - Rollback
        onError: (error) => {
          console.error('❌ [CONTEXT] Details update failed');
          setPlacesError(error.message);
        },
        
        // Rollback function
        rollback: () => {
          console.log('🔄 [CONTEXT] Rolling back details update');
        }
      });
    } catch (error) {
      console.error('❌ [CONTEXT] Error updating place details:', error);
      setPlacesError(error.message);
      throw error;
    }
  }, [loadGroups, isListenerActive]);

  /**
   * Update itinerary document
   */
  const updateItineraryDocument = useCallback(async (groupId, documentContent) => {
    try {
      await groupPlannerService.updateItineraryDocument(groupId, documentContent);
    } catch (error) {
      console.error('Error updating itinerary document:', error);
      throw error;
    }
  }, []);

  // =========================================================================
  // POLL OPERATIONS
  // =========================================================================

  /**
   * Load polls for group
   */
  const loadPolls = useCallback(async (groupId) => {
    try {
      setPollsLoading(true);
      setPollsError(null);

      const pollsList = await groupPlannerService.getGroupPolls(groupId);

      setPolls(prev => ({
        ...prev,
        [groupId]: pollsList,
      }));
    } catch (error) {
      console.error(`Error loading polls for group ${groupId}:`, error);
      setPollsError(error.message);
    } finally {
      setPollsLoading(false);
    }
  }, []);

  /**
   * Create poll in group
   */
  const createPoll = useCallback(async (groupId, pollData) => {
    try {
      // ⚡ PHASE 3: Optimistic poll creation
      const tempId = `temp-${Date.now()}`;
      const tempPoll = {
        id: tempId,
        poll_id: tempId,
        question: pollData.question,
        options: pollData.options.map((opt, idx) => ({
          option: opt,
          votes: [],
          vote_count: 0
        })),
        _optimistic: true
      };

      const result = await optimisticUpdateService.execute({
        id: `create-poll-${groupId}-${tempId}`,
        
        // Step 1: Add to UI immediately
        optimisticUpdate: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                polls: [...(group.polls || []), tempPoll]
              }
            };
          });
          return tempPoll;
        },
        
        // Step 2: Call API in background
        apiCall: async () => {
          return await groupPlannerService.createPoll(groupId, pollData);
        },
        
        // Step 3: Success - Listener will update
        onSuccess: (newPoll) => {
          console.log('✅ [CONTEXT] Poll created successfully');
        },
        
        // Step 4: Error - Rollback
        onError: (error) => {
          console.error('❌ [CONTEXT] Failed to create poll, rolling back');
          setPollsError(error.message);
        },
        
        // Rollback function
        rollback: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                polls: (group.polls || []).filter(p => p.id !== tempId)
              }
            };
          });
        }
      });

      return result;
    } catch (error) {
      console.error('Error creating poll:', error);
      setPollsError(error.message);
      throw error;
    }
  }, []);

  /**
   * Vote on poll
   */
  const voteOnPoll = useCallback(async (groupId, pollId, option) => {
    try {
      const currentAuthUser = authService.getCurrentUser();
      const userId = currentAuthUser?.uid;
      if (!userId) {
        throw new Error('User not authenticated');
      }

      // ⚡ PHASE 3: Optimistic poll vote
      await optimisticUpdateService.execute({
        id: `vote-poll-${groupId}-${pollId}-${option}`,
        
        // Step 1: Update vote in UI immediately
        optimisticUpdate: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            const polls = group.polls || [];
            const poll = polls.find(p => p.id === pollId || p.poll_id === pollId);
            if (!poll) return prev;
            
            // Toggle vote on option
            const updatedOptions = poll.options.map(opt => {
              const votes = Array.isArray(opt.votes) ? opt.votes : [];
              
              if (opt.option === option) {
                // Toggle vote on this option
                const hasVoted = votes.includes(userId);
                const newVotes = hasVoted
                  ? votes.filter(id => id !== userId)
                  : [...votes, userId];
                return { ...opt, votes: newVotes, vote_count: newVotes.length };
              } else {
                // Remove vote from other options (single choice)
                const newVotes = votes.filter(id => id !== userId);
                return { ...opt, votes: newVotes, vote_count: newVotes.length };
              }
            });
            
            const updatedPolls = polls.map(p =>
              (p.id === pollId || p.poll_id === pollId)
                ? { ...p, options: updatedOptions }
                : p
            );
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                polls: updatedPolls
              }
            };
          });
          return true;
        },
        
        // Step 2: Call API in background
        apiCall: async () => {
          return await groupPlannerService.voteOnPoll(groupId, pollId, option);
        },
        
        // Step 3: Success
        onSuccess: () => {
          console.log('✅ [CONTEXT] Poll vote registered successfully');
        },
        
        // Step 4: Error - Rollback
        onError: (error) => {
          console.error('❌ [CONTEXT] Poll vote failed, rolling back');
          setPollsError(error.message);
        },
        
        // Rollback function - toggle back
        rollback: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            const polls = group.polls || [];
            const poll = polls.find(p => p.id === pollId || p.poll_id === pollId);
            if (!poll) return prev;
            
            // Revert vote toggle
            const updatedOptions = poll.options.map(opt => {
              const votes = Array.isArray(opt.votes) ? opt.votes : [];
              
              if (opt.option === option) {
                const hasVoted = votes.includes(userId);
                const newVotes = hasVoted
                  ? votes.filter(id => id !== userId)
                  : [...votes, userId];
                return { ...opt, votes: newVotes, vote_count: newVotes.length };
              } else {
                const newVotes = votes.filter(id => id !== userId);
                return { ...opt, votes: newVotes, vote_count: newVotes.length };
              }
            });
            
            const updatedPolls = polls.map(p =>
              (p.id === pollId || p.poll_id === pollId)
                ? { ...p, options: updatedOptions }
                : p
            );
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                polls: updatedPolls
              }
            };
          });
        }
      });
    } catch (error) {
      console.error('Error voting on poll:', error);
      setPollsError(error.message);
      throw error;
    }
  }, [loadGroups]);

  /**
   * Delete poll
   */
  const deletePoll = useCallback(async (groupId, pollId) => {
    try {
      // ⚡ PHASE 3: Optimistic poll deletion
      let deletedPoll = null;
      
      await optimisticUpdateService.execute({
        id: `delete-poll-${groupId}-${pollId}`,
        
        // Step 1: Remove from UI immediately
        optimisticUpdate: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            const polls = group.polls || [];
            deletedPoll = polls.find(p => p.id === pollId || p.poll_id === pollId);
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                polls: polls.filter(p => p.id !== pollId && p.poll_id !== pollId)
              }
            };
          });
          return deletedPoll;
        },
        
        // Step 2: Call API in background
        apiCall: async () => {
          return await groupPlannerService.deletePoll(groupId, pollId);
        },
        
        // Step 3: Success
        onSuccess: () => {
          console.log('✅ [CONTEXT] Poll deleted successfully');
        },
        
        // Step 4: Error - Restore poll
        onError: (error) => {
          console.error('❌ [CONTEXT] Delete failed, restoring poll');
          setPollsError(error.message);
        },
        
        // Rollback function
        rollback: () => {
          if (deletedPoll) {
            setGroups(prev => {
              const group = prev[groupId];
              if (!group) return prev;
              
              return {
                ...prev,
                [groupId]: {
                  ...group,
                  polls: [...(group.polls || []), deletedPoll]
                }
              };
            });
          }
        }
      });
    } catch (error) {
      console.error('Error deleting poll:', error);
      setPollsError(error.message);
      throw error;
    }
  }, [loadGroups]);

  // =========================================================================
  // MEMBER OPERATIONS
  // =========================================================================

  /**
   * Load members for group
   */
  const loadMembers = useCallback(async (groupId) => {
    try {
      setMembersLoading(true);
      setMembersError(null);

      const membersList = await groupPlannerService.getGroupMembers(groupId);

      setMembers(prev => ({
        ...prev,
        [groupId]: membersList,
      }));
    } catch (error) {
      console.error(`Error loading members for group ${groupId}:`, error);
      setMembersError(error.message);
    } finally {
      setMembersLoading(false);
    }
  }, []);

  /**
   * Remove member from group
   */
  const removeMember = useCallback(async (groupId, userId) => {
    try {
      console.log('⚡ [CONTEXT] Removing member optimistically:', { groupId, userId });
      
      // ⚡ OPTIMISTIC UPDATE: Remove from UI immediately (like expense engine)
      setMembers(prev => ({
        ...prev,
        [groupId]: (prev[groupId] || []).filter(m => (m.id || m.user_id || m.uid) !== userId),
      }));
      
      console.log('✅ [CONTEXT] UI updated optimistically, calling backend...');

      // Then call backend
      await groupPlannerService.removeMember(groupId, userId);
      
      console.log('✅ [CONTEXT] Backend confirmed member removal');
      
      // ⚡ CRITICAL: Reload members to ensure consistency with backend
      await loadMembers(groupId);
    } catch (error) {
      console.error('❌ [CONTEXT] Error removing member:', error);
      setMembersError(error.message);
      // Reload members to revert optimistic update on error
      await loadMembers(groupId);
      throw error;
    }
  }, [loadMembers]);

  // =========================================================================
  // INVITATION OPERATIONS
  // =========================================================================

  /**
   * Load user invitations
   */
  const loadInvitations = useCallback(async () => {
    try {
      setInvitationsLoading(true);
      setInvitationsError(null);

      const invitationsList = await groupPlannerService.getUserInvitations();
      setInvitations(invitationsList);
    } catch (error) {
      console.error('Error loading invitations:', error);
      setInvitationsError(error.message);
    } finally {
      setInvitationsLoading(false);
    }
  }, []);

  /**
   * Create invitation with optimistic update (Phase 3)
   */
  const createInvitation = useCallback(async (groupId, email) => {
    try {
      console.log('⚡ [CONTEXT] Creating invitation optimistically:', { groupId, email });
      
      let result = null;
      
      // ⚡ PHASE 3: Optimistic invitation create
      await optimisticUpdateService.execute({
        id: `create-invitation-${groupId}-${email}`,
        
        // Step 1: Add temporary "sending..." invitation to UI
        optimisticUpdate: () => {
          const tempInvitation = {
            id: `temp-${Date.now()}`,
            group_id: groupId,
            invited_email: email,
            status: 'sending',
            created_at: new Date().toISOString(),
            _optimistic: true
          };
          setInvitations(prev => [...prev, tempInvitation]);
        },
        
        // Step 2: Send to backend
        apiCall: async () => {
          result = await groupPlannerService.createInvitation(groupId, email);
          return result;
        },
        
        // Step 3: Success - reload invitations
        onSuccess: async () => {
          console.log('✅ [CONTEXT] Invitation created, reloading...');
          await loadInvitations();
        },
        
        // Step 4: Error - remove temp invitation
        onError: (error) => {
          console.error('❌ [CONTEXT] Failed to create invitation:', error);
          setInvitations(prev => prev.filter(inv => !inv._optimistic));
        }
      });

      return result;
    } catch (error) {
      console.error('Error creating invitation:', error);
      setInvitationsError(error.message);
      throw error;
    }
  }, [loadInvitations]);

  /**
   * Accept invitation
   */
  const acceptInvitation = useCallback(async (invitationId) => {
    try {
      console.log('⚡ [CONTEXT] Accepting invitation optimistically:', invitationId);
      
      // ⚡ PHASE 3: Optimistic accept
      await optimisticUpdateService.execute({
        id: `accept-invitation-${invitationId}`,
        
        // Step 1: Update UI immediately - remove from pending list
        optimisticUpdate: () => {
          setInvitations(prev => prev.filter(inv => inv.id !== invitationId));
        },
        
        // Step 2: Send to backend
        apiCall: async () => {
          await groupPlannerService.acceptInvitation(invitationId);
        },
        
        // Step 3: Success - reload to get new group
        onSuccess: async () => {
          console.log('✅ [CONTEXT] Invitation accepted, reloading data...');
          // Clear cache to force fresh fetch (like expense engine pattern)
          groupPlannerService.clearAllCache();
          
          // Reload groups and invitations in parallel for speed
          await Promise.all([
            loadGroups(),
            loadInvitations()
          ]);
          
          console.log('✅ [CONTEXT] Groups and invitations reloaded after acceptance');
        },
        
        // Step 4: Error - restore invitation
        onError: (error) => {
          console.error('❌ [CONTEXT] Failed to accept invitation, restoring:', error);
          loadInvitations();
        }
      });
    } catch (error) {
      console.error('Error accepting invitation:', error);
      setInvitationsError(error.message);
      throw error;
    }
  }, [loadInvitations, loadGroups]);

  /**
   * Resend invitation
   */
  const resendInvitation = useCallback(async (invitationId) => {
    try {
      await groupPlannerService.resendInvitation(invitationId);

      // Refresh invitations
      await loadInvitations();
    } catch (error) {
      console.error('Error resending invitation:', error);
      setInvitationsError(error.message);
      throw error;
    }
  }, [loadInvitations]);

  /**
   * Reject invitation
   */
  const rejectInvitation = useCallback(async (invitationId) => {
    try {
      await groupPlannerService.rejectInvitation(invitationId);

      // Refresh invitations
      await loadInvitations();
    } catch (error) {
      console.error('Error rejecting invitation:', error);
      setInvitationsError(error.message);
      throw error;
    }
  }, [loadInvitations]);

  // =========================================================================
  // UI OPERATIONS
  // =========================================================================

  /**
   * Toggle modal visibility
   */
  const toggleModal = useCallback((modalName, show) => {
    setUi(prev => ({
      ...prev,
      [modalName]: show !== undefined ? show : !prev[modalName],
    }));
  }, []);

  /**
   * Set active tab
   */
  const setActiveTab = useCallback((tab) => {
    setUi(prev => ({
      ...prev,
      selectedTab: tab,
    }));
  }, []);

  // =========================================================================
  // CONTEXT VALUE
  // =========================================================================

  const value = {
    // State
    groups,
    selectedGroupId,
    selectedGroup,
    groupsLoading,
    groupsError,

    places,
    selectedGroupPlaces,
    placesLoading,
    placesError,

    polls,
    selectedGroupPolls,
    pollsLoading,
    pollsError,

    members,
    selectedGroupMembers,
    membersLoading,
    membersError,

    invitations,
    invitationsLoading,
    invitationsError,

    ui,
    
    // Real-time sync status (Phase 2)
    isListenerActive,

    // Group operations
    loadGroups,
    createGroup,
    selectGroup,
    deleteGroup,

    // Place operations
    loadPlaces,
    addPlace,
    deletePlace,
    voteOnPlace,
    addPlaceRemark,
    updatePlaceDetails,
    updateItineraryDocument,

    // Poll operations
    loadPolls,
    createPoll,
    voteOnPoll,
    deletePoll,

    // Member operations
    loadMembers,
    removeMember,

    // Invitation operations
    loadInvitations,
    createInvitation,
    acceptInvitation,
    resendInvitation,
    rejectInvitation,

    // Checklist operations
    addChecklistItem: useCallback(async (groupId, itemText) => {
      // ⚡ PHASE 3: Optimistic checklist item addition
      const tempId = `temp-${Date.now()}`;
      const tempItem = {
        id: tempId,
        text: itemText,
        completed: false,
        _optimistic: true
      };

      await optimisticUpdateService.execute({
        id: `add-checklist-${groupId}-${tempId}`,
        
        // Step 1: Add to UI immediately
        optimisticUpdate: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                checklist: [...(group.checklist || []), tempItem]
              }
            };
          });
          return tempItem;
        },
        
        // Step 2: Call API in background
        apiCall: async () => {
          return await groupPlannerService.addChecklistItem(groupId, itemText);
        },
        
        // Step 3: Success - Listener will update
        onSuccess: () => {
          console.log('✅ [CONTEXT] Checklist item added successfully');
        },
        
        // Step 4: Error - Rollback
        onError: (error) => {
          console.error('❌ [CONTEXT] Failed to add checklist item, rolling back');
        },
        
        // Rollback function
        rollback: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                checklist: (group.checklist || []).filter(item => item.id !== tempId)
              }
            };
          });
        }
      });
    }, [loadGroups, isListenerActive]),

    toggleChecklistItem: useCallback(async (groupId, itemId) => {
      // ⚡ PHASE 3: Optimistic checklist toggle (instant feedback)
      await optimisticUpdateService.execute({
        id: `toggle-checklist-${groupId}-${itemId}`,
        
        // Step 1: Toggle in UI immediately
        optimisticUpdate: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            const checklist = group.checklist || [];
            const updatedChecklist = checklist.map(item =>
              item.id === itemId
                ? { ...item, completed: !item.completed }
                : item
            );
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                checklist: updatedChecklist
              }
            };
          });
          return true;
        },
        
        // Step 2: Call API in background
        apiCall: async () => {
          return await groupPlannerService.toggleChecklistItem(groupId, itemId);
        },
        
        // Step 3: Success
        onSuccess: () => {
          console.log('✅ [CONTEXT] Checklist item toggled successfully');
        },
        
        // Step 4: Error - Toggle back
        onError: (error) => {
          console.error('❌ [CONTEXT] Toggle failed, reverting');
        },
        
        // Rollback function - toggle back
        rollback: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            const checklist = group.checklist || [];
            const updatedChecklist = checklist.map(item =>
              item.id === itemId
                ? { ...item, completed: !item.completed }
                : item
            );
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                checklist: updatedChecklist
              }
            };
          });
        }
      });
    }, [loadGroups, isListenerActive]),

    deleteChecklistItem: useCallback(async (groupId, itemId) => {
      // ⚡ PHASE 3: Optimistic checklist item deletion
      let deletedItem = null;
      
      await optimisticUpdateService.execute({
        id: `delete-checklist-${groupId}-${itemId}`,
        
        // Step 1: Remove from UI immediately
        optimisticUpdate: () => {
          setGroups(prev => {
            const group = prev[groupId];
            if (!group) return prev;
            
            const checklist = group.checklist || [];
            deletedItem = checklist.find(item => item.id === itemId);
            
            return {
              ...prev,
              [groupId]: {
                ...group,
                checklist: checklist.filter(item => item.id !== itemId)
              }
            };
          });
          return deletedItem;
        },
        
        // Step 2: Call API in background
        apiCall: async () => {
          return await groupPlannerService.deleteChecklistItem(groupId, itemId);
        },
        
        // Step 3: Success
        onSuccess: () => {
          console.log('✅ [CONTEXT] Checklist item deleted successfully');
        },
        
        // Step 4: Error - Restore item
        onError: (error) => {
          console.error('❌ [CONTEXT] Delete failed, restoring item');
        },
        
        // Rollback function
        rollback: () => {
          if (deletedItem) {
            setGroups(prev => {
              const group = prev[groupId];
              if (!group) return prev;
              
              return {
                ...prev,
                [groupId]: {
                  ...group,
                  checklist: [...(group.checklist || []), deletedItem]
                }
              };
            });
          }
        }
      });
    }, [loadGroups, isListenerActive]),

    // Budget operations
    updateBudget: useCallback(async (groupId, budget) => {
      await groupPlannerService.updateBudget(groupId, budget);
      // ✅ PHASE 2: Real-time listener will update automatically
      if (!isListenerActive) {
        await loadGroups();
      }
    }, [loadGroups, isListenerActive]),

    linkExpenseGroup: useCallback(async (groupId) => {
      const result = await groupPlannerApi.linkExpenseGroup(groupId);
      // ✅ PHASE 2: Real-time listener will update automatically
      if (!isListenerActive) {
        await loadGroups();
      }
      return result;
    }, [loadGroups, isListenerActive]),

    unlinkExpenseGroup: useCallback(async (groupId) => {
      const result = await groupPlannerApi.unlinkExpenseGroup(groupId);
      // ✅ PHASE 2: Real-time listener will update automatically
      if (!isListenerActive) {
        await loadGroups();
      }
      return result;
    }, [loadGroups, isListenerActive]),

    // UI operations
    toggleModal,
    setActiveTab,
  };

  return (
    <GroupPlannerContext.Provider value={value}>
      {children}
    </GroupPlannerContext.Provider>
  );
};

/**
 * Hook to use Group Planner Context
 */
export const useGroupPlanner = () => {
  const context = React.useContext(GroupPlannerContext);

  if (!context) {
    throw new Error('useGroupPlanner must be used within GroupPlannerProvider');
  }

  return context;
};

export default GroupPlannerContext;
