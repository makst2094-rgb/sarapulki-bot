import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import asyncpg
from aiohttp import web
import os

# ==================== НАСТРОЙКИ ====================
API_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]
DATABASE_URL = os.environ.get("DATABASE_URL", "")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
pool = None

# ==================== ФУНКЦИЯ СКЛОНЕНИЯ ====================
def pluralize(n, forms):
    n = abs(n) % 100
    n1 = n %
        if balance is not None:
            return {" 10
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
    "lambo": {"name": "🏎️ Lamborghini", "price": 200000, "desc": "Король дороги."}
}

SLOTS_SYMBOLS = ['🍒', '🍋', '🍊', '', '💎', '7️']
SLOTS_PAYOUTS = {
    '7️⃣7️⃣7️⃣': 10,
    '💎💎💎': 5,
    '🍇🍇🍇': 3,
    '🍊🍊': 2,
    '🍋🍋🍋': 2,
    '🍒🍒🍒': 2
}

# ==================== БАЗА ДАННЫХ ====================
async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY, 
                balance INTEGER DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                user_id BIGINT PRIMARY KEY, 
                job_key TEXT DEFAULT 'novice',
                level INTEGER DEFAULT 1, 
                last_work_time REAL DEFAULT 0, 
                has_coffee BOOLEAN DEFAULT FALSE
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY, 
                user_id BIGINT,
                item_name TEXT, 
                item_type TEXT, 
                rarity TEXT DEFAULT 'common'
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id SERIAL PRIMARY KEY, 
                user_id BIGINT,
