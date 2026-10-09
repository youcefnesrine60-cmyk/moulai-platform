# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HELPERS / UI MANAGER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for ui manager.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from collections.abc import Awaitable

from app.core.logger import logger
from app.helpers.state_helper import (
    append_to_state_list,
    get_user_state,
    update_state_field,
)
from app.services.telegram import (
    delete_message,
    edit_message,
    send_message,
)

# ==============================================
# 🏷️ TYPES
# ==============================================

TelegramResponse = dict[str, object] | None
ReplyMarkup = dict[str, object] | None
ReplyMarkupInput = ReplyMarkup | Awaitable[ReplyMarkup]


# ==============================================
# 🎨 UI MANAGER
# ==============================================


class UIManager:

    # ==========================================
    # 📤 SEND NEW MESSAGE
    # ==========================================

    @staticmethod
    async def send_new_message(
        *,
        chat_id: int,
        text: str,
        reply_markup: ReplyMarkupInput = None,
        store_message_id: bool = True,
    ) -> TelegramResponse:
        """
        إرسال رسالة جديدة وحفظ معرفها تلقائياً

        Args:
            chat_id: معرف المستخدم
            text: نص الرسالة
            reply_markup: أزرار تفاعلية (اختياري)
            store_message_id: تخزين message_id في الحالة (افتراضي True)

        Returns:
            TelegramResponse: رد من Telegram
        """
        try:
            # ======================================
            # 🔍 RESOLVE REPLY MARKUP
            # ======================================

            final_reply_markup = await UIManager._resolve_reply_markup(
                chat_id=chat_id,
                reply_markup=reply_markup,
            )

            # ======================================
            # 💬 SEND NEW MESSAGE
            # ======================================

            logger.info(
                "sending_new_message",
                extra={
                    "chat_id": chat_id,
                    "text_length": len(text) if text else 0,
                },
            )

            response = await send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=final_reply_markup,
            )

            # ======================================
            # 💾 STORE MESSAGE ID
            # ======================================

            if store_message_id and response and isinstance(response, dict):
                new_message_id = response.get("result", {}).get("message_id")

                if new_message_id:
                    await append_to_state_list(
                        chat_id=chat_id,
                        list_key="message_ids",
                        value=new_message_id,
                    )

                    logger.debug(
                        "message_id_stored",
                        extra={
                            "chat_id": chat_id,
                            "message_id": new_message_id,
                        },
                    )

            return response

        except Exception as e:
            logger.error(
                "send_new_message_failed",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ EDIT EXISTING MESSAGE
    # ==========================================

    @staticmethod
    async def edit(
        *,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: ReplyMarkupInput = None,
    ) -> TelegramResponse:
        """
        تحديث رسالة موجودة

        Args:
            chat_id: معرف المستخدم
            message_id: معرف الرسالة المراد تعديلها
            text: النص الجديد
            reply_markup: أزرار تفاعلية جديدة (اختياري)

        Returns:
            TelegramResponse: رد من Telegram
        """
        try:
            # ======================================
            # 🔍 RESOLVE REPLY MARKUP
            # ======================================

            final_reply_markup = await UIManager._resolve_reply_markup(
                chat_id=chat_id,
                reply_markup=reply_markup,
            )

            # ======================================
            # ✏️ EDIT MESSAGE
            # ======================================

            logger.info(
                "editing_message",
                extra={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text_length": len(text) if text else 0,
                },
            )

            response = await edit_message(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=final_reply_markup,
            )

            return response

        except Exception as e:
            logger.error(
                "edit_message_failed",
                extra={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # 📤 SEND OR EDIT MESSAGE (Legacy Support)
    # ==========================================

    @staticmethod
    async def update(
        *,
        chat_id: int,
        text: str,
        reply_markup: ReplyMarkupInput = None,
        message_id: int | None = None,
        store_message_id: bool = True,
    ) -> TelegramResponse:
        """
        إرسال أو تحديث رسالة (دالة متوافقة مع الإصدارات السابقة)

        Args:
            chat_id: معرف المستخدم
            text: نص الرسالة
            reply_markup: أزرار تفاعلية (اختياري)
            message_id: معرف الرسالة للتعديل (اختياري)
            store_message_id: تخزين message_id في الحالة (افتراضي True)

        Returns:
            TelegramResponse: رد من Telegram
        """
        try:
            # ======================================
            # ✏️ EDIT EXISTING MESSAGE
            # ======================================

            if message_id is not None:
                return await UIManager.edit(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup,
                )

            # ======================================
            # 💬 SEND NEW MESSAGE
            # ======================================

            return await UIManager.send_new_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                store_message_id=store_message_id,
            )

        except Exception as e:
            logger.error(
                "update_message_failed",
                extra={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # 🗑️ DELETE MESSAGE
    # ==========================================

    @staticmethod
    async def delete(
        *,
        chat_id: int,
        message_id: int,
        remove_from_state: bool = True,
    ) -> bool:
        """
        حذف رسالة وإزالتها من الحالة

        Args:
            chat_id: معرف المستخدم
            message_id: معرف الرسالة المراد حذفها
            remove_from_state: إزالة من قائمة message_ids في الحالة

        Returns:
            bool: True إذا تم الحذف بنجاح
        """
        try:
            # ======================================
            # 🗑️ DELETE MESSAGE
            # ======================================

            await delete_message(
                chat_id=chat_id,
                message_id=message_id,
            )

            logger.info(
                "message_deleted",
                extra={
                    "chat_id": chat_id,
                    "message_id": message_id,
                },
            )

            # ======================================
            # 🔄 REMOVE FROM STATE
            # ======================================

            if remove_from_state:
                state = await get_user_state(chat_id=chat_id)
                if state and "message_ids" in state:
                    message_ids = state.get("message_ids", [])
                    if message_id in message_ids:
                        message_ids.remove(message_id)
                        await update_state_field(
                            chat_id=chat_id,
                            key="message_ids",
                            value=message_ids,
                        )

                        logger.debug(
                            "message_id_removed_from_state",
                            extra={
                                "chat_id": chat_id,
                                "message_id": message_id,
                            },
                        )

            return True

        except Exception as e:
            logger.error(
                "delete_message_failed",
                extra={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "error": str(e),
                },
            )
            return False

    # ==========================================
    # 🧹 CLEANUP ALL MESSAGES
    # ==========================================

    @staticmethod
    async def cleanup_messages(
        *,
        chat_id: int,
        preserve_message_id: int | None = None,
    ) -> bool:
        """
        حذف جميع الرسائل المخزنة للمستخدم مع إمكانية استثناء رسالة معينة

        Args:
            chat_id: معرف المحادثة
            preserve_message_id: معرف الرسالة التي لا تريد حذفها

        Returns:
            bool: True إذا تم الحذف بنجاح
        """
        try:
            state = await get_user_state(chat_id=chat_id)

            if not state:
                return False

            message_ids = state.get("message_ids", [])

            if not isinstance(message_ids, list) or not message_ids:
                return True

            # تصفية الرسائل المراد حذفها
            messages_to_delete = [
                msg_id for msg_id in message_ids if msg_id != preserve_message_id
            ]

            if not messages_to_delete:
                return True

            # حذف الرسائل بشكل متسلسل
            deleted_count = 0
            for msg_id in messages_to_delete:
                try:
                    await delete_message(
                        chat_id=chat_id,
                        message_id=msg_id,
                    )
                    deleted_count += 1
                    logger.debug(
                        "message_deleted_during_cleanup",
                        extra={
                            "chat_id": chat_id,
                            "message_id": msg_id,
                        },
                    )
                except Exception as e:
                    logger.warning(
                        "delete_message_failed_during_cleanup",
                        extra={
                            "chat_id": chat_id,
                            "message_id": msg_id,
                            "error": str(e),
                        },
                    )
                    # نستمر في الحذف حتى لو فشلت رسالة

            # تحديث القائمة في الحالة
            await update_state_field(
                chat_id=chat_id,
                key="message_ids",
                value=[preserve_message_id] if preserve_message_id else [],
            )

            logger.info(
                "messages_cleanup_completed",
                extra={
                    "chat_id": chat_id,
                    "deleted_count": deleted_count,
                    "preserved": preserve_message_id,
                },
            )

            return True

        except Exception as e:
            logger.error(
                "cleanup_messages_failed",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                },
            )
            return False

    # ==========================================
    # 🔧 PRIVATE HELPERS
    # ==========================================

    @staticmethod
    async def _resolve_reply_markup(
        *,
        chat_id: int,
        reply_markup: ReplyMarkupInput = None,
    ) -> ReplyMarkup:
        """
        حل الـ reply_markup إذا كان Awaitable

        Args:
            chat_id: معرف المستخدم
            reply_markup: الـ reply_markup المراد حله

        Returns:
            ReplyMarkup: الـ reply_markup النهائي
        """
        final_reply_markup: ReplyMarkup = None

        if reply_markup is not None:
            if isinstance(reply_markup, Awaitable):
                try:
                    final_reply_markup = await reply_markup
                except Exception as e:
                    logger.error(
                        "reply_markup_await_failed",
                        extra={
                            "chat_id": chat_id,
                            "error": str(e),
                        },
                    )
                    final_reply_markup = None
            else:
                final_reply_markup = reply_markup

            # التحقق من صحة الـ reply_markup
            if final_reply_markup is not None and not isinstance(
                final_reply_markup, dict
            ):
                logger.warning(
                    "invalid_reply_markup_type",
                    extra={
                        "chat_id": chat_id,
                        "reply_markup_type": type(final_reply_markup).__name__,
                    },
                )
                final_reply_markup = None

        return final_reply_markup
