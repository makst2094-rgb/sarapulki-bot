import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncpg
from aiohttp import web
import os

API_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]
DATABASE_URL = os.environ.get("DATABASE_URL", "")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
pool = None

class BJStates(StatesGroup):
    waiting = State()
    betting = State()
    playing = State()

bj_tables = {}

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

JOBS = {
    "novice": {"name": "Новичок", "base_pay": 10, "cooldown": 3600},
    "miner": {"name": "Шахтёр", "base_pay": 25, "cooldown": 3600},
    "coder": {"name": "Программист", "base_pay": 50, "cooldown": 7200},
    "trader": {"name": "Трейдер", "base_pay": 80, "cooldown": 10800}
}

SHOP_ITEMS = {
    "course": {"name": "Курсы", "price": 500, "desc": "+1 уровень профессии", "type": "level_up"},
    "coffee": {"name": "Кофе-машина", "price": 1000, "desc": "-10% время отдыха", "type": "cooldown_reduce"}
}

MARKET = {
    "case_basic": {"name": "Обычный кейс", "price": 200, "type": "case"},
    "biz_shawarma": {"name": "Ларёк с шаурмой", "price": 2000, "type": "business", "income": 150},
    "biz_crypto": {"name": "Крипто-ферма", "price": 15000, "type": "business", "income": 1200}
}

CARS = {
    "ok": {"name": "Ока", "price": 3000, "desc": "Едет и едет."},
    "priora": {"name": "Приора", "price": 10000, "desc": "Музыка громче двигателя."},
    "bmw": {"name": "BMW X5", "price": 40000, "desc": "Для важных дел."},
    "gelik": {"name": "Гелик", "price": 80000, "desc": "Черный, тонированный."},
    "lambo": {"name": "Lamborghini", "price": 200000, "desc": "Король дороги."}
}

SLOTS_SYMBOLS = ['V', 'L', 'O', 'G', 'D', 'S']
SLOTS_PAYOUTS = {'SSS': 10, 'DDD': 5, 'GGG': 3, 'OO': 2, 'LLL': 2, 'VVV': 2}

async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=30,
        max_inactive_connection_lifetime=300
    )
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS lottery_tickets")
        await conn.execute("DROP TABLE IF EXISTS robbery")
        await conn.execute("DROP TABLE IF EXISTS daily_bonus")
        await conn.execute("DROP TABLE IF EXISTS garage")
        await conn.execute("DROP TABLE IF EXISTS businesses")
        await conn.execute("DROP TABLE IF EXISTS inventory")
        await conn.execute("DROP TABLE IF EXISTS profiles")
        await conn.execute("DROP TABLE IF EXISTS usernames")
        await conn.execute("DROP TABLE IF EXISTS users")
        print("Старые таблицы удалены")
        await conn.execute("CREATE TABLE users (chat_id BIGINT, user_id BIGINT, balance INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE profiles (chat_id BIGINT, user_id BIGINT, job_key TEXT DEFAULT 'novice', level INTEGER DEFAULT 1, last_work_time REAL DEFAULT 0, has_coffee BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE inventory (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, item_name TEXT, item_type TEXT, rarity TEXT DEFAULT 'common')")
        await conn.execute("CREATE TABLE businesses (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, business_name TEXT, income INTEGER, last_collect_time REAL DEFAULT 0)")
        await conn.execute("CREATE TABLE garage (chat_id BIGINT, user_id BIGINT, car_key TEXT, car_name TEXT, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE daily_bonus (chat_id BIGINT, user_id BIGINT, last_claim REAL DEFAULT 0, streak INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE robbery (chat_id BIGINT, user_id BIGINT, last_robbery REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE lottery_tickets (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, draw_date TEXT)")
        await conn.execute("CREATE TABLE usernames (chat_id BIGINT, user_id BIGINT, username TEXT, PRIMARY KEY (chat_id, user_id))")
    print("База данных создана с изоляцией групп")

async def save_username(chat_id, user_id, username):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO usernames (chat_id, user_id, username) VALUES ($1, $2, $3) ON CONFLICT (chat_id, user_id) DO UPDATE SET username = $3", chat_id, user_id, username)

async def get_username(chat_id, user_id):
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT username FROM usernames WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)

