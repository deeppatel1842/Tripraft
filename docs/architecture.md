# Architecture

The pnpm workspace has two Vite React applications, four shared packages, and a
Python API package with Turbo commands. `apps/web` consumes shared UI; `apps/admin`
consumes the generated API client and shared types. Shared configuration sets a
common syntax lint baseline, strict TypeScript settings, and formatting defaults.

Web pages compose feature modules under `src/features`. Expense, itinerary,
discovery, authentication, and trip workspace components retain their proven
JavaScript behavior. Scout/Crew cards and bot identities live in `features/scout`;
the poll feed lives in `features/polls`, with lifecycle state in the trip chat.
Common navigation stays in `components`; query hooks,
services, and cache utilities retain their stable responsibilities. `main.tsx`
is the typed entry point. Shared Toast code and styles live in `packages/ui`.

The Flask application factory is `app.core.factory:create_app()`. Each domain has
routes and services: trips, itinerary, expenses, places, scout, auth, and
notifications. Core contains configuration, database routing, cache, middleware,
shared schemas, workers, and external integrations. Domain models retain existing
SQLAlchemy relationships. The trip aggregate includes itinerary/poll/chat entities.
The unified User model lives under auth and is re-exported by expenses for compatibility. Splitting those
models needs a separate migration design; moving source files changes no table,
Alembic revision ID, or API URL.

Application data defaults to ignored `data/runtime/tripraft.db`. The reference
catalog remains `data/catalog/travel_data_complete.db`. Docker uses PostgreSQL for
application data and mounts the seed catalog read-only. At first startup the seed
is copied into a separate writable catalog volume, allowing ingestion without
changing the shipped reference dataset. Uploaded files have a separate volume.

Authentication uses httpOnly cookies and readable double-submit CSRF tokens.
The generated client includes cookie credentials and mutation CSRF headers, with
no automatic mutation replay. Admin endpoints enforce authorization on the server;
the UI waits for `/api/v1/auth/me` and displays the console only for `is_admin`.

Canonical workflows live in `infra/github/workflows`, with byte-identical copies
under `.github/workflows` for GitHub discovery. CI verifies the workspace and
regenerates the OpenAPI declarations. Deployment runs verification, then calls a
configured environment hook. Terraform provisioning is reserved until a hosting
provider and operational requirements are selected.

Native startup is managed by the root `start.py` launcher. It creates ignored
local settings and a separate development database, preserving legacy local data.
Only source and required development/operational files are published. Historical
archives and local Smartlog checkpoints remain on the development machine outside
the published tree. [The file guide](files.md) explains every published file.

Tooling references: [pnpm workspaces](https://pnpm.io/workspaces),
[Turbo tasks](https://turborepo.dev/docs/crafting-your-repository/configuring-tasks),
and [OpenAPI TypeScript generation](https://openapi-ts.dev/cli).
