// Purpose: Renders the Group Planner Manager interface within apps\web\src\features\trips\jsx.
/**
 * GroupPlannerManager - Thin orchestrator.
 *
 * Delegates rendering to extracted tab, map, chat, and shared components.
 * Owns only: routing, tab state, map day, toasts, invite/create modals.
 */

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import {
  useGroups,
  useGroupDetail,
  useGroupPlaces,
  useGroupMembers,
  useGroupActivities,
  useDestinationPlaces,
  useDestinationEvents,
  useCreateGroup,
  gpKeys,
} from '../../../hooks/useGroupPlannerQuery';
import { useQueryClient } from '@tanstack/react-query';
import groupPlannerApi from '../../../services/groupPlannerApi';
import CreateGroupModal from './CreateGroupModal';
import Toast from '@tripraft/ui/Toast';
import { ArrowLeft } from 'lucide-react';
import '../css/GroupPlannerPage.css';

import { TABS } from '../constants/tabConfig';
import { unwrap, toArray, toObject } from '../utils/groupPlannerUtils';
import { getInitials } from '../utils/formatters';

import GroupSelector from './shared/GroupSelector';
import MapPanel from './map/MapPanel';
import ChatPanel from './chat/ChatPanel';
import ItineraryTab from './tabs/ItineraryTab';
import LibraryTab from './tabs/LibraryTab';
import LogisticsTab from './tabs/LogisticsTab';
import TreasuryTab from './tabs/TreasuryTab';
import PulseTab from './tabs/PulseTab';
import CircleTab from './tabs/CircleTab';

