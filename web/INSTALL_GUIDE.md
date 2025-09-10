# Travel Planner Web Application - Complete Installation Guide

## 🚀 One-Command Setup

Run this single command to install everything needed:

```bash
npm install react@^18.2.0 react-dom@^18.2.0 react-router-dom@^6.8.1 react-redux@^9.1.0 @reduxjs/toolkit@^2.2.1 react-hot-toast@^2.4.1 firebase@^10.8.0 leaflet@^1.9.4 react-leaflet@^4.2.1 date-fns@^3.3.1 @types/react@^18.2.43 @types/react-dom@^18.2.17 @types/leaflet@^1.9.8 @vitejs/plugin-react@^4.2.1 typescript@^5.2.2 vite@^5.0.8 tailwindcss@^3.4.1 @tailwindcss/postcss@^7.0.39 postcss@^8.4.35 autoprefixer@^10.4.17 eslint@^8.57.0 @typescript-eslint/eslint-plugin@^7.0.2 @typescript-eslint/parser@^7.0.2 eslint-plugin-react@^7.33.2 eslint-plugin-react-hooks@^4.6.0 eslint-plugin-react-refresh@^0.4.5 prettier@^3.2.5 vitest@^1.3.0 @testing-library/react@^14.2.1 @testing-library/jest-dom@^6.4.2 @testing-library/user-event@^14.5.2 jsdom@^24.0.0 cypress@^13.6.6 @types/testing-library__jest-dom@^6.0.0 --save-exact
```

## 📋 Complete Dependencies List

### Production Dependencies (Runtime)
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0", 
  "react-router-dom": "^6.8.1",
  "react-redux": "^9.1.0",
  "@reduxjs/toolkit": "^2.2.1",
  "react-hot-toast": "^2.4.1",
  "firebase": "^10.8.0",
  "leaflet": "^1.9.4",
  "react-leaflet": "^4.2.1",
  "date-fns": "^3.3.1"
}
```

### Development Dependencies (Build/Dev Tools)
```json
{
  "@types/react": "^18.2.43",
  "@types/react-dom": "^18.2.17",
  "@types/leaflet": "^1.9.8",
  "@vitejs/plugin-react": "^4.2.1",
  "typescript": "^5.2.2",
  "vite": "^5.0.8",
  "tailwindcss": "^3.4.1",
  "@tailwindcss/postcss": "^7.0.39",
  "postcss": "^8.4.35",
  "autoprefixer": "^10.4.17",
  "eslint": "^8.57.0",
  "@typescript-eslint/eslint-plugin": "^7.0.2",
  "@typescript-eslint/parser": "^7.0.2",
  "eslint-plugin-react": "^7.33.2",
  "eslint-plugin-react-hooks": "^4.6.0",
  "eslint-plugin-react-refresh": "^0.4.5",
  "prettier": "^3.2.5",
  "vitest": "^1.3.0",
  "@testing-library/react": "^14.2.1",
  "@testing-library/jest-dom": "^6.4.2",
  "@testing-library/user-event": "^14.5.2",
  "jsdom": "^24.0.0",
  "cypress": "^13.6.6",
  "@types/testing-library__jest-dom": "^6.0.0"
}
```

## 🛠️ Step-by-Step Installation

If the one-command setup fails, use this step-by-step approach:

### Step 1: Core React Dependencies
```bash
npm install react react-dom react-router-dom
```

### Step 2: State Management
```bash
npm install react-redux @reduxjs/toolkit
```

### Step 3: UI and Notifications
```bash
npm install react-hot-toast
```

### Step 4: Backend and Database
```bash
npm install firebase
```

### Step 5: Maps and Location
```bash
npm install leaflet react-leaflet date-fns
```

### Step 6: Development Tools
```bash
npm install --save-dev @types/react @types/react-dom @types/leaflet @vitejs/plugin-react typescript vite
```

### Step 7: Styling (Critical for PostCSS fix)
```bash
npm install --save-dev tailwindcss @tailwindcss/postcss postcss autoprefixer
```

### Step 8: Code Quality
```bash
npm install --save-dev eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser eslint-plugin-react eslint-plugin-react-hooks eslint-plugin-react-refresh prettier
```

### Step 9: Testing
```bash
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom cypress @types/testing-library__jest-dom
```

## ⚡ Quick Fix Commands

### Clear Cache and Reinstall
```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Fix PostCSS Tailwind Issue
```bash
npm install --save-dev @tailwindcss/postcss
```

### Start Development Server
```bash
npm run dev
```

## 🐛 Common Issues and Solutions

### Issue 1: PostCSS Tailwind Error
**Problem**: `[postcss] It looks like you're trying to use tailwindcss directly as a PostCSS plugin`
**Solution**: 
1. Install: `npm install --save-dev @tailwindcss/postcss`
2. Update `postcss.config.cjs` to use `'@tailwindcss/postcss': {}`

### Issue 2: Network Timeout
**Problem**: `npm ERR! code ECONNRESET`
**Solutions**:
1. Use different registry: `npm config set registry https://registry.npmmirror.com/`
2. Increase timeout: `npm config set fetch-timeout 60000`
3. Use yarn: `npm install -g yarn && yarn install`

### Issue 3: Module Not Found
**Problem**: `Cannot find module 'react-redux'`
**Solution**: Install missing dependencies step by step

### Issue 4: File Locking (Windows)
**Problem**: `EBUSY: resource busy or locked`
**Solution**: 
1. Close all terminals and VS Code
2. Delete `node_modules` manually
3. Restart and reinstall

## 📁 Project Structure Verification

After installation, verify these files exist:
- ✅ `node_modules/` (should have ~100+ packages)
- ✅ `package-lock.json` (dependency lock file)
- ✅ `postcss.config.cjs` (uses `@tailwindcss/postcss`)
- ✅ `tailwind.config.js` (Tailwind configuration)
- ✅ `vite.config.ts` (Vite build configuration)

## 🎯 Final Verification

Run these commands to verify everything works:
```bash
# Check if all dependencies are installed
npm list --depth=0

# Start development server (should work without errors)
npm run dev

# Build for production (should complete successfully)
npm run build

# Run linting (should pass)
npm run lint

# Run tests (should pass)
npm test
```

## 📞 Support

If you encounter issues:
1. Check Node.js version: `node --version` (should be 18+)
2. Check npm version: `npm --version` (should be 9+)
3. Clear npm cache: `npm cache clean --force`
4. Try alternative registries if network issues persist

## ⚙️ Environment Requirements

- **Node.js**: v18.0.0 or higher
- **npm**: v9.0.0 or higher  
- **Operating System**: Windows 10+, macOS 10.15+, Linux Ubuntu 18.04+
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB free space for node_modules

---

*This guide ensures a consistent, error-free setup for the Travel Planner web application.*
