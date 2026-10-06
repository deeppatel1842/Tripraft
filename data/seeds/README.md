# Seed data

The existing read-only travel catalog is preserved in `../catalog/travel_data_complete.db`.
This directory is for reviewed state seed SQL files when supplied. No fabricated seed
records are loaded. Schema migrations live in `services/api/migrations`; personal
application data belongs in the ignored `data/runtime` directory or PostgreSQL.
