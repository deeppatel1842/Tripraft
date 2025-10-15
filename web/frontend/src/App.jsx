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
import HomePage from './components/page/HomePage';
import PlacesExplorer from './components/page/PlacesExplorer';
import TripPlanner from './components/page/TripPlanner';


export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/places" element={<PlacesExplorer />} />
      <Route path="/trip-planner" element={<TripPlanner />} />
    </Routes>
  );
}