async def get_user(chat_id, user_id):
    async with pool.acquire() as conn:
        balance = await conn.fetchval("SELECT balance FROM users WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)
        if balance is not None:
            return {"balance": balance}
        await conn.execute("INSERT INTO users (chat_id, user_id) VALUES ($1, $2)", chat_id, user_id)
        return {"balance": 0}

async def update_balance(chat_id, user_id, amount):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance = balance + $1 WHERE chat_id = $2 AND user_id = $3", amount, chat_id, user_id)

async def get_profile(chat_id, user_id):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT job_key, level, last_work_time, has_coffee FROM profiles WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)
        if not row:
            await conn.execute("INSERT INTO profiles (chat_id, user_id) VALUES ($1, $2)", chat_id, user_id)
            return {"job_key": "novice", "level": 1, "last_work_time": 0, "has_coffee": False}
        return dict(row)

async def set_car(chat_id, user_id, car_key, car_name):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO garage (chat_id, user_id, car_key, car_name) VALUES ($1, $2, $3, $4) ON CONFLICT (chat_id, user_id) DO UPDATE SET car_key = $3, car_name = $4", chat_id, user_id, car_key, car_name)

async def get_car(chat_id, user_id):
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT car_name FROM garage WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)

async def delete_chat_data(chat_id):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE chat_id = $1", chat_id)
        await conn.execute("DELETE FROM profiles WHERE chat_id = $1", chat_id)
        await conn.execute("DELETE FROM inventory WHERE chat_id = $1", chat_id)
        await conn.execute("DELETE FROM businesses WHERE chat_id = $1", chat_id)
        await conn.execute("DELETE FROM garage WHERE chat_id = $1", chat_id)
        await conn.execute("DELETE FROM daily_bonus WHERE chat_id = $1", chat_id)
        await conn.execute("DELETE FROM robbery WHERE chat_id = $1", chat_id)
        await conn.execute("DELETE FROM lottery_tickets WHERE chat_id = $1", chat_id)
        await conn.execute("DELETE FROM usernames WHERE chat_id = $1", chat_id)

async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("Web server started")

async def polling_health_check():
    while True:
        try:
            await asyncio.sleep(300)
            me = await bot.get_me()
            print(f"Health check OK: {me.first_name}")
        except Exception as e:
            print(f"Health check failed: {e}")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    await message.answer("Экономика группы\n\n/balance - мои сарапулки\n/work - работать\n/pay - перевести (ответь на сообщение)\n/rob - ограбить (ответь на сообщение)\n/daily - ежедневный бонус\n/slots ставка - казино\n/buy_ticket - лотерейный билет\n/shop - улучшения\n/market - бизнесы и кейсы\n/cars - автосалон\n/mycar - моя тачка\n/collect - прибыль с бизнеса\n/inv - инвентарь\n/info - моя карточка\n/rating - рейтинг богачей\n/blackjack - Блэкджек с Игорёчком (2-5 игроков)")

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    user = await get_user(chat_id, user_id)
    car = await get_car(chat_id, user_id)
    car_text = f"\nТачка: {car}" if car else "\nТачка: нет (/cars)"
    await message.answer(f"Баланс: {fmt_money(user['balance'])}{car_text}")

