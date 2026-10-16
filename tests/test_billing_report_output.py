# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify local JSON report output with all operational side effects mocked."""

from __future__ import annotations

import argparse
import io
import json
import unittest
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import (
    AsyncMock,
    patch,
)

from scripts import billing_operations

# ==============================================
# ISOLATED REPORT OUTPUT VERIFICATION
# ==============================================


class TestBillingReportOutput(unittest.TestCase):
    """Exercise the command entry point without database or network access."""

    def setUp(self) -> None:
        """Replace the project destination and every operational dispatcher."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project_root = Path(temporary.name).resolve()
        self.enterContext(
            patch.object(billing_operations, "PROJECT_ROOT", self.project_root)
        )
        self.operation = AsyncMock(return_value={"operation": "preflight"})
        self.enterContext(
            patch.object(billing_operations, "run_operation", self.operation)
        )
        self.logger = self.enterContext(patch.object(billing_operations, "logger"))

    def invoke(self, *, arguments: list[str]) -> tuple[int, str]:
        """Capture printed JSON while invoking only the mocked dispatcher."""
        output = io.StringIO()
        with (
            patch("sys.argv", ["billing_operations.py", *arguments]),
            redirect_stdout(output),
        ):
            status = billing_operations.main()
        return status, output.getvalue()

    def test_success_report_excludes_console_log_records(self) -> None:
        """Keep one valid UTF-8 JSON document for either read-only operation."""

        async def noisy_operation(*, arguments: argparse.Namespace) -> dict[str, str]:
            """Represent startup console noise without importing or calling clients."""
            print(json.dumps({"event": "test_only_startup"}))
            return {"operation": arguments.operation, "summary": "Vérifié"}

        self.operation.side_effect = noisy_operation
        for operation in ("preflight", "constraint-diagnostics"):
            with self.subTest(operation=operation):
                status, console = self.invoke(
                    arguments=[operation, "--output", f"{operation}.json"]
                )
                output_path = (
                    self.project_root
                    / "artifacts"
                    / "billing-reports"
                    / f"{operation}.json"
                )
                raw = output_path.read_bytes()
                result = json.loads(raw.decode("utf-8"))
                self.assertEqual(status, 0)
                self.assertEqual(
                    result,
                    {"ok": True, "operation": operation, "summary": "Vérifié"},
                )
                self.assertIn("test_only_startup", console)
                self.assertNotIn(b"test_only_startup", raw)
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
                self.assertEqual(list(output_path.parent.glob("*.tmp")), [])

    def test_operation_error_is_saved_without_private_exception_text(self) -> None:
        """Store the same sanitized failure printed to the console."""
        self.operation.side_effect = RuntimeError("test-only-private-connection-value")
        status, console = self.invoke(
            arguments=["preflight", "--output", "failed-preflight.json"]
        )
        saved = (
            self.project_root
            / "artifacts"
            / "billing-reports"
            / "failed-preflight.json"
        ).read_text(encoding="utf-8")
        result = json.loads(saved)
        self.assertEqual(status, 1)
        self.assertEqual(result, json.loads(console))
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "billing_operation_failed")
        self.assertNotIn("test-only-private-connection-value", saved + console)

    def test_invalid_filenames_fail_before_operation(self) -> None:
        """Deny paths, reserved names, and non-JSON output destinations."""
        invalid_names = (
            "../report.json",
            "..\\report.json",
            "D:\\report.json",
            "/report.json",
            "",
            ".env",
            ".json",
            "report.txt",
            "CON.json",
            "NUL.extra.json",
            "x" * 129 + ".json",
        )
        for filename in invalid_names:
            with self.subTest(filename=filename):
                with (
                    redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as exit,
                ):
                    self.invoke(arguments=["preflight", "--output", filename])
                self.assertEqual(exit.exception.code, 2)
        self.operation.assert_not_awaited()
        self.assertFalse((self.project_root / "artifacts").exists())

    def test_parent_escape_fails_before_operation(self) -> None:
        """Reject an artifact directory resolving through an outside junction."""
        original_resolve = Path.resolve
        directory = self.project_root / "artifacts" / "billing-reports"

        def resolve_destination(path: Path, strict: bool = False) -> Path:
            """Model a junction target without creating Windows filesystem links."""
            if path == directory:
                return self.project_root.parent / "outside-test-project"
            return original_resolve(path, strict=strict)

        with (
            patch.object(Path, "resolve", resolve_destination),
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as exit,
        ):
            self.invoke(arguments=["preflight", "--output", "report.json"])
        self.assertEqual(exit.exception.code, 2)
        self.operation.assert_not_awaited()

    def test_failed_atomic_replace_preserves_existing_report(self) -> None:
        """Report write failures safely and remove incomplete temporary output."""
        output_path = (
            self.project_root / "artifacts" / "billing-reports" / "preflight.json"
        )
        output_path.parent.mkdir(parents=True)
        original = '{"historical": true}\n'
        output_path.write_text(original, encoding="utf-8")
        with patch.object(
            Path,
            "replace",
            side_effect=PermissionError("test-only-private-file-details"),
        ):
            status, console = self.invoke(
                arguments=["preflight", "--output", output_path.name]
            )
        result = json.loads(console)
        self.assertEqual(status, 1)
        self.assertEqual(result["reason"], "billing_report_write_failed")
        self.assertNotIn("test-only-private-file-details", console)
        self.assertEqual(output_path.read_text(encoding="utf-8"), original)
        self.assertEqual(list(output_path.parent.glob("*.tmp")), [])
        self.logger.error.assert_called_once()

    def test_no_output_keeps_existing_console_behavior(self) -> None:
        """Avoid creating any artifact unless a filename is explicitly requested."""
        status, console = self.invoke(arguments=["preflight"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(console), {"ok": True, "operation": "preflight"})
        self.assertFalse((self.project_root / "artifacts").exists())

    def test_mutating_commands_do_not_accept_output_option(self) -> None:
        """Leave migration, identity binding, and webhook command contracts intact."""
        commands = (
            [
                "migrate",
                "--confirm-database",
                "test-only",
                "--expected-revision",
                "test",
            ],
            [
                "bind-admin",
                "--confirm-database",
                "test-only",
                "--admin-id",
                "1",
                "--subject",
                "test-only-subject",
            ],
            ["configure-webhook", "--url", "https://test.invalid/webhook"],
        )
        for command in commands:
            with self.subTest(command=command[0]):
                with (
                    redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as exit,
                ):
                    self.invoke(arguments=[*command, "--output", "report.json"])
                self.assertEqual(exit.exception.code, 2)
        self.operation.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
