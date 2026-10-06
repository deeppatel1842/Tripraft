# API contracts

Flask API URLs remain `/api/v1/*`; health probes remain `/api/health/live` and
`/api/health/ready`. Domain source directories do not add or change URL prefixes.
The OpenAPI route inventory is `services/api/openapi.json`; generated TypeScript
declarations are `packages/api-client/src/generated/schema.d.ts`.

Regenerate after route changes:

```sh
python infra/tools/export_openapi.py
pnpm api:generate
```

The exporter applies Alembic migrations to a disposable database under ignored
`extra/build/schema-export` and never uses personal application data. Paths and
methods come from the registered Flask routes. Explicit response contracts cover
authenticated account identity, service health, and admin ingestion audit data.
Other response payloads are deliberately `unknown`, not invented schemas. This
is a usable typed admin client and route inventory; full request/response schema
coverage remains future work.

Most application responses wrap payloads in `{ success, data, message?, meta? }`.
Health probes return plain JSON. Account identity returns `data.user`; admin audit
returns `data.total` and `data.logs`. A 503 readiness response reports degraded
database status. UUID identifiers remain strings.

`createApiClient(baseUrl)` from `@tripraft/api-client` sends `credentials: include`.
For admin, `baseUrl` is the API origin (or empty for the local proxy); generated
paths already include `/api`. The existing web client’s configured base includes
`/api`, as documented in `apps/web/.env.example`.
For mutations it echoes `csrf_token` into `X-CSRF-Token`. Existing web services use
their tested cookie-authenticated client; money and chat POST requests are not
automatically retried. The console's admin flag is only a UI gate; backend admin
decorators remain the security boundary.
