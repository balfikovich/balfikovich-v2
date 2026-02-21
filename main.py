import asyncio
import aiohttp
import logging
import json
import time

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8442227835:AAEm4UYtkDX8TrTpilX5iDJhxnMegkVdmzM"
ADMIN_ID = 5479063264

# Список подарков
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
        "price": 60,
        "gift_id": "5800655655995968830"
    }
}
# ==================================

class GiftSender:
    def __init__(self, bot_token: str, gifts: dict, admin_id: int):
        self.bot_token = bot_token
        self.gifts = gifts
        self.admin_id = admin_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Хранилища данных
        self.processed_payments = set()
        self.blocked_users = set()
        self.all_users = {}
        self.pending_gifts = {}
        self.user_states = {}
        self.order_messages = {}
        self.temp_messages = {}
    
    def is_blocked(self, username: str) -> bool:
        """Проверка заблокирован ли пользователь"""
        if not username:
            return False
        username_clean = username.lstrip("@").lower()
        return username_clean in self.blocked_users
    
    def register_user(self, user_data: dict):
        """Регистрация пользователя"""
        user_id = user_data.get("id")
        username = user_data.get("username", "")
        first_name = user_data.get("first_name", "Пользователь")
        
        if user_id:
            self.all_users[user_id] = {
                "username": f"@{username}" if username else "нет username",
                "first_name": first_name,
                "last_seen": time.time()
            }
            logger.info(f"👤 Зарегистрирован: {user_id} (@{username})")
    
    def validate_username(self, username: str) -> tuple:
        """Базовая валидация username"""
        username = username.strip().lstrip("@")
        
        if not username:
            return False, "❌ Username не может быть пустым!"
        
        if len(username) < 5:
            return False, "❌ Username слишком короткий! Минимум 5 символов."
        
        if not username.replace("_", "").isalnum():
            return False, "❌ Username может содержать только буквы, цифры и подчеркивание!"
        
        return True, username
    
    def check_username_in_database(self, username: str) -> tuple:
        """Проверка username в нашей базе пользователей"""
        username_clean = username.lstrip("@").lower()
        
        for user_id, user_data in self.all_users.items():
            user_username = user_data.get("username", "").lstrip("@").lower()
            if user_username == username_clean:
                first_name = user_data.get("first_name", "Пользователь")
                logger.info(f"✅ Username @{username} найден в базе (ID: {user_id})")
                return True, user_id, first_name
        
        logger.info(f"⚠️ Username @{username} не найден в базе")
        return False, None, None
    
    def get_order_summary(self, chat_id: int) -> str:
        """Формирование сводки заказа"""
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
        
        summary = f"✨ <b>Ты выбрал: {gift['name']}</b>\n"
        summary += f"💰 Цена: <b>{gift['price']} звезд ⭐️</b>\n\n"
        summary += "📋 <b>Детали заказа:</b>\n"
        
        # Получатель
        if recipient == "self":
            summary += "👤 Для кого: <b>Для себя</b>\n"
        elif recipient == "other":
            if recipient_username:
                summary += f"👤 Для кого: <b>Для @{recipient_username}</b>\n"
            else:
                summary += "👤 Для кого: <b>Для другого человека</b> ⏳\n"
        else:
            summary += "👤 Для кого: <i>не выбрано</i>\n"
        
        # Подпись
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
        
        return summary
    
    async def send_gift(self, user_id: int, gift_id: str, text: str = None):
        """Отправка подарка пользователю"""
        try:
            logger.info(f"🎁 Отправка подарка {gift_id} пользователю {user_id}")
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sendGift"
                payload = {
                    "user_id": user_id,
                    "gift_id": gift_id
                }
                
                if text:
                    payload["text"] = text
                
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    logger.info(f"Ответ API sendGift: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    
                    if result.get("ok"):
                        logger.info(f"✅ Подарок успешно отправлен!")
                        return True
                    else:
                        error_description = result.get("description", "Неизвестная ошибка")
                        logger.error(f"❌ Ошибка API sendGift: {error_description}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при отправке подарка: {e}")
            return False
    
    async def update_order_message(self, chat_id: int, step: str):
        """Обновление сообщения с заказом"""
        try:
            summary = self.get_order_summary(chat_id)
            
            if not summary:
                return False
            
            state = self.user_states[chat_id]
            
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
                recipient_username = state.get("pending_recipient_username", "")
                summary += f"\n\n⚠️ <b>Пользователь @{recipient_username} еще не писал боту</b>\n\n"
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
                summary += "\n\n✅ <b>Всё готово к оплате!</b>"
                keyboard["inline_keyboard"] = [
                    [{"text": "💳 Перейти к оплате", "callback_data": "proceed_payment"}],
                    [{"text": "❌ Отменить заказ", "callback_data": "cancel_order"}]
                ]
            
            elif step == "payment_sent":
                summary += "\n\n💳 <b>Счет отправлен!</b>\n\n"
                summary += "⏰ Оплатите в течение 15 минут\n"
                summary += "Для отмены напишите /cancel"
                keyboard["inline_keyboard"] = []
            
            message_id = self.order_messages.get(chat_id)
            
            if message_id:
                async with aiohttp.ClientSession() as session:
                    url = f"{self.base_url}/editMessageText"
                    payload = {
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "text": summary,
                        "parse_mode": "HTML",
                        "reply_markup": keyboard
                    }
                    
                    async with session.post(url, json=payload) as response:
                        result = await response.json()
                        return result.get("ok", False)
            else:
                async with aiohttp.ClientSession() as session:
                    url = f"{self.base_url}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": summary,
                        "parse_mode": "HTML",
                        "reply_markup": keyboard
                    }
                    
                    async with session.post(url, json=payload) as response:
                        result = await response.json()
                        
                        if result.get("ok"):
                            self.order_messages[chat_id] = result["result"]["message_id"]
                        
                        return result.get("ok", False)
                    
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения: {e}")
            return False
    
    async def cancel_order(self, chat_id: int):
        """Отмена заказа"""
        try:
            if chat_id in self.user_states:
                del self.user_states[chat_id]
            
            if chat_id in self.order_messages:
                message_id = self.order_messages[chat_id]
                await self.delete_message(chat_id, message_id)
                del self.order_messages[chat_id]
            
            if chat_id in self.temp_messages:
                for msg_id in self.temp_messages[chat_id]:
                    await self.delete_message(chat_id, msg_id)
                del self.temp_messages[chat_id]
            
            await self.send_message(
                chat_id,
                "❌ <b>Заказ отменен</b>\n\nХочешь выбрать другой подарок? Напиши /start",
                parse_mode="HTML"
            )
            
            logger.info(f"❌ Заказ отменен для {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отмены заказа: {e}")
            return False
    
    async def send_gift_menu(self, chat_id: int):
        """Отправка меню с подарками"""
        try:
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"{self.gifts['gift_1']['emoji']} Елка новогодняя - {self.gifts['gift_1']['price']}⭐️", 
                      "callback_data": "gift_1"}],
                    [{"text": f"{self.gifts['gift_2']['emoji']} Новогодний мишка - {self.gifts['gift_2']['price']}⭐️", 
                      "callback_data": "gift_2"}],
                    [{"text": f"{self.gifts['gift_3']['emoji']} Февральское сердце - {self.gifts['gift_3']['price']}⭐️", 
                      "callback_data": "gift_3"}],
                    [{"text": f"{self.gifts['gift_4']['emoji']} Февральский мишка - {self.gifts['gift_4']['price']}⭐️", 
                      "callback_data": "gift_4"}]
                ]
            }
            
            if chat_id == self.admin_id:
                keyboard["inline_keyboard"].append([{"text": "👑 Админ панель", "callback_data": "admin_panel"}])
            
            message_text = (
                "🎁 <b>Добро пожаловать в магазин подарков!</b>\n\n"
                "Выбери подарок который хочешь купить:\n\n"
                f"🎄 <b>Елка новогодняя</b> - {self.gifts['gift_1']['price']}⭐️\n"
                f"🧸 <b>Новогодний мишка</b> - {self.gifts['gift_2']['price']}⭐️\n"
                f"💝 <b>Февральское сердце</b> - {self.gifts['gift_3']['price']}⭐️\n"
                f"🧸 <b>Февральский мишка</b> - {self.gifts['gift_4']['price']}⭐️\n\n"
                "Нажми на кнопку чтобы купить! 👇"
            )
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": message_text,
                    "parse_mode": "HTML",
                    "reply_markup": keyboard
                }
                
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    return result.get("ok", False)
                    
        except Exception as e:
            logger.error(f"Ошибка отправки меню: {e}")
            return False
    
    async def send_admin_panel(self, chat_id: int):
        """Отправка админ панели"""
        try:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🚫 Заблокировать пользователя", "callback_data": "admin_block"}],
                    [{"text": "✅ Разблокировать пользователя", "callback_data": "admin_unblock"}],
                    [{"text": "👥 Последние пользователи", "callback_data": "admin_users"}],
                    [{"text": "📢 Рассылка", "callback_data": "admin_broadcast"}],
                    [{"text": "🔙 Назад в магазин", "callback_data": "back_to_shop"}]
                ]
            }
            
            blocked_count = len(self.blocked_users)
            users_count = len(self.all_users)
            
            message_text = (
                "👑 <b>АДМИН ПАНЕЛЬ</b>\n\n"
                f"📊 Всего пользователей: <b>{users_count}</b>\n"
                f"🚫 Заблокировано: <b>{blocked_count}</b>\n\n"
                "Выбери действие:"
            )
            
            await self.send_message(chat_id, message_text, parse_mode="HTML", reply_markup=keyboard)
            return True
                    
        except Exception as e:
            logger.error(f"Ошибка отправки админ панели: {e}")
            return False
    
    async def send_invoice(self, chat_id: int):
        """Отправка инвойса для оплаты"""
        try:
            if chat_id not in self.user_states:
                return False
            
            state = self.user_states[chat_id]
            gift_key = state.get("gift_key")
            recipient = state.get("recipient_username", "self")
            message_text = state.get("message")
            
            gift = self.gifts[gift_key]
            
            logger.info(f"💳 Отправка инвойса на {gift['price']}⭐️")
            
            unique_payload = f"{gift_key}_{chat_id}_{recipient}_{int(time.time()*1000)}"
            state["payload"] = unique_payload
            state["invoice_sent_at"] = time.time()
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sendInvoice"
                payload = {
                    "chat_id": chat_id,
                    "title": f"{gift['emoji']} {gift['name']}",
                    "description": f"Оплатите {gift['price']}⭐️ для отправки подарка! Для отмены /cancel",
                    "payload": unique_payload,
                    "currency": "XTR",
                    "prices": [
                        {
                            "label": gift['name'],
                            "amount": gift['price']
                        }
                    ]
                }
                
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if result.get("ok"):
                        logger.info(f"✅ Инвойс отправлен")
                        await self.update_order_message(chat_id, "payment_sent")
                        return True
                    else:
                        error_description = result.get("description", "")
                        logger.error(f"❌ Ошибка инвойса: {error_description}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке инвойса: {e}")
            return False
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = None, reply_markup: dict = None):
        """Отправка сообщения"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": text
                }
                
                if parse_mode:
                    payload["parse_mode"] = parse_mode
                
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if result.get("ok"):
                        return result["result"]["message_id"]
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return None
    
    async def answer_callback_query(self, callback_query_id: str, text: str = "", show_alert: bool = False):
        """Ответ на callback query"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/answerCallbackQuery"
                payload = {
                    "callback_query_id": callback_query_id,
                    "text": text,
                    "show_alert": show_alert
                }
                
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    return result.get("ok", False)
                    
        except Exception as e:
            logger.error(f"Ошибка ответа на callback: {e}")
            return False
    
    async def delete_message(self, chat_id: int, message_id: int):
        """Удаление сообщения"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/deleteMessage"
                payload = {
                    "chat_id": chat_id,
                    "message_id": message_id
                }
                
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    return result.get("ok", False)
                    
        except Exception as e:
            logger.error(f"Ошибка удаления сообщения: {e}")
            return False
    
    async def get_updates(self, offset=0):
        """Получение обновлений от Telegram"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/getUpdates"
                params = {"timeout": 30}
                
                if offset > 0:
                    params["offset"] = offset
                
                async with session.get(url, params=params) as response:
                    result = await response.json()
                    if result.get("ok"):
                        return result.get("result", [])
                    return []
                    
        except Exception as e:
            logger.error(f"Ошибка получения обновлений: {e}")
            return []
    
    async def process_update(self, update):
        """Обработка обновления"""
        try:
            # Обработка текстовых сообщений
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
                
                # /start
                if text == "/start":
                    if chat_id in self.user_states and self.user_states[chat_id].get("invoice_sent_at"):
                        await self.send_message(chat_id, "⚠️ У тебя активный заказ! /cancel для отмены")
                        return
                    
                    # Проверка ожидающих подарков
                    pending = [k for k, v in self.pending_gifts.items() 
                              if v.get("recipient_username", "").lower() == username.lower()]
                    
                    if pending:
                        for payload_key in pending:
                            gift_data = self.pending_gifts[payload_key]
                            gift_key = gift_data["gift_key"]
                            sender_id = gift_data["sender_id"]
                            message_text = gift_data.get("message")
                            
                            gift = self.gifts[gift_key]
                            
                            success = await self.send_gift(chat_id, gift["gift_id"], message_text)
                            
                            if success:
                                sender_info = self.all_users.get(sender_id, {})
                                sender_name = sender_info.get("first_name", "Кто-то")
                                sender_username = sender_info.get("username", "")
                                
                                from_text = f"от <b>{sender_name}</b> ({sender_username})" if sender_username != "нет username" else f"от <b>{sender_name}</b>"
                                notification = f"🎉 Ты получил {gift['emoji']} <b>{gift['name']}</b> {from_text}!"
                                
                                if message_text:
                                    notification += f"\n\n💌 <i>{message_text}</i>"
                                
                                await self.send_message(chat_id, notification, parse_mode="HTML")
                                
                                await self.send_message(
                                    sender_id,
                                    f"✅ Твой подарок {gift['emoji']} доставлен @{username}!",
                                    parse_mode="HTML"
                                )
                            
                            del self.pending_gifts[payload_key]
                    
                    await self.send_gift_menu(chat_id)
                
                # /cancel
                elif text == "/cancel":
                    if chat_id in self.user_states:
                        await self.cancel_order(chat_id)
                    else:
                        await self.send_message(chat_id, "❌ Нет активного заказа.")
                
                # Обработка состояний
                elif chat_id in self.user_states:
                    state = self.user_states[chat_id]
                    
                    # Ввод username
                    if state.get("waiting_for") == "recipient_username":
                        valid, result = self.validate_username(text)
                        
                        if not valid:
                            error_msg_id = await self.send_message(chat_id, result)
                            await self.delete_message(chat_id, message_id)
                            
                            if error_msg_id:
                                await asyncio.sleep(3)
                                await self.delete_message(chat_id, error_msg_id)
                            return
                        
                        recipient_username = result
                        
                        if recipient_username.lower() == username.lower():
                            error_msg_id = await self.send_message(
                                chat_id,
                                "❌ Нельзя отправить самому себе!\nВыбери 'Для себя'."
                            )
                            
                            await self.delete_message(chat_id, message_id)
                            
                            if error_msg_id:
                                await asyncio.sleep(3)
                                await self.delete_message(chat_id, error_msg_id)
                            return
                        
                        # Проверяем в базе
                        found, user_id, first_name = self.check_username_in_database(recipient_username)
                        
                        # Удаляем временные сообщения
                        if chat_id in self.temp_messages:
                            for msg_id in self.temp_messages[chat_id]:
                                await self.delete_message(chat_id, msg_id)
                            del self.temp_messages[chat_id]
                        
                        await self.delete_message(chat_id, message_id)
                        
                        if found:
                            # Найден - сохраняем и идем дальше
                            state["recipient_username"] = recipient_username
                            state["recipient_user_id"] = user_id
                            state["recipient_known"] = True
                            state["waiting_for"] = None
                            
                            await self.update_order_message(chat_id, "message_choice")
                        else:
                            # Не найден - показываем предупреждение
                            state["pending_recipient_username"] = recipient_username
                            state["waiting_for"] = None
                            
                            await self.update_order_message(chat_id, "username_not_found")
                    
                    # Ввод подписи
                    elif state.get("waiting_for") == "gift_message":
                        message_text = text.strip()
                        
                        if len(message_text) > 200:
                            error_msg_id = await self.send_message(
                                chat_id,
                                "❌ Подпись слишком длинная! Максимум 200 символов."
                            )
                            
                            await self.delete_message(chat_id, message_id)
                            
                            if error_msg_id:
                                await asyncio.sleep(3)
                                await self.delete_message(chat_id, error_msg_id)
                            return
                        
                        state["message"] = message_text
                        state["waiting_for"] = None
                        
                        if chat_id in self.temp_messages:
                            for msg_id in self.temp_messages[chat_id]:
                                await self.delete_message(chat_id, msg_id)
                            del self.temp_messages[chat_id]
                        
                        await self.delete_message(chat_id, message_id)
                        await self.update_order_message(chat_id, "ready")
                    
                    # Админ команды
                    elif state.get("waiting_for") == "block_username":
                        username_to_block = text.strip().lstrip("@").lower()
                        self.blocked_users.add(username_to_block)
                        state["waiting_for"] = None
                        await self.send_message(chat_id, f"✅ @{username_to_block} заблокирован!")
                    
                    elif state.get("waiting_for") == "unblock_username":
                        username_to_unblock = text.strip().lstrip("@").lower()
                        if username_to_unblock in self.blocked_users:
                            self.blocked_users.remove(username_to_unblock)
                            await self.send_message(chat_id, f"✅ @{username_to_unblock} разблокирован!")
                        else:
                            await self.send_message(chat_id, f"❌ @{username_to_unblock} не был заблокирован.")
                        state["waiting_for"] = None
                    
                    elif state.get("waiting_for") == "broadcast_text":
                        broadcast_text = text.strip()
                        
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "✅ Отправить", "callback_data": "confirm_broadcast"}],
                                [{"text": "❌ Отмена", "callback_data": "cancel_broadcast"}]
                            ]
                        }
                        
                        state["broadcast_text"] = broadcast_text
                        state["waiting_for"] = None
                        
                        preview = f"📢 <b>Предпросмотр:</b>\n\n{broadcast_text}\n\nОтправить <b>{len(self.all_users)}</b> пользователям?"
                        
                        await self.send_message(chat_id, preview, parse_mode="HTML", reply_markup=keyboard)
            
            # Обработка callback
            if "callback_query" in update:
                callback = update["callback_query"]
                callback_query_id = callback["id"]
                chat_id = callback["message"]["chat"]["id"]
                callback_data = callback["data"]
                user = callback.get("from", {})
                username = user.get("username", "")
                
                if self.is_blocked(username) and not callback_data.startswith("admin_"):
                    await self.answer_callback_query(callback_query_id, "🚫 Заблокирован!", show_alert=True)
                    return
                
                # Подтверждение неизвестного username
                if callback_data == "confirm_unknown":
                    if chat_id in self.user_states:
                        state = self.user_states[chat_id]
                        recipient_username = state.get("pending_recipient_username")
                        
                        if recipient_username:
                            state["recipient_username"] = recipient_username
                            state["recipient_user_id"] = None
                            state["recipient_known"] = False
                            
                            await self.update_order_message(chat_id, "message_choice")
                            await self.answer_callback_query(callback_query_id)
                
                elif callback_data == "reenter_username":
                    if chat_id in self.user_states:
                        state = self.user_states[chat_id]
                        state["waiting_for"] = "recipient_username"
                        state["pending_recipient_username"] = None
                        
                        await self.update_order_message(chat_id, "waiting_username")
                        
                        prompt_msg_id = await self.send_message(chat_id, "👤 Введи username получателя:")
                        
                        if prompt_msg_id:
                            self.temp_messages[chat_id] = [prompt_msg_id]
                        
                        await self.answer_callback_query(callback_query_id)
                
                # Отмена
                elif callback_data == "cancel_order":
                    await self.cancel_order(chat_id)
                    await self.answer_callback_query(callback_query_id)
                    return
                
                # Админ панель
                elif callback_data == "admin_panel":
                    if chat_id == self.admin_id:
                        await self.send_admin_panel(chat_id)
                        await self.answer_callback_query(callback_query_id)
                    else:
                        await self.answer_callback_query(callback_query_id, "⛔️ Нет доступа!", show_alert=True)
                
                elif callback_data == "back_to_shop":
                    await self.send_gift_menu(chat_id)
                    await self.answer_callback_query(callback_query_id)
                
                elif callback_data == "admin_block":
                    if chat_id == self.admin_id:
                        self.user_states[chat_id] = {"waiting_for": "block_username"}
                        await self.send_message(chat_id, "🚫 Введи username:")
                        await self.answer_callback_query(callback_query_id)
                
                elif callback_data == "admin_unblock":
                    if chat_id == self.admin_id:
                        self.user_states[chat_id] = {"waiting_for": "unblock_username"}
                        await self.send_message(chat_id, "✅ Введи username:")
                        await self.answer_callback_query(callback_query_id)
                
                elif callback_data == "admin_users":
                    if chat_id == self.admin_id:
                        sorted_users = sorted(self.all_users.items(), key=lambda x: x[1]["last_seen"], reverse=True)
                        
                        users_text = "👥 <b>Последние 10:</b>\n\n"
                        
                        for i, (uid, udata) in enumerate(sorted_users[:10], 1):
                            uname = udata["username"]
                            fname = udata["first_name"]
                            lseen = time.strftime("%d.%m %H:%M", time.localtime(udata["last_seen"]))
                            
                            users_text += f"{i}. <b>{fname}</b> ({uname})\n   <code>{uid}</code> - {lseen}\n\n"
                        
                        await self.send_message(chat_id, users_text, parse_mode="HTML")
                        await self.answer_callback_query(callback_query_id)
                
                elif callback_data == "admin_broadcast":
                    if chat_id == self.admin_id:
                        self.user_states[chat_id] = {"waiting_for": "broadcast_text"}
                        await self.send_message(chat_id, "📢 Введи текст:")
                        await self.answer_callback_query(callback_query_id)
                
                elif callback_data == "confirm_broadcast":
                    if chat_id == self.admin_id and chat_id in self.user_states:
                        broadcast_text = self.user_states[chat_id].get("broadcast_text")
                        
                        if broadcast_text:
                            sent = 0
                            for uid in self.all_users:
                                msg_id = await self.send_message(uid, broadcast_text, parse_mode="HTML")
                                if msg_id:
                                    sent += 1
                                await asyncio.sleep(0.05)
                            
                            await self.send_message(chat_id, f"✅ Отправлено: {sent}")
                        
                        del self.user_states[chat_id]
                        await self.answer_callback_query(callback_query_id)
                
                elif callback_data == "cancel_broadcast":
                    if chat_id in self.user_states:
                        del self.user_states[chat_id]
                    await self.send_message(chat_id, "❌ Отменено.")
                    await self.answer_callback_query(callback_query_id)
                
                # Выбор подарка
                elif callback_data in self.gifts:
                    if chat_id in self.user_states and self.user_states[chat_id].get("invoice_sent_at"):
                        await self.answer_callback_query(callback_query_id, "⚠️ Активный заказ! /cancel", show_alert=True)
                        return
                    
                    self.user_states[chat_id] = {"gift_key": callback_data}
                    await self.update_order_message(chat_id, "recipient")
                    await self.answer_callback_query(callback_query_id)
                
                # Получатель
                elif callback_data.startswith("recipient_self_"):
                    gift_key = callback_data.replace("recipient_self_", "")
                    
                    if chat_id not in self.user_states:
                        self.user_states[chat_id] = {}
                    
                    self.user_states[chat_id]["gift_key"] = gift_key
                    self.user_states[chat_id]["recipient"] = "self"
                    self.user_states[chat_id]["recipient_username"] = "self"
                    
                    await self.update_order_message(chat_id, "message_choice")
                    await self.answer_callback_query(callback_query_id)
                
                elif callback_data.startswith("recipient_other_"):
                    gift_key = callback_data.replace("recipient_other_", "")
                    
                    if chat_id not in self.user_states:
                        self.user_states[chat_id] = {}
                    
                    self.user_states[chat_id]["gift_key"] = gift_key
                    self.user_states[chat_id]["recipient"] = "other"
                    self.user_states[chat_id]["waiting_for"] = "recipient_username"
                    
                    await self.update_order_message(chat_id, "waiting_username")
                    
                    prompt_msg_id = await self.send_message(chat_id, "👤 Введи username получателя:")
                    
                    if prompt_msg_id:
                        self.temp_messages[chat_id] = [prompt_msg_id]
                    
                    await self.answer_callback_query(callback_query_id)
                
                # Подпись
                elif callback_data == "msg_with":
                    if chat_id in self.user_states:
                        self.user_states[chat_id]["has_message"] = "with"
                        self.user_states[chat_id]["waiting_for"] = "gift_message"
                        
                        await self.update_order_message(chat_id, "waiting_message")
                        
                        prompt_msg_id = await self.send_message(chat_id, "📝 Введи подпись (макс 200 символов):")
                        
                        if prompt_msg_id:
                            self.temp_messages[chat_id] = [prompt_msg_id]
                        
                        await self.answer_callback_query(callback_query_id)
                
                elif callback_data == "msg_without":
                    if chat_id in self.user_states:
                        self.user_states[chat_id]["has_message"] = "without"
                        self.user_states[chat_id]["message"] = None
                        
                        await self.update_order_message(chat_id, "ready")
                        await self.answer_callback_query(callback_query_id)
                
                # Оплата
                elif callback_data == "proceed_payment":
                    if chat_id in self.user_states:
                        disclaimer = (
                            "⚠️ <b>ВАЖНО:</b>\n\n"
                            "• Подарок будет отправлен после оплаты\n"
                            "• Подарки <b>нельзя продать</b>\n"
                            "• Проверь все данные!\n\n"
                            "Счет отправлен ниже 👇"
                        )
                        await self.send_message(chat_id, disclaimer, parse_mode="HTML")
                        await asyncio.sleep(1)
                        
                        await self.send_invoice(chat_id)
                        await self.answer_callback_query(callback_query_id)
            
            # Pre-checkout
            if "pre_checkout_query" in update:
                pre_checkout = update["pre_checkout_query"]
                pre_checkout_id = pre_checkout["id"]
                
                async with aiohttp.ClientSession() as session:
                    url = f"{self.base_url}/answerPreCheckoutQuery"
                    payload = {"pre_checkout_query_id": pre_checkout_id, "ok": True}
                    await session.post(url, json=payload)
            
            # Оплата
            if "message" in update and "successful_payment" in update["message"]:
                message = update["message"]
                chat_id = message["chat"]["id"]
                payment = message["successful_payment"]
                payment_id = payment.get("telegram_payment_charge_id")
                
                logger.info(f"💰 ОПЛАТА: {payment_id}")
                
                if payment_id in self.processed_payments:
                    return
                
                self.processed_payments.add(payment_id)
                
                if chat_id not in self.user_states:
                    return
                
                state = self.user_states[chat_id]
                gift_key = state.get("gift_key")
                recipient = state.get("recipient_username", "self")
                message_text = state.get("message")
                
                if not gift_key or gift_key not in self.gifts:
                    return
                
                gift = self.gifts[gift_key]
                
                # Для себя
                if recipient == "self":
                    await self.send_message(chat_id, f"⏳ Отправляю {gift['emoji']}...")
                    
                    await asyncio.sleep(1)
                    success = await self.send_gift(chat_id, gift['gift_id'], message_text)
                    
                    if success:
                        await self.send_message(
                            chat_id,
                            f"🎉 Ты получил {gift['emoji']} <b>{gift['name']}</b>!\n\n/start",
                            parse_mode="HTML"
                        )
                    else:
                        await self.send_message(chat_id, "❌ Ошибка. Обратись в поддержку.")
                
                # Для другого
                else:
                    recipient_id = state.get("recipient_user_id")
                    
                    if recipient_id:
                        # Отправляем сразу
                        success = await self.send_gift(recipient_id, gift['gift_id'], message_text)
                        
                        if success:
                            sender_info = self.all_users.get(chat_id, {})
                            sender_name = sender_info.get("first_name", "Кто-то")
                            notif = f"🎉 Ты получил {gift['emoji']} <b>{gift['name']}</b> от <b>{sender_name}</b>!"
                            
                            if message_text:
                                notif += f"\n\n💌 <i>{message_text}</i>"
                            
                            await self.send_message(recipient_id, notif, parse_mode="HTML")
                            await self.send_message(chat_id, f"✅ Подарок доставлен @{recipient}!")
                        else:
                            await self.send_message(chat_id, "❌ Ошибка.")
                    else:
                        # Сохраняем для отправки позже
                        payload_key = state.get("payload")
                        self.pending_gifts[payload_key] = {
                            "gift_key": gift_key,
                            "sender_id": chat_id,
                            "recipient_username": recipient,
                            "message": message_text
                        }
                        
                        await self.send_message(
                            chat_id,
                            f"✅ Оплачено! Подарок будет доставлен когда @{recipient} напишет /start",
                            parse_mode="HTML"
                        )
                
                # Очистка
                if chat_id in self.user_states:
                    del self.user_states[chat_id]
                if chat_id in self.order_messages:
                    del self.order_messages[chat_id]
                if chat_id in self.temp_messages:
                    del self.temp_messages[chat_id]
                    
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def run(self):
        """Основной цикл"""
        logger.info("🚀 БОТ ЗАПУЩЕН")
        
        bot_username = await self.get_bot_username()
        print("\n" + "="*50)
        print("✅ БОТ РАБОТАЕТ!")
        print(f"👉 https://t.me/{bot_username}")
        print(f"👑 Админ: {self.admin_id}")
        print("="*50 + "\n")
        
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
                logger.error(f"❌ Ошибка ({error_count}): {e}")
                
                if error_count > 10:
                    print("\n🔴 КРИТИЧЕСКАЯ ОШИБКА")
                    break
                
                await asyncio.sleep(2)
    
    async def get_bot_username(self):
        """Получение username"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/getMe"
                async with session.get(url) as response:
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

