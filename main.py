import asyncio
import aiohttp
import logging
import time
import random

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8442227835:AAEm4UYtkDX8TrTpilX5iDJhxnMegkVdmzM"
ADMIN_ID = 5479063264

API_ID = 37701409
API_HASH = "5cbdd4ad9f6d19b80e6d53685a914ec7"
PHONE = "+38093454523"
SENDER_BOT_USERNAME = "balfikovich_gifts"  # username MTProto аккаунта (без @)

MIN_DELAY = 3
MAX_DELAY = 7
MAX_GIFTS_PER_HOUR = 10
INVOICE_EXPIRE_SECONDS = 100  # 15 минут

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
# ==================================


# ═══════════════════════════════════════
# ШАБЛОНЫ СООБЩЕНИЙ
# ═══════════════════════════════════════

def msg_welcome(gifts: dict, mtproto_ready: bool) -> str:
    status = "🟢 <i>Аккаунт подключён</i>" if mtproto_ready else "🔴 <i>Аккаунт офлайн</i>"
    return (
        "╔══════════════════════╗\n"
        "║   🎁  <b>GIFT SHOP</b>  🎁    ║\n"
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

def msg_success_sender(gift: dict, recipient: str) -> str:
    return (
        f"✅ <b>Подарок успешно отправлен!</b>\n\n"
        f"┌─────────────────────┐\n"
        f"│  {gift['emoji']} {gift['name']}\n"
        f"│  👤 Получатель: @{recipient}\n"
        f"└─────────────────────┘\n\n"
        f"🎉 Получатель уже видит ваш подарок!\n"
        f"💫 Спасибо за покупку!"
    )

def msg_success_recipient(gift: dict, anonymous: bool, sender_name: str, msg_text: str = None) -> str:
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


# ═══════════════════════════════════════
# АНТИБАН
# ═══════════════════════════════════════

class AntibanManager:
    def __init__(self):
        self.gift_log: list = []

    async def safe_delay(self, extra: float = 0.0):
        delay = random.uniform(MIN_DELAY, MAX_DELAY) + extra
        logger.info(f"🛡 Антибан пауза: {delay:.1f}с")
        await asyncio.sleep(delay)

    def can_send_gift(self) -> tuple:
        now = time.time()
        # Работаем с копией списка чтобы избежать изменения во время итерации
        self.gift_log = [t for t in list(self.gift_log) if now - t < 3600]
        if len(self.gift_log) >= MAX_GIFTS_PER_HOUR:
            remaining = int(3600 - (now - self.gift_log[0]))
            return False, remaining
        return True, 0

    def log_gift(self):
        self.gift_log.append(time.time())


# ═══════════════════════════════════════
# MTPROTO ОТПРАВИТЕЛЬ
# ═══════════════════════════════════════

class MTProtoSender:
    def __init__(self, antiban: AntibanManager):
        self.client = None
        self.ready = False
        self.antiban = antiban
        # FIX #1: known_dialogs содержит ТОЛЬКО реальные диалоги MTProto аккаунта
        # НЕ добавляем сюда chat_id из бота — это разные аккаунты!
        self.known_dialogs: set = set()

    async def start(self):
        try:
            from telethon import TelegramClient
            self.client = TelegramClient('gift_account_session', API_ID, API_HASH)
            # FIX: таймаут на авторизацию чтобы не зависнуть
            await asyncio.wait_for(self.client.start(phone=PHONE), timeout=120)
            me = await self.client.get_me()
            logger.info(f"✅ MTProto: @{me.username} (ID: {me.id})")
            self.ready = True
            await self.load_dialogs()
        except asyncio.TimeoutError:
            logger.error("❌ MTProto: таймаут авторизации")
            self.ready = False
        except Exception as e:
            logger.error(f"❌ MTProto запуск: {e}")
            self.ready = False

    async def load_dialogs(self):
        """Загружает диалоги MTProto аккаунта (не бота!)"""
        if not self.client:
            return
        try:
            dialogs = await self.client.get_dialogs(limit=500)
            new_dialogs: set = set()
            for dialog in dialogs:
                try:
                    if dialog.entity and hasattr(dialog.entity, 'id'):
                        new_dialogs.add(dialog.entity.id)
                except Exception:
                    continue
            self.known_dialogs = new_dialogs
            logger.info(f"📋 MTProto диалогов: {len(self.known_dialogs)}")
        except Exception as e:
            logger.error(f"load_dialogs: {e}")

    async def has_dialog_with_user(self, user_id: int) -> bool:
        """Проверяет что пользователь писал именно MTProto аккаунту"""
        if user_id in self.known_dialogs:
            return True
        # Обновляем и проверяем снова
        await self.load_dialogs()
        return user_id in self.known_dialogs

    async def send_gift_anonymous(self, recipient_id: int, gift_id: str,
                                   message_text: str = None) -> tuple:
        if not self.ready:
            return False, "mtproto_not_ready"

        can_send, wait_seconds = self.antiban.can_send_gift()
        if not can_send:
            return False, f"rate_limit:{wait_seconds}"

        # ГЛАВНАЯ ЗАЩИТА: диалог должен существовать именно с MTProto аккаунтом
        has_dialog = await self.has_dialog_with_user(recipient_id)
        if not has_dialog:
            return False, "no_dialog"

        try:
            await self.antiban.safe_delay()

            from telethon.tl.functions.payments import SendStarGiftRequest
            from telethon.tl.types import TextWithEntities

            recipient_entity = await self.client.get_entity(recipient_id)

            request_kwargs = dict(
                peer=recipient_entity,
                gift=int(gift_id),
                hide_my_name=True,
            )
            if message_text:
                request_kwargs["message"] = TextWithEntities(text=message_text, entities=[])

            await self.client(SendStarGiftRequest(**request_kwargs))
            self.antiban.log_gift()
            logger.info(f"✅ Анонимный подарок -> {recipient_id}")
            return True, "ok"

        except Exception as e:
            err = str(e).lower()
            logger.error(f"❌ MTProto отправка: {e}")
            if "privacy" in err or "forbidden" in err:
                return False, "privacy_settings"
            if "flood" in err:
                return False, "flood_wait"
            return False, f"error:{e}"

    async def stop(self):
        try:
            if self.client and self.client.is_connected():
                await self.client.disconnect()
        except Exception as e:
            logger.error(f"MTProto stop: {e}")


# ═══════════════════════════════════════
# ОСНОВНОЙ БОТ
# ═══════════════════════════════════════

class GiftSender:
    def __init__(self, bot_token: str, gifts: dict, admin_id: int,
                 mtproto: MTProtoSender, antiban: AntibanManager):
        self.bot_token = bot_token
        self.gifts = gifts
        self.admin_id = admin_id
        self.mtproto = mtproto
        self.antiban = antiban
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

        self.processed_payments: set = set()
        self.blocked_users: set = set()
        self.all_users: dict = {}
        self.pending_gifts: dict = {}
        self.user_states: dict = {}
        self.order_messages: dict = {}
        self.temp_messages: dict = {}

    # ──────────────────────────────────────
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ──────────────────────────────────────

    def is_blocked(self, username: str) -> bool:
        if not username:
            return False
        return username.lstrip("@").lower() in self.blocked_users

    def register_user(self, user_data: dict):
        user_id = user_data.get("id")
        username = user_data.get("username", "")
        first_name = user_data.get("first_name", "Пользователь")
        if user_id:
            self.all_users[user_id] = {
                "username": f"@{username}" if username else "нет username",
                "first_name": first_name,
                "last_seen": time.time()
            }

    def validate_username(self, username: str) -> tuple:
        username = username.strip().lstrip("@")
        if not username:
            return False, "❌ Username не может быть пустым!"
        if len(username) < 5:
            return False, "❌ Username слишком короткий (мин. 5 символов)"
        cleaned = username.replace("_", "")
        if not cleaned or not cleaned.isalnum():
            return False, "❌ Только буквы, цифры и подчёркивание!"
        return True, username

    def check_username_in_database(self, username: str) -> tuple:
        username_clean = username.lstrip("@").lower()
        for user_id, user_data in self.all_users.items():
            stored = user_data.get("username", "").lstrip("@").lower()
            if stored == username_clean:
                return True, user_id, user_data.get("first_name", "Пользователь")
        return False, None, None

    def _clear_user_data(self, chat_id: int):
        """Очистка всех данных пользователя"""
        for storage in [self.user_states, self.order_messages, self.temp_messages]:
            storage.pop(chat_id, None)

    def is_invoice_expired(self, state: dict) -> bool:
        """FIX #2: Проверка истечения инвойса"""
        sent_at = state.get("invoice_sent_at")
        if not sent_at:
            return False
        return time.time() - sent_at > INVOICE_EXPIRE_SECONDS

    def has_active_invoice(self, chat_id: int) -> bool:
        """FIX #2: Активный НЕ истёкший инвойс"""
        state = self.user_states.get(chat_id, {})
        if not state.get("invoice_sent_at"):
            return False
        if self.is_invoice_expired(state):
            # Инвойс истёк — чистим состояние
            logger.info(f"⏰ Инвойс истёк для {chat_id}, очищаем")
            self._clear_user_data(chat_id)
            return False
        return True

    # ──────────────────────────────────────
    # ФОРМИРОВАНИЕ СООБЩЕНИЯ ЗАКАЗА
    # ──────────────────────────────────────

    def get_order_summary(self, chat_id: int) -> str:
        state = self.user_states.get(chat_id)
        if not state:
            return ""
        gift_key = state.get("gift_key")
        if not gift_key or gift_key not in self.gifts:
            return ""

        gift = self.gifts[gift_key]
        recipient = state.get("recipient", "")
        recipient_username = state.get("recipient_username", "")
        message_text = state.get("message", "")
        anonymous = state.get("anonymous", None)

        text = msg_order_header(gift)

        if recipient == "self":
            text += "  👤 Кому: <b>Себе</b>\n"
        elif recipient == "other":
            if recipient_username:
                text += f"  👤 Кому: <b>@{recipient_username}</b>\n"
            else:
                text += "  👤 Кому: <i>ожидается...</i>\n"

        if anonymous is True:
            text += "  🕵️ Отправитель: <b>Анонимно</b>\n"
        elif anonymous is False:
            text += "  👁 Отправитель: <b>Видно получателю</b>\n"

        if "has_message" in state:
            if state["has_message"] == "with" and message_text:
                text += f"  💌 Подпись: <i>\"{message_text}\"</i>\n"
            elif state["has_message"] == "with":
                text += "  💌 Подпись: <i>ожидается...</i>\n"
            else:
                text += "  💌 Подпись: <b>Без подписи</b>\n"

        return text

    # ──────────────────────────────────────
    # ОТПРАВКА ПОДАРКОВ
    # ──────────────────────────────────────

    async def send_gift_bot(self, user_id: int, gift_id: str, text: str = None) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.base_url}/sendGift"
                payload = {"user_id": user_id, "gift_id": gift_id}
                if text:
                    payload["text"] = text
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    if result.get("ok"):
                        return True
                    logger.error(f"Bot API sendGift: {result.get('description')}")
                    return False
        except Exception as e:
            logger.error(f"Bot API: {e}")
            return False

    async def send_gift_smart(self, recipient_id: int, gift_id: str,
                               anonymous: bool, text: str = None) -> tuple:
        """
        anonymous=True  -> MTProto (отправитель - живой аккаунт, анонимно)
        anonymous=False -> Bot API (отправитель - бот)
        """
        if anonymous and self.mtproto.ready:
            return await self.mtproto.send_gift_anonymous(recipient_id, gift_id, text)
        success = await self.send_gift_bot(recipient_id, gift_id, text)
        return (True, "ok") if success else (False, "bot_api_error")

    # ──────────────────────────────────────
    # ОБНОВЛЕНИЕ СООБЩЕНИЯ ЗАКАЗА
    # ──────────────────────────────────────

    async def update_order_message(self, chat_id: int, step: str, _depth: int = 0) -> bool:
        """FIX #4: Защита от бесконечной рекурсии через _depth"""
        if _depth > 1:
            logger.error(f"update_order_message: превышена глубина рекурсии для {chat_id}")
            return False

        state = self.user_states.get(chat_id)
        if not state:
            return False

        summary = self.get_order_summary(chat_id)
        if not summary:
            return False

        keyboard: dict = {"inline_keyboard": []}

        # FIX #9: безопасное получение gift_key
        gift_key = state.get("gift_key", "")

        if step == "recipient":
            summary += "\n\n❓ <b>Для кого подарок?</b>"
            # FIX #9: проверяем gift_key перед использованием в callback_data
            if gift_key:
                keyboard["inline_keyboard"] = [
                    [{"text": "🎁 Для себя",  "callback_data": f"recipient_self_{gift_key}"},
                     {"text": "💝 Для друга", "callback_data": f"recipient_other_{gift_key}"}],
                    [{"text": "❌ Отмена", "callback_data": "cancel_order"}]
                ]
            else:
                keyboard["inline_keyboard"] = [[{"text": "❌ Отмена", "callback_data": "cancel_order"}]]

        elif step == "anonymous_choice":
            summary += "\n\n🔐 <b>Как отправить?</b>"
            keyboard["inline_keyboard"] = [
                [{"text": "🕵️ Анонимно", "callback_data": "anon_yes"},
                 {"text": "👁 Открыто",  "callback_data": "anon_no"}],
                [{"text": "❌ Отмена", "callback_data": "cancel_order"}]
            ]

        elif step == "waiting_username":
            summary += "\n\n⏳ <b>Введи username получателя:</b>\n<i>Он должен хотя бы раз написать /start боту</i>"
            keyboard["inline_keyboard"] = [[{"text": "❌ Отмена", "callback_data": "cancel_order"}]]

        elif step == "username_not_found":
            rec_un = state.get("pending_recipient_username", "")
            summary += (
                f"\n\n⚠️ <b>@{rec_un} не найден в базе</b>\n\n"
                "Подарок доставится когда получатель напишет /start\n\n"
                "👇 <b>Что делаем?</b>"
            )
            keyboard["inline_keyboard"] = [
                [{"text": "✅ Продолжить",      "callback_data": "confirm_unknown"}],
                [{"text": "🔄 Другой username", "callback_data": "reenter_username"}],
                [{"text": "❌ Отмена",           "callback_data": "cancel_order"}]
            ]

        elif step == "check_dialog":
            # FIX #7: этот шаг теперь реально вызывается из anon_yes когда нет диалога
            rec_un = state.get("recipient_username", "")
            summary += (
                f"\n\n⚠️ <b>Нужно одно действие!</b>\n\n"
                f"Попроси @{rec_un} написать @{SENDER_BOT_USERNAME}\n\n"
                f"<i>После этого нажми кнопку ниже</i>"
            )
            keyboard["inline_keyboard"] = [
                [{"text": "✅ Написал, проверить", "callback_data": "recheck_dialog"}],
                [{"text": "👁 Отправить открыто",  "callback_data": "switch_to_bot"}],
                [{"text": "❌ Отмена",               "callback_data": "cancel_order"}]
            ]

        elif step == "message_choice":
            summary += "\n\n💌 <b>Добавить подпись?</b>"
            keyboard["inline_keyboard"] = [
                [{"text": "📝 С подписью",  "callback_data": "msg_with"},
                 {"text": "🎁 Без подписи", "callback_data": "msg_without"}],
                [{"text": "❌ Отмена", "callback_data": "cancel_order"}]
            ]

        elif step == "waiting_message":
            summary += "\n\n✏️ <b>Напиши подпись</b> (макс. 200 символов):"
            keyboard["inline_keyboard"] = [[{"text": "❌ Отмена", "callback_data": "cancel_order"}]]

        elif step == "ready":
            summary += "\n\n✅ <b>Всё готово!</b>\nПроверь детали и оплати."
            keyboard["inline_keyboard"] = [
                [{"text": "💳 Оплатить", "callback_data": "proceed_payment"}],
                [{"text": "❌ Отмена",   "callback_data": "cancel_order"}]
            ]

        elif step == "payment_sent":
            summary += "\n\n💳 <b>Счёт отправлен!</b>\n⏰ Оплатите в течение 15 минут\n/cancel — отменить"
            keyboard["inline_keyboard"] = []

        try:
            message_id = self.order_messages.get(chat_id)
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if message_id:
                    url = f"{self.base_url}/editMessageText"
                    payload = {
                        "chat_id": chat_id, "message_id": message_id,
                        "text": summary, "parse_mode": "HTML",
                        "reply_markup": keyboard
                    }
                    async with session.post(url, json=payload) as resp:
                        result = await resp.json()
                        if not result.get("ok"):
                            logger.warning(f"editMessage fail: {result.get('description')}")
                            self.order_messages.pop(chat_id, None)
                            # FIX #4: передаём _depth+1 чтобы не зациклиться
                            return await self.update_order_message(chat_id, step, _depth=_depth + 1)
                        return True
                else:
                    url = f"{self.base_url}/sendMessage"
                    payload = {
                        "chat_id": chat_id, "text": summary,
                        "parse_mode": "HTML", "reply_markup": keyboard
                    }
                    async with session.post(url, json=payload) as resp:
                        result = await resp.json()
                        if result.get("ok"):
                            self.order_messages[chat_id] = result["result"]["message_id"]
                            return True
                        return False
        except Exception as e:
            logger.error(f"update_order_message: {e}")
            return False

    # ──────────────────────────────────────
    # ОСНОВНЫЕ ДЕЙСТВИЯ
    # ──────────────────────────────────────

    async def cancel_order(self, chat_id: int):
        try:
            msg_id = self.order_messages.get(chat_id)
            self._clear_user_data(chat_id)
            if msg_id:
                await self.delete_message(chat_id, msg_id)
            keyboard = {"inline_keyboard": [[{"text": "🏠 В главное меню", "callback_data": "back_to_shop"}]]}
            await self.send_message(
                chat_id,
                "❌ <b>Заказ отменён</b>\n\n<i>Вы всегда можете вернуться и выбрать подарок</i>",
                parse_mode="HTML", reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"cancel_order: {e}")

    async def send_gift_menu(self, chat_id: int):
        try:
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"{self.gifts['gift_1']['emoji']} {self.gifts['gift_1']['name']} — {self.gifts['gift_1']['price']}⭐",
                      "callback_data": "gift_1"}],
                    [{"text": f"{self.gifts['gift_2']['emoji']} {self.gifts['gift_2']['name']} — {self.gifts['gift_2']['price']}⭐",
                      "callback_data": "gift_2"}],
                    [{"text": f"{self.gifts['gift_3']['emoji']} {self.gifts['gift_3']['name']} — {self.gifts['gift_3']['price']}⭐",
                      "callback_data": "gift_3"}],
                    [{"text": f"{self.gifts['gift_4']['emoji']} {self.gifts['gift_4']['name']} — {self.gifts['gift_4']['price']}⭐",
                      "callback_data": "gift_4"}]
                ]
            }
            if chat_id == self.admin_id:
                keyboard["inline_keyboard"].append(
                    [{"text": "⚙️ Панель администратора", "callback_data": "admin_panel"}]
                )
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": msg_welcome(self.gifts, self.mtproto.ready),
                    "parse_mode": "HTML", "reply_markup": keyboard
                }
                async with session.post(url, json=payload) as resp:
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
        # FIX #10: валидация gift_key перед обращением к словарю
        if not gift_key or gift_key not in self.gifts:
            logger.error(f"send_invoice: невалидный gift_key={gift_key}")
            return False

        recipient = state.get("recipient_username", "self")
        gift = self.gifts[gift_key]
        unique_payload = f"{gift_key}_{chat_id}_{recipient}_{int(time.time()*1000)}"
        state["payload"] = unique_payload
        state["invoice_sent_at"] = time.time()

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.base_url}/sendInvoice"
                payload = {
                    "chat_id": chat_id,
                    "title": f"{gift['emoji']} {gift['name']}",
                    "description": f"Оплатите {gift['price']}⭐ для отправки подарка. /cancel — отмена",
                    "payload": unique_payload,
                    "currency": "XTR",
                    "prices": [{"label": gift['name'], "amount": gift['price']}]
                }
                async with session.post(url, json=payload) as resp:
                    result = await resp.json()
                    if result.get("ok"):
                        await self.update_order_message(chat_id, "payment_sent")
                        return True
                    logger.error(f"sendInvoice: {result.get('description')}")
                    return False
        except Exception as e:
            logger.error(f"send_invoice: {e}")
            return False

    async def send_admin_panel(self, chat_id: int):
        now = time.time()
        # Работаем с копией списка
        gifts_this_hour = sum(1 for t in list(self.antiban.gift_log) if now - t < 3600)
        can_send, _ = self.antiban.can_send_gift()

        keyboard = {"inline_keyboard": [
            [{"text": "🚫 Заблокировать",   "callback_data": "admin_block"},
             {"text": "✅ Разблокировать",   "callback_data": "admin_unblock"}],
            [{"text": "👥 Пользователи",     "callback_data": "admin_users"}],
            [{"text": "📢 Рассылка",         "callback_data": "admin_broadcast"}],
            [{"text": "🔄 Обновить диалоги", "callback_data": "admin_reload_dialogs"}],
            [{"text": "🔙 В магазин",        "callback_data": "back_to_shop"}]
        ]}

        panel_text = (
            "⚙️ <b>ПАНЕЛЬ АДМИНИСТРАТОРА</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Пользователей: <b>{len(self.all_users)}</b>\n"
            f"🚫 Заблокировано: <b>{len(self.blocked_users)}</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🛡 <b>Антибан статус:</b>\n"
            f"  MTProto:    <b>{'🟢 Готов' if self.mtproto.ready else '🔴 Офлайн'}</b>\n"
            f"  Диалогов:  <b>{len(self.mtproto.known_dialogs)}</b>\n"
            f"  Подарков/ч: <b>{gifts_this_hour}/{MAX_GIFTS_PER_HOUR}</b>\n"
            f"  Лимит:     <b>{'🟢 ОК' if can_send else '🔴 Превышен'}</b>\n\n"
            "👇 Выбери действие:"
        )
        # FIX #11: используем panel_text вместо text чтобы не затенять переменную
        await self.send_message(chat_id, panel_text, parse_mode="HTML", reply_markup=keyboard)

    # ──────────────────────────────────────
    # ОБРАБОТКА ПЛАТЕЖЕЙ
    # ──────────────────────────────────────

    async def handle_successful_payment(self, message: dict):
        chat_id = message["chat"]["id"]
        payment = message["successful_payment"]
        payment_id = payment.get("telegram_payment_charge_id")

        if payment_id in self.processed_payments:
            return
        self.processed_payments.add(payment_id)

        state = self.user_states.get(chat_id)
        if not state:
            logger.warning(f"Оплата {payment_id} без state для {chat_id}")
            return

        gift_key = state.get("gift_key")
        recipient = state.get("recipient_username", "self")
        message_text = state.get("message")
        anonymous = state.get("anonymous", False)

        # FIX #10: валидация перед обращением к словарю
        if not gift_key or gift_key not in self.gifts:
            logger.error(f"handle_payment: невалидный gift_key={gift_key}")
            return

        gift = self.gifts[gift_key]

        # FIX #3: payload_key с защитой от None
        payload_key = state.get("payload")
        if not payload_key:
            # Генерируем fallback ключ
            payload_key = f"fallback_{chat_id}_{int(time.time())}"
            logger.warning(f"payload отсутствует, используем fallback: {payload_key}")

        # СЕБЕ
        if recipient == "self":
            await self.send_message(chat_id, f"⏳ <b>Отправляю {gift['emoji']}...</b>", parse_mode="HTML")
            await asyncio.sleep(1)
            success = await self.send_gift_bot(chat_id, gift['gift_id'], message_text)
            if success:
                await self.send_message(
                    chat_id,
                    f"🎉 <b>Вы получили {gift['emoji']} {gift['name']}!</b>\n\n/start — вернуться в магазин",
                    parse_mode="HTML"
                )
            else:
                await self.send_message(chat_id, "❌ Ошибка доставки. Напишите в поддержку.")

        # ДРУГОМУ
        else:
            recipient_id = state.get("recipient_user_id")

            if recipient_id:
                await self.send_message(chat_id, "⏳ <b>Отправляю подарок...</b>", parse_mode="HTML")
                success, reason = await self.send_gift_smart(
                    recipient_id, gift['gift_id'], anonymous, message_text
                )

                if success:
                    sender_info = self.all_users.get(chat_id, {})
                    sender_name = sender_info.get("first_name", "Аноним")
                    await self.send_message(
                        recipient_id,
                        msg_success_recipient(gift, anonymous, sender_name, message_text),
                        parse_mode="HTML"
                    )
                    await self.send_message(chat_id, msg_success_sender(gift, recipient), parse_mode="HTML")

                elif reason == "no_dialog":
                    self.pending_gifts[payload_key] = {
                        "gift_key": gift_key, "sender_id": chat_id,
                        "recipient_username": recipient, "message": message_text,
                        "anonymous": anonymous
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
                        "recipient_username": recipient, "message": message_text,
                        "anonymous": anonymous
                    }
                    await self.send_message(
                        chat_id,
                        f"⏳ <b>Оплата принята!</b>\n\n"
                        f"🛡 Лимит отправок — подарок доставится через ~{wait_secs // 60} мин.",
                        parse_mode="HTML"
                    )

                else:
                    await self.send_message(chat_id, "❌ Ошибка доставки. Напишите в поддержку.")

            else:
                # Получатель ещё не писал боту
                self.pending_gifts[payload_key] = {
                    "gift_key": gift_key, "sender_id": chat_id,
                    "recipient_username": recipient, "message": message_text,
                    "anonymous": anonymous
                }
                await self.send_message(
                    chat_id,
                    f"⏳ <b>Оплата принята!</b>\n\nПодарок доставится когда @{recipient} напишет /start боту.",
                    parse_mode="HTML"
                )

        self._clear_user_data(chat_id)

    # ──────────────────────────────────────
    # НИЗКОУРОВНЕВЫЕ API
    # ──────────────────────────────────────

    async def send_message(self, chat_id: int, text: str,
                            parse_mode: str = None, reply_markup: dict = None):
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.base_url}/sendMessage"
                payload: dict = {"chat_id": chat_id, "text": text}
                if parse_mode:
                    payload["parse_mode"] = parse_mode
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                async with session.post(url, json=payload) as resp:
                    result = await resp.json()
                    return result["result"]["message_id"] if result.get("ok") else None
        except Exception as e:
            logger.error(f"send_message: {e}")
            return None

    async def answer_callback_query(self, cq_id: str, text: str = "", show_alert: bool = False) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.base_url}/answerCallbackQuery"
                payload = {"callback_query_id": cq_id, "text": text, "show_alert": show_alert}
                async with session.post(url, json=payload) as resp:
                    result = await resp.json()
                    return result.get("ok", False)
        except Exception as e:
            logger.error(f"answerCallbackQuery: {e}")
            return False

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.base_url}/deleteMessage"
                payload = {"chat_id": chat_id, "message_id": message_id}
                async with session.post(url, json=payload) as resp:
                    result = await resp.json()
                    return result.get("ok", False)
        except Exception as e:
            logger.error(f"delete_message: {e}")
            return False

    async def get_updates(self, offset: int = 0) -> list:
        try:
            timeout = aiohttp.ClientTimeout(total=35)  # > polling timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.base_url}/getUpdates"
                params: dict = {
                    "timeout": 30,
                    "allowed_updates": ["message", "callback_query", "pre_checkout_query"]
                }
                if offset > 0:
                    params["offset"] = offset
                async with session.get(url, params=params) as resp:
                    result = await resp.json()
                    return result.get("result", []) if result.get("ok") else []
        except Exception as e:
            logger.error(f"getUpdates: {e}")
            return []

    # ──────────────────────────────────────
    # ГЛАВНЫЙ ОБРАБОТЧИК
    # ──────────────────────────────────────

    async def process_update(self, update: dict):
        try:
            # ── СООБЩЕНИЯ ──
            if "message" in update:
                message = update["message"]

                # Сначала проверяем успешную оплату
                if "successful_payment" in message:
                    await self.handle_successful_payment(message)
                    return

                chat_id = message["chat"]["id"]
                text = message.get("text", "")
                message_id = message.get("message_id")
                user = message.get("from", {})
                username = user.get("username", "")

                self.register_user(user)

                # FIX #1: НЕ добавляем chat_id в known_dialogs здесь!
                # known_dialogs должны содержать только диалоги MTProto аккаунта
                # Они загружаются через load_dialogs() из реальных диалогов аккаунта

                if self.is_blocked(username):
                    await self.send_message(chat_id, "🚫 Вы заблокированы.")
                    return

                if text == "/start":
                    # FIX #2: проверяем с учётом истечения инвойса
                    if self.has_active_invoice(chat_id):
                        await self.send_message(
                            chat_id,
                            "⚠️ <b>Активный заказ!</b>\nОтмени через /cancel",
                            parse_mode="HTML"
                        )
                        return

                    # Доставка ожидающих подарков
                    # FIX #5: пропускаем если username пустой (нет @username)
                    if username:
                        delivered_keys = []
                        for payload_key, gift_data in list(self.pending_gifts.items()):
                            stored_rec = gift_data.get("recipient_username", "")
                            # FIX #5: не сравниваем пустые строки
                            if not stored_rec or stored_rec.lower() != username.lower():
                                continue

                            gift_key = gift_data["gift_key"]
                            sender_id = gift_data["sender_id"]
                            msg_text = gift_data.get("message")
                            anonymous = gift_data.get("anonymous", False)

                            if gift_key not in self.gifts:
                                delivered_keys.append(payload_key)
                                continue

                            gift = self.gifts[gift_key]
                            success, reason = await self.send_gift_smart(
                                chat_id, gift["gift_id"], anonymous, msg_text
                            )

                            if success:
                                sender_info = self.all_users.get(sender_id, {})
                                sender_name = sender_info.get("first_name", "Аноним")
                                await self.send_message(
                                    chat_id,
                                    msg_success_recipient(gift, anonymous, sender_name, msg_text),
                                    parse_mode="HTML"
                                )
                                await self.send_message(
                                    sender_id,
                                    msg_success_sender(gift, username),
                                    parse_mode="HTML"
                                )
                                delivered_keys.append(payload_key)
                            # if no_dialog — оставляем в pending

                        for key in delivered_keys:
                            self.pending_gifts.pop(key, None)

                    await self.send_gift_menu(chat_id)

                elif text == "/cancel":
                    if chat_id in self.user_states:
                        await self.cancel_order(chat_id)
                    else:
                        await self.send_message(chat_id, "ℹ️ Нет активного заказа.")

                elif chat_id in self.user_states:
                    state = self.user_states[chat_id]
                    waiting = state.get("waiting_for")

                    if waiting == "recipient_username":
                        valid, res = self.validate_username(text)
                        if not valid:
                            err_id = await self.send_message(chat_id, res)
                            await self.delete_message(chat_id, message_id)
                            if err_id:
                                await asyncio.sleep(3)
                                await self.delete_message(chat_id, err_id)
                            return

                        rec_un = res
                        if rec_un.lower() == username.lower():
                            err_id = await self.send_message(chat_id, "❌ Нельзя отправить самому себе!")
                            await self.delete_message(chat_id, message_id)
                            if err_id:
                                await asyncio.sleep(3)
                                await self.delete_message(chat_id, err_id)
                            return

                        found, user_id, _ = self.check_username_in_database(rec_un)

                        for mid in self.temp_messages.pop(chat_id, []):
                            await self.delete_message(chat_id, mid)
                        await self.delete_message(chat_id, message_id)

                        if found:
                            state["recipient_username"] = rec_un
                            state["recipient_user_id"] = user_id
                            state["recipient_known"] = True
                            state["waiting_for"] = None
                            await self.update_order_message(chat_id, "anonymous_choice")
                        else:
                            state["pending_recipient_username"] = rec_un
                            state["waiting_for"] = None
                            await self.update_order_message(chat_id, "username_not_found")

                    elif waiting == "gift_message":
                        msg_text = text.strip()
                        if len(msg_text) > 200:
                            err_id = await self.send_message(chat_id, "❌ Максимум 200 символов!")
                            await self.delete_message(chat_id, message_id)
                            if err_id:
                                await asyncio.sleep(3)
                                await self.delete_message(chat_id, err_id)
                            return

                        state["message"] = msg_text
                        state["waiting_for"] = None

                        for mid in self.temp_messages.pop(chat_id, []):
                            await self.delete_message(chat_id, mid)
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
                            await self.send_message(chat_id, f"⚠️ @{un} не был заблокирован.")
                        state["waiting_for"] = None

                    elif waiting == "broadcast_text":
                        bcast_text = text.strip()
                        state["broadcast_text"] = bcast_text
                        state["waiting_for"] = None
                        keyboard = {"inline_keyboard": [
                            [{"text": "✅ Отправить", "callback_data": "confirm_broadcast"}],
                            [{"text": "❌ Отмена",    "callback_data": "cancel_broadcast"}]
                        ]}
                        preview = (
                            f"📢 <b>Предпросмотр:</b>\n\n{bcast_text}\n\n"
                            f"<i>Отправить {len(self.all_users)} пользователям?</i>"
                        )
                        await self.send_message(chat_id, preview, parse_mode="HTML", reply_markup=keyboard)

            # ── CALLBACK QUERY ──
            if "callback_query" in update:
                cb = update["callback_query"]
                cq_id = cb["id"]
                chat_id = cb["message"]["chat"]["id"]
                data = cb["data"]
                username = cb.get("from", {}).get("username", "")

                if self.is_blocked(username) and not data.startswith("admin_"):
                    await self.answer_callback_query(cq_id, "🚫 Вы заблокированы!", show_alert=True)
                    return

                # FIX #6: НЕ делаем глобальный ack здесь — каждая ветка сама решает
                # когда и как ответить (пустой ack или с текстом/alert)

                if data == "anon_yes":
                    if chat_id in self.user_states:
                        state = self.user_states[chat_id]
                        recipient_id = state.get("recipient_user_id")
                        # FIX #7: проверяем диалог и показываем check_dialog если нужно
                        if recipient_id and self.mtproto.ready:
                            has_dialog = await self.mtproto.has_dialog_with_user(recipient_id)
                            if not has_dialog:
                                state["anonymous"] = True
                                await self.answer_callback_query(cq_id)
                                await self.update_order_message(chat_id, "check_dialog")
                                return
                        state["anonymous"] = True
                        await self.answer_callback_query(cq_id)
                        await self.update_order_message(chat_id, "message_choice")

                elif data == "anon_no":
                    if chat_id in self.user_states:
                        self.user_states[chat_id]["anonymous"] = False
                        await self.answer_callback_query(cq_id)
                        await self.update_order_message(chat_id, "message_choice")

                elif data == "switch_to_bot":
                    if chat_id in self.user_states:
                        self.user_states[chat_id]["anonymous"] = False
                        await self.answer_callback_query(cq_id, "👁 Переключено на открытую отправку")
                        await self.update_order_message(chat_id, "message_choice")

                elif data == "recheck_dialog":
                    # FIX #6: одиночный ack с нужным текстом
                    if chat_id in self.user_states:
                        recipient_id = self.user_states[chat_id].get("recipient_user_id")
                        if recipient_id:
                            await self.mtproto.load_dialogs()
                            has_dialog = await self.mtproto.has_dialog_with_user(recipient_id)
                            if has_dialog:
                                await self.answer_callback_query(cq_id, "✅ Диалог найден!")
                                await self.update_order_message(chat_id, "message_choice")
                            else:
                                await self.answer_callback_query(cq_id, "⏳ Ещё не написал...", show_alert=True)
                        else:
                            await self.answer_callback_query(cq_id)

                elif data == "confirm_unknown":
                    if chat_id in self.user_states:
                        rec_un = self.user_states[chat_id].get("pending_recipient_username")
                        if rec_un:
                            self.user_states[chat_id].update({
                                "recipient_username": rec_un,
                                "recipient_user_id": None,
                                "recipient_known": False
                            })
                            await self.answer_callback_query(cq_id)
                            await self.update_order_message(chat_id, "anonymous_choice")
                        else:
                            await self.answer_callback_query(cq_id)

                elif data == "reenter_username":
                    if chat_id in self.user_states:
                        self.user_states[chat_id]["waiting_for"] = "recipient_username"
                        self.user_states[chat_id].pop("pending_recipient_username", None)
                        await self.answer_callback_query(cq_id)
                        await self.update_order_message(chat_id, "waiting_username")
                        prompt_id = await self.send_message(chat_id, "👤 Введи username получателя (@username):")
                        if prompt_id:
                            self.temp_messages[chat_id] = [prompt_id]
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "cancel_order":
                    await self.answer_callback_query(cq_id)
                    await self.cancel_order(chat_id)

                elif data == "back_to_shop":
                    await self.answer_callback_query(cq_id)
                    await self.send_gift_menu(chat_id)

                elif data in self.gifts:
                    # FIX #2: проверяем с учётом истечения инвойса
                    if self.has_active_invoice(chat_id):
                        await self.answer_callback_query(cq_id, "⚠️ Активный заказ! /cancel", show_alert=True)
                        return
                    self.user_states[chat_id] = {"gift_key": data}
                    await self.answer_callback_query(cq_id)
                    await self.update_order_message(chat_id, "recipient")

                elif data.startswith("recipient_self_"):
                    gift_key = data.replace("recipient_self_", "")
                    self.user_states.setdefault(chat_id, {})
                    self.user_states[chat_id].update({
                        "gift_key": gift_key, "recipient": "self",
                        "recipient_username": "self", "anonymous": False
                    })
                    await self.answer_callback_query(cq_id)
                    await self.update_order_message(chat_id, "message_choice")

                elif data.startswith("recipient_other_"):
                    gift_key = data.replace("recipient_other_", "")
                    self.user_states.setdefault(chat_id, {})
                    self.user_states[chat_id].update({
                        "gift_key": gift_key, "recipient": "other",
                        "waiting_for": "recipient_username"
                    })
                    await self.answer_callback_query(cq_id)
                    await self.update_order_message(chat_id, "waiting_username")
                    prompt_id = await self.send_message(chat_id, "👤 Введи username получателя (@username):")
                    if prompt_id:
                        self.temp_messages[chat_id] = [prompt_id]

                elif data == "msg_with":
                    if chat_id in self.user_states:
                        self.user_states[chat_id]["has_message"] = "with"
                        self.user_states[chat_id]["waiting_for"] = "gift_message"
                        await self.answer_callback_query(cq_id)
                        await self.update_order_message(chat_id, "waiting_message")
                        prompt_id = await self.send_message(chat_id, "✏️ Напиши подпись (макс. 200 символов):")
                        if prompt_id:
                            self.temp_messages[chat_id] = [prompt_id]
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "msg_without":
                    if chat_id in self.user_states:
                        self.user_states[chat_id]["has_message"] = "without"
                        self.user_states[chat_id]["message"] = None
                        await self.answer_callback_query(cq_id)
                        await self.update_order_message(chat_id, "ready")
                    else:
                        await self.answer_callback_query(cq_id)

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

                # ── АДМИН ──
                elif data == "admin_panel":
                    if chat_id == self.admin_id:
                        await self.answer_callback_query(cq_id)
                        await self.send_admin_panel(chat_id)
                    else:
                        # FIX #6: одиночный ack с алертом
                        await self.answer_callback_query(cq_id, "⛔️ Нет доступа!", show_alert=True)

                elif data == "admin_reload_dialogs":
                    if chat_id == self.admin_id:
                        await self.mtproto.load_dialogs()
                        # FIX #6: одиночный ack с нужным текстом
                        await self.answer_callback_query(
                            cq_id, f"✅ Загружено {len(self.mtproto.known_dialogs)} диалогов!", show_alert=True
                        )
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "admin_block":
                    if chat_id == self.admin_id:
                        self.user_states[chat_id] = {"waiting_for": "block_username"}
                        await self.answer_callback_query(cq_id)
                        await self.send_message(chat_id, "🚫 Введи username для блокировки:")
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "admin_unblock":
                    if chat_id == self.admin_id:
                        self.user_states[chat_id] = {"waiting_for": "unblock_username"}
                        await self.answer_callback_query(cq_id)
                        await self.send_message(chat_id, "✅ Введи username для разблокировки:")
                    else:
                        await self.answer_callback_query(cq_id)

                elif data == "admin_users":
                    if chat_id == self.admin_id:
                        sorted_users = sorted(
                            self.all_users.items(),
                            key=lambda x: x[1]["last_seen"], reverse=True
                        )
                        # FIX #11: уникальное имя переменной users_text
                        users_text = "👥 <b>Последние пользователи:</b>\n\n"
                        for i, (uid, udata) in enumerate(sorted_users[:10], 1):
                            lseen = time.strftime("%d.%m %H:%M", time.localtime(udata["last_seen"]))
                            users_text += (
                                f"{i}. <b>{udata['first_name']}</b> {udata['username']}\n"
                                f"   <code>{uid}</code> • {lseen}\n\n"
                            )
                        await self.answer_callback_query(cq_id)
                        await self.send_message(chat_id, users_text, parse_mode="HTML")
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
                        bcast_text = self.user_states[chat_id].get("broadcast_text", "")
                        if bcast_text:
                            sent = 0
                            # FIX #8: исключаем заблокированных, исключаем самого админа
                            targets = [
                                uid for uid in self.all_users
                                if uid != chat_id
                                and not self.is_blocked(
                                    self.all_users[uid].get("username", "").lstrip("@")
                                )
                            ]
                            for uid in targets:
                                msg_id = await self.send_message(uid, bcast_text, parse_mode="HTML")
                                # FIX #12: считаем только реально отправленные
                                if msg_id is not None:
                                    sent += 1
                                await asyncio.sleep(0.1)
                            # Отправляем админу отдельно (один раз)
                            await self.send_message(chat_id, bcast_text, parse_mode="HTML")
                            await self.send_message(
                                chat_id,
                                f"✅ Рассылка завершена: отправлено <b>{sent + 1}</b> сообщений",
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
                    # Неизвестный callback — просто отвечаем
                    await self.answer_callback_query(cq_id)

            # ── PRE-CHECKOUT ──
            if "pre_checkout_query" in update:
                pcq = update["pre_checkout_query"]
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    url = f"{self.base_url}/answerPreCheckoutQuery"
                    await session.post(url, json={"pre_checkout_query_id": pcq["id"], "ok": True})

        except Exception as e:
            logger.error(f"process_update: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # ──────────────────────────────────────
    # ЗАПУСК
    # ──────────────────────────────────────

    async def get_bot_username(self) -> str:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.base_url}/getMe"
                async with session.get(url) as resp:
                    result = await resp.json()
                    return result["result"].get("username", "бот") if result.get("ok") else "бот"
        except Exception as e:
            logger.error(f"get_bot_username: {e}")
            return "бот"

    async def run(self):
        bot_username = await self.get_bot_username()
        print("\n" + "═" * 50)
        print("  🎁  GIFT BOT ЗАПУЩЕН")
        print("═" * 50)
        print(f"  🤖 Бот:      @{bot_username}")
        print(f"  👑 Админ:    {self.admin_id}")
        print(f"  🕵️  MTProto:  {'✅ Подключён' if self.mtproto.ready else '❌ Не подключён'}")
        print(f"  🛡️  Диалогов: {len(self.mtproto.known_dialogs)}")
        print(f"  ⚡ Лимит:    {MAX_GIFTS_PER_HOUR} подарков/час")
        print(f"  ⏱️  Инвойс:   {INVOICE_EXPIRE_SECONDS // 60} мин до истечения")
        print("═" * 50 + "\n")

        offset = 0
        error_count = 0

        while True:
            try:
                updates = await self.get_updates(offset)
                for update in updates:
                    offset = update["update_id"] + 1
                    await self.process_update(update)
                error_count = 0
                await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                print("\n🛑 Остановлен")
                break
            except Exception as e:
                error_count += 1
                logger.error(f"Ошибка цикла ({error_count}): {e}")
                if error_count > 10:
                    print("\n🔴 Слишком много ошибок подряд!")
                    break
                await asyncio.sleep(min(error_count * 2, 30))


# ═══════════════════════════════════════
# ТОЧКА ВХОДА
# ═══════════════════════════════════════

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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Пока!")
