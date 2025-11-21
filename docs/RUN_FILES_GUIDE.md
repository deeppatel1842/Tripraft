# Run Files Guide

**TripRaft Project - Run Files Reference**  
**Date:** November 17, 2025

---

## 🎯 Which Run File Are You Using?

### ✅ **ACTIVE: `web/backend/run.py`**

**This is the file currently running your Flask application.**

**Evidence:**
- Terminal shows: `python run.py` from `C:\Users\Kashyap\Documents\Deep\Travel\web\backend`
- Editor has `web/backend/run.py` open
- This is the CORRECT and RECOMMENDED file

---

## 📁 All Run Files in Project

### 1. `web/backend/run.py` ✅ **USE THIS**

**Purpose:** Main entry point for Flask web application

**Features:**
```python
✅ Unbuffered output for real-time logs
✅ Windows Unicode encoding fixes
✅ Proper path configuration
✅ Comprehensive startup logging
✅ Configurable host/port via environment
```

**How to Run:**
```bash
cd web\backend
python run.py
```

**What It Does:**
1. Disables Python output buffering for real-time terminal logs
2. Fixes Windows PowerShell encoding issues (cp1252 → UTF-8)
3. Adds backend directory to Python path
4. Imports Flask app from `api.app.create_app()`
5. Starts server on configured host/port

**Configuration:**
- `FLASK_HOST` (default: 127.0.0.1)
- `FLASK_PORT` (default: 5000)
- `FLASK_ENV` (development/production)

---

### 2. `web/backend/api/run.py` ❌ **DELETE THIS**

**Status:** REDUNDANT - Older version, less features

**Why Not Use This:**
- ❌ No output buffering configuration
- ❌ No Windows encoding fixes
- ❌ Less detailed startup logging
- ❌ Duplicate of main run.py

**Recommendation:** **DELETE** this file

```bash
# Safe to delete
Remove-Item "web\backend\api\run.py"
```

---

### 3. `database_pipeline/run_pipeline.py` 🔧 **UTILITY**

**Purpose:** Data processing pipeline (NOT for running the web app)

**What It Does:**
- Processes JSON files in places database
- Fills missing coordinates and addresses
- Calculates ranking scores for places
- Fetches and attaches photos from Google Places API

**How to Run:**
```bash
# Dry run (preview only)
python database_pipeline\run_pipeline.py --dry-run

# Full processing with writes
python database_pipeline\run_pipeline.py --database-dir web\backend\world_database --write
```

**When to Use:**
- Updating the places database
- Processing new location data
- Enriching place information
- **NOT for running the web application**

---

## 🚀 Quick Start Guide

### Running the Web Application

```bash
# 1. Activate virtual environment
cd C:\Users\Kashyap\Documents\Deep\Travel
.\wayfinder\Scripts\Activate.ps1

# 2. Start backend (Flask API)
cd web\backend
python run.py

# 3. In another terminal, start frontend
cd web\frontend
npm run dev

# 4. Access application
# Frontend: http://localhost:5173
# Backend API: http://localhost:5000
```

---

## 📝 Run File Comparison

| Feature | web/backend/run.py | api/run.py | run_pipeline.py |
|---------|-------------------|------------|-----------------|
| **Purpose** | Main app server | Duplicate | Data pipeline |
| **Buffering Config** | ✅ Yes | ❌ No | N/A |
| **Windows Fixes** | ✅ Yes | ❌ No | N/A |
| **Startup Logs** | ✅ Detailed | ⚠️ Basic | ✅ Pipeline info |
| **Use for Web App** | ✅ **YES** | ❌ NO | ❌ NO |
| **Keep?** | ✅ **YES** | ❌ DELETE | ✅ YES |

---

## 🔧 Troubleshooting

### "Which run.py should I use?"
**Answer:** Always use `web/backend/run.py`

### "I see two run.py files in backend"
**Answer:** 
- `web/backend/run.py` ← Use this ✅
- `web/backend/api/run.py` ← Delete this ❌

### "Can I delete api/run.py?"
**Answer:** Yes, it's safe to delete. It's redundant.

### "What about run_pipeline.py?"
**Answer:** Keep it, but it's NOT for running the web app. It's for data processing.

---

## 📊 File Structure

```
web/backend/
├── run.py                    ✅ MAIN - Use this for web app
├── api/
│   ├── run.py               ❌ DUPLICATE - Delete this
│   ├── app.py               ✅ Flask app factory (imported by run.py)
│   └── ...

database_pipeline/
└── run_pipeline.py          🔧 UTILITY - For data processing only
```

---

## ⚡ Best Practices

### Starting the Server
```bash
# ✅ CORRECT
cd web\backend
python run.py

# ❌ WRONG
cd web\backend\api
python run.py
```

### Environment Variables
Create `.env` in `web/backend/`:
```env
FLASK_ENV=development
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=True
```

### Multiple Instances
```bash
# Backend (Terminal 1)
cd web\backend
python run.py

# Frontend (Terminal 2)
cd web\frontend
npm run dev

# Don't run api/run.py - it's the same thing!
```

---

## 🎯 Summary

**For Web Application:**
- **Use:** `web/backend/run.py` ✅
- **Don't use:** `web/backend/api/run.py` ❌
- **Delete:** `web/backend/api/run.py` (safe to remove)

**For Data Processing:**
- **Use:** `database_pipeline/run_pipeline.py` 🔧

**Currently Active:**
- Your terminal is running `web/backend/run.py` ✅ (Correct!)

---

## 📞 Quick Reference

| Task | Command | File |
|------|---------|------|
| Start web app | `python run.py` | `web/backend/run.py` |
| Process database | `python run_pipeline.py --write` | `database_pipeline/run_pipeline.py` |
| Check health | `curl http://localhost:5000/health` | - |

---

*Run Files Guide - Part of TripRaft Documentation*