@dp.message(Command("work"))
async def cmd_work(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    profile = await get_profile(chat_id, user_id)
    job = JOBS[profile['job_key']]
    current_time = time.time()
    cooldown = job['cooldown'] * (0.9 if profile['has_coffee'] else 1.0)
    time_passed = current_time - profile['last_work_time']
    if time_passed < cooldown:
        remaining = int(cooldown - time_passed)
        return await message.answer(f"Отдыхайте еще {remaining // 60} мин.")
    salary = job['base_pay'] * profile['level'] + random.randint(0, 5)
    await update_balance(chat_id, user_id, salary)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET last_work_time = $1 WHERE chat_id = $2 AND user_id = $3", current_time, chat_id, user_id)
    await message.answer(f"{job['name']} (Ур. {profile['level']}): заработано {fmt_money(salary)}.")

@dp.message(Command("jobs"))
async def cmd_jobs(message: Message):
    text = "Вакансии:\n"
    for key, info in JOBS.items():
        text += f"{info['name']} ({info['base_pay']} сарапулок/час) -> /job {key}\n"
    await message.answer(text)

@dp.message(Command("job"))
async def cmd_change_job(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2 or args[1] not in JOBS:
        return await message.answer("Выберите работу: /jobs")
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET job_key = $1 WHERE chat_id = $2 AND user_id = $3", args[1], chat_id, user_id)
    await message.answer(f"Вы теперь: {JOBS[args[1]]['name']}")

@dp.message(Command("pay"))
async def cmd_pay(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: /pay сумма (ответь на сообщение)")
    if not message.reply_to_message:
        return await message.answer("Ответьте на сообщение получателя!")
    try: amount = int(args[1])
    except: return await message.answer("Сумма должна быть числом!")
    if amount <= 0: return await message.answer("Сумма должна быть положительной!")
    sender_id = user_id
    receiver_id = message.reply_to_message.from_user.id
    if sender_id == receiver_id: return await message.answer("Нельзя перевести самому себе!")
    sender_bal = await get_user(chat_id, sender_id)
    if sender_bal['balance'] < amount:
        return await message.answer(f"Недостаточно ({fmt_money(sender_bal['balance'])})")
    await update_balance(chat_id, sender_id, -amount)
    await update_balance(chat_id, receiver_id, amount)
    await save_username(chat_id, receiver_id, message.reply_to_message.from_user.full_name)
    await message.answer(f"{message.from_user.full_name} перевёл {fmt_money(amount)} пользователю {message.reply_to_message.from_user.full_name}")

@dp.message(Command("rob"))
async def cmd_rob(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not message.reply_to_message:
        return await message.answer("Ответьте на сообщение жертвы!")
    robber_id = user_id
    victim_id = message.reply_to_message.from_user.id
    if robber_id == victim_id: return await message.answer("Нельзя ограбить самого себя!")
    async with pool.acquire() as conn:
        last_rob = await conn.fetchval("SELECT last_robbery FROM robbery WHERE chat_id = $1 AND user_id = $2", chat_id, robber_id)
        last_rob = last_rob or 0
        current_time = time.time()
        if current_time - last_rob < 10800:
            remaining = int(10800 - (current_time - last_rob))
            return await message.answer(f"Отдыхайте еще {remaining // 3600} ч.")
        await conn.execute("INSERT INTO robbery (chat_id, user_id, last_robbery) VALUES ($1, $2, $3) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_robbery = $3", chat_id, robber_id, current_time)
    victim_bal = await get_user(chat_id, victim_id)
    if victim_bal['balance'] < 50:
        return await message.answer("У жертвы слишком мало денег!")
    success = random.random() < 0.4
    if success:
        stolen = int(victim_bal['balance'] * random.uniform(0.1, 0.5))
        await update_balance(chat_id, victim_id, -stolen)
        await update_balance(chat_id, robber_id, stolen)
        await message.answer(f"ОГРАБЛЕНИЕ УСПЕШНО! {message.from_user.full_name} украл {fmt_money(stolen)} у {message.reply_to_message.from_user.full_name}!")
    else:
        robber_bal = await get_user(chat_id, robber_id)
        penalty = int(robber_bal['balance'] * 0.2)
        await update_balance(chat_id, robber_id, -penalty)
        await update_balance(chat_id, victim_id, penalty)
        await message.answer(f"ПОПАЛСЯ! {message.from_user.full_name} заплатил штраф {fmt_money(penalty)} пользователю {message.reply_to_message.from_user.full_name}!")

@dp.message(Command("daily"))
async def cmd_daily(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    current_time = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT last_claim, streak FROM daily_bonus WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)
        last_claim, streak = (row['last_claim'], row['streak']) if row else (0, 0)
        if current_time - last_claim < 86400:
            remaining = int(86400 - (current_time - last_claim))
            return await message.answer(f"Приходи через {remaining // 3600} ч. {remaining % 3600 // 60} мин.")
        if current_time - last_claim < 172800: streak += 1
        else: streak = 1
        base_bonus = random.randint(100, 300)
        multiplier = min(streak, 7)
        bonus = base_bonus * multiplier
        await update_balance(chat_id, user_id, bonus)
        await conn.execute("INSERT INTO daily_bonus (chat_id, user_id, last_claim, streak) VALUES ($1, $2, $3, $4) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_claim = $3, streak = $4", chat_id, user_id, current_time, streak)
    await message.answer(f"Ежедневный бонус! Ты зашёл {streak} {pluralize(streak, ['день', 'дня', 'дней'])} подряд! Получено: {fmt_money(bonus)}")

@dp.message(Command("slots"))
async def cmd_slots(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2: return await message.answer("Укажите ставку: /slots 100")
    try: bet = int(args[1])
    except: return await message.answer("Ставка должна быть числом!")
    if bet < 10: return await message.answer("Минимальная ставка: 10 сарапулок")
    user_bal = await get_user(chat_id, user_id)
    if user_bal['balance'] < bet:
        return await message.answer(f"Недостаточно ({fmt_money(user_bal['balance'])})")
    await update_balance(chat_id, user_id, -bet)
    result = [random.choice(SLOTS_SYMBOLS) for _ in range(3)]
    result_str = ''.join(result)
    win_amount = 0
    if result_str in SLOTS_PAYOUTS:
        multiplier = SLOTS_PAYOUTS[result_str]
        win_amount = bet * multiplier
        await update_balance(chat_id, user_id, win_amount)
    text = f"СЛОТЫ\n\nСтавка: {fmt_money(bet)}\nРезультат: {' | '.join(result)}\n\n"
    if win_amount > 0:
        text += f"ВЫИГРЫШ: {fmt_money(win_amount)} (x{SLOTS_PAYOUTS[result_str]})"
    else:
        text += "Проигрыш. Попробуй ещё раз!"
    await message.answer(text)

@dp.message(Command("buy_ticket"))
async def cmd_buy_ticket(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    user_bal = await get_user(chat_id, user_id)
    ticket_price = 50
    if user_bal['balance'] < ticket_price:
        return await message.answer(f"Билет стоит {fmt_money(ticket_price)}")
    await update_balance(chat_id, user_id, -ticket_price)
    today = time.strftime("%Y-%m-%d")
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO lottery_tickets (chat_id, user_id, draw_date) VALUES ($1, $2, $3)", chat_id, user_id, today)
    await message.answer(f"Вы купили лотерейный билет за {fmt_money(ticket_price)}! Розыгрыш: /lottery_draw (админ)")

@dp.message(Command("lottery_draw"))
async def cmd_lottery_draw(message: Message):
    chat_id = message.chat.id
    if message.from_user.id not in ADMIN_IDS: return
    today = time.strftime("%Y-%m-%d")
    async with pool.acquire() as conn:
        tickets = await conn.fetch("SELECT user_id FROM lottery_tickets WHERE chat_id = $1 AND draw_date = $2", chat_id, today)
        if not tickets: return await message.answer("Сегодня никто не купил билеты!")
        winner_id = random.choice(tickets)['user_id']
        bank = len(tickets) * 50
        await update_balance(chat_id, winner_id, bank)
        await conn.execute("DELETE FROM lottery_tickets WHERE chat_id = $1 AND draw_date = $2", chat_id, today)
    winner_name = await get_username(chat_id, winner_id) or f"User{winner_id}"
    await message.answer(f"РОЗЫГРЫШ ЛОТЕРЕИ!\n\nПобедитель: {winner_name}\nВыигрыш: {fmt_money(bank)}\n\nВсего участников: {len(tickets)}")

@dp.message(Command("info"))
async def cmd_info(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    user = await get_user(chat_id, user_id)
    profile = await get_profile(chat_id, user_id)
    car = await get_car(chat_id, user_id)
    async with pool.acquire() as conn:
        biz_count = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)
        inv_count = await conn.fetchval("SELECT COUNT(*) FROM inventory WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)
    job = JOBS[profile['job_key']]
    text = f"Карточка игрока\n\n{message.from_user.full_name}\n\n"
    text += f"Баланс: {fmt_money(user['balance'])}\n"
    text += f"Профессия: {job['name']} (Ур. {profile['level']})\n"
    text += f"Машина: {car if car else 'нет'}\n"
    text += f"Бизнесов: {biz_count}\n"
    text += f"Предметов: {inv_count}\n"
    if profile['has_coffee']: text += "Кофе-машина: есть\n"
    await message.answer(text)

@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    text = "Улучшения:\n"
    for k, v in SHOP_ITEMS.items():
        text += f"{v['name']} ({fmt_money(v['price'])}) -> /buy {k}\n"
    await message.answer(text)

@dp.message(Command("buy"))
async def cmd_buy(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2 or args[1] not in SHOP_ITEMS: return await message.answer("/shop")
    item = SHOP_ITEMS[args[1]]
    user = await get_user(chat_id, user_id)
    if user['balance'] < item['price']: return await message.answer(f"Нужно {fmt_money(item['price'])}")
    await update_balance(chat_id, user_id, -item['price'])
    if item['type'] == 'level_up':
        p = await get_profile(chat_id, user_id)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET level = $1 WHERE chat_id = $2 AND user_id = $3", p['level']+1, chat_id, user_id)
        await message.answer(f"Уровень повышен до {p['level']+1}!")
    elif item['type'] == 'cooldown_reduce':
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET has_coffee = TRUE WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)
        await message.answer("Кофе куплен! Работа быстрее.")

@dp.message(Command("market"))
async def cmd_market(message: Message):
    text = "Рынок:\n"
    for k, v in MARKET.items():
        text += f"{v['name']} ({fmt_money(v['price'])}) -> /buy_market {k}\n"
    await message.answer(text)

@dp.message(Command("buy_market"))
async def cmd_buy_market(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2 or args[1] not in MARKET: return await message.answer("/market")
    item = MARKET[args[1]]
    user = await get_user(chat_id, user_id)
    if user['balance'] < item['price']: return await message.answer(f"Нужно {fmt_money(item['price'])}")
    await update_balance(chat_id, user_id, -item['price'])
    if item['type'] == 'case':
        rand = random.randint(1, 100)
        if rand <= 5: prize, rar = "Золотая Скрипка", "legendary"
        elif rand <= 25: prize, rar = "Алмаз", "rare"
        else: prize, rar = "Бумага", "common"
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1, $2, $3, 'card', $4)", chat_id, user_id, prize, rar)
        await message.answer(f"Выпало: {prize} ({rar})")
    elif item['type'] == 'business':
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO businesses (chat_id, user_id, business_name, income) VALUES ($1, $2, $3, $4)", chat_id, user_id, item['name'], item['income'])
        await message.answer(f"Куплен {item['name']}. Жми /collect раз в сутки!")

@dp.message(Command("collect"))
async def cmd_collect(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    now = time.time()
    total = 0
    async with pool.acquire() as conn:
        bizs = await conn.fetch("SELECT id, income, last_collect_time FROM businesses WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)
        if not bizs: return await message.answer("Нет бизнеса.")
        for biz in bizs:
            if now - biz['last_collect_time'] > 86400:
                total += biz['income']
                await conn.execute("UPDATE businesses SET last_collect_time = $1 WHERE id = $2", now, biz['id'])
    if total > 0:
        await update_balance(chat_id, user_id, total)
        await message.answer(f"Прибыль: +{fmt_money(total)}")
    else:
        await message.answer("Рано. Приходи завтра.")

@dp.message(Command("cars"))
async def cmd_cars(message: Message):
    text = "Автосалон:\n\n"
    for k, v in CARS.items():
        text += f"{v['name']}\n   {fmt_money(v['price'])}\n   {v['desc']}\n   Купить: /buycar {k}\n\n"
    await message.answer(text)

@dp.message(Command("buycar"))
async def cmd_buycar(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2 or args[1] not in CARS: return await message.answer("/cars")
    car_key = args[1]
    car = CARS[car_key]
    user = await get_user(chat_id, user_id)
    if user['balance'] < car['price']: return await message.answer(f"Нужно {fmt_money(car['price'])}")
    await update_balance(chat_id, user_id, -car['price'])
    await set_car(chat_id, user_id, car_key, car['name'])
    await message.answer(f"КУПЛЕНО! Теперь ты ездишь на {car['name']}! Проверь через /mycar")

@dp.message(Command("mycar"))
async def cmd_mycar(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    car = await get_car(chat_id, user_id)
    if car: await message.answer(f"Твой гараж: {car}")
    else: await message.answer("Гараж пуст. Купи тачку в /cars!")

@dp.message(Command("inv"))
async def cmd_inv(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    async with pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name, rarity FROM inventory WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)
    if not items: return await message.answer("Пусто.")
    text = "Предметы:\n"
    for item in items:
        c = "L" if item['rarity']=="legendary" else "R" if item['rarity']=="rare" else "C"
        text += f"{c} {item['item_name']}\n"
    await message.answer(text)

@dp.message(Command("rating"))
async def cmd_rating(message: Message):
    chat_id = message.chat.id
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT u.user_id, u.balance, us.username FROM users u LEFT JOIN usernames us ON u.chat_id = us.chat_id AND u.user_id = us.user_id WHERE u.chat_id = $1 ORDER BY u.balance DESC LIMIT 10", chat_id)
    text = "Рейтинг богачей:\n\n"
    for i, row in enumerate(rows, 1):
        display_name = row['username'] if row['username'] else f"User{row['user_id']}"
        text += f"{i}. {display_name} - {fmt_money(row['balance'])}\n"
    await message.answer(text)

@dp.message(Command("give"))
async def cmd_give(message: Message):
    chat_id = message.chat.id
    if message.from_user.id not in ADMIN_IDS: return
    args = message.text.split()
    if len(args) < 2 or not message.reply_to_message: return await message.answer("/give сумма (ответ)")
    try: amount = int(args[1])
    except: return await message.answer("Число!")
    await update_balance(chat_id, message.reply_to_message.from_user.id, amount)
    await save_username(chat_id, message.reply_to_message.from_user.id, message.reply_to_message.from_user.full_name)
    await message.answer(f"Выдано {fmt_money(amount)}.")

# ==================== БЛЭКДЖЕК С КНОПКАМИ (2-5 ИГРОКОВ) ====================

def create_deck():
    suits = ['S', 'H', 'D', 'C']
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
        return f"? + {' '.join(f'{r}{s}' for r,s in cards[1:])}"
    return ' '.join(f'{r}{s}' for r,s in cards)

@dp.message(Command("blackjack"))
async def start_blackjack(message: Message, state: FSMContext):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if chat_id in bj_tables:
        await message.answer("Игра уже идёт! Дождитесь окончания.")
        return
    
    user = await get_user(chat_id, user_id)
    if user['balance'] < 100:
        return await message.answer(f"Нужно минимум 100 сарапулек! У тебя: {fmt_money(user['balance'])}")
    
    bj_tables[chat_id] = {
        "players": {user_id: {"name": message.from_user.first_name, "bet": 0, "cards": [], "stand": False, "busted": False, "bet_msg_id": None}},
        "order": [user_id],
        "stage": "waiting"
    }
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Присоединиться", callback_data=f"bj_join_{chat_id}")]
    ])
    
    msg = await message.answer(
        f"Игорёчек открывает стол!\n\n"
        f"Создатель: {message.from_user.first_name}\n"
        f"Игроков: 1/5\n"
        f"Сбор игроков - 60 секунд\n\n"
        f"Нажмите кнопку чтобы сесть за стол!",
        reply_markup=kb
    )
    bj_tables[chat_id]["main_msg_id"] = msg.message_id
    
    await state.set_state(BJStates.waiting)
    await asyncio.sleep(60)
    
    if chat_id not in bj_tables:
        return
    table = bj_tables[chat_id]
    
    if len(table["players"]) < 2:
        await message.answer("Недостаточно игроков (нужно минимум 2). Стол закрыт.")
        del bj_tables[chat_id]
        await state.clear()
        return
    
    table["stage"] = "betting"
    players_list = ", ".join(p["name"] for p in table["players"].values())
    
    await message.answer(
        f"Игорёчек: Отлично! Игроки: {players_list}\n\n"
        f"Каждый игрок, проверьте личку для ставки!"
    )
    
    # Отправляем КАЖДОМУ игроку отдельное сообщение со ставками
    for uid in table["order"]:
        bets_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="50", callback_data=f"bet_50_{chat_id}"),
             InlineKeyboardButton(text="100", callback_data=f"bet_100_{chat_id}"),
             InlineKeyboardButton(text="200", callback_data=f"bet_200_{chat_id}")],
            [InlineKeyboardButton(text="500", callback_data=f"bet_500_{chat_id}"),
             InlineKeyboardButton(text="1000", callback_data=f"bet_1000_{chat_id}")]
        ])
        
        try:
            bet_msg = await bot.send_message(
                uid,
                f"Игорёчек: Ваша ставка?",
                reply_markup=bets_kb
            )
            table["players"][uid]["bet_msg_id"] = bet_msg.message_id
        except:
            await message.answer(f"⚠️ {table['players'][uid]['name']}, напишите боту в личку!")

@dp.callback_query(lambda c: c.data.startswith("bj_join_"))
async def join_table(callback: types.CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split("_")[2])
    uid = callback.from_user.id
    
    if chat_id not in bj_tables:
        await callback.answer("Стол закрыт!", show_alert=True)
        return
    
    table = bj_tables[chat_id]
    
    if table["stage"] != "waiting":
        await callback.answer("Игра уже началась!", show_alert=True)
        return
    
    if uid in table["players"]:
        await callback.answer("Вы уже в игре!", show_alert=True)
        return
    
    if len(table["players"]) >= 5:
        await callback.answer("Мест нет (макс. 5)!", show_alert=True)
        return
    
    user = await get_user(chat_id, uid)
    if user['balance'] < 100:
        await callback.answer(f"Нужно 100 сарапулек! У вас: {fmt_money(user['balance'])}", show_alert=True)
        return
    
    table["players"][uid] = {"name": callback.from_user.first_name, "bet": 0, "cards": [], "stand": False, "busted": False, "bet_msg_id": None}
    table["order"].append(uid)
    
    await callback.answer(f"Вы присоединились!")
    
    players_list = "\n".join([f"- {p['name']}" for p in table["players"].values()])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Присоединиться", callback_data=f"bj_join_{chat_id}")]
    ])
    
    try:
        await callback.message.edit_text(
            f"Игорёчек открывает стол!\n\n"
            f"Игроки ({len(table['players'])}/5):\n{players_list}\n\n"
            f"Ожидание...",
            reply_markup=kb
        )
    except:
        pass

@dp.callback_query(lambda c: c.data.startswith("bet_"))
async def place_bet(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    bet = int(parts[1])
    chat_id = int(parts[2])
    uid = callback.from_user.id
    
    if chat_id not in bj_tables:
        await callback.answer("Игра не найдена!", show_alert=True)
        return
    
    table = bj_tables[chat_id]
    
    if uid not in table["players"]:
        await callback.answer("Вы не в игре!", show_alert=True)
        return
    
    if table["players"][uid]["bet"] > 0:
        await callback.answer("Вы уже сделали ставку!", show_alert=True)
        return
    
    user = await get_user(chat_id, uid)
    if user['balance'] < bet:
        await callback.answer(f"Мало сарапулек! Баланс: {fmt_money(user['balance'])}", show_alert=True)
        return
    
    await update_balance(chat_id, uid, -bet)
    table["players"][uid]["bet"] = bet
    
    # Обновляем ТОЛЬКО личное сообщение этого игрока
    try:
        await callback.message.edit_text(f"✅ Ваша ставка: {bet} сарапулек. Ждём остальных...")
    except:
        pass
    
    await callback.answer(f"Ставка {bet} принята!")
    
    # Проверяем, все ли поставили
    if all(p["bet"] > 0 for p in table["players"].values()):
        await deal_cards(chat_id, state)

async def deal_cards(chat_id, state):
    table = bj_tables[chat_id]
    table["deck"] = create_deck()
    
    for uid in table["order"]:
        p = table["players"][uid]
        p["cards"] = [table["deck"].pop(), table["deck"].pop()]
    
    table["dealer"] = [table["deck"].pop(), table["deck"].pop()]
    table["stage"] = "playing"
    
    players_info = "\n".join([f"- {p['name']}: ставка {p['bet']}" for p in table["players"].values()])
    
    await bot.send_message(
        chat_id,
        f"Игорёчек: Карты розданы!\n\n"
        f"Мои карты: {show_cards(table['dealer'], hide_first=True)}\n\n"
        f"{players_info}\n\n"
        f"Ходит: {table['players'][table['order'][0]]['name']}"
    )
    
    await state.set_state(BJStates.playing)
    await player_turn(chat_id, table["order"][0], state)

async def player_turn(chat_id, uid, state):
    table = bj_tables[chat_id]
    p = table["players"][uid]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ещё карту", callback_data=f"hit_{uid}_{chat_id}"),
         InlineKeyboardButton(text="Хватит", callback_data=f"stand_{uid}_{chat_id}")]
    ])
    
    await bot.send_message(
        uid,
        f"Ваш ход!\n\n"
        f"Ваши карты: {show_cards(p['cards'])}\n"
        f"Сумма: {calc_score(p['cards'])}\n"
        f"Ставка: {p['bet']}\n\n"
        f"Карта Игорёчка: {table['dealer'][0][0]}{table['dealer'][0][1]}",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data.startswith("hit_") or c.data.startswith("stand_"))
async def hit_stand(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    action = parts[0]
    uid = int(parts[1])
    chat_id = int(parts[2])
    
    if chat_id not in bj_tables:
        await callback.answer("Игра не найдена!", show_alert=True)
        return
    
    table = bj_tables[chat_id]
    p = table["players"][uid]
    
    if action == "hit":
        card = table["deck"].pop()
        p["cards"].append(card)
        score = calc_score(p["cards"])
        
        await callback.message.edit_text(
            f"Вы взяли: {card[0]}{card[1]}\n"
            f"Карты: {show_cards(p['cards'])}\n"
            f"Сумма: {score}"
        )
        
        if score > 21:
            p["stand"] = True
            p["busted"] = True
            await callback.message.answer(f"Перебор ({score})! Вы проиграли ставку.")
            await next_turn(chat_id, state)
        elif score == 21:
            p["stand"] = True
            await callback.message.answer(f"21! Отлично!")
            await next_turn(chat_id, state)
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Ещё карту", callback_data=f"hit_{uid}_{chat_id}"),
                 InlineKeyboardButton(text="Хватит", callback_data=f"stand_{uid}_{chat_id}")]
            ])
            await callback.message.answer(f"Сумма: {score}. Ещё?", reply_markup=kb)
    
    elif action == "stand":
        p["stand"] = True
        await callback.message.edit_text(f"Вы остановились на {calc_score(p['cards'])}")
        await next_turn(chat_id, state)

