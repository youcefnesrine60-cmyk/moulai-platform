# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HELPERS / STATE MACHINE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for state machine.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.states.transitions import ALLOWED_TRANSITIONS

# ==============================================
# ✅ CHECK STATE TRANSITION
# ==============================================


async def can_transition(
    *,
    current_state: str,
    next_state: str,
) -> bool:

    # ==========================================
    # 📚 GET ALLOWED TRANSITIONS
    # ==========================================

    allowed = ALLOWED_TRANSITIONS.get(
        current_state,
        (),
    )

    # ==========================================
    # ✅ CHECK TRANSITION
    # ==========================================

    return next_state in allowed
