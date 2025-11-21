# 🚀 Database Pipeline Quick Start

**Goal**: Get your database up and running in 30 minutes!

---

## 📁 File Structure Created

```
database_pipeline/
├── schema/
│   └── (Put SQL schema files here)
├── scripts/
│   └── (Put Python migration scripts here)
├── auth/
│   └── (Put admin authentication code here)
├── api/
│   └── (Put Flask API code here)
└── README.md (this file)
```

---

## ⚡ Quick Start (30 Minutes)

### Step 1: Install Dependencies (5 min)

```powershell
# Install PostgreSQL
# Download from: https://www.postgresql.org/download/windows/
# During install, remember the password you set!

# Install Python dependencies
pip install Flask Flask-CORS psycopg2-binary redis python-dotenv PyJWT bcrypt gunicorn
```

### Step 2: Create .env File (2 min)

Create `.env` in the `database_pipeline/` folder:

```bash
# Local Development
DB_NAME=tripraft
DB_USER=postgres
DB_PASSWORD=your-password-here
DB_HOST=localhost
DB_PORT=5432

# Redis (Upstash) - Sign up at upstash.com
REDIS_URL=rediss://default:your-password@your-db.upstash.io:6379

# Admin Auth
JWT_SECRET_KEY=change-this-to-a-long-random-string-min-32-characters
JWT_EXPIRY_HOURS=24

# Flask
FLASK_ENV=development
SECRET_KEY=another-random-string
```

### Step 3: Set Up Database (5 min)

```powershell
# Open PowerShell in database_pipeline folder
cd database_pipeline

# Create database
python scripts/setup_database.py

# Create first admin user
python scripts/create_admin.py
# Enter username: admin
# Enter email: your@email.com
# Enter password: (your secure password)
```

### Step 4: Migrate Your First Country (10 min)

```powershell
# Test with one country first (Argentina)
python scripts/migrate_single_country.py ../web/backend/world_database_2/argentina.json

# Check results
python scripts/check_database.py
```

### Step 5: Start API Server (5 min)

```powershell
# Start Flask API
python app.py

# API will run at: http://localhost:5000
```

### Step 6: Test It! (3 min)

Open another PowerShell window:

```powershell
# Test health check
curl http://localhost:5000/api/v1/health

# Test search (should return Argentina places)
curl "http://localhost:5000/api/v1/search?q=bariloche"

# Test admin login
curl -X POST http://localhost:5000/api/v1/admin/login `
  -H "Content-Type: application/json" `
  -d '{"username":"admin","password":"your-password"}'
```

---

## 🎯 Next Steps

### Migrate All Countries

```powershell
# Migrate all JSON files
python scripts/migrate_all_countries.py
```

### Deploy to Production

See `DATABASE_PIPELINE_PLAN.md` for full deployment guide to Railway!

---

## 📚 File References

All detailed code is in: `DATABASE_PIPELINE_PLAN.md`

Sections include:
1. Complete PostgreSQL schema
2. Migration scripts
3. Admin authentication
4. Public API endpoints
5. Deployment guides

---

## 🆘 Troubleshooting

**"psycopg2 error"**
→ Make sure PostgreSQL is installed and running

**"Connection refused"**
→ Check DB_PASSWORD in .env matches your PostgreSQL password

**"No module named 'flask'"**
→ Run: `pip install -r requirements.txt`

**"Table already exists"**
→ Normal if running setup twice. Safe to ignore.

---

## 💡 What's Happening?

1. **PostgreSQL** stores your places data (fast queries)
2. **Redis** caches API responses (10x faster)
3. **Flask API** serves data to your frontend
4. **Admin dashboard** lets you upload new data securely

---

## 🎉 Success Criteria

After following the quick start, you should have:

✅ PostgreSQL database with Argentina places
✅ Admin user created
✅ API running on localhost:5000
✅ Search working
✅ Ready to migrate more countries!

---

Need help? Check the full plan in `DATABASE_PIPELINE_PLAN.md`!
