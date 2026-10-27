# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Prepare a generation-only local experiment; live provider access is explicit.

No application package is imported. Reviewed, unchanged definitions are selected
from source AST to avoid package initializers, settings and business singletons.
The engine observation is offline; the proposed three live calls exercise the
existing ResponseGenerator/AIClient, not a connected restaurant agent.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import dataclasses
import hashlib
import importlib.metadata
import io
import json
import logging
import os
import re
import socket
import subprocess
import sys
import types
import typing
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "ai-generation-preparation"
BASE_URL = "https://api.deepseek.com"
PROPOSED_MODEL = "deepseek-flash"
OUTPUT_TOKENS = 500
MAX_PROMPT_BYTES = 6000
INPUT_RATE = Decimal("0.30")
OUTPUT_RATE = Decimal("1.20")
BUDGET = Decimal("0.01")
SCENARIOS = (
    (
        "fr",
        "Bonjour, je voudrais réserver une table pour quatre personnes demain à 20 h.",
    ),
    ("en", "Hello, I would like to book a table for four tomorrow at 8 PM."),
    ("ar", "مرحبًا، أريد حجز طاولة لأربعة أشخاص غدًا على الساعة الثامنة مساءً."),
)
SOURCES = {
    "app/core/ai_client.py": "a520b6ca6d21e176cac3fc0adb28d578a56682cedc940707ea27b8d41ac4c3c8",
    "app/agent/config.py": "e6c9c82e5672081e862a91bb41720a6a190270c675999f1a1a5eed71b32e6948",
    "app/agent/language/detector.py": "1e474641edd3c4b9b6f5821d2d7909a76accb9156d61ab77329c4bc8d1222d95",
    "app/agent/nlu/intent_classifier.py": "7bb8f6826b74bc6cd21f186dc5548222449a1a7942fe4d58d61eae8483f5fb1d",
    "app/agent/nlu/entity_extractor.py": "d725e3f82dfde016ed8f8980be38691e9f3fcb7cf8b0b718fc7606fbd216e181",
    "app/agent/executor/actions.py": "e7f38fe585f33777aaec87bf2265ba8e1720578fa55fe6bb03bae89a6d6eaf4d",
    "app/agent/memory/memory_manager.py": "814d1268a465c46bf8357957f87b73b615671d2e1e8a2e1b89cce1e041c5e314",
    "app/agent/prompts/templates.py": "b5e4af58785109a3064187c716c8340867ab392424603503938e54fb0172d6f7",
    "app/agent/prompts/translations.py": "c72df63c63b1f9556fee6bd8b8df0471220129777ad8c6a383acbc019f335743",
    "app/agent/response_generator.py": "0262b8cb8ba72fce48bafa99362690aff8f8c81c85fffbc5d82f5c730c91d96d",
    "app/agent/engine.py": "c113027450962fa32a1581bb24ce8b09e3ce2a437883fc8c52383bc34286963d",
}
FORBIDDEN_IMPORTS = {
    "app",
    "sqlalchemy",
    "asyncpg",
    "psycopg",
    "psycopg2",
    "sqlite3",
    "redis",
    "telegram",
    "aiogram",
    "requests",
    "aiohttp",
}


class Refused(RuntimeError):
    """A fixed public reason code; never attach provider exceptions or settings."""


