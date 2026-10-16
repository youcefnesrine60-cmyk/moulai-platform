# MoulAI documentation

English is the standard language for documentation in this directory. Write new
documents and maintain existing ones in English, including headings, tables,
instructions, and human-facing comments or prompts in examples.

Keep source identifiers, paths, configuration keys, protocol values, hashes,
timestamps, and recorded results unchanged when translating or editing. A
historical verification result must retain its date and scope; translating a
report does not rerun its checks or authorize an operational action.

## Document index

| Document | Purpose |
| --- | --- |
| [Architecture audit](order-architecture-audit.md) | Order architecture findings and the dated refactoring history |
| [Payment strategy](payment-integration-strategy.md) | Manual billing contracts and boundaries for later provider integrations |
| [Development verification](billing-development-verification.md) | Recorded isolated-database checks, migration rehearsal, and local startup |
| [Operational runbook](billing-production-runbook.md) | Deployment, identity, migration, and recovery procedures with approval limits |
| [Catalog isolation finding](catalog-options-isolation-finding.md) | Remaining authentication and tenant-boundary work for catalog options |
| [Dependency review](dependency-review.md) | Reviewed package versions, compatibility decisions, and isolated checks |
| [PowerShell standards](powershell-standards.md) | Script conventions, process ownership, and isolated verification |
| [Project maintenance](project-maintenance.md) | Repository layout, local artifacts, cache policy, and retired entry points |

## Reading the evidence

The project remains under development. Implemented features, pending work,
historical observations, and deployment authorization are distinct. Follow the
operational runbook before any action involving production data, administrative
identity, permission changes, or the live Telegram webhook.

Generated reports, source exports, and raw test captures are local files under
`artifacts/`, excluded from Git and Docker. Links to those artifacts in detailed
reports refer to the local checkout and may be unavailable on GitHub.

The local `artifacts/README.md` provides a central evidence index. Follow
[project maintenance](project-maintenance.md) when organizing generated output
or reviewing retired tools; recorded results remain tied to their original
source state and verification scope.
