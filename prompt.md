# MoulAI™ — Mandatory Python Engineering Protocol

**Document:** `prompt.md`  
**Project:** MoulAI™ Platform — Agent-as-a-Service  
**Scope:** Every Python file, without exception, including application code, scripts, migrations, and tests.  
**Status:** MANDATORY  
**Version:** 1.0 — 2026-10-08

## 0. Authority and Context Engineering

This document is the mandatory engineering contract for all Python work in MoulAI. At the start of **every** coding task, read this document, then inspect the relevant existing code, architecture, tests, configuration, and audit report before proposing changes. Do not assume the repository state from previous conversations. Follow repository-specific verified conventions when this document does not prescribe a rule; if conventions conflict with this document, report the conflict and resolve it explicitly before editing.

**MUST** = mandatory. **MUST NOT** = prohibited. **VERIFY** = prove by inspection or execution. **STOP** = do not invent missing requirements or claim completion. **EVIDENCE** = observable code, commands, and test results.

### Execution protocol

1. **DISCOVER:** Identify the requested behavior, impacted files, call chain, tenant boundaries, existing repository/service/business interfaces, `BASE SELECT` convention, SQLAlchemy session ownership, and tests.
2. **PLAN:** Describe the smallest coherent change, invariants, affected functions, transaction behavior, risks, and verification strategy.
3. **IMPLEMENT:** Preserve architecture and naming; apply all mandatory conventions below to each touched Python file. Avoid unrelated refactors.
4. **VERIFY:** Run relevant lint/type/test/integration checks where available. Never claim a command ran if it did not. Examine negative cases, tenant isolation, transaction rollback, and savepoint behavior where relevant.
5. **AUDIT:** Update `D:/MoulAI/docs/order-architecture-audit.md` whenever changes affect order architecture, its evidence, tests, or transactional behavior. Keep claims strictly aligned with observed results.
6. **DELIVER:** Provide a complete copy-ready version of **every modified Python file** (not snippets or diffs alone), its path, change summary, actual verification evidence, and remaining blockers. If a file is too large for one message, deliver it in numbered consecutive parts with no omissions; do not claim it is copy-ready until complete.

## 1. Mandatory File Header

Every Python source file MUST begin with this exact comment block (before imports, except a required shebang or encoding declaration mandated by the runtime):

```python
# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================
```

**VERIFY:** Header text and position match exactly. This is a project labeling requirement, not a substitute for a legal review of license suitability, especially for dependencies and commercial SaaS distribution.

## 2. Imports

- **MUST** use a single-line `from` import for exactly one imported symbol:

```python
from app.core.config import settings
```

- **MUST** use parenthesized, multiline `from` imports for two or more imported symbols:

```python
from app.core.database import (
    close_db,
    init_db,
)
```

- **MUST** remove unused imports. **MUST** maintain stable standard-library / third-party / application import groups and consistent ordering.
- **MUST NOT** use wildcard imports. Avoid circular imports and import-time side effects.
- Apply equivalent clean formatting to ordinary `import module` statements; do not invent parentheses for syntax that does not support them.

## 3. Typing and Interfaces

- **MUST** supply complete parameter and return type hints for all functions, including `async` functions and `-> None` where appropriate.
- **MUST** use consistent, meaningful type aliases where they improve repeated domain or query types; reuse existing aliases rather than inventing duplicates.
- **MUST** type SQLAlchemy models, statements, results, and sessions according to the installed SQLAlchemy version and the project's established interfaces.
- **MUST NOT** hide type errors using broad `Any`, unchecked casts, or blanket type ignores without documented technical justification.
- **VERIFY:** Type checking passes for the changed scope when a configured checker is available; otherwise report that it was not run.

## 4. Function Signatures and Keyword-only Parameters

Repository, Service, and Business functions **MUST** use a bare `*` to make applicable business arguments keyword-only, consistent with existing valid signatures:

```python
def get_order(*, tenant_id: int, order_id: int) -> None:
    ...
```

The example above illustrates signature shape only; ellipses are **NOT** permitted as unfinished production implementations.

