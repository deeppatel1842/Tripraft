import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Info } from 'lucide-react';
import { useGroupPlanner } from '../../context/GroupPlannerContext';
import { useGroupPlannerAuth } from '../../hooks/useGroupPlannerAuth';
import groupPlannerApi from '../../services/groupPlannerApi';
import Header from '../layout/Header';
import Footer from '../layout/Footer';
import UserAvatar from '../common/UserAvatar';
import WelcomeScreen from './WelcomeScreen';
import SidebarComponent from './SidebarComponent';
import TabNavigation from './TabNavigation';
import PlanTabContent from './PlanTabContent';
import PollsTabContent from './PollsTabContent';
import MembersTabContent from './MembersTabContent';
import PendingTabContent from './PendingTabContent';
import ItineraryTabContent from './ItineraryTabContent';
import ChecklistTabContent from './ChecklistTabContent';
import BudgetOverviewCards from './BudgetOverviewCards';
import CreateGroupModal from './CreateGroupModal';
import InviteModal from './InviteModal';
import PollModal from './PollModal';
import './GroupPlannerDemo.css';

/**
 * GroupPlannerDemo - Main component for group trip planning
 * Phase 1: Verifies authentication with backend
 * Demo mode: No Firebase, no backend API calls for groups yet
 * All data stored locally in React state
 */
