/**
 * GroupPlannerPage — Thin wrapper (same pattern as ExpensePage)
 *
 * Header + GroupPlannerManager + Footer
 */

import React from 'react';
import Header from '../../layout/jsx/Header';
import Footer from '../../layout/jsx/Footer';
import GroupPlannerManager from './GroupPlannerManager';
import { useAuth } from '../../../context/AuthContext';
import '../css/GroupPlannerPage.css';

export default function GroupPlannerPage() {
  const { currentUser, signOut } = useAuth();

  return (
    <div className="gp-page">
      <Header
        isAuthenticated={!!currentUser}
        user={currentUser}
        onLogout={signOut}
      />
      <main className="main-content">
        <GroupPlannerManager />
      </main>
      <Footer />
    </div>
  );
}
