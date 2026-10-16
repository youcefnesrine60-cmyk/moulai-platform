# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Export complete reviewed Python sources without credentials or runtime data."""

# ==============================================
# IMPORTS
# ==============================================

import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import (
    ZIP_DEFLATED,
    ZipFile,
)

# ==============================================
# REVIEW SOURCE INVENTORY
# ==============================================


def reviewed_files(*, root: Path) -> list[Path]:
    """Select existing changed Python files from supported source directories."""
    commands = (
        [
            "git",
            "-c",
            "core.quotePath=false",
            "diff",
            "--name-only",
            "--diff-filter=ACMRTUXB",
            "HEAD",
        ],
        [
            "git",
            "-c",
            "core.quotePath=false",
            "ls-files",
            "--others",
            "--exclude-standard",
        ],
    )
    names: set[str] = set()
    for command in commands:
        names.update(
            subprocess.check_output(
                command, cwd=root, text=True, encoding="utf-8", stderr=subprocess.PIPE
            ).splitlines()
        )
    allowed = {"app", "scripts", "tests", "alembic", "alembic_test"}
    return sorted(
        path
        for name in names
        if (path := root / name).suffix == ".py"
        and path.is_file()
        and path.relative_to(root).parts[0] in allowed
        and path.resolve().is_relative_to(root)
    )


# ==============================================
# REMOVED SOURCE INVENTORY
# ==============================================


def removed_files(*, root: Path) -> list[str]:
    """Record obsolete Python paths without deleting or modifying any files."""
    output = subprocess.check_output(
        [
            "git",
            "-c",
            "core.quotePath=false",
            "diff",
            "--name-only",
            "--diff-filter=D",
            "HEAD",
        ],
        cwd=root,
        text=True,
        encoding="utf-8",
        stderr=subprocess.PIPE,
    )
    allowed = {"app", "scripts", "tests", "alembic", "alembic_test"}
    return sorted(
        name
        for name in output.splitlines()
        if Path(name).suffix == ".py" and Path(name).parts[0] in allowed
    )


# ==============================================
# EXPORT COMPLETE COPYABLE SOURCES
# ==============================================


def export_sources(*, root: Path) -> dict[str, int | str]:
    """Write full source files, copyable Markdown, and content hashes."""
    output = root / "artifacts" / "billing-production-review"
    output.mkdir(parents=True, exist_ok=True)
    files = reviewed_files(root=root)
    removed = removed_files(root=root)
    markdown = [
        "# MoulAI™ — Complete Python Sources\n\n",
        "Each block contains the complete current file. Deployment and migration remain governed by the production runbook.\n\n",
    ]
    manifest: dict[str, str] = {}
    archive = output / "moulai-reviewed-python.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        for path in files:
            relative = path.relative_to(root).as_posix()
            content = path.read_bytes()
            source = (
                content.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
            )
            manifest[relative] = hashlib.sha256(content).hexdigest()
            bundle.writestr(relative, content)
            markdown.extend(
                [f"## {relative}\n\n", f"```python\n{source.rstrip()}\n```\n\n"]
            )
        bundle.writestr("source-manifest.json", json.dumps(manifest, indent=2))
        bundle.writestr("removed-python-files.json", json.dumps(removed, indent=2))
    if removed:
        markdown.extend(
            [
                "## Removed Python files\n\n",
                "These paths are removed in the workspace. The archive does not delete existing files when extracted.\n\n",
                "\n".join(f"- {name}" for name in removed) + "\n\n",
            ]
        )
    (output / "complete-python-sources.md").write_text(
        "".join(markdown), encoding="utf-8", newline="\n"
    )
    (output / "source-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8", newline="\n"
    )
    (output / "removed-python-files.json").write_text(
        json.dumps(removed, indent=2), encoding="utf-8", newline="\n"
    )
    return {
        "python_files": len(files),
        "removed_python_files": len(removed),
        "archive": str(archive),
    }


# ==============================================
# SCRIPT ENTRY POINT
# ==============================================


if __name__ == "__main__":
    print(
        json.dumps(export_sources(root=Path(__file__).resolve().parents[1]), indent=2)
    )
