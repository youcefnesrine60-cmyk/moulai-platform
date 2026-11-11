# O5 presentation and isolated staging preparation

Date: 11 November 2026. Status: **local milestone verified with reservations**.
This delivery does not complete operational integration or authorize staging activation.
No remote database, hosting configuration, deployment hook or paid service was changed.

## Approved artwork and favicon

The actual new original is `assets/originals/moulai-logo-Mode-Sombre.png`:
2048 × 682 RGBA, alpha range 0–255, 1,124,476 fully transparent pixels.
Its SHA-256 is `2449087cfb4371606965a320fae2ff22880f802b91c6b84d353b098c9c5bdb0e`.
The public dark copy is byte-identical. `brandArtwork.ts` centralizes selection;
the shared `Brand` keeps its existing CSS footprint. There is no new opaque
rectangle, crop, recolouring or regenerated symbol. The approved light logo hash
remains `f98556da16c7b63ad33242402c523de220d8782a246c8cd940b9d7fc75582dba`.
White printable documents retain their existing light artwork. Help and assistant
images and positioning are unchanged.

Both supplied favicon originals were fully opaque, including their near-white
exterior. The new versioned PNG and PNG-compressed ICO retain the original
30 × 39 raster. Only 176 near-white exterior pixels, outside the coloured
silhouette on each row, become transparent. All 994 interior pixels remain
unchanged, including the white doorway. The originals remain untouched.
`scripts/prepare_brand_assets.ps1` pins the source hashes and reproduces this
derivation. No generative image service is involved.

Fresh Chromium contexts decoded both served variants identically, checked alpha,
checked the approved logo bytes and retained the title `MoulAI™`. New filenames
avoid an old favicon cache entry. This proves the served resources, not the
browser's tab background. Windows Computer Use stopped because it could not
attest the current URL. **Visual inspection of the actual tab icon remains
unverified**; no alternate desktop capture bypass was used.

## Documentary presentation and preserved states

`DocumentFacts.tsx` formats dates through `Intl.DateTimeFormat` in FR/EN/AR with
explicit UTC. Historical naive service timestamps follow the existing UTC
storage convention; offset-bearing timestamps are converted to UTC for display.
Microseconds remain in the exact data, `time[datetime]`, titles and technical
details. Unknown date formats are explicitly unavailable, never guessed.

The full 43-character reference and complete verification URL remain visible and
copyable. Clipboard denial has an explicit fallback. Direction isolation keeps
Latin references intact in RTL. The screen uses a descriptive verification link;
the complete URL remains readable in print. No shortening service or reduced
entropy was introduced.

Three facts stay distinct: retained period status **at issuance**, **current
document validity**, and **payment status at viewing**. The last is a screen-only
consultation outside the immutable printed document. These changes do not
recalculate funds or update retained snapshots. The previous issuance and
invalidation recipe was not repeated. The retained source is still one document
and two events; the current owner view and minimal reader both say invalidated.
Earlier PDFs remain historical copies; their QR checks current validity.

The direct-body print portal still excludes application navigation, illustration
and footer. Heading/paragraph pagination rules and an indivisible verification
block preserve legibility without a fixed one-page height. All three actual
final PDFs were reopened with Windows.Data.Pdf and every page inspected: **one
page each**, no blank extra page, entire QR and quiet zone. Earlier QR-only views
were partial screenshots, not an extra page in the previously verified PDFs.
Long multi-page/table stress cases remain open; no universal single-page claim
is made. Physical printing, phone scanning and an independent decode of the
newly rendered PDF raster remain unverified. Shared QR codec regressions pass.

Local `127.0.0.1` links are still explicitly labelled as inaccessible from another
phone. Future staging must use its explicit configured origin. Existing local
documents are retained as test history; no origin is rewritten. New issuance in
another environment must be deliberate, versioned and subject to its own funds,
permission and retained-source checks. Restaurant and SaaS circuits remain separate.

## Legacy continuity increment

`ReviewEditor` and `AgentEditor` now register dirty state with the shared navigation
guard. Cancel, close and Escape require an explicit discard; failed persistence
keeps the draft. Successful saves close normally, and session expiry still takes
priority. Pending agent submission cannot be closed. Nested-dialog focus no longer
overrides an editor's already restored opener.

