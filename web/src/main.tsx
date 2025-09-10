/**
 * Main Application Entry Point
 * 
 * This file serves as the root entry point for the Travel Planner React application.
 * It sets up:
 * - React root rendering
 * - Redux store provider for state management
 * - React Router for navigation
 * - Global CSS imports (Tailwind CSS)
 * - Application-wide providers and context
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'
import { store } from '@store/index'
import App from './App'
import '@assets/styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Provider store={store}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </Provider>
  </React.StrictMode>
)