def sha(data: bytes) -> str:
    """Fingerprint approved content without exposing it."""
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    """Use one stable approval representation."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def verify_sources() -> None:
    """Refuse drift instead of executing newly introduced source definitions."""
    for name, expected in SOURCES.items():
        if sha((ROOT / name).read_bytes()) != expected:
            raise Refused("reviewed_source_changed")


def configuration() -> dict[str, str]:
    """Read only the three required settings, without interpolation or app imports."""
    from dotenv import dotenv_values

    selected = []
    env_path = ROOT / ".env"
    contents = env_path.read_text(encoding="utf-8-sig") if env_path.is_file() else ""
    for line in contents.splitlines():
        if re.match(
            r"^\s*(?:export\s+)?(?:OPENAI_API_KEY|OPENAI_BASE_URL|AI_MODEL)\s*=", line
        ):
            selected.append(line)
    local = dotenv_values(stream=io.StringIO("\n".join(selected)), interpolate=False)
    result = {
        name: os.environ.get(name, local.get(name) or "")
        for name in (
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "AI_MODEL",
        )
    }
    base = result["OPENAI_BASE_URL"].rstrip("/")
    if base not in {BASE_URL, BASE_URL + "/v1"}:
        raise Refused("provider_endpoint_not_approved")
    if not re.fullmatch(r"[a-zA-Z0-9._-]{1,80}", result["AI_MODEL"]):
        raise Refused("model_configuration_invalid")
    if "${" in result["OPENAI_API_KEY"] or "\n" in result["OPENAI_API_KEY"]:
        raise Refused("key_configuration_invalid")
    return result


def sanitized_environment() -> dict[str, str]:
    """Give the child OS essentials and fixed safety flags, with no inherited credentials."""
    keep = {
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
    }
    result = {key: value for key, value in os.environ.items() if key.upper() in keep}
    result.update(
        DEBUG="false",
        DB_ECHO="false",
        OIDC_DIAGNOSTICS_ENABLED="false",
        OIDC_ALLOW_LOCAL_HTTP="false",
    )
    return result


class Boundary:
    """Deny business imports, writes, processes and networking outside one provider transport."""

    def __init__(self) -> None:
        self.provider_active = False
        self.allowed_addresses: set[str] = set()
        self.denied = 0

    def audit(self, event: str, arguments: tuple[typing.Any, ...]) -> None:
        """Apply the child boundary before loading reviewed definitions or the SDK."""
        forbidden = False
        if event == "import":
            forbidden = str(arguments[0]).split(".")[0] in FORBIDDEN_IMPORTS
        elif event.startswith("socket."):
            if event == "socket.__new__":
                return
            if (
                self.provider_active
                and event == "socket.getaddrinfo"
                and arguments[0] == "api.deepseek.com"
                and arguments[1] in {443, "443"}
            ):
                return
            if self.provider_active and event == "socket.connect":
                target = arguments[1]
                if (
                    isinstance(target, tuple)
                    and target[0] in self.allowed_addresses
                    and target[1] == 443
                ):
                    return
            forbidden = True
        elif event in {
            "subprocess.Popen",
            "os.system",
            "os.posix_spawn",
            "os.exec",
            "os.spawn",
        }:
            forbidden = True
        elif event == "open":
            mode, flags = arguments[1:3]
            forbidden = bool(
                isinstance(mode, str) and any(x in mode for x in "wax+")
            ) or bool(
                isinstance(flags, int)
                and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            )
        elif event in {"os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.truncate"}:
            forbidden = True
        if forbidden:
            self.denied += 1
            raise Refused("isolated_operation_refused")


def source_namespace(
    factory: typing.Callable[..., typing.Any],
) -> dict[str, typing.Any]:
    """Compile original approved definitions, never their imports or module singletons."""
    verify_sources()
    module = types.ModuleType("_moulai_generation_definitions")
    sys.modules[module.__name__] = module
    scope = module.__dict__
    scope.update(vars(typing))
    scope.update(
        __builtins__=vars(builtins),
        __name__=module.__name__,
        re=re,
        json=json,
        datetime=datetime,
        hashlib=hashlib,
        dataclass=dataclasses.dataclass,
        OpenAI=factory,
        logger=logging.getLogger("isolated-null"),
        settings=types.SimpleNamespace(
            OPENAI_API_KEY="", OPENAI_BASE_URL=BASE_URL, AI_MODEL=PROPOSED_MODEL
        ),
        default_config=types.SimpleNamespace(
            max_history=10,
            session_timeout=3600,
            confidence_threshold=0.7,
            default_language="ar",
            llm_provider="offline",
        ),
    )
    for name in ["LanguageCode", "LanguageName"]:
        scope[name] = str
    scope["ConfidenceScore"] = float
    for name in [
        "AIMessage",
        "AIResponse",
        "ResponseContext",
        "ResponseResult",
        "IntentResult",
        "EntityDict",
        "SessionData",
        "ContextData",
        "ActionContext",
        "ProcessResult",
        "AgentResponse",
    ]:
        scope[name] = dict[str, typing.Any]
    for name in ["AIMessages", "MessageHistory", "EntityList", "ConversationHistory"]:
        scope[name] = list[dict[str, typing.Any]]
    scope.update(IntentList=list[str], LanguageDetectionResult=tuple[str, float])
    for name in ["LanguageMap", "PromptMap", "ResponseMap"]:
        scope[name] = dict[str, str]
    for name in ["PatternMap", "PhraseMap"]:
        scope[name] = dict[str, list[str]]
    scope["MultiLangPromptMap"] = dict[str, dict[str, str]]

    def load(filename: str, names: set[str], literals: bool = False) -> None:
        """Select whole unmodified AST nodes; no class/function body is rewritten."""
        tree = ast.parse((ROOT / filename).read_text(encoding="utf-8-sig"), filename)
        selected: list[ast.stmt] = []
        for node in tree.body:
            if (
                isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in names
            ):
                selected.append(node)
            elif (
                literals
                and isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
            ):
                try:
                    scope[node.target.id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    pass
        if {getattr(node, "name", None) for node in selected} != names:
            raise Refused("reviewed_definition_missing")
        # Only pinned repository AST definitions are compiled; prompts and responses never reach exec.
        exec(  # noqa: S102 -- pinned source definitions only.
            compile(ast.Module(body=selected, type_ignores=[]), filename, "exec"), scope
        )

    load("app/core/ai_client.py", {"AIClient"})
    load("app/agent/executor/actions.py", {"ActionResponse"})
    load("app/agent/config.py", {"LanguageConfig"})
    scope["language_config"] = scope["LanguageConfig"]()
    load("app/agent/prompts/translations.py", set(), literals=True)
    load(
        "app/agent/prompts/templates.py",
        {
            "get_system_prompt",
            "get_intent_classification_prompt",
            "get_response_generation_prompt",
            "get_entity_extraction_prompt",
            "get_confirmation_prompt",
            "get_error_prompt",
            "get_success_prompt",
        },
        literals=True,
    )
    load("app/agent/language/detector.py", {"LanguageDetector", "detect_language"})
    load("app/agent/nlu/intent_classifier.py", {"IntentClassifier"})
    load("app/agent/nlu/entity_extractor.py", {"EntityExtractor"})
    load("app/agent/memory/memory_manager.py", {"MemoryManager"})
    load("app/agent/response_generator.py", {"ResponseGenerator"})
    # Constructor arguments below are always explicit. These aliases are annotations only.
    scope.update(
        AgentConfig=types.SimpleNamespace, ActionExecutor=types.SimpleNamespace
    )
    load("app/agent/engine.py", {"AgentEngine"})
    return scope


def complete(
    coroutine: typing.Coroutine[typing.Any, typing.Any, typing.Any],
) -> typing.Any:
    """Run the existing immediate coroutines without an event loop or socket pair."""
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    finally:
        coroutine.close()
    raise Refused("unexpected_async_io")


class NoBusinessExecutor:
    """No registry, database, business service or callable tool is available."""

    async def execute(self, **_kwargs: typing.Any) -> dict[str, typing.Any]:
        """Report an unavailable action without invoking anything."""
        return {
            "success": False,
            "action": None,
            "message": "",
            "data": {},
            "error": "tools_disabled",
        }


def engine_observation(scope: dict[str, typing.Any]) -> list[dict[str, typing.Any]]:
    """Observe the unmodified engine's offline behavior on each exact message."""
    observations = []
    for index, (language, message) in enumerate(SCENARIOS):
        disabled = types.SimpleNamespace(enabled=False)
        memory = scope["MemoryManager"]()
        engine = scope["AgentEngine"](
            config=scope["default_config"],
            memory_manager=memory,
            intent_classifier=scope["IntentClassifier"](ai_client=disabled),
            entity_extractor=scope["EntityExtractor"](ai_client=disabled),
            action_executor=NoBusinessExecutor(),
            response_generator=scope["ResponseGenerator"](
                ai_client=disabled, use_ai=False
            ),
        )
        result = complete(
            engine.process(
                user_id=980001 + index,
                message=message,
                session_id=f"isolated-{language}",
                channel="local-probe",
                context={
                    "restaurant_id": 980001,
                    "restaurant_name": "Synthetic Restaurant",
                    "business_tools": [],
                },
            )
        )
        observations.append(
            {
                "expected_language": language,
                "detected_language": result["language"],
                "intent": result["intent"],
                "response": result["response"],
                "provenance": "offline_rules_or_template",
                "provider_calls": 0,
                "business_actions": [],
                "memory_backend": "fresh_ram",
            }
        )
    return observations


