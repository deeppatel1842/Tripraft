// Purpose: Renders the Library Tab interface within apps\web\src\features\trips\jsx\tabs.
import React, { useState, useMemo } from 'react';
import { useDestinationPlaces, useDestinationEvents, useAddPlace, useGroupPlaces } from '../../../../hooks/useGroupPlannerQuery';
import { unwrap, toArray } from '../../utils/groupPlannerUtils';
import PlaceDetailModal from '../../../discover/jsx/PlaceDetailModal';

/**
 * Library tab - destination discovery: places, restaurants, events.
 *
 * Props: groupId, destination, group, showToast
 */
export default function LibraryTab({ groupId, destination, group, showToast }) {
  const { data: destPlacesRaw } = useDestinationPlaces(destination);
  const { data: destEventsRaw } = useDestinationEvents(destination);
  const { data: placesRaw } = useGroupPlaces(groupId);
  const addPlaceMut = useAddPlace(groupId);

  const [libraryFilter, setLibraryFilter] = useState('all');
  const [selectedLibraryPlace, setSelectedLibraryPlace] = useState(null);

  const places = useMemo(() => toArray(placesRaw, 'places'), [placesRaw]);

  const addedPlaceNames = useMemo(() => {
    const names = new Set();
    places.forEach((p) => {
      if (!p.is_deleted && p.name) names.add(p.name.toLowerCase().trim());
    });
    return names;
  }, [places]);

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
          _source: 'search',
          id: 'search-' + p.id,
          sourceId: p.id,
          name: p.name,
          description: p.ai_summary || '',
          address: p.address || (p.city_name ? (p.city_name + (p.state_name ? ', ' + p.state_name : '')) : ''),
          latitude: p.latitude,
          longitude: p.longitude,
          photo_url: p.photo_url || (p.photos && p.photos[0]?.url) || '',
          rating: p.rating_tourist_priority,
          category: label,
          website: p.official_website || '',
        });
      });
    }

    const eventsData = unwrap(destEventsRaw);
    const events = eventsData?.events || (Array.isArray(eventsData) ? eventsData : []);
    if (Array.isArray(events)) {
      events.forEach((e) => {
        items.push({
          _source: 'event',
          id: 'event-' + e.id,
          sourceId: e.id,
          name: e.name,
          description: e.venue ? (e.venue + ' \u2014 ' + (e.date || '')) : e.date || '',
          address: e.address || e.venue || '',
          latitude: e.latitude,
          longitude: e.longitude,
          photo_url: e.image_url || '',
          rating: null,
          category: 'EVENT',
          website: e.url || '',
        });
      });
    }

    return items;
  }, [destPlacesRaw, destEventsRaw]);

  const filteredLibrary = useMemo(() => {
    if (libraryFilter === 'all') return destinationLibrary;
    return destinationLibrary.filter((i) => i.category === libraryFilter);
  }, [destinationLibrary, libraryFilter]);

  const handleAddLibraryItem = async (item) => {
    try {
      await addPlaceMut.mutateAsync({
        name: item.name,
        description: item.description,
        address: item.address,
        latitude: item.latitude,
        longitude: item.longitude,
        category: item.category === 'RES' ? 'restaurant' : item.category === 'EVENT' ? 'event' : 'attraction',
        photo_url: item.photo_url,
        rating: item.rating,
        website: item.website,
      });
      showToast(item.name + ' added to group');
    } catch (err) {
      if (err?.status === 409) showToast('Already in the group', 'error');
      else showToast('Failed to add place', 'error');
    }
  };

  return (
    <div className="gp-view">
      <h2 className="gp-section-title">Local Gems.</h2>
      <p style={{ color: '#71717a', fontSize: 13, marginBottom: 16 }}>
        Places, restaurants, and events in {destination || 'your destination'}.
      </p>

      <div className="gp-day-tabs" style={{ marginBottom: 16 }}>
        {[
          { key: 'all', label: 'All' },
          { key: 'PLACE', label: 'Places' },
          { key: 'RES', label: 'Restaurants' },
          { key: 'EVENT', label: 'Events' },
        ].map((f) => (
          <button key={f.key} className={'gp-day-tab' + (libraryFilter === f.key ? ' active' : '')} onClick={() => setLibraryFilter(f.key)}>
            {f.label}
          </button>
        ))}
      </div>

      <div className="gp-section-header" style={{ marginBottom: 12 }}>
        <span className="gp-section-label">Discover {destination || ''}</span>
      </div>

      {filteredLibrary.length === 0 ? (
        <div className="gp-empty-agenda">
          {destination ? 'No results found. Try a different filter.' : 'Set a destination to see curated places.'}
        </div>
      ) : (
        <div className="gp-library-grid">
          {filteredLibrary.map((item) => {
            const isAdded = addedPlaceNames.has((item.name || '').toLowerCase().trim());
            return (
              <div key={item.id} className="gp-library-card" onClick={() => setSelectedLibraryPlace({ ...item, id: item.sourceId })} style={{ cursor: 'pointer' }}>
                {item.photo_url ? (
                  <img src={item.photo_url} alt={item.name} className="gp-library-card-img" loading="lazy" />
                ) : (
                  <div className="gp-library-card-img" style={{ background: '#f0f0f0' }} />
                )}
                <div className="gp-library-card-body">
                  <h3 className="gp-library-card-name">{item.name}</h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span className={'gp-library-label gp-library-label-' + item.category.toLowerCase()}>
                      {item.category === 'RES' ? 'Restaurant' : item.category === 'EVENT' ? 'Event' : 'Place'}
                    </span>
                  </div>
                  {item.address && <p className="gp-library-card-addr">{item.address}</p>}
                  <p className="gp-library-card-desc">{item.description || 'No description'}</p>
                  <div className="gp-library-card-footer">
                    {item.website && (
                      <a href={item.website} target="_blank" rel="noopener noreferrer" className="gp-library-card-link" onClick={(e) => e.stopPropagation()}>Visit Website</a>
                    )}
                    {isAdded ? (
                      <span className="gp-library-added-badge">Already Added</span>
                    ) : (
                      <button className="gp-library-add-btn" onClick={(e) => { e.stopPropagation(); handleAddLibraryItem(item); }}>Add to Group</button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedLibraryPlace && (
        <PlaceDetailModal place={selectedLibraryPlace} onClose={() => setSelectedLibraryPlace(null)} />
      )}
    </div>
  );
}
