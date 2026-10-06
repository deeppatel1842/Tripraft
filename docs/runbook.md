# Development and operations

## Install and run

Use Node 22, pnpm 10.34.6, and Python 3.11. `pnpm install --frozen-lockfile` installs
the JavaScript workspace. Create an isolated Python environment and install
`services/api/requirements.txt` and `services/api/requirements-dev.txt`.
The root `start.py` automates one-time setup and starts the whole project; see
[startup](startup.md). The optional backend-only PowerShell helper creates `.venv`.

From `services/api`, run `alembic upgrade head`, then `python run.py`.
From the repository root, `pnpm dev` starts web (5173) and admin (5174); their
development proxies forward `/api` to localhost:5000. A local SQLite database is
used by default. Set `REDIS_URL` to a running instance, or empty it for development
without cache/worker support. Use `ADMIN_EMAILS` to configure server admin accounts.
Do not embed personal allowlists in frontend source.

For PostgreSQL and Redis:

```sh
docker compose -f infra/docker/docker-compose.yml up --build
docker compose -f infra/docker/docker-compose.yml --profile workers up --build
```

The API waits for healthy PostgreSQL and Redis, applies migrations, then starts
Gunicorn. One local Gunicorn worker supports Socket.IO; multiple workers require
deployment routing/sticky-session validation. Development secrets in Compose are
for local use. Configure real secrets and production settings before deployment.

## Verification and release

`pnpm verify` runs structure validation, syntax lint, Python 3.11 syntax checks,
strict TypeScript checks for entry points/shared packages/admin, tests, and builds.
`pnpm format:check` checks workspace configuration formatting. The JavaScript
modules have syntax lint and regression coverage; they are not fully typechecked.

Update canonical CI/deployment workflows under `infra/github/workflows`, then
`pnpm workflows:sync`. Set the GitHub repository variable `DEPLOY_HOOKS_ENABLED=true` to enable
deployment after configuring staging/production environments and their
`STAGING_DEPLOY_HOOK`/`PRODUCTION_DEPLOY_HOOK` secrets. Main pushes trigger staging;
`v*` tags trigger production after verification. Configure production environment
reviewers if approval is required. Hooks must deploy the selected revision from the
connected repository; no provider is provisioned here. Missing hooks fail clearly.
The workflow was checked locally, but hosted CI and real deployments require the
repository's remote setup. Docker was unavailable during the reorganization, so
the Compose topology was validated statically rather than run locally.

## Back up and restore

Back up PostgreSQL with `pg_dump` or the provider's snapshot tooling before schema
changes. With SQLite, stop writers and back up `data/runtime/tripraft.db` and
associated WAL data together. Preserve uploaded files separately. The travel
catalog is reference data, not the private expense/group database. Docker named
volumes contain persistent database and uploads; removing those volumes erases
data and is not part of routine shutdown.

Local archived files and earlier Smartlog checkpoints are preserved on the
development machine. They are not included in the published source tree. The
current file responsibilities are documented in [files.md](files.md).
