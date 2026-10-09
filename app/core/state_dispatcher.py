# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / STATE DISPATCHER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for state dispatcher.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.handlers.owner_handler import handle_owner_state
from app.handlers.customer_handler import handle_customer_state


class StateDispatcher:

    # ==============================================
    # DISPATCH
    # ==============================================

    @classmethod
    async def dispatch(
        cls,
        *,
        chat_id: int,
        text: str,
        state: dict,
        message_id: int,
    ) -> None:
        """
        توزيع الحالة إلى المعالج المناسب

        Args:
            chat_id: معرف المستخدم
            text: النص المرسل
            state: حالة المستخدم الحالية
            message_id: معرف الرسالة (للتحديث)
        """
        flow = state.get("flow")

        # ==========================================
        # OWNER FLOW
        # ==========================================

        if flow == "owner":
            return await handle_owner_state(
                chat_id=chat_id,
                text=text,
                state=state,
                message_id=message_id,
            )

        # ==========================================
        # CUSTOMER FLOW
        # ==========================================

        elif flow == "customer":
            return await handle_customer_state(
                chat_id=chat_id,
                text=text,
                state=state,
                message_id=message_id,
            )

        # ==========================================
        # UNKNOWN FLOW
        # ==========================================

        logger.warning(
            "unknown_flow_state",
            extra={
                "chat_id": chat_id,
                "flow": flow,
            },
        )

        return None