def cost_projection(messages: list[dict[str, str]]) -> dict[str, typing.Any]:
    """Use UTF-8 bytes plus framing as a conservative estimate, not a verified tokenizer."""
    size = sum(len(item["content"].encode("utf-8")) for item in messages)
    if size > MAX_PROMPT_BYTES:
        raise Refused("prompt_budget_exceeded")
    estimate = (
        Decimal(size + 256) * INPUT_RATE + Decimal(OUTPUT_TOKENS) * OUTPUT_RATE
    ) / 1_000_000
    return {
        "utf8_bytes": size,
        "input_token_proxy": size + 256,
        "output_token_limit": OUTPUT_TOKENS,
        "estimated_usd_peak_uncached": str(estimate),
        "method": "utf8_bytes_plus_256_not_verified_tokenizer",
    }


class CompletionGate:
    """Only three fixed plain-text completions; no tool options or hidden SDK retries."""

    def __init__(self, create: typing.Callable[..., typing.Any], live: bool) -> None:
        self.create_provider = create
        self.live = live
        self.events: list[dict[str, typing.Any]] = []

    def create(self, **kwargs: typing.Any) -> typing.Any:
        """Record safe provenance around the exact existing AIClient SDK boundary."""
        if len(self.events) >= 3 or set(kwargs) != {
            "model",
            "messages",
            "temperature",
            "max_tokens",
        }:
            raise Refused("completion_contract_refused")
        if kwargs["model"] != PROPOSED_MODEL or kwargs["max_tokens"] != OUTPUT_TOKENS:
            raise Refused("completion_contract_refused")
        messages = kwargs["messages"]
        if len(messages) != 2 or [item["role"] for item in messages] != [
            "system",
            "user",
        ]:
            raise Refused("completion_contract_refused")
        if any(
            set(item) != {"role", "content"} or not isinstance(item["content"], str)
            for item in messages
        ):
            raise Refused("completion_contract_refused")
        event = {
            "stage": "isolated_response_generator",
            "provenance": "provider_pending" if self.live else "offline_mock",
            "request_sha256": sha(canonical(kwargs)),
            "projection": cost_projection(messages),
            "provider_response_received": False,
            "business_actions": [],
        }
        projected = sum(
            Decimal(item["projection"]["estimated_usd_peak_uncached"])
            for item in self.events
        ) + Decimal(event["projection"]["estimated_usd_peak_uncached"])
        if projected > BUDGET:
            raise Refused("total_budget_exceeded")
        self.events.append(event)
        try:
            response = self.create_provider(
                **kwargs, extra_body={"thinking": {"type": "disabled"}}
            )
        except Exception as error:  # noqa: BLE001 -- sanitize provider errors.
            event.update(
                provenance="provider_error" if self.live else "offline_mock_error",
                error_type=type(error).__name__,
            )
            raise Refused("provider_request_failed") from None
        content = response.choices[0].message.content
        usage = response.usage
        event.update(
            provenance="provider_response" if self.live else "offline_mock",
            provider_response_received=self.live,
            response_id=response.id,
            model_returned=response.model,
            finish_reason=response.choices[0].finish_reason,
            usage=(
                {
                    key: getattr(usage, key, None)
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                }
                if usage
                else None
            ),
            response=content,
        )
        if self.live and (
            not usage
            or any(
                not isinstance(getattr(usage, name, None), int)
                or getattr(usage, name) < 0
                for name in ("prompt_tokens", "completion_tokens", "total_tokens")
            )
        ):
            event["provenance"] = "provider_usage_missing"
            raise Refused("provider_usage_missing")
        if usage:
            amount = (
                Decimal(usage.prompt_tokens) * INPUT_RATE
                + Decimal(usage.completion_tokens) * OUTPUT_RATE
            ) / 1_000_000
            event["estimated_cost_from_usage_usd_peak"] = str(amount)
            if (
                sum(
                    Decimal(item.get("estimated_cost_from_usage_usd_peak", "0"))
                    for item in self.events
                )
                > BUDGET
            ):
                event["provenance"] = "provider_budget_exceeded"
                raise Refused("observed_usage_budget_exceeded")
        if (
            not isinstance(content, str)
            or not content.strip()
            or response.choices[0].finish_reason != "stop"
        ):
            event["provenance"] = (
                "provider_incomplete" if self.live else "offline_mock_incomplete"
            )
            raise Refused("provider_response_incomplete")
        return response


