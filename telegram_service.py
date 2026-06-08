import os
import logging
from collections import deque
from datetime import datetime
from html import escape
from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from sqlalchemy import func
from dotenv import load_dotenv
from ..config import get_settings
from .telegram_ui_v2 import TelegramUIV2

load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPER_ADMIN_TELEGRAM_IDS = {
    admin_id.strip()
    for admin_id in os.getenv("SUPER_ADMIN_IDS", "").split(",")
    if admin_id.strip()
}
ADMIN_TELEGRAM_IDS = {
    admin_id.strip()
    for admin_id in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",")
    if admin_id.strip()
}

PENDING_USER_COMMANDS = [
    BotCommand("start", "Open telecom access onboarding"),
    BotCommand("register", "Submit telecom access request"),
    BotCommand("status", "Check approval status"),
]

APPROVED_USER_COMMANDS = [
    BotCommand("home", "Open telecom home menu"),
    BotCommand("search", "Search a telecom site"),
    BotCommand("site", "Open telecom site dashboard"),
    BotCommand("dashboard", "Open telecom operations dashboard"),
    BotCommand("profile", "View your telecom profile"),
]

ADMIN_COMMANDS = [
    *APPROVED_USER_COMMANDS,
    BotCommand("pending", "Review pending access requests"),
    BotCommand("approve", "Approve access request by ID"),
    BotCommand("reject", "Reject access request by ID"),
    BotCommand("unapprove", "Move user to pending"),
    BotCommand("unreject", "Move rejected user to pending"),
    BotCommand("block", "Block user by Telegram ID"),
    BotCommand("unblock", "Unblock user by Telegram ID"),
    BotCommand("reapprove", "Reapprove user by Telegram ID"),
    BotCommand("approved", "List active users"),
    BotCommand("blocked", "List blocked users"),
    BotCommand("rejected", "List rejected users"),
    BotCommand("users", "List telecom access users"),
    BotCommand("stats", "View access control metrics"),
]

SUPER_ADMIN_COMMANDS = [
    *ADMIN_COMMANDS,
    BotCommand("make_admin", "Promote user to admin"),
    BotCommand("remove_admin", "Remove admin role"),
    BotCommand("admins", "List admin users"),
    BotCommand("super_admins", "List super admin users"),
]

