# Development Environment Setup Guide - Web-First Approach

## Prerequisites

### System Requirements
- **Operating System**: Windows 10+, macOS 12+, or Ubuntu 20.04+
- **RAM**: Minimum 8GB, Recommended 16GB
- **Storage**: 20GB+ available space for web development
- **Internet**: Stable broadband connection for API integrations

### Required Software

#### 1. Node.js and npm
```bash
# Download and install Node.js 18+ from https://nodejs.org
# Verify installation
node --version  # Should be 18.0.0 or higher
npm --version   # Should be 8.0.0 or higher
```

#### 2. Git Version Control
```bash
# Install Git from https://git-scm.com
git --version  # Verify installation

# Configure Git
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

#### 3. Code Editor
- **Recommended**: Visual Studio Code with extensions:
  - ES7+ React/Redux/React-Native snippets
  - TypeScript Importer
  - ESLint
  - Prettier
  - Tailwind CSS IntelliSense
  - Firebase
  - GitLens
  - Auto Rename Tag
  - Bracket Pair Colorizer

#### 4. Modern Web Browser
- **Chrome** (recommended for development tools)
- **Firefox Developer Edition**
- **Edge** or **Safari** for cross-browser testing

## Project Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-org/collaborative-trip-planner.git
cd collaborative-trip-planner
```

### 2. Environment Configuration

#### Backend Environment Variables
```bash
# Navigate to backend directory
cd backend

# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
```

**Backend .env Configuration:**
```env
# Server Configuration
PORT=3000
NODE_ENV=development

# Firebase Configuration
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour-Private-Key\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token

# External API Keys
AMADEUS_CLIENT_ID=your-amadeus-client-id
AMADEUS_CLIENT_SECRET=your-amadeus-client-secret
BOOKING_COM_API_KEY=your-booking-api-key
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
TRIPADVISOR_API_KEY=your-tripadvisor-api-key

# Database Configuration
FIRESTORE_DATABASE_URL=https://your-project.firebaseio.com

# Security
JWT_SECRET=your-jwt-secret-key
ENCRYPTION_KEY=your-encryption-key

# Email Configuration (for invitations)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

#### Web App Environment Configuration
```bash
# Navigate to web app directory
cd ../web-app

# Copy environment template
cp .env.example .env

# Edit .env file
```

**Web App .env Configuration:**
```env
# API Configuration
VITE_API_BASE_URL=http://localhost:3000/api
VITE_WS_BASE_URL=ws://localhost:3000

# Firebase Configuration (Web)
VITE_FIREBASE_API_KEY=your-firebase-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456789:web:abcdef123456

# Google Maps API Key (for web)
VITE_GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# Environment
NODE_ENV=development
```

### 3. Install Dependencies

#### Backend Dependencies
```bash
cd backend
npm install

# Install global TypeScript if not already installed
npm install -g typescript ts-node

# Install development tools
npm install -g nodemon concurrently
```

#### Web App Dependencies
```bash
cd ../web-app
npm install

# Install global Vite CLI (optional)
npm install -g vite
```

### 4. Firebase Project Setup

#### Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create new project
3. Enable Authentication (Email/Password, Google, Apple)
4. Create Firestore database
5. Set up storage bucket
6. Enable Cloud Functions

#### Generate Service Account Key
1. Go to Project Settings > Service Accounts
2. Generate new private key
3. Download JSON file
4. Extract values for backend .env file

#### Configure Authentication Providers
```javascript
// Enable in Firebase Console Authentication > Sign-in method
- Email/Password
- Google
- Apple (for iOS)
```

#### Firestore Security Rules
```javascript
// Deploy these rules to Firestore
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Development rules - update for production
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

### 5. External API Setup