def mock_completion(**kwargs: typing.Any) -> typing.Any:
    """Synthetic transport reply for offline mechanics; never label it AI-generated."""
    return types.SimpleNamespace(
        id="offline-mock",
        model=kwargs["model"],
        usage=None,
        choices=[
            types.SimpleNamespace(
                message=types.SimpleNamespace(
                    content="OFFLINE MOCK — no model called."
                ),
                finish_reason="stop",
            )
        ],
    )


def generation_cases(
    scope: dict[str, typing.Any], gate: CompletionGate, key: str
) -> list[dict[str, typing.Any]]:
    """Exercise only the existing generator's AI path, independently of the engine's NLU."""
    scope["OpenAI"] = lambda **_kwargs: types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=gate)
    )
    client = scope["AIClient"](api_key=key, base_url=BASE_URL, model=PROPOSED_MODEL)
    generator = scope["ResponseGenerator"](ai_client=client)
    results = []
    for language, message in SCENARIOS:
        before = len(gate.events)
        response = complete(
            generator.generate(
                intent="unknown",
                language=language,
                user_message=message,
                action_result=scope["ActionResponse"](
                    True, "", data={"operation": "no_op", "business_actions": []}
                ),
                context={
                    "restaurant": "Synthetic Restaurant 980001",
                    "expected_language": language,
                    "availability": "UNKNOWN: no schedule or reservation system is connected.",
                    "instructions": "Reply in the expected language. Recognize the table request for four tomorrow at 20:00. Explain that availability must be verified; do not claim a booking, availability, or booking number. No business action is possible.",
                    "synthetic_clock": "2026-10-26; restaurant timezone Africa/Algiers",
                },
                entities={},
                history=[],
            )
        )
        events = gate.events[before:]
        valid = (
            len(events) == 1
            and events[0]["provenance"] in {"provider_response", "offline_mock"}
            and response == events[0].get("response")
        )
        results.append(
            {
                "language": language,
                "message": message,
                "returned_response": response,
                "response_origin": (
                    events[0]["provenance"] if valid else "fallback_or_error"
                ),
                "events": events,
                "business_actions": [],
                "semantic_evaluation": "human_review_required",
            }
        )
        if not valid:
            break  # The existing AIClient may swallow an error into a stock response. Never continue silently.
    return results


