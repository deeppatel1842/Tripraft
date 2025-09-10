#!/bin/bash
# Travel Planner - One Command Installation Script

echo "🚀 Installing Travel Planner Dependencies..."

# Single command to install ALL dependencies
npm install react@18.2.0 react-dom@18.2.0 react-router-dom@6.8.1 react-redux@9.1.0 @reduxjs/toolkit@2.2.1 react-hot-toast@2.4.1 firebase@10.8.0 leaflet@1.9.4 react-leaflet@4.2.1 date-fns@3.3.1 @types/react@18.2.43 @types/react-dom@18.2.17 @types/leaflet@1.9.8 @vitejs/plugin-react@4.2.1 typescript@5.2.2 vite@5.0.8 tailwindcss@3.4.1 @tailwindcss/postcss@7.0.39 postcss@8.4.35 autoprefixer@10.4.17 eslint@8.57.0 @typescript-eslint/eslint-plugin@7.0.2 @typescript-eslint/parser@7.0.2 eslint-plugin-react@7.33.2 eslint-plugin-react-hooks@4.6.0 eslint-plugin-react-refresh@0.4.5 prettier@3.2.5 vitest@1.3.0 @testing-library/react@14.2.1 @testing-library/jest-dom@6.4.2 @testing-library/user-event@14.5.2 jsdom@24.0.0 cypress@13.6.6 @types/testing-library__jest-dom@6.0.0

if [ $? -eq 0 ]; then
    echo "✅ All dependencies installed successfully!"
    echo "🎯 You can now run: npm run dev"
else
    echo "❌ Installation failed. Try step-by-step installation."
fi
