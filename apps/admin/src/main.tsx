// Purpose: Renders the admin console with initialized server-account authorization, readiness and ingestion audit results.
import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './styles.css';
const root = document.getElementById('root');
if (!root) throw new Error('Missing application root');
createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