export default function GroupPlannerDemo() {
  const navigate = useNavigate();
  
  // Get real user from Firebase auth
  const { isAuthenticated, currentUser, getToken, loading: authLoading, logout } = useGroupPlannerAuth();
  
  // Phase 1: Auth verification state
  const [authVerified, setAuthVerified] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [verifyingAuth, setVerifyingAuth] = useState(true);
  
  const {
    groups,
    selectedGroupId,
    selectedGroup,
    places,
    polls,
    members,
    invitations,
    ui,
    groupsLoading,
    isListenerActive,
    loadGroups,
    loadInvitations,
    selectGroup,
    createGroup,
    deleteGroup,
    addPlace,
    deletePlace,
    voteOnPlace,
    addPlaceRemark,
    updatePlaceDetails,
    updateItineraryDocument,
    createPoll,
    voteOnPoll,
    deletePoll,
    createInvitation,
    acceptInvitation,
    removeMember,
    addChecklistItem,
    toggleChecklistItem,
    deleteChecklistItem,
    updateBudget,
    linkExpenseGroup,
    unlinkExpenseGroup,
    toggleModal,
    setActiveTab
  } = useGroupPlanner();

  const [currentTab, setCurrentTab] = useState('plan');
  const [editingDoc, setEditingDoc] = useState(false);
  const [docText, setDocText] = useState('');
  
  // Local modal states (UI-specific, not global)
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showPollModal, setShowPollModal] = useState(false);
  const [inviteError, setInviteError] = useState('');
  const [inviteSuccess, setInviteSuccess] = useState('');
  const [showExpenseTooltip, setShowExpenseTooltip] = useState(false);
  const [linkingExpense, setLinkingExpense] = useState(false);
  const [showUnlinkModal, setShowUnlinkModal] = useState(false);

  // Check if current user is group owner
  const isGroupOwner = selectedGroup?.created_by === currentUser?.uid;

  /**
   * Phase 1: Verify authentication with backend on mount
   * This tests:
   * - User is authenticated
   * - currentUser.uid is valid Firebase UID
   * - Auth token is present and valid
   * - Backend can access the token
   */
  useEffect(() => {
    const verifyPhase1Auth = async () => {
      setVerifyingAuth(true);
      const startTime = performance.now();
      
      console.log('\n════════════════════════════════════════════════');
      console.log('🔐 [Phase 1 AUTH] STARTING VERIFICATION');
      console.log('════════════════════════════════════════════════');
      console.log('⏰ Timestamp:', new Date().toISOString());
      
      try {
        if (!isAuthenticated) {
          console.warn('⚠️ [Phase 1] User not authenticated - skipping verification');
          setVerifyingAuth(false);
          return;
        }

        console.log('✅ [Phase 1] User authenticated');
        console.log('👤 Current User UID:', currentUser?.uid);
        console.log('📧 Email:', currentUser?.email);
        console.log('📛 Display Name:', currentUser?.displayName);

        // Get token with timing
        console.log('\n📍 Step 1: Getting authentication token...');
        const tokenStart = performance.now();
        const token = await getToken();
        const tokenTime = (performance.now() - tokenStart).toFixed(2);
        
        if (!token) {
          throw new Error('Failed to obtain authentication token');
        }
        console.log('✅ Token obtained');
        console.log(`   ⏱️  Duration: ${tokenTime}ms`);
        console.log(`   📏 Token length: ${token.length} chars`);
        console.log(`   🔍 First 50 chars: ${token.substring(0, 50)}...`);

        // Initialize API service
        console.log('\n📍 Step 2: Initializing API service...');
        groupPlannerApi.setCurrentUser(currentUser);
        groupPlannerApi.setAuthToken(token);
        console.log('✅ API service initialized');
        console.log(`   📡 Base URL: ${groupPlannerApi.baseUrl}`);

        // Verify with backend
        console.log('\n📍 Step 3: Sending verification request to backend...');
        const verifyStart = performance.now();
        const result = await groupPlannerApi.verifyAuth();
        const verifyTime = (performance.now() - verifyStart).toFixed(2);
        
        console.log(`✅ Backend response received`);
        console.log(`   ⏱️  Duration: ${verifyTime}ms`);
        console.log(`   📊 Response:`, result);

        if (result.success === false) {
          throw new Error(result.error || result.message || 'Verification failed');
        }

        console.log('\n✅ [Phase 1] AUTH VERIFICATION SUCCESSFUL');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('User Details from Backend:');
        console.log('  UID:', result.data?.user?.uid || 'N/A');
        console.log('  Email:', result.data?.user?.email || 'N/A');
        console.log('  Status:', result.data?.token?.status || 'N/A');
        console.log('Total Time:', `${(performance.now() - startTime).toFixed(2)}ms`);
        console.log('════════════════════════════════════════════════\n');
        
        setAuthVerified(true);
        setAuthError(null);
      } catch (error) {
        console.error('\n❌ [Phase 1] AUTH VERIFICATION FAILED');
        console.error('════════════════════════════════════════════════');
        console.error('Error Message:', error.message);
        console.error('Error Stack:', error.stack);
        console.error('Total Time:', `${(performance.now() - startTime).toFixed(2)}ms`);
        console.error('════════════════════════════════════════════════\n');
        
        setAuthError(error.message);
        setAuthVerified(false);
      } finally {
        setVerifyingAuth(false);
      }
    };

    if (!authLoading && isAuthenticated) {
      verifyPhase1Auth();
    }
  }, [isAuthenticated, authLoading, getToken, currentUser]);

  /**
   * Initialize API service with current user and load groups
   * Automatically cached after first load
   */
  useEffect(() => {
    if (isAuthenticated && currentUser) {
      // 🔑 CRITICAL: Set currentUser in API service for auth
      const initializeAndLoad = async () => {
        const groupPlannerApi = (await import('../../services/groupPlannerApi')).default;
        groupPlannerApi.setCurrentUser(currentUser);
        
        // Force fresh token fetch for the current user
        const freshToken = await currentUser.getIdToken(true);
        groupPlannerApi.setAuthToken(freshToken);
        console.log('✅ [DEMO] GroupPlannerApi initialized with user:', currentUser.email);
        console.log('🔑 [DEMO] Fresh token obtained for:', currentUser.email);
        
        // Now load data
        loadGroups();
        loadInvitations();
      };
      
      initializeAndLoad();
    }
  }, [isAuthenticated, currentUser, loadGroups, loadInvitations]);

  /**
   * Handle group creation
   * @param {Object} data - { name, destination }
   */
  const handleCreateGroup = async (data) => {
    try {
      console.log('🟣 [DEMO] handleCreateGroup called with:', data);
      const result = await createGroup(data.name, data.destination);
      console.log('🟣 [DEMO] Group created, result:', result);
      
      setShowCreateModal(false);
      console.log('🟣 [DEMO] Modal closed');
      console.log('🟣 [DEMO] Group created successfully - staying on planner view');
    } catch (error) {
      console.error('🔴 [DEMO] Failed to create group:', error);
      throw error;
    }
  };

  /**
   * Handle member invitation
   * @param {string} email - Member email
   */
  const handleInvite = async (email) => {
    if (!selectedGroupId) return;
    setInviteError('');
    setInviteSuccess('');
    
    try {
      await createInvitation(selectedGroupId, email);
      setInviteSuccess('Invitation sent successfully');
      setTimeout(() => {
        setShowInviteModal(false);
        setInviteSuccess('');
      }, 1000);
    } catch (error) {
      console.error('Failed to invite:', error);
      setInviteError(error.message || 'Failed to send invitation');
    }
  };

  /**
   * Handle place addition
   * @param {string} placeName - Name of place
   */
  const handleAddPlace = async (placeName) => {
    if (!selectedGroupId) return;
    try {
      await addPlace(selectedGroupId, placeName);
      console.log('✅ [DEMO] Place added successfully:', placeName);
    } catch (error) {
      console.error('❌ [DEMO] Failed to add place:', error);
      // Re-throw so PlanTabContent can handle it
      throw error;
    }
  };

  /**
   * Handle place vote
   * @param {string} placeId - Place ID
   */
  const handleVotePlace = async (placeId) => {
    if (!selectedGroupId) return;
    try {
      await voteOnPlace(selectedGroupId, placeId);
    } catch (error) {
      console.error('Failed to vote:', error);
    }
  };

  /**
   * Handle place deletion
   * @param {string} placeId - Place ID
   */
  const handleDeletePlace = async (placeId) => {
    if (!selectedGroupId) return;
    try {
      await deletePlace(selectedGroupId, placeId);
    } catch (error) {
      console.error('Failed to delete:', error);
    }
  };

  /**
   * Handle place remark update
   * @param {string} placeId - Place ID
   * @param {string} newRemark - New remark text
   */
  const handleUpdatePlaceRemark = async (placeId, newRemark) => {
    if (!selectedGroupId) return;
    try {
      await addPlaceRemark(selectedGroupId, placeId, newRemark);
    } catch (error) {
      console.error('Failed to update remark:', error);
    }
  };

  /**
   * Handle place details update (date, duration, notes)
   * @param {string} placeId - Place ID
   * @param {object} updates - { visit_date, suggested_duration, remarks }
   */
  const handleUpdatePlaceDetails = async (placeId, updates) => {
    if (!selectedGroupId) return;
    try {
      await updatePlaceDetails(selectedGroupId, placeId, updates);
    } catch (error) {
      console.error('Failed to update place details:', error);
    }
  };

  /**
   * Handle itinerary document update
   * @param {string} content - Document content
   */
  const handleUpdateItineraryDocument = async (content) => {
    if (!selectedGroupId) return;
    try {
      await updateItineraryDocument(selectedGroupId, content);
    } catch (error) {
      console.error('Failed to update itinerary document:', error);
    }
  };

  /**
   * Handle poll creation
   * @param {Object} data - { name, options }
   */
  const handleCreatePoll = async (data) => {
    if (!selectedGroupId) return;
    try {
      await createPoll(selectedGroupId, data);
      setShowPollModal(false);
    } catch (error) {
      console.error('Failed to create poll:', error);
      throw error;
    }
  };

  /**
   * Handle poll vote
   * @param {string} pollId - Poll ID
   * @param {string} option - Vote option
   */
  const handleVotePoll = async (pollId, option) => {
    if (!selectedGroupId) return;
    try {
      await voteOnPoll(selectedGroupId, pollId, option);
    } catch (error) {
      console.error('Failed to vote:', error);
    }
  };

  /**
   * Handle expense group linking
   * Creates expense group with same name and members
   */
  const handleLinkExpense = async () => {
    if (!selectedGroupId || linkingExpense) return;
    
    try {
      setLinkingExpense(true);
      console.log('💰 [DEMO] Linking to expense engine:', selectedGroupId);
      
      const result = await linkExpenseGroup(selectedGroupId);
      
      if (result.data?.expense_group_id) {
        console.log('✅ [DEMO] Expense group linked:', result.data.expense_group_id);
      }
    } catch (error) {
      console.error('❌ [DEMO] Failed to link expense group:', error);
    } finally {
      setLinkingExpense(false);
    }
  };

  /**
   * Handle expense group unlinking
   * Deletes expense group and removes link
   */
  const handleUnlinkExpense = async () => {
    if (!selectedGroupId || linkingExpense) return;
    setShowUnlinkModal(true);
  };

  /**
   * Confirm and execute unlink
   */
  const confirmUnlinkExpense = async () => {
    setShowUnlinkModal(false);
    
    try {
      setLinkingExpense(true);
      console.log('🔓 [DEMO] Unlinking expense group:', selectedGroupId);
      
      const result = await unlinkExpenseGroup(selectedGroupId);
      
      if (result.success) {
        console.log('✅ [DEMO] Expense group unlinked successfully');
        // Force immediate refresh to show Link button again
        await loadGroups();
      }
    } catch (error) {
      console.error('❌ [DEMO] Failed to unlink expense group:', error);
      alert('Failed to unlink expense group. Please try again.');
    } finally {
      setLinkingExpense(false);
    }
  };

  /**
   * Handle poll deletion
   * @param {string} pollId - Poll ID
   */
  const handleDeletePoll = async (pollId) => {
    if (!selectedGroupId) return;
    try {
      await deletePoll(selectedGroupId, pollId);
    } catch (error) {
      console.error('Failed to delete poll:', error);
    }
  };

  /**
   * Handle invitation acceptance
   * @param {string} invitationId - Invitation ID
   */
  const handleAcceptInvitation = async (invitationId) => {
    try {
      await acceptInvitation(invitationId);
      await loadGroups();
    } catch (error) {
      console.error('Failed to accept invitation:', error);
      throw error;
    }
  };

  /**
   * Toggle document editing mode
   */
  const toggleDocEdit = () => {
    if (!editingDoc && selectedGroup) {
      setDocText(selectedGroup.plan_doc || '');
    }
    setEditingDoc(!editingDoc);
  };

  /**
   * Save document changes (placeholder)
   */
  const saveDoc = async () => {
    if (!selectedGroupId) return;
    try {
      // Call service to update plan doc
      setEditingDoc(false);
    } catch (error) {
      console.error('Failed to save doc:', error);
    }
  };

  /**
   * Generate itinerary (placeholder)
   */
  const handleBuildItinerary = async () => {
    if (!selectedGroupId) return;
    try {
      // Call service to generate itinerary
    } catch (error) {
      console.error('Failed to build itinerary:', error);
    }
  };

  const hasGroups = isAuthenticated && Object.keys(groups).length > 0;
  console.log('🟣 [DEMO] Groups object:', groups);
  console.log('🟣 [DEMO] Has groups:', hasGroups);
  console.log('🟣 [DEMO] Groups loading:', groupsLoading);
  console.log('🟣 [DEMO] Selected Group:', selectedGroup);
  console.log('🟣 [DEMO] Expense Group ID:', selectedGroup?.expense_group_id);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Auto-select first group if user has groups and none is selected
  React.useEffect(() => {
    // Wait for groups to load, then check if we have any
    if (!groupsLoading && isAuthenticated) {
      const groupIds = Object.keys(groups);
      console.log('🟣 [DEMO] Auto-select check:', { groupIds, selectedGroupId, groupsLoading });
      
      if (groupIds.length > 0 && !selectedGroupId) {
        const firstGroupId = groupIds[0];
        console.log('🟣 [DEMO] Auto-selecting first group:', firstGroupId);
        selectGroup(firstGroupId);
      }
    }
  }, [groupsLoading, isAuthenticated, groups, selectedGroupId, selectGroup]);

  // Show loading spinner while groups are loading on initial mount
  if (groupsLoading && Object.keys(groups).length === 0) {
    return (
      <>
        <Header 
          isAuthenticated={isAuthenticated}
          user={currentUser}
          onLogout={isAuthenticated ? handleLogout : undefined}
        />
        <div style={{
          background: authVerified ? '#10b981' : (authError ? '#ef4444' : '#f59e0b'),
          color: 'white',
          padding: '12px 20px',
          fontSize: '14px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>
            {verifyingAuth ? '🔄 [Phase 1] Verifying authentication...' : 
             authVerified ? '✅ [Phase 1] Authentication verified' :
             authError ? `❌ [Phase 1] Auth error: ${authError}` :
             '⚠️ [Phase 1] Auth not verified'}
          </span>
          {currentUser && (
            <span style={{ opacity: 0.8 }}>UID: {currentUser.uid.substring(0, 12)}...</span>
          )}
        </div>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '80vh',
          flexDirection: 'column',
          gap: '20px'
        }}>
          <div className="spinner" style={{
            width: '50px',
            height: '50px',
            border: '5px solid #f3f3f3',
            borderTop: '5px solid #3498db',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }}></div>
          <p style={{ fontSize: '16px', color: '#666' }}>Loading your travel groups...</p>
        </div>
        <Footer />
      </>
    );
  }

  // Show welcome screen only if not loading and no groups exist
  console.log('🔍 [DEMO] Render decision:', { hasGroups, groupsLoading, groupCount: Object.keys(groups).length });
  
  if (!hasGroups && !groupsLoading) {
    console.log('📋 [DEMO] Showing WELCOME SCREEN');
    return (
      <>
        <Header 
          isAuthenticated={isAuthenticated}
          user={currentUser}
          onLogout={isAuthenticated ? handleLogout : undefined}
        />
        {/* Phase 1 Auth Status Banner */}
        <div style={{
          background: authVerified ? '#10b981' : (authError ? '#ef4444' : '#f59e0b'),
          color: 'white',
          padding: '12px 20px',
          fontSize: '14px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>
            {verifyingAuth ? '🔄 [Phase 1] Verifying authentication...' : 
             authVerified ? '✅ [Phase 1] Authentication verified' :
             authError ? `❌ [Phase 1] Auth error: ${authError}` :
             '⚠️ [Phase 1] Auth not verified'}
          </span>
          {currentUser && (
            <span style={{ opacity: 0.8 }}>UID: {currentUser.uid.substring(0, 12)}...</span>
          )}
        </div>
        <WelcomeScreen onGroupCreated={loadGroups} />
        <Footer />
      </>
    );
  }
  
  console.log('🎯 [DEMO] Showing MAIN GROUP PLANNER');

  return (
    <>
      <Header 
        isAuthenticated={isAuthenticated}
        user={currentUser}
        onLogout={handleLogout}
      />
      {/* Phase 1 Auth Status + Phase 2 Real-time Sync Banner */}
      <div style={{
        background: authVerified ? '#10b981' : (authError ? '#ef4444' : '#f59e0b'),
        color: 'white',
        padding: '12px 20px',
        fontSize: '14px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <span>
            {verifyingAuth ? '🔄 [Phase 1] Verifying authentication...' : 
             authVerified ? '✅ [Phase 1] Authentication verified' :
             authError ? `❌ [Phase 1] Auth error: ${authError}` :
             '⚠️ [Phase 1] Auth not verified'}
          </span>
          {selectedGroup && (
            <span style={{ 
              padding: '4px 12px', 
              background: isListenerActive ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)',
              borderRadius: '12px',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              {isListenerActive ? (
                <>
                  <span style={{ 
                    width: '8px', 
                    height: '8px', 
                    background: '#4ade80', 
                    borderRadius: '50%',
                    animation: 'pulse 2s infinite'
                  }}></span>
                  🔄 Auto-Sync Active
                </>
              ) : '📡 Sync Inactive'}
            </span>
          )}
        </div>
        {currentUser && (
          <span style={{ opacity: 0.8 }}>UID: {currentUser.uid.substring(0, 12)}...</span>
        )}
      </div>
      <div className="demo-wrapper">
        <div className="demo-app">
          {/* SIDEBAR */}
          <SidebarComponent
            groups={groups}
            selectedGroupId={selectedGroupId}
            onSelectGroup={selectGroup}
            onCreateGroup={() => setShowCreateModal(true)}
            onDeleteGroup={async (groupId) => {
              try {
                console.log('🗑️ [DEMO] Deleting group:', groupId);
                await deleteGroup(groupId);
                console.log('✅ [DEMO] Group deleted successfully');
              } catch (error) {
                console.error('❌ [DEMO] Failed to delete group:', error);
              }
            }}
            currentUserId={currentUser?.uid}
          />

          {/* MAIN CONTENT */}
          <div className="demo-content">
            {selectedGroup ? (
              <>
                {/* HEADER */}
                <header className="demo-top">
                  <div>
                    <div className="demo-group-title">{selectedGroup.name}</div>
                    <div className="demo-avatars" style={{ marginTop: '8px' }}>
                      {selectedGroup.member_details?.slice(0, 4).map((member) => {
                        const memberUser = {
                          displayName: member.display_name,
                          email: member.email,
                          photoURL: member.photoURL || null
                        };
                        return (
                          <div key={member.uid} style={{ display: 'inline-block' }}>
                            <UserAvatar user={memberUser} size="medium" />
                          </div>
                        );
                      })}
                      {selectedGroup.pending?.length > 0 && (
                        <div 
                          key="pending-badge"
                          className="demo-avatar demo-avatar-pending"
                          title="Pending invitations"
                        >
                          +{selectedGroup.pending.length}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="demo-bar">
                    <button className="demo-invite-btn" onClick={() => setShowInviteModal(true)}>
                      ✉ Invite Member
                    </button>
                    
                    {/* Show ONLY Link button OR Unlink button, not both */}
                    {!selectedGroup?.expense_group_id ? (
                      <>
                        <button 
                          className="demo-expense-link-btn" 
                          onClick={handleLinkExpense}
                          disabled={linkingExpense || !isGroupOwner || (selectedGroup?.members?.length < 2)}
                          style={{
                            opacity: (linkingExpense || !isGroupOwner || (selectedGroup?.members?.length < 2)) ? 0.6 : 1,
                            cursor: (linkingExpense || !isGroupOwner || (selectedGroup?.members?.length < 2)) ? 'not-allowed' : 'pointer',
                            position: 'relative',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}
                        >
                          {linkingExpense ? '⏳ Processing...' : '💰 Link to Expenses'}
                          <span
                            onMouseEnter={() => setShowExpenseTooltip(true)}
                            onMouseLeave={() => setShowExpenseTooltip(false)}
                            style={{
                              cursor: 'help',
                              display: 'inline-flex',
                              alignItems: 'center',
                              position: 'relative'
                            }}
                          >
                            <Info size={16} style={{ opacity: 0.8 }} />
                            {showExpenseTooltip && (
                              <div style={{
                                position: 'absolute',
                                top: 'calc(100% + 12px)',
                                right: '0',
                                padding: '16px',
                                background: '#1f2937',
                                color: '#f9fafb',
                                borderRadius: '12px',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.4)',
                                zIndex: 1000,
                                width: '380px',
                                fontSize: '13px',
                                lineHeight: '1.6',
                                border: '1px solid rgba(255,255,255,0.1)',
                                pointerEvents: 'none'
                              }}>
                                <div style={{ marginBottom: '10px', fontWeight: '500', color: '#fff' }}>
                                  Clicking this button instantly creates an expense group for all current members, seamlessly integrating everyone into the expense engine.
                                </div>
                                <div style={{ opacity: 0.9 }}>
                                  In the Expense tab, members can view, edit, and manage all individual expenses. The total trip cost and per-person cost will be calculated instantly and displayed on this screen.
                                </div>
                              </div>
                            )}
                          </span>
                        </button>
                        
                        {/* Show reason why button is disabled - inline next to button */}
                        {(!isGroupOwner || selectedGroup?.members?.length < 2) && (
                          <span style={{
                            fontSize: '12px',
                            color: '#9ca3af',
                            fontStyle: 'italic',
                            marginLeft: '12px'
                          }}>
                            {!isGroupOwner 
                              ? '⚠️ Only group owner can link expenses' 
                              : selectedGroup?.members?.length < 2 
                                ? '⚠️ Need 2+ members to link expenses' 
                                : ''}
                          </span>
                        )}
                      </>
                    ) : (
                      <button 
                        className="demo-expense-unlink-btn" 
                        onClick={handleUnlinkExpense}
                        disabled={linkingExpense || !isGroupOwner}
                        style={{
                          padding: '10px 18px',
                          background: !isGroupOwner ? '#9ca3af' : '#dc2626',
                          color: '#fff',
                          border: 'none',
                          borderRadius: '8px',
                          fontSize: '14px',
                          fontWeight: '500',
                          cursor: (linkingExpense || !isGroupOwner) ? 'not-allowed' : 'pointer',
                          opacity: (linkingExpense || !isGroupOwner) ? 0.6 : 1,
                          transition: 'all 0.2s ease',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                        onMouseEnter={(e) => { if (isGroupOwner && !linkingExpense) e.target.style.background = '#b91c1c'; }}
                        onMouseLeave={(e) => { if (isGroupOwner) e.target.style.background = '#dc2626'; }}
                      >
                        {linkingExpense ? '⏳ Processing...' : '🔓 Unlink Expense'}
                      </button>
                    )}
                  </div>
                </header>

                {/* BUDGET OVERVIEW CARDS - Always visible */}
                <BudgetOverviewCards
                  budget={selectedGroup?.budget || { transactions: [] }}
                  estimatedBudget={selectedGroup?.estimated_budget || 0}
                  onUpdateBudget={async (newBudget) => {
                    try {
                      await updateBudget(selectedGroupId, newBudget);
                      console.log('Budget updated successfully!');
                    } catch (error) {
                      console.error('Failed to update budget:', error);
                    }
                  }}
                />

                {/* TAB NAVIGATION */}
                <TabNavigation
                  activeTab={currentTab}
                  onTabChange={setCurrentTab}
                  tabs={['plan', 'itinerary', 'polls', 'checklist', 'members', 'pending']}
                  counts={{
                    plan: selectedGroup?.places?.length || 0,
                    itinerary: selectedGroup?.places?.length || 0,
                    polls: (polls[selectedGroupId]?.length || selectedGroup?.polls?.length || 0),
                    checklist: selectedGroup?.checklist?.length || 0,
                    members: selectedGroup?.member_details?.length || 0,
                    pending: invitations?.length || 0
                  }}
                />

                {/* TAB CONTENT */}
                <main className="demo-main">
                  {currentTab === 'plan' && (
                    <section>
                      <PlanTabContent
                        places={places[selectedGroupId] || selectedGroup?.places}
                        currentUserId={currentUser?.uid}
                        onAddPlace={handleAddPlace}
                        onVotePlace={handleVotePlace}
                        onDeletePlace={handleDeletePlace}
                        onUpdatePlaceRemark={handleUpdatePlaceRemark}
                      />
                    </section>
                  )}

                  {currentTab === 'itinerary' && (
                    <section>
                      <ItineraryTabContent
                        groupName={selectedGroup?.name || 'Trip Group'}
                        destination={selectedGroup?.destination || 'Unknown'}
                        places={places[selectedGroupId] || selectedGroup?.places || []}
                        currentUserId={currentUser?.uid}
                        onUpdatePlaceRemark={handleUpdatePlaceRemark}
                        onUpdatePlaceDetails={handleUpdatePlaceDetails}
                        onUpdateItineraryDocument={handleUpdateItineraryDocument}
                        onDeletePlace={handleDeletePlace}
                        savedDocument={selectedGroup?.itinerary_document || ''}
                      />
                    </section>
                  )}

                  {currentTab === 'polls' && (
                    <section>
                      <PollsTabContent
                        polls={polls[selectedGroupId] || selectedGroup?.polls}
                        currentUserId={currentUser?.uid}
                        members={members[selectedGroupId] || selectedGroup?.member_details || []}
                        onCreatePoll={() => setShowPollModal(true)}
                        onVotePoll={handleVotePoll}
                        onDeletePoll={handleDeletePoll}
                      />
                    </section>
                  )}

                  {currentTab === 'checklist' && (
                    <section>
                      <ChecklistTabContent
                        checklist={selectedGroup?.checklist || []}
                        currentUserId={currentUser?.uid}
                        onAddChecklistItem={async (itemText) => {
                          try {
                            await addChecklistItem(selectedGroupId, itemText);
                          } catch (error) {
                            console.error('Failed to add checklist item:', error);
                          }
                        }}
                        onToggleChecklistItem={async (itemId) => {
                          try {
                            await toggleChecklistItem(selectedGroupId, itemId);
                          } catch (error) {
                            console.error('Failed to toggle checklist item:', error);
                          }
                        }}
                        onDeleteChecklistItem={async (itemId) => {
                          try {
                            await deleteChecklistItem(selectedGroupId, itemId);
                          } catch (error) {
                            console.error('Failed to delete checklist item:', error);
                          }
                        }}
                      />
                    </section>
                  )}

                  {currentTab === 'members' && (
                    <section>
                      <MembersTabContent
                        members={members[selectedGroupId] || selectedGroup?.member_details || []}
                        currentUserId={currentUser?.uid}
                        onDeleteMember={(memberId) => {
                          if (selectedGroupId) {
                            removeMember(selectedGroupId, memberId);
                            console.log('🟣 [DEMO] Member removed:', memberId);
                          }
                        }}
                      />
                    </section>
                  )}

                  {currentTab === 'pending' && (
                    <section>
                      <PendingTabContent
                        pendingInvitations={invitations}
                        currentUserId={currentUser?.uid}
                        onAcceptInvitation={handleAcceptInvitation}
                      />
                    </section>
                  )}
                </main>
              </>
            ) : (
              <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>
                Select a group to get started
              </div>
            )}
          </div>
        </div>
      </div>

      {/* MODALS */}
      <CreateGroupModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreateGroup}
      />

      <InviteModal
        isOpen={showInviteModal}
        onClose={() => {
          setShowInviteModal(false);
          setInviteError('');
          setInviteSuccess('');
        }}
        onSubmit={handleInvite}
        error={inviteError}
        successMessage={inviteSuccess}
      />

      <PollModal
        isOpen={showPollModal}
        onClose={() => setShowPollModal(false)}
        onSubmit={handleCreatePoll}
      />

      {/* Unlink Confirmation Modal */}
      {showUnlinkModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999
        }}>
          <div style={{
            background: '#fff',
            borderRadius: '16px',
            padding: '32px',
            maxWidth: '480px',
            width: '90%',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)'
          }}>
            <div style={{
              fontSize: '24px',
              fontWeight: '600',
              marginBottom: '16px',
              color: '#111827'
            }}>
              🔓 Unlink Expense Group?
            </div>
            <div style={{
              fontSize: '15px',
              color: '#6b7280',
              lineHeight: '1.6',
              marginBottom: '24px'
            }}>
              Are you sure you want to unlink this expense group? All expenses will be permanently deleted. This action cannot be undone.
            </div>
            <div style={{
              display: 'flex',
              gap: '12px',
              justifyContent: 'flex-end'
            }}>
              <button
                onClick={() => setShowUnlinkModal(false)}
                style={{
                  padding: '10px 24px',
                  background: '#f3f4f6',
                  color: '#374151',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => e.target.style.background = '#e5e7eb'}
                onMouseLeave={(e) => e.target.style.background = '#f3f4f6'}
              >
                Cancel
              </button>
              <button
                onClick={confirmUnlinkExpense}
                style={{
                  padding: '10px 24px',
                  background: '#dc2626',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => e.target.style.background = '#b91c1c'}
                onMouseLeave={(e) => e.target.style.background = '#dc2626'}
              >
                Yes, Unlink
              </button>
            </div>
          </div>
        </div>
      )}

      <Footer />
    </>
  );
}