balance": balance}
        await conn.execute("INSERT INTO                business_name TEXT, 
                income INTEGER, 
                last_collect_time REAL DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS garage (
                user_id BIGINT PRIMARY KEY, 
                car_key TEXT, 
                car_name TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_bonus (
                user_id BIGINT PRIMARY KEY, 
                last_claim REAL DEFAULT 0, 
                streak INTEGER DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS robbery (
                user_id BIGINT PRIMARY KEY, 
                last_robbery REAL DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS lottery_tickets (
                id SERIAL PRIMARY KEY, 
                user_id BIGINT, 
                draw_date TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS usernames (
                user_id BIGINT PRIMARY KEY, 
                username TEXT
            )
        """)
    
    print("✅ База данных PostgreSQL инициализирована")

async def save_username(user_id: int, username: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO usernames (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET username = $2",
            user_id, username
        )

async def get_username(user_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT username FROM usernames WHERE user_id = $1", user_id)

async def get_user(user_id: int):
    async with pool.acquire() as conn:
        balance = await conn.fetchval("SELECT balance FROM users WHERE user_id = $1", user_id)
        if balance is not None:
            return {"balance": balance}
        await conn.execute("INSERT INTO users (user_id) VALUES ($1)", user_id) users (user_id) VALUES ($1)", user_id)
        return {"balance": 0}

async def
        return {"balance": 0}

async def update_balance(user_id: int, amount: int):
 update_balance(user_id: int, amount: int):
    async with pool.acquire() as conn:
        await    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance = balance + $1 conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", amount, user_id) WHERE user_id = $2", amount, user_id)

async def get_profile(user_id: int):
   

async def get_profile(user_id: int):
    async with pool.acquire() as conn:
        row = async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT job_key, await conn.fetchrow(
            "SELECT job_key, level, last_work_time, has_coffee FROM profiles WHERE level, last_work_time, has_coffee FROM profiles WHERE user_id = $1", 
            user_id
 user_id = $1", 
            user_id
        )
        if not row:
            await conn        )
        if not row:
            await conn.execute("INSERT INTO profiles (user_id) VALUES ($1.execute("INSERT INTO profiles (user_id) VALUES ($1)", user_id)
            return {"job_key": ")", user_id)
            return {"job_key": "novice", "level": 1, "last_worknovice", "level": 1, "last_work_time": 0, "has_coffee": False}_time": 0, "has_coffee": False}
        return dict(row)

async def set_car(user
        return dict(row)

async def set_car(user_id: int, car_key: str, car_name:_id: int, car_key: str, car_name: str):
    async with pool.acquire() as conn: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO garage
        await conn.execute(
            "INSERT INTO garage (user_id, car_key, car_name) VALUES ($ (user_id, car_key, car_name) VALUES ($1, $2, $3) ON CONFLICT (1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET car_key = $2,user_id) DO UPDATE SET car_key = $2, car_name = $3",
            user_id, car car_name = $3",
            user_id, car_key, car_name
        )

async def get_car_key, car_name
        )

async def get_car(user_id: int):
    async with pool.acquire()(user_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT as conn:
        return await conn.fetchval("SELECT car_name FROM garage WHERE user_id = $1", user car_name FROM garage WHERE user_id = $1", user_id)

# ==================== ВЕБ-СЕР_id)

# ==================== ВЕБ-СЕРВЕР ====================
async def handle_ping(request):ВЕР ====================
async def handle_ping(request):
    return web.Response(text="Bot is alive! 
    return web.Response(text="Bot is alive! ")

async def start_web_server():
   ")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app) handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.T
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0CPSite(runner, '0.0.0.0', 8080)
    await.0', 8080)
    await site.start()
    print("✅ Web server started on site.start()
    print("✅ Web server started on port 8080")

# ==================== КО port 8080")

# ==================== КОМАНДЫ ====================
@dp.message(Command("МАНДЫ ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
start"))
async def cmd_start(message: Message):
    await save_username(message.from_user.id, message.from_user    await save_username(message.from_user.id, message.from_user.full_name)
    
    await message.answer(
       .full_name)
    
    await message.answer(
        "👋 <b>Экономика группы</ "👋 <b>Экономика группы</b>\n\n"
        "💰 /balanceb>\n\n"
        "💰 /balance - мои сарапулки\n"
        " - мои сарапулки\n"
        " /work - работать\n"
        "💸 /work - работать\n"
        "💸 /pay - перевести (ответь на сообщение)\n /pay - перевести (ответь на сообщение)\n"
        "🔫 /rob - ограбить"
        "🔫 /rob - ограбить (ответь на сообщение)\n"
        " (ответь на сообщение)\n"
        " /daily - ежедневный бонус\n" /daily - ежедневный бонус\n"
        "🎰 /slots ставка - казино
        "🎰 /slots ставка - казино\n"
        "🎟️ /buy_ticket\n"
        "🎟️ /buy_ticket - лотерейный билет\n"
        " - лотерейный билет\n"
        "🛒 /shop - улучшения\n"
        "🛒 /shop - улучшения\n"
        "🏪 /market - бизнесы и кейсы\n🏪 /market - бизнесы и кейсы\n"
        "🚗 /cars - авт"
        "🚗 /cars - автосалон\n"
        "осалон\n"
        "️ /mycar - моя тачка\n"️ /mycar - моя тачка\n"
        "💼 /collect - прибыль с бизнеса\n
        "💼 /collect - прибыль с бизнеса\n"
        "🎒 /inv - инв"
        "🎒 /inv - инвентарь\n"
        "📊 /ентарь\n"
        "📊 /info - моя карточка\n"
        "info - моя карточка\n"
        " /rating - рейтинг богачей\n"
 /rating - рейтинг богачей\n"
        "🃏 /blackjack - Блэк        "🃏 /blackjack - Блэкджек с Игорёчком"
    )

@джек с Игорёчком"
    )

@dp.message(Command("balance"))
async def cmd_balance(messagedp.message(Command("balance"))
async def cmd_balance(message: Message):
    await save_username(message.from_user.id: Message):
    await save_username(message.from_user.id, message.from_user.full_name)
    user = await, message.from_user.full_name)
    user = await get_user(message.from_user.id)
    car = await get_user(message.from_user.id)
    car = await get_car(message.from_user.id)
    car_text = get_car(message.from_user.id)
    car_text = f"\n🚗 Тачка: {car f"\n🚗 Тачка: {car}" if car else "\n🚗 Тачка}" if car else "\n🚗 Тачка: нет (/cars)"
    await message.answer(f": нет (/cars)"
    await message.answer(f"💰 Баланс: <b>{fmt_money(user💰 Баланс: <b>{fmt_money(user['balance'])}</b>{car_text}", parse_mode="['balance'])}</b>{car_text}", parse_mode="HTML")

@dp.message(Command("work"))
asyncHTML")

@dp.message(Command("work"))
async def cmd_work(message: Message):
    await save_username def cmd_work(message: Message):
    await save_username(message.from_user.id, message.from_user.full_name)
(message.from_user.id, message.from_user.full_name)
    user_id = message.from_user.id
    profile =    user_id = message.from_user.id
    profile = await get_profile(user_id)
    job = JOBS await get_profile(user_id)
    job = JOBS[profile['job_key']]
    current_time = time[profile['job_key']]
    current_time = time.time()
    cooldown = job['cooldown'] * (.time()
    cooldown = job['cooldown'] * (0.9 if profile['has_coffee'] else 0.9 if profile['has_coffee'] else 1.0)
    time_passed = current_time -1.0)
    time_passed = current_time - profile['last_work_time']
    if time_passed < profile['last_work_time']
    if time_passed < cooldown:
        remaining = int(cooldown - time_passed cooldown:
        remaining = int(cooldown - time_passed)
        return await message.answer(f"⏳)
        return await message.answer(f"⏳ Отдыхайте еще {remaining // 60} мин Отдыхайте еще {remaining // 60} мин.")
    salary = job['base_pay'] * profile.")
    salary = job['base_pay'] * profile['level'] + random.randint(0, 5)['level'] + random.randint(0, 5)
    await update_balance(user_id, salary)
   
    await update_balance(user_id, salary)
    async with pool.acquire() as conn:
        await conn async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET last_work_time = $1 WHERE.execute("UPDATE profiles SET last_work_time = $1 WHERE user_id = $2", current_time, user_id) user_id = $2", current_time, user_id)
    await message.answer(f"💼 <b>{
    await message.answer(f"💼 <b>{job['name']}</b> (Ур. {profilejob['name']}</b> (Ур. {profile['level']}): заработано <b>{fmt_money(s['level']}): заработано <b>{fmt_money(salary)}</b>.", parse_mode="HTML")

@alary)}</b>.", parse_mode="HTML")

@dp.message(Command("jobs"))
async def cmd_jobs(messagedp.message(Command("jobs"))
async def cmd_jobs(message: Message):
    text = "📋 <: Message):
    text = "📋 <b>Вакансии:</b>\n"
b>Вакансии:</b>\n"
    for key, info in JOBS.items():
           for key, info in JOBS.items():
        text += f"🔹 {info['name']} text += f"🔹 {info['name']} ({info['base_pay']} сарапулок/час ({info['base_pay']} сарапулок/час) → /job {key}\n"
    await) → /job {key}\n"
    await message.answer(text, parse_mode="HTML")

@dp message.answer(text, parse_mode="HTML")

@dp.message(Command("job"))
async def cmd_change_job(message.message(Command("job"))
async def cmd_change_job(message: Message):
    args = message.text.split()
: Message):
    args = message.text.split()
    if len(args) < 2 or args[1    if len(args) < 2 or args[1] not in JOBS:
        return await message.answer] not in JOBS:
        return await message.answer("Выберите работу: /jobs")
    async("Выберите работу: /jobs")
    async with pool.acquire() as conn:
        await conn.execute with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET job_key = $1 WHERE user_id("UPDATE profiles SET job_key = $1 WHERE user_id = $2", args[1], message.from_user.id = $2", args[1], message.from_user.id)
    await message.answer(f"✅ Вы теперь:)
    await message.answer(f"✅ Вы теперь: <b>{JOBS[args[1]]['name']}</ <b>{JOBS[args[1]]['name']}</b>", parse_mode="HTML")

@dp.message(Commandb>", parse_mode="HTML")

@dp.message(Command("pay"))
async def cmd_pay(message: Message):("pay"))
async def cmd_pay(message: Message):
    args = message.text.split()
    if len
    args = message.text.split()
    if len(args) < 2:
        return await message.answer(args) < 2:
        return await message.answer("Использование: /pay сумма (ответь на("Использование: /pay сумма (ответь на сообщение)")
    if not message.reply_to_message:
 сообщение)")
    if not message.reply_to_message:
        return await message.answer("Ответьте на сообщение получателя        return await message.answer("Ответьте на сообщение получателя!")
    try: amount = int(args[1])!")
    try: amount = int(args[1])
    except: return await message.answer("Сумма
    except: return await message.answer("Сумма должна быть числом!")
    if amount <= 0 должна быть числом!")
    if amount <= 0: return await message.answer("Сумма должна быть положитель: return await message.answer("Сумма должна быть положительной!")
    sender_id = message.from_user.id
ной!")
    sender_id = message.from_user.id
    receiver_id = message.reply_to_message.from_user.id
    receiver_id = message.reply_to_message.from_user.id
    if sender_id == receiver_id: return await message.answer    if sender_id == receiver_id: return await message.answer("Нельзя перевести самому себе!")
    sender_bal("Нельзя перевести самому себе!")
    sender_bal = await get_user(sender_id)
    if sender_bal = await get_user(sender_id)
    if sender_bal['balance'] < amount:
        return await message.answer['balance'] < amount:
        return await message.answer(f"❌ Недостаточно ({fmt_money(sender_bal(f"❌ Недостаточно ({fmt_money(sender_bal['balance'])})")
    await update_balance(sender_id['balance'])})")
    await update_balance(sender_id, -amount)
    await update_balance(receiver_id,, -amount)
    await update_balance(receiver_id, amount)
    await save_username(receiver_id, message.reply amount)
    await save_username(receiver_id, message.reply_to_message.from_user.full_name)
    await message.answer_to_message.from_user.full_name)
    await message.answer(f"✅ <b>{message.from_user.full_name}</(f"✅ <b>{message.from_user.full_name}</b> перевёл <b>{fmt_money(amount)}</bb> перевёл <b>{fmt_money(amount)}</b> пользователю <b>{message.reply_to_message> пользователю <b>{message.reply_to_message.from_user.full_name}</b>", parse_mode="HTML").from_user.full_name}</b>", parse_mode="HTML")

@dp.message(Command("rob"))
async def cmd

@dp.message(Command("rob"))
async def cmd_rob(message: Message):
    if not message.reply_rob(message: Message):
    if not message.reply_to_message:
        return await message.answer("Ответьте_to_message:
        return await message.answer("Ответьте на сообщение жертвы!")
    robber_id = message.from на сообщение жертвы!")
    robber_id = message.from_user.id
    victim_id = message.reply_to_message.from_user.id
    victim_id = message.reply_to_message.from_user.id
    if robber_id == victim_id: return_user.id
    if robber_id == victim_id: return await message.answer("Нельзя ограбить самого себя!")
 await message.answer("Нельзя ограбить самого себя!")
    async with pool.acquire() as conn:
        last    async with pool.acquire() as conn:
        last_rob = await conn.fetchval("SELECT last_rob_rob = await conn.fetchval("SELECT last_robbery FROM robbery WHERE user_id = $1", robber_idbery FROM robbery WHERE user_id = $1", robber_id)
        last_rob = last_rob or )
        last_rob = last_rob or 0
        current_time = time.time()
        if0
        current_time = time.time()
        if current_time - last_rob < 1080 current_time - last_rob < 10800:
            remaining = int(10800:
            remaining = int(10800 - (current_time - last_rob))
           0 - (current_time - last_rob))
            return await message.answer(f"⏳ Отдыхайте return await message.answer(f"⏳ Отдыхайте еще {remaining // 3600} ч.") еще {remaining // 3600} ч.")
        await conn.execute(
            "INSERT INTO robbery
        await conn.execute(
            "INSERT INTO robbery (user_id, last_robbery) VALUES ($1 (user_id, last_robbery) VALUES ($1, $2) ON CONFLICT (user_id) DO, $2) ON CONFLICT (user_id) DO UPDATE SET last_robbery = $2",
            UPDATE SET last_robbery = $2",
            robber_id, current_time
        )
    victim_bal robber_id, current_time
        )
    victim_bal = await get_user(victim_id)
    if victim = await get_user(victim_id)
    if victim_bal['balance'] < 50:
        return_bal['balance'] < 50:
        return await message.answer("У жертвы слишком мало денег!")
 await message.answer("У жертвы слишком мало денег!")
    success = random.random() < 0.4
    success = random.random() < 0.4
    if success:
        stolen = int(victim_bal    if success:
        stolen = int(victim_bal['balance'] * random.uniform(0.1, ['balance'] * random.uniform(0.1, 0.5))
        await update_balance(victim_id0.5))
        await update_balance(victim_id, -stolen)
        await update_balance(rob, -stolen)
        await update_balance(robber_id, stolen)
        await message.answer(f"ber_id, stolen)
        await message.answer(f"🔫 <b>ОГРАБЛЕНИЕ У🔫 <b>ОГРАБЛЕНИЕ УСПЕШНО!</b>\n\n{message.fromСПЕШНО!</b>\n\n{message.from_user.full_name} украл <b>{fmt_money_user.full_name} украл <b>{fmt_money(stolen)}</b> у {message.reply_to_message.from(stolen)}</b> у {message.reply_to_message.from_user.full_name}!", parse_mode="HTML")
_user.full_name}!", parse_mode="HTML")
    else:
        robber_bal = await get_user(    else:
        robber_bal = await get_user(robber_id)
        penalty = int(robberrobber_id)
        penalty = int(robber_bal['balance'] * 0.2)
       _bal['balance'] * 0.2)
        await update_balance(robber_id, -penalty) await update_balance(robber_id, -penalty)
        await update_balance(victim_id, penalty)

        await update_balance(victim_id, penalty)
        await message.answer(f"🚔        await message.answer(f"🚔 <b>ПОПАЛСЯ!</b>\n <b>ПОПАЛСЯ!</b>\n\n{message.from_user.full_name} заплатил штраф <\n{message.from_user.full_name} заплатил штраф <b>{fmt_money(penalty)}</b> пользоватb>{fmt_money(penalty)}</b> пользователю {message.reply_to_message.from_user.full_name}елю {message.reply_to_message.from_user.full_name}!", parse_mode="HTML")

@dp.message(Command("!", parse_mode="HTML")

@dp.message(Command("daily"))
async def cmd_daily(message: Message):
daily"))
async def cmd_daily(message: Message):
    user_id = message.from_user.id
    await save    user_id = message.from_user.id
    await save_username(user_id, message.from_user.full_name)
   _username(user_id, message.from_user.full_name)
    current_time = time.time()
    async with pool.acquire current_time = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow() as conn:
        row = await conn.fetchrow("SELECT last_claim, streak FROM daily_bonus WHERE user_id("SELECT last_claim, streak FROM daily_bonus WHERE user_id = $1", user_id)
        last_claim, = $1", user_id)
        last_claim, streak = (row['last_claim'], row['streak streak = (row['last_claim'], row['streak']) if row else (0, 0)
       ']) if row else (0, 0)
        if current_time - last_claim < 8640 if current_time - last_claim < 86400:
            remaining = int(86400:
            remaining = int(86400 - (current_time - last_claim))
            return0 - (current_time - last_claim))
            return await message.answer(f"⏰ Приходи через { await message.answer(f"⏰ Приходи через {remaining // 3600} ч. {remainingremaining // 3600} ч. {remaining % 3600 // 60} мин % 3600 // 60} мин.")
        if current_time - last_claim < 1.")
        if current_time - last_claim < 172800: streak += 1
       72800: streak += 1
        else: streak = 1
        base_bonus = random else: streak = 1
        base_bonus = random.randint(100, 300)
.randint(100, 300)
        multiplier = min(streak, 7)
               multiplier = min(streak, 7)
        bonus = base_bonus * multiplier
        await update_balance(user bonus = base_bonus * multiplier
        await update_balance(user_id, bonus)
        await conn.execute(
           _id, bonus)
        await conn.execute(
            "INSERT INTO daily_bonus (user_id, last_claim, "INSERT INTO daily_bonus (user_id, last_claim, streak) VALUES ($1, $2, $3) streak) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET last_claim ON CONFLICT (user_id) DO UPDATE SET last_claim = $2, streak = $3",
            user = $2, streak = $3",
            user_id, current_time, streak
        )
    await_id, current_time, streak
        )
    await message.answer(f"🎁 <b>Еже message.answer(f"🎁 <b>Ежедневный бонус!</b>\n\nТыдневный бонус!</b>\n\nТы зашёл {streak} {pluralize(streak, зашёл {streak} {pluralize(streak, ['день', 'дня', 'дней'])} подряд ['день', 'дня', 'дней'])} подряд!\n💰 Получено: <b>{fmt_money!\n💰 Получено: <b>{fmt_money(bonus)}</b>", parse_mode="HTML")

@dp.message(Command("slots"))
async def cmd_slots(message(bonus)}</b>", parse_mode="HTML")

@dp.message(Command("slots"))
async def cmd_slots(message: Message):
    args = message.text.split()
: Message):
    args = message.text.split()
    if len(args) < 2: return await message    if len(args) < 2: return await message.answer("Укажите ставку: /slots 100.answer("Укажите ставку: /slots 100")
    try: bet = int(args[1])")
    try: bet = int(args[1])
    except: return await message.answer("Ставка должна
    except: return await message.answer("Ставка должна быть числом!")
    if bet < 10 быть числом!")
    if bet < 10: return await message.answer("Минимальная ставка:: return await message.answer("Минимальная ставка: 10 сарапулок")
    user 10 сарапулок")
    user_id = message.from_user.id
    user_bal = await_id = message.from_user.id
    user_bal = await get_user(user_id)
    if user_bal['balance get_user(user_id)
    if user_bal['balance'] < bet:
        return await message.answer(f"'] < bet:
        return await message.answer(f"❌ Недостаточно ({fmt_money(user_bal['balance❌ Недостаточно ({fmt_money(user_bal['balance'])})")
    await update_balance(user_id, -'])})")
    await update_balance(user_id, -bet)
    result = [random.choice(SLOTS_SYMBOLbet)
    result = [random.choice(SLOTS_SYMBOLS) for _ in range(3)]
    resultS) for _ in range(3)]
    result_str = ''.join(result)
    win_amount = _str = ''.join(result)
    win_amount = 0
    if result_str in SLOTS_PAYOUTS0
    if result_str in SLOTS_PAYOUTS:
        multiplier = SLOTS_PAYOUTS[result_str:
        multiplier = SLOTS_PAYOUTS[result_str]
        win_amount = bet * multiplier
        await]
        win_amount = bet * multiplier
        await update_balance(user_id, win_amount)
    text = update_balance(user_id, win_amount)
    text = f"🎰 <b>СЛОТЫ</ f"🎰 <b>СЛОТЫ</b>\n\nСтавка: {fmt_money(betb>\n\nСтавка: {fmt_money(bet)}\nРезультат: {' | '.join)}\nРезультат: {' | '.join(result)}\n\n"
    if win_amount >(result)}\n\n"
    if win_amount > 0:
        text += f"🎉 0:
        text += f"🎉 <b>ВЫИГРЫШ: {fmt <b>ВЫИГРЫШ: {fmt_money(win_amount)}</b> (x{SLOTS_P_money(win_amount)}</b> (x{SLOTS_PAYOUTS[result_str]})"
    else:
AYOUTS[result_str]})"
    else:
        text += "💀 Проигрыш. Попр        text += "💀 Проигрыш. Попробуй ещё раз!"
    await message.answer(text,обуй ещё раз!"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("buy parse_mode="HTML")

@dp.message(Command("buy_ticket"))
async def cmd_buy_ticket(message: Message):_ticket"))
async def cmd_buy_ticket(message: Message):
    user_id = message.from_user.id
    await
    user_id = message.from_user.id
    await save_username(user_id, message.from_user.full_name)
 save_username(user_id, message.from_user.full_name)
    user_bal = await get_user(user_id)
       user_bal = await get_user(user_id)
    ticket_price = 50
    if user_bal[' ticket_price = 50
    if user_bal['balance'] < ticket_price:
        return await message.answerbalance'] < ticket_price:
        return await message.answer(f"❌ Билет стоит {fmt_money(ticket(f"❌ Билет стоит {fmt_money(ticket_price)}")
    await update_balance(user_id, -_price)}")
    await update_balance(user_id, -ticket_price)
    today = time.strftime("%Y-%ticket_price)
    today = time.strftime("%Y-%m-%d")
    async with pool.acquire() asm-%d")
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO lottery_tickets conn:
        await conn.execute("INSERT INTO lottery_tickets (user_id, draw_date) VALUES ($1, $ (user_id, draw_date) VALUES ($1, $2)", user_id, today)
    await message.answer2)", user_id, today)
    await message.answer(f"🎟️ Вы купили лотер(f"🎟️ Вы купили лотерейный билет за {fmt_money(ticket_price)}!\nейный билет за {fmt_money(ticket_price)}!\nРозыгрыш: /lottery_draw (адРозыгрыш: /lottery_draw (админ)")

@dp.message(Command("lottery_draw"))мин)")

@dp.message(Command("lottery_draw"))
async def cmd_lottery_draw(message: Message):

async def cmd_lottery_draw(message: Message):
    if message.from_user.id not in ADMIN_IDS: return    if message.from_user.id not in ADMIN_IDS: return
    today = time.strftime("%Y-%m-%
    today = time.strftime("%Y-%m-%d")
    async with pool.acquire() as conn:d")
    async with pool.acquire() as conn:
        tickets = await conn.fetch("SELECT user_id FROM
        tickets = await conn.fetch("SELECT user_id FROM lottery_tickets WHERE draw_date = $1", today)
 lottery_tickets WHERE draw_date = $1", today)
        if not tickets: return await message.answer("Сегодня        if not tickets: return await message.answer("Сегодня никто не купил билеты!")
        winner_id = random никто не купил билеты!")
        winner_id = random.choice(tickets)['user_id']
        bank = len.choice(tickets)['user_id']
        bank = len(tickets) * 50
        await update_balance(tickets) * 50
        await update_balance(winner_id, bank)
        await conn.execute("(winner_id, bank)
        await conn.execute("DELETE FROM lottery_tickets WHERE draw_date = $1", todayDELETE FROM lottery_tickets WHERE draw_date = $1", today)
    winner_name = await get_username(winner_id)
    winner_name = await get_username(winner_id) or f"User{winner_id}"
    await) or f"User{winner_id}"
    await message.answer(f"🎊 <b>РОЗ message.answer(f"🎊 <b>РОЗЫГРЫШ ЛОТЕРЕИ!</b>\ЫГРЫШ ЛОТЕРЕИ!</b>\n\n🏆 Победитель: <b>{n\n🏆 Победитель: <b>{winner_name}</b>\n💰 Выигрыш:winner_name}</b>\n💰 Выигрыш: <b>{fmt_money(bank)}</b>\ <b>{fmt_money(bank)}</b>\n\nВсего участников: {len(tickets)}n\nВсего участников: {len(tickets)}", parse_mode="HTML")

@dp.message(Command("", parse_mode="HTML")

@dp.message(Command("info"))
async def cmd_info(message: Message):
info"))
async def cmd_info(message: Message):
    user_id = message.from_user.id
    await save    user_id = message.from_user.id
    await save_username(user_id, message.from_user.full_name)
   _username(user_id, message.from_user.full_name)
    user = await get_user(user_id)
    profile = user = await get_user(user_id)
    profile = await get_profile(user_id)
    car = await get await get_profile(user_id)
    car = await get_car(user_id)
    async with pool.acquire() as_car(user_id)
    async with pool.acquire() as conn:
        biz_count = await conn.fetchval(" conn:
        biz_count = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE user_id = $1",SELECT COUNT(*) FROM businesses WHERE user_id = $1", user_id)
        inv_count = await conn.fetchval user_id)
        inv_count = await conn.fetchval("SELECT COUNT(*) FROM inventory WHERE user_id = $1("SELECT COUNT(*) FROM inventory WHERE user_id = $1", user_id)
    job = JOBS[profile", user_id)
    job = JOBS[profile['job_key']]
    text = f"['job_key']]
    text = f" <b>Карточка игрока</b>\ <b>Карточка игрока</b>\n\n👤 <b>{message.from_user.fulln\n👤 <b>{message.from_user.full_name}</b>\n\n"
    text += f_name}</b>\n\n"
    text += f"💰 Баланс: <b>{fmt_money"💰 Баланс: <b>{fmt_money(user['balance'])}</b>\n"
   (user['balance'])}</b>\n"
    text += f"💼 Профессия: < text += f"💼 Профессия: <b>{job['name']}</b> (Ур.b>{job['name']}</b> (Ур. {profile['level']})\n"
    text {profile['level']})\n"
    text += f"🚗 Машина: <b>{ += f"🚗 Машина: <b>{car if car else 'нет'}</b>\n"car if car else 'нет'}</b>\n"
    text += f"🏢 Бизнес
    text += f"🏢 Бизнесов: <b>{biz_count}</b>\n"ов: <b>{biz_count}</b>\n"
    text += f"🎒 Предметов
    text += f"🎒 Предметов: <b>{inv_count}</b>\n"
: <b>{inv_count}</b>\n"
    if profile['has_coffee']: text += "    if profile['has_coffee']: text += " Кофе-машина: <b>есть Кофе-машина: <b>есть</b>\n"
    await message.answer(text,</b>\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("shop parse_mode="HTML")

@dp.message(Command("shop"))
async def cmd_shop(message: Message):
   "))
async def cmd_shop(message: Message):
    text = "🛒 <b>Улучшения text = "🛒 <b>Улучшения:</b>\n"
    for k, v in:</b>\n"
    for k, v in SHOP_ITEMS.items():
        text += f" SHOP_ITEMS.items():
        text += f" {v['name']} ({fmt_money(v['price {v['name']} ({fmt_money(v['price'])}) → /buy {k}\n"
   '])}) → /buy {k}\n"
    await message.answer(text, parse_mode="HTML")

@ await message.answer(text, parse_mode="HTML")

@dp.message(Command("buy"))
async def cmd_buy(messagedp.message(Command("buy"))
async def cmd_buy(message: Message):
    args = message.text.split()
: Message):
    args = message.text.split()
    if len(args) < 2 or args[1    if len(args) < 2 or args[1] not in SHOP_ITEMS: return await message.answer("/shop] not in SHOP_ITEMS: return await message.answer("/shop")
    item = SHOP_ITEMS[args[1]]
")
    item = SHOP_ITEMS[args[1]]
    user_id = message.from_user.id
    user =    user_id = message.from_user.id
    user = await get_user(user_id)
    if user['balance await get_user(user_id)
    if user['balance'] < item['price']: return await message.answer(f"'] < item['price']: return await message.answer(f"❌ Нужно {fmt_money(item['price'])}")
❌ Нужно {fmt_money(item['price'])}")
    await update_balance(user_id, -item['price'])    await update_balance(user_id, -item['price'])
    if item['type'] == 'level_up':
    if item['type'] == 'level_up':
        p = await get_profile(user_id)
       
        p = await get_profile(user_id)
        async with pool.acquire() as conn:
            await conn async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET level = $1 WHERE user_id.execute("UPDATE profiles SET level = $1 WHERE user_id = $2", p['level']+1, user_id = $2", p['level']+1, user_id)
        await message.answer(f"✅ Уровень повышен до)
        await message.answer(f"✅ Уровень повышен до {p['level']+1}!")
    elif item {p['level']+1}!")
    elif item['type'] == 'cooldown_reduce':
        async with['type'] == 'cooldown_reduce':
        async with pool.acquire() as conn:
            await conn.execute(" pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET has_coffee = TRUE WHERE user_id =UPDATE profiles SET has_coffee = TRUE WHERE user_id = $1", user_id)
        await message.answer(" $1", user_id)
        await message.answer("✅ Кофе куплен! Работа быстрее.")

@dp✅ Кофе куплен! Работа быстрее.")

@dp.message(Command("market"))
async def cmd_market(message:.message(Command("market"))
async def cmd_market(message: Message):
    text = "🏪 <b Message):
    text = "🏪 <b>Рынок:</b>\n"
    for>Рынок:</b>\n"
    for k, v in MARKET.items():
        text += f k, v in MARKET.items():
        text += f"🔹 {v['name']} ({fmt_money"🔹 {v['name']} ({fmt_money(v['price'])}) → /buy_market {k}\(v['price'])}) → /buy_market {k}\n"
    await message.answer(text, parse_mode="n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("buy_market"))
HTML")

@dp.message(Command("buy_market"))
async def cmd_buy_market(message: Message):
    argsasync def cmd_buy_market(message: Message):
    args = message.text.split()
    if len(args) < = message.text.split()
    if len(args) < 2 or args[1] not in MARKET: return 2 or args[1] not in MARKET: return await message.answer("/market")
    item = MARKET[args await message.answer("/market")
    item = MARKET[args[1]]
    user_id = message.from_user.id[1]]
    user_id = message.from_user.id
    user = await get_user(user_id)
   
    user = await get_user(user_id)
    if user['balance'] < item['price']: return await if user['balance'] < item['price']: return await message.answer(f"❌ Нужно {fmt_money(item[' message.answer(f"❌ Нужно {fmt_money(item['price'])}")
    await update_balance(user_id, -price'])}")
    await update_balance(user_id, -item['price'])
    if item['type'] ==item['price'])
    if item['type'] == 'case':
        rand = random.randint(1, 'case':
        rand = random.randint(1, 100)
        if rand <= 5 100)
        if rand <= 5: prize, rar = "🎸: prize, rar = "🎸 Золотая Скрипка", "legendary" Золотая Скрипка", "legendary"
        elif rand <= 25: prize, rar
        elif rand <= 25: prize, rar = "💎 Алмаз", "rare"
 = "💎 Алмаз", "rare"
        else: prize, rar = "📄 Б        else: prize, rar = "📄 Бумага", "common"
        async with pool.acquireумага", "common"
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO() as conn:
            await conn.execute("INSERT INTO inventory (user_id, item_name, item_type, rarity inventory (user_id, item_name, item_type, rarity) VALUES ($1, $2, 'card', $) VALUES ($1, $2, 'card', $3)", user_id, prize, rar)
        await3)", user_id, prize, rar)
        await message.answer(f"📦 Выпало: < message.answer(f"📦 Выпало: <b>{prize}</b> ({rar})", parse_modeb>{prize}</b> ({rar})", parse_mode="HTML")
    elif item['type'] == '="HTML")
    elif item['type'] == 'business':
        async with pool.acquire() as conn:business':
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO businesses (user_id
            await conn.execute("INSERT INTO businesses (user_id, business_name, income) VALUES ($1, $2, business_name, income) VALUES ($1, $2, $3)", user_id, item['name'], item, $3)", user_id, item['name'], item['income'])
        await message.answer(f"✅ К['income'])
        await message.answer(f"✅ Куплен <b>{item['name']}</b>. Жуплен <b>{item['name']}</b>. Жми /collect раз в сутки!", parse_mode="HTML")ми /collect раз в сутки!", parse_mode="HTML")

@dp.message(Command("collect"))
async def cmd

@dp.message(Command("collect"))
async def cmd_collect(message: Message):
    user_id = message.from_collect(message: Message):
    user_id = message.from_user.id
    now = time.time()
    total_user.id
    now = time.time()
    total = 0
    async with pool.acquire() as conn = 0
    async with pool.acquire() as conn:
        bizs = await conn.fetch("SELECT id:
        bizs = await conn.fetch("SELECT id, income, last_collect_time FROM businesses WHERE user_id =, income, last_collect_time FROM businesses WHERE user_id = $1", user_id)
        if not bizs $1", user_id)
        if not bizs: return await message.answer("Нет бизнеса.")
        for: return await message.answer("Нет бизнеса.")
        for biz in bizs:
            if now - biz[' biz in bizs:
            if now - biz['last_collect_time'] > 86400:last_collect_time'] > 86400:
                total += biz['income']
                await conn
                total += biz['income']
                await conn.execute("UPDATE businesses SET last_collect_time = $1 WHERE.execute("UPDATE businesses SET last_collect_time = $1 WHERE id = $2", now, biz['id'])
 id = $2", now, biz['id'])
    if total > 0:
        await update_balance    if total > 0:
        await update_balance(user_id, total)
        await message.answer(f"(user_id, total)
        await message.answer(f"💼 Прибыль: <b>+{fmt_money💼 Прибыль: <b>+{fmt_money(total)}</b>", parse_mode="HTML")
    else(total)}</b>", parse_mode="HTML")
    else:
        await message.answer("⏳ Р:
        await message.answer("⏳ Рано. Приходи завтра.")

@dp.message(Command("ано. Приходи завтра.")

@dp.message(Command("cars"))
async def cmd_cars(message: Message):cars"))
async def cmd_cars(message: Message):
    text = "🚗 <b>А
    text = "🚗 <b>Автосалон:</b>\n\n"
   втосалон:</b>\n\n"
    for k, v in CARS.items():
        text for k, v in CARS.items():
        text += f"🔸 <b>{v['name += f"🔸 <b>{v['name']}</b>\n   💰 {fmt_money(v['']}</b>\n   💰 {fmt_money(v['price'])}\n   <i>{v['desc']}</price'])}\n   <i>{v['desc']}</i>\n   Купить: <code>/buycari>\n   Купить: <code>/buycar {k}</code>\n\n"
    await message {k}</code>\n\n"
    await message.answer(text, parse_mode="HTML")

@dp.message.answer(text, parse_mode="HTML")

@dp.message(Command("buycar"))
async def cmd_bu(Command("buycar"))
async def cmd_buycar(message: Message):
    args = message.textycar(message: Message):
    args = message.text.split()
    if len(args) < 2 or.split()
    if len(args) < 2 or args[1] not in CARS: return await message args[1] not in CARS: return await message.answer("/cars")
    car_key = args[1.answer("/cars")
    car_key = args[1]
    car = CARS[car_key]
]
    car = CARS[car_key]
    user_id = message.from_user.id
    user =    user_id = message.from_user.id
    user = await get_user(user_id)
    if user['balance await get_user(user_id)
    if user['balance'] < car['price']: return await message.answer(f"'] < car['price']: return await message.answer(f"❌ Нужно {fmt_money(car['price'])}")
❌ Нужно {fmt_money(car['price'])}")
    await update_balance(user_id, -car['price'])    await update_balance(user_id, -car['price'])
    await set_car(user_id, car_key, car
    await set_car(user_id, car_key, car['name'])
    await message.answer(f"['name'])
    await message.answer(f" <b>КУПЛЕНО!</b>\n <b>КУПЛЕНО!</b>\nТеперь ты ездишь на <b>{carТеперь ты ездишь на <b>{car['name']}</b>!\nПроверь через /['name']}</b>!\nПроверь через /mycar", parse_mode="HTML")

@dp.messagemycar", parse_mode="HTML")

@dp.message(Command("mycar"))
async def cmd_mycar(Command("mycar"))
async def cmd_mycar(message: Message):
    car = await get_car(message(message: Message):
    car = await get_car(message.from_user.id)
    if car: await message.answer.from_user.id)
    if car: await message.answer(f"🅿️ Твой гараж:\n(f"🅿️ Твой гараж:\n🚗 <b>{car}</b>", parse_mode🚗 <b>{car}</b>", parse_mode="HTML")
    else: await message.answer("="HTML")
    else: await message.answer("️ Гараж пуст. Купи т️ Гараж пуст. Купи тачку в /cars!")

@dp.message(Command("ачку в /cars!")

@dp.message(Command("inv"))
async def cmd_inv(message: Message):
inv"))
async def cmd_inv(message: Message):
    async with pool.acquire() as conn:
        items    async with pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name, rarity FROM inventory = await conn.fetch("SELECT item_name, rarity FROM inventory WHERE user_id = $1", message.from_user.id) WHERE user_id = $1", message.from_user.id)
    if not items: return await message.answer("
    if not items: return await message.answer(" Пусто.")
    text = " Пусто.")
    text = " <b>Предметы:</b>\n <b>Предметы:</b>\n"
    for item in items:
        c ="
    for item in items:
        c = "🟡" if item['rarity']=="legend "🟡" if item['rarity']=="legendary" else "🔵" if item['rary" else "🔵" if item['rarity']=="rare" else "🟢"
arity']=="rare" else "🟢"
        text += f"{c} {item['item_name        text += f"{c} {item['item_name']}\n"
    await message.answer(text, parse']}\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("rating"))_mode="HTML")

@dp.message(Command("rating"))
async def cmd_rating(message: Message):
    async
async def cmd_rating(message: Message):
    async with pool.acquire() as conn:
        rows = await with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT u.user_id, u.balance conn.fetch("""
            SELECT u.user_id, u.balance, us.username 
            FROM users u 
            LEFT JOIN, us.username 
            FROM users u 
            LEFT JOIN usernames us ON u.user_id = us.user_id 
            usernames us ON u.user_id = us.user_id 
            ORDER BY u.balance DESC LIMIT 10
        "" ORDER BY u.balance DESC LIMIT 10
        """)
    
    text = "🏆 <b")
    
    text = "🏆 <b>Рейтинг богачей:</b>\n\n>Рейтинг богачей:</b>\n\n"
    for i, row in enumerate(rows, "
    for i, row in enumerate(rows, 1):
        display_name = row['username'] if1):
        display_name = row['username'] if row['username'] else f"User{row['user row['username'] else f"User{row['user_id']}"
        text += f"{i}. <_id']}"
        text += f"{i}. <b>{display_name}</b> — {fmt_money(rowb>{display_name}</b> — {fmt_money(row['balance'])}\n"
    
    await message.answer['balance'])}\n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(Command(text, parse_mode="HTML")

@dp.message(Command("give"))
async def cmd_give(message: Message("give"))
async def cmd_give(message: Message):
    if message.from_user.id not in ADMIN_IDS):
    if message.from_user.id not in ADMIN_IDS: return
    args = message.text.split()
   : return
    args = message.text.split()
    if len(args) < 2 or not message.reply_to if len(args) < 2 or not message.reply_to_message: return await message.answer("/give сумма (ответ)")_message: return await message.answer("/give сумма (ответ)")
    try: amount = int(args[1])

    try: amount = int(args[1])
    except: return await message.answer("Число!")
    except: return await message.answer("Число!")
    await update_balance(message.reply_to_message.from_user.id,    await update_balance(message.reply_to_message.from_user.id, amount)
    await save_username(message.reply_to_message.from amount)
    await save_username(message.reply_to_message.from_user.id, message.reply_to_message.from_user.full_name)_user.id, message.reply_to_message.from_user.full_name)
    await message.answer(f"✅ Выдано {
    await message.answer(f"✅ Выдано {fmt_money(amount)}.")

# ==================== БЛfmt_money(amount)}.")

# ==================== БЛЭКДЖЕК С ИГОРЁЧКОМЭКДЖЕК С ИГОРЁЧКОМ (УПРОЩЁННЫЙ) ================= (УПРОЩЁННЫЙ) ====================
@dp.message(Command("blackjack"))
async===
@dp.message(Command("blackjack"))
async def cmd_blackjack(message: Message):
    user_id def cmd_blackjack(message: Message):
    user_id = message.from_user.id
    user = await get_user = message.from_user.id
    user = await get_user(user_id)
    
    if user['balance'] <(user_id)
    
    if user['balance'] < 100:
        return await message.answer(f 100:
        return await message.answer(f"❌ Для игры нужно минимум 10"❌ Для игры нужно минимум 100 сарапулек!\nУ тебя0 сарапулек!\nУ тебя: {fmt_money(user['balance'])}")
    
   : {fmt_money(user['balance'])}")
    
    # Списываем ставку
    bet =  # Списываем ставку
    bet = 100
    await update_balance(user_id, -100
    await update_balance(user_id, -bet)
    
    # Создаём колоду
   bet)
    
    # Создаём колоду
    suits = ['♠', '♥', '♦', suits = ['♠', '♥', '♦', '♣']
    ranks = ['2','3 '♣']
    ranks = ['2','3','4','5','6','7','8','9','4','5','6','7','8','9','10','J','Q','K','A']','10','J','Q','K','A']
    deck = [(r, s) for s in
    deck = [(r, s) for s in suits for r in ranks]
    random.shuffle(deck) suits for r in ranks]
    random.shuffle(deck)
    
    # Раздаём карты
    player_cards
    
    # Раздаём карты
    player_cards = [deck.pop(), deck.pop()]
    = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]
    
 dealer_cards = [deck.pop(), deck.pop()]
    
    def card_value(card):
        r = card[    def card_value(card):
        r = card[0]
        if r in ['J','Q','0]
        if r in ['J','Q','K']: return 10
        if r == 'K']: return 10
        if r == 'A': return 11
        return int(r)A': return 11
        return int(r)
    
    def calc_score(cards):
        score =
    
    def calc_score(cards):
        score = sum(card_value(c) for c in cards)
        sum(card_value(c) for c in cards)
        aces = sum(1 for c in cards if c aces = sum(1 for c in cards if c[0] == 'A')
        while score >[0] == 'A')
        while score > 21 and aces > 0:
            21 and aces > 0:
            score -= 10
            aces -= 1 score -= 10
            aces -= 1
        return score
    
    def show_cards(cards,
        return score
    
    def show_cards(cards, hide_first=False):
        if hide_first:
            hide_first=False):
        if hide_first:
            return f"🂠 + {' '.join(f'{ return f"🂠 + {' '.join(f'{r}{s}' for r,s in cards[1:])r}{s}' for r,s in cards[1:])}"
        return ' '.join(f'{r}{s}"
        return ' '.join(f'{r}{s}' for r,s in cards)
    
    player_score}' for r,s in cards)
    
    player_score = calc_score(player_cards)
    dealer_score = calc = calc_score(player_cards)
    dealer_score = calc_score(dealer_cards)
    
    # Д_score(dealer_cards)
    
    # Дилер берёт карты до 17
    whileилер берёт карты до 17
    while dealer_score < 17:
        dealer dealer_score < 17:
        dealer_cards.append(deck.pop())
        dealer_score = calc_score_cards.append(deck.pop())
        dealer_score = calc_score(dealer_cards)
    
    # Определяем(dealer_cards)
    
    # Определяем победителя
    if player_score > 21:
        result = "💀 победителя
    if player_score > 21:
        result = "💀 <b>ПЕРЕБОР!</b> Игорё <b>ПЕРЕБОР!</b> Игорёчек забирает ставку."
    elif dealer_score >чек забирает ставку."
    elif dealer_score > 21:
        result = " 21:
        result = "🎉 <b>Игорёчек перебр🎉 <b>Игорёчек перебрал!</b> Ты выиграл!"
        awaitал!</b> Ты выиграл!"
        await update_balance(user_id, bet * 2)
    update_balance(user_id, bet * 2)
    elif player_score > dealer_score:
        result = " elif player_score > dealer_score:
        result = "🏆 <b>Победа!</b🏆 <b>Победа!</b> Ты обыграл Игорёчка!"
> Ты обыграл Игорёчка!"
        await update_balance(user_id, bet * 2)        await update_balance(user_id, bet * 2)
    elif player_score == dealer_score:
        result
    elif player_score == dealer_score:
        result = "🤝 <b>Нич = "🤝 <b>Ничья!</b> Ставка возвращена."
       ья!</b> Ставка возвращена."
        await update_balance(user_id, bet)
    else: await update_balance(user_id, bet)
    else:
        result = "😢 <b>Проигры
        result = "😢 <b>Проигрыш.</b> Игорёчек забирает ставку."ш.</b> Игорёчек забирает ставку."
    
    await message.answer(
        f"
    
    await message.answer(
        f" <b>Блэкджек с <b>Блэкджек с Игорёчком</b>\n\n"
        f Игорёчком</b>\n\n"
        f"👤 Твои карты:"👤 Твои карты: {show_cards(player_cards)} ({player_score})\ {show_cards(player_cards)} ({player_score})\n"
        f"🤖 Кn"
        f"🤖 Карты Игорёчка: {show_cards(dealer_cardsарты Игорёчка: {show_cards(dealer_cards)} ({dealer_score})\n\n"
        f)} ({dealer_score})\n\n"
        f"💰 Ставка: {fmt_money"💰 Ставка: {fmt_money(bet)}\n\n"
        f"{result(bet)}\n\n"
        f"{result}",
        parse_mode="HTML"
    )

}",
        parse_mode="HTML"
    )

# ==================== АВТО-РЕГИСТРА# ==================== АВТО-РЕГИСТРАЦИЯ ====================
@dp.message()
async def autoЦИЯ ====================
@dp.message()
async def auto_register(message: Message):
    if message.chat.type not_register(message: Message):
    if message.chat.type not in ['group', 'supergroup']: return
    in ['group', 'supergroup']: return
    user_id = message.from_user.id
    await get_user user_id = message.from_user.id
    await get_user(user_id)

# ==================== ЗАПУСК ====================(user_id)

# ==================== ЗАПУСК ====================
async def main():
    await init_db()

async def main():
    await init_db()
    print("🤖 Бот запущен!    print("🤖 Бот запущен! Валюта: Сарапулки")
    asyncio.create Валюта: Сарапулки")
    asyncio.create_task(start_web_server())
    await dp.start_polling_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":(bot)

if __name__ == "__main__":
    asyncio.run(main())
