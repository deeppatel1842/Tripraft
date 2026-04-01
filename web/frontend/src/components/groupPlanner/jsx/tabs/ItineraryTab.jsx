import React, { useState, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useGroupPlaces, useAddPlace, gpKeys } from '../../../../hooks/useGroupPlannerQuery';
import groupPlannerApi from '../../../../services/groupPlannerApi';
import { toArray } from '../../utils/groupPlannerUtils';
import { formatDate, formatDateRange } from '../../utils/formatters';
import { Pencil, X, Calendar, Trash2 } from 'lucide-react';

/**
 * Itinerary tab - day-by-day schedule of places.
 *
 * Props: groupId, group, showToast
 */
export default function ItineraryTab({ groupId, group, showToast }) {
  const queryClient = useQueryClient();
  const { data: placesRaw } = useGroupPlaces(groupId);
  const addPlaceMut = useAddPlace(groupId);

  const places = useMemo(() => toArray(placesRaw, 'places'), [placesRaw]);
  const itineraryPlaces = useMemo(() => places.filter((p) => p.visit_date && !p.is_deleted), [places]);
  const unscheduledPlaces = useMemo(() => places.filter((p) => !p.visit_date && !p.is_deleted), [places]);

  const uniqueDates = useMemo(() => {
    const dates = new Set();
    itineraryPlaces.forEach((p) => { if (p.visit_date) dates.add(p.visit_date); });
    return [...dates].sort();
  }, [itineraryPlaces]);

  const dayNumbers = useMemo(() => uniqueDates.map((_, i) => i + 1), [uniqueDates]);

  const tripDuration = useMemo(() => {
    if (!group?.start_date || !group?.end_date) return null;
    const diff = Math.ceil((new Date(group.end_date) - new Date(group.start_date)) / 86400000);
    return diff > 0 ? diff : null;
  }, [group]);

  const [activeDay, setActiveDay] = useState('all');
  const [showEditModal, setShowEditModal] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [editDate, setEditDate] = useState('');
  const [editTime, setEditTime] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [showGroupNameEdit, setShowGroupNameEdit] = useState(false);
  const [editGroupName, setEditGroupName] = useState('');
  const [editingBudget, setEditingBudget] = useState(false);
  const [budgetInput, setBudgetInput] = useState('');
  const [editingDates, setEditingDates] = useState(false);
  const [dateStartInput, setDateStartInput] = useState('');
  const [dateEndInput, setDateEndInput] = useState('');

  const estimatedBudget = group?.estimated_budget || 0;
  const budgetCurrency = group?.budget_currency || 'USD';

  function getDayNumber(dateStr) {
    if (!dateStr) return 1;
    const idx = uniqueDates.indexOf(dateStr);
    if (idx >= 0) return idx + 1;
    const sorted = [...uniqueDates, dateStr].sort();
    return sorted.indexOf(dateStr) + 1;
  }

  function formatCurrency(amount, currency) {
    currency = currency || 'USD';
    return new Intl.NumberFormat('en-US', {
      style: 'currency', currency, minimumFractionDigits: 0, maximumFractionDigits: 0,
    }).format(amount);
  }

  // Format 24-hour time to 12-hour with AM/PM
  function formatTimeWithAMPM(timeStr) {
    if (!timeStr) return '--:--';
    const [hours, minutes] = timeStr.split(':');
    if (!hours) return '--:--';
    
    const hour = parseInt(hours, 10);
    const minute = parseInt(minutes, 10) || 0;
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    
    return `${displayHour}:${String(minute).padStart(2, '0')} ${ampm}`;
  }

  const filteredItinerary = useMemo(() => {
    let items = itineraryPlaces.slice();
    if (activeDay !== 'all') {
      items = items.filter((p) => getDayNumber(p.visit_date) === parseInt(activeDay));
    }
    items.sort((a, b) => {
      const dayA = getDayNumber(a.visit_date);
      const dayB = getDayNumber(b.visit_date);
      if (dayA !== dayB) return dayA - dayB;
      return (a.suggested_time || a.visit_date || '').localeCompare(b.suggested_time || b.visit_date || '');
    });
    return items;
  }, [itineraryPlaces, activeDay]);

  const handleEditPlace = async () => {
    if (!showEditModal) return;
    try {
      const place = places.find((p) => p.id === showEditModal);
      const origDate = place?.visit_date || '';
      const origTime = place?.suggested_time || '';
      const origNotes = place?.remarks || '';
      const updates = {};
      if (editDate !== origDate) updates.visit_date = editDate;
      if (editTime !== origTime) updates.suggested_time = editTime;
      if (editNotes !== origNotes) updates.remarks = editNotes;
      if (Object.keys(updates).length === 0) { setShowEditModal(null); return; }
      await groupPlannerApi.updatePlace(groupId, showEditModal, updates);
      queryClient.invalidateQueries({ queryKey: gpKeys.places(groupId) });
      setShowEditModal(null);
      setEditNotes('');
      setEditDate('');
      setEditTime('');
      showToast('Place updated');
    } catch {
      showToast('Failed to update', 'error');
    }
  };

  const handleDeletePlace = async (placeId, placeName) => {
    try {
      await groupPlannerApi.deletePlace(groupId, placeId);
      queryClient.invalidateQueries({ queryKey: gpKeys.places(groupId) });
      setShowEditModal(null);
      setConfirmDelete(null);
      showToast(`Removed ${placeName}`);
    } catch {
      showToast('Failed to remove place', 'error');
    }
  };

  const handleEditGroupName = async () => {
    if (!editGroupName.trim() || editGroupName.trim() === group?.name) {
      setShowGroupNameEdit(false);
      return;
    }
    try {
      await groupPlannerApi.updateGroup(groupId, { name: editGroupName.trim() });
      queryClient.invalidateQueries({ queryKey: gpKeys.group(groupId) });
      queryClient.invalidateQueries({ queryKey: gpKeys.groups() });
      setShowGroupNameEdit(false);
      showToast('Group renamed');
    } catch {
      showToast('Failed to rename group', 'error');
    }
  };

  const handleSaveBudget = async () => {
    const val = parseFloat(budgetInput);
    if (isNaN(val) || val < 0) { setEditingBudget(false); return; }
    try {
      await groupPlannerApi.updateGroup(groupId, { estimated_budget: val });
      queryClient.invalidateQueries({ queryKey: gpKeys.group(groupId) });
      setEditingBudget(false);
      showToast('Budget updated');
    } catch {
      showToast('Failed to update budget', 'error');
    }
  };

  const handleSaveDates = async () => {
    try {
      await groupPlannerApi.updateGroup(groupId, { start_date: dateStartInput || null, end_date: dateEndInput || null });
      queryClient.invalidateQueries({ queryKey: gpKeys.group(groupId) });
      setEditingDates(false);
      showToast('Trip dates updated');
    } catch {
      showToast('Failed to update dates', 'error');
    }
  };

  const humanMemberCount = group?.member_count || 0;

  return (
    <div className="gp-view">
      {/* Header */}
      <div className="gp-itinerary-header">
        <div>
          {showGroupNameEdit ? (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
              <input type="text" className="gp-modal-input" style={{ marginBottom: 0, fontSize: 18, fontWeight: 600, padding: '6px 12px' }} value={editGroupName} onChange={(e) => setEditGroupName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleEditGroupName()} autoFocus />
              <button className="gp-modal-btn-primary" style={{ padding: '6px 16px' }} onClick={handleEditGroupName}>Save</button>
              <button className="gp-modal-btn-secondary" style={{ padding: '6px 12px' }} onClick={() => setShowGroupNameEdit(false)}>Cancel</button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span className="gp-itinerary-group-label">{group?.name || 'Untitled'}</span>
              <button className="gp-itinerary-edit-btn" onClick={() => { setEditGroupName(group?.name || ''); setShowGroupNameEdit(true); }} title="Rename group"><Pencil size={12} /></button>
            </div>
          )}
          {(group?.start_date || group?.end_date) && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
              <span className="gp-itinerary-date-label">{formatDateRange(group.start_date, group.end_date)}</span>
              <button className="gp-itinerary-edit-btn" onClick={() => { setEditingDates(true); setDateStartInput(group?.start_date || ''); setDateEndInput(group?.end_date || ''); }} title="Edit dates"><Pencil size={10} /></button>
            </div>
          )}
          {!group?.start_date && !group?.end_date && !editingDates && (
            <button className="gp-itinerary-edit-btn" style={{ fontSize: 10, marginBottom: 4 }} onClick={() => { setEditingDates(true); setDateStartInput(''); setDateEndInput(''); }}>+ Set Trip Dates</button>
          )}
          {editingDates && (
            <div className="gp-dates-edit-row">
              <input type="date" className="gp-date-inline-input" value={dateStartInput} onChange={(e) => setDateStartInput(e.target.value)} />
              <span style={{ color: '#888' }}>to</span>
              <input type="date" className="gp-date-inline-input" value={dateEndInput} onChange={(e) => setDateEndInput(e.target.value)} />
              <button className="gp-itinerary-edit-btn" onClick={handleSaveDates} title="Save"><Pencil size={10} /></button>
              <button className="gp-itinerary-edit-btn" onClick={() => setEditingDates(false)} title="Cancel"><X size={10} /></button>
            </div>
          )}
          <h1 className="gp-itinerary-title">
            {group?.destination ? <>{group.destination.split(',')[0]} <br /></> : 'Plan'}
          </h1>
        </div>
      </div>

      {/* Stats */}
      <div className="gp-consultation-card">
        <div className="gp-stat">
          <span className="gp-stat-label">Duration</span>
          <span className="gp-stat-value">{tripDuration ? (tripDuration + ' Days') : '--'}</span>
        </div>
        <div className="gp-stat">
          <span className="gp-stat-label" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            Est. Budget
            {!editingBudget && <Pencil size={9} style={{ opacity: 0.55, cursor: 'pointer' }} onClick={() => { setBudgetInput(String(estimatedBudget || '')); setEditingBudget(true); }} />}
          </span>
          {editingBudget ? (
            <span className="gp-stat-value" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <input type="text" inputMode="numeric" className="gp-budget-inline-input" value={budgetInput} onChange={(e) => { const v = e.target.value; if (/^\d*\.?\d*$/.test(v)) setBudgetInput(v); }} onKeyDown={(e) => { if (e.key === 'Enter') handleSaveBudget(); if (e.key === 'Escape') setEditingBudget(false); }} autoFocus />
              <button className="gp-itinerary-edit-btn" onClick={handleSaveBudget} title="Save"><Pencil size={12} /></button>
              <button className="gp-itinerary-edit-btn" onClick={() => setEditingBudget(false)} title="Cancel"><X size={12} /></button>
            </span>
          ) : (
            <span className="gp-stat-value" style={{ cursor: 'pointer' }} onClick={() => { setBudgetInput(String(estimatedBudget || '')); setEditingBudget(true); }}>
              {estimatedBudget ? formatCurrency(estimatedBudget, budgetCurrency) : '--'}
            </span>
          )}
        </div>
        <div className="gp-stat">
          <span className="gp-stat-label">The Circle</span>
          <span className="gp-stat-value">{humanMemberCount} {humanMemberCount === 1 ? 'Partner' : 'Partners'}</span>
        </div>
        <div className="gp-stat gp-stat-bordered">
          <span className="gp-stat-label">Stops</span>
          <span className="gp-stat-value">{itineraryPlaces.length + unscheduledPlaces.length} Total</span>
        </div>
      </div>

      {/* Day Tabs */}
      <div className="gp-day-tabs">
        <button className={'gp-day-tab' + (activeDay === 'all' ? ' active' : '')} onClick={() => setActiveDay('all')}>Full Agenda</button>
        {dayNumbers.map((d) => (
          <button key={d} className={'gp-day-tab' + (activeDay === String(d) ? ' active' : '')} onClick={() => setActiveDay(String(d))}>Day {String(d).padStart(2, '0')}</button>
        ))}
      </div>

      {/* Timeline */}
      <div className="gp-calendar">
        {filteredItinerary.length === 0 && unscheduledPlaces.length === 0 ? (
          <div className="gp-empty-agenda">No agenda items yet. Add places from the Library.</div>
        ) : (
          <>
            {filteredItinerary.length > 0 && (() => {
              let currentDay = null;
              return filteredItinerary.map((place) => {
                const day = getDayNumber(place.visit_date);
                const showDayDivider = activeDay === 'all' && currentDay !== day;
                if (showDayDivider) currentDay = day;
                const dayDate = place.visit_date ? formatDate(place.visit_date) : '';
                return (
                  <React.Fragment key={place.id}>
                    {showDayDivider && (
                      <div className="gp-day-divider">
                        Day {day}{dayDate ? <span style={{ fontWeight: 400, fontSize: 9, marginLeft: 8, color: '#a1a1aa', letterSpacing: '0.05em' }}>{dayDate}</span> : null}
                      </div>
                    )}
                    <div className="gp-timeline-item">
                      <span className="gp-time-marker">
                        <div>{formatTimeWithAMPM(place.suggested_time)}</div>
                        <div style={{ fontSize: '11px', fontWeight: 600, color: '#4f46e5', marginTop: '2px' }}>{formatDate(place.visit_date)}</div>
                      </span>
                      <div className="gp-place-card">
                        {place.photo_url ? (
                          <img src={place.photo_url} alt={place.name} className="gp-place-img" loading="lazy" />
                        ) : (
                          <div className="gp-place-img gp-place-img-placeholder" />
                        )}
                        <div className="gp-place-info">
                          <div className="gp-place-name-row">
                            <h3 className="gp-place-name">{place.name}</h3>
                            <div style={{ display: 'flex', gap: 4 }}>
                              <button className="gp-place-edit-btn" onClick={() => { setShowEditModal(place.id); setEditDate(place.visit_date || ''); setEditTime(place.suggested_time || ''); setEditNotes(place.remarks || ''); }} title="Edit schedule">Edit</button>
                              <button className="gp-place-edit-btn" style={{ color: '#dc2626' }} onClick={() => setConfirmDelete({ id: place.id, name: place.name })} title="Remove from itinerary"><Trash2 size={12} /></button>
                            </div>
                          </div>
                          {place.remarks && <p className="gp-place-remarks">{place.remarks}</p>}
                        </div>
                      </div>
                    </div>
                  </React.Fragment>
                );
              });
            })()}

            {unscheduledPlaces.length > 0 && activeDay === 'all' && (
              <>
                <div className="gp-day-divider gp-day-divider-unassigned">Unassigned</div>
                {unscheduledPlaces.map((place) => (
                  <div key={place.id} className="gp-timeline-item gp-timeline-unassigned">
                    <span className="gp-time-marker gp-time-unset"><Calendar size={14} /></span>
                    <div className="gp-place-card">
                      {place.photo_url ? (
                        <img src={place.photo_url} alt={place.name} className="gp-place-img" loading="lazy" />
                      ) : (
                        <div className="gp-place-img gp-place-img-placeholder" />
                      )}
                      <div className="gp-place-info">
                        <div className="gp-place-name-row">
                          <h3 className="gp-place-name">{place.name}</h3>
                          <div style={{ display: 'flex', gap: 4 }}>
                              <button className="gp-place-edit-btn" onClick={() => { setShowEditModal(place.id); setEditDate(''); setEditTime(''); setEditNotes(place.remarks || ''); }} title="Set date">Schedule</button>
                              <button className="gp-place-edit-btn" style={{ color: '#dc2626' }} onClick={() => setConfirmDelete({ id: place.id, name: place.name })} title="Remove from itinerary"><Trash2 size={12} /></button>
                            </div>
                          </div>
                          {place.remarks && <p className="gp-place-remarks">{place.remarks}</p>}
                        </div>
                      </div>
                    </div>
                ))}
              </>
            )}
          </>
        )}
      </div>

      {/* Edit Place Modal */}
      {showEditModal && (
        <div className="gp-modal-overlay" onClick={() => setShowEditModal(null)}>
          <div className="gp-modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="gp-modal-title">Edit Stop</h3>
            <div style={{ marginBottom: 16 }}>
              <label className="gp-modal-label">Date</label>
              <input type="date" className="gp-modal-input" value={editDate} onChange={(e) => setEditDate(e.target.value)} />
              {editDate && group?.start_date && (
                <span style={{ fontSize: 11, color: '#71717a', marginTop: -10, display: 'block', marginBottom: 8 }}>Day {getDayNumber(editDate)}</span>
              )}
            </div>
            <div style={{ marginBottom: 16 }}>
              <label className="gp-modal-label">Time</label>
              <input type="time" className="gp-modal-input" value={editTime} onChange={(e) => setEditTime(e.target.value)} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label className="gp-modal-label">Notes</label>
              <textarea className="gp-modal-input" rows={3} value={editNotes} onChange={(e) => setEditNotes(e.target.value)} placeholder="Add notes for this stop..." />
            </div>
            <div className="gp-modal-actions">
              <button className="gp-modal-btn-primary" onClick={handleEditPlace}>Update</button>
              <button className="gp-modal-btn-secondary" onClick={() => setShowEditModal(null)}>Cancel</button>
              <button className="gp-modal-btn-secondary" style={{ color: '#dc2626', borderColor: '#fca5a5', marginLeft: 'auto' }} onClick={() => { const place = places.find((p) => p.id === showEditModal); setConfirmDelete({ id: showEditModal, name: place?.name || 'this place' }); setShowEditModal(null); }}>Remove</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {confirmDelete && (
        <div className="gp-modal-overlay" onClick={() => setConfirmDelete(null)}>
          <div className="gp-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 380 }}>
            <h3 className="gp-modal-title" style={{ color: '#dc2626' }}>Remove Place</h3>
            <p style={{ fontSize: 13, color: '#52525b', margin: '0 0 20px' }}>
              Remove <strong>{confirmDelete.name}</strong> from the itinerary? This cannot be undone.
            </p>
            <div className="gp-modal-actions">
              <button className="gp-modal-btn-secondary" style={{ color: '#dc2626', borderColor: '#fca5a5' }} onClick={() => handleDeletePlace(confirmDelete.id, confirmDelete.name)}>Remove</button>
              <button className="gp-modal-btn-secondary" onClick={() => setConfirmDelete(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