def live_client(
    key: str, boundary: Boundary, trace: list[dict[str, typing.Any]]
) -> typing.Any:
    """Construct the only permitted HTTPS transport, with no proxy, redirects or retries."""
    import httpx
    from openai import OpenAI

    class Transport(httpx.BaseTransport):
        """Validate each SDK request before enabling the narrow network boundary."""

        def __init__(self) -> None:
            self.inner = httpx.HTTPTransport(retries=0, verify=True)

        def handle_request(self, request: httpx.Request) -> httpx.Response:
            """Allow only the reviewed model-completion request to the exact provider."""
            if (
                request.method != "POST"
                or str(request.url) != BASE_URL + "/chat/completions"
                or len(trace) >= 3
            ):
                raise Refused("http_destination_refused")
            body = json.loads(request.content)
            if (
                set(body)
                != {"model", "messages", "temperature", "max_tokens", "thinking"}
                or body["model"] != PROPOSED_MODEL
                or body["thinking"] != {"type": "disabled"}
                or body["max_tokens"] != OUTPUT_TOKENS
                or body["temperature"] != 0.7
            ):
                raise Refused("http_body_refused")
            if (
                len(body["messages"]) != 2
                or [row["role"] for row in body["messages"]] != ["system", "user"]
                or any(
                    set(row) != {"role", "content"}
                    or not isinstance(row["content"], str)
                    for row in body["messages"]
                )
            ):
                raise Refused("http_body_refused")
            cost_projection(body["messages"])
            event: dict[str, typing.Any] = {
                "transport_attempted": True,
                "transmission_confirmed": False,
                "http_status": None,
            }
            trace.append(event)
            print(json.dumps({"progress": dict(event)}), flush=True)
            boundary.provider_active = True
            try:
                addresses = socket.getaddrinfo(
                    "api.deepseek.com", 443, type=socket.SOCK_STREAM
                )
                boundary.allowed_addresses = {entry[4][0] for entry in addresses}
                response = self.inner.handle_request(request)
                response.read()  # Keep body receipt inside the same bounded transport attempt.
                event.update(
                    transmission_confirmed=True, http_status=response.status_code
                )
                print(json.dumps({"progress": dict(event)}), flush=True)
                return response
            finally:
                boundary.provider_active = False
                boundary.allowed_addresses.clear()

        def close(self) -> None:
            """Close only this dedicated provider connection pool."""
            self.inner.close()

    return OpenAI(
        api_key=key,
        base_url=BASE_URL,
        max_retries=0,
        timeout=25,
        http_client=httpx.Client(
            transport=Transport(), trust_env=False, follow_redirects=False, timeout=25
        ),
    )


