# Wayfinder Frontend

A modern, secure React.js travel planning application built with Vite.

## 🚀 Quick Start

### Prerequisites
- Node.js v18.17.0 or higher
- npm v9.6.7 or higher

### Installation

```bash
cd web/frontend
npm install
```

### Development

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## 📁 Project Structure

```
web/frontend/
├── src/
│   ├── components/
│   │   ├── layout/          # Layout components (Header, Footer)
│   │   │   ├── Header.jsx
│   │   │   └── Footer.jsx
│   │   ├── page/            # Page components
│   │   │   ├── HomePage.jsx       # Main landing page
│   │   │   ├── LoginPage.jsx      # Authentication
│   │   │   ├── Dashboard.jsx      # User dashboard
│   │   │   ├── FlightsPage.jsx    # Flight search
│   │   │   ├── HotelSearch.jsx    # Hotel search
│   │   │   ├── PlaceSearchPage.jsx # Places explorer
│   │   │   ├── AuthContext.jsx    # Authentication context
│   │   │   ├── ProtectedRoute.jsx # Route protection
│   │   │   └── Logo.jsx           # Logo component
│   │   └── css/             # Component-specific styles
│   │       ├── Header.css
│   │       ├── Footer.css
│   │       └── HomePage.css
│   ├── firebase/
│   │   └── authService.js   # Firebase authentication
│   ├── config/              # Configuration files
│   ├── assets/              # Images, fonts, etc.
│   ├── App.jsx              # Main app component
│   ├── main.jsx             # Application entry point
│   └── styles.css           # Global styles
├── index.html               # HTML template
├── package.json             # Dependencies
├── vite.config.js           # Vite configuration
└── .env.local               # Environment variables (not in git)
```

## 🎨 Tech Stack

- **React.js 18.2.0** - UI framework
- **React Router 7.9.1** - Client-side routing
- **Vite 5.0.0** - Build tool & dev server
- **Firebase 10.4.0** - Authentication & backend services
- **Font Awesome 6.4.0** - Icons
- **Google Fonts (Inter)** - Typography

## 🔐 Security Features

### Authentication
- Firebase Authentication integration
- Protected routes with authentication checks
- Secure token management
- Session persistence

### Data Protection
- Environment variables for sensitive data
- XSS protection via React
- CORS configuration
- HTTPS enforcement in production

### Best Practices
- No hardcoded credentials
- Input validation
- Secure HTTP headers
- Content Security Policy

## 🔧 Configuration

### Environment Variables

Create a `.env.local` file in the `web/frontend` directory:

```env
VITE_FIREBASE_API_KEY=your-firebase-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-app.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-app.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
VITE_FIREBASE_APP_ID=your-app-id
VITE_API_URL=http://localhost:5000
```

### Vite Configuration

The `vite.config.js` includes:
- React plugin for fast refresh
- Proxy configuration for API calls
- Port 5173 for development server

```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000/',
        changeOrigin: true,
      },
    },
  },
})
```

## 📱 Features

### Home Page
- Hero section with search
- Features showcase
- AI Trip Planner preview
- Group Trip collaboration
- Expense Management
- Pricing plans
- Contact section

### Authentication
- Email/Password login
- Google Sign-In
- Protected routes
- Session management

### User Dashboard
- Personalized experience
- Trip management
- Profile settings

### Navigation
- Responsive header
- Dynamic navigation based on auth state
- Smooth scrolling
- Mobile-friendly menu

## 🎯 Component Architecture

### Layout Components
- **Header**: Global navigation with authentication state
- **Footer**: Site-wide footer with links and social media

### Page Components
- **HomePage**: Main landing page with all sections
- **LoginPage**: Authentication interface
- **Dashboard**: User's personalized dashboard
- **Protected Pages**: Require authentication

### Context Providers
- **AuthContext**: Global authentication state management

## 🌐 Routing

```javascript
/ - Home page (public)
/login - Login page (public)
/signup - Signup page (public)
/dashboard - User dashboard (protected)
/flights - Flight search (public)
/hotels - Hotel search (public)
/placesearch - Places explorer (public)
```

## 🎨 Styling

### Global Styles
- Inter font family
- Font Awesome icons
- CSS custom properties for theming
- Responsive design

### Component Styles
- Separate CSS files for each component
- Modular and maintainable
- Mobile-first approach

### Color Palette
- Primary: `#7c3aed` (Violet)
- Background: `#f8fafc` (Light Gray)
- Text: `#1e293b` (Dark Gray)
- Accents: Various shades of gray and violet

## 🔄 State Management

### Authentication State
- Managed via `AuthContext`
- Accessible throughout the app
- Automatic persistence

### Route Protection
- `ProtectedRoute` component
- Redirects unauthenticated users
- Preserves intended destination

## 🚀 Deployment

### Build Process
1. Run `npm run build`
2. Output in `dist/` directory
3. Upload to your hosting service

### Hosting Options
- Vercel
- Netlify
- Firebase Hosting
- AWS Amplify

### Environment Setup
- Set production environment variables
- Configure HTTPS
- Update CORS settings
- Set proper API endpoints

## 📊 Performance

### Optimizations
- Code splitting
- Lazy loading routes
- Image optimization
- CSS minification
- Tree shaking

### Vite Benefits
- Lightning-fast HMR (Hot Module Replacement)
- Optimized build output
- Native ES modules
- Built-in TypeScript support

## 🐛 Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Change port in vite.config.js or use:
npm run dev -- --port 3000
```

**Module not found:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Build errors:**
```bash
# Check Node version
node --version  # Should be 18.17.0 or higher
```

## 📚 Additional Resources

- [React Documentation](https://react.dev)
- [Vite Documentation](https://vitejs.dev)
- [React Router Documentation](https://reactrouter.com)
- [Firebase Documentation](https://firebase.google.com/docs)

## 🤝 Contributing

1. Follow the existing code structure
2. Use meaningful component and variable names
3. Add comments for complex logic
4. Test thoroughly before submitting
5. Update documentation as needed

## 📄 License

This project is part of the Wayfinder travel planning platform.

---

**Built with ❤️ using React.js and Vite**
