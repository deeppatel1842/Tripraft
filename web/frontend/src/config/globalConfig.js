/**
 * Global Configuration for Frontend
 * 
 * This file loads configuration from environment variables and provides
 * a centralized configuration object for the entire frontend application.
 * 
 * Brand name and other settings can be easily changed via .env file.
 */

const GlobalConfig = {
  // Brand Configuration - can be overridden via backend API
  APP_NAME: import.meta.env.VITE_APP_NAME || 'Tripraft',
  APP_DESCRIPTION: import.meta.env.VITE_APP_DESCRIPTION || 'AI-powered travel planning platform',
  APP_TAGLINE: import.meta.env.VITE_APP_TAGLINE || 'Discover. Plan. Explore.',
  
  // API Configuration
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
  
  // Asset Paths
  STATIC_ASSETS_PATH: '/',
  
  // Feature Flags
  ENABLE_ANALYTICS: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  ENABLE_DEBUG_MODE: import.meta.env.VITE_ENABLE_DEBUG_MODE === 'true',
}

// Function to fetch dynamic config from backend
let cachedConfig = null

export const fetchBackendConfig = async () => {
  if (cachedConfig) return cachedConfig
  
  try {
    const response = await fetch(`${GlobalConfig.API_BASE_URL}/config`)
    if (response.ok) {
      const config = await response.json()
      cachedConfig = config
      
      // Override frontend config with backend values
      if (config.app_name) GlobalConfig.APP_NAME = config.app_name
      if (config.app_description) GlobalConfig.APP_DESCRIPTION = config.app_description
      if (config.app_tagline) GlobalConfig.APP_TAGLINE = config.app_tagline
      
      return config
    }
  } catch (error) {
    console.warn('Could not fetch backend config, using defaults:', error)
  }
  
  return GlobalConfig
}

export default GlobalConfig
