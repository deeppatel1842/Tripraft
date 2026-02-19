import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { AuthProvider } from './context/AuthContext';
import { GroupPlannerProvider } from './context/GroupPlannerContext';
import ProtectedRoute from './components/auth/jsx/ProtectedRoute';
import HomePage from './components/pages/jsx/HomePage';
import TripPlanner from './components/pages/jsx/TripPlanner';
import ExpensePage from './components/pages/jsx/ExpensePage';
import Analytics from './components/pages/jsx/Analytics';
import ExpenseAnalytics from './components/pages/jsx/ExpenseAnalytics';
import About from './components/pages/jsx/About';
import Contact from './components/pages/jsx/Contact';
import Pricing from './components/pages/jsx/Pricing';
import Login from './components/auth/jsx/Login';
import Signup from './components/auth/jsx/Signup';
import AuthPage from './components/auth/jsx/AuthPage';
import SmartInvitationHandler from './components/pages/jsx/SmartInvitationHandler';
import { GroupPlannerDashboard, GroupPlanner } from './components/groupPlanner';
import InactivityTracker from './components/auth/jsx/InactivityTracker';
import { PlaceSearchPage } from './components/placeSearch';


export default function App() {
  return (
    <AuthProvider>
      <GroupPlannerProvider>
        {/* Inactivity tracker for security - logs out after 15 min inactive */}
        <InactivityTracker />
        <Routes>
        {/* Public routes */}
        <Route path="/" element={<HomePage />} />
        <Route path="/about" element={<About />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/pricing" element={<Pricing/>} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/auth" element={<AuthPage />} />

        {/* Public: Place Search & Trip Planner (read-only, no auth) */}
        <Route path="/places" element={<PlaceSearchPage />} />
        <Route path="/place-search" element={<PlaceSearchPage />} />
        <Route path="/trip-planner" element={<TripPlanner />} />

        {/* Invitation handler — works both logged-in and logged-out */}
        <Route path="/invitation/:invitationId" element={<SmartInvitationHandler />} />
        <Route path="/invitations/:invitationId" element={<SmartInvitationHandler />} />
        <Route path="/accept-invitation" element={<SmartInvitationHandler />} />

        {/* Protected routes — require authentication */}
        <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
        <Route path="/expenses" element={<ProtectedRoute><ExpensePage /></ProtectedRoute>} />
        <Route path="/admin/analysis" element={<ProtectedRoute><ExpenseAnalytics /></ProtectedRoute>} />
        <Route path="/group-planner" element={<ProtectedRoute><GroupPlannerDashboard /></ProtectedRoute>} />
        <Route path="/group-planner/:groupId" element={<ProtectedRoute><GroupPlanner /></ProtectedRoute>} />
      </Routes>
      {/* React Query DevTools - disabled in production for cleaner UI */}
      {import.meta.env.DEV && import.meta.env.VITE_SHOW_DEVTOOLS === 'true' && (
        <ReactQueryDevtools initialIsOpen={false} position="bottom-right" />
      )}
      </GroupPlannerProvider>
    </AuthProvider>
  );
}