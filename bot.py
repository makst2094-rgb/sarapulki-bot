import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
import asyncpg
from aiohttp import web
import os

API_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]
DATABASE_URL = os.environ.get("DATABASE_URL", "")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
pool = None

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
SLOTS_PAYOUTS = {
    'SSS': 10,
    'DDD': 5,
    'GGG': 3,
    'OO': 2,
    'LLL': 2,
    'VVV': 2
}

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, balance INTEGER DEFAULT 0)")
        await conn.execute("CREATE TABLE IF NOT EXISTS profiles (user_id BIGINT PRIMARY KEY, job_key TEXT DEFAULT 'novice', level INTEGER DEFAULT 1, last_work_time REAL DEFAULT 0, has_coffee BOOLEAN DEFAULT FALSE)")
        await conn.execute("CREATE TABLE IF NOT EXISTS inventory (id SERIAL PRIMARY KEY, user_id BIGINT, item_name TEXT, item_type TEXT, rarity TEXT DEFAULT 'common')")
        await conn.execute("CREATE TABLE IF NOT EXISTS businesses (id SERIAL PRIMARY KEY, user_id BIGINT, business_name TEXT, income INTEGER, last_collect_time REAL DEFAULT 0)")
        await conn.execute("CREATE TABLE IF NOT EXISTS garage (user_id BIGINT PRIMARY KEY, car_key TEXT, car_name TEXT)")
        await conn.execute("CREATE TABLE IF NOT EXISTS daily_bonus (user_id BIGINT PRIMARY KEY, last_claim REAL DEFAULT 0, streak INTEGER DEFAULT 0)")
        await conn.execute("CREATE TABLE IF NOT EXISTS robbery (user_id BIGINT PRIMARY KEY, last_robbery REAL DEFAULT 0)")
        await conn.execute("CREATE TABLE IF NOT EXISTS lottery_tickets (id SERIAL PRIMARY KEY, user_id BIGINT, draw_date TEXT)")
        await conn.execute("CREATE TABLE IF NOT EXISTS usernames (user_id BIGINT PRIMARY KEY, username TEXT)")
    print("DB initialized")

