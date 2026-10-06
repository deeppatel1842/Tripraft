// Purpose: Mounts the React application into the HTML root element.
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient, initializeQueryPersistence } from './lib/queryClientPersist';
import App from './App.jsx'
import './styles/global.css'
import './styles.css'

// Initialize query persistence (IndexedDB cache)
initializeQueryPersistence(queryClient).catch(() => {
  // Silently fail - app works without persistence
});

const root = document.getElementById('root');
if (!root) throw new Error('Application root is missing');
ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