class TelegramService:
    def __init__(self):
        self.ui = TelegramUIV2()
        self.settings = get_settings()
        self.recent_searches = {}
        self.admin_telegram_ids = ADMIN_TELEGRAM_IDS
        self.super_admin_telegram_ids = SUPER_ADMIN_TELEGRAM_IDS
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_token_here":
            logging.warning("TELEGRAM_BOT_TOKEN is not set correctly in .env file")
            self.application = None
            return
        
        self.application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        self._add_handlers()

    def _add_handlers(self):
        if not self.application:
            return
        # Access and help commands
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("home", self.home_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("register", self.register_command))
        self.application.add_handler(CommandHandler("request_access", self.request_access_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("dashboard", self.dashboard_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("upload", self.upload_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("pending", self.pending_command))
        self.application.add_handler(CommandHandler("approve", self.approve_command))
        self.application.add_handler(CommandHandler("reject", self.reject_command))
        self.application.add_handler(CommandHandler("unapprove", self.unapprove_command))
        self.application.add_handler(CommandHandler("unreject", self.unreject_command))
        self.application.add_handler(CommandHandler("block", self.block_command))
        self.application.add_handler(CommandHandler("unblock", self.unblock_command))
        self.application.add_handler(CommandHandler("reapprove", self.reapprove_command))
        self.application.add_handler(CommandHandler("approved", self.approved_command))
        self.application.add_handler(CommandHandler("blocked", self.blocked_command))
        self.application.add_handler(CommandHandler("rejected", self.rejected_command))
        self.application.add_handler(CommandHandler("admins", self.admins_command))
        self.application.add_handler(CommandHandler("super_admins", self.super_admins_command))
        self.application.add_handler(CommandHandler("make_admin", self.make_admin_command))
        self.application.add_handler(CommandHandler("remove_admin", self.remove_admin_command))
        self.application.add_handler(CommandHandler("users", self.users_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))

        # Existing data commands
        self.application.add_handler(CommandHandler("site", self.site_info))
        self.application.add_handler(CommandHandler("trend", self.trend_info))
        self.application.add_handler(CommandHandler("daywise", self.daywise_info))
        self.application.add_handler(CommandHandler("dgdeployment", self.dgdeployment_info))

        # Keep access decision callbacks separate from site detail callbacks
        self.application.add_handler(CallbackQueryHandler(self.access_request_callback, pattern=r"^access\|"))
        self.application.add_handler(CallbackQueryHandler(self.home_menu_callback, pattern=r"^menu\|"))
        self.application.add_handler(CallbackQueryHandler(self.site_quick_open_callback, pattern=r"^site\|"))
        self.application.add_handler(CallbackQueryHandler(self.location_callback, pattern=r"^location\|"))
        self.application.add_handler(
            CallbackQueryHandler(
                self.site_option_callback,
                pattern=r"^(details|tech|other|hygiene|climate|monthwise|daywise|all|back)\|",
            )
        )

        # Add a message handler for text messages
        self.application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))

    def _build_reply_menu_keyboard(self, is_admin: bool = False):
        return self._build_home_menu_keyboard(is_admin)

    def _default_reply_markup(self, reply_markup=None):
        if reply_markup is False:
            return None
        return reply_markup if reply_markup is not None else self._build_reply_menu_keyboard(False)

    async def _reply_text(self, message, text: str, reply_markup=None):
        await message.reply_text(text, reply_markup=self._default_reply_markup(reply_markup))

    async def _reply_html(self, message, text: str, reply_markup=None):
        await message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=self._default_reply_markup(reply_markup),
        )

    async def _edit_html(self, query, text: str, reply_markup=None):
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        except BadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return
            raise

    async def _answer_callback_query(self, query):
        try:
            await query.answer()
        except BadRequest as exc:
            if "query is too old" in str(exc).lower() or "query id is invalid" in str(exc).lower():
                return
            raise

    async def location_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        try:
            await query.answer("Location not available", show_alert=True)
        except BadRequest:
            return

    def _safe(self, value):
        if value is None or value == "":
            return "N/A"
        return escape(str(value))

    def _is_admin_telegram_id(self, telegram_id: str) -> bool:
        return str(telegram_id) in self.admin_telegram_ids

    def _is_super_admin_telegram_id(self, telegram_id: str) -> bool:
        return str(telegram_id) in self.super_admin_telegram_ids

    def _is_approved_user(self, user) -> bool:
        return user and user.status == "active"

    def _is_admin_user(self, user) -> bool:
        return bool(user and user.status == "active" and user.role in {"admin", "super_admin"})

    def _is_super_admin_user(self, user) -> bool:
        return bool(user and user.status == "active" and user.role == "super_admin")

    def _sync_user_role(self, db_user, telegram_id=None) -> bool:
        effective_telegram_id = telegram_id or getattr(db_user, "telegram_id", None)
        should_be_super_admin = self._is_super_admin_telegram_id(effective_telegram_id)
        should_be_admin = bool(getattr(db_user, "is_admin", False) or self._is_admin_telegram_id(effective_telegram_id))
        expected_role = "super_admin" if should_be_super_admin else "admin" if should_be_admin else "user"
        changed = False

        if getattr(db_user, "is_admin", False) != (should_be_admin or should_be_super_admin):
            db_user.is_admin = should_be_admin or should_be_super_admin
            changed = True

        if getattr(db_user, "role", None) != expected_role:
            db_user.role = expected_role
            changed = True

        if should_be_super_admin and getattr(db_user, "status", None) != "active":
            db_user.status = "active"
            changed = True

        return changed

    def _commands_for_user(self, user):
        if self._is_super_admin_user(user):
            return SUPER_ADMIN_COMMANDS
        if self._is_admin_user(user):
            return ADMIN_COMMANDS
        if self._is_approved_user(user):
            return APPROVED_USER_COMMANDS
        return PENDING_USER_COMMANDS

    async def _set_commands_for_chat(self, chat_id, user):
        if not self.application or not chat_id:
            return
        try:
            await self.application.bot.set_my_commands(
                self._commands_for_user(user),
                scope=BotCommandScopeChat(chat_id=int(chat_id)),
            )
        except Exception as exc:
            logging.warning("Failed to set command menu for chat %s: %s", chat_id, exc)

    async def _register_startup_command_menus(self):
        from ..database import SessionLocal
        from ..models.user import User

        if not self.application:
            return

        await self.application.bot.set_my_commands(PENDING_USER_COMMANDS, scope=BotCommandScopeDefault())

        db = SessionLocal()
        try:
            users = db.query(User).filter(User.telegram_id.isnot(None)).all()
            for db_user in users:
                if self._sync_user_role(db_user):
                    db.commit()
                    db.refresh(db_user)
                await self._set_commands_for_chat(db_user.telegram_id, db_user)
        finally:
            db.close()

    async def _load_user_for_update(self, db, telegram_user):
        from ..models.user import User

        db_user = db.query(User).filter(User.telegram_id == str(telegram_user.id)).first()
        if db_user:
            changed = self._sync_user_role(db_user, telegram_user.id)
            db_user.last_active_at = datetime.utcnow()
            if changed:
                db.commit()
                db.refresh(db_user)
            else:
                db.commit()
        return db_user

    async def _require_admin_message(self, db, message, telegram_user):
        admin_user = await self._load_user_for_update(db, telegram_user)
        if not self._is_admin_user(admin_user):
            await self._reply_html(
                message,
                "<b>🔒 Admin Access Required</b>\nTelecom access management commands are restricted to active administrators.",
                reply_markup=False,
            )
            return None

        await self._set_commands_for_chat(getattr(message.chat, "id", None), admin_user)
        return admin_user

    async def _require_super_admin_message(self, db, message, telegram_user):
        admin_user = await self._load_user_for_update(db, telegram_user)
        if not self._is_super_admin_user(admin_user):
            await self._reply_html(
                message,
                "<b>🔒 Super Admin Access Required</b>\nThis action is restricted to super administrators.",
                reply_markup=False,
            )
            return None

        await self._set_commands_for_chat(getattr(message.chat, "id", None), admin_user)
        return admin_user

    async def _require_admin_query(self, db, query):
        admin_user = await self._load_user_for_update(db, query.from_user)
        if not self._is_admin_user(admin_user):
            await self._edit_html(
                query,
                "<b>🔒 Admin Access Required</b>\nTelecom access management actions are restricted to active administrators.",
            )
            return None

        await self._set_commands_for_chat(query.message.chat.id if query.message else query.from_user.id, admin_user)
        return admin_user

    async def _apply_access_decision(self, db, admin_user, request_id: int, action: str, note: str = None):
        from ..models.access_request import AccessRequest
        from ..models.admin_log import AdminLog
        from ..models.user import User

        access_request = db.query(AccessRequest).filter(AccessRequest.id == int(request_id)).first()
        if not access_request:
            raise ValueError("Access request not found")

        target_user = db.query(User).filter(User.telegram_id == access_request.telegram_id).first()
        if not target_user:
            raise ValueError("Linked user not found")

        status_map = {
            "approve": "active",
            "reject": "rejected",
            "block": "blocked",
            "unblock": "active",
            "reapprove": "active",
        }
        if action not in status_map:
            raise ValueError("Unsupported admin action")

        next_status = status_map[action]
        target_user.status = next_status
        target_user.approved_by = admin_user.id
        target_user.last_action = action
        self._sync_user_role(target_user, target_user.telegram_id)
        access_request.status = next_status
        access_request.review_note = note
        access_request.reviewed_by = admin_user.id
        access_request.reviewed_at = datetime.utcnow()

        db.add(
            AdminLog(
                admin_user_id=admin_user.id,
                action=f"access_{action}",
                target_type="access_request",
                target_id=str(access_request.id),
                details=f"Decision={action}; telegram_id={access_request.telegram_id}; note={note or 'N/A'}",
            )
        )

        db.commit()
        db.refresh(access_request)
        db.refresh(target_user)
        return access_request, target_user, next_status

    def _pending_message(self) -> str:
        return "Your access request is pending admin approval."

    def _denied_message(self) -> str:
        return "❌ Access denied. Contact admin."

    def _ensure_access_request(self, db, db_user, telegram_user):
        from ..models.access_request import AccessRequest

        existing_pending = (
            db.query(AccessRequest)
            .filter(AccessRequest.telegram_id == str(telegram_user.id), AccessRequest.status == "pending")
            .first()
        )
        if existing_pending:
            return existing_pending

        request = AccessRequest(
            user_id=db_user.id,
            telegram_id=str(telegram_user.id),
            username=telegram_user.username,
            full_name=db_user.full_name,
            status="pending",
        )
        db_user.last_action = "requested_access"
        db.add(request)
        db.commit()
        db.refresh(request)
        return request

    def _record_recent_search(self, user_id: str, site_code: str, max_items: int = 6):
        if not user_id or not site_code:
            return
        key = str(user_id)
        history = self.recent_searches.get(key)
        if history is None:
            history = deque(maxlen=max_items)
            self.recent_searches[key] = history

        try:
            history.remove(site_code)
        except ValueError:
            pass

        history.appendleft(site_code)

    def _log_site_search(self, db, db_user, site_code: str):
        from ..models.admin_log import AdminLog

        if not db_user or not site_code:
            return

        db.add(
            AdminLog(
                admin_user_id=db_user.id,
                action="site_search",
                target_type="site",
                target_id=str(site_code),
                details=f"telegram_id={db_user.telegram_id}; username={db_user.username or 'N/A'}",
            )
        )
        db.commit()

    def _initial_role_status(self, telegram_user):
        if self._is_super_admin_telegram_id(telegram_user.id):
            return "super_admin", "active", True
        if self._is_admin_telegram_id(telegram_user.id):
            return "admin", "active", True
        return "user", "pending", False

    def _get_recent_searches(self, user_id: str):
        return list(self.recent_searches.get(str(user_id), []))

    def _build_recent_searches_keyboard(self, site_codes):
        if not site_codes:
            return self._build_home_menu_keyboard(False)

        buttons = []
        row = []
        for index, code in enumerate(site_codes, start=1):
            row.append(InlineKeyboardButton(f"#{index} {code}", callback_data=f"site|{code}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        buttons.append([InlineKeyboardButton("⬅ Back", callback_data="menu|dashboard")])
        return InlineKeyboardMarkup(buttons)

    def _get_site_related_rows(self, db, site_code: str):
        from .infra_hygine_correction_service import InfraHygineCorrectionService
        from .infra_climate_proofing_service import InfraClimateProofingService
        from .nwa_trend_service import NWATrendService

        hygiene_row = InfraHygineCorrectionService.get_record_by_site_id(db, site_code)
        climate_row = InfraClimateProofingService.get_record_by_site_id(db, site_code)
        trend_row = NWATrendService.get_trend_by_site_id(db, site_code)
        return hygiene_row, climate_row, trend_row

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        from ..database import SessionLocal
        from .user_service import UserService
        from ..schemas.user import UserCreate
        
        db = SessionLocal()
        try:
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                role, status, is_admin = self._initial_role_status(user)
                db_user = UserService.create_user(
                    db,
                    UserCreate(
                        telegram_id=str(user.id),
                        username=user.username,
                        full_name=user.first_name,
                        status=status,
                        role=role,
                    ),
                )
                if is_admin:
                    db_user.is_admin = True
                    db.commit()
                    db.refresh(db_user)
                    await self._set_commands_for_chat(update.effective_chat.id, db_user)
                else:
                    logging.info(f"New user registered (PENDING): {user.first_name} (ID: {user.id})")
                    request = self._ensure_access_request(db, db_user, user)
                    await self._notify_admins_for_access_request(db, request)
                    await self._set_commands_for_chat(update.effective_chat.id, db_user)
                    await self._reply_text(update.message, self._pending_message(), reply_markup=False)
                return

            if self._sync_user_role(db_user, user.id):
                db.commit()
                db.refresh(db_user)
            await self._set_commands_for_chat(update.effective_chat.id, db_user)

            if db_user.status == "pending":
                await self._reply_text(update.message, self._pending_message(), reply_markup=False)
            elif db_user.status == "rejected":
                await self._reply_text(update.message, self._denied_message(), reply_markup=False)
            elif db_user.status == "active":
                await self._reply_html(
                    update.message,
                    f"<b>✅ Welcome back {self._safe(user.first_name)}!</b>\n"
                    f"<b>👤 Name:</b> {self._safe(db_user.full_name or user.first_name)}\n"
                    f"<b>🆔 Telegram ID:</b> <code>{self._safe(user.id)}</code>\n"
                    f"<b>Access:</b> Authorized\n"
                    f"<b>Mode:</b> V2 Active\n\n"
                    "<b>Quick Start</b>\n"
                    "• <code>/home</code> Open menu\n"
                    "• <code>/site SITE_ID</code> Open site dashboard\n"
                    "• <code>/help</code> See commands",
                    reply_markup=self._build_home_menu_keyboard(db_user.is_admin),
                )
        finally:
            db.close()

    async def home_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        from ..database import SessionLocal
        from .user_service import UserService
        from ..schemas.user import UserCreate

        db = SessionLocal()
        try:
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                role, status, is_admin = self._initial_role_status(user)
                db_user = UserService.create_user(
                    db,
                    UserCreate(
                        telegram_id=str(user.id),
                        username=user.username,
                        full_name=user.first_name,
                        status=status,
                        role=role,
                    ),
                )
                if is_admin:
                    db_user.is_admin = True
                    db.commit()
                    db.refresh(db_user)
                    await self._set_commands_for_chat(update.effective_chat.id, db_user)
                else:
                    request = self._ensure_access_request(db, db_user, user)
                    await self._notify_admins_for_access_request(db, request)
                    await self._set_commands_for_chat(update.effective_chat.id, db_user)
                    await self._reply_text(update.message, self._pending_message(), reply_markup=False)
                return

            if self._sync_user_role(db_user, user.id):
                db.commit()
                db.refresh(db_user)
            await self._set_commands_for_chat(update.effective_chat.id, db_user)

            if db_user.status == "pending":
                await self._reply_text(update.message, self._pending_message(), reply_markup=False)
                return
            if db_user.status != "active":
                await self._reply_text(update.message, self._denied_message(), reply_markup=False)
                return

            await self._reply_html(
                update.message,
                self._build_home_text(db, db_user),
                reply_markup=self._build_home_menu_keyboard(db_user.is_admin)
            )
        finally:
            db.close()

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._reply_html(
            update.message,
            "<b>📘 Bot Help</b>\n\n"
            "<b>Telecom Access Management</b>\n"
            "<code>/start</code> Initialize your telecom workspace\n"
            "<code>/register</code> Submit or renew access request\n"
            "<code>/status</code> Check approval status\n\n"
            "<b>Active User Operations</b>\n"
            "<code>/search bhpat01</code> Search a site\n"
            "<code>/site bhpat-01</code> Open a site dashboard\n"
            "<i>Also works with BHPAT01, Bhpat01, BHPAT-01, Bhpat-01.</i>\n"
            "<code>/dashboard</code> Open web operations dashboard\n"
            "<code>/profile</code> View your telecom profile\n\n"
            "<b>Admin Access Control</b>\n"
            "<code>/pending</code> Review pending access requests\n"
            "<code>/approve 12</code> Approve request ID 12\n"
            "<code>/reject 12 Invalid data</code> Reject request with note\n"
            "<code>/unapprove 123456789</code> Move user to pending\n"
            "<code>/unreject 123456789</code> Move rejected user to pending\n"
            "<code>/block 123456789</code> Block user by Telegram ID\n"
            "<code>/unblock 123456789</code> Unblock user by Telegram ID\n"
            "<code>/reapprove 123456789</code> Re-approve user by Telegram ID\n"
            "<code>/approved</code> List active users\n"
            "<code>/blocked</code> List blocked users\n"
            "<code>/rejected</code> List rejected users\n"
            "<code>/admins</code> List admin users\n"
            "<code>/super_admins</code> List super admins\n"
            "<code>/make_admin 123456789</code> Promote user to admin\n"
            "<code>/remove_admin 123456789</code> Remove admin role\n"
            "<code>/users</code> Inspect telecom access roster\n"
            "<code>/stats</code> View access control metrics"
        )

    async def register_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.request_access_command(update, context)

    async def request_access_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        from ..database import SessionLocal
        from ..models.access_request import AccessRequest
        from .user_service import UserService
        from ..schemas.user import UserCreate

        db = SessionLocal()
        try:
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                role, status, is_admin = self._initial_role_status(user)
                db_user = UserService.create_user(
                    db,
                    UserCreate(
                        telegram_id=str(user.id),
                        username=user.username,
                        full_name=user.first_name,
                        status=status,
                        role=role,
                    ),
                )
                if is_admin:
                    db_user.is_admin = True
                    db.commit()
                    db.refresh(db_user)
                    await self._set_commands_for_chat(update.effective_chat.id, db_user)
            else:
                if self._sync_user_role(db_user, user.id):
                    db.commit()
                    db.refresh(db_user)
                if db_user.status != "active":
                    db_user.status = "pending"
                    db.commit()
                    db.refresh(db_user)

            await self._set_commands_for_chat(update.effective_chat.id, db_user)

            existing_pending = (
                db.query(AccessRequest)
                .filter(AccessRequest.telegram_id == str(user.id), AccessRequest.status == "pending")
                .first()
            )
            if existing_pending:
                await self._reply_html(update.message, "<b>⏳ Pending Review</b>\nYour access request is already pending admin review.")
                return

            request = AccessRequest(
                user_id=db_user.id,
                telegram_id=str(user.id),
                username=user.username,
                full_name=user.full_name,
                status="pending",
            )
            db.add(request)
            db.commit()
            db.refresh(request)

            await self._notify_admins_for_access_request(db, request)
            await self._reply_text(update.message, self._pending_message(), reply_markup=False)
        finally:
            db.close()

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        from ..database import SessionLocal
        from .user_service import UserService

        db = SessionLocal()
        try:
            db_user = UserService.get_user_by_telegram_id(db, str(user.id))
            if not db_user:
                await self._reply_html(update.message, "<b>ℹ No Account Found</b>\nUse <code>/request_access</code> to register.")
                return
            if self._sync_user_role(db_user, user.id):
                db.commit()
                db.refresh(db_user)
            await self._set_commands_for_chat(update.effective_chat.id, db_user)
            reply_markup = False if db_user.status != "active" else self._build_home_menu_keyboard(db_user.is_admin)
            await self._reply_html(
                update.message,
                "<b>🛡 Telecom Access Status</b>\n"
                f"<b>Status:</b> <code>{self._safe((db_user.status or 'pending').upper())}</code>\n"
                f"<b>Role:</b> <code>{self._safe((db_user.role or 'user').upper())}</code>",
                reply_markup=reply_markup,
            )
        finally:
            db.close()

    async def dashboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        from ..database import SessionLocal

        db = SessionLocal()
        try:
            db_user = await self._load_user_for_update(db, user)
            if not self._is_admin_user(db_user):
                await self._reply_html(update.message, "<b>Access Denied</b>", reply_markup=False)
                return

            v1_url = self.settings.web_dashboard_v1_url
            v2_url = self.settings.web_dashboard_v2_url
            await self._reply_html(
                update.message,
                "<b>📊 Web Dashboards</b>\nSelect a dashboard to open.",
                reply_markup=self.ui.build_dashboard_links_keyboard(v1_url, v2_url),
            )
        finally:
            db.close()

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        from ..database import SessionLocal

        db = SessionLocal()
        try:
            db_user = await self._load_user_for_update(db, user)
            if not db_user:
                await self._reply_html(update.message, "<b>ℹ No Account Found</b>\nUse <code>/start</code> to initialize your telecom access profile.")
                return

            await self._set_commands_for_chat(update.effective_chat.id, db_user)
            if db_user.status == "pending":
                await self._reply_text(update.message, self._pending_message(), reply_markup=False)
                return
            if db_user.status != "active":
                await self._reply_text(update.message, self._denied_message(), reply_markup=False)
                return

            await self._reply_html(
                update.message,
                self._build_profile_text(db_user),
                reply_markup=self._build_home_menu_keyboard(db_user.is_admin),
            )
        finally:
            db.close()

    async def upload_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._reply_html(
            update.message,
            "<b>📤 Upload Guidance</b>\nUse <b>Web Dashboard → Upload Center</b> for secure Excel uploads with preview and validation."
        )

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = " ".join(context.args).strip()
        if not query:
            await self._reply_html(update.message, "<b>Usage</b>\n<code>/search &lt;site_id&gt;</code>\nSupports partial IDs, mixed case, spaces, and hyphens.")
            return
        context.args = [query]
        await self.site_info(update, context)

    async def pending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from ..database import SessionLocal
        from ..models.access_request import AccessRequest

        db = SessionLocal()
        try:
            admin_user = await self._require_admin_message(db, update.message, update.effective_user)
            if not admin_user:
                return

            rows = (
                db.query(AccessRequest)
                .filter(AccessRequest.status == "pending")
                .order_by(AccessRequest.requested_at.desc())
                .limit(10)
                .all()
            )
            if not rows:
                await self._reply_html(update.message, "<b>🛡 Pending Access Queue</b>\nNo pending telecom access requests.")
                return

            lines = ["<b>🛡 Pending Access Queue</b>", "<i>Use /approve &lt;request_id&gt; or /reject &lt;request_id&gt;</i>", ""]
            for row in rows:
                lines.append(
                    f"<b>#{row.id}</b> | <code>{self._safe(row.telegram_id)}</code> | {self._safe(row.full_name or row.username or 'Unknown')}"
                )
            await self._reply_html(update.message, "\n".join(lines))
        finally:
            db.close()

    async def approve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_access_command(update, context, "approve")

    async def reject_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_access_command(update, context, "reject")

    async def unapprove_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_user_status_command(update, context, "pending", action_label="unapproved")

    async def unreject_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_user_status_command(update, context, "pending", action_label="unrejected")

    async def block_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_user_status_command(update, context, "blocked")

    async def unblock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_user_status_command(update, context, "active", action_label="unblocked")

    async def reapprove_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_user_status_command(update, context, "active", action_label="reapproved")

    async def approved_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_list_command(update, "active", "👥 Active Users")

    async def blocked_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_list_command(update, "blocked", "🚫 Blocked Users")

    async def rejected_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_list_command(update, "rejected", "❌ Rejected Users")

    async def admins_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_role_list_command(update, "admin", "🛡 Admin Users")

    async def super_admins_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_role_list_command(update, "super_admin", "🛡 Super Admin Users")

    async def make_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_role_change(update, context, "admin")

    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_admin_role_change(update, context, "user")

    async def _handle_admin_list_command(self, update: Update, status: str, title: str):
        from ..database import SessionLocal
        from ..models.user import User

        db = SessionLocal()
        try:
            admin_user = await self._require_admin_message(db, update.message, update.effective_user)
            if not admin_user:
                return

            rows = (
                db.query(User)
                .filter(User.is_admin == False, User.status == status)
                .order_by(User.created_at.desc(), User.id.desc())
                .limit(20)
                .all()
            )
            if not rows:
                await self._reply_html(update.message, f"<b>{title}</b>\nNo users found.")
                return

            lines = [f"<b>{title}</b>", ""]
            for row in rows:
                lines.append(
                    f"<code>{self._safe(row.telegram_id or row.id)}</code> | {self._safe(row.full_name or row.username or 'Unknown')}"
                )
            await self._reply_html(update.message, "\n".join(lines))
        finally:
            db.close()

    async def _handle_admin_role_list_command(self, update: Update, role: str, title: str):
        from ..database import SessionLocal
        from ..models.user import User

        db = SessionLocal()
        try:
            admin_user = await self._require_admin_message(db, update.message, update.effective_user)
            if not admin_user:
                return

            rows = (
                db.query(User)
                .filter(User.role == role)
                .order_by(User.created_at.desc(), User.id.desc())
                .limit(20)
                .all()
            )
            if not rows:
                await self._reply_html(update.message, f"<b>{title}</b>\nNo users found.")
                return

            lines = [f"<b>{title}</b>", ""]
            for row in rows:
                lines.append(
                    f"<code>{self._safe(row.telegram_id or row.id)}</code> | {self._safe(row.full_name or row.username or 'Unknown')}")
            await self._reply_html(update.message, "\n".join(lines))
        finally:
            db.close()

    async def _handle_admin_role_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE, role: str):
        from ..database import SessionLocal
        from ..models.user import User
        from ..models.admin_log import AdminLog

        db = SessionLocal()
        try:
            admin_user = await self._require_super_admin_message(db, update.message, update.effective_user)
            if not admin_user:
                return

            if not context.args:
                command = "/make_admin" if role == "admin" else "/remove_admin"
                await self._reply_html(update.message, f"<b>Usage</b>\n<code>{command} &lt;telegram_id&gt;</code>")
                return

            telegram_id = context.args[0].strip()
            target_user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not target_user:
                await self._reply_html(update.message, "<b>User not found.</b>")
                return
            if target_user.role == "super_admin" and role != "super_admin":
                await self._reply_html(update.message, "<b>Cannot modify super admin role.</b>")
                return

            target_user.role = role
            target_user.is_admin = role in {"admin", "super_admin"}
            if role in {"admin", "super_admin"}:
                target_user.status = "active"

            db.add(
                AdminLog(
                    admin_user_id=admin_user.id,
                    action="user_promoted_admin" if role == "admin" else "user_demoted_admin",
                    target_type="user",
                    target_id=str(target_user.id),
                    details=f"telegram_id={target_user.telegram_id}",
                )
            )
            db.commit()
            db.refresh(target_user)

            await self._set_commands_for_chat(target_user.telegram_id, target_user)
            try:
                await self.application.bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=(
                        "<b>🛡 Role Update</b>\n"
                        f"Your telecom role is now <code>{self._safe(role.upper())}</code>."
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception as exc:
                logging.warning("Failed to notify user %s about role change: %s", target_user.telegram_id, exc)
            await self._reply_html(
                update.message,
                "<b>✅ Role Updated</b>\n"
                f"User <code>{self._safe(target_user.telegram_id)}</code> role is now <code>{self._safe(role.upper())}</code>.",
            )
        finally:
            db.close()

    async def _handle_admin_user_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, status: str, action_label: str = None):
        from ..database import SessionLocal
        from ..models.user import User
        from ..models.admin_log import AdminLog

        db = SessionLocal()
        try:
            admin_user = await self._require_admin_message(db, update.message, update.effective_user)
            if not admin_user:
                return

            if not context.args:
                if action_label == "unblocked":
                    command = "/unblock"
                elif action_label == "reapproved":
                    command = "/reapprove"
                elif action_label == "unapproved":
                    command = "/unapprove"
                elif action_label == "unrejected":
                    command = "/unreject"
                else:
                    command = "/block"
                await self._reply_html(update.message, f"<b>Usage</b>\n<code>{command} &lt;telegram_id&gt;</code>")
                return

            telegram_id = context.args[0].strip()
            target_user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not target_user:
                await self._reply_html(update.message, "<b>User not found.</b>")
                return
            if target_user.role in {"admin", "super_admin"} and not self._is_super_admin_user(admin_user):
                await self._reply_html(update.message, "<b>Cannot modify admin users.</b>")
                return

            target_user.status = status
            target_user.approved_by = admin_user.id
            target_user.last_action = action_label or status
            self._sync_user_role(target_user, target_user.telegram_id)
            db.add(
                AdminLog(
                    admin_user_id=admin_user.id,
                    action=f"user_{action_label or status}",
                    target_type="user",
                    target_id=str(target_user.id),
                    details=f"telegram_id={target_user.telegram_id}",
                )
            )
            db.commit()
            db.refresh(target_user)

            await self._set_commands_for_chat(target_user.telegram_id, target_user)
            try:
                await self.application.bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=(
                        "<b>🛡 Access Update</b>\n"
                        f"Your telecom access is now <code>{self._safe(status.upper())}</code>."
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception as exc:
                logging.warning("Failed to notify user %s after admin update: %s", target_user.telegram_id, exc)

            await self._reply_html(
                update.message,
                "<b>✅ Access Updated</b>\n"
                f"User <code>{self._safe(target_user.telegram_id)}</code> is now <code>{self._safe(status.upper())}</code>.",
            )
        finally:
            db.close()

    async def _handle_admin_access_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
        from ..database import SessionLocal

        db = SessionLocal()
        try:
            admin_user = await self._require_admin_message(db, update.message, update.effective_user)
            if not admin_user:
                return

            if not context.args:
                usage = "/approve &lt;request_id&gt;" if action == "approve" else "/reject &lt;request_id&gt; [note]"
                await self._reply_html(update.message, f"<b>Usage</b>\n<code>{usage}</code>")
                return

            try:
                request_id = int(context.args[0])
            except ValueError:
                await self._reply_html(update.message, "<b>Invalid request ID.</b>\nUse the numeric request ID from <code>/pending</code>.")
                return

            note = " ".join(context.args[1:]).strip() or None
            try:
                access_request, target_user, next_status = await self._apply_access_decision(db, admin_user, request_id, action, note)
            except ValueError as exc:
                await self._reply_html(update.message, f"<b>Access Update Failed</b>\n{self._safe(exc)}")
                return

            await self._set_commands_for_chat(target_user.telegram_id, target_user)
            try:
                await self.application.bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=(
                        "<b>🛡 Telecom Access Update</b>\n"
                        f"Your access request <code>#{access_request.id}</code> is now <code>{self._safe(next_status.upper())}</code>."
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception as exc:
                logging.warning("Failed to notify user %s after %s: %s", target_user.telegram_id, action, exc)

            await self._reply_html(
                update.message,
                "<b>✅ Access Request Updated</b>\n"
                f"Request <code>#{access_request.id}</code> is now <code>{self._safe(next_status.upper())}</code>.\n"
                f"<b>User:</b> <code>{self._safe(target_user.telegram_id)}</code>",
            )
        finally:
            db.close()

    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from ..database import SessionLocal
        from ..models.user import User

        db = SessionLocal()
        try:
            admin_user = await self._require_admin_message(db, update.message, update.effective_user)
            if not admin_user:
                return

            users = db.query(User).order_by(User.created_at.desc(), User.id.desc()).limit(12).all()
            lines = ["<b>👥 Telecom Access Roster</b>", "<i>Latest registered users</i>", ""]
            for row in users:
                lines.append(
                    f"<code>{self._safe(row.telegram_id or row.id)}</code> | {self._safe(row.full_name or row.username or 'Unknown')} | {self._safe((row.role or 'user').upper())} | {self._safe((row.status or 'pending').upper())}"
                )
            await self._reply_html(update.message, "\n".join(lines))
        finally:
            db.close()

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from ..database import SessionLocal
        from ..models.access_request import AccessRequest
        from ..models.site_list import SiteList1
        from ..models.user import User

        db = SessionLocal()
        try:
            admin_user = await self._require_admin_message(db, update.message, update.effective_user)
            if not admin_user:
                return

            total_users = db.query(User).count()
            approved_users = db.query(User).filter(User.role == "user", User.status == "active").count()
            pending_users = db.query(User).filter(User.role == "user", User.status == "pending").count()
            rejected_users = db.query(User).filter(User.role == "user", User.status == "rejected").count()
            admin_count = db.query(User).filter(User.role == "admin").count()
            super_admin_count = db.query(User).filter(User.role == "super_admin").count()
            pending_requests = db.query(AccessRequest).filter(AccessRequest.status == "pending").count()
            total_sites = db.query(SiteList1).count()

            await self._reply_html(
                update.message,
                "<b>📡 Telecom Access Control Metrics</b>\n"
                f"<b>Total Sites:</b> <code>{self.ui.format_value(total_sites)}</code>\n"
                f"<b>Total Users:</b> <code>{self.ui.format_value(total_users)}</code>\n"
                f"<b>Active Users:</b> <code>{self.ui.format_value(approved_users)}</code>\n"
                f"<b>Pending Users:</b> <code>{self.ui.format_value(pending_users)}</code>\n"
                f"<b>Rejected Users:</b> <code>{self.ui.format_value(rejected_users)}</code>\n"
                f"<b>Admin Users:</b> <code>{self.ui.format_value(admin_count)}</code>\n"
                f"<b>Super Admin Users:</b> <code>{self.ui.format_value(super_admin_count)}</code>\n"
                f"<b>Pending Requests:</b> <code>{self.ui.format_value(pending_requests)}</code>",
            )
        finally:
            db.close()

    def _build_home_text(self, db, db_user):
        from ..models.site_list import SiteList1
        from ..models.user import User

        display_name = db_user.full_name or db_user.username or "User"
        username = f"@{db_user.username}" if db_user.username else "N/A"
        role_label = "Super Admin" if db_user.role == "super_admin" else "Admin" if db_user.role == "admin" else "User"
        total_sites = db.query(SiteList1).count()
        approved_users = db.query(User).filter(User.role == "user", User.status == "active").count()
        pending_users = db.query(User).filter(User.role == "user", User.status == "pending").count()

        return self.ui.build_home_text(display_name, db_user.telegram_id, username, role_label, db_user.status.upper(), total_sites, approved_users, pending_users)

    def _build_profile_text(self, db_user):
        display_name = db_user.full_name or db_user.username or "User"
        username = f"@{db_user.username}" if db_user.username else "N/A"
        role_label = "Super Admin" if db_user.role == "super_admin" else "Admin" if db_user.role == "admin" else "User"
        last_active = db_user.last_active_at or db_user.updated_at or db_user.created_at
        return self.ui.build_profile_text(
            display_name,
            db_user.telegram_id,
            username,
            role_label,
            db_user.status.upper(),
            db_user.created_at,
            last_active,
        )

    def _build_home_menu_keyboard(self, is_admin: bool):
        return self.ui.build_home_menu_keyboard(is_admin)

    def _build_admin_menu_keyboard(self):
        return self.ui.build_admin_menu_keyboard()

    def _build_admin_user_list_text(self, db, title: str, status: str):
        from ..models.user import User

        rows = (
            db.query(User)
            .filter(User.role == "user", User.status == status)
            .order_by(User.created_at.desc(), User.id.desc())
            .limit(20)
            .all()
        )
        if not rows:
            return f"<b>{title}</b>\nNo users found."

        lines = [f"<b>{title}</b>", ""]
        for row in rows:
            lines.append(
                f"<code>{self._safe(row.telegram_id or row.id)}</code> | {self._safe(row.full_name or row.username or 'Unknown')}"
            )
        return "\n".join(lines)

    async def home_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await self._answer_callback_query(query)

        parts = (query.data or "").split("|", 1)
        if len(parts) != 2:
            await self._edit_html(query, "<b>Invalid menu action.</b>")
            return

        _, action = parts
        from ..database import SessionLocal
        from ..models.user import User

        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == str(query.from_user.id)).first()
            if not db_user:
                await self._edit_html(query, "<b>User profile not found.</b>")
                return

            if self._sync_user_role(db_user, query.from_user.id):
                db.commit()
                db.refresh(db_user)
            await self._set_commands_for_chat(query.message.chat.id if query.message else query.from_user.id, db_user)

            if db_user.status == "pending":
                await self._edit_html(query, f"<b>{self._pending_message()}</b>")
                return
            if db_user.status != "active":
                await self._edit_html(query, f"<b>{self._denied_message()}</b>")
                return

            recent_sites = []

            if action == "search":
                text = (
                    "<b>🔎 Search Site</b>\n"
                    "Type a <b>SITE ID</b> in chat to open the site dashboard.\n"
                    "<b>Examples:</b> <code>bhpat01</code>, <code>BHPAT01</code>, <code>Bhpat01</code>\n"
                    "<code>bhpat-01</code>, <code>BHPAT-01</code>, <code>Bhpat-01</code>\n"
                    "<i>Case and hyphens do not matter.</i>\n\n"
                    "You can also use:\n"
                    "<code>/site bhpat01</code>\n"
                    "<code>/search bhpat-01</code>"
                )
            elif action == "home":
                text = self._build_home_text(db, db_user)
            elif action == "dashboard":
                if not self._is_admin_user(db_user):
                    text = "<b>Access Denied</b>"
                else:
                    v1_url = self.settings.web_dashboard_v1_url
                    v2_url = self.settings.web_dashboard_v2_url
                    text = "<b>📊 Web Dashboards</b>\nSelect a dashboard to open."
            elif action == "profile":
                text = self._build_profile_text(db_user)
            elif action == "howto":
                text = self.ui.build_how_to_use_text()
            elif action == "analytics":
                text = (
                    "<b>📡 Analytics Workspace</b>\n"
                    "Use <code>/site SITE_ID</code> to open the live site dashboard, then open Month Wise and Day Wise trend cards.\n\n"
                    "<b>Available analytics</b>\n"
                    "• NWA Month Wise\n"
                    "• 4G Day Wise\n"
                    "• Climate status\n"
                    "• Hygiene completion"
                )
            elif action == "technology":
                text = "🛰 Use /site <SITE ID> and tap 'Site Technology Specification' for live technology details."
            elif action == "climate":
                text = "🌦 Use /site <SITE ID> and tap 'Climate Proofing' for climate information."
            elif action == "hygiene":
                text = "🧹 Use /site <SITE ID> and tap 'Site Asset / Hygine update' for hygiene details."
            elif action == "reports":
                text = "📈 Use /site <SITE ID> to access NWA Month Wise and 4G Day Wise reports."
            elif action == "favorites":
                text = "⭐ Favorites is reserved for V2 enhancement. For now, use /site <SITE ID> for direct access."
            elif action == "recent":
                recent_sites = self._get_recent_searches(str(query.from_user.id))
                text = self.ui.build_recent_searches_text(recent_sites)
            elif action == "admin":
                if not self._is_admin_user(db_user):
                    text = "<b>Access Denied</b>"
                else:
                    text = (
                        "<b>🛠 Admin Panel</b>\n\n"
                        f"⏳ Pending Requests: {db.query(User).filter(User.role == 'user', User.status == 'pending').count()}\n"
                        f"✅ Active Users: {db.query(User).filter(User.role == 'user', User.status == 'active').count()}\n"
                        f"🚫 Blocked Users: {db.query(User).filter(User.role == 'user', User.status == 'blocked').count()}\n"
                        f"❌ Rejected Users: {db.query(User).filter(User.role == 'user', User.status == 'rejected').count()}"
                    )
            elif action == "approved":
                if not self._is_admin_user(db_user):
                    text = "<b>Access Denied</b>"
                else:
                    text = self._build_admin_user_list_text(db, "👥 Active Users", "active")
            elif action == "pending":
                if not self._is_admin_user(db_user):
                    text = "<b>Access Denied</b>"
                else:
                    text = self._build_admin_user_list_text(db, "⏳ Pending Users", "pending")
            elif action == "blocked":
                if not self._is_admin_user(db_user):
                    text = "<b>Access Denied</b>"
                else:
                    text = self._build_admin_user_list_text(db, "🚫 Blocked Users", "blocked")
            elif action == "rejected":
                if not self._is_admin_user(db_user):
                    text = "<b>Access Denied</b>"
                else:
                    text = self._build_admin_user_list_text(db, "❌ Rejected Users", "rejected")
            elif action == "stats":
                if not self._is_admin_user(db_user):
                    text = "<b>Access Denied</b>"
                else:
                    text = (
                        "<b>📡 Telecom Access Control Metrics</b>\n"
                        f"<b>Total Users:</b> <code>{self.ui.format_value(db.query(User).count())}</code>\n"
                        f"<b>Active Users:</b> <code>{self.ui.format_value(db.query(User).filter(User.status == 'active').count())}</code>\n"
                        f"<b>Pending Users:</b> <code>{self.ui.format_value(db.query(User).filter(User.status == 'pending').count())}</code>\n"
                        f"<b>Blocked Users:</b> <code>{self.ui.format_value(db.query(User).filter(User.status == 'blocked').count())}</code>\n"
                        f"<b>Rejected Users:</b> <code>{self.ui.format_value(db.query(User).filter(User.status == 'rejected').count())}</code>"
                    )
            else:
                text = "Unknown menu action."

            reply_markup = None
            if action == "recent":
                reply_markup = self._build_recent_searches_keyboard(recent_sites)
            elif action == "admin" and self._is_admin_user(db_user):
                reply_markup = self._build_admin_menu_keyboard()
            elif action == "dashboard" and self._is_admin_user(db_user):
                v1_url = self.settings.web_dashboard_v1_url
                v2_url = self.settings.web_dashboard_v2_url
                reply_markup = self.ui.build_dashboard_links_keyboard(v1_url, v2_url)
            else:
                reply_markup = self._build_home_menu_keyboard(db_user.is_admin)

            await self._edit_html(query, text, reply_markup=reply_markup)
        finally:
            db.close()

    async def _notify_admins_for_access_request(self, db, request):
        from ..models.user import User

        if not self.application:
            return

        admin_users = db.query(User).filter(User.is_admin == True).all()
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"access|{request.id}|approve"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"access|{request.id}|reject"),
                ],
                [
                    InlineKeyboardButton("🚫 Block", callback_data=f"access|{request.id}|block"),
                    InlineKeyboardButton("🔓 Unblock", callback_data=f"access|{request.id}|unblock"),
                ]
            ]
        )

        text = (
            "<b>🆕 New Access Request</b>\n"
            f"<b>Request ID:</b> <code>{request.id}</code>\n"
            f"<b>Full Name:</b> {self._safe(request.full_name or 'N/A')}\n"
            f"<b>Username:</b> @{self._safe(request.username or 'N/A')}\n"
            f"<b>Telegram ID:</b> <code>{self._safe(request.telegram_id)}</code>\n"
            f"<b>Request Time:</b> {self._safe(request.requested_at)}"
        )

        admin_targets = {admin.telegram_id for admin in admin_users if admin.telegram_id}
        admin_targets.update(self.admin_telegram_ids)
        admin_targets.update(self.super_admin_telegram_ids)
        for admin_id in admin_targets:
            try:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
            except Exception as exc:
                logging.warning("Failed to notify admin %s: %s", admin_id, exc)

    async def access_request_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await self._answer_callback_query(query)

        parts = (query.data or "").split("|")
        if len(parts) != 3:
            await self._edit_html(query, "<b>Invalid access action.</b>")
            return

        _, request_id, action = parts
        from ..database import SessionLocal

        db = SessionLocal()
        try:
            admin_user = await self._require_admin_query(db, query)
            if not admin_user:
                return

            try:
                access_request, target_user, next_status = await self._apply_access_decision(db, admin_user, int(request_id), action)
            except ValueError as exc:
                await self._edit_html(query, f"<b>Access Update Failed</b>\n{self._safe(exc)}")
                return

            await self._set_commands_for_chat(target_user.telegram_id, target_user)

            try:
                await self.application.bot.send_message(
                    chat_id=access_request.telegram_id,
                    text=f"<b>🛡 Access Update</b>\nYour access request is now: <code>{self._safe(next_status.upper())}</code>.",
                    parse_mode=ParseMode.HTML,
                )
            except Exception as exc:
                logging.warning("Failed to notify user %s: %s", access_request.telegram_id, exc)

            await self._edit_html(
                query,
                f"<b>✅ Request Updated</b>\nRequest <code>#{access_request.id}</code> updated to <code>{self._safe(next_status.upper())}</code> by @{self._safe(admin_user.username or admin_user.id)}."
            )
        finally:
            db.close()

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat = update.effective_chat
        message = update.message
        from ..database import SessionLocal
        from .user_service import UserService
        from ..schemas.user import UserCreate
        
        db = SessionLocal()
        try:
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                # Auto-register as pending
                role, status, is_admin = self._initial_role_status(user)
                db_user = UserService.create_user(
                    db,
                    UserCreate(
                        telegram_id=str(user.id),
                        username=user.username,
                        full_name=user.first_name,
                        status=status,
                        role=role,
                    ),
                )
                if is_admin:
                    db_user.is_admin = True
                    db.commit()
                    db.refresh(db_user)
                    await self._set_commands_for_chat(chat.id, db_user)
                else:
                    request = self._ensure_access_request(db, db_user, user)
                    await self._notify_admins_for_access_request(db, request)
                    await self._set_commands_for_chat(chat.id, db_user)
                    await self._reply_text(update.message, self._pending_message(), reply_markup=False)
                return

            if self._sync_user_role(db_user, user.id):
                db.commit()
                db.refresh(db_user)
            await self._set_commands_for_chat(chat.id, db_user)

            if db_user.status == "pending":
                await self._reply_text(update.message, self._pending_message(), reply_markup=False)
                return
            if db_user.status != "active":
                await self._reply_text(update.message, self._denied_message(), reply_markup=False)
                return
            
            # Detailed logging for approved users
            logging.info(f"--- MESSAGE FROM AUTHORIZED USER ---")
            logging.info(f"User: {user.first_name} (@{user.username}) [ID: {user.id}]")
            logging.info(f"Chat: {chat.id} ({chat.type})")
            logging.info(f"Text: {message.text}")
            logging.info(f"------------------------------------")

            normalized_text = (message.text or "").strip().lower()
            if normalized_text in {"home", "menu", "dashboard"}:
                await self._reply_html(
                    update.message,
                    self._build_home_text(db, db_user),
                    reply_markup=self._build_home_menu_keyboard(db_user.is_admin)
                )
                return

            site = self._find_site(db, message.text)
            if site:
                site_code = site.site_id or site.site_id_2 or str(site.sr_id)
                self._record_recent_search(user.id, site_code)
                self._log_site_search(db, db_user, site_code)
                hygiene_row, climate_row, trend_row = self._get_site_related_rows(db, site_code)
                loading_message = await update.message.reply_text(
                    self.ui.build_site_search_loading(site_code),
                    parse_mode=ParseMode.HTML,
                )
                await loading_message.edit_text(
                    self.ui.build_site_dashboard_text(site, hygiene_row, climate_row, trend_row),
                    parse_mode=ParseMode.HTML,
                    reply_markup=self._build_site_menu_keyboard(site)
                )
                return

            await self._reply_text(
                update.message,
                "No matching site found. Try any part of the site ID with or without hyphens, for example /site bhpat01 or /site bhpat-01."
            )
        finally:
            db.close()

    async def site_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        from ..database import SessionLocal
        from .user_service import UserService
        from ..schemas.user import UserCreate
        from ..models.site_list import SiteList1

        db = SessionLocal()
        try:
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                UserService.create_user(db, UserCreate(
                    telegram_id=str(user.id),
                    username=user.username,
                    full_name=user.first_name,
                    status="pending"
                ))
                await self._reply_text(update.message, "⏳ You are not authorized yet. An access request has been sent to the admin.")
                return

            if db_user.status != "active":
                msg = self._pending_message() if db_user.status == "pending" else self._denied_message()
                await self._reply_text(update.message, msg)
                return

            query = " ".join(context.args).strip()
            if not query:
                await self._reply_text(update.message, "Usage: /site <Sr ID or Site ID>. Partial matches, mixed case, spaces, and hyphens are supported.")
                return

            site = self._find_site(db, query)
            if not site:
                await self._reply_text(update.message, f"No matching site found for: {query}. Try a shorter partial site ID or remove formatting.")
                return

            site_code = site.site_id or site.site_id_2 or str(site.sr_id)
            self._record_recent_search(user.id, site_code)
            self._log_site_search(db, db_user, site_code)
            hygiene_row, climate_row, trend_row = self._get_site_related_rows(db, site_code)
            loading_message = await update.message.reply_text(
                self.ui.build_site_search_loading(site_code),
                parse_mode=ParseMode.HTML,
            )
            await loading_message.edit_text(
                self.ui.build_site_dashboard_text(site, hygiene_row, climate_row, trend_row),
                parse_mode=ParseMode.HTML,
                reply_markup=self._build_site_menu_keyboard(site)
            )
        finally:
            db.close()

    def _build_site_menu_keyboard(self, site):
        site_code = site.site_id or site.site_id_2 or site.sr_id or "N/A"
        latitude = getattr(site, "lat", None)
        longitude = getattr(site, "long", None)
        return self.ui.build_site_menu_keyboard(str(site_code), latitude, longitude)

    def _normalize_site_query(self, query: str) -> str:
        from ..utils.site_search import normalize_site_id

        return normalize_site_id(query) or ""

    def _find_site(self, db, query: str):
        from .site_service import SiteService

        return SiteService.get_site_by_site_id(db, query)

    async def site_option_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await self._answer_callback_query(query)
        data = query.data.split("|", 1)
        if len(data) != 2:
            await self._edit_html(query, "<b>Invalid option selected.</b>")
            return

        category, site_code = data
        from ..database import SessionLocal
        from ..models.user import User

        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == str(query.from_user.id)).first()
            if not db_user:
                await self._edit_html(query, "<b>User profile not found.</b>")
                return
            if db_user.status == "pending":
                await self._edit_html(query, f"<b>{self._pending_message()}</b>")
                return
            if db_user.status != "active":
                await self._edit_html(query, f"<b>{self._denied_message()}</b>")
                return

            if category == "back":
                site = self._find_site(db, site_code)
                if not site:
                    await self._edit_html(query, "<b>No site found for this code.</b>")
                    return
                await self._edit_html(
                    query,
                    "<b>Choose one of the following options:</b>",
                    reply_markup=self._build_site_menu_keyboard(site)
                )
                return

            text = self._get_site_option_text(db, category, site_code)
            await self._edit_html(
                query,
                text,
                reply_markup=self._build_back_button(site_code)
            )
        finally:
            db.close()

    async def site_quick_open_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await self._answer_callback_query(query)

        _, site_code = (query.data or "").split("|", 1)
        from ..database import SessionLocal
        from ..models.user import User

        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == str(query.from_user.id)).first()
            if not db_user:
                await self._edit_html(query, "<b>User profile not found.</b>")
                return
            if db_user.status == "pending":
                await self._edit_html(query, f"<b>{self._pending_message()}</b>")
                return
            if db_user.status != "active":
                await self._edit_html(query, f"<b>{self._denied_message()}</b>")
                return

            site = self._find_site(db, site_code)
            if not site:
                await self._edit_html(query, "<b>No site found for this code.</b>")
                return

            self._record_recent_search(query.from_user.id, site_code)
            self._log_site_search(db, db_user, site_code)
            hygiene_row, climate_row, trend_row = self._get_site_related_rows(db, site_code)
            await self._edit_html(
                query,
                self.ui.build_site_dashboard_text(site, hygiene_row, climate_row, trend_row),
                reply_markup=self._build_site_menu_keyboard(site),
            )
        finally:
            db.close()

    def _build_back_button(self, site_code: str):
        return self.ui.build_back_button(site_code)

    def _get_site_option_text(self, db, category: str, site_code: str):
        from .day_wise_service import DayWiseService

        site = self._find_site(db, site_code)
        if not site:
            return f"No site found with ID: {site_code}"

        hygiene_row, climate_row, trend_row = self._get_site_related_rows(db, site_code)
        daywise_payload = DayWiseService.get_daywise_payload_by_site_id(db, site_code)

        if category == "details":
            return self._build_site_details_text(site)
        if category == "tech":
            return self._build_site_technology_text(site)
        if category == "other":
            return self._build_site_other_text(site)
        if category == "hygiene":
            return self._build_asset_hygiene_text(db, site_code)
        if category == "climate":
            return self.ui.build_climate_proofing_text(climate_row)
        if category == "monthwise":
            return self.ui.build_nwa_month_wise_text(trend_row)
        if category == "daywise":
            return self.ui.build_daywise_trend_text(daywise_payload)
        if category == "all":
            sections = [
                self._build_site_details_text(site),
                self._build_site_technology_text(site),
                self._build_site_other_text(site),
                self._build_asset_hygiene_text(db, site_code),
                self.ui.build_climate_proofing_text(climate_row),
                self.ui.build_nwa_month_wise_text(trend_row),
                self.ui.build_daywise_trend_text(daywise_payload),
            ]
            return "\n\n".join(sections)

        return "Unknown option requested."

    def _build_site_details_text(self, site):
        return self.ui.build_site_details_text(site)

    def _build_site_technology_text(self, site):
        return self.ui.build_site_technology_text(site)

    def _build_site_other_text(self, site):
        return self.ui.build_site_other_text(site)

    def _build_asset_hygiene_text(self, db, site_code: str):
        from types import SimpleNamespace
        from .infra_hygine_correction_service import InfraHygineCorrectionService

        payload = InfraHygineCorrectionService.get_record_payload_by_site_id(db, site_code)
        if not payload:
            return self.ui.build_asset_hygiene_text(None)
        return self.ui.build_asset_hygiene_text(SimpleNamespace(**payload))

    def _build_climate_proofing_text(self, db, site_code: str):
        from .infra_climate_proofing_service import InfraClimateProofingService

        row = InfraClimateProofingService.get_record_by_site_id(db, site_code)
        return self.ui.build_climate_proofing_text(row)

    def _build_nwa_month_wise_text(self, db, site_code: str):
        from .nwa_trend_service import NWATrendService

        trend = NWATrendService.get_trend_by_site_id(db, site_code)
        return self.ui.build_nwa_month_wise_text(trend)

    def _build_nwa_trend_daywise_text(self, db, site_code: str):
        from .nwa_trend_service import NWATrendService

        trend = NWATrendService.get_trend_by_site_id(db, site_code)
        return self.ui.build_nwa_trend_daywise_text(trend)

    async def trend_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        from ..database import SessionLocal
        from .user_service import UserService
        from ..schemas.user import UserCreate
        from ..models.nwa_trend import NWATrend

        db = SessionLocal()
        try:
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                UserService.create_user(db, UserCreate(
                    telegram_id=str(user.id),
                    username=user.username,
                    full_name=user.first_name,
                    status="pending"
                ))
                await self._reply_text(update.message, "⏳ You are not authorized yet. An access request has been sent to the admin.")
                return

            if db_user.status != "active":
                msg = self._pending_message() if db_user.status == "pending" else self._denied_message()
                await self._reply_text(update.message, msg)
                return

            query = " ".join(context.args).strip()
            if not query:
                await self._reply_text(update.message, "Usage: /trend <SITE ID>. Partial matches and mixed formatting are supported.")
                return

            from .nwa_trend_service import NWATrendService

            trend = NWATrendService.get_trend_by_site_id(db, query)
            if not trend:
                await self._reply_text(update.message, f"No trend data found for SITE ID: {query}")
                return

            text = (
                f"SITE ID: {trend.site_id or 'N/A'}\n"
                f"Cluster: {trend.cluster or 'N/A'}\n"
                f"DG/Non-DG: {trend.dg_non_dg or 'N/A'}\n"
                f"Current Status: {trend.current_site_status or 'N/A'}\n"
                f"5th Nov Incidence: {self.ui.format_value(trend.fifth_nov_incidence)}\n"
                f"MTD incidence: {self.ui.format_value(trend.mtd_incidence)}\n"
                f"Jan-26: {self.ui.format_value(trend.jan_26)}\n"
                f"Feb-26: {self.ui.format_value(trend.feb_26)}\n"
                f"Mar-26: {self.ui.format_value(trend.mar_26)}"
            )
            await self._reply_text(update.message, text)
        finally:
            db.close()

    async def daywise_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        from ..database import SessionLocal
        from .user_service import UserService
        from ..schemas.user import UserCreate
        from .day_wise_service import DayWiseService

        db = SessionLocal()
        try:
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                UserService.create_user(db, UserCreate(
                    telegram_id=str(user.id),
                    username=user.username,
                    full_name=user.first_name,
                    status="pending"
                ))
                await self._reply_text(update.message, "⏳ You are not authorized yet. An access request has been sent to the admin.")
                return

            if db_user.status != "active":
                msg = self._pending_message() if db_user.status == "pending" else self._denied_message()
                await self._reply_text(update.message, msg)
                return

            query = " ".join(context.args).strip()
            if not query:
                await self._reply_text(update.message, "Usage: /daywise <SITE ID>")
                return

            payload = DayWiseService.get_daywise_payload_by_site_id(db, query)
            if not payload:
                await self._reply_text(update.message, f"No data found for SITE ID: {query}")
                return

            await self._reply_html(update.message, self.ui.build_daywise_trend_text(payload))
        finally:
            db.close()

    async def dgdeployment_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        from ..database import SessionLocal
        from .user_service import UserService
        from ..schemas.user import UserCreate
        from .dg_deployment_service import DGDeploymentService

        db = SessionLocal()
        try:
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                UserService.create_user(db, UserCreate(
                    telegram_id=str(user.id),
                    username=user.username,
                    full_name=user.first_name,
                    status="pending"
                ))
                await self._reply_text(update.message, "⏳ You are not authorized yet. An access request has been sent to the admin.")
                return

            if db_user.status != "active":
                msg = self._pending_message() if db_user.status == "pending" else self._denied_message()
                await self._reply_text(update.message, msg)
                return

            query = " ".join(context.args).strip()
            if not query:
                await self._reply_text(update.message, "Usage: /dgdeployment <SITE ID>. Partial matches and mixed formatting are supported.")
                return

            deployment = DGDeploymentService.get_deployment_by_site_id(db, query)
            if not deployment:
                await self._reply_text(update.message, f"No DG deployment data found for SITE ID: {query}")
                return

            text = (
                f"Sr ID: {deployment.sr_id or 'N/A'}\n"
                f"Site ID: {deployment.site_id or 'N/A'}\n"
                f"Site ID-A: {deployment.site_id_a or 'N/A'}\n"
                f"Site Type: {deployment.site_type or 'N/A'}\n"
                f"Airtel Site Name: {deployment.airtel_site_name or 'N/A'}\n"
                f"DG/Non DG: {deployment.dg_non_dg or 'N/A'}\n"
                f"RFI Date: {deployment.rfi_date or 'N/A'}\n"
                f"RFI Month: {deployment.rfi_month or 'N/A'}"
            )
            await self._reply_text(update.message, text)
        finally:
            db.close()

    async def bbdeployment_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        from ..database import SessionLocal
        from .user_service import UserService
        from ..schemas.user import UserCreate
        from .bb_deployment_service import BBDeploymentService

        db = SessionLocal()
        try:
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                UserService.create_user(db, UserCreate(
                    telegram_id=str(user.id),
                    username=user.username,
                    full_name=user.first_name,
                    status="pending"
                ))
                await self._reply_text(update.message, "⏳ You are not authorized yet. An access request has been sent to the admin.")
                return

            if db_user.status != "active":
                msg = self._pending_message() if db_user.status == "pending" else self._denied_message()
                await self._reply_text(update.message, msg)
                return

            query = " ".join(context.args).strip()
            if not query:
                await self._reply_text(update.message, "Usage: /bbdeployment <SITE ID>. Partial matches and mixed formatting are supported.")
                return

            deployment = BBDeploymentService.get_deployment_by_site_id(db, query)
            if not deployment:
                await self._reply_text(update.message, f"No BB deployment data found for SITE ID: {query}")
                return

            text = (
                f"SITE ID: {deployment.site_id or deployment.site_id_2 or 'N/A'}\n"
                f"Cluster: {deployment.cluster or 'N/A'}\n"
                f"District: {deployment.district or 'N/A'}\n"
                f"BZ: {deployment.bz or 'N/A'}\n"
                f"BB Status Final: {deployment.bb_status_final or 'N/A'}\n"
                f"RFI Date: {deployment.rfi_date or 'N/A'}\n"
                f"Month: {deployment.month or 'N/A'}"
            )
            await self._reply_text(update.message, text)
        finally:
            db.close()

    async def send_message(self, chat_id: str, text: str):
        if not self.application:
            logging.error("Telegram application not initialized")
            return
        await self.application.bot.send_message(chat_id=chat_id, text=text)

    async def initialize(self):
        if self.application:
            print("NEW VERSION RUNNING")
            await self.application.initialize()
            await self.application.start()
            await self._register_startup_command_menus()
            logging.info("Telegram Bot initialized")
            
            # Start polling if mode is set to polling
            if self.settings.telegram_mode == "polling":
                await self.application.bot.delete_webhook(drop_pending_updates=False)
                logging.info("Starting Telegram Bot in POLLING mode...")
                await self.application.updater.start_polling()
            elif self.settings.webhook_url:
                await self.application.bot.set_webhook(url=self.settings.webhook_url)
                logging.info("Starting Telegram Bot in WEBHOOK mode with %s", self.settings.webhook_url)

    async def shutdown(self):
        if self.application:
            if self.application.updater.running:
                await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logging.info("Telegram Bot stopped and shutdown")

# Create a singleton instance
telegram_service = TelegramService()
