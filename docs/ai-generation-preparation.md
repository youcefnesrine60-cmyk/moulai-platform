# Local AI generation — preparation and authorization boundary

Current status: **experiment closed — generation inconclusive (HTTP 402)**.
See [the closure and separate fallback-language defect](ai-generation-test-closure.md).
The preparation record below is historical; its original SHA and example command
do not authorize another invocation. The launcher remains unchanged.

Date: 2026-10-26. Status: **prepared offline; no real provider call authorized
or executed**. This is a limited engine experiment, not Business Integration or
an end-to-end restaurant-agent validation.

## Prepared mechanism and observed limits

Added only:

- [Local launcher](../scripts/prepare_ai_generation.py).
- [Standalone offline checks](../tests/test_ai_generation_preparation.py).
- This report.

The launcher loads reviewed, hash-pinned definitions of the existing
`AgentEngine`, `AIClient`, `ResponseGenerator`, RAM memory, language/NLU helpers
and prompt functions. It selects whole original AST definitions without changing
their bodies. It does not execute package imports, application settings or global
singletons. No existing engine, business source, frontend, dependency declaration
or environment file is modified.

Two observations are deliberately separate:

1. **Existing engine, offline:** the three exact messages run through the original
   language detector, pattern NLU and engine, with a fresh RAM memory per case,
   disabled provider clients and a no-business executor. These are rules/template
   observations, never claimed as generated AI responses.
2. **Proposed generative calls:** the same three messages reach the existing
   `ResponseGenerator.generate` and `AIClient.chat` with explicit language,
   `intent="unknown"` and an empty synthetic no-op result. This selects the
   existing generation branch. It is not the engine's natural intent-routing
   behavior and does not validate its NLU or a persisted agent configuration.

Actual offline engine observations:

| Exact input language | Detected language | Intent     | Response provenance                          |
| -------------------- | ----------------- | ---------- | -------------------------------------------- |
| French               | English           | `unknown`  | Stock error/template; zero provider calls.   |
| English              | English           | `greeting` | Predetermined greeting; zero provider calls. |
| Arabic               | Arabic            | `greeting` | Predetermined greeting; zero provider calls. |

The generator returns greetings, failed-action text and successful nonempty action
messages before reaching its AI branch. The French language mismatch and these
short circuits prevent claiming a natural end-to-end generative pass today.
Correcting language detection or changing generation precedence requires a
separately approved minimal engine change; neither was performed. The prepared
generator-only experiment remains usable without those changes.

## Isolation and tracing

- Dedicated Python child with `-I -B`; no public server or application startup.
  `DEBUG=false`, `DB_ECHO=false` and both OIDC flags are child-only. The terminal's
  inherited `DEBUG=release` and `.env` remain unchanged.
- Synthetic user IDs 980001–980003, restaurant 980001 and new RAM memory. No
  PostgreSQL, Neon, Redis, customer data, channel or real account is accessed.
- No business registry, database factory or mutation action is loaded. The only
  executor reports `tools_disabled`; model output is returned as text, never
  interpreted as code or a tool request.
- Child audit hooks refuse business imports, database/network destinations,
  binding a socket, subprocess creation and filesystem mutation. Only the exact
  provider HTTPS completion transport can open network access during an approved
  live call. TLS verification remains enabled; proxies, redirects and retries
  are disabled. These are reviewed-process controls, not an OS sandbox for
  arbitrary hostile Python code.
- The parent reads only the three required `.env` entries without interpolation.
  Inherited overrides take precedence and are validated. Keys are never printed,
  passed in command arguments or placed in reports. A future key crosses only a
  private child stdin pipe; echoed credentials are redacted before JSON encoding.
- Future traces distinguish transport attempts, HTTP acknowledgements, returned
  model/completion IDs, finish reason, response text, numeric usage, estimated
  cost, fallback and sanitized error type. A transport attempt without a response
  does not prove receipt by the provider. A timeout preserves available transport
  progress and reports unknown usage. No balance or model-list API call is made.
- Three attempts maximum, 500 output tokens each, fixed short prompts, no tools,
  no automatic retry/fallback provider. Failure, truncation, missing usage or an
  exceeded observed usage estimate stops subsequent scenarios. Returned answers
  require human semantic review; receipt of text is not an authorization pass.

## Provider, model and proposed cost

