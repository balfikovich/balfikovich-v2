import asyncio
import aiohttp
import logging
import json
import time

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8442227835:AAEm4UYtkDX8TrTpilX5iDJhxnMegkVdmzM"
ADMIN_ID = 5479063264

# ========== ЦЕНА АНОНИМНОСТИ (РЕДАКТИРУЙ ЗДЕСЬ) ==========
ANONYMITY_PRICE = 1  # стоимость в звёздах ⭐️
# =========================================================

GIFTS = {
    "gift_1": {
        "name": "🎄 Елка новогодняя",
        "emoji": "🎄",
        "price": 60,
        "gift_id": "5922558454332916696"
    },
    "gift_2": {
        "name": "🧸 Новогодний мишка",
        "emoji": "🧸",
        "price": 60,
        "gift_id": "5956217000635139069"
    },
    "gift_3": {
        "name": "💝 Февральское сердце",
        "emoji": "💝",
        "price": 60,
        "gift_id": "5801108895304779062"
    },
    "gift_4": {
        "name": "🧸 Февральский мишка",
        "emoji": "🧸",
        "price": 50,
        "gift_id": "5800655655995968830"
    }
}


class GiftSender:
    def __init__(self, bot_token: str, gifts: dict, admin_id: int):
        self.bot_token = bot_token
        self.gifts = gifts
        self.admin_id = admin_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

        self.processed_payments = set()
        self.blocked_users = set()
        self.all_users = {}
        self.pending_gifts = {}
        self.user_states = {}
        self.order_messages = {}
        self.temp_messages = {}

    # ─────────────────────────────────────────
    # УТИЛИТЫ
    # ─────────────────────────────────────────

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
            return False, "❌ Username слишком короткий! Минимум 5 символов."
        if not username.replace("_", "").isalnum():
            return False, "❌ Username может содержать только буквы, цифры и подчеркивание!"
        return True, username

    def check_username_in_database(self, username: str) -> tuple:
        username_clean = username.lstrip("@").lower()
        for user_id, user_data in self.all_users.items():
            user_username = user_data.get("username", "").lstrip("@").lower()
            if user_username == username_clean:
                return True, user_id, user_data.get("first_name", "Пользователь")
        return False, None, None

    def calc_total(self, chat_id: int) -> int:
        state = self.user_states.get(chat_id, {})
        gift_key = state.get("gift_key")
        if not gift_key or gift_key not in self.gifts:
            return 0
        base = self.gifts[gift_key]["price"]
        anon = ANONYMITY_PRICE if state.get("anonymous", False) else 0
        return base + anon

    # ─────────────────────────────────────────
    # СВОДКА ЗАКАЗА
    # ─────────────────────────────────────────

    def get_order_summary(self, chat_id: int) -> str:
        if chat_id not in self.user_states:
            return ""
        state = self.user_states[chat_id]
        gift_key = state.get("gift_key")
        if not gift_key or gift_key not in self.gifts:
            return ""

        gift = self.gifts[gift_key]
        recipient = state.get("recipient", "")
        recipient_username = state.get("recipient_username", "")
        message_text = state.get("message", "")
        is_anonymous = state.get("anonymous", False)
        total_price = self.calc_total(chat_id)

        summary = f"✨ <b>Ты выбрал: {gift['name']}</b>\n"
        summary += f"💰 Цена подарка: <b>{gift['price']} ⭐️</b>\n"
        if is_anonymous:
            summary += f"🕵️ Анонимность: <b>+{ANONYMITY_PRICE} ⭐️</b>\n"
        summary += f"💎 <b>Итого: {total_price} ⭐️</b>\n\n"
        summary += "📋 <b>Детали заказа:</b>\n"

        if recipient == "self":
            summary += "👤 Для кого: <b>Для себя</b>\n"
        elif recipient == "other":
            if recipient_username:
                summary += f"👤 Для кого: <b>Для @{recipient_username}</b>\n"
            else:
                summary += "👤 Для кого: <b>Для другого человека</b> ⏳\n"
        else:
            summary += "👤 Для кого: <i>не выбрано</i>\n"

        if "has_message" in state:
            if state["has_message"] == "with":
                if message_text:
                    summary += f"💌 Подпись: <b>Да</b>\n   <i>\"{message_text}\"</i>\n"
                else:
                    summary += "💌 Подпись: <b>Да</b> ⏳ <i>(ожидается ввод)</i>\n"
            else:
                summary += "💌 Подпись: <b>Нет</b>\n"
        else:
            summary += "💌 Подпись: <i>не выбрано</i>\n"

        if is_anonymous:
            summary += "🕵️ Анонимность: <b>Включена</b>\n"
        else:
            summary += "🕵️ Анонимность: <b>Нет</b>\n"

        return summary

    # ─────────────────────────────────────────
    # ОБНОВЛЕНИЕ СООБЩЕНИЯ ЗАКАЗА
    # ─────────────────────────────────────────

    async def update_order_message(self, chat_id: int, step: str):
        try:
            summary = self.get_order_summary(chat_id)
            if not summary:
                return False

            state = self.user_states[chat_id]
            is_anonymous = state.get("anonymous", False)
            total_price = self.calc_total(chat_id)
            keyboard = {"inline_keyboard": []}

            if step == "recipient":
                summary += "\n👇 <b>Для кого этот подарок?</b>"
                keyboard["inline_keyboard"] = [
                    [{"text": "🎁 Для себя", "callback_data": f"recipient_self_{state['gift_key']}"}],
                    [{"text": "💝 Для другого человека", "callback_data": f"recipient_other_{state['gift_key']}"}],
                    [{"text": "❌ Отменить заказ", "callback_data": "cancel_order"}]
                ]

            elif step == "waiting_username":
                summary += "\n⏳ <b>Жду ввод username получателя...</b>\n"
                summary += "<i>Получатель должен хотя бы раз писать боту /start</i>"
                keyboard["inline_keyboard"] = [
                    [{"text": "❌ Отменить заказ", "callback_data": "cancel_order"}]
                ]

            elif step == "username_not_found":
                ru = state.get("pending_recipient_username", "")
                summary += f"\n\n⚠️ <b>Пользователь @{ru} еще не писал боту</b>\n\n"
                summary += "Подарок будет отправлен когда он напишет /start.\n\n"
                summary += "👇 <b>Что делать?</b>"
                keyboard["inline_keyboard"] = [
                    [{"text": "✅ Да, продолжить", "callback_data": "confirm_unknown"}],
                    [{"text": "🔄 Ввести другой username", "callback_data": "reenter_username"}],
                    [{"text": "❌ Отменить заказ", "callback_data": "cancel_order"}]
                ]

            elif step == "message_choice":
                summary += "\n👇 <b>Добавить подпись к подарку?</b>"
                keyboard["inline_keyboard"] = [
                    [{"text": "📝 С подписью", "callback_data": "msg_with"}],
                    [{"text": "🎁 Без подписи", "callback_data": "msg_without"}],
                    [{"text": "❌ Отменить заказ", "callback_data": "cancel_order"}]
                ]

            elif step == "waiting_message":
                summary += "\n⏳ <b>Жду текст подписи...</b>"
                keyboard["inline_keyboard"] = [
                    [{"text": "❌ Отменить заказ", "callback_data": "cancel_order"}]
                ]

            elif step == "ready":
                summary += f"\n\n✅ <b>Всё готово к оплате!</b>"
                anon_btn = (
                    f"✅ Анонимность включена (+{ANONYMITY_PRICE} ⭐️)"
                    if is_anonymous else
                    f"🕵️ Добавить анонимность (+{ANONYMITY_PRICE} ⭐️)"
                )
                keyboard["inline_keyboard"] = [
                    [{"text": anon_btn, "callback_data": "toggle_anonymity"}],
                    [{"text": f"💳 Оплатить {total_price} ⭐️", "callback_data": "proceed_payment"}],
                    [{"text": "❌ Отменить заказ", "callback_data": "cancel_order"}]
                ]

            elif step == "payment_sent":
                summary += "\n\n💳 <b>Счёт отправлен!</b>\n\n"
                summary += "⏰ Оплатите в течение 15 минут\n"
                summary += "Для отмены напишите /cancel"
                keyboard["inline_keyboard"] = []

            message_id = self.order_messages.get(chat_id)

            if message_id:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{self.base_url}/editMessageText", json={
                        "chat_id": chat_id, "message_id": message_id,
                        "text": summary, "parse_mode": "HTML", "reply_markup": keyboard
                    }) as response:
                        result = await response.json()
                        if not result.get("ok"):
                            logger.warning(f"editMessageText failed ({result.get('description')}), resending")
                            del self.order_messages[chat_id]
                            return await self.update_order_message(chat_id, step)
                        return True
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{self.base_url}/sendMessage", json={
                        "chat_id": chat_id, "text": summary,
                        "parse_mode": "HTML", "reply_markup": keyboard
                    }) as response:
                        result = await response.json()
                        if result.get("ok"):
                            self.order_messages[chat_id] = result["result"]["message_id"]
                        return result.get("ok", False)

        except Exception as e:
            logger.error(f"update_order_message ошибка: {e}")
            return False

    # ─────────────────────────────────────────
    # ОТПРАВКА ПОДАРКА
    # ИСПРАВЛЕНО: hide_my_name → hide_name
    # ─────────────────────────────────────────

    async def send_gift(self, user_id: int, gift_id: str, text: str = None, anonymous: bool = False):
        try:
            logger.info(f"🎁 sendGift → user={user_id}, gift={gift_id}, anonymous={anonymous}")

            payload = {
                "user_id": user_id,
                "gift_id": gift_id,
            }

            if text:
                payload["text"] = text

            # ПРАВИЛЬНЫЙ ПАРАМЕТР ДЛЯ АНОНИМНОСТИ
            if anonymous:
                payload["hide_name"] = True

            logger.info(f"📤 sendGift payload: {json.dumps(payload, ensure_ascii=False)}")

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/sendGift", json=payload) as response:
                    result = await response.json()
                    logger.info(f"📥 sendGift ответ: {json.dumps(result, ensure_ascii=False)}")

                    if result.get("ok"):
                        logger.info(f"✅ Подарок отправлен (anonymous={anonymous})")
                        return True

                    logger.error(f"❌ sendGift ошибка: {result.get('description')}")
                    return False

        except Exception as e:
            logger.error(f"❌ sendGift исключение: {e}")
            return False

    # ─────────────────────────────────────────
    # ИНВОЙС
    # ─────────────────────────────────────────

    async def send_invoice(self, chat_id: int):
        try:
            if chat_id not in self.user_states:
                return False

            state = self.user_states[chat_id]
            gift_key = state.get("gift_key")
            if not gift_key or gift_key not in self.gifts:
                logger.error("send_invoice: gift_key не найден")
                return False

            gift = self.gifts[gift_key]
            is_anonymous = state.get("anonymous", False)
            total_price = self.calc_total(chat_id)

            recipient_raw = state.get("recipient_username", "self")
            recipient_safe = "".join(c for c in str(recipient_raw) if c.isalnum() or c == "_")
            unique_payload = f"{gift_key}_{chat_id}_{recipient_safe}_{int(time.time())}"

            state["payload"] = unique_payload
            state["invoice_sent_at"] = time.time()

            logger.info(f"💳 Инвойс: {total_price}⭐️, anon={is_anonymous}, payload={unique_payload}")

            label = gift["name"]
            if is_anonymous:
                label += " + Анонимность"

            invoice_payload = {
                "chat_id": chat_id,
                "title": f"{gift['emoji']} {gift['name']}",
                "description": (
                    f"{'🕵️ Анонимный подарок' if is_anonymous else '🎁 Подарок'}: "
                    f"{gift['name']} — {total_price} ⭐️. Для отмены /cancel"
                ),
                "payload": unique_payload,
                "currency": "XTR",
                "prices": [{"label": label, "amount": total_price}]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/sendInvoice", json=invoice_payload) as response:
                    result = await response.json()
                    logger.info(f"sendInvoice ответ: {json.dumps(result, ensure_ascii=False)}")

                    if result.get("ok"):
                        logger.info(f"✅ Инвойс отправлен: {total_price}⭐️")
                        await self.update_order_message(chat_id, "payment_sent")
                        return True
                    else:
                        err = result.get("description", "неизвестная ошибка")
                        logger.error(f"❌ sendInvoice: {err}")
                        await self.send_message(
                            chat_id,
                            f"❌ Не удалось создать счёт: <code>{err}</code>\n"
                            "Попробуй ещё раз или напиши /cancel",
                            parse_mode="HTML"
                        )
                        return False

        except Exception as e:
            logger.error(f"❌ send_invoice исключение: {e}")
            return False

    # ─────────────────────────────────────────
    # ОТМЕНА ЗАКАЗА
    # ─────────────────────────────────────────

    async def cancel_order(self, chat_id: int):
        try:
            if chat_id in self.user_states:
                del self.user_states[chat_id]
            if chat_id in self.order_messages:
                await self.delete_message(chat_id, self.order_messages[chat_id])
                del self.order_messages[chat_id]
            if chat_id in self.temp_messages:
                for mid in self.temp_messages[chat_id]:
                    await self.delete_message(chat_id, mid)
                del self.temp_messages[chat_id]

            await self.send_message(
                chat_id,
                "❌ <b>Заказ отменён</b>\n\nХочешь выбрать другой подарок? Напиши /start",
                parse_mode="HTML"
            )
            logger.info(f"❌ Заказ отменён: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"cancel_order ошибка: {e}")
            return False

    # ─────────────────────────────────────────
    # МЕНЮ ПОДАРКОВ
    # ─────────────────────────────────────────

    async def send_gift_menu(self, chat_id: int):
        try:
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"{g['emoji']} {g['name']} — {g['price']}⭐️", "callback_data": key}]
                    for key, g in self.gifts.items()
                ]
            }
            if chat_id == self.admin_id:
                keyboard["inline_keyboard"].append(
                    [{"text": "👑 Админ панель", "callback_data": "admin_panel"}]
                )

            lines = "\n".join(
                f"{g['emoji']} <b>{g['name']}</b> — {g['price']}⭐️"
                for g in self.gifts.values()
            )
            text = (
                "🎁 <b>Добро пожаловать в магазин подарков!</b>\n\n"
                f"{lines}\n\n"
                "👇 Нажми на кнопку чтобы купить!"
            )

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/sendMessage", json={
                    "chat_id": chat_id, "text": text,
                    "parse_mode": "HTML", "reply_markup": keyboard
                }) as response:
                    result = await response.json()
                    return result.get("ok", False)
        except Exception as e:
            logger.error(f"send_gift_menu ошибка: {e}")
            return False

    # ─────────────────────────────────────────
    # АДМИН ПАНЕЛЬ
    # ─────────────────────────────────────────

    async def send_admin_panel(self, chat_id: int):
        try:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🚫 Заблокировать", "callback_data": "admin_block"}],
                    [{"text": "✅ Разблокировать", "callback_data": "admin_unblock"}],
                    [{"text": "👥 Последние пользователи", "callback_data": "admin_users"}],
                    [{"text": "📢 Рассылка", "callback_data": "admin_broadcast"}],
                    [{"text": "🔙 В магазин", "callback_data": "back_to_shop"}]
                ]
            }
            text = (
                "👑 <b>АДМИН ПАНЕЛЬ</b>\n\n"
                f"📊 Пользователей: <b>{len(self.all_users)}</b>\n"
                f"🚫 Заблокировано: <b>{len(self.blocked_users)}</b>\n\n"
                "Выбери действие:"
            )
            await self.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"send_admin_panel ошибка: {e}")

    # ─────────────────────────────────────────
    # HTTP МЕТОДЫ
    # ─────────────────────────────────────────

    async def send_message(self, chat_id: int, text: str, parse_mode: str = None, reply_markup: dict = None):
        try:
            payload = {"chat_id": chat_id, "text": text}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            if reply_markup:
                payload["reply_markup"] = reply_markup

            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.base_url}/sendMessage", json=payload) as response:
                    result = await response.json()
                    if result.get("ok"):
                        return result["result"]["message_id"]
                    logger.warning(f"sendMessage failed: {result.get('description')}")
                    return None
        except Exception as e:
            logger.error(f"send_message ошибка: {e}")
            return None

    async def answer_callback_query(self, cq_id: str, text: str = "", show_alert: bool = False):
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.base_url}/answerCallbackQuery", json={
                    "callback_query_id": cq_id, "text": text, "show_alert": show_alert
                }) as response:
                    result = await response.json()
                    return result.get("ok", False)
        except Exception as e:
            logger.error(f"answerCallbackQuery ошибка: {e}")
            return False

    async def delete_message(self, chat_id: int, message_id: int):
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.base_url}/deleteMessage", json={
                    "chat_id": chat_id, "message_id": message_id
                }) as response:
                    result = await response.json()
                    return result.get("ok", False)
        except Exception as e:
            logger.error(f"deleteMessage ошибка: {e}")
            return False

    async def get_updates(self, offset: int = 0):
        try:
            params = {
                "timeout": 30,
                "allowed_updates": ["message", "callback_query", "pre_checkout_query"]
            }
            if offset > 0:
                params["offset"] = offset

            timeout = aiohttp.ClientTimeout(total=40)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/getUpdates", params=params) as response:
                    result = await response.json()
                    if result.get("ok"):
                        return result.get("result", [])
                    return []
        except Exception as e:
            logger.error(f"getUpdates ошибка: {e}")
            return []

    # ─────────────────────────────────────────
    # ОБРАБОТКА ОПЛАТЫ
    # ─────────────────────────────────────────

    async def handle_successful_payment(self, message: dict):
        chat_id = message["chat"]["id"]
        payment = message["successful_payment"]
        payment_id = payment.get("telegram_payment_charge_id", "")

        logger.info(f"💰 ОПЛАТА: payment_id={payment_id}, chat={chat_id}")

        if payment_id in self.processed_payments:
            logger.warning(f"⚠️ Дублированный платёж проигнорирован: {payment_id}")
            return
        self.processed_payments.add(payment_id)

        if chat_id not in self.user_states:
            logger.error(f"❌ State не найден для chat={chat_id} при оплате {payment_id}!")
            await self.send_message(
                chat_id,
                "✅ Оплата получена, но возникла ошибка при доставке подарка.\n"
                "Пожалуйста, обратитесь к администратору."
            )
            return

        state = self.user_states[chat_id]
        gift_key = state.get("gift_key")
        recipient = state.get("recipient_username", "self")
        message_text = state.get("message")
        is_anonymous = state.get("anonymous", False)

        if not gift_key or gift_key not in self.gifts:
            logger.error(f"❌ gift_key={gift_key} не найден при оплате")
            return

        gift = self.gifts[gift_key]

        # ── Для себя ──
        if recipient == "self":
            await self.send_message(chat_id, f"⏳ Отправляю {gift['emoji']}...")
            await asyncio.sleep(1)
            success = await self.send_gift(chat_id, gift["gift_id"], message_text, anonymous=False)
            if success:
                await self.send_message(
                    chat_id,
                    f"🎉 Ты получил {gift['emoji']} <b>{gift['name']}</b>!\n\nХочешь ещё? Напиши /start",
                    parse_mode="HTML"
                )
            else:
                await self.send_message(chat_id, "❌ Ошибка при отправке подарка. Обратись к администратору.")

        # ── Для другого ──
        else:
            recipient_id = state.get("recipient_user_id")

            if recipient_id:
                success = await self.send_gift(
                    recipient_id, gift["gift_id"], message_text, anonymous=is_anonymous
                )
                if success:
                    sender_info = self.all_users.get(chat_id, {})
                    sender_name = sender_info.get("first_name", "Кто-то")

                    if is_anonymous:
                        notif = f"🎉 Ты получил {gift['emoji']} <b>{gift['name']}</b> от анонима!"
                    else:
                        notif = f"🎉 Ты получил {gift['emoji']} <b>{gift['name']}</b> от <b>{sender_name}</b>!"

                    if message_text:
                        notif += f"\n\n💌 <i>{message_text}</i>"

                    await self.send_message(recipient_id, notif, parse_mode="HTML")

                    confirm = (
                        f"✅ Анонимный подарок доставлен @{recipient}! 🕵️"
                        if is_anonymous else
                        f"✅ Подарок доставлен @{recipient}!"
                    )
                    await self.send_message(chat_id, confirm)
                else:
                    await self.send_message(chat_id, "❌ Ошибка при доставке. Обратись к администратору.")
            else:
                payload_key = state.get("payload", f"pending_{chat_id}_{int(time.time())}")
                self.pending_gifts[payload_key] = {
                    "gift_key": gift_key,
                    "sender_id": chat_id,
                    "recipient_username": recipient,
                    "message": message_text,
                    "anonymous": is_anonymous
                }
                await self.send_message(
                    chat_id,
                    f"✅ Оплачено! Подарок будет доставлен когда @{recipient} напишет /start",
                    parse_mode="HTML"
                )

        for storage in [self.user_states, self.order_messages, self.temp_messages]:
            if chat_id in storage:
                del storage[chat_id]

    # ─────────────────────────────────────────
    # ОБРАБОТКА ВСЕХ АПДЕЙТОВ
    # ─────────────────────────────────────────

    async def process_update(self, update: dict):
        try:
            if "pre_checkout_query" in update:
                pcq = update["pre_checkout_query"]
                logger.info(f"💳 Pre-checkout: id={pcq['id']}, amount={pcq.get('total_amount')}⭐️")
                timeout = aiohttp.ClientTimeout(total=8)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    await session.post(
                        f"{self.base_url}/answerPreCheckoutQuery",
                        json={"pre_checkout_query_id": pcq["id"], "ok": True}
                    )
                return

            if "message" in update and "successful_payment" in update["message"]:
                await self.handle_successful_payment(update["message"])
                return

            if "message" in update:
                message = update["message"]
                chat_id = message["chat"]["id"]
                text = message.get("text", "")
                message_id = message.get("message_id")
                user = message.get("from", {})
                username = user.get("username", "")

                self.register_user(user)

                if self.is_blocked(username):
                    await self.send_message(chat_id, "🚫 Вы заблокированы.")
                    return

                if text == "/start":
                    if chat_id in self.user_states and self.user_states[chat_id].get("invoice_sent_at"):
                        await self.send_message(chat_id, "⚠️ У тебя активный заказ! /cancel для отмены")
                        return

                    if username:
                        pending_keys = [
                            k for k, v in self.pending_gifts.items()
                            if v.get("recipient_username", "").lower() == username.lower()
                        ]
                        for payload_key in pending_keys:
                            gift_data = self.pending_gifts.get(payload_key)
                            if not gift_data:
                                continue
                            gift = self.gifts.get(gift_data["gift_key"])
                            if not gift:
                                continue

                            is_anon = gift_data.get("anonymous", False)
                            sender_id = gift_data["sender_id"]
                            msg = gift_data.get("message")

                            success = await self.send_gift(chat_id, gift["gift_id"], msg, anonymous=is_anon)
                            if success:
                                sender_info = self.all_users.get(sender_id, {})
                                sender_name = sender_info.get("first_name", "Кто-то")
                                sender_uname = sender_info.get("username", "")

                                if is_anon:
                                    notif = f"🎉 Ты получил {gift['emoji']} <b>{gift['name']}</b> от анонима!"
                                else:
                                    from_text = (
                                        f"от <b>{sender_name}</b> ({sender_uname})"
                                        if sender_uname != "нет username"
                                        else f"от <b>{sender_name}</b>"
                                    )
                                    notif = f"🎉 Ты получил {gift['emoji']} <b>{gift['name']}</b> {from_text}!"

                                if msg:
                                    notif += f"\n\n💌 <i>{msg}</i>"

                                await self.send_message(chat_id, notif, parse_mode="HTML")
                                await self.send_message(
                                    sender_id,
                                    f"✅ Твой подарок {gift['emoji']} доставлен @{username}!",
                                    parse_mode="HTML"
                                )
                            del self.pending_gifts[payload_key]

                    await self.send_gift_menu(chat_id)

                elif text == "/cancel":
                    if chat_id in self.user_states:
                        await self.cancel_order(chat_id)
                    else:
                        await self.send_message(chat_id, "❌ Нет активного заказа.")

                elif chat_id in self.user_states:
                    state = self.user_states[chat_id]
                    waiting = state.get("waiting_for")

                    if waiting == "recipient_username":
                        valid, result = self.validate_username(text)
                        if not valid:
                            err_id = await self.send_message(chat_id, result)
                            await self.delete_message(chat_id, message_id)
                            if err_id:
                                await asyncio.sleep(3)
                                await self.delete_message(chat_id, err_id)
                            return

                        recipient_username = result
                        if recipient_username.lower() == username.lower():
                            err_id = await self.send_message(
                                chat_id, "❌ Нельзя отправить самому себе!\nВыбери 'Для себя'."
                            )
                            await self.delete_message(chat_id, message_id)
                            if err_id:
                                await asyncio.sleep(3)
                                await self.delete_message(chat_id, err_id)
                            return

                        found, user_id, _ = self.check_username_in_database(recipient_username)

                        if chat_id in self.temp_messages:
                            for mid in self.temp_messages[chat_id]:
                                await self.delete_message(chat_id, mid)
                            del self.temp_messages[chat_id]
                        await self.delete_message(chat_id, message_id)

                        if found:
                            state["recipient_username"] = recipient_username
                            state["recipient_user_id"] = user_id
                            state["recipient_known"] = True
                            state["waiting_for"] = None
                            await self.update_order_message(chat_id, "message_choice")
                        else:
                            state["pending_recipient_username"] = recipient_username
                            state["waiting_for"] = None
                            await self.update_order_message(chat_id, "username_not_found")

                    elif waiting == "gift_message":
                        msg_text = text.strip()
                        if len(msg_text) > 200:
                            err_id = await self.send_message(
                                chat_id, "❌ Подпись слишком длинная! Максимум 200 символов."
                            )
                            await self.delete_message(chat_id, message_id)
                            if err_id:
                                await asyncio.sleep(3)
                                await self.delete_message(chat_id, err_id)
                            return

                        state["message"] = msg_text
                        state["waiting_for"] = None

                        if chat_id in self.temp_messages:
                            for mid in self.temp_messages[chat_id]:
                                await self.delete_message(chat_id, mid)
                            del self.temp_messages[chat_id]

                        await self.delete_message(chat_id, message_id)
                        await self.update_order_message(chat_id, "ready")

                    elif waiting == "block_username":
                        to_block = text.strip().lstrip("@").lower()
                        self.blocked_users.add(to_block)
                        state["waiting_for"] = None
                        await self.send_message(chat_id, f"✅ @{to_block} заблокирован!")

                    elif waiting == "unblock_username":
                        to_unblock = text.strip().lstrip("@").lower()
                        if to_unblock in self.blocked_users:
                            self.blocked_users.remove(to_unblock)
                            await self.send_message(chat_id, f"✅ @{to_unblock} разблокирован!")
                        else:
                            await self.send_message(chat_id, f"❌ @{to_unblock} не заблокирован.")
                        state["waiting_for"] = None

                    elif waiting == "broadcast_text":
                        state["broadcast_text"] = text.strip()
                        state["waiting_for"] = None
                        keyboard = {"inline_keyboard": [
                            [{"text": "✅ Отправить", "callback_data": "confirm_broadcast"}],
                            [{"text": "❌ Отмена", "callback_data": "cancel_broadcast"}]
                        ]}
                        preview = (
                            f"📢 <b>Предпросмотр:</b>\n\n{text.strip()}\n\n"
                            f"Отправить <b>{len(self.all_users)}</b> пользователям?"
                        )
                        await self.send_message(chat_id, preview, parse_mode="HTML", reply_markup=keyboard)

            if "callback_query" in update:
                cb = update["callback_query"]
                cq_id = cb["id"]
                chat_id = cb["message"]["chat"]["id"]
                data = cb["data"]
                user = cb.get("from", {})
                username = user.get("username", "")

                if self.is_blocked(username) and not data.startswith("admin_"):
                    await self.answer_callback_query(cq_id, "🚫 Заблокирован!", show_alert=True)
                    return

                if data == "toggle_anonymity":
                    if chat_id in self.user_states:
                        state = self.user_states[chat_id]
                        state["anonymous"] = not state.get("anonymous", False)
                        if state["anonymous"]:
                            await self.answer_callback_query(cq_id, f"🕵️ Анонимность включена (+{ANONYMITY_PRICE} ⭐️)")
                        else:
                            await self.answer_callback_query(cq_id, "❌ Анонимность отключена")
                        await self.update_order_message(chat_id, "ready")
                    else:
                        await self.answer_callback_query(cq_id, "⚠️ Заказ не найден", show_alert=True)
                    return

                elif data == "confirm_unknown":
                    if chat_id in self.user_states:
                        state = self.user_states[chat_id]
                        ru = state.get("pending_recipient_username")
                        if ru:
                            state["recipient_username"] = ru
                            state["recipient_user_id"] = None
                            state["recipient_known"] = False
                            await self.update_order_message(chat_id, "message_choice")
                    await self.answer_callback_query(cq_id)

                elif data == "reenter_username":
                    if chat_id in self.user_states:
                        state = self.user_states[chat_id]
                        state["waiting_for"] = "recipient_username"
                        state["pending_recipient_username"] = None
                        await self.update_order_message(chat_id, "waiting_username")
                        p_id = await self.send_message(chat_id, "👤 Введи username получателя:")
                        if p_id:
                            self.temp_messages[chat_id] = [p_id]
                    await self.answer_callback_query(cq_id)

                elif data == "cancel_order":
                    await self.cancel_order(chat_id)
                    await self.answer_callback_query(cq_id)

                elif data == "admin_panel":
                    if chat_id == self.admin_id:
                        await self.send_admin_panel(chat_id)
                        await self.answer_callback_query(cq_id)
                    else:
                        await self.answer_callback_query(cq_id, "⛔️ Нет доступа!", show_alert=True)

                elif data == "back_to_shop":
                    await self.send_gift_menu(chat_id)
                    await self.answer_callback_query(cq_id)

                elif data == "admin_block":
                    if chat_id == self.admin_id:
                        self.user_states[chat_id] = {"waiting_for": "block_username"}
                        await self.send_message(chat_id, "🚫 Введи username для блокировки:")
                        await self.answer_callback_query(cq_id)

                elif data == "admin_unblock":
                    if chat_id == self.admin_id:
                        self.user_states[chat_id] = {"waiting_for": "unblock_username"}
                        await self.send_message(chat_id, "✅ Введи username для разблокировки:")
                        await self.answer_callback_query(cq_id)

                elif data == "admin_users":
                    if chat_id == self.admin_id:
                        sorted_users = sorted(
                            self.all_users.items(), key=lambda x: x[1]["last_seen"], reverse=True
                        )
                        text = "👥 <b>Последние 10 пользователей:</b>\n\n"
                        for i, (uid, ud) in enumerate(sorted_users[:10], 1):
                            ts = time.strftime("%d.%m %H:%M", time.localtime(ud["last_seen"]))
                            text += f"{i}. <b>{ud['first_name']}</b> ({ud['username']})\n   <code>{uid}</code> — {ts}\n\n"
                        await self.send_message(chat_id, text, parse_mode="HTML")
                        await self.answer_callback_query(cq_id)

                elif data == "admin_broadcast":
                    if chat_id == self.admin_id:
                        self.user_states[chat_id] = {"waiting_for": "broadcast_text"}
                        await self.send_message(chat_id, "📢 Введи текст рассылки:")
                        await self.answer_callback_query(cq_id)

                elif data == "confirm_broadcast":
                    if chat_id == self.admin_id and chat_id in self.user_states:
                        btext = self.user_states[chat_id].get("broadcast_text")
                        if btext:
                            sent = 0
                            for uid in list(self.all_users.keys()):
                                if await self.send_message(uid, btext, parse_mode="HTML"):
                                    sent += 1
                                await asyncio.sleep(0.05)
                            await self.send_message(chat_id, f"✅ Отправлено: {sent}/{len(self.all_users)}")
                        del self.user_states[chat_id]
                        await self.answer_callback_query(cq_id)

                elif data == "cancel_broadcast":
                    if chat_id in self.user_states:
                        del self.user_states[chat_id]
                    await self.send_message(chat_id, "❌ Рассылка отменена.")
                    await self.answer_callback_query(cq_id)

                elif data in self.gifts:
                    if chat_id in self.user_states and self.user_states[chat_id].get("invoice_sent_at"):
                        await self.answer_callback_query(cq_id, "⚠️ Активный заказ! /cancel для отмены", show_alert=True)
                        return
                    if chat_id in self.order_messages:
                        await self.delete_message(chat_id, self.order_messages[chat_id])
                        del self.order_messages[chat_id]
                    self.user_states[chat_id] = {"gift_key": data, "anonymous": False}
                    await self.update_order_message(chat_id, "recipient")
                    await self.answer_callback_query(cq_id)

                elif data.startswith("recipient_self_"):
                    gift_key = data.replace("recipient_self_", "")
                    if chat_id not in self.user_states:
                        self.user_states[chat_id] = {"anonymous": False}
                    self.user_states[chat_id].update({
                        "gift_key": gift_key, "recipient": "self", "recipient_username": "self"
                    })
                    await self.update_order_message(chat_id, "message_choice")
                    await self.answer_callback_query(cq_id)

                elif data.startswith("recipient_other_"):
                    gift_key = data.replace("recipient_other_", "")
                    if chat_id not in self.user_states:
                        self.user_states[chat_id] = {"anonymous": False}
                    self.user_states[chat_id].update({
                        "gift_key": gift_key, "recipient": "other", "waiting_for": "recipient_username"
                    })
                    await self.update_order_message(chat_id, "waiting_username")
                    p_id = await self.send_message(chat_id, "👤 Введи username получателя:")
                    if p_id:
                        self.temp_messages[chat_id] = [p_id]
                    await self.answer_callback_query(cq_id)

                elif data == "msg_with":
                    if chat_id in self.user_states:
                        state = self.user_states[chat_id]
                        state["has_message"] = "with"
                        state["waiting_for"] = "gift_message"
                        await self.update_order_message(chat_id, "waiting_message")
                        p_id = await self.send_message(chat_id, "📝 Введи подпись (макс 200 символов):")
                        if p_id:
                            self.temp_messages[chat_id] = [p_id]
                        await self.answer_callback_query(cq_id)

                elif data == "msg_without":
                    if chat_id in self.user_states:
                        self.user_states[chat_id]["has_message"] = "without"
                        self.user_states[chat_id]["message"] = None
                        await self.update_order_message(chat_id, "ready")
                        await self.answer_callback_query(cq_id)

                elif data == "proceed_payment":
                    if chat_id in self.user_states:
                        state = self.user_states[chat_id]
                        gift_key = state.get("gift_key")
                        gift = self.gifts.get(gift_key)
                        if not gift:
                            await self.answer_callback_query(cq_id, "⚠️ Ошибка заказа", show_alert=True)
                            return

                        is_anonymous = state.get("anonymous", False)
                        total_price = self.calc_total(chat_id)

                        disclaimer = (
                            "⚠️ <b>ВАЖНО:</b>\n\n"
                            "• Подарок отправляется после оплаты\n"
                            "• Подарки <b>нельзя продать</b>\n"
                            "• Проверь все данные!\n\n"
                            f"💎 К оплате: <b>{total_price} ⭐️</b>\n"
                        )
                        if is_anonymous:
                            disclaimer += "🕵️ Отправляется <b>анонимно</b>\n"
                        disclaimer += "\nСчёт отправлен ниже 👇"

                        await self.send_message(chat_id, disclaimer, parse_mode="HTML")
                        await asyncio.sleep(0.5)
                        await self.send_invoice(chat_id)
                        await self.answer_callback_query(cq_id)

        except Exception as e:
            logger.error(f"❌ process_update ошибка: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # ─────────────────────────────────────────
    # ГЛАВНЫЙ ЦИКЛ
    # ─────────────────────────────────────────

    async def run(self):
        logger.info("🚀 Запуск бота...")
        bot_username = await self.get_bot_username()

        stale = await self.get_updates(offset=0)
        offset = (stale[-1]["update_id"] + 1) if stale else 0
        if stale:
            logger.info(f"⏩ Пропущено {len(stale)} старых апдейтов (offset={offset})")

        print("\n" + "=" * 50)
        print("✅ БОТ РАБОТАЕТ!")
        print(f"👉 https://t.me/{bot_username}")
        print(f"👑 Админ ID: {self.admin_id}")
        print(f"🕵️ Цена анонимности: {ANONYMITY_PRICE} ⭐️")
        print("=" * 50 + "\n")

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
                logger.error(f"❌ Ошибка цикла ({error_count}): {e}")
                if error_count > 10:
                    print("\n🔴 КРИТИЧЕСКАЯ ОШИБКА — перезапусти бота")
                    break
                await asyncio.sleep(min(2 * error_count, 30))

    async def get_bot_username(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/getMe") as response:
                    result = await response.json()
                    if result.get("ok"):
                        return result["result"].get("username", "бот")
            return "бот"
        except:
            return "бот"


async def main():
    sender = GiftSender(bot_token=BOT_TOKEN, gifts=GIFTS, admin_id=ADMIN_ID)
    await sender.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Пока!")