async def save_username(user_id, username):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO usernames (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET username = $2", user_id, username)

async def get_username(user_id):
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT username FROM usernames WHERE user_id = $1", user_id)

async def get_user(user_id):
    async with pool.acquire() as conn:
        balance = await conn.fetchval("SELECT balance FROM users WHERE user_id = $1", user_id)
        if balance is not None:
            return {"balance": balance}
        await conn.execute("INSERT INTO users (user_id) VALUES ($1)", user_id)
        return {"balance": 0}

async def update_balance(user_id, amount):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", amount, user_id)

async def get_profile(user_id):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT job_key, level, last_work_time, has_coffee FROM profiles WHERE user_id = $1", user_id)
        if not row:
            await conn.execute("INSERT INTO profiles (user_id) VALUES ($1)", user_id)
            return {"job_key": "novice", "level": 1, "last_work_time": 0, "has_coffee": False}
        return dict(row)

async def set_car(user_id, car_key, car_name):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO garage (user_id, car_key, car_name) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET car_key = $2, car_name = $3", user_id, car_key, car_name)

async def get_car(user_id):
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT car_name FROM garage WHERE user_id = $1", user_id)

async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await save_username(message.from_user.id, message.from_user.full_name)
    await message.answer(
        "Экономика группы\n\n"
        "/balance - мои сарапулки\n"
        "/work - работать\n"
        "/pay - перевести (ответь на сообщение)\n"
        "/rob - ограбить (ответь на сообщение)\n"
        "/daily - ежедневный бонус\n"
        "/slots ставка - казино\n"
        "/buy_ticket - лотерейный билет\n"
        "/shop - улучшения\n"
        "/market - бизнесы и кейсы\n"
        "/cars - автосалон\n"
        "/mycar - моя тачка\n"
        "/collect - прибыль с бизнеса\n"
        "/inv - инвентарь\n"
        "/info - моя карточка\n"
        "/rating - рейтинг богачей\n"
        "/blackjack - Блэкджек с Игорёчком"
    )

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    await save_username(message.from_user.id, message.from_user.full_name)
    user = await get_user(message.from_user.id)
    car = await get_car(message.from_user.id)
    car_text = f"\nТачка: {car}" if car else "\nТачка: нет (/cars)"
    await message.answer(f"Баланс: {fmt_money(user['balance'])}{car_text}")

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
        return await message.answer(f"Отдыхайте еще {remaining // 60} мин.")
    salary = job['base_pay'] * profile['level'] + random.randint(0, 5)
    await update_balance(user_id, salary)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET last_work_time = $1 WHERE user_id = $2", current_time, user_id)
    await message.answer(f"{job['name']} (Ур. {profile['level']}): заработано {fmt_money(salary)}.")

@dp.message(Command("jobs"))
async def cmd_jobs(message: Message):
    text = "Вакансии:\n"
    for key, info in JOBS.items():
        text += f"{info['name']} ({info['base_pay']} сарапулок/час) -> /job {key}\n"
    await message.answer(text)

@dp.message(Command("job"))
async def cmd_change_job(message: Message):
    args = message.text.split()
    if len(args) < 2 or args[1] not in JOBS:
        return await message.answer("Выберите работу: /jobs")
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET job_key = $1 WHERE user_id = $2", args[1], message.from_user.id)
    await message.answer(f"Вы теперь: {JOBS[args[1]]['name']}")

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
        return await message.answer(f"Недостаточно ({fmt_money(sender_bal['balance'])})")
    await update_balance(sender_id, -amount)
    await update_balance(receiver_id, amount)
    await save_username(receiver_id, message.reply_to_message.from_user.full_name)
    await message.answer(f"{message.from_user.full_name} перевёл {fmt_money(amount)} пользователю {message.reply_to_message.from_user.full_name}")

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
            return await message.answer(f"Отдыхайте еще {remaining // 3600} ч.")
        await conn.execute("INSERT INTO robbery (user_id, last_robbery) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET last_robbery = $2", robber_id, current_time)
    victim_bal = await get_user(victim_id)
    if victim_bal['balance'] < 50:
        return await message.answer("У жертвы слишком мало денег!")
    success = random.random() < 0.4
    if success:
        stolen = int(victim_bal['balance'] * random.uniform(0.1, 0.5))
        await update_balance(victim_id, -stolen)
        await update_balance(robber_id, stolen)
        await message.answer(f"ОГРАБЛЕНИЕ УСПЕШНО! {message.from_user.full_name} украл {fmt_money(stolen)} у {message.reply_to_message.from_user.full_name}!")
    else:
        robber_bal = await get_user(robber_id)
        penalty = int(robber_bal['balance'] * 0.2)
        await update_balance(robber_id, -penalty)
        await update_balance(victim_id, penalty)
        await message.answer(f"ПОПАЛСЯ! {message.from_user.full_name} заплатил штраф {fmt_money(penalty)} пользователю {message.reply_to_message.from_user.full_name}!")

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
            return await message.answer(f"Приходи через {remaining // 3600} ч. {remaining % 3600 // 60} мин.")
        if current_time - last_claim < 172800: streak += 1
        else: streak = 1
        base_bonus = random.randint(100, 300)
        multiplier = min(streak, 7)
        bonus = base_bonus * multiplier
        await update_balance(user_id, bonus)
        await conn.execute("INSERT INTO daily_bonus (user_id, last_claim, streak) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET last_claim = $2, streak = $3", user_id, current_time, streak)
    await message.answer(f"Ежедневный бонус! Ты зашёл {streak} {pluralize(streak, ['день', 'дня', 'дней'])} подряд! Получено: {fmt_money(bonus)}")

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
        return await message.answer(f"Недостаточно ({fmt_money(user_bal['balance'])})")
    await update_balance(user_id, -bet)
    result = [random.choice(SLOTS_SYMBOLS) for _ in range(3)]
    result_str = ''.join(result)
    win_amount = 0
    if result_str in SLOTS_PAYOUTS:
        multiplier = SLOTS_PAYOUTS[result_str]
        win_amount = bet * multiplier
        await update_balance(user_id, win_amount)
    text = f"СЛОТЫ\n\nСтавка: {fmt_money(bet)}\nРезультат: {' | '.join(result)}\n\n"
    if win_amount > 0:
        text += f"ВЫИГРЫШ: {fmt_money(win_amount)} (x{SLOTS_PAYOUTS[result_str]})"
    else:
        text += "Проигрыш. Попробуй ещё раз!"
    await message.answer(text)

@dp.message(Command("buy_ticket"))
async def cmd_buy_ticket(message: Message):
    user_id = message.from_user.id
    await save_username(user_id, message.from_user.full_name)
    user_bal = await get_user(user_id)
    ticket_price = 50
    if user_bal['balance'] < ticket_price:
        return await message.answer(f"Билет стоит {fmt_money(ticket_price)}")
    await update_balance(user_id, -ticket_price)
    today = time.strftime("%Y-%m-%d")
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO lottery_tickets (user_id, draw_date) VALUES ($1, $2)", user_id, today)
    await message.answer(f"Вы купили лотерейный билет за {fmt_money(ticket_price)}! Розыгрыш: /lottery_draw (админ)")

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
    await message.answer(f"РОЗЫГРЫШ ЛОТЕРЕИ!\n\nПобедитель: {winner_name}\nВыигрыш: {fmt_money(bank)}\n\nВсего участников: {len(tickets)}")

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
    args = message.text.split()
    if len(args) < 2 or args[1] not in SHOP_ITEMS: return await message.answer("/shop")
    item = SHOP_ITEMS[args[1]]
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user['balance'] < item['price']: return await message.answer(f"Нужно {fmt_money(item['price'])}")
    await update_balance(user_id, -item['price'])
    if item['type'] == 'level_up':
        p = await get_profile(user_id)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET level = $1 WHERE user_id = $2", p['level']+1, user_id)
        await message.answer(f"Уровень повышен до {p['level']+1}!")
    elif item['type'] == 'cooldown_reduce':
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET has_coffee = TRUE WHERE user_id = $1", user_id)
        await message.answer("Кофе куплен! Работа быстрее.")

@dp.message(Command("market"))
async def cmd_market(message: Message):
    text = "Рынок:\n"
    for k, v in MARKET.items():
        text += f"{v['name']} ({fmt_money(v['price'])}) -> /buy_market {k}\n"
    await message.answer(text)

@dp.message(Command("buy_market"))
async def cmd_buy_market(message: Message):
    args = message.text.split()
    if len(args) < 2 or args[1] not in MARKET: return await message.answer("/market")
    item = MARKET[args[1]]
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user['balance'] < item['price']: return await message.answer(f"Нужно {fmt_money(item['price'])}")
    await update_balance(user_id, -item['price'])
    if item['type'] == 'case':
        rand = random.randint(1, 100)
        if rand <= 5: prize, rar = "Золотая Скрипка", "legendary"
        elif rand <= 25: prize, rar = "Алмаз", "rare"
        else: prize, rar = "Бумага", "common"
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO inventory (user_id, item_name, item_type, rarity) VALUES ($1, $2, 'card', $3)", user_id, prize, rar)
        await message.answer(f"Выпало: {prize} ({rar})")
    elif item['type'] == 'business':
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO businesses (user_id, business_name, income) VALUES ($1, $2, $3)", user_id, item['name'], item['income'])
        await message.answer(f"Куплен {item['name']}. Жми /collect раз в сутки!")

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
    args = message.text.split()
    if len(args) < 2 or args[1] not in CARS: return await message.answer("/cars")
    car_key = args[1]
    car = CARS[car_key]
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user['balance'] < car['price']: return await message.answer(f"Нужно {fmt_money(car['price'])}")
    await update_balance(user_id, -car['price'])
    await set_car(user_id, car_key, car['name'])
    await message.answer(f"КУПЛЕНО! Теперь ты ездишь на {car['name']}! Проверь через /mycar")

@dp.message(Command("mycar"))
async def cmd_mycar(message: Message):
    car = await get_car(message.from_user.id)
    if car: await message.answer(f"Твой гараж: {car}")
    else: await message.answer("Гараж пуст. Купи тачку в /cars!")

@dp.message(Command("inv"))
async def cmd_inv(message: Message):
    async with pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name, rarity FROM inventory WHERE user_id = $1", message.from_user.id)
    if not items: return await message.answer("Пусто.")
    text = "Предметы:\n"
    for item in items:
        c = "L" if item['rarity']=="legendary" else "R" if item['rarity']=="rare" else "C"
        text += f"{c} {item['item_name']}\n"
    await message.answer(text)

@dp.message(Command("rating"))
async def cmd_rating(message: Message):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT u.user_id, u.balance, us.username FROM users u LEFT JOIN usernames us ON u.user_id = us.user_id ORDER BY u.balance DESC LIMIT 10")
    text = "Рейтинг богачей:\n\n"
    for i, row in enumerate(rows, 1):
        display_name = row['username'] if row['username'] else f"User{row['user_id']}"
        text += f"{i}. {display_name} — {fmt_money(row['balance'])}\n"
    await message.answer(text)

@dp.message(Command("give"))
async def cmd_give(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    args = message.text.split()
    if len(args) < 2 or not message.reply_to_message: return await message.answer("/give сумма (ответ)")
    try: amount = int(args[1])
    except: return await message.answer("Число!")
    await update_balance(message.reply_to_message.from_user.id, amount)
    await save_username(message.reply_to_message.from_user.id, message.reply_to_message.from_user.full_name)
    await message.answer(f"Выдано {fmt_money(amount)}.")

@dp.message(Command("blackjack"))
async def cmd_blackjack(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user['balance'] < 100:
        return await message.answer(f"Для игры нужно минимум 100 сарапулек! У тебя: {fmt_money(user['balance'])}")
    bet = 100
    await update_balance(user_id, -bet)
    suits = ['S', 'H', 'D', 'C']
    ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
    deck = [(r, s) for s in suits for r in ranks]
    random.shuffle(deck)
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]
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
    player_score = calc_score(player_cards)
    dealer_score = calc_score(dealer_cards)
    while dealer_score < 17:
        dealer_cards.append(deck.pop())
        dealer_score = calc_score(dealer_cards)
    if player_score > 21:
        result = "ПЕРЕБОР! Игорёчек забирает ставку."
    elif dealer_score > 21:
        result = "Игорёчек перебрал! Ты выиграл!"
        await update_balance(user_id, bet * 2)
    elif player_score > dealer_score:
        result = "Победа! Ты обыграл Игорёчка!"
        await update_balance(user_id, bet * 2)
    elif player_score == dealer_score:
        result = "Ничья! Ставка возвращена."
        await update_balance(user_id, bet)
    else:
        result = "Проигрыш. Игорёчек забирает ставку."
    await message.answer(
        f"Блэкджек с Игорёчком\n\n"
        f"Твои карты: {show_cards(player_cards)} ({player_score})\n"
        f"Карты Игорёчка: {show_cards(dealer_cards)} ({dealer_score})\n\n"
        f"Ставка: {fmt_money(bet)}\n\n"
        f"{result}"
    )

@dp.message()
async def auto_register(message: Message):
    if message.chat.type not in ['group', 'supergroup']: return
    user_id = message.from_user.id
    await get_user(user_id)

async def main():
    await init_db()
    print("Bot started!")
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
