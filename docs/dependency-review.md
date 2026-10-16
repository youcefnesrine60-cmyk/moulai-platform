# Dependency review — 2026-10-16

This review updates `requirements.txt` for the current application. Package
metadata was checked against PyPI, and the selected baseline was installed into
an independent Windows environment using Python 3.14.4. The existing `.venv`,
`.env`, deployed service, and production database were not changed.

## Selected updates

| Dependency | Previous declaration | Reviewed declaration |
| --- | --- | --- |
| FastAPI | `0.136.1` | `0.136.3` |
| Starlette | `1.0.0` | `1.8.0` |
| Pydantic | `2.13.4` | `2.13.5` |
| pydantic-core | `2.46.4` | `2.46.5` |
| Redis client | `7.4.0` | `7.4.1` |
| python-dotenv | `1.2.2` | `1.2.4` |
| pytest-cov | `5.0.0` | `7.1.0` |
| bcrypt backend | Not declared | `4.0.1` |

Selected transitive packages were also updated: annotated-doc, certifi, and
typing-inspection. The Pydantic/core pair was checked against wheel metadata;
the exact core version is required by that Pydantic release.

Starlette 1.0.0 was affected by the upstream malformed-Host URL advisory.
The selected version includes its fix and later changes documented in the
[official release notes](https://starlette.dev/release-notes/). See the
[upstream advisory](https://github.com/Kludex/starlette/security/advisories/GHSA-86qp-5c8j-p5mr)
for the affected behavior and patched versions.

Open-ended ORM, driver, Settings, and quality-tool declarations now use the
installed versions already exercised by the project. This prevents a fresh
install from silently selecting a different ORM generation. New upstream minor
or major releases were not accepted automatically. The file is a reviewed
compatibility baseline, not a promise that every package is the latest release.

## Password backend compatibility

The application uses Passlib's bcrypt context. Previously, `passlib==1.7.4`
did not declare its required bcrypt backend, while the local environment
contained bcrypt 5.0.0. An isolated probe of that original pair failed even
for a short test password.

The requirements now declare `passlib[bcrypt]==1.7.4` and `bcrypt==4.0.1`.
The latter is an intentional compatibility pin. Its availability and binary
distribution are documented on [PyPI](https://pypi.org/project/bcrypt/4.0.1/);
compatibility with this project was established by the local checks below,
rather than inferred from package metadata alone.

Application-level hashing and verification passed for ASCII, Unicode, and
72-byte inputs. The check rejected incorrect passwords and accepted the legacy
`$2a$` hash prefix. No stored password was read or changed. This dependency
change does not introduce a password-algorithm migration or change the existing
bcrypt policy for inputs longer than 72 bytes.

## Removed and retained dependencies

The reviewed application, scripts, migrations, and tests do not import
python-telegram-bot, openpyxl, or requests. Their declarations and dedicated
dependencies et-xmlfile, urllib3, and charset-normalizer were removed. Telegram
operations continue through the existing HTTPX transport. The unrelated
git-filter-repo utility was also removed from the application install list.

Psycopg and psycopg-pool were retained in this review because the existing
`app/core/db.py` implements an asynchronous pool. The legacy root diagnostic
that referenced it was subsequently retired during
[repository cleanup](project-maintenance.md). That retirement did not remove
the runtime module or establish that these dependencies are unused. The
canonical ORM path continues to use SQLAlchemy AsyncSession and asyncpg.

Runtime packages and development tools remain in one file to preserve the
current Render installation command. All 43 declarations are exact pins, but
the file does not pin every transitive package or constitute a cross-platform
lock. The resolved Windows inventory is saved locally under
`artifacts/dependency-review/`.

## Verification and its limits

| Check | Result |
| --- | --- |
| Fresh isolated installation | Passed; binary distributions only |
| `pip check` | No broken requirements |
| Independent unittest selection | 83 passed with `-W error` |
| Mocked/local Pytest selection | 322 passed, one upstream warning |
| Explicit coverage-plugin check | 13 passed, zero warnings |
| Password compatibility samples | Three inputs passed all checks |

The final test runners prevented external connections before importing the
application. Redis was disabled only inside those test processes. The final
unittest and Pytest reports recorded zero denied connection attempts;
Windows asyncio loopback support was allowed separately. No live PostgreSQL
or Redis service was used.

The separate coverage check reran 13 cases already included in the 322-case
selection; they are not additional distinct tests. It exercised pytest-cov
7.1.0 with coverage 7.15.2 and measured 100% of the 25 statements in
`payment_transaction.py`. This is module coverage, not platform coverage.
Version 7 changed subprocess coverage behavior, as documented in the
[pytest-cov changelog](https://pytest-cov.readthedocs.io/en/latest/changelog.html).

The 322-case run retains one `StarletteDeprecationWarning`: Starlette's test
client deprecates its HTTPX backend in favor of httpx2. No warning filter or
extra HTTP client was added. The existing application HTTPX transport remains
unchanged; migration of the optional test-client backend is separate work.

An initial guarded run detected and blocked an import-side Redis lookup.
That result was retained separately before the corrected process configuration
passed. The guard prevented an external connection in the initial run too.

Detailed JSON reports, resolved versions, and installation evidence are local
files in `artifacts/dependency-review/`. Test captures are indexed in
`artifacts/test-logs/INDEX.md`. Both directories are excluded from Git and Docker.
The temporary review environment and downloaded wheel directory were removed
during the subsequent local cleanup; the main `.venv` was preserved. Reports,
the resolved Windows inventory, and installation evidence remain available,
with wheel hashes and cleanup scope recorded in
`artifacts/project-cleanup/cleanup-manifest.json`. The historical test results
do not imply that the disposable review environment remains available. Consult
the reviewed requirements and resolved inventory when preparing a new isolated
environment.

These checks do not verify Linux/Render deployment, Docker's Python 3.11 image,
live identity-provider setup, or PostgreSQL integration under the new baseline.

The unsafe `scripts/create_test_tables_sync.py` entry point was subsequently
archived and removed from active paths. It derived a target from the primary
URL and performed table drop/create operations without the central isolation
guard. It was neither imported nor executed during this review, and no
dependency was added to enable it. See
[project maintenance](project-maintenance.md) for the retirement record and
supported replacements. Test preparation uses `scripts/create_test_tables.py`;
setup, migration, and recovery remain governed by the
[billing runbook](billing-production-runbook.md).
