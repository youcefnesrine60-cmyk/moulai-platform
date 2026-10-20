# GitHub backup after K10: publication preparation

Date: **2026-10-20**. Target branch: **`feature/keycloak-k10-complete`**.
This delivery prepares a local commit. **No push, merge or deployment is
authorized or performed.** Publication requires the user's explicit approval.

## Starting point and included work

The initial local branch was `main` at
`7a667633f593afbabc9949cef12f603535eba94e` (2026-10-16). A direct read of
GitHub confirmed that `origin/main` has the same commit and that the proposed
feature branch did not exist remotely at inspection time. The dedicated local
branch was created from this commit; local `main` remains at that starting point.

The reviewed commit includes **155 changed or added files**:

| Group | Files | Scope |
| --- | --- | --- |
| Application | 53 | K8 JWT/JWKS validation and disabled diagnostics; K9 identity, organization, membership, roles, grants and TenantContext; K10 opt-in dependencies; previously validated API/RBAC and repository corrections. |
| Migration histories and support | 9 | Both E1 wrappers, frozen shared schema/SQL, explicit target metadata and pinned local migration environment. |
| Scripts | 12 | PKCE/E2E helpers, offline reviews, guarded G2 tooling and isolated local PostgreSQL launcher. |
| Test support | 3 | Local target admission and disposable K10 HTTP application. |
| Tests | 45 | JWT, tenant isolation, API/RBAC, E1, runner boundaries and PostgreSQL profiles. |
| Documentation | 28 | K8/K9/K10 validation, accepted limits, environment roles, local commands and this publication record. |
| Root configuration/documentation | 5 | `.env.example`, `.gitattributes`, README, reviewed requirements and dedicated PostgreSQL Compose file. |

The Git commit's name/status inventory is authoritative. A detailed local
inventory and review evidence are retained under ignored
`artifacts/git-publication/`; they are not publication inputs.

## Publication-only reproducibility correction

Review found that the G2 catalog verifier loaded SQL definitions from an ignored
historical collector. `scripts/tenant_catalog_queries.py` now contains the same
**13 SELECT definitions**, compared exactly with that collector. The verifier
loads this ordinary source with its own reviewed SHA-256 check. Its comparison
logic, E1 trigger allowlist and database admission controls are unchanged.

The regression rejects any attempt to read source from `artifacts/`.
`.gitattributes` disables newline conversion for frozen E1 sources and the catalog
contract, preserving their approved exact bytes on Windows and Linux. Several
approved E1 files use CRLF; normalizing them to LF would invalidate their hashes.
The path-specific whitespace rule recognizes CRLF without suppressing real
trailing-space checks or changing global Git settings.
No frozen migration definition was edited. Historical collector/result files
remain local; no ignored artifact was force-added or copied wholesale.

Targeted verifier/launcher checks passed **14 tests**, without warnings or database
access. A separate checkout assembled from the reviewed Git index passed
**70 tests, zero failures, skips or warnings**, without `.env` or ignored
artifacts: E1 static compilation and targeted HTTP/verifier regressions.
An initial checkout check exposed newline conversion and an overly broad test
path check; both were corrected, and that initial result remains local.
This is a packaging check, not a new PostgreSQL campaign.

The user's accepted PostgreSQL total remains **136 passed**: legacy 110 and
K10/E1 26. These campaigns were not repeated for publication preparation.
K10's [159 targeted results](keycloak-k10-validation.md) retain their dated scope.

## Safety and remaining limits

- The reviewed file snapshot contains no `.env`, real private key, database,
  dump, test log, server-data directory, local credential store or ignored
  artifact. Existing ignore rules remain active.
- Source inspection checks credential/token patterns and matches real locally
  configured secret values in memory, without exporting those values. The
  reported URL matches are configuration examples, synthetic test fixtures or
  dynamically constructed process-local URLs. No real secret was found in the
  reviewed snapshot. This does not claim exhaustive secret detection.
- `.env.example` retains example values and disabled OIDC flags. Real environment
  files, generated manifests, raw results and recovery evidence stay local.
- Declared requirements and the existing virtual environment differ as documented
  in the root README. No dependency installation or release certification is
  implied by this backup.
- E1 files are source code only. Publication does not authorize migration,
  identity linking, tenant cutover, enabled diagnostics or changes to current
  production protections. Remote replay still requires fresh admission and
  separately approved private evidence; expired rehearsal resources are not
  silently replaced or re-admitted.
- The feature branch must not be merged into `main` as part of this backup.
  The reported Render deployment branch remains `main`; account-side preview or
  integration behavior must be considered before approving any publication.

## Commit and proposed publication

Prepared commit message:

```text
feat: complete K8-K10 authorization and PostgreSQL test tooling

Integrate strict Keycloak JWT validation and PostgreSQL tenant identity,
membership, permission and restaurant-grant authority.

Include E1 migrations, guarded local legacy/K10 PostgreSQL profiles,
targeted authorization tests and validated API/RBAC corrections.

Make the G2 catalog contract reproducible without ignored artifacts,
preserve frozen source line endings and document accepted scope and limits.
```

Review the local commit before approval:

```powershell
git status --short --branch
git show --stat --oneline HEAD
git diff --name-status main..feature/keycloak-k10-complete
```

Only after explicit publication approval, the proposed push is:

```powershell
git push --set-upstream origin feature/keycloak-k10-complete
```

Verify the remote feature-branch SHA against the prepared local commit:

```powershell
git rev-parse feature/keycloak-k10-complete
git ls-remote --heads origin refs/heads/feature/keycloak-k10-complete
git ls-remote --heads origin refs/heads/main
```

Matching feature-branch commit IDs establish the same Git tree and history.
Recheck `main` independently; report unrelated upstream movement instead of
rewriting it. No force push, automatic merge, Render action, Neon operation,
Keycloak/Telegram change or production-security change belongs to this step.
