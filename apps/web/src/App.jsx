// Purpose: Renders the App interface within apps\web\src.
import React, { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './features/auth/jsx/ProtectedRoute';

// Lazy-loaded route components
const HomePage = lazy(() => import('./pages/HomePage'));
const TripPlanner = lazy(() => import('./pages/TripPlanner'));
const ExpensePage = lazy(() => import('./pages/ExpensePage'));
const Analytics = lazy(() => import('./pages/Analytics'));
const ExpenseAnalytics = lazy(() => import('./pages/ExpenseAnalytics'));
const About = lazy(() => import('./pages/About'));
const Contact = lazy(() => import('./pages/Contact'));
const Pricing = lazy(() => import('./pages/Pricing'));
const Login = lazy(() => import('./features/auth/jsx/Login'));
const Signup = lazy(() => import('./features/auth/jsx/Signup'));
const AuthPage = lazy(() => import('./features/auth/jsx/AuthPage'));
const SmartInvitationHandler = lazy(() => import('./pages/SmartInvitationHandler'));
const PlaceSearchPage = lazy(() => import('./features/discover/jsx/PlaceSearchPage'));

// These are lightweight wrappers, loaded eagerly
import InactivityTracker from './features/auth/jsx/InactivityTracker';
import FeatureErrorBoundary from './components/common/jsx/FeatureErrorBoundary';
import PageSkeleton from './components/common/jsx/PageSkeleton';

// Lazy import for group planner (single reference for both routes)
const GroupPlannerPage = lazy(() => import('./features/trips/jsx/GroupPlannerPage'));

export default function App() {
  return (
    <AuthProvider>
        {/* Inactivity tracker for security - logs out after 15 min inactive */}
        <InactivityTracker />
        <Suspense fallback={<PageSkeleton />}>
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
        <Route path="/places" element={
          <FeatureErrorBoundary featureName="Place Search"><PlaceSearchPage /></FeatureErrorBoundary>
        } />
        <Route path="/place-search" element={
          <FeatureErrorBoundary featureName="Place Search"><PlaceSearchPage /></FeatureErrorBoundary>
        } />
        <Route path="/trip-planner" element={
          <FeatureErrorBoundary featureName="Trip Planner"><TripPlanner /></FeatureErrorBoundary>
        } />

        {/* Invitation handler */}
        <Route path="/invitation/:invitationId" element={<SmartInvitationHandler />} />
        <Route path="/invitations/:invitationId" element={<SmartInvitationHandler />} />
        <Route path="/accept-invitation" element={<SmartInvitationHandler />} />

        {/* Protected routes */}
        <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
        <Route path="/expenses/:userId?/:mode?" element={
          <ProtectedRoute>
            <FeatureErrorBoundary featureName="Expenses"><ExpensePage /></FeatureErrorBoundary>
          </ProtectedRoute>
        } />
        <Route path="/admin/analysis" element={<ProtectedRoute><ExpenseAnalytics /></ProtectedRoute>} />
        <Route path="/group-planner/:groupId?" element={
          <ProtectedRoute>
            <FeatureErrorBoundary featureName="Group Planner"><GroupPlannerPage /></FeatureErrorBoundary>
          </ProtectedRoute>
        } />
      </Routes>
      </Suspense>
      {/* React Query DevTools - disabled in production for cleaner UI */}
      {import.meta.env.DEV && import.meta.env.VITE_SHOW_DEVTOOLS === 'true' && (
        <ReactQueryDevtools initialIsOpen={false} position="bottom-right" />
      )}
    </AuthProvider>
  );
}