export default function GroupPlannerManager() {
  const { groupId: routeGroupId } = useParams();
  const navigate = useNavigate();
  const { currentUser, loading: authLoading } = useAuth();
  const queryClient = useQueryClient();

  // -- Orchestrator state --
  const [selectedGroupId, setSelectedGroupId] = useState(routeGroupId || null);
  const [activeTab, setActiveTab] = useState('itinerary');
  const [mapDay, setMapDay] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [toasts, setToasts] = useState([]);
  const [pulseUnread, setPulseUnread] = useState(false);
  const activityCursor = useRef({ groupId: null, newestId: null });
  const [isInviting, setIsInviting] = useState(false);
  const invitingRef = useRef(false);

  // -- Queries (shared across children / needed for MapPanel) --
  const { data: groupsRaw, isLoading: groupsLoading } = useGroups();
  const { data: groupDetailRaw, isLoading: groupLoading } = useGroupDetail(selectedGroupId);
  const { data: placesRaw } = useGroupPlaces(selectedGroupId);
  const { data: membersRaw } = useGroupMembers(selectedGroupId);
  const { data: activitiesRaw } = useGroupActivities(selectedGroupId);

  const group = useMemo(() => toObject(groupDetailRaw), [groupDetailRaw]);
  const destination = group?.destination || '';

  const { data: destPlacesRaw } = useDestinationPlaces(destination);
  const { data: destEventsRaw } = useDestinationEvents(destination);

  const createGroupMut = useCreateGroup();

  // -- Derived data --
  const groups = useMemo(() => toArray(groupsRaw, 'groups'), [groupsRaw]);
  const places = useMemo(() => toArray(placesRaw, 'places'), [placesRaw]);
  const members = useMemo(() => toArray(membersRaw, 'members'), [membersRaw]);
  const activities = useMemo(() => toArray(activitiesRaw, 'activities'), [activitiesRaw]);
  const budgetCurrency = group?.budget_currency || 'USD';

  const humanMembers = useMemo(
    () => members.filter((m) => m.is_active !== false && m.type !== 'ai'),
    [members],
  );

  const destinationLibrary = useMemo(() => {
    const items = [];
    const searchData = unwrap(destPlacesRaw);
    const searchItems = searchData?.places || searchData?.data || searchData?.results || (Array.isArray(searchData) ? searchData : []);
    if (Array.isArray(searchItems)) {
      searchItems.forEach((p) => {
        const tags = (p.tags || []).join(' ').toLowerCase();
        const nameLC = (p.name || '').toLowerCase();
        let label = 'PLACE';
        if (tags.includes('restaurant') || tags.includes('food') || tags.includes('dining') || nameLC.includes('restaurant')) label = 'RES';
        else if (tags.includes('event') || tags.includes('entertainment') || tags.includes('nightlife')) label = 'EVENT';
        items.push({
          _source: 'search', id: 'search-' + p.id, sourceId: p.id, name: p.name,
          description: p.ai_summary || '', address: p.address || (p.city_name ? (p.city_name + (p.state_name ? ', ' + p.state_name : '')) : ''),
          latitude: p.latitude, longitude: p.longitude,
          photo_url: p.photo_url || (p.photos && p.photos[0]?.url) || '',
          rating: p.rating_tourist_priority, category: label, website: p.official_website || '',
        });
      });
    }
    const eventsData = unwrap(destEventsRaw);
    const events = eventsData?.events || (Array.isArray(eventsData) ? eventsData : []);
    if (Array.isArray(events)) {
      events.forEach((e) => {
        items.push({
          _source: 'event', id: 'event-' + e.id, sourceId: e.id, name: e.name,
          description: e.venue ? (e.venue + ' \u2014 ' + (e.date || '')) : e.date || '',
          address: e.address || e.venue || '', latitude: e.latitude, longitude: e.longitude,
          photo_url: e.image_url || '', rating: null, category: 'EVENT', website: e.url || '',
        });
      });
    }
    return items;
  }, [destPlacesRaw, destEventsRaw]);

  const itineraryPlaces = useMemo(() => places.filter((p) => p.visit_date && !p.is_deleted), [places]);
  const uniqueDates = useMemo(() => {
    const dates = new Set();
    itineraryPlaces.forEach((p) => { if (p.visit_date) dates.add(p.visit_date); });
    return [...dates].sort();
  }, [itineraryPlaces]);
  const dayNumbers = useMemo(() => uniqueDates.map((_, i) => i + 1), [uniqueDates]);

  // -- Route sync --
  useEffect(() => {
    const id = routeGroupId || null;
    if (id !== selectedGroupId) setSelectedGroupId(id);
  }, [routeGroupId, selectedGroupId]);

  // -- Auto-redirect to last visited group --
  useEffect(() => {
    if (routeGroupId || authLoading || groupsLoading) return;
    const lastGroupId = localStorage.getItem('gp_last_group');
    if (!lastGroupId) return;
    if (groups.length > 0 && groups.some((g) => String(g.id) === lastGroupId)) {
      navigate('/group-planner/' + lastGroupId, { replace: true });
    }
  }, [routeGroupId, authLoading, groupsLoading, groups, navigate]);

  useEffect(() => {
    const newestId = activities[0]?.id || null;
    const previous = activityCursor.current;
    if (previous.groupId !== selectedGroupId) setPulseUnread(false);
    else if (previous.newestId && newestId && previous.newestId !== newestId && activeTab !== 'pulse') setPulseUnread(true);
    activityCursor.current = { groupId: selectedGroupId, newestId };
  }, [activities, activeTab, selectedGroupId]);

  // -- Helpers --
  function showToast(message, type) {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type: type || 'success' }]);
  }
  function hideToast(id) {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }

  // -- Actions --
  const handleSelectGroup = useCallback((id) => {
    setSelectedGroupId(id);
    setActiveTab('itinerary');
    setMapDay('all');
    localStorage.setItem('gp_last_group', String(id));
    navigate('/group-planner/' + id);
  }, [navigate]);

  const handleBackToDashboard = useCallback(() => {
    setSelectedGroupId(null);
    setActiveTab('itinerary');
    navigate('/group-planner');
  }, [navigate]);

  const handleCreateGroup = async (groupData) => {
    try {
      const result = await createGroupMut.mutateAsync(groupData);
      const newGroup = unwrap(result);
      setShowCreateModal(false);
      showToast('Group created');
      if (newGroup?.id) handleSelectGroup(newGroup.id);
    } catch (err) {
      showToast(err?.message || 'Failed to create group', 'error');
    }
  };

  const handleSendInvite = async () => {
    if (invitingRef.current || !inviteEmail.trim()) return;
    const emails = [...new Set(inviteEmail.split(',').map(e => e.trim().toLowerCase()).filter(Boolean))];
    if (emails.some(e => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e))) { showToast('Enter valid email addresses', 'error'); return; }
    if (emails.length === 0) { showToast('Enter valid email addresses', 'error'); return; }
    invitingRef.current = true;
    setIsInviting(true);
    let successCount = 0;
    let failCount = 0;
    for (const email of emails) {
      try { await groupPlannerApi.createInvitation(selectedGroupId, email); successCount++; } catch { failCount++; }
    }
    invitingRef.current = false;
    setIsInviting(false);
    setInviteEmail('');
    queryClient.invalidateQueries({ queryKey: gpKeys.members(selectedGroupId) });
    if (successCount > 0) showToast(successCount === 1 ? 'Invitation created' : `${successCount} invitations created`);
    if (failCount > 0) showToast(`${failCount} invite${failCount > 1 ? 's' : ''} failed`, 'error');
    if (successCount > 0 && failCount === 0) setShowInviteModal(false);
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab === 'pulse') setPulseUnread(false);
  };

  // -- Loading --
  if (authLoading) {
    return <div className="gp-loading"><div className="gp-loading-spinner" /> Loading...</div>;
  }

  // -- Dashboard (no group selected) --
  if (!selectedGroupId) {
    return (
      <>
        <GroupSelector
          groups={groups}
          groupsLoading={groupsLoading}
          onSelectGroup={handleSelectGroup}
          onCreateGroup={() => setShowCreateModal(true)}
        />
        <CreateGroupModal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} onCreateGroup={handleCreateGroup} isLoading={createGroupMut.isPending} />
        {toasts.map((t) => <Toast key={t.id} message={t.message} type={t.type} onClose={() => hideToast(t.id)} />)}
      </>
    );
  }

  // -- Loading workspace --
  if (groupLoading) {
    return <div className="gp-loading"><div className="gp-loading-spinner" /> Loading workspace...</div>;
  }

  // -- Active tab renderer --
  const renderTab = () => {
    switch (activeTab) {
      case 'itinerary': return <ItineraryTab groupId={selectedGroupId} group={group} showToast={showToast} />;
      case 'library': return <LibraryTab groupId={selectedGroupId} destination={destination} group={group} showToast={showToast} />;
      case 'logistics': return <LogisticsTab groupId={selectedGroupId} showToast={showToast} />;
      case 'treasury': return <TreasuryTab groupId={selectedGroupId} budgetCurrency={budgetCurrency} />;
      case 'pulse': return <PulseTab groupId={selectedGroupId} />;
      case 'circle': return <CircleTab groupId={selectedGroupId} showToast={showToast} />;
      default: return null;
    }
  };

  return (
    <div className="gp-workspace">
      {/* Sidebar */}
      <aside className="gp-sidebar">
        <button className="gp-orb gp-orb-back" onClick={handleBackToDashboard} title="Back to all groups"><ArrowLeft size={16} /></button>
        {groups.map((g) => (
          <button key={g.id} className={'gp-orb' + (g.id === selectedGroupId ? ' active' : '')} onClick={() => handleSelectGroup(g.id)} title={g.name}>
            {getInitials(g.name)}
          </button>
        ))}
        <button className="gp-orb gp-orb-add" onClick={() => setShowCreateModal(true)} title="New group">+</button>
      </aside>

      {/* Content */}
      <div className="gp-workspace-content">
        {/* Nav */}
        <nav className="gp-workspace-nav">
          <div className="gp-workspace-nav-left">
            <div className="gp-tabs">
              {TABS.map((tab) => (
                <button key={tab.key} className={'gp-tab' + (activeTab === tab.key ? ' active' : '')} onClick={() => handleTabChange(tab.key)}>
                  {tab.label}
                  {tab.key === 'pulse' && pulseUnread && <span className="gp-tab-pulse-dot" />}
                </button>
              ))}
            </div>
          </div>
          <div className="gp-workspace-nav-right">
            <div className="gp-member-avatars">
              {humanMembers.slice(0, 4).map((m) =>
                m.photo_url || m.avatar ? (
                  <img key={m.id || m.user_id} src={m.photo_url || m.avatar} alt={m.display_name} className="gp-member-avatar-img" title={m.display_name || m.email} />
                ) : (
                  <div key={m.id || m.user_id} className="gp-member-avatar" title={m.display_name || m.email}>{getInitials(m.display_name || m.email || 'U')}</div>
                ),
              )}
              {humanMembers.length > 4 && <div className="gp-member-avatar" title={'+' + (humanMembers.length - 4) + ' more'}>+{humanMembers.length - 4}</div>}
            </div>
            <button className="gp-btn-invite" onClick={() => setShowInviteModal(true)}>Invite Friend</button>
          </div>
        </nav>

        {/* Body */}
        <div className="gp-workspace-body">
          <section className="gp-left-pane">{renderTab()}</section>
          <section className="gp-right-pane">
            <MapPanel
              group={group} places={places} filteredLibrary={destinationLibrary}
              activeTab={activeTab} mapDay={mapDay} uniqueDates={uniqueDates}
              dayNumbers={dayNumbers} onMapDayChange={setMapDay}
            />
            <ChatPanel groupId={selectedGroupId} destination={destination} showToast={showToast} />
          </section>
        </div>
      </div>

      {/* Modals */}
      <CreateGroupModal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} onCreateGroup={handleCreateGroup} isLoading={createGroupMut.isPending} />

      {showInviteModal && (
        <div className="gp-modal-overlay" onClick={() => setShowInviteModal(false)}>
          <div className="gp-modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="gp-modal-title">Invite Friends</h3>
            <p style={{ fontSize: 13, color: '#71717a', margin: '0 0 16px' }}>Enter email addresses separated by commas to invite multiple people at once.</p>
            <textarea
              className="gp-modal-input" disabled={isInviting} rows={3} placeholder="friend1@email.com, friend2@email.com"
              value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendInvite(); } }}
              autoFocus
            />
            {inviteEmail.trim() && (
              <span style={{ fontSize: 11, color: '#71717a', display: 'block', marginTop: -10, marginBottom: 12 }}>
                {inviteEmail.split(',').map((e) => e.trim()).filter((e) => e && e.includes('@')).length} recipient(s)
              </span>
            )}
            <div className="gp-modal-actions">
              <button className="gp-modal-btn-primary" disabled={isInviting} onClick={handleSendInvite}>{isInviting ? 'Sending...' : 'Send Invites'}</button>
              <button className="gp-modal-btn-secondary" onClick={() => setShowInviteModal(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {toasts.map((t) => <Toast key={t.id} message={t.message} type={t.type} onClose={() => hideToast(t.id)} />)}
    </div>
  );
}

