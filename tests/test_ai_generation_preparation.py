# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Standalone offline isolation checks; run directly, without database conftest."""

from __future__ import annotations

import importlib.util
import io
import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ai_generation_preparation", ROOT / "scripts/prepare_ai_generation.py"
)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


class PreparationTests(unittest.TestCase):
    """Exercise real source definitions while every provider completion is synthetic."""

    @classmethod
    def setUpClass(cls) -> None:
        """Create one private source namespace, never the app package."""
        cls.previous_logging = logging.root.manager.disable
        cls.preexisting_modules = set(sys.modules)
        logging.disable(logging.CRITICAL)
        cls.scope = probe.source_namespace(lambda **_kwargs: None)

    @classmethod
    def tearDownClass(cls) -> None:
        """Preserve logging behavior when collected alongside unrelated tests."""
        logging.disable(cls.previous_logging)

    def request(self, **overrides: object) -> dict[str, object]:
        """Build a small exact approved SDK request."""
        return {
            "model": probe.PROPOSED_MODEL,
            "max_tokens": 500,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": "Synthetic system."},
                {"role": "user", "content": "Synthetic question."},
            ],
            **overrides,
        }

    def admission_case(
        self, changed_field: str | None = None, approval: str | None = None
    ) -> tuple[int, dict[str, Any], list[Any]]:
        """Exercise real parent admission; replace both child launches with no-I/O mocks."""
        config = {
            "OPENAI_API_KEY": "synthetic-key-not-real",
            "OPENAI_BASE_URL": probe.BASE_URL,
            "AI_MODEL": "deepseek-chat",
        }
        offline = {
            "scenarios": [
                {"events": [{"projection": {"estimated_usd_peak_uncached": "0.0005"}}]}
                for _ in probe.SCENARIOS
            ]
        }
        plan = probe.make_plan(config, offline)
        fingerprint = probe.sha(probe.canonical(plan))
        stored = json.loads(probe.canonical(plan))
        self.assertIsInstance(plan["scenarios"][0], tuple)
        self.assertIsInstance(stored["scenarios"][0], list)
        if changed_field == "scenarios":
            stored["scenarios"][0][1] += " Unauthorized change."
        elif changed_field == "proposed_model":
            stored["proposed_model"] = "unapproved-model"
        elif changed_field == "calls_maximum":
            stored["calls_maximum"] = 3.0
        child = Mock(
            side_effect=[
                offline,
                {"all_generated": True, "external_attempts": 3, "business_actions": []},
            ]
        )
        arguments = [
            str(ROOT / "scripts/prepare_ai_generation.py"),
            "run",
            "--approval-sha256",
            approval if approval is not None else fingerprint,
            "--allow-three-provider-calls",
            "--model",
            probe.PROPOSED_MODEL,
            "--budget-usd",
            "0.01",
        ]
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, f"plan-{fingerprint}.json").write_text(
                json.dumps(stored, ensure_ascii=False), encoding="utf-8"
            )
            with patch.object(probe, "OUTPUT", Path(directory)), patch.object(
                probe, "configuration", return_value=config
            ), patch.object(probe, "run_child", child), patch.object(
                probe, "write_evidence"
            ), patch.object(
                probe, "live_client", side_effect=AssertionError("provider forbidden")
            ) as provider, patch.object(
                socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden")
            ) as dns, patch.object(
                sys, "argv", arguments
            ), redirect_stdout(
                output
            ):
                result = probe.main()
                provider.assert_not_called()
                dns.assert_not_called()
        return result, json.loads(output.getvalue()), child.call_args_list

    def test_positive_plan_admission_accepts_json_round_trip_of_tuple_scenarios(
        self,
    ) -> None:
        """The unchanged approved JSON plan admits exactly the simulated child stage."""
        result, report, calls = self.admission_case()
        self.assertEqual(result, 0, report)
        self.assertEqual(
            report["status"], "responses_received_semantic_review_required"
        )
        self.assertEqual([call.args[0] for call in calls], ["offline", "live"])
        self.assertEqual(calls[1].args[2]["model"], "deepseek-flash")
        self.assertEqual(calls[1].args[2]["budget_usd"], "0.01")

    def test_normalization_still_refuses_a_changed_scenario(self) -> None:
        """A real message change is not a tuple/list representation difference."""
        result, report, calls = self.admission_case(changed_field="scenarios")
        self.assertEqual(result, 2)
        self.assertEqual(report["reason"], "approved_plan_mismatch")
        self.assertEqual([call.args[0] for call in calls], ["offline"])

    def test_normalization_still_refuses_a_changed_model(self) -> None:
        """Stored model changes are refused before the simulated provider stage."""
        result, report, calls = self.admission_case(changed_field="proposed_model")
        self.assertEqual(result, 2)
        self.assertEqual(report["reason"], "approved_plan_mismatch")
        self.assertEqual([call.args[0] for call in calls], ["offline"])

    def test_normalization_still_refuses_an_incorrect_fingerprint(self) -> None:
        """Canonical comparison does not replace the exact approval fingerprint."""
        result, report, calls = self.admission_case(approval="0" * 64)
        self.assertEqual(result, 2)
        self.assertEqual(report["reason"], "approved_plan_mismatch")
        self.assertEqual([call.args[0] for call in calls], ["offline"])

    def test_old_approval_does_not_authorize_the_corrected_launcher(self) -> None:
        """The prior code-bound approval cannot be carried into this correction."""
        result, report, calls = self.admission_case(
            approval="7ba50be8a76d7870d9bb9f080b622d311b9f820309fef558db025e46254281a8"
        )
        self.assertEqual(result, 2)
        self.assertEqual(report["reason"], "approved_plan_mismatch")
        self.assertEqual([call.args[0] for call in calls], ["offline"])

    def test_normalization_refuses_json_scalar_type_changes(self) -> None:
        """Equal Python numbers of different JSON representations are not ignored."""
        result, report, calls = self.admission_case(changed_field="calls_maximum")
        self.assertEqual(result, 2)
        self.assertEqual(report["reason"], "approved_plan_mismatch")
        self.assertEqual([call.args[0] for call in calls], ["offline"])

    def test_total_software_budget_is_checked_before_any_provider_call(self) -> None:
        """An insufficient estimate allowance refuses even a valid fixed request."""
        provider = Mock(side_effect=AssertionError("provider forbidden"))
        gate = probe.CompletionGate(provider, live=False)
        with patch.object(probe, "BUDGET", Decimal("0.00001")), self.assertRaisesRegex(
            probe.Refused, "total_budget_exceeded"
        ):
            gate.create(**self.request())
        provider.assert_not_called()
        self.assertEqual(gate.events, [])

    def test_original_source_hashes_and_definition_locations(self) -> None:
        """Production definitions are pinned and their method filenames retained."""
        probe.verify_sources()
        for name, filename in [
            ("AgentEngine", "app/agent/engine.py"),
            ("AIClient", "app/core/ai_client.py"),
            ("ResponseGenerator", "app/agent/response_generator.py"),
        ]:
            self.assertEqual(self.scope[name].__init__.__code__.co_filename, filename)

    def test_source_drift_refuses_loading(self) -> None:
        """Changing reviewed content requires a fresh source review."""
        with patch.dict(
            probe.SOURCES, {"app/core/ai_client.py": "0" * 64}
        ), self.assertRaisesRegex(probe.Refused, "reviewed_source_changed"):
            probe.source_namespace(lambda **_kwargs: None)

    def test_no_business_package_or_action_class_loaded(self) -> None:
        """Neither package initializers nor executable business classes exist here."""
        self.assertFalse(
            any(
                name.split(".")[0] in probe.FORBIDDEN_IMPORTS
                for name in set(sys.modules) - self.preexisting_modules
            )
        )
        for name in [
            "AsyncSessionLocal",
            "OrderFoodAction",
            "ActionRegistry",
            "place_customer_order",
            "redis_client",
        ]:
            self.assertNotIn(name, self.scope)

    def test_environment_removes_all_credentials_and_proxies(self) -> None:
        """Only OS essentials and process-local safety booleans cross the boundary."""
        with patch.dict(
            os.environ,
            {
                "DEBUG": "release",
                "DATABASE_URL": "fake-db",
                "TEST_DATABASE_URL": "fake-test",
                "REDIS_URL": "fake-redis",
                "OPENAI_API_KEY": "fake-key",
                "HTTP_PROXY": "fake-proxy",
                "TELEGRAM_TOKEN": "fake-token",
            },
        ):
            environment = probe.sanitized_environment()
            self.assertEqual(environment["DEBUG"], "false")
            for name in [
                "DATABASE_URL",
                "TEST_DATABASE_URL",
                "REDIS_URL",
                "OPENAI_API_KEY",
                "HTTP_PROXY",
                "TELEGRAM_TOKEN",
            ]:
                self.assertNotIn(name, environment)
            self.assertEqual(os.environ["DEBUG"], "release")
            for name in [
                "DB_ECHO",
                "OIDC_DIAGNOSTICS_ENABLED",
                "OIDC_ALLOW_LOCAL_HTTP",
            ]:
                self.assertEqual(environment[name], "false")

    def test_configuration_only_reads_selected_variables_without_interpolation(
        self,
    ) -> None:
        """Unrelated file values are not loaded or interpolated into the key."""
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".env").write_text(
                "DATABASE_URL=unrelated\nOPENAI_API_KEY=${DO_NOT_READ}\nOPENAI_BASE_URL=https://api.deepseek.com\nAI_MODEL=deepseek-chat\n",
                encoding="utf-8",
            )
            with patch.object(probe, "ROOT", Path(directory)), patch.dict(
                os.environ, {}, clear=True
            ), self.assertRaisesRegex(probe.Refused, "key_configuration_invalid"):
                probe.configuration()

    def test_custom_endpoint_is_refused_without_echoing_it(self) -> None:
        """No arbitrary host, proxy route or credential-bearing URL is admitted."""
        for url in [
            "http://api.deepseek.com",
            "https://api.deepseek.com.evil.invalid",
            "https://user:secret@api.deepseek.com",
            "https://api.deepseek.com?token=secret",
            "https://api.deepseek.com:444",
            "https://api.openai.com/v1",
        ]:
            with self.subTest(url=url), patch.dict(
                os.environ, {"OPENAI_BASE_URL": url}
            ), self.assertRaisesRegex(probe.Refused, "provider_endpoint_not_approved"):
                probe.configuration()

    def test_engine_probe_records_actual_rules_and_known_french_detection_limit(
        self,
    ) -> None:
        """Do not transform stock replies or an incorrect language into a generative pass."""
        rows = probe.engine_observation(self.scope)
        self.assertEqual([row["detected_language"] for row in rows], ["en", "en", "ar"])
        self.assertEqual(
            [row["intent"] for row in rows], ["unknown", "greeting", "greeting"]
        )
        self.assertTrue(
            all(
                row["provider_calls"] == 0 and row["business_actions"] == []
                for row in rows
            )
        )
        self.assertTrue(
            all(row["provenance"] == "offline_rules_or_template" for row in rows)
        )

    def test_memory_is_new_ram_for_each_synthetic_case(self) -> None:
        """No session or restaurant context is inherited by another instance."""
        first, second = self.scope["MemoryManager"](), self.scope["MemoryManager"]()
        probe.complete(first.create_session(session_id="synthetic", user_id=980001))
        self.assertIsNone(probe.complete(second.get_session(session_id="synthetic")))
        self.assertIsNone(first.redis_client)
        self.assertIsNone(second.redis_client)

    def test_no_business_executor_has_no_registry(self) -> None:
        """Even a mutation intent has no callable business implementation."""
        executor = probe.NoBusinessExecutor()
        self.assertEqual(vars(executor), {})
        for name in ["order_food", "cancel_order", "complaint", "reserve_table"]:
            result = probe.complete(executor.execute(intent_result={"intent": name}))
            self.assertFalse(result["success"])
            self.assertIsNone(result["action"])

    def test_three_exact_messages_and_explicit_mock_provenance(self) -> None:
        """All three generation mechanics work with the original classes, offline only."""
        gate = probe.CompletionGate(probe.mock_completion, live=False)
        rows = probe.generation_cases(self.scope, gate, "offline-placeholder")
        self.assertEqual(
            [(row["language"], row["message"]) for row in rows], list(probe.SCENARIOS)
        )
        self.assertEqual(len(gate.events), 3)
        self.assertTrue(all(row["response_origin"] == "offline_mock" for row in rows))
        self.assertTrue(
            all(not event["provider_response_received"] for event in gate.events)
        )

    def test_fourth_completion_refused(self) -> None:
        """No implicit retries or extra scenario calls fit the completion budget."""
        gate = probe.CompletionGate(probe.mock_completion, live=False)
        for _ in range(3):
            gate.create(**self.request())
        with self.assertRaisesRegex(probe.Refused, "completion_contract_refused"):
            gate.create(**self.request())

    def test_tools_models_and_output_overrides_refused(self) -> None:
        """Unsupported calls never reach even the fake provider."""
        for value in [
            {"tools": []},
            {"stream": True},
            {"n": 2},
            {"model": "deepseek-chat"},
            {"max_tokens": 501},
            {"messages": [{"role": "tool", "content": "no"}]},
        ]:
            with self.subTest(value=value):
                gate = probe.CompletionGate(
                    lambda **_: self.fail("provider invoked"), live=False
                )
                with self.assertRaises(probe.Refused):
                    gate.create(**self.request(**value))
                self.assertEqual(gate.events, [])

    def test_oversized_prompt_refused(self) -> None:
        """Prompt input bounds are enforced before a provider event is reserved."""
        with self.assertRaisesRegex(probe.Refused, "prompt_budget_exceeded"):
            probe.cost_projection([{"content": "a" * 6001}])

    def test_original_generator_short_circuit_uses_no_provider(self) -> None:
        """The harness explicitly preserves the observed generator limitation."""
        gate = probe.CompletionGate(probe.mock_completion, live=False)
        self.scope["OpenAI"] = lambda **_: types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=gate)
        )
        client = self.scope["AIClient"](
            api_key="offline-placeholder", model=probe.PROPOSED_MODEL
        )
        generator = self.scope["ResponseGenerator"](ai_client=client)
        for intent, result in [
            ("greeting", None),
            (
                "unknown",
                self.scope["ActionResponse"](True, "Predetermined action reply"),
            ),
            ("unknown", self.scope["ActionResponse"](False, "", error="unknown")),
        ]:
            self.assertTrue(
                probe.complete(
                    generator.generate(
                        intent=intent, language="fr", action_result=result
                    )
                )
            )
        self.assertEqual(gate.events, [])

    def test_provider_error_is_a_fallback_and_stops_after_first_case(self) -> None:
        """AIClient's caught exception cannot count as a received generated response."""

        def failed(**_kwargs: object) -> object:
            raise RuntimeError("synthetic fake secret must not appear")

        gate = probe.CompletionGate(failed, live=True)
        rows = probe.generation_cases(self.scope, gate, "offline-placeholder")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["response_origin"], "fallback_or_error")
        self.assertEqual(gate.events[0]["provenance"], "provider_error")
        self.assertNotIn("fake secret", json.dumps(rows))

    def test_truncation_empty_reply_and_missing_usage_are_not_success(self) -> None:
        """A successful HTTP response is insufficient evidence of a complete answer."""
        for content, finish, usage in [
            ("", "stop", None),
            (
                "partial",
                "length",
                types.SimpleNamespace(
                    prompt_tokens=10, completion_tokens=10, total_tokens=20
                ),
            ),
            ("text", "stop", None),
        ]:
            with self.subTest(content=content, finish=finish):
                response = types.SimpleNamespace(
                    id="synthetic",
                    model=probe.PROPOSED_MODEL,
                    usage=usage,
                    choices=[
                        types.SimpleNamespace(
                            message=types.SimpleNamespace(content=content),
                            finish_reason=finish,
                        )
                    ],
                )
                gate = probe.CompletionGate(
                    lambda value=response, **_: value, live=True
                )
                with self.assertRaises(probe.Refused):
                    gate.create(**self.request())

    def test_usage_and_received_response_are_recorded_separately(self) -> None:
        """Numeric returned usage yields an estimate, not an invented billed charge."""
        response = types.SimpleNamespace(
            id="synthetic-completion",
            model=probe.PROPOSED_MODEL,
            usage=types.SimpleNamespace(
                prompt_tokens=100, completion_tokens=50, total_tokens=150
            ),
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(
                        content="Synthetic transport response"
                    ),
                    finish_reason="stop",
                )
            ],
        )
        gate = probe.CompletionGate(lambda **_: response, live=True)
        gate.create(**self.request())
        event = gate.events[0]
        self.assertEqual(event["provenance"], "provider_response")
        self.assertEqual(event["usage"]["total_tokens"], 150)
        self.assertTrue(event["provider_response_received"])
        self.assertEqual(event["estimated_cost_from_usage_usd_peak"], "0.00009")

    def test_child_offline_really_opens_no_network_and_keeps_safety_flags(self) -> None:
        """Run the full child path, not a mocked engine or namespace loader."""
        report = probe.run_child("offline")
        self.assertEqual(report["external_attempts"], 0)
        self.assertEqual(report["denied_operations"], 0)
        self.assertEqual(report["business_modules_loaded"], [])
        self.assertEqual(report["effective_debug"], "false")
        self.assertFalse(report["all_generated"])

    def test_run_requires_distinct_authorization_before_configuration(self) -> None:
        """The ordinary run command cannot accidentally enable provider access."""
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(ROOT / "scripts/prepare_ai_generation.py"),
                "run",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            json.loads(result.stdout)["reason"],
            "separate_provider_authorization_required",
        )

    def test_child_live_mode_alone_is_not_an_authorization(self) -> None:
        """Direct child invocation cannot bypass the reviewed-plan admission."""
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(ROOT / "scripts/prepare_ai_generation.py"),
                "--child",
            ],
            input=json.dumps({"mode": "live", "key": "offline-placeholder"}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 2)

    def test_audit_refuses_business_imports_mutations_and_nonprovider_network(
        self,
    ) -> None:
        """Exercise denied event classes without touching any real resource."""
        events = [
            ("import", ("sqlalchemy",)),
            ("import", ("app.main",)),
            ("socket.connect", (None, ("127.0.0.1", 5432))),
            ("socket.bind", (None, ("127.0.0.1", 0))),
            ("socket.getaddrinfo", ("neon.invalid", 5432)),
            ("subprocess.Popen", ()),
            ("open", ("fake", "w", os.O_WRONLY)),
            ("os.remove", ("fake",)),
        ]
        for event, arguments in events:
            with self.subTest(event=event), self.assertRaisesRegex(
                probe.Refused, "isolated_operation_refused"
            ):
                probe.Boundary().audit(event, arguments)

    def test_actual_socket_and_business_import_are_stopped_in_a_child(self) -> None:
        """The audit hook stops real import/connect attempts before any connection."""
        code = """
import importlib.util,json,sys,socket
spec=importlib.util.spec_from_file_location('probe',sys.argv[1]); p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
b=p.Boundary();sys.addaudithook(b.audit)
results=[]
for operation in [lambda: __import__('sqlalchemy'),lambda: socket.create_connection(('127.0.0.1',5432)),lambda: __import__('app.main')]:
 try: operation()
 except p.Refused: results.append('refused')
print(json.dumps(results))
"""
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                "-c",
                code,
                str(ROOT / "scripts/prepare_ai_generation.py"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), ["refused"] * 3)

    def test_provider_boundary_allows_only_pinned_https_addresses(self) -> None:
        """A provider request scope is not general network access."""
        boundary = probe.Boundary()
        boundary.provider_active = True
        boundary.allowed_addresses = {"192.0.2.1"}
        boundary.audit("socket.getaddrinfo", ("api.deepseek.com", 443))
        boundary.audit("socket.connect", (None, ("192.0.2.1", 443)))
        for event, arguments in [
            ("socket.getaddrinfo", ("different.invalid", 443)),
            ("socket.connect", (None, ("192.0.2.2", 443))),
            ("socket.connect", (None, ("192.0.2.1", 5432))),
        ]:
            with self.assertRaises(probe.Refused):
                boundary.audit(event, arguments)

    def test_real_sdk_request_shape_with_fully_mocked_transport_and_dns(self) -> None:
        """Exercise installed SDK serialization, including thinking=false and retry settings."""
        import httpx

        requests = []

        def respond(_transport: object, request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                request=request,
                json={
                    "id": "synthetic-http",
                    "object": "chat.completion",
                    "created": 1,
                    "model": probe.PROPOSED_MODEL,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "Synthetic HTTP response",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150,
                    },
                },
            )

        with patch.object(
            httpx.HTTPTransport, "handle_request", autospec=True, side_effect=respond
        ), patch.object(
            socket,
            "getaddrinfo",
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 443))
            ],
        ):
            trace = []
            sdk = probe.live_client("offline-placeholder", probe.Boundary(), trace)
            try:
                gate = probe.CompletionGate(sdk.chat.completions.create, live=True)
                response = gate.create(**self.request())
                self.assertEqual(response.id, "synthetic-http")
                self.assertEqual(sdk.max_retries, 0)
                self.assertFalse(sdk._client.follow_redirects)
                self.assertFalse(sdk._client.trust_env)
                body = json.loads(requests[0].content)
                self.assertEqual(body["thinking"], {"type": "disabled"})
                self.assertEqual(body["max_tokens"], 500)
                self.assertNotIn("tools", body)
                self.assertEqual(
                    str(requests[0].url), probe.BASE_URL + "/chat/completions"
                )
                self.assertEqual(len(trace), 1)
            finally:
                sdk.close()

    def test_redaction_precedes_encoding_and_covers_nested_provider_echoes(
        self,
    ) -> None:
        """A quoted credential cannot survive in nested responses or dictionary keys."""
        key = 'synthetic-"credential\\value'
        result = probe.redact({key: [f"echo {key}", {"response": key}]}, key)
        self.assertNotIn(key, json.dumps(result))
        self.assertEqual(
            result, {"[REDACTED]": ["echo [REDACTED]", {"response": "[REDACTED]"}]}
        )

    def test_plan_evidence_is_idempotent_and_never_overwrites_a_different_plan(
        self,
    ) -> None:
        """Re-running preparation preserves the exact reviewed evidence."""
        with tempfile.TemporaryDirectory() as directory, patch.object(
            probe, "OUTPUT", Path(directory)
        ):
            probe.write_evidence("plan-test.json", {"synthetic": 1})
            probe.write_evidence("plan-test.json", {"synthetic": 1})
            with self.assertRaisesRegex(
                probe.Refused, "existing_plan_content_mismatch"
            ):
                probe.write_evidence("plan-test.json", {"synthetic": 2})
            self.assertEqual(
                json.loads(Path(directory, "plan-test.json").read_text()),
                {"synthetic": 1},
            )

    def test_wrong_plan_hash_refuses_before_provider_access(self) -> None:
        """Even the explicit run flags do not admit an unapproved manifest."""
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(ROOT / "scripts/prepare_ai_generation.py"),
                "run",
                "--allow-three-provider-calls",
                "--model",
                probe.PROPOSED_MODEL,
                "--budget-usd",
                "0.01",
                "--approval-sha256",
                "0" * 64,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["reason"], "approved_plan_mismatch")

    def test_transport_refuses_foreign_url_before_dns_or_http(self) -> None:
        """The dedicated SDK client cannot be reused as a business HTTP client."""
        import httpx

        with patch.object(
            httpx.HTTPTransport,
            "handle_request",
            side_effect=AssertionError("forward forbidden"),
        ) as forward, patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden")
        ) as dns:
            sdk = probe.live_client("offline-placeholder", probe.Boundary(), [])
            try:
                for url in [
                    "https://api.deepseek.com/models",
                    "https://foreign.invalid/chat/completions",
                    "http://127.0.0.1:5432/",
                ]:
                    with self.assertRaisesRegex(
                        probe.Refused, "http_destination_refused"
                    ):
                        sdk._client.post(url, json={})
                forward.assert_not_called()
                dns.assert_not_called()
            finally:
                sdk.close()

    def test_http_errors_and_redirects_do_not_retry_or_follow(self) -> None:
        """A failed or redirecting provider consumes one attempt and stops."""
        import httpx

        for status in [301, 503]:
            with self.subTest(status=status), patch.object(
                httpx.HTTPTransport,
                "handle_request",
                autospec=True,
                side_effect=lambda _transport, request, code=status: httpx.Response(
                    code,
                    request=request,
                    headers={"Location": "https://foreign.invalid"},
                    json={"error": {"message": "synthetic private error"}},
                ),
            ) as forward, patch.object(
                socket,
                "getaddrinfo",
                return_value=[
                    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 443))
                ],
            ), redirect_stdout(
                io.StringIO()
            ):
                trace = []
                sdk = probe.live_client("offline-placeholder", probe.Boundary(), trace)
                try:
                    gate = probe.CompletionGate(sdk.chat.completions.create, live=True)
                    with self.assertRaisesRegex(
                        probe.Refused, "provider_request_failed"
                    ):
                        gate.create(**self.request())
                    self.assertEqual(forward.call_count, 1)
                    self.assertEqual(len(trace), 1)
                    self.assertEqual(trace[0]["http_status"], status)
                    self.assertNotIn("private error", json.dumps(gate.events))
                finally:
                    sdk.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