Read-only configuration inspection found **DeepSeek**, endpoint
`https://api.deepseek.com`, model **`deepseek-chat`**, and a nonempty key.
Key validity, model access and account balance remain unverified.

The official changelog announced retirement of `deepseek-chat` on 2026-07-24.
The current documented Flash identifier is **`deepseek-flash`**. The proposal
therefore requires explicit approval for this model override in the isolated
process; `.env` is not changed and no silent substitute is allowed.
[DeepSeek changelog](https://api-docs.deepseek.com/updates/).

Preparation uses the published peak, uncached prices: **USD 0.30 per million
input tokens and USD 1.20 per million output tokens**. The three fixed prompt
projections total 3,858 input proxy units, with at most 1,500 output tokens:
**USD 0.0029574**, approximately **USD 0.003**. Input estimation uses UTF-8 byte
counts plus framing allowance, not a verified tokenizer or a billing guarantee.
The proposed admission budget is **USD 0.01**; no spending is authorized yet.
Existing usage/cache/peak conditions and future actual token counts determine
billing. No credit purchase, account upgrade or currency conversion is proposed.
[DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/).

The test transport explicitly disables thinking mode for bounded textual replies,
using the provider's documented `extra_body` option. This is confined to the
launcher; the existing AIClient source is unchanged.
[DeepSeek thinking control](https://api-docs.deepseek.com/guides/thinking_mode/).

Dependencies already installed: Python environment, `openai` 2.32.0,
`httpx` 0.28.1 and `python-dotenv` (version pinned in the generated plan).
No local-model or Gemini connector is assumed or installed.

## Commands and acceptance

Safe preparation, executed without provider access:

```powershell
Set-Location D:\MoulAI
.\.venv\Scripts\python.exe -I -B scripts/prepare_ai_generation.py prepare
.\.venv\Scripts\python.exe -I -B tests/test_ai_generation_preparation.py
```

The final prepared plan SHA-256 is:

```text
7ba50be8a76d7870d9bb9f080b622d311b9f820309fef558db025e46254281a8
```

The following command is **prepared only and was not executed**. It requires the
user's distinct approval of the three provider calls, model override and budget:

```powershell
.\.venv\Scripts\python.exe -I -B scripts/prepare_ai_generation.py run `
  --approval-sha256 7ba50be8a76d7870d9bb9f080b622d311b9f820309fef558db025e46254281a8 `
  --allow-three-provider-calls --model deepseek-flash --budget-usd 0.01
```

The approved plan binds the launcher/source hashes, exact messages, model,
installed SDK versions and limits. Drift, another destination/model, a missing
approval or wrong plan hash refuses execution. CLI flags are operator controls,
not a replacement for the user's authorization. Re-running unchanged preparation
is idempotent; older plan files remain historical and cannot admit changed code.

For each real answer, review the expected language, recognition of four people
tomorrow at 20:00, a clear need to verify availability, and absence of invented
booking confirmation/number. The prompt uses an explicitly synthetic clock
(2026-10-26, Africa/Algiers); no real reservation is proposed for execution.
Stock responses, provider errors and incomplete outputs cannot count as generated
successes. Business actions must remain an empty list in every result.

## Verification and stop point

**29 standalone offline tests passed**, including real engine-source observations,
fresh memory, source drift, process flags, absent business imports, actual blocked
import/socket attempts, explicit authorization/hash refusals, key redaction,
three-call limits, errors/fallback/truncation, SDK serialization, redirect/retry
refusal and unauthorized HTTP destinations. SDK responses and DNS were mocked
for transport tests; they are not live provider observations. Black and Ruff pass.

Local ignored evidence is retained under
[`artifacts/ai-generation-preparation/`](../artifacts/ai-generation-preparation/):
the final `plan-<SHA>.json`, timestamped offline observations,
`offline-tests.log`, before-source inventory and `validation.json`. These files
are not automatically published, and no artifact was force-added to Git.

All 743 pre-existing inventoried files, including `.env` and the complete
frontend, retain their pre-task hashes. The three files listed above are the
only added publishable files. Branch remains `feature/keycloak-k10-complete`,
HEAD `457154a2598a4d8a1313e0449faa855e8e32f1f1`; existing uncommitted work is
preserved, with no staged change, commit, push, network Git synchronization or
deployment. No remote service or permission setting was changed.

**Stop here before the first provider request.** The generative stage is prepared;
semantic results and a full AgentEngine validation remain unproven.
