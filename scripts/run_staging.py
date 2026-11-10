# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT STAGING ENTRY POINT
# Install staging-only settings and an outbound allowlist before importing legacy
# components; never start migrations, fixture seeding, notifications or a worker.
# ==============================================

"""Check required configuration by default; --serve is a separate deployment action."""

from __future__ import annotations

# isort: split
# ==============================================
# ENTRY DEPENDENCIES
# No project .env or deployed app.main is imported by this launcher.
# ==============================================

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.staging.config import StagingConfig

# ==============================================
# PROCESS INITIALIZATION
# One worker is mandatory while login attempts and encrypted SQLite sessions are used.
# ==============================================


def main() -> int:
    """Validate explicit staging settings or serve after an external activation decision."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    options = parser.parse_args()
    configuration = StagingConfig.load()
    if not options.serve:
        print(
            json.dumps(
                {
                    "status": "configuration_valid",
                    "environment": "staging",
                    "syntheticOnly": True,
                    "service_started": False,
                }
            )
        )
        return 0
    configuration.process_environment()
    configuration.directory.joinpath("private").mkdir(
        parents=True, exist_ok=True, mode=0o700
    )
    from app.staging.network import StagingNetworkGuard

    port = int(os.environ["PORT"])
    if not 1024 <= port <= 65535:
        raise ValueError("staging_listener_port_invalid")
    sys.addaudithook(StagingNetworkGuard(configuration=configuration, port=port))
    import uvicorn

    from app.staging.web import create_staging_app

    app = create_staging_app(
        configuration=configuration, frontend=ROOT / "frontend/staging-dist"
    )
    # Access logs would include single-use OAuth callback query parameters.
    uvicorn.run(
        app, host="0.0.0.0", port=port, workers=1, proxy_headers=False, access_log=False
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