Catalogue section, search, category, product and availability filters are retained
in scoped URL parameters, including across reload/back navigation. Reset removes
only those filters, keeping unrelated parameters. This is UI continuity tested
with the explicitly synthetic legacy adapter; it does **not** turn catalogue or
agent editing into a verified persistent integration.

## Staging O5 contract and rehearsals

The prepared host now requires exactly `o520261111`; O4, S1a and unknown revisions
are refused. The attested project/branch/endpoint/database marker and runtime-role
checks remain unchanged. The main Alembic history and O5 migration are unchanged.
`alembic_staging` admits the explicit O5 upgrade target, never `stamp`.

`prepare_staging_sql.py --target o520261111 --verify-runtime` builds a fresh local
cluster, executes the frozen bootstrap/main chain and replays captured SQL on a
second local database. O4 and O5 phases are separate: **391 / 141 / 9 statements**,
ending at **103 tables**. O4 rows are unchanged except Alembic's revision. The
initialization-clock differences of seven configuration tables are recorded;
all non-clock reference values and catalog hashes match. No fixture tariffs,
personal administrators or cash grants are included in the generated SQL.

Final rehearsal: `artifacts/staging-o5-20261111/rehearsals/03b9ee21615f437cb981e70263d63ecb`.
The O4→O5 body in `deploy/staging/migrations/from-o4-to-o5.sql` is captured from
the unchanged executed migration, not handwritten replacement DDL. Its outer
identity/marker/revision guard is for the approved isolated remote target, and
has **not** been executed remotely. The manifest separately hashes that body,
guarded file, migration sources and runtime SQL. Earlier O4 artifacts and remote
proofs are preserved as O4 history.

Runtime preparation now requires O5 and the marker. The two documentary tables
receive SELECT/INSERT and sequence usage, with UPDATE/DELETE/TRUNCATE revoked;
immutability triggers provide an additional protection. On the disposable local
server, both privileges and sequences were checked separately. Eight direct
forbidden commands were rejected, including UPDATE/DELETE/TRUNCATE on both
histories, Alembic writes and schema creation. The runtime cannot inherit the
owner. The complete remote grant script correctly rejected that local target;
only its exact grant body was exercised separately. This is not a remote login
or a general K11 least-privilege certification. Existing broader business-table
grants still need their own review.

The image `moulai-staging:review-o5-20261111` was built locally. Its compiled
frontend, CSP, session boundary, title and new resources passed an ASGI smoke
check in a read-only container with `--network none`. **No database connection,
lifespan or listener** is claimed by that smoke check. Real FastAPI/Keycloak
startup was checked on the retained local review; remote OIDC, runtime login,
storage and resource/load sizing remain activation prerequisites.

## O5-aware backup and recovery

A fresh backup of the quiescent retained local O5 review was restored and compared
in an owned clone on port 55434. `--recover-o5` requires an O5 source and 103
tables; it cannot accept O4. All catalogue definitions, ACLs and row fingerprints
matched, including **one subscription document and two documentary events**.
Recovery was performed in the clone and returned to that same O5 baseline.
The source was never restored, migrated or edited by this operation.

Proof: `artifacts/staging-o5-20261111/recovery/restore-942e4e07edf0499bbe2af53fd3f14639/summary.json`.
The private archive is outside tracked sources, under the retained instance's
`private/backups/o520261111-942e4e07edf0499bbe2af53fd3f14639/`.
SHA-256: `ae71049d4d67238437c8d375c656aae92ab78dd834f00fc371cec1df498d7dea`.
This is a local recovery proof, not a Neon backup or complete Keycloak/files/key
recovery. The prior O4 archive is not an automatic recovery source after O5 writes.

Future remote procedure, **not authorized for execution here**:

1. Reattest the pinned isolated target, exact O4 revision, marker and inventory;
   reject any divergence and stop all writers.
2. Take a fresh full O4 backup with roles/ACL metadata, independently restore it,
   compare schema/rows and establish a preserved pre-transition recovery branch.
3. Verify O5 manifest hashes. Execute only the guarded O4→O5 file with
   `psql -X --set=ON_ERROR_STOP=1 --single-transaction`, using a private libpq
   service, never a password in arguments. No retry or automatic downgrade.
4. Compare O5 catalogue, old row fingerprints, triggers and exact role privileges.
   Apply explicit authorized account permissions separately, without role inference.
