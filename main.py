import asyncio
import aiohttp
import logging
import time
import random
import os
import base64

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# НАСТРОЙКИ — читаем из переменных окружения (Railway/любой хостинг)
# На Railway: Settings → Variables → добавить каждую переменную
# Локально: просто замени os.environ.get("...", "ЗНАЧЕНИЕ_ПО_УМОЛЧАНИЮ")
# ═══════════════════════════════════════════════════════════
BOT_TOKEN             = os.environ.get("BOT_TOKEN", "8442227835:AAEm4UYtkDX8TrTpilX5iDJhxnMegkVdmzM")
ADMIN_ID              = int(os.environ.get("ADMIN_ID", "5479063264"))
API_ID                = int(os.environ.get("API_ID", "37701409"))
API_HASH              = os.environ.get("API_HASH", "5cbdd4ad9f6d19b80e6d53685a914ec7")
PHONE                 = os.environ.get("PHONE", "+380934545223")
SENDER_BOT_USERNAME   = os.environ.get("SENDER_BOT_USERNAME", "balfikovich_gifts")
# FIX #1 #3: сессия хранится в BASE64 в env переменной (для Railway и любого хостинга)
SESSION_BASE64        = os.environ.get("SESSION_BASE64", "U1FMaXRlIGZvcm1hdCAzABAAAQEAQCAgAAAACgAAAAcAAAAAAAAAAAAAAAUAAAAEAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKAC5LkA0NdwAGCwEAD7IOpQ1/DAYNQgsBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAggIGBxclJQGDR3RhYmxldXBkYXRlX3N0YXRldXBkYXRlX3N0YXRlB0NSRUFURSBUQUJMRSB1cGRhdGVfc3RhdGUgKAogICAgICAgICAgICAgICAgICAgIGlkIGludGVnZXIgcHJpbWFyeSBrZXksCiAgICAgICAgICAgICAgICAgICAgcHRzIGludGVnZXIsCiAgICAgICAgICAgICAgICAgICAgcXRzIGludGVnZXIsCiAgICAgICAgICAgICAgICAgICAgZGF0ZSBpbnRlZ2VyLAogICAgICAgICAgICAgICAgICAgIHNlcSBpbnRlZ2VyCiAgICAgICAgICAgICAgICApgjkEBxchIQGEPXRhYmxlc2VudF9maWxlc3NlbnRfZmlsZXMFQ1JFQVRFIFRBQkxFIHNlbnRfZmlsZXMgKAogICAgICAgICAgICAgICAgICAgIG1kNV9kaWdlc3QgYmxvYiwKICAgICAgICAgICAgICAgICAgICBmaWxlX3NpemUgaW50ZWdlciwKICAgICAgICAgICAgICAgICAgICB0eXBlIGludGVnZXIsCiAgICAgICAgICAgICAgICAgICAgaWQgaW50ZWdlciwKICAgICAgICAgICAgICAgICAgICBoYXNoIGludGVnZXIsCiAgICAgICAgICAgICAgICAgICAgcHJpbWFyeSBrZXkobWQ1X2RpZ2VzdCwgZmlsZV9zaXplLCB0eXBlKQogICAgICAgICAgICAgICAgKTMFBhdHIQEAaW5kZXhzcWxpdGVfYXV0b2luZGV4X3NlbnRfZmlsZXNfMXNlbnRfZmlsZXMGAAAACAAAAACCIwMHFx0dAYQZdGFibGVlbnRpdGllc2VudGl0aWVzBENSRUFURSBUQUJMRSBlbnRpdGllcyAoCiAgICAgICAgICAgICAgICAgICAgaWQgaW50ZWdlciBwcmltYXJ5IGtleSwKICAgICAgICAgICAgICAgICAgICBoYXNoIGludGVnZXIgbm90IG51bGwsCiAgICAgICAgICAgICAgICAgICAgdXNlcm5hbWUgdGV4dCwKICAgICAgICAgICAgICAgICAgICBwaG9uZSBpbnRlZ2VyLAogICAgICAgICAgICAgICAgICAgIG5hbWUgdGV4dCwKICAgICAgICAgICAgICAgICAgICBkYXRlIGludGVnZXIKICAgICAgICAgICAgICAgICmCCgIHFx0dAYNndGFibGVzZXNzaW9uc3Nlc3Npb25zA0NSRUFURSBUQUJMRSBzZXNzaW9ucyAoCiAgICAgICAgICAgICAgICAgICAgZGNfaWQgaW50ZWdlciBwcmltYXJ5IGtleSwKICAgICAgICAgICAgICAgICAgICBzZXJ2ZXJfYWRkcmVzcyB0ZXh0LAogICAgICAgICAgICAgICAgICAgIHBvcnQgaW50ZWdlciwKICAgICAgICAgICAgICAgICAgICBhdXRoX2tleSBibG9iLAogICAgICAgICAgICAgICAgICAgIHRha2VvdXRfaWQgaW50ZWdlcgogICAgICAgICAgICAgICAgKUwBBhcbGwFxdGFibGV2ZXJzaW9udmVyc2lvbgJDUkVBVEUgVEFCTEUgdmVyc2lvbiAodmVyc2lvbiBpbnRlZ2VyIHByaW1hcnkga2V5KQ0AAAABD/wAD/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

MIN_DELAY             = 3
MAX_DELAY             = 7
MAX_GIFTS_PER_HOUR    = 10
INVOICE_EXPIRE_SECS   = 100   # 15 минут
PENDING_GIFT_TTL_DAYS = 30     # подарки старше 30 дней удаляются из pending
SESSION_FILE          = "gift_account_session.session"

GIFTS = {
    "gift_1": {"name": "Новогодняя Ёлочка", "emoji": "🎄", "price": 60,
               "gift_id": "5922558454332916696", "description": "Классический новогодний подарок"},
    "gift_2": {"name": "Новогодний Мишка",   "emoji": "🧸", "price": 60,
               "gift_id": "5956217000635139069", "description": "Милый плюшевый друг"},
    "gift_3": {"name": "Февральское Сердце", "emoji": "💝", "price": 60,
               "gift_id": "5801108895304779062", "description": "С любовью и теплом"},
    "gift_4": {"name": "Февральский Мишка",  "emoji": "🧸", "price": 60,
               "gift_id": "5800655655995968830", "description": "Романтичный подарок"},
}


# ═══════════════════════════════════════════════════════════
# ШАБЛОНЫ СООБЩЕНИЙ
# ═══════════════════════════════════════════════════════════

def msg_welcome(gifts: dict, mtproto_ready: bool) -> str:
    status = "🟢 <i>Анонимная отправка доступна</i>" if mtproto_ready else "🔴 <i>Только открытая отправка</i>"
    return (
        "╔══════════════════════╗\n"
        "║   🎁  <b>GIFT SHOP</b>  🎁   ║\n"
        "╚══════════════════════╝\n\n"
        "✨ Добро пожаловать в магазин подарков!\n"
        "Дарите радость близким прямо в Telegram.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🛍 <b>Доступные подарки:</b>\n\n"
        f"  {gifts['gift_1']['emoji']} <b>{gifts['gift_1']['name']}</b> — {gifts['gift_1']['price']}⭐\n"
        f"  {gifts['gift_2']['emoji']} <b>{gifts['gift_2']['name']}</b> — {gifts['gift_2']['price']}⭐\n"
        f"  {gifts['gift_3']['emoji']} <b>{gifts['gift_3']['name']}</b> — {gifts['gift_3']['price']}⭐\n"
        f"  {gifts['gift_4']['emoji']} <b>{gifts['gift_4']['name']}</b> — {gifts['gift_4']['price']}⭐\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{status}\n\n"
        "👇 <b>Выбери подарок ниже:</b>"
    )

def msg_order_header(gift: dict) -> str:
    return (
        f"┌─────────────────────┐\n"
        f"│  {gift['emoji']} <b>{gift['name']}</b>\n"
        f"│  💰 Цена: <b>{gift['price']}⭐</b>\n"
        f"│  📝 {gift['description']}\n"
        f"└─────────────────────┘\n\n"
        f"📋 <b>Детали заказа:</b>\n"
    )

def msg_success_sender(gift: dict, recipient_display: str) -> str:
    # FIX #7: recipient_display уже отформатирован снаружи
    return (
        f"✅ <b>Подарок успешно отправлен!</b>\n\n"
        f"┌─────────────────────┐\n"
        f"│  {gift['emoji']} {gift['name']}\n"
        f"│  👤 Получатель: {recipient_display}\n"
        f"└─────────────────────┘\n\n"
        f"🎉 Получатель уже видит ваш подарок!\n"
        f"💫 Спасибо за покупку!"
    )

def msg_success_recipient(gift: dict, anonymous: bool,
                           sender_name: str, msg_text: str = None) -> str:
    from_line = "🕵️ <i>Отправитель скрыт</i>" if anonymous else f"👤 От: <b>{sender_name}</b>"
    text = (
        f"🎁 <b>Вам пришёл подарок!</b>\n\n"
        f"┌─────────────────────┐\n"
        f"│  {gift['emoji']} <b>{gift['name']}</b>\n"
        f"│  {from_line}\n"
        f"└─────────────────────┘\n"
    )
    if msg_text:
        text += f"\n💌 <i>\"{msg_text}\"</i>\n"
    text += "\n🎊 Наслаждайтесь!"
    return text


# ═══════════════════════════════════════════════════════════
# АНТИБАН
# ═══════════════════════════════════════════════════════════

class AntibanManager:
    def __init__(self):
        self.gift_log: list = []

    async def safe_delay(self, extra: float = 0.0):
        delay = random.uniform(MIN_DELAY, MAX_DELAY) + extra
        logger.info(f"🛡 Антибан пауза: {delay:.1f}с")
        await asyncio.sleep(delay)

    def can_send_gift(self) -> tuple:
        now = time.time()
        self.gift_log = [t for t in list(self.gift_log) if now - t < 3600]
        if len(self.gift_log) >= MAX_GIFTS_PER_HOUR:
            remaining = int(3600 - (now - self.gift_log[0]))
            return False, remaining
        return True, 0

    def log_gift(self):
        self.gift_log.append(time.time())


# ═══════════════════════════════════════════════════════════
# MTPROTO ОТПРАВИТЕЛЬ
# ═══════════════════════════════════════════════════════════

class MTProtoSender:
    def __init__(self, antiban: AntibanManager):
        self.client = None
        self.ready = False
        self.antiban = antiban
        self.known_dialogs: set = set()

    async def start(self):
        """
        FIX #1 #2 #3: Загружает сессию из SESSION_BASE64 env переменной,
        проверяет авторизацию через is_user_authorized(), не зависает.
        """
        try:
            from telethon import TelegramClient

            # FIX #1 #3: восстанавливаем .session файл из base64 env переменной
            if SESSION_BASE64:
                try:
                    session_bytes = base64.b64decode(SESSION_BASE64)
                    with open(SESSION_FILE, "wb") as f:
                        f.write(session_bytes)
                    logger.info("✅ Сессия восстановлена из SESSION_BASE64")
                except Exception as e:
                    logger.error(f"❌ Не удалось декодировать SESSION_BASE64: {e}")
                    self.ready = False
                    return
            elif not os.path.exists(SESSION_FILE):
                logger.error("❌ SESSION_BASE64 не задана и файл сессии не найден")
                logger.error("   Создай сессию локально и добавь SESSION_BASE64 в env переменные")
                self.ready = False
                return

            self.client = TelegramClient(SESSION_FILE.replace(".session", ""), API_ID, API_HASH)
            await self.client.connect()

            # FIX #2: проверяем авторизацию без ожидания ввода кода
            if not await self.client.is_user_authorized():
                logger.error("❌ MTProto: сессия не авторизована (истекла или неверная)")
                logger.error("   Пересоздай сессию локально и обнови SESSION_BASE64")
                await self.client.disconnect()
                self.ready = False
                return

            me = await self.client.get_me()
            logger.info(f"✅ MTProto: @{me.username} (ID: {me.id})")
            self.ready = True
            await self.load_dialogs()

        except Exception as e:
            logger.error(f"❌ MTProto запуск: {e}")
            self.ready = False

    async def load_dialogs(self):
        """Загружает диалоги MTProto аккаунта (НЕ бота — разные аккаунты!)"""
        if not self.client:
            return
        try:
            dialogs = await self.client.get_dialogs(limit=500)
            new_dialogs: set = set()
            for dialog in dialogs:
                try:
                    if dialog.entity and hasattr(dialog.entity, "id"):
                        new_dialogs.add(dialog.entity.id)
                except Exception:
                    continue
            self.known_dialogs = new_dialogs
            logger.info(f"📋 MTProto диалогов: {len(self.known_dialogs)}")
        except Exception as e:
            logger.error(f"load_dialogs: {e}")

    async def has_dialog_with_user(self, user_id: int) -> bool:
        if user_id in self.known_dialogs:
            return True
        await self.load_dialogs()
        return user_id in self.known_dialogs

    async def send_gift_anonymous(self, recipient_id: int, gift_id: str,
                                   message_text: str = None) -> tuple:
        if not self.ready:
            return False, "mtproto_not_ready"

        can_send, wait_seconds = self.antiban.can_send_gift()
        if not can_send:
            return False, f"rate_limit:{wait_seconds}"

        has_dialog = await self.has_dialog_with_user(recipient_id)
        if not has_dialog:
            return False, "no_dialog"

        try:
            await self.antiban.safe_delay()

            # FIX #4 #5 #6: правильный вызов SendStarGiftRequest
            # peer= → user_id=, message= просто строка (не объект),
            # gift= должен быть InputGift объект
            from telethon.tl.functions.payments import SendStarGiftRequest
            from telethon.tl.types import InputUser

            recipient_entity = await self.client.get_entity(recipient_id)

            # Собираем kwargs
            kwargs = {
                "user_id": recipient_entity,
                "gift_id": int(gift_id),
                "hide_my_name": True,
            }
            if message_text:
                kwargs["message"] = message_text

            await self.client(SendStarGiftRequest(**kwargs))
            self.antiban.log_gift()
            logger.info(f"✅ Анонимный подарок → {recipient_id}")
            return True, "ok"

        except Exception as e:
            err = str(e).lower()
            logger.error(f"❌ MTProto отправка: {e}")
            if "privacy" in err or "forbidden" in err:
                return False, "privacy_settings"
            if "flood" in err:
                return False, "flood_wait"
            if "attribute" in err or "import" in err:
                return False, f"telethon_api_error:{e}"
            return False, f"error:{e}"

    async def stop(self):
        try:
            if self.client and self.client.is_connected():
                await self.client.disconnect()
        except Exception as e:
            logger.error(f"MTProto stop: {e}")


# ═══════════════════════════════════════════════════════════
# ОСНОВНОЙ БОТ
# ═══════════════════════════════════════════════════════════

class GiftSender:
    def __init__(self, bot_token: str, gifts: dict, admin_id: int,
                 mtproto: MTProtoSender, antiban: AntibanManager):
        self.bot_token   = bot_token
        self.gifts       = gifts
        self.admin_id    = admin_id
        self.mtproto     = mtproto
        self.antiban     = antiban
        self.base_url    = f"https://api.telegram.org/bot{bot_token}"

        # FIX #9: processed_payments с меткой времени для очистки
        self.processed_payments: dict = {}   # payment_id → timestamp
        self.blocked_users: set       = set()
        # FIX #10: all_users ограничен — храним только последние 10000
        self.all_users: dict          = {}
        # FIX #11: pending_gifts содержит created_at для TTL
        self.pending_gifts: dict      = {}
        self.user_states: dict        = {}
        self.order_messages: dict     = {}
        self.temp_messages: dict      = {}

    # ──────────────────────────────────────────────────────
    # ОБСЛУЖИВАНИЕ (очистка памяти)
    # ──────────────────────────────────────────────────────

    def _cleanup_memory(self):
        """FIX #9 #10 #11: Периодическая очистка утечек памяти"""
        now = time.time()

        # Чистим processed_payments старше 48ч
        self.processed_payments = {
            k: v for k, v in self.processed_payments.items()
            if now - v < 172800
        }

        # Чистим pending_gifts с истёкшим TTL
        ttl = PENDING_GIFT_TTL_DAYS * 86400
        self.pending_gifts = {
            k: v for k, v in self.pending_gifts.items()
            if now - v.get("created_at", now) < ttl
        }

        # all_users — оставляем только 10000 последних активных
        if len(self.all_users) > 10000:
            sorted_ids = sorted(
                self.all_users,
                key=lambda uid: self.all_users[uid].get("last_seen", 0),
                reverse=True
            )
            self.all_users = {uid: self.all_users[uid] for uid in sorted_ids[:10000]}

        logger.info(f"🧹 Очистка памяти: payments={len(self.processed_payments)}, "
                    f"pending={len(self.pending_gifts)}, users={len(self.all_users)}")

    # ──────────────────────────────────────────────────────
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ──────────────────────────────────────────────────────

    def is_blocked(self, username: str) -> bool:
        if not username:
            return False
        return username.lstrip("@").lower() in self.blocked_users

    def register_user(self, user_data: dict):
        user_id    = user_data.get("id")
        username   = user_data.get("username", "")
        first_name = user_data.get("first_name", "Пользователь")
        if user_id:
            self.all_users[user_id] = {
                "username":   username,   # FIX #12: храним чистый username без 'нет username'
                "first_name": first_name,
                "last_seen":  time.time()
            }

    def validate_username(self, username: str) -> tuple:
        username = username.strip().lstrip("@")
        if not username:
            return False, "❌ Username не может быть пустым!"
        if len(username) < 5:
            return False, "❌ Username слишком короткий (мин. 5 символов)"
        if len(username) > 32:
            # FIX #12: Telegram лимит 32 символа
            return False, "❌ Username слишком длинный (макс. 32 символа)"
        cleaned = username.replace("_", "")
        if not cleaned or not cleaned.isalnum():
            return False, "❌ Только буквы, цифры и подчёркивание!"
        return True, username

    def check_username_in_database(self, username: str) -> tuple:
        # FIX #12: теперь сравниваем только реальные username, не 'нет username'
        username_clean = username.lstrip("@").lower()
        if not username_clean:
            return False, None, None
        for user_id, user_data in self.all_users.items():
            stored = user_data.get("username", "").lower()
            if stored and stored == username_clean:
                return True, user_id, user_data.get("first_name", "Пользователь")
        return False, None, None

    def _clear_user_data(self, chat_id: int):
        for storage in [self.user_states, self.order_messages, self.temp_messages]:
            storage.pop(chat_id, None)

    def has_active_invoice(self, chat_id: int) -> bool:
        state = self.user_states.get(chat_id, {})
        if not state.get("invoice_sent_at"):
            return False
        if time.time() - state["invoice_sent_at"] > INVOICE_EXPIRE_SECS:
            logger.info(f"⏰ Инвойс истёк для {chat_id}, очищаем")
            self._clear_user_data(chat_id)
            return False
        return True

    async def _delete_temp_messages(self, chat_id: int):
        """Удаляем старые temp сообщения перед записью новых"""
        for mid in self.temp_messages.pop(chat_id, []):
            await self.delete_message(chat_id, mid)

    # ──────────────────────────────────────────────────────
    # ФОРМИРОВАНИЕ СООБЩЕНИЯ ЗАКАЗА
    # ──────────────────────────────────────────────────────

    def get_order_summary(self, chat_id: int) -> str:
        state = self.user_states.get(chat_id)
        if not state:
            return ""
        gift_key = state.get("gift_key")
        if not gift_key or gift_key not in self.gifts:
            return ""

        gift             = self.gifts[gift_key]
        recipient        = state.get("recipient", "")
        recipient_uname  = state.get("recipient_username", "")
        message_text     = state.get("message", "")
        anonymous        = state.get("anonymous", None)

        text = msg_order_header(gift)

        if recipient == "self":
            text += "  👤 Кому: <b>Себе</b>\n"
        elif recipient == "other":
            if recipient_uname:
                text += f"  👤 Кому: <b>@{recipient_uname}</b>\n"
            else:
                text += "  👤 Кому: <i>ожидается...</i>\n"

        if anonymous is True:
            text += "  🕵️ Отправитель: <b>Анонимно</b>\n"
        elif anonymous is False:
            text += "  👁 Отправитель: <b>Открыто</b>\n"

        if "has_message" in state:
            if state["has_message"] == "with" and message_text:
                text += f"  💌 Подпись: <i>\"{message_text}\"</i>\n"
            elif state["has_message"] == "with":
                text += "  💌 Подпись: <i>ожидается...</i>\n"
            else:
                text += "  💌 Подпись: <b>Без подписи</b>\n"

        return text

    # ──────────────────────────────────────────────────────
    # ОТПРАВКА ПОДАРКОВ
    # ──────────────────────────────────────────────────────

    async def send_gift_bot(self, user_id: int, gift_id: str,
                             text: str = None) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url     = f"{self.base_url}/sendGift"
                payload = {"user_id": user_id, "gift_id": gift_id}
                if text:
                    payload["text"] = text
                async with session.post(url, json=payload) as resp:
                    result = await resp.json()
                    if result.get("ok"):
                        return True
                    logger.error(f"sendGift: {result.get('description')}")
                    return False
        except Exception as e:
            logger.error(f"send_gift_bot: {e}")
            return False

    async def send_gift_smart(self, recipient_id: int, gift_id: str,
                               anonymous: bool, text: str = None) -> tuple:
        if anonymous and self.mtproto.ready:
            return await self.mtproto.send_gift_anonymous(recipient_id, gift_id, text)
        success = await self.send_gift_bot(recipient_id, gift_id, text)
        return (True, "ok") if success else (False, "bot_api_error")

    # ──────────────────────────────────────────────────────
    # ОБНОВЛЕНИЕ СООБЩЕНИЯ ЗАКАЗА
    # ──────────────────────────────────────────────────────

    async def update_order_message(self, chat_id: int, step: str,
                                    _depth: int = 0) -> bool:
        if _depth > 1:
            logger.error(f"update_order_message: рекурсия для {chat_id}")
            return False

        state = self.user_states.get(chat_id)
        if not state:
            return False

        summary = self.get_order_summary(chat_id)
        if not summary:
            return False

        keyboard: dict = {"inline_keyboard": []}
        gift_key = state.get("gift_key", "")

        if step == "recipient":
            summary += "\n\n❓ <b>Для кого подарок?</b>"
            if gift_key:
                keyboard["inline_keyboard"] = [
                    [{"text": "🎁 Для себя",  "callback_data": f"rs_{gift_key}"},
                     {"text": "💝 Для друга", "callback_data": f"ro_{gift_key}"}],
                    [{"text": "❌ Отмена", "callback_data": "cancel_order"}]
                ]
            else:
                keyboard["inline_keyboard"] = [
                    [{"text": "❌ Отмена", "callback_data": "cancel_order"}]
                ]

        elif step == "anonymous_choice":
            summary += "\n\n🔐 <b>Как отправить?</b>"
            keyboard["inline_keyboard"] = [
                [{"text": "🕵️ Анонимно", "callback_data": "anon_yes"},
                 {"text": "👁 Открыто",  "callback_data": "anon_no"}],
                [{"text": "❌ Отмена", "callback_data": "cancel_order"}]
            ]

        elif step == "waiting_username":
            summary += "\n\n⏳ <b>Введи @username получателя:</b>"
            keyboard["inline_keyboard"] = [
                [{"text": "❌ Отмена", "callback_data": "cancel_order"}]
            ]

        elif step == "username_not_found":
            rec_un = state.get("pending_recipient_username", "")
            summary += (
                f"\n\n⚠️ <b>@{rec_un} ещё не писал боту</b>\n\n"
                "Подарок доставится автоматически когда он напишет /start\n\n"
                "👇 <b>Что делаем?</b>"
            )
            keyboard["inline_keyboard"] = [
                [{"text": "✅ Продолжить",      "callback_data": "confirm_unknown"}],
                [{"text": "🔄 Другой username", "callback_data": "reenter_username"}],
                [{"text": "❌ Отмена",           "callback_data": "cancel_order"}]
            ]

        elif step == "check_dialog":
            rec_un = state.get("recipient_username", "")
            summary += (
                f"\n\n⚠️ <b>Нужно одно действие!</b>\n\n"
                f"Попроси <b>@{rec_un}</b> написать любое сообщение аккаунту "
                f"<b>@{SENDER_BOT_USERNAME}</b>\n\n"
                f"<i>После этого нажми кнопку «Проверить»</i>"
            )
            keyboard["inline_keyboard"] = [
                [{"text": "✅ Проверить",        "callback_data": "recheck_dialog"}],
                [{"text": "👁 Отправить открыто", "callback_data": "switch_to_bot"}],
                [{"text": "❌ Отмена",             "callback_data": "cancel_order"}]
            ]

        elif step == "message_choice":
            summary += "\n\n💌 <b>Добавить подпись к подарку?</b>"
            keyboard["inline_keyboard"] = [
                [{"text": "📝 С подписью",  "callback_data": "msg_with"},
                 {"text": "🎁 Без подписи", "callback_data": "msg_without"}],
                [{"text": "❌ Отмена", "callback_data": "cancel_order"}]
            ]

        elif step == "waiting_message":
            summary += "\n\n✏️ <b>Напиши подпись</b> (макс. 200 символов):"
            keyboard["inline_keyboard"] = [
                [{"text": "❌ Отмена", "callback_data": "cancel_order"}]
            ]

        elif step == "ready":
            summary += "\n\n✅ <b>Всё готово!</b>\nПроверь детали и оплати."
            keyboard["inline_keyboard"] = [
                [{"text": "💳 Оплатить", "callback_data": "proceed_payment"}],
                [{"text": "❌ Отмена",   "callback_data": "cancel_order"}]
            ]

        elif step == "payment_sent":
            summary += "\n\n💳 <b>Счёт отправлен!</b>\n⏰ Оплатите в течение 15 минут\n/cancel — отмена"
            keyboard["inline_keyboard"] = []

        try:
            message_id = self.order_messages.get(chat_id)
            timeout    = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                if message_id:
                    url     = f"{self.base_url}/editMessageText"
                    payload = {
                        "chat_id": chat_id, "message_id": message_id,
                        "text": summary, "parse_mode": "HTML",
                        "reply_markup": keyboard
                    }
                    async with s.post(url, json=payload) as resp:
                        result = await resp.json()
                        if not result.get("ok"):
                            logger.warning(f"editMessage fail: {result.get('description')}")
                            self.order_messages.pop(chat_id, None)
                            return await self.update_order_message(chat_id, step, _depth + 1)
                        return True
                else:
                    url     = f"{self.base_url}/sendMessage"
                    payload = {
                        "chat_id": chat_id, "text": summary,
                        "parse_mode": "HTML", "reply_markup": keyboard
                    }
                    async with s.post(url, json=payload) as resp:
                        result = await resp.json()
                        if result.get("ok"):
                            self.order_messages[chat_id] = result["result"]["message_id"]
                            return True
                        return False
        except Exception as e:
            logger.error(f"update_order_message: {e}")
            return False

    # ──────────────────────────────────────────────────────
    # ДЕЙСТВИЯ
    # ──────────────────────────────────────────────────────

    async def cancel_order(self, chat_id: int):
        try:
            msg_id = self.order_messages.get(chat_id)
            self._clear_user_data(chat_id)
            if msg_id:
                await self.delete_message(chat_id, msg_id)
            keyboard = {"inline_keyboard": [
                [{"text": "🏠 В главное меню", "callback_data": "back_to_shop"}]
            ]}
            await self.send_message(
                chat_id,
                "❌ <b>Заказ отменён</b>\n\n<i>Вы можете вернуться и выбрать подарок</i>",
                parse_mode="HTML", reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"cancel_order: {e}")

    async def send_gift_menu(self, chat_id: int):
        try:
            keyboard = {"inline_keyboard": [
                [{"text": f"{self.gifts[k]['emoji']} {self.gifts[k]['name']} — {self.gifts[k]['price']}⭐",
                  "callback_data": k}]
                for k in ["gift_1", "gift_2", "gift_3", "gift_4"]
            ]}
            if chat_id == self.admin_id:
                keyboard["inline_keyboard"].append(
                    [{"text": "⚙️ Панель администратора", "callback_data": "admin_panel"}]
                )
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": msg_welcome(self.gifts, self.mtproto.ready),
                    "parse_mode": "HTML", "reply_markup": keyboard
                }
                async with s.post(url, json=payload) as resp:
                    result = await resp.json()
                    return result.get("ok", False)
        except Exception as e:
            logger.error(f"send_gift_menu: {e}")
            return False

    async def send_invoice(self, chat_id: int) -> bool:
        state = self.user_states.get(chat_id)
        if not state:
            return False
        gift_key = state.get("gift_key")
        if not gift_key or gift_key not in self.gifts:
            logger.error(f"send_invoice: невалидный gift_key={gift_key}")
            return False

        recipient    = state.get("recipient_username", "self")
        gift         = self.gifts[gift_key]
        unique_key   = f"{gift_key}_{chat_id}_{recipient}_{int(time.time()*1000)}"

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                url     = f"{self.base_url}/sendInvoice"
                payload = {
                    "chat_id":     chat_id,
                    "title":       f"{gift['emoji']} {gift['name']}",
                    "description": f"Оплатите {gift['price']}⭐ для отправки подарка. /cancel — отмена",
                    "payload":     unique_key,
                    "currency":    "XTR",
                    "prices":      [{"label": gift["name"], "amount": gift["price"]}]
                }
                async with s.post(url, json=payload) as resp:
                    result = await resp.json()
                    if result.get("ok"):
                        # FIX #15: устанавливаем invoice_sent_at ТОЛЬКО после успешной отправки
                        state["payload"]          = unique_key
                        state["invoice_sent_at"]  = time.time()
                        await self.update_order_message(chat_id, "payment_sent")
                        return True
                    logger.error(f"sendInvoice: {result.get('description')}")
                    return False
        except Exception as e:
            logger.error(f"send_invoice: {e}")
            return False

    async def send_admin_panel(self, chat_id: int):
        now              = time.time()
        gifts_this_hour  = sum(1 for t in list(self.antiban.gift_log) if now - t < 3600)
        can_send, _      = self.antiban.can_send_gift()

        keyboard = {"inline_keyboard": [
            [{"text": "🚫 Заблокировать",   "callback_data": "admin_block"},
             {"text": "✅ Разблокировать",   "callback_data": "admin_unblock"}],
            [{"text": "👥 Пользователи",     "callback_data": "admin_users"}],
            [{"text": "📢 Рассылка",         "callback_data": "admin_broadcast"}],
            [{"text": "🔄 Обновить диалоги", "callback_data": "admin_reload_dialogs"}],
            [{"text": "🔙 В магазин",        "callback_data": "back_to_shop"}]
        ]}

        pending_count = len(self.pending_gifts)
        panel_text = (
            "⚙️ <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Пользователей:  <b>{len(self.all_users)}</b>\n"
            f"🚫 Заблокировано:  <b>{len(self.blocked_users)}</b>\n"
            f"⏳ Ожид. подарков: <b>{pending_count}</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🛡 <b>Антибан статус:</b>\n"
            f"  MTProto:    <b>{'🟢 Готов' if self.mtproto.ready else '🔴 Офлайн'}</b>\n"
            f"  Диалогов:  <b>{len(self.mtproto.known_dialogs)}</b>\n"
            f"  Подарков/ч: <b>{gifts_this_hour}/{MAX_GIFTS_PER_HOUR}</b>\n"
            f"  Лимит:     <b>{'🟢 ОК' if can_send else '🔴 Превышен'}</b>\n\n"
            "👇 Выбери действие:"
        )
        await self.send_message(chat_id, panel_text, parse_mode="HTML", reply_markup=keyboard)

    # ──────────────────────────────────────────────────────
    # ОБРАБОТКА ПЛАТЕЖЕЙ
    # ──────────────────────────────────────────────────────

    async def handle_successful_payment(self, message: dict):
        chat_id    = message["chat"]["id"]
        payment    = message["successful_payment"]
        payment_id = payment.get("telegram_payment_charge_id")

        # FIX #9: используем dict с timestamp вместо set
        if payment_id in self.processed_payments:
            return

        state = self.user_states.get(chat_id)
        if not state:
            logger.warning(f"Оплата {payment_id} без state для {chat_id}")
            return

        gift_key     = state.get("gift_key")
        recipient    = state.get("recipient_username", "self")
        message_text = state.get("message")
        anonymous    = state.get("anonymous", False)

        if not gift_key or gift_key not in self.gifts:
            logger.error(f"handle_payment: невалидный gift_key={gift_key}")
            return

        gift        = self.gifts[gift_key]
        payload_key = state.get("payload")
        if not payload_key:
            payload_key = f"fallback_{chat_id}_{int(time.time())}"
            logger.warning(f"payload отсутствует, fallback: {payload_key}")

        recipient_id = state.get("recipient_user_id")

        # FIX #18: сначала пытаемся отправить подарок, потом помечаем как обработанный
        # --- СЕБЕ ---
        if recipient == "self":
            await self.send_message(chat_id,
                f"⏳ <b>Отправляю {gift['emoji']}...</b>", parse_mode="HTML")
            await asyncio.sleep(1)
            success = await self.send_gift_bot(chat_id, gift["gift_id"], message_text)
            # Помечаем только после попытки
            self.processed_payments[payment_id] = time.time()
            if success:
                await self.send_message(
                    chat_id,
                    f"🎉 <b>Вы получили {gift['emoji']} {gift['name']}!</b>\n\n/start — в магазин",
                    parse_mode="HTML"
                )
            else:
                await self.send_message(chat_id, "❌ Ошибка доставки. Напишите в поддержку.")

        # --- ДРУГОМУ (известный получатель) ---
        elif recipient_id:
            await self.send_message(chat_id,
                "⏳ <b>Отправляю подарок...</b>", parse_mode="HTML")
            success, reason = await self.send_gift_smart(
                recipient_id, gift["gift_id"], anonymous, message_text
            )
            self.processed_payments[payment_id] = time.time()

            if success:
                sender_info  = self.all_users.get(chat_id, {})
                sender_name  = sender_info.get("first_name", "Аноним")
                # FIX #7: правильное отображение получателя
                display      = f"@{recipient}"
                await self.send_message(
                    recipient_id,
                    msg_success_recipient(gift, anonymous, sender_name, message_text),
                    parse_mode="HTML"
                )
                await self.send_message(chat_id,
                    msg_success_sender(gift, display), parse_mode="HTML")

            elif reason == "no_dialog":
                self.pending_gifts[payload_key] = {
                    "gift_key": gift_key, "sender_id": chat_id,
                    "recipient_username": recipient,
                    "recipient_user_id": recipient_id,
                    "message": message_text, "anonymous": anonymous,
                    "created_at": time.time()   # FIX #11: TTL метка
                }
                keyboard = {"inline_keyboard": [[
                    {"text": f"👉 Написать @{SENDER_BOT_USERNAME}",
                     "url": f"https://t.me/{SENDER_BOT_USERNAME}"}
                ]]}
                await self.send_message(
                    chat_id,
                    f"⏳ <b>Оплата принята!</b>\n\n"
                    f"Для анонимной доставки попроси @{recipient} написать:\n"
                    f"➡️ @{SENDER_BOT_USERNAME}\n\n"
                    f"<i>Подарок доставится автоматически!</i>",
                    parse_mode="HTML", reply_markup=keyboard
                )

            elif "rate_limit" in str(reason):
                wait_secs = int(reason.split(":")[1]) if ":" in reason else 3600
                self.pending_gifts[payload_key] = {
                    "gift_key": gift_key, "sender_id": chat_id,
                    "recipient_username": recipient,
                    "recipient_user_id": recipient_id,
                    "message": message_text, "anonymous": anonymous,
                    "created_at": time.time()
                }
                await self.send_message(
                    chat_id,
                    f"⏳ <b>Оплата принята!</b>\n\n"
                    f"🛡 Лимит — доставка через ~{wait_secs // 60} мин.",
                    parse_mode="HTML"
                )

            else:
                await self.send_message(chat_id,
                    "❌ Ошибка доставки. Напишите в поддержку.")

        # --- ДРУГОМУ (получатель ещё не писал боту) ---
        else:
            self.processed_payments[payment_id] = time.time()
            self.pending_gifts[payload_key] = {
                "gift_key": gift_key, "sender_id": chat_id,
                "recipient_username": recipient,
                "recipient_user_id": None,
                "message": message_text, "anonymous": anonymous,
                "created_at": time.time()
            }
            await self.send_message(
                chat_id,
                f"⏳ <b>Оплата принята!</b>\n\n"
                f"Подарок доставится когда @{recipient} напишет /start боту.",
                parse_mode="HTML"
            )

        self._clear_user_data(chat_id)

    # ──────────────────────────────────────────────────────
    # НИЗКОУРОВНЕВЫЕ API
    # ──────────────────────────────────────────────────────

    async def send_message(self, chat_id: int, text: str,
                            parse_mode: str = None,
                            reply_markup: dict = None):
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                url     = f"{self.base_url}/sendMessage"
                payload: dict = {"chat_id": chat_id, "text": text}
                if parse_mode:
                    payload["parse_mode"] = parse_mode
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                async with s.post(url, json=payload) as resp:
                    result = await resp.json()
                    if result.get("ok"):
                        return result["result"]["message_id"]
                    # FIX #8: обработка 403 Forbidden
                    desc = result.get("description", "")
                    if "bot was blocked" in desc or "user is deactivated" in desc:
                        logger.info(f"Юзер {chat_id} заблокировал бота или деактивирован")
                        # Помечаем чтобы не слать снова в broadcast
                        if chat_id in self.all_users:
                            self.all_users[chat_id]["bot_blocked"] = True
                    else:
                        logger.error(f"sendMessage {chat_id}: {desc}")
                    return None
        except Exception as e:
            logger.error(f"send_message: {e}")
            return None

    async def answer_callback_query(self, cq_id: str, text: str = "",
                                     show_alert: bool = False) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                url     = f"{self.base_url}/answerCallbackQuery"
                payload = {"callback_query_id": cq_id,
                           "text": text, "show_alert": show_alert}
                async with s.post(url, json=payload) as resp:
                    result = await resp.json()
                    return result.get("ok", False)
        except Exception as e:
            logger.error(f"answerCallbackQuery: {e}")
            return False

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                url     = f"{self.base_url}/deleteMessage"
                payload = {"chat_id": chat_id, "message_id": message_id}
                async with s.post(url, json=payload) as resp:
                    result = await resp.json()
                    return result.get("ok", False)
        except Exception as e:
            logger.error(f"delete_message: {e}")
            return False

    async def get_updates(self, offset: int = 0) -> list:
        try:
            timeout = aiohttp.ClientTimeout(total=35)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                url    = f"{self.base_url}/getUpdates"
                params: dict = {
                    "timeout": 30,
                    "allowed_updates": [
                        "message", "callback_query", "pre_checkout_query"
                    ]
                }
                if offset > 0:
                    params["offset"] = offset
                async with s.get(url, params=params) as resp:
                    result = await resp.json()
                    return result.get("result", []) if result.get("ok") else []
        except Exception as e:
            logger.error(f"getUpdates: {e}")
            return []

    # ──────────────────────────────────────────────────────
    # ГЛАВНЫЙ ОБРАБОТЧИК
    # ──────────────────────────────────────────────────────

    async def process_update(self, update: dict):
        try:
            # ═══ СООБЩЕНИЯ ═══
            if "message" in update:
                message = update["message"]

                if "successful_payment" in message:
                    await self.handle_successful_payment(message)
                    return

                chat_id    = message["chat"]["id"]
                text       = message.get("text", "")
                message_id = message.get("message_id")
                user       = message.get("from", {})
                username   = user.get("username", "")

                self.register_user(user)

                if self.is_blocked(username):
                    await self.send_message(chat_id, "🚫 Вы заблокированы.")
                    return

                # ─── /start ───
                if text == "/start":
                    # FIX #13: /start полностью сбрасывает состояние (кроме активного инвойса)
                    if self.has_active_invoice(chat_id):
                        await self.send_message(
                            chat_id,
                            "⚠️ <b>Активный заказ!</b>\nОтмени через /cancel",
                            parse_mode="HTML"
                        )
                        return

                    # FIX #13: сбрасываем waiting_for если не инвойс
                    if chat_id in self.user_states:
                        self._clear_user_data(chat_id)

                    # Доставляем ожидающие подарки
                    if username:
                        delivered_keys = []
                        for pk, gd in list(self.pending_gifts.items()):
                            stored = gd.get("recipient_username", "")
                            if not stored or stored.lower() != username.lower():
                                continue
                            gk          = gd["gift_key"]
                            sender_id   = gd["sender_id"]
                            msg_t       = gd.get("message")
                            anon        = gd.get("anonymous", False)
                            rec_id      = gd.get("recipient_user_id")

                            if gk not in self.gifts:
                                delivered_keys.append(pk)
                                continue

                            gift = self.gifts[gk]
                            # Если recipient_user_id неизвестен — используем chat_id
                            target = rec_id if rec_id else chat_id
                            success, _ = await self.send_gift_smart(
                                target, gift["gift_id"], anon, msg_t
                            )
                            if success:
                                s_info  = self.all_users.get(sender_id, {})
                                s_name  = s_info.get("first_name", "Аноним")
                                await self.send_message(
                                    chat_id,
                                    msg_success_recipient(gift, anon, s_name, msg_t),
                                    parse_mode="HTML"
                                )
                                await self.send_message(
                                    sender_id,
                                    msg_success_sender(gift, f"@{username}"),
                                    parse_mode="HTML"
                                )
                                delivered_keys.append(pk)

                        for k in delivered_keys:
                            self.pending_gifts.pop(k, None)

                    await self.send_gift_menu(chat_id)

                # ─── /cancel ───
                elif text == "/cancel":
                    if chat_id in self.user_states:
                        await self.cancel_order(chat_id)
                    else:
                        await self.send_message(chat_id, "ℹ️ Нет активного заказа.")

                # ─── Ввод данных пользователем ───
                elif chat_id in self.user_states:
                    state   = self.user_states[chat_id]
                    waiting = state.get("waiting_for")

                    if waiting == "recipient_username":
                        valid, res = self.validate_username(text)
                        if not valid:
                            err_id = await self.send_message(chat_id, res)
                            await self.delete_message(chat_id, message_id)
                            if err_id:
                                # FIX #20: убираем блокирующий sleep — удаляем через task
                                asyncio.create_task(
                                    self._delayed_delete(chat_id, err_id, 3)
                                )
                            return

                        rec_un = res
                        if rec_un.lower() == username.lower():
                            err_id = await self.send_message(
                                chat_id, "❌ Нельзя отправить самому себе!")
                            await self.delete_message(chat_id, message_id)
                            if err_id:
                                asyncio.create_task(
                                    self._delayed_delete(chat_id, err_id, 3)
                                )
                            return

                        found, found_id, _ = self.check_username_in_database(rec_un)

                        # FIX #19: сначала удаляем старые temp, потом сохраняем новые
                        await self._delete_temp_messages(chat_id)
                        await self.delete_message(chat_id, message_id)

                        if found:
                            state.update({
                                "recipient_username": rec_un,
                                "recipient_user_id":  found_id,
                                "recipient_known":    True,
                                "waiting_for":        None
                            })
                            await self.update_order_message(chat_id, "anonymous_choice")
                        else:
                            state.update({
                                "pending_recipient_username": rec_un,
                                "waiting_for": None
                            })
                            await self.update_order_message(chat_id, "username_not_found")

                    elif waiting == "gift_message":
                        msg_t = text.strip()
                        if len(msg_t) > 200:
                            err_id = await self.send_message(
                                chat_id, "❌ Максимум 200 символов!")
                            await self.delete_message(chat_id, message_id)
                            if err_id:
                                asyncio.create_task(
                                    self._delayed_delete(chat_id, err_id, 3)
                                )
                            return

                        state["message"]     = msg_t
                        state["waiting_for"] = None
                        await self._delete_temp_messages(chat_id)
                        await self.delete_message(chat_id, message_id)
                        await self.update_order_message(chat_id, "ready")

                    elif waiting == "block_username":
                        un = text.strip().lstrip("@").lower()
                        self.blocked_users.add(un)
                        state["waiting_for"] = None
                        await self.send_message(chat_id, f"✅ @{un} заблокирован!")

                    elif waiting == "unblock_username":
                        un = text.strip().lstrip("@").lower()
                        if un in self.blocked_users:
                            self.blocked_users.remove(un)
                            await self.send_message(chat_id, f"✅ @{un} разблокирован!")
                        else:
                            await self.send_message(chat_id,
                                f"⚠️ @{un} не найден в списке заблокированных.")
                        state["waiting_for"] = None

                    elif waiting == "broadcast_text":
                        bcast = text.strip()
                        state.update({"broadcast_text": bcast, "waiting_for": None})
                        kb = {"inline_keyboard": [
                            [{"text": "✅ Отправить", "callback_data": "confirm_broadcast"}],
                            [{"text": "❌ Отмена",    "callback_data": "cancel_broadcast"}]
                        ]}
                        preview = (
                            f"📢 <b>Предпросмотр:</b>\n\n{bcast}\n\n"
                            f"<i>Отправить {len(self.all_users)} пользователям?</i>"
                        )
                        await self.send_message(
                            chat_id, preview, parse_mode="HTML", reply_markup=kb)

            # ═══ CALLBACK QUERY ═══
            if "callback_query" in update:
                cb       = update["callback_query"]
                cq_id    = cb["id"]
                chat_id  = cb["message"]["chat"]["id"]
                data     = cb["data"]
                username = cb.get("from", {}).get("username", "")

                if self.is_blocked(username) and not data.startswith("admin_"):
                    await self.answer_callback_query(
                        cq_id, "🚫 Вы заблокированы!", show_alert=True)
                    return

                # ── Выбор подарка ──
                if data in self.gifts:
                    if self.has_active_invoice(chat_id):
                        await self.answer_callback_query(
                            cq_id, "⚠️ Активный заказ! /cancel", show_alert=True)
                        return
                    self.user_states[chat_id] = {"gift_key": data}
                    await self.answer_callback_query(cq_id)
                    await self.update_order_message(chat_id, "recipient")

                # ── Получатель ──
                elif data.startswith("rs_"):
                    gift_key = data[3:]
                    self.user_states.setdefault(chat_id, {})
                    self.user_states[chat_id].update({
                        "gift_key": gift_key, "recipient": "self",
                        "recipient_username": "self", "anonymous": False
                    })
                    await self.answer_callback_query(cq_id)
                    await self.update_order_message(chat_id, "message_choice")

                elif data.startswith("ro_"):
                    gift_key = data[3:]
                    self.user_states.setdefault(chat_id, {})
                    self.user_states[chat_id].update({
                        "gift_key": gift_key, "recipient": "other",
                        "waiting_for": "recipient_username"
                    })
                    await self.answer_callback_query(cq_id)
                    await self.update_order_message(chat_id, "waiting_username")
                    # FIX #19: сначала удаляем старые temp
                    await self._delete_temp_messages(chat_id)
                    pid = await self.send_message(
                        chat_id, "👤 Введи @username получателя:")
                    if pid:
                        self.temp_messages[chat_id] = [pid]

                # ── Анонимность ──
                elif data == "anon_yes":
                    if chat_id in self.user_states:
                        state       = self.user_states[chat_id]
                        recipient_id = state.get("recipient_user_id")
                        if recipient_id and self.mtproto.ready:
                            has_d = await self.mtproto.has_dialog_with_user(recipient_id)
                            if not has_d:
                                state["anonymous"] = True
                                await self.answer_callback_query(cq_id)
                                await self.update_order_message(chat_id, "check_dialog")
                                return
                        state["anonymous"] = True
                        await self.answer_callback_query(cq_id)
                        await self.update_order_message(chat_id, "message_choice")
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "anon_no":
                    if chat_id in self.user_states:
                        self.user_states[chat_id]["anonymous"] = False
                        await self.answer_callback_query(cq_id)
                        await self.update_order_message(chat_id, "message_choice")
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "switch_to_bot":
                    if chat_id in self.user_states:
                        self.user_states[chat_id]["anonymous"] = False
                        await self.answer_callback_query(
                            cq_id, "👁 Переключено на открытую отправку")
                        await self.update_order_message(chat_id, "message_choice")
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "recheck_dialog":
                    if chat_id in self.user_states:
                        rid = self.user_states[chat_id].get("recipient_user_id")
                        if rid:
                            await self.mtproto.load_dialogs()
                            has_d = await self.mtproto.has_dialog_with_user(rid)
                            if has_d:
                                await self.answer_callback_query(cq_id, "✅ Диалог найден!")
                                await self.update_order_message(chat_id, "message_choice")
                            else:
                                await self.answer_callback_query(
                                    cq_id, "⏳ Ещё не написал...", show_alert=True)
                        else:
                            await self.answer_callback_query(cq_id)
                    else:
                        await self.answer_callback_query(cq_id)

                # ── Неизвестный получатель ──
                elif data == "confirm_unknown":
                    if chat_id in self.user_states:
                        rec_un = self.user_states[chat_id].get(
                            "pending_recipient_username")
                        if rec_un:
                            self.user_states[chat_id].update({
                                "recipient_username": rec_un,
                                "recipient_user_id":  None,
                                "recipient_known":    False
                            })
                            await self.answer_callback_query(cq_id)
                            await self.update_order_message(chat_id, "anonymous_choice")
                        else:
                            await self.answer_callback_query(cq_id)
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "reenter_username":
                    if chat_id in self.user_states:
                        self.user_states[chat_id]["waiting_for"] = "recipient_username"
                        self.user_states[chat_id].pop(
                            "pending_recipient_username", None)
                        await self.answer_callback_query(cq_id)
                        await self.update_order_message(chat_id, "waiting_username")
                        # FIX #19: удаляем старые temp перед записью новых
                        await self._delete_temp_messages(chat_id)
                        pid = await self.send_message(
                            chat_id, "👤 Введи @username получателя:")
                        if pid:
                            self.temp_messages[chat_id] = [pid]
                    else:
                        await self.answer_callback_query(cq_id)

                # ── Подпись ──
                elif data == "msg_with":
                    if chat_id in self.user_states:
                        self.user_states[chat_id].update({
                            "has_message": "with",
                            "waiting_for": "gift_message"
                        })
                        await self.answer_callback_query(cq_id)
                        await self.update_order_message(chat_id, "waiting_message")
                        await self._delete_temp_messages(chat_id)
                        pid = await self.send_message(
                            chat_id, "✏️ Напиши подпись (макс. 200 символов):")
                        if pid:
                            self.temp_messages[chat_id] = [pid]
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "msg_without":
                    if chat_id in self.user_states:
                        self.user_states[chat_id].update({
                            "has_message": "without",
                            "message": None
                        })
                        await self.answer_callback_query(cq_id)
                        await self.update_order_message(chat_id, "ready")
                    else:
                        await self.answer_callback_query(cq_id)

                # ── Оплата ──
                elif data == "proceed_payment":
                    if chat_id in self.user_states:
                        warning = (
                            "⚠️ <b>Перед оплатой проверь:</b>\n\n"
                            "• Правильный ли получатель?\n"
                            "• Подарки нельзя вернуть\n"
                            "• После оплаты отмена невозможна\n\n"
                            "💳 Счёт ниже 👇"
                        )
                        await self.answer_callback_query(cq_id)
                        await self.send_message(chat_id, warning, parse_mode="HTML")
                        await asyncio.sleep(1)
                        await self.send_invoice(chat_id)
                    else:
                        await self.answer_callback_query(cq_id)

                # ── Отмена / Назад ──
                elif data == "cancel_order":
                    await self.answer_callback_query(cq_id)
                    await self.cancel_order(chat_id)

                elif data == "back_to_shop":
                    await self.answer_callback_query(cq_id)
                    await self.send_gift_menu(chat_id)

                # ── АДМИН ──
                elif data == "admin_panel":
                    if chat_id == self.admin_id:
                        await self.answer_callback_query(cq_id)
                        await self.send_admin_panel(chat_id)
                    else:
                        await self.answer_callback_query(
                            cq_id, "⛔️ Нет доступа!", show_alert=True)

                elif data == "admin_reload_dialogs":
                    if chat_id == self.admin_id:
                        await self.mtproto.load_dialogs()
                        await self.answer_callback_query(
                            cq_id,
                            f"✅ Загружено {len(self.mtproto.known_dialogs)} диалогов!",
                            show_alert=True
                        )
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "admin_block":
                    if chat_id == self.admin_id:
                        self.user_states[chat_id] = {"waiting_for": "block_username"}
                        await self.answer_callback_query(cq_id)
                        await self.send_message(chat_id,
                            "🚫 Введи @username для блокировки:")
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "admin_unblock":
                    if chat_id == self.admin_id:
                        self.user_states[chat_id] = {"waiting_for": "unblock_username"}
                        await self.answer_callback_query(cq_id)
                        await self.send_message(chat_id,
                            "✅ Введи @username для разблокировки:")
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "admin_users":
                    if chat_id == self.admin_id:
                        sorted_u = sorted(
                            self.all_users.items(),
                            key=lambda x: x[1].get("last_seen", 0), reverse=True
                        )
                        users_txt = "👥 <b>Последние пользователи:</b>\n\n"
                        for i, (uid, ud) in enumerate(sorted_u[:10], 1):
                            lseen = time.strftime(
                                "%d.%m %H:%M",
                                time.localtime(ud.get("last_seen", 0))
                            )
                            uname = f"@{ud['username']}" if ud.get("username") else "<i>нет username</i>"
                            blocked_mark = " 🚫" if ud.get("bot_blocked") else ""
                            users_txt += (
                                f"{i}. <b>{ud['first_name']}</b> {uname}{blocked_mark}\n"
                                f"   <code>{uid}</code> • {lseen}\n\n"
                            )
                        await self.answer_callback_query(cq_id)
                        await self.send_message(chat_id, users_txt, parse_mode="HTML")
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "admin_broadcast":
                    if chat_id == self.admin_id:
                        self.user_states[chat_id] = {"waiting_for": "broadcast_text"}
                        await self.answer_callback_query(cq_id)
                        await self.send_message(chat_id, "📢 Введи текст рассылки:")
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "confirm_broadcast":
                    if chat_id == self.admin_id and chat_id in self.user_states:
                        bcast = self.user_states[chat_id].get("broadcast_text", "")
                        if bcast:
                            sent = 0
                            # FIX #8: исключаем заблокировавших бота и blocked_users
                            targets = [
                                uid for uid, ud in self.all_users.items()
                                if uid != chat_id
                                and not ud.get("bot_blocked", False)
                                and not self.is_blocked(ud.get("username", ""))
                            ]
                            for uid in targets:
                                mid = await self.send_message(
                                    uid, bcast, parse_mode="HTML")
                                if mid is not None:
                                    sent += 1
                                await asyncio.sleep(0.05)
                            await self.send_message(chat_id, bcast, parse_mode="HTML")
                            await self.send_message(
                                chat_id,
                                f"✅ Рассылка завершена: <b>{sent + 1}</b> сообщений",
                                parse_mode="HTML"
                            )
                        self.user_states.pop(chat_id, None)
                        await self.answer_callback_query(cq_id)
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "cancel_broadcast":
                    self.user_states.pop(chat_id, None)
                    await self.answer_callback_query(cq_id)
                    await self.send_message(chat_id, "❌ Рассылка отменена.")

                else:
                    await self.answer_callback_query(cq_id)

            # ═══ PRE-CHECKOUT ═══
            if "pre_checkout_query" in update:
                pcq = update["pre_checkout_query"]
                # FIX #17: проверяем что payload принадлежит нашему боту
                payload_str = pcq.get("invoice_payload", "")
                is_ours = any(
                    payload_str.startswith(k + "_")
                    for k in self.gifts
                ) or payload_str.startswith("fallback_")

                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as s:
                    url = f"{self.base_url}/answerPreCheckoutQuery"
                    if is_ours:
                        await s.post(url, json={
                            "pre_checkout_query_id": pcq["id"], "ok": True
                        })
                    else:
                        await s.post(url, json={
                            "pre_checkout_query_id": pcq["id"],
                            "ok": False,
                            "error_message": "Неверный платёж"
                        })

        except Exception as e:
            logger.error(f"process_update: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # ──────────────────────────────────────────────────────
    # ВСПОМОГАТЕЛЬНЫЕ ASYNC МЕТОДЫ
    # ──────────────────────────────────────────────────────

    async def _delayed_delete(self, chat_id: int, message_id: int, delay: float):
        """FIX #20: удаление сообщения без блокировки основного цикла"""
        await asyncio.sleep(delay)
        await self.delete_message(chat_id, message_id)

    # ──────────────────────────────────────────────────────
    # ЗАПУСК
    # ──────────────────────────────────────────────────────

    async def get_bot_username(self) -> str:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                url = f"{self.base_url}/getMe"
                async with s.get(url) as resp:
                    result = await resp.json()
                    return (result["result"].get("username", "бот")
                            if result.get("ok") else "бот")
        except Exception as e:
            logger.error(f"get_bot_username: {e}")
            return "бот"

    async def run(self):
        bot_username = await self.get_bot_username()
        print("\n" + "═" * 52)
        print("  🎁  GIFT BOT ЗАПУЩЕН")
        print("═" * 52)
        print(f"  🤖 Бот:       @{bot_username}")
        print(f"  👑 Админ:     {self.admin_id}")
        print(f"  🕵️  MTProto:   {'✅ Подключён' if self.mtproto.ready else '❌ Не подключён'}")
        print(f"  🛡️  Диалогов:  {len(self.mtproto.known_dialogs)}")
        print(f"  ⚡ Лимит:     {MAX_GIFTS_PER_HOUR} подарков/час")
        print(f"  ⏱️  Инвойс:    {INVOICE_EXPIRE_SECS // 60} мин до истечения")
        print("═" * 52 + "\n")

        offset      = 0
        error_count = 0
        last_cleanup = time.time()

        while True:
            try:
                # FIX #9 #10 #11: очистка памяти каждые 6 часов
                if time.time() - last_cleanup > 21600:
                    self._cleanup_memory()
                    last_cleanup = time.time()

                updates = await self.get_updates(offset)
                for upd in updates:
                    offset = upd["update_id"] + 1
                    await self.process_update(upd)
                error_count = 0
                await asyncio.sleep(0.1)

            except Exception as e:
                error_count += 1
                logger.error(f"Ошибка цикла ({error_count}): {e}")
                if error_count > 10:
                    print("\n🔴 Слишком много ошибок подряд! Перезапуск через 60с...")
                    await asyncio.sleep(60)
                    error_count = 0
                else:
                    await asyncio.sleep(min(error_count * 2, 30))


# ═══════════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════════

async def main():
    antiban = AntibanManager()
    mtproto = MTProtoSender(antiban)
    await mtproto.start()

    sender = GiftSender(
        bot_token=BOT_TOKEN, gifts=GIFTS,
        admin_id=ADMIN_ID, mtproto=mtproto, antiban=antiban
    )

    try:
        await sender.run()
    finally:
        await mtproto.stop()
        print("👋 Бот остановлен")


if __name__ == "__main__":
    # FIX #16: KeyboardInterrupt ловится на верхнем уровне, не внутри asyncio loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Пока!")
