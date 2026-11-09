# MoulAI Python programming rules

These are the owner's agreed implementation standards. Apply them to new and
reviewed Python code. Preserve existing business rules, transaction boundaries,
and restaurant/owner isolation when harmonizing style. Do not refactor unrelated
legacy files merely to enlarge a change.

## File identity and documentation

Start every Python source file with this exact banner:

```python
# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================
```

After the legal banner, leave a blank line and add a framed program title with
a concrete explanatory comment describing that program's role, following the
owner's `admin_log.py` example. Follow it with a meaningful module docstring.
Use consistent section, class and function headings. Every logical block needs
a descriptive title and a useful explanatory comment; do not merely repeat its
name as the explanation. Retain meaningful existing comments and document
responsibility, inputs, results and relevant failure conditions in docstrings.

Always leave at least one blank line after a heading's closing separator and
before the following code or decorator. Keep headings before decorators, never
between a decorator and its definition. Preserve Python's required placement of
`from __future__` imports after the module docstring. For comment-only reviews,
verify executable AST equivalence rather than changing signatures or business
behavior to satisfy presentation rules.

When Ruff would remove the required blank line after an imports heading, place
the local `# isort: split` boundary before that framed heading. Keep import
sorting and unused-import checks active; do not remove the owner's spacing or
disable those checks for the whole file.

## Imports, typing and formatting

- A single imported item uses one line. Multiple items use parentheses, one item
  per line, with a trailing comma. Remove unused imports.
- Keep complete parameter and return annotations. Use shared `TypeAlias` or
  structured contracts where useful; avoid replacing concrete types with `Any`
  merely to silence checking.
- Use consistent Black formatting and Ruff checks. For an unusually long
  single-item import, `# fmt: skip` preserves the required one-line form.
- Use SQLAlchemy-compatible types and genuine async/await for asynchronous work.

## Architecture and safety

- Repository, Service and Business function parameters are keyword-only using
  `*`, after `self` or `cls` when present. Update callers when changing a signature.
- DB helpers accepting SQL arguments, including `*args` predicates, retain
  positional SQL parameters. Framework callbacks retain required signatures.
- Use the established BASE SELECT pattern and preserve all ownership predicates,
  joins, locks and transaction boundaries. BASE SELECT alone does not authorize
  access to a restaurant or tenant.
- Log important operation outcomes with useful, nonsensitive metadata. Avoid
  redundant logging, secrets, tokens and customer message contents. Distinguish
  preparation inside a transaction from a successfully committed operation.
- Implement authorized behavior completely. Do not leave TODO tasks,
  unimplemented functions, approximate replacements or runtime placeholders.
  Genuine offline fixtures, abstract typing contracts and deliberate rejection
  of unsupported operations are not unfinished business implementations.
- Do not claim production readiness solely from formatting or offline tests.
  Report the checks actually run and their limits. Do not run database migrations,
  external calls or deployments to validate style changes without authorization.

## Review delivery

After a code review, provide complete copyable Python versions. For a large
multi-file delivery, provide a linked complete-source archive and/or a document
containing the full sources, plus a concise report of changes and verification.
Do not offer only abbreviated snippets as the complete corrected program.