def child(payload: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """Install isolation first; no app imports, environment loading or file writes follow."""
    logging.disable(logging.CRITICAL)
    boundary = Boundary()
    sys.addaudithook(boundary.audit)
    live = payload.get("mode") == "live"
    if payload.get("mode") not in {"offline", "live"}:
        raise Refused("child_mode_refused")
    if live:
        approval = payload.get("authorization", {})
        fingerprint = approval.get("plan_sha256", "")
        if not re.fullmatch(r"[a-f0-9]{64}", fingerprint) or approval != {
            "plan_sha256": fingerprint,
            "allow_three_provider_calls": True,
            "model": PROPOSED_MODEL,
            "budget_usd": str(BUDGET),
        }:
            raise Refused("separate_provider_authorization_required")
        approved = json.loads(
            (OUTPUT / f"plan-{fingerprint}.json").read_text(encoding="utf-8")
        )
        if (
            sha(canonical(approved)) != fingerprint
            or approved["launcher_sha256"] != sha(Path(__file__).read_bytes())
            or approved["reviewed_sources"] != SOURCES
        ):
            raise Refused("approved_plan_mismatch")
    transport_trace: list[dict[str, typing.Any]] = []
    gate = CompletionGate(mock_completion, live=False)
    scope = source_namespace(lambda **_kwargs: None)
    observations = engine_observation(scope)
    sdk = None
    if live:
        sdk = live_client(payload["key"], boundary, transport_trace)
        gate = CompletionGate(sdk.chat.completions.create, live=True)
    try:
        results = generation_cases(
            scope, gate, payload.get("key") or "offline-placeholder"
        )
    finally:
        if sdk:
            sdk.close()
    imported = sorted(
        name for name in sys.modules if name.split(".")[0] in FORBIDDEN_IMPORTS
    )
    if imported:
        raise Refused("business_module_present")
    return {
        "mode": "live" if live else "offline",
        "engine_observation": observations,
        "generation_stage": "isolated_response_generator_not_end_to_end_agent",
        "scenarios": results,
        "transport": transport_trace,
        "external_attempts": len(transport_trace),
        "denied_operations": boundary.denied,
        "business_modules_loaded": imported,
        "business_actions": [],
        "effective_debug": os.environ.get("DEBUG"),
        "all_generated": live
        and boundary.denied == 0
        and len(transport_trace) == 3
        and len(results) == 3
        and all(case["response_origin"] == "provider_response" for case in results),
    }


def redact(value: typing.Any, key: str) -> typing.Any:
    """Redact before JSON encoding, including a credential containing escaped characters."""
    if isinstance(value, str):
        return value.replace(key, "[REDACTED]") if key else value
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if isinstance(value, dict):
        return {redact(name, key): redact(item, key) for name, item in value.items()}
    return value


def run_child(
    mode: str, key: str = "", authorization: dict[str, typing.Any] | None = None
) -> dict[str, typing.Any]:
    """Send a key only through the private child stdin, never argv, env or logs."""
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child"],
            input=json.dumps(
                {"mode": mode, "key": key, "authorization": authorization}
            ),
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=sanitized_environment(),
            cwd=ROOT,
            timeout=120,
            check=False,
        )
        output = result.stdout
    except subprocess.TimeoutExpired as error:
        output = error.stdout or b""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        result = None
    try:
        lines = [json.loads(line) for line in output.splitlines()]
        report = (
            lines[-1].get("report")
            if lines and result and not result.returncode
            else None
        )
    except (ValueError, TypeError, AttributeError):
        raise Refused("isolated_child_output_invalid") from None
    if not isinstance(report, dict):
        if mode != "live":
            raise Refused("isolated_child_failed")
        progress = [row["progress"] for row in lines if "progress" in row]
        report = {
            "all_generated": False,
            "external_attempts": sum(
                row.get("http_status") is None for row in progress
            ),
            "business_actions": [],
            "progress": progress,
            "error": "child_timeout_or_failure_usage_unknown",
            "scenarios": [],
        }
    # Defense in depth: even a provider echo must never persist the actual credential.
    if key:
        report = redact(report, key)
    return report