5. Start the reviewed image without workers/providers and perform remote OIDC,
   tenant-isolation and documentary acceptance. Take a fresh O5 backup before
   accepting further test writes, and verify an O5 recovery preserving histories.
6. On failure after new writes, freeze writers and capture current O5 first;
   choose reviewed roll-forward or O5 restore. Never silently restore O4 and lose
   issued documents. Keycloak database, durable files and session key need their
   separate consistent backups and recovery recipe.

## Executed checks and evidence

| Check | Actual result | Boundary |
| --- | --- | --- |
| Artwork/document presentation unit tests | 54 distinct tests passed | jsdom; 18 affected tests also passed after the final status display change |
| Legacy continuity and regressions | 40 passed | Four files, serial workers; synthetic adapter |
| Staging admission/shared QR/schema compatibility | 76 passed | Offline, network guard, no destructive shared conftest |
| Resource/brand browser proof | 36 captures passed | Access, workspace, public menu entry; 3 languages × 2 themes × 2 sizes |
| SaaS owner/reader proof | 24 captures passed | Real local authenticated owner and minimal reader, same retained document |
| Owner/reader Axe | No violations in those 24 views | Incomplete rules retained in evidence; no accessibility certification |
| Actual PDF reopening/rendering | FR/EN/AR, 1 page each | Every final rendered page inspected |
| O5 SQL replay/runtime/recovery | Passed | Disposable local PostgreSQL, no remote writes |
| Image build and network-free smoke | Passed | No remote startup or image publication |

The previous historical-schema/test corrections are included in the backup as
their own change group. Their existing evidence remains at
`artifacts/local-startup-audit-fix-20261111/rapport.md`: 398 PostgreSQL cases in
six bounded lots covering all original 360 selections, 120 offline checks, four
HTTP tests and 60 O2/O5 regressions. Those campaigns were not repeated. The
previous monolithic Windows run remains inconclusive after Win32 1453/WAL failure.

Intermediate failures are retained: an unavailable sandbox PostgreSQL launch,
an intentionally network-free image build lacking dependency cache, a wrong
public-route capture, the newly exposed nested focus regression, and a parallel
test timeout. Final proofs are separately named. The build then used public
locked package dependencies; no paid activation or provider invocation occurred.

Local captures, PDFs, logs and complete-source export:
`artifacts/documents-o5-polish-20261111/`. They remain excluded from Git and Docker.
The gallery distinguishes comparable earlier O5 captures from final views, and
before-invalidation history from current after-invalidation views.

## Updated delivery and decision matrix

| Requirement | Current increment | Remaining work / decision |
| --- | --- | --- |
| Favicon alpha | Derived assets and fresh-context resource checks verified | Actual tab visual check blocked by Windows URL-attestation tool |
| Dark logo only | Shared exact approved original, 36 views | Owner visual acceptance |
| Dates, references, state distinctions | Implemented and tested | Long-document/table pagination stress and physical print |
| QR safety/current invalidation | Preserved, current reader consistent | Independent raster decode and physical phone scan |
| Staging O5 | Host contract, delta, runtime and O5 recovery prepared locally | Funding/activation decision and fresh remote attestation/backup/rehearsal |
| Legacy drafts/filters | Catalogue/profile/order-note and agent-editor guard increment | Other legacy editors and persistent catalogue adapter still open |
| Offer feature detail | Existing owned simulation retained | Authoritative included/excluded/optional projection remains to connect; no new prices approved here |
| Autonomous catalogue/reports | Existing screens/services retained | Persistent scoped adapter, exact monetary/metric contracts and full UI recipe still open |
| Product options | Existing structure and guards retained | Exact Decimal/currency catalogue source and approved choice/pricing rules need alignment; Float is not silently treated as exact |
| Language/contrast/assistive tools | FR/EN/AR, RTL, current unit/browser checks | Native zoom, screen reader and physical devices remain unverified |
| Agent context/actions/quota contracts | Existing engine and local documentary assistant retained | No conversational/provider integration added; server context, sector/subscription authority, confirmations, idempotence and explicit quota contract remain separate work |
| AI/voice/external services | No paid activation or provider call | Separate technical integration and budget authorization |

B remains approved/configurable at 3,000 DZD for Algeria; approved branch grids
are not reopened. Unapproved feature prices, legal text and document retention
policy for real companies remain separate decisions. This milestone supplies no
new commercial, fiscal or production-readiness approval.