- Preserve required Python semantics for `self`, `cls`, decorators, framework callback signatures, and externally imposed interfaces. For instance methods, use `def method(self, *, ...)`.
- DB helper functions **MUST NOT** be forced to use a bare `*` when their established interface uses positional SQL arguments or `*args`.
- **MUST NOT** break existing public interfaces silently. If a mandatory signature change impacts callers, update all callers and tests together.
- **VERIFY:** All relevant call sites pass keyword-only parameters correctly.

## 5. SQLAlchemy and BASE SELECT

- **MUST** preserve the repository's established **BASE SELECT** architectural pattern. Find its real definition and reuse it; do not invent a replacement query abstraction or duplicate filters.
- **MUST** follow the installed SQLAlchemy version, mapped models, async session APIs, existing repository interfaces, and current transaction boundaries.
- **MUST** keep persistence/query construction in the intended repository layer and business decisions in the appropriate business/service layer.
- **MUST** use parameterized queries and avoid unsafe string-built SQL.
- **MUST NOT** introduce hidden commits, implicit session creation, unbounded lazy loading, or unexpected transaction ownership changes.
- **VERIFY:** Query behavior, filtering, joins, eager loading, result cardinality, and error paths match existing contracts.

## 6. Async and Await

- **MUST** use `async def` and `await` for actual asynchronous I/O and existing async contracts.
- **MUST NOT** add artificial `async` wrappers to purely synchronous logic or forget to await coroutines.
- **MUST NOT** block the event loop with synchronous I/O inside async request paths.
- **VERIFY:** Session lifetime, cancellation, exception propagation, and resource cleanup work as intended.

## 7. Tenant and Restaurant Isolation — Security Invariant

- **MUST** enforce tenant and restaurant scope at every data-access path that handles scoped resources, including reads, writes, updates, deletes, counts, joins, and existence checks.
- **MUST** derive trusted scope from authenticated/authorized context, not merely from client-supplied IDs.
- **MUST** validate resource ownership and restaurant membership before business actions; avoid cross-tenant ID enumeration or information leakage.
- **MUST** preserve isolation from Business Logic through Services to Repositories and Database.
- **MUST NOT** accept a globally unique resource ID as proof of authorization.
- **VERIFY:** Include negative tests for cross-tenant and cross-restaurant access, including modified IDs and mixed-scope joins.

## 8. Transactions, Savepoints, and Error Handling

- **MUST** identify the owner of each transaction and use consistent SQLAlchemy session and `begin_nested()`/SAVEPOINT semantics where the existing workflow requires them.
- **MUST** distinguish a nested savepoint rollback from rollback of the outer transaction; verify persistence after outer commit and behavior after failures.
- **MUST NOT** report savepoint safety based solely on code inspection or mocked tests.
- **MUST** use explicit, appropriate exception handling; do not swallow errors or leave sessions in an invalid state.
- **VERIFY:** Test successful nested operation, nested failure/rollback, outer rollback, and the final database state using a real database when making integration claims.

## 9. Logging

- **MUST** log important operational events, unexpected failures, and security-relevant anomalies where actionable.
- **MUST NOT** add noisy, redundant, decorative, or per-line logging.
- **MUST NOT** log credentials, tokens, secrets, unnecessary personal data, or full sensitive payloads.
- **MUST** use the project's established logger conventions and appropriate levels; preserve useful context without leaking tenant data.

## 10. Comments, Docstrings, and Formatting

- **MUST** keep one consistent formatting style across the entire project.
- **MUST** write meaningful module, class, and function docstrings as appropriate, covering behavior, constraints, side effects, and exceptions where useful.
- **MUST** organize section headings and comments consistently; explain *why* and invariants rather than restating obvious code.
- **MUST NOT** introduce contradictory, stale, repetitive, or ornamental comments.
- **MUST** preserve existing naming and domain terminology unless a deliberate, fully propagated change is approved.
- **VERIFY:** Formatting and import sorting match project configuration; where no configuration exists, document the chosen convention before applying it broadly.

## 11. Production Readiness — No TODOs or Placeholders

