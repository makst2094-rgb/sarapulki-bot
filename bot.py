import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncpg
from aiohttp import web
import os

# ==================== НАСТРОЙКИ ====================
API_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]
DATABASE_URL = os.environ.get("DATABASE_URL", "")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
pool = None

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
    "course": {"name": "📚 Курсы", "price": 500, "desc": "+1 уровень профессии", "type": "level_up"},
    "coffee": {"name": "☕ Кофе-машина", "price": 1000, "desc": "-10% время отдыха", "type": "cooldown_reduce"}
}

MARKET = {
    "case_basic": {"name": "📦 Обычный кейс", "price": 200, "type": "case"},
    "biz_shawarma": {"name": "🌯 Ларёк с шаурмой", "price": 2000, "type": "business", "income": 150},
    "biz_crypto": {"name": "💻 Крипто-ферма", "price": 15000, "type": "business", "income": 1200}
}

CARS = {
    "ok": {"name": "🚲 Ока", "price": 3000, "desc": "Едет и едет."},
    "priora": {"name": "🚘 Приора", "price": 10000, "desc": "Музыка громче двигателя."},
    "bmw": {"name": "🏎️ BMW X5", "price": 40000, "desc": "Для важных дел."},
    "gelik": {"name": "🚙 Гелик", "price": 80000, "desc": "Черный, тонированный."},
    "lambo": {"name": " Lamborghini", "price": 200000, "desc": "Король дороги."}
}