def make_plan(
    config: dict[str, str], offline: dict[str, typing.Any]
) -> dict[str, typing.Any]:
    """Bind the proposed model change, fixed scenarios, source code and usage envelope."""
    return {
        "version": 1,
        "scope": "isolated_response_generator_not_end_to_end_agent",
        "provider": "DeepSeek",
        "detected_model": config["AI_MODEL"],
        "proposed_model": PROPOSED_MODEL,
        "base_url": BASE_URL,
        "key_present": bool(config["OPENAI_API_KEY"]),
        "key_verified": False,
        "account_balance_checked": False,
        "model_change_requires_approval": config["AI_MODEL"] != PROPOSED_MODEL,
        "calls_maximum": 3,
        "sdk_retries": 0,
        "output_tokens_per_call": OUTPUT_TOKENS,
        "peak_uncached_rates_usd_per_million": {
            "input": str(INPUT_RATE),
            "output": str(OUTPUT_RATE),
        },
        "pricing_review_date": "2026-10-26",
        "proposed_budget_usd": str(BUDGET),
        "estimate_usd_peak_uncached": str(
            sum(
                Decimal(case["events"][0]["projection"]["estimated_usd_peak_uncached"])
                for case in offline["scenarios"]
            )
        ),
        "estimate_is_not_a_billing_guarantee": True,
        "scenarios": list(SCENARIOS),
        "business_tools": [],
        "reviewed_sources": SOURCES,
        "launcher_sha256": sha(Path(__file__).read_bytes()),
        "sdk_versions": {
            name: importlib.metadata.version(name)
            for name in ("openai", "httpx", "python-dotenv")
        },
    }


