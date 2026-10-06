# TripRaft

React trip planning and expense sharing, backed by Flask, PostgreSQL/SQLite, Redis,
and optional Celery workers.

## Workspace

```text
apps/web/              React application: pages, features, components, hooks
apps/admin/            Account-gated service health and ingestion audit console
services/api/          Flask domains, migrations, tests, Dockerfile, requirements
packages/ui/           Shared React components
packages/api-client/   OpenAPI-generated declarations and cookie-auth client
packages/types/        Shared TypeScript contracts
packages/config/       ESLint, TypeScript, Prettier presets
data/catalog/          Preserved reference travel catalog
data/runtime/          Private local SQLite data (ignored)
data/seeds/            Reviewed SQL seeds when supplied
infra/docker/          Local API + PostgreSQL + Redis, optional worker
infra/github/          Canonical CI and deployment workflows
infra/terraform/       Provisioning reservation; provider not selected
infra/tools/           Workspace verification and generation tools
docs/                  Architecture, API, runbook, assessment
```

GitHub requires workflows under `.github/workflows`; synchronized discovery copies
live there. Edit `infra/github/workflows` and run `pnpm workflows:sync`.

## One-time setup and start

Install Node.js 22 or newer and Python 3.11, then run:

```sh
python start.py --setup
python start.py
```

The single launcher installs local dependencies once, starts API/web/admin, waits
for readiness, and opens http://localhost:5173. Admin is on port 5174. Ctrl+C stops
the services it launched. First launch also sets up automatically if needed.
`python start.py --docker` uses PostgreSQL/Redis/API/worker in Docker instead.
See [startup](docs/startup.md) for prerequisites, preserved data and integrations,
and [the runbook](docs/runbook.md) for backups and releases.

## Verify

`pnpm verify` checks structure, syntax lint, TypeScript entry points/contracts,
backend/frontend regressions, and both production frontend builds. Python must
have the development dependencies installed. `pnpm api:generate` regenerates the
client declarations; export registered routes first with
`python infra/tools/export_openapi.py`.

The existing web modules remain JavaScript. TypeScript checks the new entry points
and shared contracts; it does not certify the entire legacy JavaScript application.
See [architecture](docs/architecture.md), [API coverage](docs/api.md), and the
[complete file-purpose guide](docs/files.md). Source files have purpose comments;
strict JSON, generated contracts and binary assets are explained in the guide.

Only source, required configuration, tests, documentation and the reference travel
catalog are published. `extra/`, local settings/secrets, `.venv`, `.tripraft`, private
databases, uploads, dependencies, logs and build output remain local and ignored.
