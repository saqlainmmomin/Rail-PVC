# Seed scripts

Scripts to load reference index data and a full end-to-end demo contract into
the database. Both read `DATABASE_URL` from `backend/.env` and connect with the
same asyncpg pattern, so they can be run from the repo root with a bare
`uv run` — they auto re-exec under the backend project environment.

## Prerequisites

- A valid `backend/.env` with a working `DATABASE_URL` (Supabase pooler URL).
  If the password contains special characters, URL-encode them (e.g. `@` → `%40`).
- Your tenant must already exist (it is created the first time you log in).

## Run order

Indices are global (not tenant-scoped) and must exist before the demo contract,
which validates that the index months it needs are present.

```bash
# 1. Reference index data (RBI + JPC steel). Idempotent.
uv run python seeds/seed_indices.py

# 2. Demo contract BCT-24-25-252 with two running bills. Idempotent.
uv run python seeds/seed_demo_contract.py
```

Both scripts are safe to re-run: existing rows are detected by their natural
keys and skipped, so no duplicates are created.

## Targeting your own tenant

`seed_demo_contract.py` writes to the tenant in `SEED_TENANT_ID`, defaulting to
the shared dev tenant. Because of tenant isolation you only see contracts in
**your** tenant, so seed into the tenant your login resolves to:

```bash
SEED_TENANT_ID=<your-tenant-uuid> uv run python seeds/seed_demo_contract.py
```

Find your tenant uuid by email:

```bash
uv --project backend run python -c "
import os, asyncio, asyncpg
from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url
load_dotenv('backend/.env', override=True)
u = make_url(os.environ['DATABASE_URL'].strip())
async def go():
    c = await asyncpg.connect(host=u.host, port=u.port, user=u.username,
                              password=str(u.password), database=u.database)
    for r in await c.fetch(\"select tenant_id::text, email from users where email=\$1\",
                           'you@example.com'):
        print(r['email'], '->', r['tenant_id'])
    await c.close()
asyncio.run(go())
"
```

After seeding, refresh the app and open the contract from the run summary:
`/contracts/<contract_id>/bills`.

## Troubleshooting

- **`password authentication failed`** — the `DATABASE_URL` password in
  `backend/.env` is stale or not URL-encoded. Refresh it from the Supabase
  dashboard (Project Settings → Database) and encode special characters.
- **`Missing required index observations`** — run `seed_indices.py` first.
- **`Tenant <uuid> not found`** — log into the app once to create your tenant,
  or pass a `SEED_TENANT_ID` that exists.
- **Seed succeeds but you can't see the contract** — you seeded a different
  tenant than the one your login uses. Re-run with the correct `SEED_TENANT_ID`.
