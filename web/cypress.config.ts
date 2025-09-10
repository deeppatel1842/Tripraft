/**
 * Cypress Configuration File
 * 
 * This file configures Cypress for end-to-end testing in the Travel Planner application.
 * It sets up:
 * - E2E testing environment with local development server
 * - Component testing for isolated React component testing
 * - Video and screenshot settings for test debugging
 * - Viewport configuration for responsive testing
 * - Test file patterns and support files
 */

import { defineConfig } from 'cypress'

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:5173',
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    video: false,
    screenshotOnRunFailure: false,
    viewportWidth: 1280,
    viewportHeight: 720,
  },
  component: {
    devServer: {
      framework: 'react',
      bundler: 'vite',
    },
    supportFile: 'cypress/support/component.ts',
    specPattern: 'cypress/component/**/*.cy.{js,jsx,ts,tsx}',
  },
})
