import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import SidebarComponent from './SidebarComponent';
import TripPlannerHeader from './TripPlannerHeader';
import PlacesSidebar from './PlacesSidebar';
import MapSection from './MapSection';
import NotesSection from './NotesSection';
import RightSidebar from './RightSidebar';
import PendingModal from './PendingModal';
import CreateGroupModal from './CreateGroupModal';
import CreatePollModal from './CreatePollModal';
import CreateChecklistModal from './CreateChecklistModal';
import EditItineraryModal from './EditItineraryModal';
import EditChecklistModal from './EditChecklistModal';
import EditPollModal from './EditPollModal';
import MembersModal from './MembersModal';
import MembersPanel from './MembersPanel';
import Header from '../../layout/jsx/Header';
import Footer from '../../layout/jsx/Footer';
import groupPlannerApi from '../../../services/groupPlannerApi';
import GlobalConfig from '../../../config/globalConfig';
import { useAuth } from '../../../context/AuthContext';
import '../css/GroupPlannerPage.css';

export default function GroupPlannerPage({
  useExternalLayout = false,
}) {
  // Get current user from auth context and groupId from URL params
  const { currentUser, signOut } = useAuth();
  const { groupId: urlGroupId } = useParams();

  // Wrap content with site Header/Footer (unless using external layout)
  const PageShell = ({ children }) => {
    if (useExternalLayout) return children;
    return (
      <>
        <Header
          isAuthenticated={!!currentUser}
          user={currentUser}
          onLogout={signOut}
        />
        {children}
      </>
    );
  };

  // State management
  const [groups, setGroups] = useState({});
  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [places, setPlaces] = useState([]);
  const [polls, setPolls] = useState([]);
  const [checklist, setChecklist] = useState([]);
  const [itinerary, setItinerary] = useState([]);
  const [pendingInvitations, setPendingInvitations] = useState([]);
  const [placesFilter, setPlacesFilter] = useState('all'); // Filter for map markers
  
  // UI state
  const [isPendingModalOpen, setIsPendingModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isPollModalOpen, setIsPollModalOpen] = useState(false);
  const [isChecklistModalOpen, setIsChecklistModalOpen] = useState(false);
  const [isEditItineraryModalOpen, setIsEditItineraryModalOpen] = useState(false);
  const [isEditChecklistModalOpen, setIsEditChecklistModalOpen] = useState(false);
  const [isEditPollModalOpen, setIsEditPollModalOpen] = useState(false);
  const [isMembersModalOpen, setIsMembersModalOpen] = useState(false);
  const [isMembersPanelOpen, setIsMembersPanelOpen] = useState(false);
  const [groupMembers, setGroupMembers] = useState([]);
  const [editingItineraryItem, setEditingItineraryItem] = useState(null);
  const [editingChecklistItem, setEditingChecklistItem] = useState(null);
  const [editingPoll, setEditingPoll] = useState(null);
  const [showItineraryOnMap, setShowItineraryOnMap] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState(null);
  
  // Document content for notes
  const [documentContent, setDocumentContent] = useState('');
  const documentSaveTimeout = useRef(null);
  
  // Expense tracking state
  const [expenseSummary, setExpenseSummary] = useState({
    linked: false,
    totalSpent: 0,
    perPerson: 0,
    estimatedBudget: 0,
    memberCount: 0,
    expenseCount: 0
  });
  const [isLinkingExpense, setIsLinkingExpense] = useState(false);
  const [isSavingBudget, setIsSavingBudget] = useState(false);
  
  // Events state
  const [events, setEvents] = useState([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);

  // Fetch user groups on mount
  useEffect(() => {
    fetchUserGroups();
  }, []);

  // Auto-select group from URL params
  useEffect(() => {
    if (urlGroupId && !selectedGroupId) {
      setSelectedGroupId(Number(urlGroupId));
    }
  }, [urlGroupId]);

  // Fetch group details when selected group changes
  useEffect(() => {
    if (selectedGroupId) {
      fetchGroupDetails(selectedGroupId);
      fetchExpenseSummary(selectedGroupId);
      fetchGroupMembers(selectedGroupId);
    }
  }, [selectedGroupId]);
  
  // Fetch expense summary for linked group
  const fetchExpenseSummary = async (groupId) => {
    try {
      const response = await groupPlannerApi.getExpenseSummary(groupId);
      if (response.success && response.data) {
        // Use user's share from expense group balance
        const userShare = response.data.user_share || 0;
        
        setExpenseSummary({
          linked: response.data.linked || false,
          expenseGroupId: response.data.expense_group_id,
          totalSpent: response.data.total_spent || 0,
          userSpent: userShare, // Now using user_share from balance calculation
          perPerson: response.data.per_person || 0,
          estimatedBudget: response.data.estimated_budget || 0,
          memberCount: response.data.member_count || 0,
          expenseCount: response.data.expense_count || 0
        });
      }
    } catch {
      // Error handled silently
    }
  };
  
  // Fetch events for destination
  const fetchDestinationEvents = async (groupId) => {
    try {
      const group = groups[groupId];
      if (!group?.destination) {
        setEvents([]);
        return;
      }
      
      setIsLoadingEvents(true);
      const response = await groupPlannerApi.getDestinationEvents(group.destination, {
        limit: 20,
        startDate: group.start_date,
        endDate: group.end_date
      });
      
      if (response.success && response.data) {
        setEvents(response.data);
      }
    } catch (err) {
      setEvents([]);
    } finally {
      setIsLoadingEvents(false);
    }
  };
  
  // Fetch detailed group members with owner/can_remove info
  const fetchGroupMembers = async (groupId) => {
    try {
      const response = await groupPlannerApi.getGroupMembers(groupId);
      if (response.success && response.data?.members) {
        setGroupMembers(response.data.members);
      }
    } catch (err) {
      setGroupMembers([]);
    }
  };
  
  // Handle linking expense group
  const handleLinkExpenses = async () => {
    if (!selectedGroupId) return;
    
    try {
      setIsLinkingExpense(true);
      const response = await groupPlannerApi.linkExpenseGroup(selectedGroupId);
      
      if (response.success) {
        // Refresh expense summary
        await fetchExpenseSummary(selectedGroupId);
        alert('Successfully linked to expense tracking!');
      }
    } catch (err) {
      alert('Failed to link expense group: ' + err.message);
    } finally {
      setIsLinkingExpense(false);
    }
  };

  const fetchUserGroups = async () => {
    try {
      setIsLoading(true);
      const response = await groupPlannerApi.getUserGroups();
      
      if (response.success && response.data) {
        // Convert array to object keyed by group_id
        const groupsMap = {};
        response.data.forEach(group => {
          const id = group.id || group.group_id;
          groupsMap[id] = { ...group, id };
        });
        setGroups(groupsMap);
        
        // Auto-select first group if none selected
        if (!selectedGroupId && response.data.length > 0) {
          const firstGroup = response.data[0];
          setSelectedGroupId(firstGroup.id || firstGroup.group_id);
        }
      }
    } catch (err) {
      setError('Failed to load groups');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchGroupDetails = async (groupId, { skipPlaces = false } = {}) => {
    try {
      const response = await groupPlannerApi.getGroup(groupId);
      
      if (response.success && response.data) {
        const group = response.data;
        setSelectedGroup(group);
        setPolls(group.polls || []);
        setChecklist(group.checklist || []);
        setDocumentContent(group.itinerary_document || '');
        
        // Update group in groups map
        setGroups(prev => {
          const updated = { ...prev, [groupId]: { ...prev[groupId], ...group } };
          return updated;
        });
        
        // Reset itinerary map view when switching groups
        if (!skipPlaces) {
          setShowItineraryOnMap(false);
        }

        // Only fetch destination places/events on initial load or group switch
        if (!skipPlaces && group.destination) {
          fetchGroupPlacesForDestination(group.destination);
          fetchDestinationEventsForGroup(group);
        }
      }
      
      // Fetch pending invitations for this group
      try {
        const invitationsResponse = await groupPlannerApi.getGroupInvitations(groupId);
        if (invitationsResponse.success && invitationsResponse.data) {
          const pendingInvites = invitationsResponse.data.filter(inv => inv.status === 'pending');
          setPendingInvitations(pendingInvites);
        }
      } catch (err) {
        setPendingInvitations([]);
      }
      
      // Fetch group's saved itinerary places
      const placesResponse = await groupPlannerApi.getGroupPlaces(groupId);
      if (placesResponse.success && placesResponse.data) {
        const savedPlaces = placesResponse.data.map((p, idx) => {
          // Extract coordinates - backend returns [lat, lng] array
          let lat = null;
          let lng = null;
          if (p.coordinates && Array.isArray(p.coordinates)) {
            lat = p.coordinates[0];
            lng = p.coordinates[1];
          } else if (p.latitude && p.longitude) {
            lat = p.latitude;
            lng = p.longitude;
          }
          
          // Parse time from remarks if stored there
          let time = null;
          let notes = p.remarks || '';
          if (notes.startsWith('Time:')) {
            const timeMatch = notes.match(/^Time:\s*([^\n]+)/);
            if (timeMatch) {
              time = timeMatch[1].trim();
              notes = notes.replace(/^Time:\s*[^\n]+\n?/, '').trim();
            }
          }
          
          return {
            id: p.id,
            order: idx + 1,
            name: p.name || p.place_name,
            category: p.category === 'restaurant' ? 'Restaurant' : 'Sightseeing',
            duration: p.suggested_duration || '1 hr',
            time: time,
            date: p.visit_date || null,
            notes: notes,
            color: p.category === 'restaurant' ? 'orange' : 'indigo',
            lat: lat,
            lng: lng,
          };
        });
        setItinerary(savedPlaces);
      } else {
        setItinerary([]);
      }
    } catch {
      // Error handled silently
    }
  };

  const fetchGroupPlaces = async (groupId) => {
    try {
      const group = groups[groupId];
      if (group?.destination) {
        fetchGroupPlacesForDestination(group.destination);
      }
    } catch {
      // Error handled silently
    }
  };

  // Fetch destination places directly with destination string (avoids race condition)
  const fetchGroupPlacesForDestination = async (destination) => {
    try {
      const encodedDest = encodeURIComponent(destination);
      const response = await fetch(
        `${GlobalConfig.API_BASE_URL}/v2/group-planner/destinations/${encodedDest}/places?limit=50`,
        { credentials: 'include' }
      );
      
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.places) {
          const transformedPlaces = data.places.map(p => ({
            id: p.id,
            name: p.name || p.place_name,
            description: p.description || p.ai_summary || '',
            rating: p.rating || 4.5,
            image: p.image_url || p.photo_url || p.photos?.[0] || null,
            category: p.category === 'restaurant' ? 'restaurants' : 'places',
            lat: p.latitude || p.coordinates?.lat,
            lng: p.longitude || p.coordinates?.lng,
          }));
          setPlaces(transformedPlaces);
        }
      }
    } catch {
      // Error handled silently
    }
  };

  // Fetch destination events directly with group object (avoids race condition)
  const fetchDestinationEventsForGroup = async (group) => {
    if (!group?.destination) {
      setEvents([]);
      return;
    }
    try {
      setIsLoadingEvents(true);
      const response = await groupPlannerApi.getDestinationEvents(group.destination, {
        limit: 20,
        startDate: group.start_date,
        endDate: group.end_date
      });
      if (response.success && response.data) {
        setEvents(response.data);
      }
    } catch {
      setEvents([]);
    } finally {
      setIsLoadingEvents(false);
    }
  };

  // Create group handler
  const handleCreateGroup = async (groupData) => {
    try {
      setIsCreating(true);
      const response = await groupPlannerApi.createGroup(groupData);
      
      if (response.success && response.data) {
        const newGroup = response.data;
        const groupId = newGroup.id || newGroup.group_id;
        
        // Add to groups
        setGroups(prev => ({
          ...prev,
          [groupId]: { ...newGroup, id: groupId }
        }));
        
        // Select the new group
        setSelectedGroupId(groupId);
        setIsCreateModalOpen(false);
        
        // Send invitations if provided
        if (groupData.invite_emails?.length > 0) {
          for (const email of groupData.invite_emails) {
            try {
              await groupPlannerApi.createInvitation(groupId, email);
            } catch {
              // Invitation error handled silently
            }
          }
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsCreating(false);
    }
  };

  const handleSelectGroup = (groupId) => {
    setSelectedGroupId(groupId);
  };

  const handleDeleteGroup = async (groupId) => {
    if (!confirm('Are you sure you want to delete this group?')) return;
    
    try {
      await groupPlannerApi.deleteGroup(groupId);
      
      // Remove from state
      const newGroups = { ...groups };
      delete newGroups[groupId];
      setGroups(newGroups);
      
      // Select another group if available
      const remainingIds = Object.keys(newGroups);
      if (remainingIds.length > 0) {
        setSelectedGroupId(remainingIds[0]);
      } else {
        setSelectedGroupId(null);
        setSelectedGroup(null);
      }
    } catch {
      // Error handled silently
    }
  };

  // Handle member removal from group
  const handleMemberRemoval = async (_memberId, _removalData) => {
    try {
      if (selectedGroupId) {
        await fetchGroupDetails(selectedGroupId, { skipPlaces: true });
        await fetchExpenseSummary(selectedGroupId);
      }
    } catch {
      // Silently handle — UI already reflects state
    }
  };

  // Handle member leaving the group
  const handleLeaveGroup = (_groupId) => {
    setSelectedGroupId(null);
    setSelectedGroup(null);
    fetchUserGroups();
  };

  // Handle budget save
  const handleSaveBudget = async (amount, currency) => {
    if (!selectedGroupId) return;
    setIsSavingBudget(true);
    try {
      await groupPlannerApi.updateGroup(selectedGroupId, {
        estimated_budget: amount,
        currency,
      });
      setExpenseSummary((prev) => ({ ...prev, estimatedBudget: amount }));
      await fetchGroupDetails(selectedGroupId, { skipPlaces: true });
    } catch {
      throw new Error('Failed to save budget');
    } finally {
      setIsSavingBudget(false);
    }
  };

  // Add place to itinerary
  const handleAddToItinerary = useCallback(async (place) => {
    if (!selectedGroupId) return;
    
    try {
      const response = await groupPlannerApi.addPlace(selectedGroupId, {
        name: place.name,
        description: place.description,
        latitude: place.lat,
        longitude: place.lng,
        category: place.category === 'restaurants' ? 'restaurant' : 'attraction',
        rating: place.rating,
        photo_url: place.image,
      });
      
      if (response.success) {
        // Add to local itinerary for display with coordinates for map
        const newItem = {
          id: response.data?.id || Date.now(),
          order: itinerary.length + 1,
          name: place.name,
          category: place.category === 'restaurants' ? 'Restaurant' : 'Sightseeing',
          duration: '1 hr',
          color: place.category === 'restaurants' ? 'orange' : 'indigo',
          lat: place.lat,
          lng: place.lng,
        };
        setItinerary(prev => [...prev, newItem]);
      }
    } catch {
      // Error handled silently
    }
  }, [selectedGroupId, itinerary.length]);

  const handleDeleteItinerary = async (itemId) => {
    try {
      await groupPlannerApi.deletePlace(selectedGroupId, itemId);
      setItinerary(prev => prev.filter(item => item.id !== itemId));
    } catch {
      // Error handled silently
    }
  };

  const handleEditItinerary = (itemId) => {
    const item = itinerary.find(i => i.id === itemId);
    if (item) {
      setEditingItineraryItem(item);
      setIsEditItineraryModalOpen(true);
    }
  };

  const handleSaveItinerary = async (updatedItem) => {
    try {
      await groupPlannerApi.updatePlaceDetails(selectedGroupId, updatedItem.id, {
        date: updatedItem.date,
        time: updatedItem.time,
        duration: updatedItem.duration,
        notes: updatedItem.notes,
      });
      
      // Update local state
      setItinerary(prev => prev.map(item => 
        item.id === updatedItem.id 
          ? { ...item, ...updatedItem }
          : item
      ));
      setIsEditItineraryModalOpen(false);
      setEditingItineraryItem(null);
    } catch {
      // Error handled silently
    }
  };

  const handleShowItineraryMap = () => {
    setShowItineraryOnMap(prev => !prev);
  };

  // Notes auto-save
  const handleNotesChange = useCallback((content) => {
    setDocumentContent(content);
    
    // Debounce save
    if (documentSaveTimeout.current) {
      clearTimeout(documentSaveTimeout.current);
    }
    
    documentSaveTimeout.current = setTimeout(async () => {
      if (selectedGroupId) {
        try {
          await groupPlannerApi.updateItineraryDocument(selectedGroupId, content);
        } catch {
          // Error handled silently
        }
      }
    }, 1500);
  }, [selectedGroupId]);

  // Poll operations - using modal
  const handleOpenPollModal = () => {
    setIsPollModalOpen(true);
  };

  const handleCreatePoll = async (pollData) => {
    try {
      const response = await groupPlannerApi.createPoll(selectedGroupId, {
        name: pollData.name,
        options: pollData.options
      });
      
      if (response.success) {
        setPolls(prev => [...prev, response.data]);
        setIsPollModalOpen(false);
      }
    } catch {
      // Error handled silently
    }
  };

  const handleVotePoll = async (pollId, optionIndex) => {
    try {
      await groupPlannerApi.voteOnPoll(selectedGroupId, pollId, optionIndex);
      // Only refresh polls — do NOT refetch entire group (prevents map re-render)
      const response = await groupPlannerApi.getGroup(selectedGroupId);
      if (response.success && response.data) {
        setPolls(response.data.polls || []);
      }
    } catch {
      // Error handled silently
    }
  };

  const handleDeletePoll = async (pollId) => {
    try {
      await groupPlannerApi.deletePoll(selectedGroupId, pollId);
      setPolls(prev => prev.filter(p => p.id !== pollId));
    } catch {
      // Error handled silently
    }
  };

  // Checklist operations - using modal
  const handleOpenChecklistModal = () => {
    setIsChecklistModalOpen(true);
  };

  const handleAddChecklistItem = async (text) => {
    try {
      const response = await groupPlannerApi.addChecklistItem(selectedGroupId, text);
      if (response.success) {
        setChecklist(prev => [...prev, response.data]);
        setIsChecklistModalOpen(false);
      }
    } catch {
      // Error handled silently
    }
  };

  const handleToggleChecklistItem = async (itemId) => {
    try {
      await groupPlannerApi.toggleChecklistItem(selectedGroupId, itemId);
      setChecklist(prev => prev.map(item => 
        item.id === itemId ? { ...item, completed: !item.completed } : item
      ));
    } catch {
      // Error handled silently
    }
  };

  const handleDeleteChecklistItem = async (itemId) => {
    try {
      await groupPlannerApi.deleteChecklistItem(selectedGroupId, itemId);
      setChecklist(prev => prev.filter(item => item.id !== itemId));
    } catch {
      // Error handled silently
    }
  };

  const handleEditChecklistItem = (itemId) => {
    const item = checklist.find(i => i.id === itemId);
    if (item) {
      setEditingChecklistItem({
        id: item.id,
        text: item.item || item.text,
        priority: item.priority,
        due_date: item.due_date,
      });
      setIsEditChecklistModalOpen(true);
    }
  };

  const handleSaveChecklistItem = async (updatedItem) => {
    try {
      const response = await groupPlannerApi.updateChecklistItem(selectedGroupId, updatedItem.id, {
        text: updatedItem.text,
        priority: updatedItem.priority,
        due_date: updatedItem.due_date,
      });
      
      // Update local state with the exact field names from backend
      setChecklist(prev => prev.map(i => 
        i.id === updatedItem.id 
          ? { 
              ...i, 
              item: updatedItem.text, 
              text: updatedItem.text, 
              priority: updatedItem.priority, 
              due_date: updatedItem.due_date 
            } 
          : i
      ));
      
      setIsEditChecklistModalOpen(false);
      setEditingChecklistItem(null);
    } catch (err) {
      alert('Failed to save checklist item. Please try again.');
    }
  };

  const handleEditPoll = (pollId) => {
    const poll = polls.find(p => p.id === pollId);
    if (poll) {
      setEditingPoll(poll);
      setIsEditPollModalOpen(true);
    }
  };

  const handleSavePoll = async (updatedPoll) => {
    // Note: Poll editing requires delete + create since options can't be modified
    // This is a UX choice - show what they're editing but create new on save
    try {
      if (updatedPoll.id) {
        // Delete old poll
        await groupPlannerApi.deletePoll(selectedGroupId, updatedPoll.id);
        setPolls(prev => prev.filter(p => p.id !== updatedPoll.id));
      }
      // Create new poll with updated data
      const response = await groupPlannerApi.createPoll(selectedGroupId, {
        name: updatedPoll.name,
        options: updatedPoll.options
      });
      if (response.success) {
        setPolls(prev => [...prev, response.data]);
      }
      setIsEditPollModalOpen(false);
      setEditingPoll(null);
    } catch {
      // Error handled silently
    }
  };

  // Invitation state
  const [showInviteCard, setShowInviteCard] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteStatus, setInviteStatus] = useState(''); // 'sending', 'success', 'error'
  const [inviteMessage, setInviteMessage] = useState('');

  // Invitation handlers
  const handleInvite = () => {
    setShowInviteCard(true);
    setInviteEmail('');
    setInviteStatus('');
    setInviteMessage('');
  };

  const handleSendInvitation = async () => {
    // Parse comma-separated emails
    const emails = inviteEmail
      .split(',')
      .map(e => e.trim())
      .filter(e => e.length > 0);

    if (emails.length === 0) {
      setInviteStatus('error');
      setInviteMessage('Please enter at least one email address.');
      return;
    }

    // Validate all emails
    const invalidEmails = emails.filter(e => !e.includes('@'));
    if (invalidEmails.length > 0) {
      setInviteStatus('error');
      setInviteMessage(`Invalid: ${invalidEmails.join(', ')}`);
      return;
    }

    try {
      setInviteStatus('sending');
      setInviteMessage(`Sending ${emails.length} invitation${emails.length > 1 ? 's' : ''}...`);

      let successCount = 0;
      let failCount = 0;

      for (const email of emails) {
        try {
          await groupPlannerApi.createInvitation(selectedGroupId, email);
          successCount++;
        } catch {
          failCount++;
        }
      }

      if (failCount === 0) {
        setInviteStatus('success');
        setInviteMessage(`${successCount} invitation${successCount > 1 ? 's' : ''} sent!`);
      } else {
        setInviteStatus(successCount > 0 ? 'success' : 'error');
        setInviteMessage(`${successCount} sent, ${failCount} failed.`);
      }

      setInviteEmail('');
      // Auto-close after result
      setTimeout(() => {
        setShowInviteCard(false);
        setInviteStatus('');
      }, 2500);
    } catch (err) {
      setInviteStatus('error');
      setInviteMessage(err.message || 'Failed to send invitations.');
    }
  };

  const handleCloseInviteCard = () => {
    setShowInviteCard(false);
    setInviteStatus('');
    setInviteMessage('');
    setInviteEmail('');
  };

  const handleAcceptPending = async (_invitationId) => {
    // Pending request handling not yet implemented
  };

  const handleRejectPending = async (_invitationId) => {
    // Pending request rejection not yet implemented
  };

  // Build trip info for header - memoized to prevent unnecessary re-renders
  const trip = useMemo(() => {
    if (!selectedGroup) {
      return { name: 'Select a Group', location: '', center: [0, 0], startDate: '', endDate: '', duration: '', emoji: '' };
    }
    
    const startDate = selectedGroup.start_date 
      ? new Date(selectedGroup.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      : '';
    const endDate = selectedGroup.end_date
      ? new Date(selectedGroup.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      : '';
    
    let duration = '';
    if (selectedGroup.start_date && selectedGroup.end_date) {
      const days = Math.ceil((new Date(selectedGroup.end_date) - new Date(selectedGroup.start_date)) / (1000 * 60 * 60 * 24)) + 1;
      duration = `${days} Days`;
    }
    
    return {
      name: selectedGroup.name || 'Untitled Trip',
      emoji: '',
      startDate,
      endDate,
      duration,
      location: selectedGroup.destination || '',
      center: selectedGroup.destination_lat && selectedGroup.destination_lng 
        ? [selectedGroup.destination_lat, selectedGroup.destination_lng]
        : [40.7128, -74.0060],
    };
  }, [selectedGroup?.name, selectedGroup?.destination, selectedGroup?.start_date, selectedGroup?.end_date, selectedGroup?.destination_lat, selectedGroup?.destination_lng]);
  
  // Use the detailed members fetched from the API
  const members = groupMembers;

  // Memoize markers to prevent unnecessary map re-renders
  const markers = useMemo(() => {
    // If showing itinerary on map, return only itinerary items with coordinates
    if (showItineraryOnMap) {
      return itinerary
        .filter(item => item.lat && item.lng)
        .map((item, idx) => ({
          id: item.id,
          name: item.name,
          lat: item.lat,
          lng: item.lng,
          type: item.category === 'Restaurant' ? 'restaurant' : 'attraction',
          order: idx + 1,
        }));
    }
    
    // Otherwise show places filtered by category
    const placeMarkers = places
      .filter(p => p.lat && p.lng)
      .filter(p => {
        if (placesFilter === 'all') return true;
        if (placesFilter === 'places' || placesFilter === 'attraction') {
          return p.category === 'places' || p.category === 'attraction';
        }
        if (placesFilter === 'restaurants' || placesFilter === 'restaurant') {
          return p.category === 'restaurants' || p.category === 'restaurant';
        }
        if (placesFilter === 'events') return false;
        return true;
      })
      .map(p => ({
        id: p.id,
        name: p.name,
        lat: p.lat,
        lng: p.lng,
        type: p.category === 'restaurants' || p.category === 'restaurant' ? 'restaurant' : 'attraction',
      }));

    // Add event markers when showing all or events filter
    const eventMarkers = (placesFilter === 'all' || placesFilter === 'events')
      ? events
          .filter(e => e.latitude && e.longitude)
          .map(e => ({
            id: e.id,
            name: e.name,
            lat: e.latitude,
            lng: e.longitude,
            type: 'event',
          }))
      : [];

    return [...placeMarkers, ...eventMarkers];
  }, [showItineraryOnMap, itinerary, places, events, placesFilter]);

  // Memoize map location label to prevent unnecessary map re-renders
  const mapLocation = useMemo(() => {
    if (showItineraryOnMap) {
      const count = itinerary.filter(i => i.lat && i.lng).length;
      return `Itinerary (${count} places)`;
    }
    return trip.location;
  }, [showItineraryOnMap, itinerary, trip.location]);

  // Loading state
  if (isLoading) {
    return (
      <PageShell>
      <div className={`gpp-container ${useExternalLayout ? 'gpp-external-layout' : ''}`}>
        <div className="gpp-empty-state">
          <div className="gpp-loader"></div>
          <p>Loading your trips...</p>
        </div>
      </div>
      </PageShell>
    );
  }

  // No groups state
  if (Object.keys(groups).length === 0) {
    return (
      <PageShell>
      <div className={`gpp-container ${useExternalLayout ? 'gpp-external-layout' : ''}`}>
        <SidebarComponent
          groups={groups}
          selectedGroupId={selectedGroupId}
          onSelectGroup={handleSelectGroup}
          onCreateGroup={() => setIsCreateModalOpen(true)}
          onDeleteGroup={handleDeleteGroup}
          currentUserId={currentUser?.uid}
        />
        <div className="gpp-empty-state">
          <h2>Welcome to Group Planner</h2>
          <p>Create your first trip to get started!</p>
          <button 
            className="gpp-create-first-btn"
            onClick={() => setIsCreateModalOpen(true)}
          >
            Create Your First Trip
          </button>
        </div>
        
        <CreateGroupModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onCreateGroup={handleCreateGroup}
          isLoading={isCreating}
        />
      </div>
      </PageShell>
    );
  }

  // Transform polls for RightSidebar format
  const formattedPolls = polls.map(poll => ({
    id: poll.id,
    question: poll.name,
    options: (poll.options || []).map((opt, idx) => ({
      id: idx,
      label: opt,
      emoji: '',
      votes: poll.votes?.[opt] || 0,
    })),
  }));

  // Transform checklist for RightSidebar format
  const formattedChecklist = checklist.map(item => ({
    id: item.id,
    label: item.item || item.text,
    completed: item.completed || false,
    author: item.author_name,
    priority: item.priority || 'medium',
  }));

  // Build expenses from expense summary or fallback to estimated budget
  const expenses = {
    totalEstimated: expenseSummary.estimatedBudget || selectedGroup?.estimated_budget || 0,
    spent: expenseSummary.totalSpent || 0,
    userSpent: expenseSummary.userSpent || 0,
    perPerson: expenseSummary.linked 
      ? expenseSummary.perPerson 
      : (selectedGroup?.estimated_budget 
          ? Math.round(selectedGroup.estimated_budget / Math.max(1, members.length))
          : 0),
    linked: expenseSummary.linked,
    expenseGroupId: expenseSummary.expenseGroupId,
    expenseCount: expenseSummary.expenseCount || 0
  };

  return (
    <PageShell>
    <div className={`gpp-container ${useExternalLayout ? 'gpp-external-layout' : ''}`}>
      {/* Groups Sidebar */}
      <SidebarComponent
        groups={groups}
        selectedGroupId={selectedGroupId}
        onSelectGroup={handleSelectGroup}
        onCreateGroup={() => setIsCreateModalOpen(true)}
        onDeleteGroup={handleDeleteGroup}
        currentUserId={currentUser?.uid}
      />

      {/* Main Trip Planner Area */}
      <div className="gpp-main-area">
        {/* Trip Header */}
        <TripPlannerHeader
          tripName={trip.name}
          tripEmoji={trip.emoji}
          destination={trip.location}
          startDate={trip.startDate}
          endDate={trip.endDate}
          duration={trip.duration}
          createdAt={selectedGroup?.created_at}
          members={members}
          currentUser={currentUser}
          pendingCount={pendingInvitations.length}
          onPendingClick={() => setIsPendingModalOpen(true)}
          onInviteClick={handleInvite}
          onMembersClick={() => setIsMembersPanelOpen(true)}
        />

        {/* Floating Invite Dropdown */}
        {showInviteCard && (
          <div className="gpp-invite-card">
            <div className="gpp-invite-card-inner">
              <p className="gpp-invite-label">Invite Members</p>
              <p className="gpp-invite-hint">Separate multiple emails with commas</p>
              <div className="gpp-invite-input-row">
                <input
                  type="text"
                  className="gpp-invite-input"
                  placeholder="alice@email.com, bob@email.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendInvitation()}
                  autoFocus
                />
                <button
                  className="gpp-invite-send-btn"
                  onClick={handleSendInvitation}
                  disabled={inviteStatus === 'sending'}
                >
                  {inviteStatus === 'sending' ? 'Sending...' : 'Send'}
                </button>
                <button className="gpp-invite-close-btn" onClick={handleCloseInviteCard}>
                  &times;
                </button>
              </div>
              {inviteMessage && (
                <p className={`gpp-invite-msg ${inviteStatus === 'success' ? 'gpp-invite-success' : 'gpp-invite-error'}`}>
                  {inviteMessage}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Content Area */}
        <div className="gpp-content">
          {/* Places Sidebar */}
          <PlacesSidebar
            places={places}
            events={events}
            isLoadingEvents={isLoadingEvents}
            onAddPlace={handleAddToItinerary}
            activeFilter={placesFilter}
            onFilterChange={setPlacesFilter}
          />

          {/* Center Section - Map + Notes */}
          <section className="gpp-center">
            <MapSection
              location={mapLocation}
              markers={markers}
              center={trip.center}
              zoom={12}
              fitBounds={showItineraryOnMap && markers.length > 0}
            />
            <NotesSection
              key={selectedGroupId}
              initialContent={documentContent}
              onContentChange={handleNotesChange}
              lastSaved="Auto-saving..."
            />
          </section>

          {/* Right Sidebar */}
          <RightSidebar
            expenses={expenses}
            itinerary={itinerary}
            polls={formattedPolls}
            checklist={formattedChecklist}
            onLinkSplitwise={handleLinkExpenses}
            isLinkingExpense={isLinkingExpense}
            onEditItinerary={handleEditItinerary}
            onDeleteItinerary={handleDeleteItinerary}
            onShowItineraryMap={handleShowItineraryMap}
            showingItineraryMap={showItineraryOnMap}
            onCreatePoll={handleOpenPollModal}
            onEditPoll={handleEditPoll}
            onVotePoll={handleVotePoll}
            onDeletePoll={handleDeletePoll}
            onAddChecklistItem={handleOpenChecklistModal}
            onEditChecklistItem={handleEditChecklistItem}
            onToggleChecklistItem={handleToggleChecklistItem}
            onDeleteChecklistItem={handleDeleteChecklistItem}
            onExport={() => {}}
            onSaveBudget={handleSaveBudget}
            isSavingBudget={isSavingBudget}
          />
        </div>
      </div>

      {/* Pending Requests Modal */}
      <PendingModal
        isOpen={isPendingModalOpen}
        onClose={() => setIsPendingModalOpen(false)}
        pendingRequests={pendingInvitations}
        invitedBy={currentUser?.displayName || 'You'}
        onAccept={handleAcceptPending}
        onReject={handleRejectPending}
      />
      
      {/* Create Group Modal */}
      <CreateGroupModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreateGroup={handleCreateGroup}
        isLoading={isCreating}
      />
      
      {/* Create Poll Modal */}
      <CreatePollModal
        isOpen={isPollModalOpen}
        onClose={() => setIsPollModalOpen(false)}
        onCreatePoll={handleCreatePoll}
      />
      
      {/* Create Checklist Modal */}
      <CreateChecklistModal
        isOpen={isChecklistModalOpen}
        onClose={() => setIsChecklistModalOpen(false)}
        onAddItem={handleAddChecklistItem}
      />
      
      {/* Edit Itinerary Modal */}
      <EditItineraryModal
        isOpen={isEditItineraryModalOpen}
        onClose={() => {
          setIsEditItineraryModalOpen(false);
          setEditingItineraryItem(null);
        }}
        onSave={handleSaveItinerary}
        item={editingItineraryItem}
      />
      
      {/* Edit Checklist Modal */}
      <EditChecklistModal
        isOpen={isEditChecklistModalOpen}
        onClose={() => {
          setIsEditChecklistModalOpen(false);
          setEditingChecklistItem(null);
        }}
        onSave={handleSaveChecklistItem}
        item={editingChecklistItem}
      />
      
      {/* Edit Poll Modal */}
      <EditPollModal
        isOpen={isEditPollModalOpen}
        onClose={() => {
          setIsEditPollModalOpen(false);
          setEditingPoll(null);
        }}
        onSave={handleSavePoll}
        poll={editingPoll}
      />
      
      {/* Pending List Modal */}
      <PendingModal
        isOpen={isPendingModalOpen}
        onClose={() => setIsPendingModalOpen(false)}
        pendingRequests={pendingInvitations.map(inv => ({
          id: inv.id || inv.invitation_id,
          name: inv.invitee_user?.display_name || inv.invitee_email?.split('@')[0] || 'User',
          email: inv.invitee_email,
          avatar: inv.invitee_user?.photo_url
        }))}
        invitedBy={selectedGroup?.created_by_name || 'Trip Owner'}
      />
      
      {/* Members Modal */}
      <MembersModal
        isOpen={isMembersModalOpen}
        onClose={() => setIsMembersModalOpen(false)}
        groupId={selectedGroupId}
        groupName={selectedGroup?.name}
        currentUserId={currentUser?.uid}
        onRemoveMember={handleMemberRemoval}
      />
      
      {/* Compact Members Panel */}
      <MembersPanel
        isOpen={isMembersPanelOpen}
        onClose={() => setIsMembersPanelOpen(false)}
        groupId={selectedGroupId}
        groupName={selectedGroup?.name}
        currentUserId={currentUser?.uid}
        members={members}
        onRemoveMember={handleMemberRemoval}
        isOwner={selectedGroup?.created_by === currentUser?.uid}
        onLeaveGroup={handleLeaveGroup}
      />
    </div>
    </PageShell>
  );
}
