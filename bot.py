import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
import aiosqlite
from aiohttp import web
import threading
import os

# ==================== НАСТРОЙКИ ====================
API_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "123456789").split(",")]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ==================== ФУНКЦИЯ СКЛОНЕНИЯ ====================
def pluralize(n, forms):
    n = abs(n) % 100
    n1 = n % 10
    if n > 10 and n < 20: return forms[2]
    if n1 > 1 and n1 < 5: return forms[1]
    if n1 == 1: return forms[0]
    return forms[2]

def fmt_money(amount):
    word = pluralize(amount, ['сарапулка', 'сарапулки', 'сарапулок'])
    return f"{amount} {word}"

# ==================== КОНФИГУРАЦИЯ ====================
JOBS = {
    "novice": {"name": "Новичок", "base_pay": 10, "cooldown": 3600},
    "miner": {"name": "Шахтёр", "base_pay": 25, "cooldown": 3600},
    "coder": {"name": "Программист", "base_pay": 50, "cooldown": 7200},
    "trader": {"name": "Трейдер", "base_pay": 80, "cooldown": 10800}
}

SHOP_ITEMS = {
    "course": {"name": " Курсы", "price": 500, "desc": "+1 уровень профессии", "type": "level_up"},
    "coffee": {"name": "☕ Кофе-машина", "price": 1000, "desc": "-10% время отдыха", "type": "cooldown_reduce"}
}

MARKET = {
    "case_basic": {"name": "📦 Обычный кейс", "price": 200, "type": "case"},
    "biz_shawarma": {"name": "🌯 Ларёк с шаурмой", "price": 2000, "type": "business", "income": 150},
    "biz_crypto": {"name": " Крипто-ферма", "price": 15000, "type": "business", "income": 1200}
}

CARS = {
    "ok": {"name": "🚲 Ока", "price": 3000, "desc": "Едет и едет."},
    "priora": {"name": "🚘 Приора", "price": 10000, "desc": "Музыка громче двигателя."},
    "bmw": {"name": "🏎️ BMW X5", "price": 40000, "desc": "Для важных дел."},
    "gelik": {"name": "🚙 Гелик", "price": 80000, "desc": "Черный, тонированный."},
    "lambo": {"name": "🚀 Lamborghini", "price": 200000, "desc": "Король дороги."}
}

SLOTS_SYMBOLS = ['🍒', '', '🍊', '🍇', '💎', '7️⃣']
SLOTS_PAYOUTS = {
    '7️⃣7️⃣7️': 10, '💎💎': 5, '🍇🍇': 3,
    '🍊🍊🍊': 2, '🍋🍋🍋': 2, '🍒🍒': 2
}