#### Amadeus API (Flights)
1. Register at [Amadeus Developers](https://developers.amadeus.com)
2. Create application
3. Get Client ID and Secret
4. Add to backend .env

#### Booking.com API (Hotels)
1. Apply for [Booking.com Partner Hub](https://partners.booking.com)
2. Get API credentials
3. Add to backend .env

#### Google Maps Platform
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable Maps, Places, and Directions APIs
3. Create API key
4. Set up billing account
5. Add restrictions for security

#### TripAdvisor API (Reviews)
1. Register at [TripAdvisor Developer Portal](https://developer-tripadvisor.com)
2. Get API key
3. Add to backend .env

## Development Workflow

### 1. Start Development Servers

#### Terminal 1 - Backend Server
```bash
cd backend
npm run dev

# This starts the Express server with hot reload
# Server will be available at http://localhost:3000
# API endpoints will be at http://localhost:3000/api
```

#### Terminal 2 - Web Application
```bash
cd web-app
npm run dev

# This starts the Vite development server
# Web app will be available at http://localhost:5173
# Hot reload enabled for instant updates
```

### 2. Database Initialization

#### Run Database Seed Scripts
```bash
cd backend
npm run seed:dev

# This will create initial data structure in Firestore
```

### 3. Testing Setup

#### Run Backend Tests
```bash
cd backend
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

#### Run Web App Tests
```bash
cd web-app
npm test

# Run tests in watch mode
npm run test:watch

# Run E2E tests with Cypress
npm run test:e2e

# Run tests with coverage
npm run test:coverage
```

## Development Tools

### Browser Development Tools

#### Chrome DevTools Extensions
- **React Developer Tools** - Debug React components
- **Redux DevTools** - Monitor Redux state changes
- **Firebase DevTools** - Debug Firebase integration

#### Browser Testing
```bash
# Web app automatically opens in default browser
# Test in multiple browsers:
# - Chrome (primary development)
# - Firefox
# - Safari (macOS)
# - Edge

# Responsive design testing built into browsers
```

### Code Quality Tools

#### ESLint and Prettier Setup
```bash
# Backend
cd backend
npm run lint
npm run lint:fix
npm run format

# Web App
cd web-app
npm run lint
npm run lint:fix
npm run format
```

#### Pre-commit Hooks
```bash
# Install husky for git hooks
npm install -g husky

# Set up pre-commit hooks (run from project root)
npx husky install
npx husky add .husky/pre-commit "npm run lint && npm test"
```

## Common Issues and Solutions

### Vite Development Server Issues

#### Port Already in Use
```bash
# Kill process using port 5173
# Windows
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:5173 | xargs kill -9

# Or use different port
npm run dev -- --port 3001
```

#### Build Issues
```bash
# Clear Vite cache
rm -rf node_modules/.vite
npm run dev

# Clear npm cache
npm cache clean --force

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Firebase Issues

#### Authentication Not Working
- Check API keys in .env files
- Verify Firebase project configuration
- Ensure authentication providers are enabled
- Check CORS settings for web

#### Firestore Permission Denied
- Check security rules in Firebase Console
- Verify user authentication
- Update rules for development environment
- Check network connectivity

### API Integration Issues

#### CORS Errors
```bash
# Add to backend CORS configuration
app.use(cors({
  origin: ['http://localhost:5173', 'http://localhost:3000'],
  credentials: true
}));
```

#### External API Rate Limits
- Implement proper caching
- Add request throttling
- Use development vs production keys
- Monitor API usage in respective dashboards

### Tailwind CSS Issues

#### Styles Not Loading
```bash
# Ensure Tailwind is properly configured
# Check tailwind.config.js
# Verify CSS imports in main CSS file
# Clear browser cache and hard refresh
```

## Production Considerations

### Environment Variables for Production
```bash
# Web App Production Environment
VITE_API_BASE_URL=https://your-api-domain.com/api
VITE_FIREBASE_PROJECT_ID=your-production-project

# Backend Production Environment
NODE_ENV=production
PORT=443
CORS_ORIGIN=https://your-domain.com
```

### Build and Deployment

#### Web App Build
```bash
cd web-app
npm run build

# This creates optimized production build in 'dist' folder
# Static files ready for deployment to CDN or hosting service
```

#### Backend Deployment
```bash
cd backend
npm run build

# Compile TypeScript to JavaScript in 'dist' folder
# Ready for deployment to cloud platform
```

### Performance Optimization
- [ ] Bundle size analysis with `npm run analyze`
- [ ] Image optimization and lazy loading
- [ ] API response caching
- [ ] Database query optimization
- [ ] Lighthouse performance audit

This web-first setup guide provides a streamlined development experience focused on rapid web application development with future mobile expansion capabilities.
