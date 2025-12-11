// import React from 'react'
// import { createRoot } from 'react-dom/client'
// import App from './App'
// import './styles.css'

// const root = createRoot(document.getElementById('root'))
// root.render(<App />)


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

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)