# ==================== БАЗА ДАННЫХ ====================
async def init_db():
    async with aiosqlite.connect("economy.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY, job_key TEXT DEFAULT 'novice',
            level INTEGER DEFAULT 1, last_work_time REAL DEFAULT 0, has_coffee INTEGER DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            item_name TEXT, item_type TEXT, rarity TEXT DEFAULT 'common')""")
        await db.execute("""CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            business_name TEXT, income INTEGER, last_collect_time REAL DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS garage (
            user_id INTEGER PRIMARY KEY, car_key TEXT DEFAULT None, car_name TEXT DEFAULT None)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS daily_bonus (
            user_id INTEGER PRIMARY KEY, last_claim REAL DEFAULT 0, streak INTEGER DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS robbery (
            user_id INTEGER PRIMARY KEY, last_robbery REAL DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS lottery_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, draw_date TEXT)""")
        await db.commit()

# ==================== ФУНКЦИИ БД ====================
async def get_user(user_id: int):
    async with aiosqlite.connect("economy.db") as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        if result: return {"balance": result[0]}
        await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()
        return {"balance": 0}

async def update_balance(user_id: int, amount: int):
    async with aiosqlite.connect("economy.db") as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def get_profile(user_id: int):
    async with aiosqlite.connect("economy.db") as db:
        cursor = await db.execute("SELECT job_key, level, last_work_time, has_coffee FROM profiles WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        if not result:
            await db.execute("INSERT INTO profiles (user_id) VALUES (?)", (user_id,))
            await db.commit()
            return {"job_key": "novice", "level": 1, "last_work_time": 0, "has_coffee": 0}
        return {"job_key": result[0], "level": result[1], "last_work_time": result[2], "has_coffee": result[3]}

async def set_car(user_id: int, car_key: str, car_name: str):
    async with aiosqlite.connect("economy.db") as db:
        await db.execute("REPLACE INTO garage (user_id, car_key, car_name) VALUES (?, ?, ?)", (user_id, car_key, car_name))
        await db.commit()

async def get_car(user_id: int):
    async with aiosqlite.connect("economy.db") as db:
        cursor = await db.execute("SELECT car_name FROM garage WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

# ==================== ВЕБ-СЕРВЕР (чтобы Render не усыплял) ====================
async def handle_ping(request):
    return web.Response(text="Bot is alive! 🤖")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("✅ Web server started on port 8080")

# ==================== КОМАНДЫ ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 <b>Экономика группы</b>\n\n"
        "💰 /balance - мои сарапулки\n"
        "💼 /work - работать\n"
        "💸 /pay - перевести (ответь на сообщение)\n"
        "🔫 /rob - ограбить (ответь на сообщение)\n"
        " /daily - ежедневный бонус\n"
        "🎰 /slots ставка - казино\n"
        "🎟️ /buy_ticket - лотерейный билет\n"
        "🛒 /shop - улучшения\n"
        "🏪 /market - бизнесы и кейсы\n"
        "🚗 /cars - автосалон\n"
        "️ /mycar - моя тачка\n"
        "💼 /collect - прибыль с бизнеса\n"
        "🎒 /inv - инвентарь\n"
        "📊 /info - моя карточка\n"
        "🏆 /top - топ богачей"
    )

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    user = await get_user(message.from_user.id)
    car = await get_car(message.from_user.id)
    car_text = f"\n🚗 Тачка: {car}" if car else "\n🚗 Тачка: нет (/cars)"
    await message.answer(f"💰 Баланс: <b>{fmt_money(user['balance'])}</b>{car_text}", parse_mode="HTML")

@dp.message(Command("work"))
async def cmd_work(message: Message):
    user_id = message.from_user.id
    profile = await get_profile(user_id)
    job = JOBS[profile['job_key']]
    current_time = time.time()
    cooldown = job['cooldown'] * (0.9 if profile['has_coffee'] else 1.0)
    time_passed = current_time - profile['last_work_time']
    if time_passed < cooldown:
        remaining = int(cooldown - time_passed)
        return await message.answer(f"⏳ Отдыхайте еще {remaining // 60} мин.")
    salary = job['base_pay'] * profile['level'] + random.randint(0, 5)
    await update_balance(user_id, salary)
    async with aiosqlite.connect("economy.db") as db:
        await db.execute("UPDATE profiles SET last_work_time = ? WHERE user_id = ?", (current_time, user_id))
        await db.commit()
    await message.answer(f"💼 <b>{job['name']}</b> (Ур. {profile['level']}): заработано <b>{fmt_money(salary)}</b>.", parse_mode="HTML")

@dp.message(Command("jobs"))
async def cmd_jobs(message: Message):
    text = "📋 <b>Вакансии:</b>\n"
    for key, info in JOBS.items():
        text += f" {info['name']} ({info['base_pay']} сарапулок/час) → /job {key}\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("job"))
async def cmd_change_job(message: Message):
    args = message.text.split()
    if len(args) < 2 or args[1] not in JOBS:
        return await message.answer("Выберите работу: /jobs")
    async with aiosqlite.connect("economy.db") as db:
        await db.execute("UPDATE profiles SET job_key = ? WHERE user_id = ?", (args[1], message.from_user.id))
        await db.commit()
    await message.answer(f"✅ Вы теперь: <b>{JOBS[args[1]]['name']}</b>", parse_mode="HTML")

@dp.message(Command("pay"))
async def cmd_pay(message: Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: /pay сумма (ответь на сообщение)")
    if not message.reply_to_message:
        return await message.answer("Ответьте на сообщение получателя!")
    try: amount = int(args[1])
    except: return await message.answer("Сумма должна быть числом!")
    if amount <= 0: return await message.answer("Сумма должна быть положительной!")
    sender_id = message.from_user.id
    receiver_id = message.reply_to_message.from_user.id
    if sender_id == receiver_id: return await message.answer("Нельзя перевести самому себе!")
    sender_bal = await get_user(sender_id)
    if sender_bal['balance'] < amount:
        return await message.answer(f"❌ Недостаточно ({fmt_money(sender_bal['balance'])})")
    await update_balance(sender_id, -amount)
    await update_balance(receiver_id, amount)
    await message.answer(f"✅ <b>{message.from_user.full_name}</b> перевёл <b>{fmt_money(amount)}</b> пользователю <b>{message.reply_to_message.from_user.full_name}</b>", parse_mode="HTML")

@dp.message(Command("rob"))
async def cmd_rob(message: Message):
    if not message.reply_to_message:
        return await message.answer("Ответьте на сообщение жертвы!")
    robber_id = message.from_user.id
    victim_id = message.reply_to_message.from_user.id
    if robber_id == victim_id: return await message.answer("Нельзя ограбить самого себя!")
    async with aiosqlite.connect("economy.db") as db:
        cursor = await db.execute("SELECT last_robbery FROM robbery WHERE user_id = ?", (robber_id,))
        result = await cursor.fetchone()
        last_rob = result[0] if result else 0
        current_time = time.time()
        if current_time - last_rob < 10800:
            remaining = int(10800 - (current_time - last_rob))
            return await message.answer(f"⏳ Отдыхайте еще {remaining // 3600} ч.")
        await db.execute("REPLACE INTO robbery (user_id, last_robbery) VALUES (?, ?)", (robber_id, current_time))
        await db.commit()
    victim_bal = await get_user(victim_id)
    if victim_bal['balance'] < 50:
        return await message.answer("У жертвы слишком мало денег!")
    success = random.random() < 0.4
    if success:
        stolen = int(victim_bal['balance'] * random.uniform(0.1, 0.5))
        await update_balance(victim_id, -stolen)
        await update_balance(robber_id, stolen)
        await message.answer(f"🔫 <b>ОГРАБЛЕНИЕ УСПЕШНО!</b>\n\n{message.from_user.full_name} украл <b>{fmt_money(stolen)}</b> у {message.reply_to_message.from_user.full_name}!", parse_mode="HTML")
    else:
        robber_bal = await get_user(robber_id)
        penalty = int(robber_bal['balance'] * 0.2)
        await update_balance(robber_id, -penalty)
        await update_balance(victim_id, penalty)
        await message.answer(f"🚨 <b>ПОПАЛСЯ!</b>\n\n{message.from_user.full_name} заплатил штраф <b>{fmt_money(penalty)}</b> пользователю {message.reply_to_message.from_user.full_name}!", parse_mode="HTML")

@dp.message(Command("daily"))
async def cmd_daily(message: Message):
    user_id = message.from_user.id
    current_time = time.time()
    async with aiosqlite.connect("economy.db") as db:
        cursor = await db.execute("SELECT last_claim, streak FROM daily_bonus WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        last_claim, streak = (result[0], result[1]) if result else (0, 0)
        if current_time - last_claim < 86400:
            remaining = int(86400 - (current_time - last_claim))
            return await message.answer(f"⏳ Приходи через {remaining // 3600} ч. {remaining % 3600 // 60} мин.")
        if current_time - last_claim < 172800: streak += 1
        else: streak = 1
        base_bonus = random.randint(100, 300)
        multiplier = min(streak, 7)
        bonus = base_bonus * multiplier
        await update_balance(user_id, bonus)
        await db.execute("REPLACE INTO daily_bonus (user_id, last_claim, streak) VALUES (?, ?, ?)", (user_id, current_time, streak))
        await db.commit()
    await message.answer(f"🎁 <b>Ежедневный бонус!</b>\n\nТы зашёл {streak} {pluralize(streak, ['день', 'дня', 'дней'])} подряд!\n💰 Получено: <b>{fmt_money(bonus)}</b>", parse_mode="HTML")

@dp.message(Command("slots"))
async def cmd_slots(message: Message):
    args = message.text.split()
    if len(args) < 2: return await message.answer("Укажите ставку: /slots 100")
    try: bet = int(args[1])
    except: return await message.answer("Ставка должна быть числом!")
    if bet < 10: return await message.answer("Минимальная ставка: 10 сарапулок")
    user_id = message.from_user.id
    user_bal = await get_user(user_id)
    if user_bal['balance'] < bet:
        return await message.answer(f"❌ Недостаточно ({fmt_money(user_bal['balance'])})")
    await update_balance(user_id, -bet)
    result = [random.choice(SLOTS_SYMBOLS) for _ in range(3)]
    result_str = ''.join(result)
    win_amount = 0
    if result_str in SLOTS_PAYOUTS:
        multiplier = SLOTS_PAYOUTS[result_str]
        win_amount = bet * multiplier
        await update_balance(user_id, win_amount)
    text = f"🎰 <b>СЛОТЫ</b>\n\nСтавка: {fmt_money(bet)}\nРезультат: {' | '.join(result)}\n\n"
    if win_amount > 0:
        text += f"🎉 <b>ВЫИГРЫШ: {fmt_money(win_amount)}</b> (x{SLOTS_PAYOUTS[result_str]})"
    else:
        text += "💀 Проигрыш. Попробуй ещё раз!"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("buy_ticket"))
async def cmd_buy_ticket(message: Message):
    user_id = message.from_user.id
    user_bal = await get_user(user_id)
    ticket_price = 50
    if user_bal['balance'] < ticket_price:
        return await message.answer(f"❌ Билет стоит {fmt_money(ticket_price)}")
    await update_balance(user_id, -ticket_price)
    today = time.strftime("%Y-%m-%d")
    async with aiosqlite.connect("economy.db") as db:
        await db.execute("INSERT INTO lottery_tickets (user_id, draw_date) VALUES (?, ?)", (user_id, today))
        await db.commit()
    await message.answer(f"🎟️ Вы купили лотерейный билет за {fmt_money(ticket_price)}!\nРозыгрыш: /lottery_draw (админ)")

@dp.message(Command("lottery_draw"))
async def cmd_lottery_draw(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    today = time.strftime("%Y-%m-%d")
    async with aiosqlite.connect("economy.db") as db:
        cursor = await db.execute("SELECT user_id FROM lottery_tickets WHERE draw_date = ?", (today,))
        tickets = await cursor.fetchall()
        if not tickets: return await message.answer("Сегодня никто не купил билеты!")
        winner_id = random.choice(tickets)[0]
        bank = len(tickets) * 50
        await update_balance(winner_id, bank)
        await db.execute("DELETE FROM lottery_tickets WHERE draw_date = ?", (today,))
        await db.commit()
    winner = await bot.get_chat_member(message.chat.id, winner_id)
    await message.answer(f"🎊 <b>РОЗЫГРЫШ ЛОТЕРЕИ!</b>\n\n🏆 Победитель: <b>{winner.user.full_name}</b>\n💰 Выигрыш: <b>{fmt_money(bank)}</b>\n\nВсего участников: {len(tickets)}", parse_mode="HTML")

@dp.message(Command("info"))
async def cmd_info(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    profile = await get_profile(user_id)
    car = await get_car(user_id)
    async with aiosqlite.connect("economy.db") as db:
        cursor = await db.execute("SELECT COUNT(*) FROM businesses WHERE user_id = ?", (user_id,))
        biz_count = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (user_id,))
        inv_count = (await cursor.fetchone())[0]
    job = JOBS[profile['job_key']]
    text = f" <b>Карточка игрока</b>\n\n👤 <b>{message.from_user.full_name}</b>\n\n"
    text += f"💰 Баланс: <b>{fmt_money(user['balance'])}</b>\n"
    text += f"💼 Профессия: <b>{job['name']}</b> (Ур. {profile['level']})\n"
    text += f"🚗 Машина: <b>{car if car else 'нет'}</b>\n"
    text += f"🏪 Бизнесов: <b>{biz_count}</b>\n"
    text += f"🎒 Предметов: <b>{inv_count}</b>\n"
    if profile['has_coffee']: text += "☕ Кофе-машина: <b>есть</b>\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    text = "🛒 <b>Улучшения:</b>\n"
    for k, v in SHOP_ITEMS.items():
        text += f"🔹 {v['name']} ({fmt_money(v['price'])}) → /buy {k}\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("buy"))
async def cmd_buy(message: Message):
    args = message.text.split()
    if len(args) < 2 or args[1] not in SHOP_ITEMS: return await message.answer("/shop")
    item = SHOP_ITEMS[args[1]]
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user['balance'] < item['price']: return await message.answer(f"❌ Нужно {fmt_money(item['price'])}")
    await update_balance(user_id, -item['price'])
    if item['type'] == 'level_up':
        p = await get_profile(user_id)
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("UPDATE profiles SET level = ? WHERE user_id = ?", (p['level']+1, user_id))
            await db.commit()
        await message.answer(f"✅ Уровень повышен до {p['level']+1}!")
    elif item['type'] == 'cooldown_reduce':
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("UPDATE profiles SET has_coffee = 1 WHERE user_id = ?", (user_id,))
            await db.commit()
        await message.answer("✅ Кофе куплен! Работа быстрее.")

@dp.message(Command("market"))
async def cmd_market(message: Message):
    text = " <b>Рынок:</b>\n"
    for k, v in MARKET.items():
        text += f"🔹 {v['name']} ({fmt_money(v['price'])}) → /buy_market {k}\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("buy_market"))
async def cmd_buy_market(message: Message):
    args = message.text.split()
    if len(args) < 2 or args[1] not in MARKET: return await message.answer("/market")
    item = MARKET[args[1]]
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user['balance'] < item['price']: return await message.answer(f"❌ Нужно {fmt_money(item['price'])}")
    await update_balance(user_id, -item['price'])
    if item['type'] == 'case':
        rand = random.randint(1, 100)
        if rand <= 5: prize, rar = " Золотая Скрипка", "legendary"
        elif rand <= 25: prize, rar = "💎 Алмаз", "rare"
        else: prize, rar = "📄 Бумага", "common"
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("INSERT INTO inventory (user_id, item_name, item_type, rarity) VALUES (?, ?, 'card', ?)", (user_id, prize, rar))
            await db.commit()
        await message.answer(f"📦 Выпало: <b>{prize}</b> ({rar})", parse_mode="HTML")
    elif item['type'] == 'business':
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("INSERT INTO businesses (user_id, business_name, income) VALUES (?, ?, ?)", (user_id, item['name'], item['income']))
            await db.commit()
        await message.answer(f"✅ Куплен <b>{item['name']}</b>. Жми /collect раз в сутки!", parse_mode="HTML")

@dp.message(Command("collect"))
async def cmd_collect(message: Message):
    user_id = message.from_user.id
    now = time.time()
    total = 0
    async with aiosqlite.connect("economy.db") as db:
        cursor = await db.execute("SELECT id, income, last_collect_time FROM businesses WHERE user_id = ?", (user_id,))
        bizs = await cursor.fetchall()
        if not bizs: return await message.answer("Нет бизнеса.")
        for bid, inc, last in bizs:
            if now - last > 86400:
                total += inc
                await db.execute("UPDATE businesses SET last_collect_time = ? WHERE id = ?", (now, bid))
        await db.commit()
    if total > 0:
        await update_balance(user_id, total)
        await message.answer(f"💼 Прибыль: <b>+{fmt_money(total)}</b>", parse_mode="HTML")
    else:
        await message.answer("⏳ Рано. Приходи завтра.")

@dp.message(Command("cars"))
async def cmd_cars(message: Message):
    text = "🚗 <b>Автосалон:</b>\n\n"
    for k, v in CARS.items():
        text += f" <b>{v['name']}</b>\n   💰 {fmt_money(v['price'])}\n   <i>{v['desc']}</i>\n   Купить: <code>/buycar {k}</code>\n\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("buycar"))
async def cmd_buycar(message: Message):
    args = message.text.split()
    if len(args) < 2 or args[1] not in CARS: return await message.answer("/cars")
    car_key = args[1]
    car = CARS[car_key]
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user['balance'] < car['price']: return await message.answer(f"❌ Нужно {fmt_money(car['price'])}")
    await update_balance(user_id, -car['price'])
    await set_car(user_id, car_key, car['name'])
    await message.answer(f"🎉 <b>КУПЛЕНО!</b>\nТеперь ты ездишь на <b>{car['name']}</b>!\nПроверь через /mycar", parse_mode="HTML")

@dp.message(Command("mycar"))
async def cmd_mycar(message: Message):
    car = await get_car(message.from_user.id)
    if car: await message.answer(f"🅿️ Твой гараж:\n <b>{car}</b>", parse_mode="HTML")
    else: await message.answer("🅿️ Гараж пуст. Купи тачку в /cars!")

@dp.message(Command("inv"))
async def cmd_inv(message: Message):
    async with aiosqlite.connect("economy.db") as db:
        cursor = await db.execute("SELECT item_name, rarity FROM inventory WHERE user_id = ?", (message.from_user.id,))
        items = await cursor.fetchall()
    if not items: return await message.answer("🎒 Пусто.")
    text = "🎒 <b>Предметы:</b>\n"
    for name, rar in items:
        c = "🟡" if rar=="legendary" else "🔵" if rar=="rare" else "🟢"
        text += f"{c} {name}\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("top"))
async def cmd_top(message: Message):
    async with aiosqlite.connect("economy.db") as db:
        cursor = await db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
        rows = await cursor.fetchall()
    text = "🏆 <b>Топ сарапулек:</b>\n\n"
    for i, (uid, bal) in enumerate(rows, 1):
        try:
            u = await bot.get_chat_member(message.chat.id, uid)
            name = u.user.full_name
        except: name = f"User{uid}"
        text += f"{i}. {name} — {fmt_money(bal)}\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("give"))
async def cmd_give(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    args = message.text.split()
    if len(args) < 2 or not message.reply_to_message: return await message.answer("/give сумма (ответ)")
    try: amount = int(args[1])
    except: return await message.answer("Число!")
    await update_balance(message.reply_to_message.from_user.id, amount)
    await message.answer(f"✅ Выдано {fmt_money(amount)}.")

# ==================== ЗАПУСК ====================
async def main():
    await init_db()
    print("🤖 Бот запущен! Валюта: Сарапулки")
    # Запускаем веб-сервер в фоне
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
