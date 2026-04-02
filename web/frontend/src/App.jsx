import React, { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/auth/jsx/ProtectedRoute';

// Lazy-loaded route components
const HomePage = lazy(() => import('./components/pages/jsx/HomePage'));
const TripPlanner = lazy(() => import('./components/pages/jsx/TripPlanner'));
const ExpensePage = lazy(() => import('./components/pages/jsx/ExpensePage'));
const Analytics = lazy(() => import('./components/pages/jsx/Analytics'));
const ExpenseAnalytics = lazy(() => import('./components/pages/jsx/ExpenseAnalytics'));
const About = lazy(() => import('./components/pages/jsx/About'));
const Contact = lazy(() => import('./components/pages/jsx/Contact'));
const Pricing = lazy(() => import('./components/pages/jsx/Pricing'));
const Login = lazy(() => import('./components/auth/jsx/Login'));
const Signup = lazy(() => import('./components/auth/jsx/Signup'));
const AuthPage = lazy(() => import('./components/auth/jsx/AuthPage'));
const SmartInvitationHandler = lazy(() => import('./components/pages/jsx/SmartInvitationHandler'));
const PlaceSearchPage = lazy(() => import('./components/placeSearch/jsx/PlaceSearchPage'));

// These are lightweight wrappers, loaded eagerly
import InactivityTracker from './components/auth/jsx/InactivityTracker';
import FeatureErrorBoundary from './components/common/jsx/FeatureErrorBoundary';
import PageSkeleton from './components/common/jsx/PageSkeleton';

// Lazy import for group planner (single reference for both routes)
const GroupPlannerPage = lazy(() => import('./components/groupPlanner/jsx/GroupPlannerPage'));

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