import asyncio
import aiohttp
import logging
import time

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8442227835:AAEm4UYtkDX8TrTpilX5iDJhxnMegkVdmzM"
ADMIN_ID = 5479063264
ANONYMOUS_PRICE = 5

GIFTS = {
    "gift_1": {"name": "🎄 Елка новогодняя", "emoji": "🎄", "price": 60, "gift_id": "5922558454332916696"},
    "gift_2": {"name": "🧸 Новогодний мишка", "emoji": "🧸", "price": 65, "gift_id": "5956217000635139069"},
    "gift_3": {"name": "💝 Февральское сердце", "emoji": "💝", "price": 65, "gift_id": "5801108895304779062"},
    "gift_4": {"name": "🧸 Февральский мишка", "emoji": "🧸", "price": 50, "gift_id": "5800655655995968830"}
}

class Bot:
    def __init__(self):
        self.url = f"https://api.telegram.org/bot{BOT_TOKEN}"
        self.users = {}
        self.states = {}
        self.orders = {}
        self.pending = {}
        self.blocked = set()
        self.payments = set()
        self.temps = {}
    
    async def api(self, method, **kw):
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{self.url}/{method}", json=kw) as r:
                return await r.json()
    
    def calc_price(self, gk, anon):
        """ПРАВИЛЬНЫЙ расчет цены"""
        return GIFTS[gk]["price"] + (ANONYMOUS_PRICE if anon else 0)
    
    async def run(self):
        logger.info("🚀 Запуск")
        me = await self.api("getMe")
        print(f"\n✅ @{me['result']['username']}\n👑 Админ: {ADMIN_ID}\n🎭 Анонимность: +{ANONYMOUS_PRICE}⭐️\n")
        
        o = 0
        while True:
            try:
                r = await self.api("getUpdates", timeout=30, offset=o)
                for u in r.get("result", []):
                    o = u["update_id"] + 1
                    await self.h(u)
                await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await asyncio.sleep(2)
    
    async def h(self, u):
        try:
            # MESSAGE
            if "message" in u:
                m = u["message"]
                c = m["chat"]["id"]
                t = m.get("text", "")
                user = m["from"]
                un = user.get("username", "")
                
                # Регистрация
                if c not in self.users:
                    self.users[c] = {"un": f"@{un}" if un else "нет", "name": user.get("first_name", "Юзер"), "t": time.time()}
                    logger.info(f"Новый: {c} @{un}")
                else:
                    self.users[c]["t"] = time.time()
                
                # Блок
                if un.lower() in self.blocked:
                    await self.api("sendMessage", chat_id=c, text="🚫 Заблокирован")
                    return
                
                # /start
                if t == "/start":
                    # Проверка активного заказа
                    if c in self.states and self.states[c].get("inv"):
                        await self.api("sendMessage", chat_id=c, text="⚠️ Активный заказ! /cancel")
                        return
                    
                    # Доставка ожидающих подарков
                    for k in list(self.pending.keys()):
                        p = self.pending[k]
                        if p["un"].lower() == un.lower():
                            g = GIFTS[p["gk"]]
                            ok = await self.api("sendGift", user_id=c, gift_id=g["gift_id"], text=p.get("msg"), pay_for_upgrade=p.get("anon", False))
                            if ok.get("ok"):
                                txt = f"🎉 {g['emoji']} <b>{g['name']}</b>"
                                if p.get("anon"):
                                    txt += " 🎭 анонимно!"
                                else:
                                    s = self.users.get(p["sid"], {})
                                    txt += f" от <b>{s.get('name', 'Кто-то')}</b>!"
                                if p.get("msg"):
                                    txt += f"\n\n💌 {p['msg']}"
                                await self.api("sendMessage", chat_id=c, text=txt, parse_mode="HTML")
                                await self.api("sendMessage", chat_id=p["sid"], text=f"✅ Доставлено @{un}!")
                            del self.pending[k]
                    
                    # Меню
                    kb = {"inline_keyboard": [[{"text": f"{g['emoji']} {g['name']} - {g['price']}⭐️", "callback_data": k}] for k, g in GIFTS.items()]}
                    if c == ADMIN_ID:
                        kb["inline_keyboard"].append([{"text": "👑 Админ", "callback_data": "adm"}])
                    await self.api("sendMessage", chat_id=c, text="🎁 <b>Магазин подарков</b>\n\nВыбери:", parse_mode="HTML", reply_markup=kb)
                
                # /cancel
                elif t == "/cancel":
                    if c in self.states:
                        if c in self.orders:
                            await self.api("deleteMessage", chat_id=c, message_id=self.orders[c])
                            del self.orders[c]
                        if c in self.temps:
                            for mid in self.temps[c]:
                                await self.api("deleteMessage", chat_id=c, message_id=mid)
                            del self.temps[c]
                        del self.states[c]
                        await self.api("sendMessage", chat_id=c, text="❌ Отменено\n\n/start")
                    else:
                        await self.api("sendMessage", chat_id=c, text="❌ Нет заказа")
                
                # Обработка ввода
                elif c in self.states:
                    s = self.states[c]
                    
                    # Ввод username
                    if s.get("w") == "un":
                        un_input = t.strip().lstrip("@")
                        if len(un_input) < 5:
                            await self.api("sendMessage", chat_id=c, text="❌ Минимум 5 символов!")
                            return
                        
                        if un_input.lower() == un.lower():
                            await self.api("sendMessage", chat_id=c, text="❌ Нельзя себе!")
                            return
                        
                        # Поиск в базе
                        found = None
                        for uid, ud in self.users.items():
                            if ud["un"].lstrip("@").lower() == un_input.lower():
                                found = uid
                                break
                        
                        # Удаляем сообщения
                        if c in self.temps:
                            for mid in self.temps[c]:
                                await self.api("deleteMessage", chat_id=c, message_id=mid)
                            del self.temps[c]
                        await self.api("deleteMessage", chat_id=c, message_id=m["message_id"])
                        
                        if found:
                            s["un"] = un_input
                            s["uid"] = found
                            s["w"] = None
                            await self.upd(c, "anon")
                        else:
                            s["pun"] = un_input
                            s["w"] = None
                            await self.upd(c, "nf")
                    
                    # Ввод подписи
                    elif s.get("w") == "msg":
                        if len(t.strip()) > 200:
                            await self.api("sendMessage", chat_id=c, text="❌ Макс 200!")
                            return
                        s["msg"] = t.strip()
                        s["w"] = None
                        if c in self.temps:
                            for mid in self.temps[c]:
                                await self.api("deleteMessage", chat_id=c, message_id=mid)
                            del self.temps[c]
                        await self.api("deleteMessage", chat_id=c, message_id=m["message_id"])
                        await self.upd(c, "ok")
                    
                    # Админ: блок
                    elif s.get("w") == "bl":
                        self.blocked.add(t.strip().lstrip("@").lower())
                        s["w"] = None
                        await self.api("sendMessage", chat_id=c, text=f"✅ Заблокирован!")
                    
                    # Админ: разблок
                    elif s.get("w") == "ubl":
                        uname = t.strip().lstrip("@").lower()
                        if uname in self.blocked:
                            self.blocked.remove(uname)
                            await self.api("sendMessage", chat_id=c, text="✅ Разблокирован!")
                        else:
                            await self.api("sendMessage", chat_id=c, text="❌ Не был заблокирован")
                        s["w"] = None
                    
                    # Админ: рассылка
                    elif s.get("w") == "br":
                        kb = {"inline_keyboard": [[{"text": "✅ Да", "callback_data": "cbr"}], [{"text": "❌ Нет", "callback_data": "cbrc"}]]}
                        s["brt"] = t.strip()
                        s["w"] = None
                        await self.api("sendMessage", chat_id=c, text=f"📢 Отправить {len(self.users)} юзерам?", reply_markup=kb)
            
            # CALLBACK
            if "callback_query" in u:
                q = u["callback_query"]
                c = q["message"]["chat"]["id"]
                d = q["data"]
                user = q["from"]
                un = user.get("username", "")
                
                # Регистрация при callback
                if c not in self.users:
                    self.users[c] = {"un": f"@{un}" if un else "нет", "name": user.get("first_name", "Юзер"), "t": time.time()}
                    logger.info(f"Новый (callback): {c} @{un}")
                else:
                    self.users[c]["t"] = time.time()
                
                # ВСЕГДА отвечаем на callback
                await self.api("answerCallbackQuery", callback_query_id=q["id"])
                
                # Блок
                if un.lower() in self.blocked and not d.startswith("adm"):
                    return
                
                # Обработка callback
                if d == "cunk":
                    if c in self.states:
                        s = self.states[c]
                        s["un"] = s.get("pun")
                        s["uid"] = None
                        await self.upd(c, "anon")
                
                elif d == "reun":
                    if c in self.states:
                        self.states[c]["w"] = "un"
                        self.states[c]["pun"] = None
                        await self.upd(c, "wun")
                        r = await self.api("sendMessage", chat_id=c, text="👤 Введи username:")
                        if r.get("ok"):
                            self.temps[c] = [r["result"]["message_id"]]
                
                elif d == "can":
                    if c in self.states:
                        if c in self.orders:
                            await self.api("deleteMessage", chat_id=c, message_id=self.orders[c])
                            del self.orders[c]
                        if c in self.temps:
                            for mid in self.temps[c]:
                                await self.api("deleteMessage", chat_id=c, message_id=mid)
                            del self.temps[c]
                        del self.states[c]
                        await self.api("sendMessage", chat_id=c, text="❌ Отменено\n\n/start")
                
                elif d == "adm":
                    if c == ADMIN_ID:
                        kb = {"inline_keyboard": [[{"text": "🚫 Блок", "callback_data": "abl"}], [{"text": "✅ Разблок", "callback_data": "aubl"}], [{"text": "👥 Юзеры", "callback_data": "au"}], [{"text": "📢 Рассылка", "callback_data": "abr"}], [{"text": "🔙 Назад", "callback_data": "back"}]]}
                        await self.api("sendMessage", chat_id=c, text=f"👑 <b>АДМИН</b>\n\n📊 Юзеров: {len(self.users)}\n🚫 Заблок: {len(self.blocked)}", parse_mode="HTML", reply_markup=kb)
                
                elif d == "back":
                    kb = {"inline_keyboard": [[{"text": f"{g['emoji']} {g['name']} - {g['price']}⭐️", "callback_data": k}] for k, g in GIFTS.items()]}
                    if c == ADMIN_ID:
                        kb["inline_keyboard"].append([{"text": "👑 Админ", "callback_data": "adm"}])
                    await self.api("sendMessage", chat_id=c, text="🎁 <b>Магазин</b>\n\nВыбери:", parse_mode="HTML", reply_markup=kb)
                
                elif d == "abl":
                    if c == ADMIN_ID:
                        self.states[c] = {"w": "bl"}
                        await self.api("sendMessage", chat_id=c, text="🚫 Username:")
                
                elif d == "aubl":
                    if c == ADMIN_ID:
                        self.states[c] = {"w": "ubl"}
                        await self.api("sendMessage", chat_id=c, text="✅ Username:")
                
                elif d == "au":
                    if c == ADMIN_ID:
                        us = sorted(self.users.items(), key=lambda x: x[1]["t"], reverse=True)[:10]
                        txt = "👥 <b>Последние 10:</b>\n\n"
                        for i, (uid, ud) in enumerate(us, 1):
                            txt += f"{i}. <b>{ud['name']}</b> {ud['un']}\n<code>{uid}</code>\n\n"
                        await self.api("sendMessage", chat_id=c, text=txt, parse_mode="HTML")
                
                elif d == "abr":
                    if c == ADMIN_ID:
                        self.states[c] = {"w": "br"}
                        await self.api("sendMessage", chat_id=c, text="📢 Текст:")
                
                elif d == "cbr":
                    if c == ADMIN_ID and c in self.states:
                        txt = self.states[c].get("brt")
                        if txt:
                            sent = 0
                            for uid in self.users:
                                if (await self.api("sendMessage", chat_id=uid, text=txt, parse_mode="HTML")).get("ok"):
                                    sent += 1
                                await asyncio.sleep(0.05)
                            await self.api("sendMessage", chat_id=c, text=f"✅ Отправлено: {sent}")
                        del self.states[c]
                
                elif d == "cbrc":
                    if c in self.states:
                        del self.states[c]
                    await self.api("sendMessage", chat_id=c, text="❌ Отменено")
                
                # Выбор подарка
                elif d in GIFTS:
                    if c in self.states and self.states[c].get("inv"):
                        return
                    self.states[c] = {"gk": d}
                    await self.upd(c, "rec")
                
                # Для себя
                elif d.startswith("rs_"):
                    gk = d[3:]
                    self.states[c] = {"gk": gk, "rec": "self", "un": "self"}
                    await self.upd(c, "anon")
                
                # Для другого
                elif d.startswith("ro_"):
                    gk = d[3:]
                    self.states[c] = {"gk": gk, "rec": "other", "w": "un"}
                    await self.upd(c, "wun")
                    r = await self.api("sendMessage", chat_id=c, text="👤 Введи username:")
                    if r.get("ok"):
                        self.temps[c] = [r["result"]["message_id"]]
                
                # Анонимность: да
                elif d == "ay":
                    if c in self.states:
                        self.states[c]["anon"] = True
                        self.states[c]["acs"] = True
                        await self.upd(c, "msgc")
                
                # Анонимность: нет
                elif d == "an":
                    if c in self.states:
                        self.states[c]["anon"] = False
                        self.states[c]["acs"] = True
                        await self.upd(c, "msgc")
                
                # Подпись: да
                elif d == "mw":
                    if c in self.states:
                        self.states[c]["hm"] = "y"
                        self.states[c]["w"] = "msg"
                        await self.upd(c, "wmsg")
                        r = await self.api("sendMessage", chat_id=c, text="📝 Подпись (макс 200):")
                        if r.get("ok"):
                            self.temps[c] = [r["result"]["message_id"]]
                
                # Подпись: нет
                elif d == "mn":
                    if c in self.states:
                        self.states[c]["hm"] = "n"
                        self.states[c]["msg"] = None
                        await self.upd(c, "ok")
                
                # Оплатить
                elif d == "pay":
                    if c in self.states:
                        await self.api("sendMessage", chat_id=c, text="⚠️ <b>ВАЖНО:</b>\n• Подарки нельзя продать\n• Проверь данные!", parse_mode="HTML")
                        await asyncio.sleep(1)
                        await self.inv(c)
            
            # PRE-CHECKOUT
            if "pre_checkout_query" in u:
                await self.api("answerPreCheckoutQuery", pre_checkout_query_id=u["pre_checkout_query"]["id"], ok=True)
            
            # PAYMENT
            if "message" in u and "successful_payment" in u["message"]:
                m = u["message"]
                c = m["chat"]["id"]
                pid = m["successful_payment"]["telegram_payment_charge_id"]
                
                if pid in self.payments:
                    return
                self.payments.add(pid)
                
                if c not in self.states:
                    return
                
                s = self.states[c]
                g = GIFTS[s["gk"]]
                un = s.get("un", "self")
                msg = s.get("msg")
                anon = s.get("anon", False)
                
                # Для себя
                if un == "self":
                    await self.api("sendMessage", chat_id=c, text=f"⏳ Отправляю {g['emoji']}...")
                    await asyncio.sleep(1)
                    r = await self.api("sendGift", user_id=c, gift_id=g["gift_id"], text=msg, pay_for_upgrade=anon)
                    if r.get("ok"):
                        await self.api("sendMessage", chat_id=c, text=f"🎉 {g['emoji']} <b>{g['name']}</b>!\n\n/start", parse_mode="HTML")
                    else:
                        await self.api("sendMessage", chat_id=c, text="❌ Ошибка")
                
                # Для другого
                else:
                    uid = s.get("uid")
                    if uid:
                        r = await self.api("sendGift", user_id=uid, gift_id=g["gift_id"], text=msg, pay_for_upgrade=anon)
                        if r.get("ok"):
                            txt = f"🎉 {g['emoji']} <b>{g['name']}</b>"
                            if anon:
                                txt += " 🎭 анонимно!"
                            else:
                                snd = self.users.get(c, {})
                                txt += f" от <b>{snd.get('name', 'Кто-то')}</b>!"
                            if msg:
                                txt += f"\n\n💌 {msg}"
                            await self.api("sendMessage", chat_id=uid, text=txt, parse_mode="HTML")
                            await self.api("sendMessage", chat_id=c, text=f"✅ Доставлено @{un}!")
                        else:
                            await self.api("sendMessage", chat_id=c, text="❌ Ошибка")
                    else:
                        self.pending[s.get("pl")] = {"gk": s["gk"], "sid": c, "un": un, "msg": msg, "anon": anon}
                        await self.api("sendMessage", chat_id=c, text=f"✅ Оплачено! Доставится когда @{un} напишет /start")
                
                # Очистка
                if c in self.states:
                    del self.states[c]
                if c in self.orders:
                    del self.orders[c]
                if c in self.temps:
                    del self.temps[c]
        
        except Exception as e:
            logger.error(f"handle: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def upd(self, c, step):
        """Обновление сообщения заказа"""
        s = self.states[c]
        g = GIFTS[s["gk"]]
        
        # ПРАВИЛЬНЫЙ расчет цены
        anon = s.get("anon", False)
        bp = g["price"]
        tp = self.calc_price(s["gk"], anon)
        
        txt = f"✨ <b>{g['name']}</b>\n💰 Цена: <b>{bp}⭐️</b>\n"
        if anon:
            txt += f"🎭 Анонимность: <b>+{ANONYMOUS_PRICE}⭐️</b>\n"
        txt += f"💵 <b>ИТОГО: {tp}⭐️</b>\n\n"
        
        # Получатель
        if s.get("rec") == "self":
            txt += "👤 <b>Для себя</b>\n"
        elif s.get("rec") == "other":
            if s.get("un"):
                txt += f"👤 <b>@{s['un']}</b>\n"
            else:
                txt += "👤 ⏳\n"
        else:
            txt += "👤 <i>не выбрано</i>\n"
        
        # Анонимность
        if s.get("acs"):
            txt += f"🎭 <b>{'Анонимно' if anon else 'С именем'}</b>\n"
        else:
            txt += "🎭 <i>не выбрано</i>\n"
        
        # Подпись
        if s.get("hm") == "y":
            if s.get("msg"):
                txt += f"💌 {s['msg']}\n"
            else:
                txt += "💌 ⏳\n"
        elif s.get("hm") == "n":
            txt += "💌 <b>Нет</b>\n"
        else:
            txt += "💌 <i>не выбрано</i>\n"
        
        kb = {"inline_keyboard": []}
        
        if step == "rec":
            txt += "\n👇 <b>Для кого?</b>"
            kb["inline_keyboard"] = [
                [{"text": "🎁 Для себя", "callback_data": f"rs_{s['gk']}"}],
                [{"text": "💝 Для другого", "callback_data": f"ro_{s['gk']}"}],
                [{"text": "❌ Отменить", "callback_data": "can"}]
            ]
        elif step == "wun":
            txt += "\n⏳ <b>Жду username...</b>"
            kb["inline_keyboard"] = [[{"text": "❌ Отменить", "callback_data": "can"}]]
        elif step == "nf":
            txt += f"\n\n⚠️ <b>@{s.get('pun')} не писал боту</b>\n\nПодарок отправится когда напишет /start\n\n👇"
            kb["inline_keyboard"] = [
                [{"text": "✅ Да", "callback_data": "cunk"}],
                [{"text": "🔄 Другой", "callback_data": "reun"}],
                [{"text": "❌ Отменить", "callback_data": "can"}]
            ]
        elif step == "anon":
            txt += f"\n👇 <b>Анонимно? (+{ANONYMOUS_PRICE}⭐️)</b>"
            kb["inline_keyboard"] = [
                [{"text": f"🎭 Да (+{ANONYMOUS_PRICE}⭐️)", "callback_data": "ay"}],
                [{"text": "👤 Нет", "callback_data": "an"}],
                [{"text": "❌ Отменить", "callback_data": "can"}]
            ]
        elif step == "msgc":
            txt += "\n👇 <b>Подпись?</b>"
            kb["inline_keyboard"] = [
                [{"text": "📝 Да", "callback_data": "mw"}],
                [{"text": "🎁 Нет", "callback_data": "mn"}],
                [{"text": "❌ Отменить", "callback_data": "can"}]
            ]
        elif step == "wmsg":
            txt += "\n⏳ <b>Жду подпись...</b>"
            kb["inline_keyboard"] = [[{"text": "❌ Отменить", "callback_data": "can"}]]
        elif step == "ok":
            txt += "\n\n✅ <b>Готово!</b>"
            kb["inline_keyboard"] = [
                [{"text": "💳 Оплатить", "callback_data": "pay"}],
                [{"text": "❌ Отменить", "callback_data": "can"}]
            ]
        elif step == "sent":
            txt += "\n\n💳 <b>Счет отправлен!</b>\n⏰ Оплати за 15 мин | /cancel"
            kb["inline_keyboard"] = []
        
        mid = self.orders.get(c)
        if mid:
            await self.api("editMessageText", chat_id=c, message_id=mid, text=txt, parse_mode="HTML", reply_markup=kb)
        else:
            r = await self.api("sendMessage", chat_id=c, text=txt, parse_mode="HTML", reply_markup=kb)
            if r.get("ok"):
                self.orders[c] = r["result"]["message_id"]
    
    async def inv(self, c):
        """Отправка инвойса"""
        s = self.states[c]
        g = GIFTS[s["gk"]]
        anon = s.get("anon", False)
        
        # ПРАВИЛЬНЫЙ расчет цены
        tp = self.calc_price(s["gk"], anon)
        
        pl = f"{s['gk']}_{c}_{int(time.time()*1000)}"
        s["pl"] = pl
        s["inv"] = time.time()
        
        # ПРАВИЛЬНЫЕ prices
        prices = [{"label": g["name"], "amount": g["price"]}]
        if anon:
            prices.append({"label": "🎭 Анонимность", "amount": ANONYMOUS_PRICE})
        
        logger.info(f"💳 Инвойс: {tp}⭐️ | Анон: {anon} | Prices: {prices}")
        
        r = await self.api(
            "sendInvoice",
            chat_id=c,
            title=f"{g['emoji']} {g['name']}",
            description=f"Оплата {tp}⭐️ | /cancel",
            payload=pl,
            currency="XTR",
            prices=prices
        )
        
        if r.get("ok"):
            await self.upd(c, "sent")
        else:
            logger.error(f"❌ Инвойс: {r.get('description')}")
            await self.api("sendMessage", chat_id=c, text=f"❌ Ошибка инвойса: {r.get('description')}")

if __name__ == "__main__":
    try:
        asyncio.run(Bot().run())
    except KeyboardInterrupt:
        print("\n👋")
