// TripCommandCenter - Wrapper for GroupPlannerPage
// This component provides the full trip command center experience
// with groups sidebar, map, notes, expenses, itinerary, polls, and checklists

import React from 'react';
import GroupPlannerPage from './GroupPlannerPage';

export default function TripCommandCenter(props) {
  return <GroupPlannerPage {...props} />;
}