SLOTS_SYMBOLS = ['', '🍋', '🍊', '🍇', '💎', '7️⃣']
SLOTS_PAYOUTS = {
    '7️7️7️⃣': 10,
    '💎💎💎': 5,
    '🍇🍇': 3,
    '🍊': 2,
    '🍋🍋': 2,
    '🍒🍒': 2
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
                business_name TEXT, 
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
        await conn.execute("INSERT INTO users (user_id) VALUES ($1)", user_id)
        return {"balance": 0}

async def update_balance(user_id: int, amount: int):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", amount, user_id)

async def get_profile(user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT job_key, level, last_work_time, has_coffee FROM profiles WHERE user_id = $1", 
            user_id
        )
        if not row:
            await conn.execute("INSERT INTO profiles (user_id) VALUES ($1)", user_id)
            return {"job_key": "novice", "level": 1, "last_work_time": 0, "has_coffee": False}
        return dict(row)

async def set_car(user_id: int, car_key: str, car_name: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO garage (user_id, car_key, car_name) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET car_key = $2, car_name = $3",
            user_id, car_key, car_name
        )

async def get_car(user_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT car_name FROM garage WHERE user_id = $1", user_id)

# ==================== ВЕБ-СЕРВЕР ====================
async def handle_ping(request):
    return web.Response(text="Bot is alive! ")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("✅ Web server started on port 8080")

# ==================== КОМАНДЫ ЭКОНОМИКИ ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await save_username(message.from_user.id, message.from_user.full_name)
    
    await message.answer(
        " <b>Экономика группы</b>\n\n"
        "💰 /balance - мои сарапулки\n"
        "💼 /work - работать\n"
        "💸 /pay - перевести (ответь на сообщение)\n"
        "🔫 /rob - ограбить (ответь на сообщение)\n"
        "🎁 /daily - ежедневный бонус\n"
        "🎰 /slots ставка - казино\n"
        "🎟️ /buy_ticket - лотерейный билет\n"
        " /shop - улучшения\n"
        " /market - бизнесы и кейсы\n"
        "🚗 /cars - автосалон\n"
        "️ /mycar - моя тачка\n"
        "💼 /collect - прибыль с бизнеса\n"
        " /inv - инвентарь\n"
        "📊 /info - моя карточка\n"
        " /rating - рейтинг богачей\n"
        "🃏 /blackjack - Блэкджек с Игорёчком"
    )

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    await save_username(message.from_user.id, message.from_user.full_name)
    user = await get_user(message.from_user.id)
    car = await get_car(message.from_user.id)
    car_text = f"\n🚗 Тачка: {car}" if car else "\n Тачка: нет (/cars)"
    await message.answer(f"💰 Баланс: <b>{fmt_money(user['balance'])}</b>{car_text}", parse_mode="HTML")

@dp.message(Command("work"))
async def cmd_work(message: Message):
    await save_username(message.from_user.id, message.from_user.full_name)
    user_id = message.from_user.id
    profile = await get_profile(user_id)
    job = JOBS[profile['job_key']]
    current_time = time.time()
    cooldown = job['cooldown'] * (0.9 if profile['has_coffee'] else 1.0)
    time_passed = current_time - profile['last_work_time']
    if time_passed < cooldown:
        remaining = int(cooldown - time_passed)
        return await message.answer(f" Отдыхайте еще {remaining // 60} мин.")
    salary = job['base_pay'] * profile['level'] + random.randint(0, 5)
    await update_balance(user_id, salary)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET last_work_time = $1 WHERE user_id = $2", current_time, user_id)
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
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET job_key = $1 WHERE user_id = $2", args[1], message.from_user.id)
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
    await save_username(receiver_id, message.reply_to_message.from_user.full_name)
    await message.answer(f"✅ <b>{message.from_user.full_name}</b> перевёл <b>{fmt_money(amount)}</b> пользователю <b>{message.reply_to_message.from_user.full_name}</b>", parse_mode="HTML")

@dp.message(Command("rob"))
async def cmd_rob(message: Message):
    if not message.reply_to_message:
        return await message.answer("Ответьте на сообщение жертвы!")
    robber_id = message.from_user.id
    victim_id = message.reply_to_message.from_user.id
    if robber_id == victim_id: return await message.answer("Нельзя ограбить самого себя!")
    async with pool.acquire() as conn:
        last_rob = await conn.fetchval("SELECT last_robbery FROM robbery WHERE user_id = $1", robber_id)
        last_rob = last_rob or 0
        current_time = time.time()
        if current_time - last_rob < 10800:
            remaining = int(10800 - (current_time - last_rob))
            return await message.answer(f" Отдыхайте еще {remaining // 3600} ч.")
        await conn.execute(
            "INSERT INTO robbery (user_id, last_robbery) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET last_robbery = $2",
            robber_id, current_time
        )
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
        await message.answer(f" <b>ПОПАЛСЯ!</b>\n\n{message.from_user.full_name} заплатил штраф <b>{fmt_money(penalty)}</b> пользователю {message.reply_to_message.from_user.full_name}!", parse_mode="HTML")

@dp.message(Command("daily"))
async def cmd_daily(message: Message):
    user_id = message.from_user.id
    await save_username(user_id, message.from_user.full_name)
    current_time = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT last_claim, streak FROM daily_bonus WHERE user_id = $1", user_id)
        last_claim, streak = (row['last_claim'], row['streak']) if row else (0, 0)
        if current_time - last_claim < 86400:
            remaining = int(86400 - (current_time - last_claim))
            return await message.answer(f" Приходи через {remaining // 3600} ч. {remaining % 3600 // 60} мин.")
        if current_time - last_claim < 172800: streak += 1
        else: streak = 1
        base_bonus = random.randint(100, 300)
        multiplier = min(streak, 7)
        bonus = base_bonus * multiplier
        await update_balance(user_id, bonus)
        await conn.execute(
            "INSERT INTO daily_bonus (user_id, last_claim, streak) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET last_claim = $2, streak = $3",
            user_id, current_time, streak
        )
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
    await save_username(user_id, message.from_user.full_name)
    user_bal = await get_user(user_id)
    ticket_price = 50
    if user_bal['balance'] < ticket_price:
        return await message.answer(f"❌ Билет стоит {fmt_money(ticket_price)}")
    await update_balance(user_id, -ticket_price)
    today = time.strftime("%Y-%m-%d")
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO lottery_tickets (user_id, draw_date) VALUES ($1, $2)", user_id, today)
    await message.answer(f"🎟️ Вы купили лотерейный билет за {fmt_money(ticket_price)}!\nРозыгрыш: /lottery_draw (админ)")

@dp.message(Command("lottery_draw"))
async def cmd_lottery_draw(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    today = time.strftime("%Y-%m-%d")
    async with pool.acquire() as conn:
        tickets = await conn.fetch("SELECT user_id FROM lottery_tickets WHERE draw_date = $1", today)
        if not tickets: return await message.answer("Сегодня никто не купил билеты!")
        winner_id = random.choice(tickets)['user_id']
        bank = len(tickets) * 50
        await update_balance(winner_id, bank)
        await conn.execute("DELETE FROM lottery_tickets WHERE draw_date = $1", today)
    winner_name = await get_username(winner_id) or f"User{winner_id}"
    await message.answer(f"🎊 <b>РОЗЫГРЫШ ЛОТЕРЕИ!</b>\n\n Победитель: <b>{winner_name}</b>\n💰 Выигрыш: <b>{fmt_money(bank)}</b>\n\nВсего участников: {len(tickets)}", parse_mode="HTML")

@dp.message(Command("info"))
async def cmd_info(message: Message):
    user_id = message.from_user.id
    await save_username(user_id, message.from_user.full_name)
    user = await get_user(user_id)
    profile = await get_profile(user_id)
    car = await get_car(user_id)
    async with pool.acquire() as conn:
        biz_count = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE user_id = $1", user_id)
        inv_count = await conn.fetchval("SELECT COUNT(*) FROM inventory WHERE user_id = $1", user_id)
    job = JOBS[profile['job_key']]
    text = f"📊 <b>Карточка игрока</b>\n\n👤 <b>{message.from_user.full_name}</b>\n\n"
    text += f"💰 Баланс: <b>{fmt_money(user['balance'])}</b>\n"
    text += f"💼 Профессия: <b>{job['name']}</b> (Ур. {profile['level']})\n"
    text += f"🚗 Машина: <b>{car if car else 'нет'}</b>\n"
    text += f" Бизнесов: <b>{biz_count}</b>\n"
    text += f"🎒 Предметов: <b>{inv_count}</b>\n"
    if profile['has_coffee']: text += "☕ Кофе-машина: <b>есть</b>\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    text = "🛒 <b>Улучшения:</b>\n"
    for k, v in SHOP_ITEMS.items():
        text += f" {v['name']} ({fmt_money(v['price'])}) → /buy {k}\n"
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
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET level = $1 WHERE user_id = $2", p['level']+1, user_id)
        await message.answer(f"✅ Уровень повышен до {p['level']+1}!")
    elif item['type'] == 'cooldown_reduce':
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET has_coffee = TRUE WHERE user_id = $1", user_id)
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
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO inventory (user_id, item_name, item_type, rarity) VALUES ($1, $2, 'card', $3)", user_id, prize, rar)
        await message.answer(f"📦 Выпало: <b>{prize}</b> ({rar})", parse_mode="HTML")
    elif item['type'] == 'business':
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO businesses (user_id, business_name, income) VALUES ($1, $2, $3)", user_id, item['name'], item['income'])
        await message.answer(f"✅ Куплен <b>{item['name']}</b>. Жми /collect раз в сутки!", parse_mode="HTML")

@dp.message(Command("collect"))
async def cmd_collect(message: Message):
    user_id = message.from_user.id
    now = time.time()
    total = 0
    async with pool.acquire() as conn:
        bizs = await conn.fetch("SELECT id, income, last_collect_time FROM businesses WHERE user_id = $1", user_id)
        if not bizs: return await message.answer("Нет бизнеса.")
        for biz in bizs:
            if now - biz['last_collect_time'] > 86400:
                total += biz['income']
                await conn.execute("UPDATE businesses SET last_collect_time = $1 WHERE id = $2", now, biz['id'])
    if total > 0:
        await update_balance(user_id, total)
        await message.answer(f"💼 Прибыль: <b>+{fmt_money(total)}</b>", parse_mode="HTML")
    else:
        await message.answer(" Рано. Приходи завтра.")

@dp.message(Command("cars"))
async def cmd_cars(message: Message):
    text = "🚗 <b>Автосалон:</b>\n\n"
    for k, v in CARS.items():
        text += f"🔸 <b>{v['name']}</b>\n   💰 {fmt_money(v['price'])}\n   <i>{v['desc']}</i>\n   Купить: <code>/buycar {k}</code>\n\n"
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
    await message.answer(f" <b>КУПЛЕНО!</b>\nТеперь ты ездишь на <b>{car['name']}</b>!\nПроверь через /mycar", parse_mode="HTML")

@dp.message(Command("mycar"))
async def cmd_mycar(message: Message):
    car = await get_car(message.from_user.id)
    if car: await message.answer(f"🅿️ Твой гараж:\n🚗 <b>{car}</b>", parse_mode="HTML")
    else: await message.answer("🅿️ Гараж пуст. Купи тачку в /cars!")

@dp.message(Command("inv"))
async def cmd_inv(message: Message):
    async with pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name, rarity FROM inventory WHERE user_id = $1", message.from_user.id)
    if not items: return await message.answer("🎒 Пусто.")
    text = "🎒 <b>Предметы:</b>\n"
    for item in items:
        c = "🟡" if item['rarity']=="legendary" else "🔵" if item['rarity']=="rare" else "🟢"
        text += f"{c} {item['item_name']}\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("rating"))
async def cmd_rating(message: Message):
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT u.user_id, u.balance, us.username 
            FROM users u 
            LEFT JOIN usernames us ON u.user_id = us.user_id 
            ORDER BY u.balance DESC LIMIT 10
        """)
    
    text = "🏆 <b>Рейтинг богачей:</b>\n\n"
    for i, row in enumerate(rows, 1):
        display_name = row['username'] if row['username'] else f"User{row['user_id']}"
        text += f"{i}. <b>{display_name}</b> — {fmt_money(row['balance'])}\n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("give"))
async def cmd_give(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    args = message.text.split()
    if len(args) < 2 or not message.reply_to_message: return await message.answer("/give сумма (ответ)")
    try: amount = int(args[1])
    except: return await message.answer("Число!")
    await update_balance(message.reply_to_message.from_user.id, amount)
    await save_username(message.reply_to_message.from_user.id, message.reply_to_message.from_user.full_name)
    await message.answer(f"✅ Выдано {fmt_money(amount)}.")

# ==================== АВТО-РЕГИСТРАЦИЯ ====================
@dp.message()
async def auto_register(message: Message):
    if message.chat.type not in ['group', 'supergroup']: return
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    chat_id = message.chat.id
    
    # Проверяем, есть ли пользователь в базе
    user = await get_user(user_id)
    # Если баланс 0 и это первое сообщение, можно добавить приветствие,
    # но чтобы не спамить, просто регистрируем молча или один раз.
    # В данном случае get_user уже создает запись, если её нет.

# ==================== БЛЭКДЖЕК С ИГОРЁЧКОМ ====================

class BJStates(StatesGroup):
    waiting = State()
    betting = State()
    playing = State()

bj_tables = {}

IGOR_PHRASES = {
    "greeting": [" Йоу, братва! Игорёчек на связи!", " Привет! Ваш Игорёчек готов раздавать!"],
    "hit": [" Игорёчек раздаёт карту...", " Держи, не благодари!"],
    "stand": ["✋ Остановился? Смелое решение!", " Хм, Игорёчек запоминает..."],
    "bust": [" Перебор! Игорёчек сочувствует...", " Сгорел! Ставки ушли Игорёчку!"],
    "dealer_bust": ["😱 О нет! Игорёчек перебрал! Вы выиграли!", "‍♂️ Блин, Игорёчек сегодня не в форме!"],
    "player_win": [" Поздравляю! Вы обыграли Игорёчка!", " Забирайте выигрыш!"],
    "dealer_win": [" Игорёчек забирает ставки!", "😏 Игорёчек сегодня в ударе!"],
    "push": [" Ничья! Ставки возвращаются."],
    "blackjack": [" БЛЭКДЖЕК! Игорёчек в восторге!"]
}

def igor_says(category):
    return random.choice(IGOR_PHRASES[category])

def create_deck():
    suits = ['♠', '♥', '♦', '♣']
    ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
    deck = [(r, s) for s in suits for r in ranks]
    random.shuffle(deck)
    return deck

def card_value(card):
    r = card[0]
    if r in ['J','Q','K']: return 10
    if r == 'A': return 11
    return int(r)

def calc_score(cards):
    score = sum(card_value(c) for c in cards)
    aces = sum(1 for c in cards if c[0] == 'A')
    while score > 21 and aces > 0:
        score -= 10
        aces -= 1
    return score

def show_cards(cards, hide_first=False):
    if hide_first:
        return f"🂠 + {' '.join(f'{r}{s}' for r,s in cards[1:])}"
    return ' '.join(f'{r}{s}' for r,s in cards)

@dp.message(Command("blackjack"))
async def start_blackjack(message: Message, state: FSMContext):
    chat_id = message.chat.id
    if chat_id in bj_tables:
        await message.answer(" Игорёчек уже ведёт игру!"); return
    
    bj_tables[chat_id] = {
        "players": {message.from_user.id: {"name": message.from_user.first_name, "bet": 0, "cards": [], "stand": False}},
        "order": [message.from_user.id]
    }
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Присоединиться (/join)", callback_data="bj_join")]])
    await message.answer(
        f" {igor_says('greeting')}\n\n🃏 <b>Стол открыт!</b>\n⏳ Сбор игроков — 60 сек\n\n"
        f"Нажмите кнопку или напишите /join, чтобы сесть за стол!", reply_markup=kb, parse_mode="HTML"
    )
    await state.set_state(BJStates.waiting)
    await asyncio.sleep(60)
    
    if chat_id not in bj_tables: return
    table = bj_tables[chat_id]
    if len(table["players"]) < 2:
        await message.answer("😔 Недостаточно игроков. Стол закрыт.")
        del bj_tables[chat_id]; await state.clear(); return
    
    await message.answer(f" <b>Игорёчек:</b> Отлично! Делайте ставки!\n\n"
                         f"Участники: {', '.join(p['name'] for p in table['players'].values())}", parse_mode="HTML")
    await state.set_state(BJStates.betting)
    
    bets_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50", callback_data="bet_50"), InlineKeyboardButton(text="100", callback_data="bet_100"), InlineKeyboardButton(text="200", callback_data="bet_200")],
        [InlineKeyboardButton(text="500", callback_data="bet_500"), InlineKeyboardButton(text="1000", callback_data="bet_1000")]
    ])
    for uid in table["order"]:
        try: await message.bot.send_message(uid, "💰 Ваша ставка:", reply_markup=bets_kb)
        except: await message.answer(f"⚠️ {table['players'][uid]['name']}, напишите боту в личку для ставки!")

@dp.callback_query(lambda c: c.data == "bj_join")
async def join_table(callback: types.CallbackQuery):
    chat_id, uid = callback.message.chat.id, callback.from_user.id
    if chat_id not in bj_tables: await callback.answer("Стол закрыт!", show_alert=True); return
    table = bj_tables[chat_id]
    if uid in table["players"]: await callback.answer("Вы уже в игре!", show_alert=True); return
    if len(table["players"]) >= 5: await callback.answer("Мест нет!", show_alert=True); return
    
    table["players"][uid] = {"name": callback.from_user.first_name, "bet": 0, "cards": [], "stand": False}
    table["order"].append(uid)
    await callback.answer(f"✅ {igor_says('greeting')}")
    
    players_list = "\n".join([f"• {p['name']}" for p in table["players"].values()])
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Присоединиться (/join)", callback_data="bj_join")]])
    try:
        await callback.message.edit_text(f" {igor_says('greeting')}\n\n📋 <b>Стол!</b>\n{players_list}\n⏳ Ожидание...", reply_markup=kb, parse_mode="HTML")
    except: pass

@dp.callback_query(lambda c: c.data.startswith("bet_"))
async def place_bet(callback: types.CallbackQuery, state: FSMContext):
    bet = int(callback.data.split("_")[1])
    uid, chat_id = callback.from_user.id, callback.message.chat.id
    if chat_id not in bj_tables: return
    table = bj_tables[chat_id]
    player = table["players"].get(uid)
    if not player: return
    
    user = await get_user(uid)
    if not user or user['balance'] < bet:
        await callback.answer(f"Мало сарапулек! Баланс: {fmt_money(user['balance'] if user else 0)}", show_alert=True); return
    
    await update_balance(uid, -bet)
    player["bet"] = bet
    await callback.message.edit_text(f"✅ Ставка {bet} принята! Ждём остальных...")
    
    if all(p["bet"] > 0 for p in table["players"].values()):
        await deal_cards(callback.bot, chat_id, state)

async def deal_cards(bot, chat_id, state):
    table = bj_tables[chat_id]
    table["deck"] = create_deck()
    for uid in table["order"]:
        p = table["players"][uid]
        p["cards"] = [table["deck"].pop(), table["deck"].pop()]
    table["dealer"] = [table["deck"].pop(), table["deck"].pop()]
    
    players_info = "\n".join([f"👤 {p['name']}: ставка {p['bet']}" for p in table["players"].values()])
    await bot.send_message(chat_id, f"🎩 <b>Игорёчек:</b> Карты розданы!\n\n"
                           f" Мои карты: {show_cards(table['dealer'], hide_first=True)}\n\n{players_info}\n\n"
                           f"🎮 Ходит: {table['players'][table['order'][0]]['name']}", parse_mode="HTML")
    await state.set_state(BJStates.playing)
    await player_turn(bot, chat_id, state, table["order"][0])

async def player_turn(bot, chat_id, state, uid):
    table = bj_tables[chat_id]
    p = table["players"][uid]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Ещё (/hit)", callback_data=f"hit_{uid}"), InlineKeyboardButton(text="✋ Хватит (/stand)", callback_data=f"stand_{uid}")]
    ])
    await bot.send_message(uid, f"🎩 <b>Игорёчек:</b> Ваш ход!\n\n"
                           f" Ваши карты: {show_cards(p['cards'])}\n🔢 Сумма: {calc_score(p['cards'])}\n"
                           f" Ставка: {p['bet']}\n\n🤖 Карта Игорёчка: {table['dealer'][0][0]}{table['dealer'][0][1]}", 
                           reply_markup=kb, parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith("hit_") or c.data.startswith("stand_"))
async def hit_stand(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    action, uid = parts[0], int(parts[1])
    chat_id = callback.message.chat.id
    if chat_id not in bj_tables: return
    table = bj_tables[chat_id]
    p = table["players"][uid]
    
    if action == "hit":
        card = table["deck"].pop()
        p["cards"].append(card)
        score = calc_score(p["cards"])
        await callback.message.edit_text(f"🎩 {igor_says('hit')}\n\n Вы взяли: {card[0]}{card[1]}\n Карты: {show_cards(p['cards'])}\n🔢 Сумма: {score}")
        
        if score > 21:
            p["stand"] = True; await callback.message.answer(f"💥 {igor_says('bust')}"); await next_turn(callback.bot, chat_id, state)
        elif score == 21:
            p["stand"] = True; await callback.message.answer(f"🎉 {igor_says('blackjack')}"); await next_turn(callback.bot, chat_id, state)
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🃏 Ещё (/hit)", callback_data=f"hit_{uid}"), InlineKeyboardButton(text="✋ Хватит (/stand)", callback_data=f"stand_{uid}")]])
            await callback.message.answer(f" Сумма: {score}. Ещё?", reply_markup=kb)
    elif action == "stand":
        p["stand"] = True
        await callback.message.edit_text(f" {igor_says('stand')} Сумма: {calc_score(p['cards'])}")
        await next_turn(callback.bot, chat_id, state)

async def next_turn(bot, chat_id, state):
    table = bj_tables[chat_id]
    next_uid = next((uid for uid in table["order"] if not table["players"][uid]["stand"]), None)
    if next_uid: await player_turn(bot, chat_id, state, next_uid)
    else: await dealer_play(bot, chat_id, state)

async def dealer_play(bot, chat_id, state):
    table = bj_tables[chat_id]
    await bot.send_message(chat_id, f"🎩 <b>Игорёчек:</b> Теперь мой ход!\n\n Мои карты: {show_cards(table['dealer'])}", parse_mode="HTML")
    
    while calc_score(table["dealer"]) < 17:
        await asyncio.sleep(1)
        card = table["deck"].pop()
        table["dealer"].append(card)
        await bot.send_message(chat_id, f" {igor_says('hit')}\n + {card[0]}{card[1]} → сумма: {calc_score(table['dealer'])}")
    
    dealer_score = calc_score(table["dealer"])
    results = []
    for uid in table["order"]:
        p = table["players"][uid]
        ps, bet = calc_score(p["cards"]), p["bet"]
        user = await get_user(uid)
        
        if ps > 21: results.append(f" {p['name']}: перебор ({ps})")
        elif dealer_score > 21:
            await update_balance(uid, bet * 2); results.append(f"🎉 {p['name']}: Игорёчек перебрал! +{bet}")
        elif ps > dealer_score:
            await update_balance(uid, bet * 2); results.append(f"🏆 {p['name']}: победа! +{bet}")
        elif ps == dealer_score:
            await update_balance(uid, bet); results.append(f" {p['name']}: ничья")
        else: results.append(f" {p['name']}: проигрыш")
    
    final_phrase = igor_says("dealer_bust") if dealer_score > 21 else igor_says("player_win") if any("победа" in r or "перебрал" in r for r in results) else igor_says("dealer_win") if any("проигрыш" in r for r in results) else igor_says("push")
    
    await bot.send_message(chat_id, f" <b>Игорёчек:</b> {final_phrase}\n\n🤖 Карты Игорёчка: {show_cards(table['dealer'])} ({dealer_score})\n\n📊 Результаты:\n" + "\n".join(results), parse_mode="HTML")
    del bj_tables[chat_id]; await state.clear()

# ==================== ЗАПУСК ====================
async def main():
    await init_db()
    print(" Бот запущен! Валюта: Сарапулки")
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