def write_evidence(name: str, value: object) -> None:
    """Write only local ignored evidence without overwriting an existing result."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / name
    if target.exists() and name.startswith("plan-"):
        if json.loads(target.read_text(encoding="utf-8")) == value:
            return
        raise Refused("existing_plan_content_mismatch")
    with target.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> int:
    """Preparation is offline; live mode additionally requires exact reviewed-plan approval."""
    if sys.argv[1:] == ["--child"]:
        try:
            payload = json.loads(sys.stdin.read(65536))
            report = child(payload)
            print(json.dumps({"report": report}, ensure_ascii=True))
            return 0
        except Exception as error:  # noqa: BLE001 -- no secret tracebacks.
            print(
                json.dumps(
                    {
                        "error": "isolated_child_failed",
                        "error_type": type(error).__name__,
                        "missing_symbol": (
                            error.name if isinstance(error, NameError) else None
                        ),
                        "reason": str(error) if isinstance(error, Refused) else None,
                    }
                )
            )
            return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run"])
    parser.add_argument("--approval-sha256")
    parser.add_argument("--allow-three-provider-calls", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--budget-usd")
    args = parser.parse_args()
    try:
        if args.command == "run" and not (
            args.allow_three_provider_calls
            and args.approval_sha256
            and args.model == PROPOSED_MODEL
            and args.budget_usd == str(BUDGET)
        ):
            raise Refused("separate_provider_authorization_required")
        verify_sources()
        config = configuration()
        offline = run_child("offline")
        plan = make_plan(config, offline)
        fingerprint = sha(canonical(plan))
        if args.command == "prepare":
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            write_evidence(f"offline-{stamp}.json", offline)
            write_evidence(f"plan-{fingerprint}.json", plan)
            print(
                json.dumps(
                    {
                        "status": "prepared_no_provider_call",
                        "plan_sha256": fingerprint,
                        "provider": "DeepSeek",
                        "detected_model": plan["detected_model"],
                        "proposed_model": PROPOSED_MODEL,
                        "estimated_usd": plan["estimate_usd_peak_uncached"],
                        "key_present": plan["key_present"],
                    }
                )
            )
            return 0
        approved_path = OUTPUT / f"plan-{fingerprint}.json"
        if (
            args.approval_sha256 != fingerprint
            or not approved_path.is_file()
            or canonical(json.loads(approved_path.read_text(encoding="utf-8")))
            != canonical(plan)
        ):
            raise Refused("approved_plan_mismatch")
        if not config["OPENAI_API_KEY"]:
            raise Refused("provider_key_missing")
        report = run_child(
            "live",
            config["OPENAI_API_KEY"],
            {
                "plan_sha256": fingerprint,
                "allow_three_provider_calls": True,
                "model": args.model,
                "budget_usd": args.budget_usd,
            },
        )
        report["approved_plan_sha256"] = fingerprint
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        write_evidence(f"provider-result-{stamp}.json", report)
        print(
            json.dumps(
                {
                    "status": (
                        "responses_received_semantic_review_required"
                        if report["all_generated"]
                        else "stopped_for_review"
                    ),
                    "provider_calls_attempted": report["external_attempts"],
                    "business_actions": [],
                }
            )
        )
        return 0 if report["all_generated"] else 2
    except Refused as error:
        print(json.dumps({"status": "refused", "reason": str(error)}))
        return 2
    except Exception:  # noqa: BLE001 -- fail closed with a fixed public diagnostic.
        print('{"status":"refused","reason":"preparation_failed"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
