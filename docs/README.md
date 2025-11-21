# TripRaft Documentation Index

**Last Updated:** November 17, 2025

Welcome to the TripRaft project documentation! This folder contains all organized documentation for the travel planning platform.

---

## 📚 Documentation Structure

```
docs/
├── PROJECT_ANALYSIS.md           # Comprehensive project analysis
├── README.md                     # This file
├── database_pipeline/            # Database pipeline documentation
│   ├── DATABASE_PIPELINE_README.md
│   ├── PIPELINE_GUIDE.md
│   └── DEMO_RESULTS.md
└── modules/                      # Module-specific documentation
    ├── API_README.md
    ├── FRONTEND_README.md
    ├── EXPENSE_ENGINE_README.md
    ├── EXPENSE_DATABASE_README.md
    ├── SCRIPTS_README.md
    ├── IMAGES_README.md
    └── ANIMATION_IMAGES.md
```

---

## 📖 Quick Links

### **Core Documentation**
- [Project Analysis](./PROJECT_ANALYSIS.md) - Full project structure, duplicates, and recommendations

### **Database Pipeline**
- [Database Pipeline README](./database_pipeline/DATABASE_PIPELINE_README.md) - Overview of the data processing pipeline
- [Pipeline Guide](./database_pipeline/PIPELINE_GUIDE.md) - Step-by-step guide for running the pipeline
- [Demo Results](./database_pipeline/DEMO_RESULTS.md) - Example outputs and results

### **Web Application Modules**
- [API README](./modules/API_README.md) - Places API documentation
- [Frontend README](./modules/FRONTEND_README.md) - React frontend documentation
- [Expense Engine README](./modules/EXPENSE_ENGINE_README.md) - Expense management system
- [Expense Database README](./modules/EXPENSE_DATABASE_README.md) - Expense database structure
- [Scripts README](./modules/SCRIPTS_README.md) - Utility scripts documentation
- [Images README](./modules/IMAGES_README.md) - Frontend images documentation
- [Animation Images](./modules/ANIMATION_IMAGES.md) - Animation assets documentation

---

## 🚀 Quick Start

### Running the Main Application

```bash
# Activate virtual environment
cd c:\Users\Kashyap\Documents\Deep\Travel
.\wayfinder\Scripts\Activate.ps1

# Start backend server
cd web\backend
python run.py

# In another terminal, start frontend
cd web\frontend
npm run dev
```

### Running the Database Pipeline

```bash
# Process database files
python database_pipeline\run_pipeline.py --database-dir web\backend\world_database --write
```

---

## 📁 Project Overview

**TripRaft** is a dynamic, scalable AI-powered travel planning platform with:

- **Frontend:** React.js with Vite
- **Backend:** Python/Flask with Redis caching
- **Database:** SQLite + Firestore (Firebase)
- **Authentication:** Firebase Auth
- **Features:**
  - Places Explorer with AI-powered recommendations
  - Group Trip Planning
  - Expense Management & Split Bills
  - Real-time collaboration

---

## 🔑 Key Files

### Main Entry Points
- `web/backend/run.py` - **Main application server** ✅
- `database_pipeline/run_pipeline.py` - Data processing utility

### Configuration
- `web/backend/config.py` - Global backend configuration
- `web/backend/api/config/settings.py` - API-specific settings
- `.env` - Environment variables (not in repo)

### Documentation (in this folder)
- All `.md` files have been organized here for easy access

---

## 🛠️ Development Guidelines

### Before Making Changes
1. Read the relevant module documentation
2. Check [Project Analysis](./PROJECT_ANALYSIS.md) for duplicate files
3. Follow the coding standards in `.github/instructions/intro.instructions.md`

### Code Style
- **Frontend:** React.js (no emojis, clean code)
- **Backend:** Python/Flask (clean, well-structured)
- **No messy code generation** - Follow project patterns

---

## 📊 Project Status

### Active Components
- ✅ Places API (fully functional)
- ✅ Frontend (React + Vite)
- ✅ Expense Management System
- ✅ Group Planner
- ✅ Firebase Integration
- ✅ Redis Caching

### Known Issues & Improvements
See [Project Analysis](./PROJECT_ANALYSIS.md) for:
- Duplicate files to remove
- Email service consolidation
- Configuration optimization

---

## 🤝 Contributing

1. Read relevant documentation before changes
2. Test locally before committing
3. Update documentation if adding features
4. Follow the existing code patterns

---

## 📞 Support

For questions or issues:
1. Check the relevant module documentation
2. Review [Project Analysis](./PROJECT_ANALYSIS.md)
3. Check the main [README](../README.md) in the root

---

*This documentation is maintained as part of the TripRaft project.*