- **MUST NOT** deliver unfinished implementations containing `TODO`, `FIXME`, `NotImplementedError`, `pass` used as a stub, `...` used as a stub, dummy returns, fabricated test fixtures presented as real behavior, or placeholder integrations.
- **MUST** finish all newly introduced or encountered incomplete logic **within the agreed task scope** before marking the task complete.
- **MUST NOT** silently rewrite unrelated legacy modules just to remove historical TODOs; instead inventory them, report them as blockers to any claim of whole-project compliance, and request scope approval.
- **STOP** if completion requires missing business rules, credentials, external services, or schema facts. Ask for the missing information rather than fabricating behavior.
- **VERIFY:** Search touched files for forbidden stubs and manually inspect flagged matches; literal mentions in comments, documentation, or tests are not automatically unfinished code.

## 12. Testing and Evidence

- **MUST** run the most relevant existing tests and add targeted tests for new behavior, regressions, permissions, and transaction boundaries.
- **MUST** distinguish unit tests, mocked tests, integration tests with a real database, and end-to-end tests.
- **MUST** report exact commands, environment, pass/fail/skip counts, and failures or tests not executed.
- **MUST NOT** claim 'production-ready', 'all tests pass', tenant isolation proven, or savepoints proven without sufficient evidence.
- **VERIFY:** No tests are silently skipped, no failures hidden, and no destructive operations run against production data.

## 13. Order Architecture Audit — Mandatory Synchronization

**Canonical path:** `D:/MoulAI/docs/order-architecture-audit.md`

Whenever order architecture or its verification changes, **MUST** update the report with:

1. Date, change summary, affected modules/functions, and actual architectural decisions.
2. Repository → Service → Business → Database execution paths and BASE SELECT compliance.
3. Tenant/restaurant isolation checks and remaining gaps.
4. Transaction owner, nested transaction/savepoint boundaries, rollback and commit outcomes.
5. **Real test coverage:** test identifiers, actual commands, environment, passed/failed/skipped outcomes, and whether tests were mocked or database-backed.
6. **Limits of evidence:** what was not tested, environmental restrictions, assumptions, and outstanding risks.
7. Differences from the previous audit and precise references to evidence.

**MUST NOT** retroactively assert results not observed. If the report cannot be accessed, **STOP** claiming the audit is current; provide the proposed exact update and identify the access blocker.

## 14. Change Control and Delivery Gate

Before accepting any Python modification, answer **YES** with evidence for each applicable item:

- [ ] Read current project context and traced impacted call sites.
- [ ] Exact MoulAI header on every touched Python file.
- [ ] Imports clean, grouped, unused imports removed.
- [ ] Complete type hints and consistent aliases.
- [ ] Keyword-only `*` policy applied with DB helper exceptions.
- [ ] Existing BASE SELECT and SQLAlchemy patterns preserved.
- [ ] Correct async/await and session lifecycle.
- [ ] Tenant and restaurant isolation verified.
- [ ] Transaction/savepoint semantics verified where applicable.
- [ ] Useful logging; no sensitive-data leaks.
- [ ] Consistent formatting, comments, and docstrings.
- [ ] No incomplete implementations in changed scope.
- [ ] Relevant tests executed and evidence recorded honestly.
- [ ] Order audit synchronized when applicable.
- [ ] Every changed Python file delivered completely, ready to copy.

**If any required item is NO or UNKNOWN:** do not mark the task complete. State the precise blocker, risk, and next required action.

## 15. Required Assistant Response Format for Coding Tasks

1. **Context verified:** files inspected, architecture, dependencies, assumptions.
2. **Changes:** paths and exact behavior changed.
3. **Complete Python files:** full contents of each modified Python file, with the exact required header.
4. **Verification evidence:** commands and actual results, including isolation and savepoint tests when relevant.
5. **Audit update:** exact changes to `docs/order-architecture-audit.md` or explicit reason it was not updated.
6. **Compliance verdict:** PASSED / BLOCKED, with unresolved facts clearly identified.

**Final rule:** Correctness, security, consistency, and evidence outrank speed. Never invent source code context, test results, database behavior, or audit completion.
