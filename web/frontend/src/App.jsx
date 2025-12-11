// import React, { useEffect, useState } from 'react'
// import LoginPage from './components/page/LoginPage'
// import authService from './firebase/authService'

// export default function App() {
//   const [appName, setAppName] = useState('Wayfinder')
//   const [user, setUser] = useState(null)
//   const [loading, setLoading] = useState(true)

//   useEffect(() => {
//     // This useEffect is correct and handles the initial login check
//     const unsubscribe = authService.onAuthStateChanged(async (firebaseUser) => {
//       if (firebaseUser) {
//         try {
//           const idToken = await firebaseUser.getIdToken()
//           const result = await authService.verifyWithBackend(idToken)
//           if (result.success) {
//             setUser(result.user)
//           } else {
//             setUser(null)
//           }
//         } catch (error) {
//           console.error('Error verifying user:', error)
//           setUser(null)
//         }
//       } else {
//         setUser(null)
//       }
//       setLoading(false)
//     })
//     return () => unsubscribe()
//   }, [])

//   const handleLoginSuccess = (userData) => {
//     setUser(userData)
//   }

//   const handleLogout = async () => {
//     await authService.signOut()
//     setUser(null)
//   }

//   if (loading) {
//     return <div>Loading...</div>
//   }

//   if (!user) {
//     return <LoginPage onLoginSuccess={handleLoginSuccess} />
//   }

//   return (
//     <div className="app-root">
//       <header style={{ 
//         display: 'flex', 
//         justifyContent: 'space-between', 
//         alignItems: 'center',
//         padding: '20px',
//         background: '#1a1a2e',
//         color: '#ffffff'
//       }}>
//         <h1>{appName}</h1>
//         <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
//           <span>Welcome, {user.name || user.email}</span>
//           <button 
//             onClick={handleLogout}
//             style={{
//               padding: '8px 16px',
//               background: '#6366f1',
//               color: 'white',
//               border: 'none',
//               borderRadius: '6px',
//               cursor: 'pointer'
//             }}
//           >
//             Logout
//           </button>
//         </div>
//       </header>
//       <main style={{ 
//         padding: '40px',
//         background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
//         minHeight: 'calc(100vh - 80px)',
//         color: '#ffffff'
//       }}>
//         <p>Welcome to the Wayfinder dashboard! You are successfully logged in.</p>
//         <div style={{ marginTop: '20px', padding: '20px', background: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}>
//           <h3>User Information:</h3>
//           <p><strong>UID:</strong> {user.uid}</p>
//           <p><strong>Email:</strong> {user.email}</p>
//           <p><strong>Name:</strong> {user.name || 'Not provided'}</p>
//           <p><strong>Email Verified:</strong> {user.email_verified ? 'Yes' : 'No'}</p>
//         </div>
//       </main>
//     </div>
//   )
// }



import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { AuthProvider } from './context/AuthContext';
import { GroupPlannerProvider } from './context/GroupPlannerContext';
import ProtectedRoute from './components/ProtectedRoute';
import HomePage from './components/page/HomePage';
import PlacesExplorer from './components/page/PlacesExplorer';
import TripPlanner from './components/page/TripPlanner';
import ExpensePage from './components/page/ExpensePage';
import Analytics from './components/page/Analytics';
import ExpenseAnalytics from './components/page/ExpenseAnalytics';
import About from './components/page/About';
import Contact from './components/page/Contact';
import Pricing from './components/page/Pricing';
import Login from './components/page/Login';
import Signup from './components/page/Signup';
import AuthPage from './components/page/AuthPage';
import SmartInvitationHandler from './components/page/SmartInvitationHandler';
import GroupPlannerDemo from './components/Group_planner/GroupPlannerDemo';


export default function App() {
  return (
    <AuthProvider>
      <GroupPlannerProvider>
        <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/about" element={<About />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/pricing" element={<Pricing/>} />
        <Route path="/places" element={<PlacesExplorer />} />
        <Route path="/trip-planner" element={<TripPlanner />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/expenses" element={<ExpensePage />} />
        <Route path="/admin/analysis" element={<ExpenseAnalytics />} />
        <Route path="/group-trip" element={<GroupPlannerDemo />} />
        <Route path="/invitation/:invitationId" element={<SmartInvitationHandler />} />
        <Route path="/invitations/:invitationId" element={<SmartInvitationHandler />} />
        <Route path="/accept-invitation" element={<SmartInvitationHandler />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/auth" element={<AuthPage />} />
      </Routes>
      {/* React Query DevTools - only shows in development */}
      <ReactQueryDevtools initialIsOpen={false} position="bottom-right" />
      </GroupPlannerProvider>
    </AuthProvider>
  );
}