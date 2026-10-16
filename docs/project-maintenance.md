# Project Maintenance and Local Artifacts

Reviewed: **2026-10-16**. This document records repository organization and
local cleanup. It does not authorize a database operation or deployment.

## Maintained layout

| Path | Purpose |
| --- | --- |
| `app/` | Application code and runtime contracts |
| `alembic/` | Production migration history |
| `alembic_test/` | Separate, guarded test migration history |
| `scripts/` | Maintained operational tools and the PowerShell module |
| `tests/` | Automated tests, including isolated PowerShell checks |
| `docs/` | Maintained English documentation |
| `artifacts/` | Generated reports, source exports, and archived evidence |

Keep application code, migrations, and tests in their existing packages.
Cleaning generated output does not justify moving business modules, changing
imports, resetting databases, or discarding uncommitted work.

## Generated output and caches

Use these local destinations:

| Path | Contents |
| --- | --- |
| `artifacts/README.md` | Central index of local evidence |
| `artifacts/test-logs/` | Console captures and diagnostic snapshots |
| `artifacts/billing-reports/` | Standalone UTF-8 billing JSON reports |
| `artifacts/billing-production-review/` | Python exports and billing evidence |
| `artifacts/powershell-review/` | PowerShell source exports and verification |
| `artifacts/dependency-review/` | Dependency metadata and results |
| `artifacts/project-cleanup/` | Cleanup manifests and archived retired files |

These directories are excluded from Git and Docker. Logs and captured output
belong under `artifacts/test-logs/`, rather than the repository root. Billing
`preflight` and `constraint-diagnostics` accept `--output FILENAME.json` to
write a single JSON document under `artifacts/billing-reports/`. Console output
can include logger records and must not be treated as a JSON report.

Python bytecode and tool caches are disposable generated files. Recreate them
through the relevant tool when needed. Preserve reports, diagnostic captures,
source archives, manifests, and resolved dependency inventories when removing
caches. Ignore rules prevent new additions; they do not remove tracked files
or erase earlier versions from Git history.

The main `.venv`, the separate root `venv`, and local `.env` are preserved.
The temporary `artifacts/dependency-review/venv` and downloaded `wheels`
directory used by the dependency review are disposable. Their cleanup retains
the installation report, resolved versions, test results, and wheel hash
inventory. The recorded checks remain historical evidence; the temporary
environment is no longer an available test runner.

## Retired entry points

The following files were removed from active project paths after their original
bytes were archived. The archive preserves evidence, not supported commands.

| Retired path | Reason |
| --- | --- |
| `test_db.py` | Legacy root diagnostic outside the maintained test suite |
| `scripts/check_test_db.py` | Unguarded primary database creation |
| `scripts/create_test_tables_sync.py` | Table reset at import |
| `scripts/run_migrations.py` | Unguarded shell migration wrapper |
| `.github/workflows/python-publish.yml` | Unconfigured PyPI template |

The retired database check could create a database through the primary
connection without the isolation guard. The synchronous table utility derived
its target from the primary URL and dropped and recreated tables at import.
The generic migration wrapper exposed shell-based upgrades and downgrades
outside the guarded operational flow.

The PyPI workflow had no package build metadata and did not implement the
approved GitHub to Render deployment path. Its retirement does not configure
a replacement workflow or authorize publishing.

Original files are stored as non-executable text under
`artifacts/project-cleanup/retired-files/`, retaining their relative paths with
an added `.txt` suffix. Hashes, cleanup scope, and generated-file inventories
are recorded in `artifacts/project-cleanup/cleanup-manifest.json`.
Completed local checks are recorded separately in
`artifacts/project-cleanup/verification.json`.

The focused `scripts/check_base.py` and `scripts/check_models.py` diagnostics
remain available. Application modules and both migration histories were
preserved. Retiring an entry point does not certify every remaining legacy
module or remove a runtime dependency without a separate review.

## Supported operational paths

- Use `scripts/create_test_tables.py` for approved test-schema preparation
  through the dedicated test Alembic history. It validates the isolated target
  and applies migrations without resetting existing tables.
- Use `scripts/verify_development_startup.py` for the guarded read-only
  development startup check, following the
  [development verification guide](billing-development-verification.md).
- Use `scripts/billing_test_rehearsal.py` only under its isolated-target and
  rollback contract. It is separate from pytest cleanup fixtures.
- Follow the [operational runbook](billing-production-runbook.md) for billing
  preflight, deployment, identity, migration, recovery, and Telegram procedures.
  Production changes and live integrations retain their existing authorization
  limits.

Local cleanup does not connect to PostgreSQL or Redis, import the application,
start a server, modify identities, register webhooks, or publish a release.