async def next_turn(chat_id, state):
    table = bj_tables[chat_id]
    
    next_uid = None
    for uid in table["order"]:
        if not table["players"][uid]["stand"]:
            next_uid = uid
            break
    
    if next_uid:
        p = table["players"][next_uid]
        await bot.send_message(chat_id, f"Ходит: {p['name']}")
        await player_turn(chat_id, next_uid, state)
    else:
        await dealer_play(chat_id, state)

async def dealer_play(chat_id, state):
    table = bj_tables[chat_id]
    
    await bot.send_message(
        chat_id,
        f"Игорёчек: Теперь мой ход!\n\n"
        f"Мои карты: {show_cards(table['dealer'])}"
    )
    
    while calc_score(table["dealer"]) < 17:
        await asyncio.sleep(1)
        card = table["deck"].pop()
        table["dealer"].append(card)
        await bot.send_message(
            chat_id,
            f"Игорёчек берёт: {card[0]}{card[1]} -> сумма: {calc_score(table['dealer'])}"
        )
    
    dealer_score = calc_score(table["dealer"])
    
    results = []
    for uid in table["order"]:
        p = table["players"][uid]
        ps = calc_score(p["cards"])
        bet = p["bet"]
        
        if p["busted"]:
            results.append(f"{p['name']}: перебор ({ps}) - проигрыш")
        elif dealer_score > 21:
            await update_balance(chat_id, uid, bet * 2)
            results.append(f"{p['name']}: Игорёчек перебрал! +{bet}")
        elif ps > dealer_score:
            await update_balance(chat_id, uid, bet * 2)
            results.append(f"{p['name']}: победа! +{bet}")
        elif ps == dealer_score:
            await update_balance(chat_id, uid, bet)
            results.append(f"{p['name']}: ничья")
        else:
            results.append(f"{p['name']}: проигрыш")
    
    if dealer_score > 21:
        final = "Игорёчек перебрал!"
    elif any("победа" in r for r in results):
        final = "Игорёчек поздравляет победителей!"
    elif any("проигрыш" in r for r in results):
        final = "Игорёчек забирает ставки!"
    else:
        final = "Ничья!"
    
    await bot.send_message(
        chat_id,
        f"Игорёчек: {final}\n\n"
        f"Карты Игорёчка: {show_cards(table['dealer'])} ({dealer_score})\n\n"
        f"Результаты:\n" + "\n".join(results)
    )
    
    del bj_tables[chat_id]
    await state.clear()

@dp.message()
async def auto_register(message: Message):
    if message.chat.type not in ['group', 'supergroup']: return
    chat_id = message.chat.id
    user_id = message.from_user.id
    await get_user(chat_id, user_id)

@dp.message(F.new_chat_members)
async def on_user_join(message: Message):
    chat_id = message.chat.id
    for user in message.new_chat_members:
        if user.is_bot:
            if user.id == int(API_TOKEN.split(':')[0]):
                await message.answer("Привет! Я экономический бот. Напиши /start чтобы начать!")
            continue
        await get_user(chat_id, user.id)
        await save_username(chat_id, user.id, user.full_name)

async def main():
    await init_db()
    print("Бот запущен!")
    asyncio.create_task(start_web_server())
    asyncio.create_task(polling_health_check())
    await dp.start_polling(bot, timeout=30, allowed_updates=["message", "callback_query", "my_chat_member"])

if __name__ == "__main__":
    asyncio.run(main())
