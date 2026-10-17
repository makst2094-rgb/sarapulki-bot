# ============================================================================
# 🤖 ЭКОНОМИЧЕСКИЙ БОТ ДЛЯ TELEGRAM ГРУПП - ВЕРСИЯ 25.0
# ============================================================================

import asyncio
import logging
import random
import time
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncpg
from aiohttp import web

API_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]
DATABASE_URL = os.environ.get("DATABASE_URL", "")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
pool = None

class BlackjackStates(StatesGroup):
    waiting = State()
    betting = State()
    playing = State()

bj_tables = {}
exam_sessions = {}
active_cases = {}

# ==================== НАСТРОЙКИ МАФИИ ====================
MAFIA_BALANCE_THRESHOLD = 30000
MAFIA_BANK_THRESHOLD = 50000
MAFIA_CHECK_INTERVAL = 86400
MAFIA_CHANCE = 0.15
MAFIA_RANSOM_RATE = 0.20
MAFIA_PENALTY_RATE = 0.30
MAFIA_DEADLINE_HOURS = 1

# ==================== НАСТРОЙКИ ТЮРЬМЫ ====================
JAIL_FINE_RATE = 0.25
JAIL_DEBT_THRESHOLD = 500
JAIL_DEBT_TIMEOUT = 7200

CRAFT_RECIPES = {
    "diamond": {"name": "💎 Алмаз", "requires": {" Бумага": 10}, "rarity": "rare"},
    "scriptka": {"name": "🎸 Золотая Скрипка", "requires": {"💎 Алмаз": 5}, "rarity": "legendary"}
}

LOTTERY_PRICE = 50
LOTTERY_INTERVAL = 12 * 3600
BANK_INTEREST_RATE = 0.01
CREDIT_MULTIPLIER = 10
CREDIT_DAILY_RATE = 0.02
CREDIT_TERM_DAYS = 7
ROB_SUCCESS_RATE = 0.6
ROB_COOLDOWN = 10800
ROB_MIN_PERCENT = 0.1
ROB_MAX_PERCENT = 0.5
ROB_PENALTY_RATE = 0.2
ROB_DEBT_TIMEOUT = 7200
DICE_MIN_BET = 10
DICE_WIN_THRESHOLD = 4
DICE_WIN_MULTIPLIER = 2
BJ_MIN_BALANCE = 100
BJ_MAX_PLAYERS = 5
BJ_WAIT_TIME = 60
BJ_DEALER_STOP = 17
JAIL_TIME_HOURS = 2
JAIL_FINE_PER_HOUR = 50
LAWYER_MIN_FEE = 500

COURSES = {
    "miner": {
        "name": "📘 Курс шахтёра",
        "price": 500,
        "required_for": "miner",
        "questions": [
            {"q": "Что нужно надевать в шахте?", "a": ["каска", "шлем", "защита"], "correct": 0},
            {"q": "Сколько тонн весит вагонетка?", "a": ["1", "5", "10"], "correct": 1},
            {"q": "Главный инструмент шахтёра?", "a": ["лопата", "отбойный молоток", "кирка"], "correct": 2}
        ]
    },
    "coder": {
        "name": " Курс программирования",
        "price": 2000,
        "required_for": "coder",
        "questions": [
            {"q": "Язык для веб-разработки?", "a": ["Python", "HTML", "C++"], "correct": 1},
            {"q": "Что такое баг?", "a": ["ошибка", "функция", "переменная"], "correct": 0},
            {"q": "Сколько бит в байте?", "a": ["4", "8", "16"], "correct": 1}
        ]
    },
    "trader": {
        "name": "📈 Курс трейдинга",
        "price": 5000,
        "required_for": "trader",
        "questions": [
            {"q": "Что такое бычий рынок?", "a": ["рост", "падение", "стабильность"], "correct": 0},
            {"q": "Диверсификация это?", "a": ["риск", "распределение", "прибыль"], "correct": 1},
            {"q": "Ликвидность актива?", "a": ["скорость продажи", "цена", "объём"], "correct": 0}
        ]
    },
    "lawyer": {
        "name": "️ Курс адвоката",
        "price": 3000,
        "required_for": None,
        "questions": [
            {"q": "Что такое презумпция невиновности?", "a": ["виновен пока не доказано", "невиновен пока не доказано", "все равны"], "correct": 1},
            {"q": "Срок давности уголовного дела?", "a": ["5 лет", "10 лет", "зависит от тяжести"], "correct": 2},
            {"q": "Кто защищает обвиняемого?", "a": ["прокурор", "адвокат", "судья"], "correct": 1}
        ]
    },
    "mba": {
        "name": "🎓 MBA",
        "price": 15000,
        "required_for": None,
        "questions": [
            {"q": "ROI это?", "a": ["возврат инвестиций", "риск", "доход"], "correct": 0},
            {"q": "EBITDA показывает?", "a": ["прибыль", "убыток", "оборот"], "correct": 0},
            {"q": "Стратегия роста?", "a": ["сокращение", "инвестиции", "стагнация"], "correct": 1}
        ]
    }
}

JOBS = {
    "novice": {"name": "👶 Новичок", "base_pay": 25, "cooldown": 3600},
    "miner": {"name": "⛏️ Шахтёр", "base_pay": 50, "cooldown": 3600},
    "coder": {"name": "💻 Программист", "base_pay": 100, "cooldown": 7200},
    "trader": {"name": " Трейдер", "base_pay": 200, "cooldown": 10800}
}

SHOP_ITEMS = {
    "course": {"name": "📚 Уровень+", "price": 3000, "type": "level_up"},
    "coffee": {"name": "☕ Кофе-машина", "price": 6000, "type": "cooldown_reduce"}
}

MARKET = {
    "case_basic": {"name": "📦 Кейс", "price": 200, "type": "case"},
    "biz_newspaper": {"name": " 📰Газетный киоск", "price": 500, "type": "business", "income": 83},
    "biz_shawarma": {"name": "🌯 Шаурма", "price": 2000, "type": "business", "income": 333},
    "biz_coffee": {"name": "☕ Кофейня", "price": 5000, "type": "business", "income": 833},
    "biz_crypto": {"name": "💻 Крипто-ферма", "price": 15000, "type": "business", "income": 2500},
    "biz_hotel": {"name": "🏨 Отель", "price": 50000, "type": "business", "income": 8333}
}

CARS = {
    "ok": {"name": " 🚘Ока", "price": 3000},
    "priora": {"name": " 🚗Приора", "price": 10000},
    "bmw": {"name": "🏎️ BMW", "price": 40000},
    "gelik": {"name": "🚙 Гелик", "price": 80000},
    "lambo": {"name": "🏎️ Lamborghini", "price": 200000}
}

def pluralize(n, forms):
    n = abs(n) % 100
    n1 = n % 10
    if n > 10 and n < 20:
        return forms[2]
    if n1 > 1 and n1 < 5:
        return forms[1]
    if n1 == 1:
        return forms[0]
    return forms[2]

def fmt_money(amount):
    return f"{amount} {pluralize(amount, ['сарапулка', 'сарапулки', 'сарапулок'])}"

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours} ч {minutes} мин"
    return f"{minutes} мин"

def format_date(timestamp):
    return time.strftime('%d.%m.%Y', time.localtime(timestamp))

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10, command_timeout=30)
    async with pool.acquire() as conn:
        await conn.execute("""CREATE TABLE IF NOT EXISTS users (chat_id BIGINT, user_id BIGINT, balance INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS profiles (chat_id BIGINT, user_id BIGINT, job_key TEXT DEFAULT 'novice', level INTEGER DEFAULT 1, last_work_time REAL DEFAULT 0, has_coffee BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS inventory (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, item_name TEXT, item_type TEXT, rarity TEXT DEFAULT 'common')""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS businesses (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, business_name TEXT, income INTEGER, last_collect_time REAL DEFAULT 0)""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS garage (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, car_key TEXT, car_name TEXT)""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS daily_bonus (chat_id BIGINT, user_id BIGINT, last_claim REAL DEFAULT 0, streak INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("DROP TABLE IF EXISTS robbery")
        await conn.execute("""CREATE TABLE robbery (chat_id BIGINT, user_id BIGINT, last_robbery REAL DEFAULT 0, debt_amount INTEGER DEFAULT 0, debt_time REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        print("✅ Таблица robbery пересоздана")
        await conn.execute("""CREATE TABLE IF NOT EXISTS lottery_tickets (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, buy_time REAL)""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS usernames (chat_id BIGINT, user_id BIGINT, username TEXT, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS bank (chat_id BIGINT, user_id BIGINT, deposit INTEGER DEFAULT 0, last_interest_time REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS education (chat_id BIGINT, user_id BIGINT, completed_courses TEXT[] DEFAULT '{}', has_mba BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS loans (chat_id BIGINT, user_id BIGINT, amount INTEGER DEFAULT 0, interest INTEGER DEFAULT 0, taken_at REAL DEFAULT 0, due_date REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS jail (chat_id BIGINT, user_id BIGINT, release_time REAL DEFAULT 0, fine_per_hour INTEGER DEFAULT 50, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS jail_fines (
            chat_id BIGINT,
            user_id BIGINT,
            fine_amount INTEGER DEFAULT 0,
            debt_time REAL DEFAULT 0,
            paid BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (chat_id, user_id)
        )""")
        print("✅ Таблица jail_fines создана")
        await conn.execute("""CREATE TABLE IF NOT EXISTS mafia_threats (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            user_id BIGINT,
            threat_time REAL DEFAULT 0,
            deadline REAL DEFAULT 0,
            ransom_amount INTEGER DEFAULT 0,
            threat_type TEXT DEFAULT 'asset',
            target_asset TEXT DEFAULT '',
            paid BOOLEAN DEFAULT FALSE
        )""")
        print("✅ Таблица mafia_threats создана")
    print("✅ База данных готова")

async def save_username(cid, uid, name):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO usernames VALUES ($1,$2,$3) ON CONFLICT (chat_id, user_id) DO UPDATE SET username=$3", cid, uid, name)

async def get_user(cid, uid):
    async with pool.acquire() as conn:
        b = await conn.fetchval("SELECT balance FROM users WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if b is not None:
            return {"balance": b}
        await conn.execute("INSERT INTO users VALUES ($1,$2,0)", cid, uid)
        return {"balance": 0}

async def update_balance(cid, uid, amt):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance=balance+$1 WHERE chat_id=$2 AND user_id=$3", amt, cid, uid)

async def get_profile(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT job_key, level, last_work_time, has_coffee FROM profiles WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if not r:
            await conn.execute("INSERT INTO profiles VALUES ($1,$2,'novice',1,0,FALSE)", cid, uid)
            return {"job_key": "novice", "level": 1, "last_work_time": 0, "has_coffee": False}
        return dict(r)

async def set_car(cid, uid, key, name):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO garage (chat_id, user_id, car_key, car_name) VALUES ($1,$2,$3,$4)", cid, uid, key, name)

async def get_car(cid, uid):
    async with pool.acquire() as conn:
        cars = await conn.fetch("SELECT car_name FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
        return ", ".join([c['car_name'] for c in cars]) if cars else None

async def get_bank(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT deposit, last_interest_time FROM bank WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if not r:
            await conn.execute("INSERT INTO bank VALUES ($1,$2,0,$3)", cid, uid, time.time())
            return {"deposit": 0, "last_interest_time": time.time()}
        return dict(r)

async def update_bank(cid, uid, amt):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE bank SET deposit=deposit+$1 WHERE chat_id=$2 AND user_id=$3", amt, cid, uid)

async def calc_interest(dep, lt):
    days = (time.time() - lt) / 86400
    return int(dep * BANK_INTEREST_RATE * days), time.time()

async def get_education(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT completed_courses, has_mba FROM education WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if not r:
            await conn.execute("INSERT INTO education VALUES ($1,$2,'{}',FALSE)", cid, uid)
            return {"completed_courses": [], "has_mba": False}
        return {"completed_courses": r['completed_courses'] or [], "has_mba": r['has_mba']}

async def complete_course(cid, uid, ck):
    async with pool.acquire() as conn:
        if ck == "mba":
            await conn.execute("UPDATE education SET has_mba=TRUE WHERE chat_id=$1 AND user_id=$2", cid, uid)
        else:
            await conn.execute("UPDATE education SET completed_courses=array_append(completed_courses,$1) WHERE chat_id=$2 AND user_id=$3", ck, cid, uid)

async def get_loan(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT amount, interest, taken_at, due_date FROM loans WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if not r:
            return {"amount": 0, "interest": 0, "taken_at": 0, "due_date": 0}
        return dict(r)

async def update_loan(cid, uid, amount, interest, taken_at, due_date):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO loans (chat_id, user_id, amount, interest, taken_at, due_date) VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT (chat_id, user_id) DO UPDATE SET amount=$3, interest=$4, taken_at=$5, due_date=$6", cid, uid, amount, interest, taken_at, due_date)

async def clear_loan(cid, uid):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM loans WHERE chat_id=$1 AND user_id=$2", cid, uid)

async def is_in_jail(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT release_time FROM jail WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if not r:
            return False
        if time.time() >= r['release_time']:
            await conn.execute("DELETE FROM jail WHERE chat_id=$1 AND user_id=$2", cid, uid)
            return False
        return True

async def get_jail_info(cid, uid):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT release_time, fine_per_hour FROM jail WHERE chat_id=$1 AND user_id=$2", cid, uid)

async def send_to_jail(cid, uid, hours):
    release_time = time.time() + (hours * 3600)
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO jail VALUES ($1,$2,$3,$4) ON CONFLICT (chat_id, user_id) DO UPDATE SET release_time=$3, fine_per_hour=$4", cid, uid, release_time, JAIL_FINE_PER_HOUR)
    return release_time

async def release_from_jail(cid, uid):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM jail WHERE chat_id=$1 AND user_id=$2", cid, uid)

async def find_lawyers_in_chat(cid):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT e.user_id, u.username FROM education e JOIN usernames u ON e.chat_id = u.chat_id AND e.user_id = u.user_id WHERE e.chat_id = $1 AND 'lawyer' = ANY(e.completed_courses)", cid)
        return [(r['user_id'], r['username']) for r in rows]

async def cleanup_old_cases():
    now = time.time()
    to_delete = []
    for case_id, case in active_cases.items():
        try:
            timestamp = int(case_id.split("_")[-1])
            if now - timestamp > 600:
                to_delete.append(case_id)
        except:
            to_delete.append(case_id)
    for case_id in to_delete:
        parts = case_id.split("_")
        cid = int(parts[0])
        rid = int(parts[1])
        await send_to_jail(cid, rid, JAIL_TIME_HOURS)
        try:
            await bot.send_message(cid, f"⏳ <b>Время вышло!</b>\n\nИгрок не сделал выбор за 10 минут и автоматически отправлен в тюрьму на {JAIL_TIME_HOURS} часа.", parse_mode="HTML")
        except:
            pass
        del active_cases[case_id]

async def auto_cleanup_timer(case_id):
    await asyncio.sleep(600)
    if case_id in active_cases:
        await cleanup_old_cases()

async def arrest_player(cid, uid):
    arrested = []
    bank_data = await get_bank(cid, uid)
    if bank_data['deposit'] > 0:
        arrested.append(f"💰 Банк: {fmt_money(bank_data['deposit'])}")
        async with pool.acquire() as conn:
            await conn.execute("UPDATE bank SET deposit=0, last_interest_time=$1 WHERE chat_id=$2 AND user_id=$3", time.time(), cid, uid)
    car = await get_car(cid, uid)
    if car:
        arrested.append(f"🚗 Машины: {car}")
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
    async with pool.acquire() as conn:
        businesses = await conn.fetch("SELECT business_name FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if businesses:
            arrested.append(f" Бизнесы: {', '.join([b['business_name'] for b in businesses])}")
            await conn.execute("DELETE FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
    async with pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if items:
            arrested.append(f" Предметы: {', '.join([i['item_name'] for i in items])}")
            await conn.execute("DELETE FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET job_key='novice', level=1 WHERE chat_id=$1 AND user_id=$2", cid, uid)
    arrested.append("💼 Профессия сброшена")
    return arrested

async def handle_ping(request):
    return web.Response(text="🤖 Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    print("🌐 Web server started")

async def polling_health_check():
    while True:
        try:
            await asyncio.sleep(300)
            await bot.get_me()
        except Exception as e:
            print(f"Health check failed: {e}")

async def auto_lottery_loop():
    print("🎰 Авто-лотерея запущена")
    while True:
        await asyncio.sleep(3600)
        now = time.time()
        async with pool.acquire() as conn:
            chats = await conn.fetch("SELECT DISTINCT chat_id FROM lottery_tickets")
            for row in chats:
                cid = row['chat_id']
                tickets = await conn.fetch("SELECT id, user_id FROM lottery_tickets WHERE chat_id=$1 AND buy_time<=$2", cid, now - LOTTERY_INTERVAL)
                if len(tickets) >= 2:
                    winner = random.choice(tickets)
                    bank = len(tickets) * LOTTERY_PRICE
                    await update_balance(cid, winner['user_id'], bank)
                    wname = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, winner['user_id']) or f"User{winner['user_id']}"
                    await conn.execute("DELETE FROM lottery_tickets WHERE chat_id=$1", cid)
                    try:
                        await bot.send_message(cid, f"🎊 <b>АВТО-РОЗЫГРЫШ!</b>\n\n {wname}\n💰 {fmt_money(bank)}", parse_mode="HTML")
                    except:
                        pass

async def loan_interest_loop():
    print("💳 Цикл кредитов запущен")
    while True:
        await asyncio.sleep(86400)
        async with pool.acquire() as conn:
            loans = await conn.fetch("SELECT chat_id, user_id, amount, interest, due_date FROM loans WHERE amount>0")
            for loan in loans:
                cid, uid = loan['chat_id'], loan['user_id']
                if time.time() > loan['due_date']:
                    total_debt = loan['amount'] + loan['interest']
                    arrested = await arrest_player(cid, uid)
                    await clear_loan(cid, uid)
                    try:
                        await bot.send_message(cid, f"🚔 <b>АРЕСТ ИМУЩЕСТВА!</b>\n\nДолг: <b>{fmt_money(total_debt)}</b>\n\nКонфисковано:\n" + "\n".join([f"• {item}" for item in arrested]), parse_mode="HTML")
                    except:
                        pass
                else:
                    daily_interest = int(loan['amount'] * CREDIT_DAILY_RATE)
                    await update_loan(cid, uid, loan['amount'], loan['interest'] + daily_interest, loan['taken_at'], loan['due_date'])

async def rob_debt_check_loop():
    print("⚖️ Цикл проверки долгов за ограбления запущен")
    while True:
        await asyncio.sleep(300)
        now = time.time()
        async with pool.acquire() as conn:
            debts = await conn.fetch("SELECT chat_id, user_id FROM robbery WHERE debt_amount > 0")
            for d in debts:
                cid, uid = d['chat_id'], d['user_id']
                row = await conn.fetchrow("SELECT debt_time FROM robbery WHERE chat_id=$1 AND user_id=$2", cid, uid)
                if not row or now - row['debt_time'] < ROB_DEBT_TIMEOUT:
                    continue
                arrested = await arrest_player(cid, uid)
                await conn.execute("UPDATE robbery SET debt_amount=0, debt_time=0 WHERE chat_id=$1 AND user_id=$2", cid, uid)
                try:
                    msg = f"🚔 <b>АРЕСТ ЗА НЕОПЛАЧЕННЫЙ ШТРАФ!</b>\n\nВы не погасили штраф за ограбление за {int(ROB_DEBT_TIMEOUT/3600)} часа.\n\n<b>Конфисковано:</b>\n" + "\n".join([f"• {i}" for i in arrested])
                    await bot.send_message(cid, msg, parse_mode="HTML")
                except:
                    pass

async def mafia_threat_loop():
    print("🕴️ Цикл мафии запущен")
    while True:
        await asyncio.sleep(MAFIA_CHECK_INTERVAL)
        async with pool.acquire() as conn:
            users = await conn.fetch(
                "SELECT u.chat_id, u.user_id, u.balance, COALESCE(b.deposit, 0) as deposit "
                "FROM users u LEFT JOIN bank b ON u.chat_id=b.chat_id AND u.user_id=b.user_id "
                "WHERE u.balance > $1 OR COALESCE(b.deposit, 0) > $2",
                MAFIA_BALANCE_THRESHOLD, MAFIA_BANK_THRESHOLD
            )
            for user in users:
                cid, uid = user['chat_id'], user['user_id']
                balance = user['balance'] or 0
                deposit = user['deposit'] or 0
                total_wealth = balance + deposit
                active_threat = await conn.fetchval(
                    "SELECT COUNT(*) FROM mafia_threats WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE AND deadline > $3",
                    cid, uid, time.time()
                )
                if active_threat > 0:
                    continue
                if random.random() > MAFIA_CHANCE:
                    continue
                ransom = int(total_wealth * MAFIA_RANSOM_RATE)
                deadline = time.time() + (MAFIA_DEADLINE_HOURS * 3600)
                businesses = await conn.fetch(
                    "SELECT business_name, income FROM businesses WHERE chat_id=$1 AND user_id=$2 ORDER BY income DESC",
                    cid, uid
                )
                cars = await conn.fetch(
                    "SELECT car_key, car_name FROM garage WHERE chat_id=$1 AND user_id=$2",
                    cid, uid
                )
                if businesses or cars:
                    threat_type = 'asset'
                    if businesses and (not cars or businesses[0]['income'] * 6 >= (CARS.get(cars[0]['car_key'], {}).get('price', 0) if cars else 0)):
                        target = businesses[0]['business_name']
                        target_desc = f"🏢 Бизнес <b>{target}</b> (доход {fmt_money(businesses[0]['income'])}/сутки)"
                    else:
                        target = cars[0]['car_name']
                        target_desc = f"🚗 Машину <b>{target}</b>"
                else:
                    threat_type = 'balance'
                    target = 'balance'
                    penalty = int(total_wealth * MAFIA_PENALTY_RATE)
                    target_desc = f"💰 <b>{fmt_money(penalty)}</b> с вашего счёта (30%)"
                await conn.execute(
                    "INSERT INTO mafia_threats (chat_id, user_id, threat_time, deadline, ransom_amount, threat_type, target_asset) "
                    "VALUES ($1,$2,$3,$4,$5,$6,$7)",
                    cid, uid, time.time(), deadline, ransom, threat_type, target
                )
                username = await conn.fetchval(
                    "SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2",
                    cid, uid
                ) or f"User{uid}"
                msg = (
                    f"️ <b>К ВАМ ПРИШЛА МАФИЯ!</b>\n\n"
                    f"👤 {username}, мы знаем о ваших доходах...\n\n"
                    f"💰 <b>Ваш капитал:</b> {fmt_money(total_wealth)}\n"
                    f"  • 💵 Основной: {fmt_money(balance)}\n"
                    f"  • 🏦 Банк: {fmt_money(deposit)}\n\n"
                    f"⚠️ <b>ТРЕБОВАНИЕ:</b>\n"
                    f"Переведите нам <b>{fmt_money(ransom)}</b> в течение <b>{MAFIA_DEADLINE_HOURS} часа</b>\n\n"
                    f"🔫 <b>ИНАЧЕ МЫ ЗАБЕРЁМ:</b>\n{target_desc}\n\n"
                    f"💳 Для оплаты напишите: <b>/pay_mafia</b>\n\n"
                    f"⏳ Время пошло..."
                )
                try:
                    await bot.send_message(cid, msg, parse_mode="HTML")
                except:
                    pass

async def execute_mafia_threats():
    async with pool.acquire() as conn:
        expired = await conn.fetch(
            "SELECT * FROM mafia_threats WHERE paid=FALSE AND deadline < $1",
            time.time()
        )
        for threat in expired:
            cid, uid = threat['chat_id'], threat['user_id']
            threat_type = threat['threat_type']
            target = threat['target_asset']
            username = await conn.fetchval(
                "SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2",
                cid, uid
            ) or f"User{uid}"
            if threat_type == 'asset':
                businesses = await conn.fetch("SELECT business_name FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
                cars = await conn.fetch("SELECT car_name FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
                if target in [b['business_name'] for b in businesses]:
                    await conn.execute("DELETE FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name=$3", cid, uid, target)
                    msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ВАШ БИЗНЕС!</b>\n\n👤 {username}, вы не заплатили выкуп.\n🏢 Конфискован: <b>{target}</b>\n\n💡 В следующий раз платите вовремя..."
                elif target in [c['car_name'] for c in cars]:
                    await conn.execute("DELETE FROM garage WHERE chat_id=$1 AND user_id=$2 AND car_name=$3", cid, uid, target)
                    msg = f"🔫 <b>МАФИЯ УКРАЛА ВАШУ МАШИНУ!</b>\n\n👤 {username}, вы не заплатили выкуп.\n🚗 Украдена: <b>{target}</b>\n\n💡 В следующий раз платите вовремя..."
                else:
                    user = await get_user(cid, uid)
                    bank = await get_bank(cid, uid)
                    penalty = int((user['balance'] + bank['deposit']) * MAFIA_PENALTY_RATE)
                    paid_from_balance = min(penalty, user['balance'])
                    remaining = penalty - paid_from_balance
                    if paid_from_balance > 0:
                        await update_balance(cid, uid, -paid_from_balance)
                    if remaining > 0 and bank['deposit'] > 0:
                        await update_bank(cid, uid, -min(remaining, bank['deposit']))
                    msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ДЕНЬГИ!</b>\n\n👤 {username}, вы не заплатили выкуп.\n💸 Списано: <b>{fmt_money(penalty)}</b>\n\n💡 В следующий раз платите вовремя..."
            else:
                user = await get_user(cid, uid)
                bank = await get_bank(cid, uid)
                penalty = int((user['balance'] + bank['deposit']) * MAFIA_PENALTY_RATE)
                paid_from_balance = min(penalty, user['balance'])
                remaining = penalty - paid_from_balance
                if paid_from_balance > 0:
                    await update_balance(cid, uid, -paid_from_balance)
                if remaining > 0 and bank['deposit'] > 0:
                    await update_bank(cid, uid, -min(remaining, bank['deposit']))
                msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ДЕНЬГИ!</b>\n\n👤 {username}, вы не заплатили выкуп.\n💸 Списано: <b>{fmt_money(penalty)}</b>\n\n В следующий раз платите вовремя..."
            await conn.execute("UPDATE mafia_threats SET paid=TRUE WHERE id=$1", threat['id'])
            try:
                await bot.send_message(cid, msg, parse_mode="HTML")
            except:
                pass

async def mafia_check_loop():
    print("⏰ Цикл проверки мафии запущен")
    while True:
        await asyncio.sleep(300)
        await execute_mafia_threats()

async def jail_fine_check_loop():
    print("⚖️ Цикл проверки долгов после тюрьмы запущен")
    while True:
        await asyncio.sleep(300)
        async with pool.acquire() as conn:
            fines = await conn.fetch(
                "SELECT * FROM jail_fines WHERE paid=FALSE AND fine_amount > 0"
            )
            for fine in fines:
                cid, uid = fine['chat_id'], fine['user_id']
                in_jail = await is_in_jail(cid, uid)
                if in_jail:
                    continue
                user = await get_user(cid, uid)
                bank = await get_bank(cid, uid)
                total_available = user['balance'] + bank['deposit']
                if total_available >= fine['fine_amount']:
                    paid_from_balance = min(fine['fine_amount'], user['balance'])
                    remaining = fine['fine_amount'] - paid_from_balance
                    if paid_from_balance > 0:
                        await update_balance(cid, uid, -paid_from_balance)
                    if remaining > 0 and bank['deposit'] > 0:
                        await update_bank(cid, uid, -min(remaining, bank['deposit']))
                    await conn.execute(
                        "UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2",
                        cid, uid
                    )
                    continue
                if fine['debt_time'] > 0 and time.time() - fine['debt_time'] > JAIL_DEBT_TIMEOUT:
                    if user['balance'] < JAIL_DEBT_THRESHOLD:
                        arrested = await arrest_player(cid, uid)
                        await conn.execute(
                            "UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2",
                            cid, uid
                        )
                        username = await conn.fetchval(
                            "SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2",
                            cid, uid
                        ) or f"User{uid}"
                        try:
                            msg = (
                                f"🚔 <b>АРЕСТ ЗА НЕОПЛАЧЕННЫЙ ШТРАФ ПОСЛЕ ТЮРЬМЫ!</b>\n\n"
                                f"👤 {username}, вы не заплатили штраф после выхода из тюрьмы.\n\n"
                                f"<b>Конфисковано:</b>\n" + "\n".join([f"• {i}" for i in arrested])
                            )
                            await bot.send_message(cid, msg, parse_mode="HTML")
                        except:
                            pass

@dp.message(Command("start"))
async def cmd_start(m: Message):
    await save_username(m.chat.id, m.from_user.id, m.from_user.full_name)
    await m.answer(
        "🎩 <b>Добро пожаловать в мир Сарапулок!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>Финансы:</b>\n"
        "  /balance — мой баланс\n"
        "  /pay сумма — перевод (ответ)\n"
        "  /bank — банковский счёт\n"
        "  /deposit сумма — вклад\n"
        "  /withdraw сумма — снять\n\n"
        "💼 <b>Работа:</b>\n"
        "  /work — работать\n"
        "  /jobs — вакансии\n"
        "  /job ключ — сменить работу\n\n"
        "🔫 <b>Криминал:</b>\n"
        "  /rob — ограбить (ответ)\n"
        "  ️ /hire_lawyer @user сумма\n"
        "  🏛️ /court — суд\n"
        "  🔒 /jail — статус тюрьмы\n"
        "  💸 /jail_pay — оплатить штраф\n\n"
        "🎮 <b>Игры:</b>\n"
        "  🎲 /dice сумма — кости\n"
        "  🃏 /blackjack — блэкджек\n"
        "  🎟️ /buy_ticket — лотерея\n"
        "  🎁 /daily — бонус\n\n"
        "🏪 <b>Бизнес:</b>\n"
        "  /market — рынок\n"
        "  /buy_market ключ — купить\n"
        "  /collect — прибыль\n\n"
        " <b>Авто:</b>\n"
        "  /cars — автосалон\n"
        "  /buycar ключ — купить\n"
        "  /mycar — мои машины\n\n"
        "🎓 <b>Образование:</b>\n"
        "  /education — курсы\n"
        "  /buy_course ключ — купить\n\n"
        "💳 <b>Кредиты:</b>\n"
        "  /credit сумма — взять\n"
        "  /debt — долг\n"
        "  /repay сумма — погасить\n"
        "  /repay_all — всё погасить\n\n"
        "🛒 <b>Магазин:</b>\n"
        "  /shop — улучшения\n"
        "  /buy ключ — купить\n\n"
        " <b>Инвентарь:</b>\n"
        "  /inv — инвентарь\n"
        "  /craft — крафт\n"
        "  /craft_item ключ\n"
        "  /trade @user предмет кол-во\n\n"
        "🏆 <b>Инфо:</b>\n"
        "  /info — карточка\n"
        "  /rating — рейтинг\n\n"
        "🕴️ <b>Мафия:</b>\n"
        "  /pay_mafia — оплатить выкуп\n"
        "━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )

@dp.message(Command("balance"))
async def cmd_balance(m: Message):
    await save_username(m.chat.id, m.from_user.id, m.from_user.full_name)
    u = await get_user(m.chat.id, m.from_user.id)
    c = await get_car(m.chat.id, m.from_user.id)
    bd = await get_bank(m.chat.id, m.from_user.id)
    in_jail = await is_in_jail(m.chat.id, m.from_user.id)
    jail_text = "\n🔒 <b>В ТЮРЬМЕ!</b>" if in_jail else ""
    debt_text = f"\n <b>ДОЛГ: {fmt_money(abs(u['balance']))}</b>" if u['balance'] < 0 else ""
    await m.answer(
        f"💰 <b>Баланс:</b> {fmt_money(u['balance'])}\n"
        f"🏦 <b>Банк:</b> {fmt_money(bd['deposit'])}\n"
        f"🚗 <b>Машины:</b> {c or 'нет'}{jail_text}{debt_text}",
        parse_mode="HTML"
    )

@dp.message(Command("work"))
async def cmd_work(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        info = await get_jail_info(cid, uid)
        return await m.answer(f"🔒 Вы в тюрьме! Осталось: {format_time(int(info['release_time'] - time.time()))}\n💸 Используйте /jail_pay")
    user = await get_user(cid, uid)
    if user['balance'] < 0:
        return await m.answer(f"⛔ У вас долг {fmt_money(abs(user['balance']))}! Пополните баланс через /pay или ждите ареста.")
    await save_username(cid, uid, m.from_user.full_name)
    p = await get_profile(cid, uid)
    jk = p['job_key']
    if jk != 'novice':
        edu = await get_education(cid, uid)
        if jk not in edu['completed_courses']:
            async with pool.acquire() as conn:
                await conn.execute("UPDATE profiles SET job_key='novice' WHERE chat_id=$1 AND user_id=$2", cid, uid)
            jk = 'novice'
            p['job_key'] = 'novice'
    j = JOBS[jk]
    ct = time.time()
    cd = j['cooldown'] * (0.9 if p['has_coffee'] else 1.0)
    if ct - p['last_work_time'] < cd:
        return await m.answer(f"⏳ Отдых {int((cd - (ct - p['last_work_time'])) // 60)} мин.")
    sal = j['base_pay'] * p['level'] + random.randint(0, 5)
    edu = await get_education(cid, uid)
    if edu['has_mba']:
        sal = int(sal * 1.5)
    await update_balance(cid, uid, sal)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET last_work_time=$1 WHERE chat_id=$2 AND user_id=$3", ct, cid, uid)
    await m.answer(f"💼 <b>{j['name']}</b> (Ур.{p['level']}): +<b>{fmt_money(sal)}</b>", parse_mode="HTML")

@dp.message(Command("jobs"))
async def cmd_jobs(m: Message):
    t = " <b>Вакансии:</b>\n\n"
    for k, v in JOBS.items():
        t += f"🔹 {v['name']} — {fmt_money(v['base_pay'])}/ч → /job {k}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("job"))
async def cmd_change_job(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2 or args[1] not in JOBS:
        return await m.answer("/jobs")
    if args[1] != 'novice':
        edu = await get_education(cid, uid)
        if args[1] not in edu['completed_courses']:
            return await m.answer(f"❌ Нужен курс: /buy_course {args[1]}")
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET job_key=$1 WHERE chat_id=$2 AND user_id=$3", args[1], cid, uid)
    await m.answer(f"✅ Теперь: <b>{JOBS[args[1]]['name']}</b>", parse_mode="HTML")

@dp.message(Command("pay"))
async def cmd_pay(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя переводить!")
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message:
        return await m.answer("/pay сумма (ответ)")
    try:
        amt = int(args[1])
    except:
        return await m.answer("❌ Число!")
    if amt <= 0:
        return await m.answer("❌ >0!")
    s, r = uid, m.reply_to_message.from_user.id
    if s == r:
        return await m.answer("❌ Себе нельзя!")
    sb = await get_user(cid, s)
    if sb['balance'] < amt:
        return await m.answer(f" Мало ({fmt_money(sb['balance'])})")
    await update_balance(cid, s, -amt)
    await update_balance(cid, r, amt)
    await save_username(cid, r, m.reply_to_message.from_user.full_name)
    await m.answer(f"✅ Перевод <b>{fmt_money(amt)}</b>", parse_mode="HTML")

@dp.message(Command("rob"))
async def cmd_rob(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        info = await get_jail_info(cid, uid)
        return await m.answer(f" Вы в тюрьме! Осталось: {format_time(int(info['release_time'] - time.time()))}")
    user = await get_user(cid, uid)
    if user['balance'] < 0:
        return await m.answer(f"⛔ У вас долг! Сначала погасите его.")
    if not m.reply_to_message:
        return await m.answer("🔫 Ответьте на жертву!")
    rid, vid = uid, m.reply_to_message.from_user.id
    if rid == vid:
        return await m.answer("❌ Себя нельзя!")
    if await is_in_jail(cid, vid):
        return await m.answer("❌ Жертва в тюрьме!")
    async with pool.acquire() as conn:
        lr = await conn.fetchval("SELECT last_robbery FROM robbery WHERE chat_id=$1 AND user_id=$2", cid, rid) or 0
        ct = time.time()
        if ct - lr < ROB_COOLDOWN:
            return await m.answer(f"⏳ Кулдаун {format_time(ROB_COOLDOWN - (ct - lr))}")
        await conn.execute("INSERT INTO robbery (chat_id, user_id, last_robbery, debt_amount, debt_time) VALUES ($1,$2,$3,0,0) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_robbery=$3", cid, rid, ct)
    vb = await get_user(cid, vid)
    if vb['balance'] < 50:
        return await m.answer("❌ У жертвы мало денег!")
    if random.random() < ROB_SUCCESS_RATE:
        st = int(vb['balance'] * random.uniform(ROB_MIN_PERCENT, ROB_MAX_PERCENT))
        await update_balance(cid, vid, -st)
        await update_balance(cid, rid, st)
        await m.answer(
            f"🔫 <b>ОГРАБЛЕНИЕ УСПЕШНО!</b>\n\n"
            f"{m.from_user.full_name} украл <b>{fmt_money(st)}</b>\n"
            f"у {m.reply_to_message.from_user.full_name}!",
            parse_mode="HTML"
        )
    else:
        rb = await get_user(cid, rid)
        bank_data = await get_bank(cid, rid)
        total_wealth = rb['balance'] + bank_data['deposit']
        fine_amount = int(total_wealth * JAIL_FINE_RATE)
        
        async with pool.acquire() as conn2:
            await conn2.execute(
                "INSERT INTO jail_fines (chat_id, user_id, fine_amount, debt_time, paid) "
                "VALUES ($1,$2,$3,$4,FALSE) "
                "ON CONFLICT (chat_id, user_id) DO UPDATE SET fine_amount=$3, debt_time=$4, paid=FALSE",
                cid, rid, fine_amount, time.time()
            )
        
        lawyers = await find_lawyers_in_chat(cid)
        
        if not lawyers:
            await send_to_jail(cid, rid, JAIL_TIME_HOURS)
            await m.answer(
                f"🚔 <b>ПОПАЛСЯ!</b>\n\n"
                f" Тюрьма: <b>{JAIL_TIME_HOURS} часа</b>\n\n"
                f"⚠️ После выхода штраф <b>25%</b> от вашего капитала:\n"
                f"💰 Ожидаемый штраф: <b>{fmt_money(fine_amount)}</b>\n\n"
                f"⚖️ Нет адвокатов в чате — защитить некому!",
                parse_mode="HTML"
            )
        else:
            case_id = f"{cid}_{rid}_{int(time.time())}"
            active_cases[case_id] = {"criminal": rid, "victim": vid, "penalty": fine_amount, "lawyer": None, "paid_fee": 0}
            asyncio.create_task(auto_cleanup_timer(case_id))
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚖️ Нанять адвоката", callback_data=f"find_lawyer_{case_id}")],
                [InlineKeyboardButton(text=" Пойти в тюрьму", callback_data=f"go_jail_{case_id}")]
            ])
            lawyer_list = "\n".join([f"• @{l[1]}" for l in lawyers[:5]])
            await m.answer(
                f"🚔 <b>ПОПАЛСЯ!</b>\n\n"
                f"🔒 Тюрьма: <b>{JAIL_TIME_HOURS} часа</b>\n\n"
                f"⚠️ После выхода штраф <b>25%</b> от капитала:\n"
                f"💰 Ожидаемый штраф: <b>{fmt_money(fine_amount)}</b>\n\n"
                f"⚖️ Доступные адвокаты:\n{lawyer_list}\n\n"
                f"Выберите:\n"
                f"• Нанять адвоката (шанс 50/50 избежать всего)\n"
                f"• Пойти в тюрьму и заплатить штраф",
                reply_markup=kb,
                parse_mode="HTML"
            )

@dp.callback_query(lambda c: c.data.startswith("go_jail_"))
async def go_jail_cb(cb: types.CallbackQuery):
    case_id = "_".join(cb.data.split("_")[2:])
    if case_id not in active_cases:
        return await cb.answer("Дело закрыто!", show_alert=True)
    cid = cb.message.chat.id
    criminal_uid = active_cases[case_id]["criminal"]
    if cb.from_user.id != criminal_uid:
        return await cb.answer("Не ваше дело!", show_alert=True)
    await send_to_jail(cid, criminal_uid, JAIL_TIME_HOURS)
    del active_cases[case_id]
    await cb.message.edit_text(
        f"🔒 <b>Вы выбрали тюрьму!</b>\n\n"
        f"⏰ Срок: {JAIL_TIME_HOURS} часа\n"
        f"⚠️ После выхода — штраф 25% от капитала\n\n"
        f"Используйте /jail_pay для досрочного выхода",
        parse_mode="HTML"
    )
    await cb.answer("Вы в тюрьме!")

@dp.callback_query(lambda c: c.data.startswith("find_lawyer_"))
async def find_lawyer_cb(cb: types.CallbackQuery):
    case_id = "_".join(cb.data.split("_")[2:])
    if case_id not in active_cases:
        return await cb.answer("Дело закрыто!", show_alert=True)
    cid = cb.message.chat.id
    if cb.from_user.id != active_cases[case_id]["criminal"]:
        return await cb.answer("Не ваше дело!", show_alert=True)
    await cleanup_old_cases()
    await cb.message.edit_text(
        f"⚖️ <b>Поиск адвоката...</b>\n\n"
        f"Адвокат должен ответить на ваше сообщение:\n"
        f"<b>/hire_lawyer @ваш_ник сумма</b>\n\n"
        f"⏰ 10 минут, иначе — тюрьма!",
        parse_mode="HTML"
    )

@dp.message(Command("hire_lawyer"))
async def cmd_hire_lawyer(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя нанимать!")
    args = m.text.split()
    if len(args) < 3 or not m.reply_to_message:
        return await m.answer("⚖️ <b>/hire_lawyer @user сумма</b> (ответ на сообщение клиента)", parse_mode="HTML")
    try:
        fee = int(args[2])
    except:
        return await m.answer("❌ Число!")
    if fee < LAWYER_MIN_FEE:
        return await m.answer(f"❌ Минимум: {fmt_money(LAWYER_MIN_FEE)}")
    client_uid = m.reply_to_message.from_user.id
    lawyer_uid = uid
    if lawyer_uid == client_uid:
        return await m.answer("❌ Нельзя нанять себя!")
    await cleanup_old_cases()
    my_case = None
    for case_id, case in active_cases.items():
        if case["criminal"] == client_uid and case["lawyer"] is None:
            my_case = case_id
            break
    if not my_case:
        return await m.answer("❌ У клиента нет активных дел!")
    edu = await get_education(cid, lawyer_uid)
    if "lawyer" not in edu['completed_courses']:
        return await m.answer("❌ У вас нет курса адвоката!")
    client_bal = await get_user(cid, client_uid)
    if client_bal['balance'] < fee:
        return await m.answer(f"❌ У клиента мало средств ({fmt_money(client_bal['balance'])})")
    await update_balance(cid, client_uid, -fee)
    await update_balance(cid, lawyer_uid, fee)
    active_cases[my_case]["lawyer"] = lawyer_uid
    active_cases[my_case]["paid_fee"] = fee
    client_name = m.reply_to_message.from_user.full_name
    lawyer_name = m.from_user.full_name
    await m.answer(
        f"⚖️ <b>Вы наняты адвокатом!</b>\n\n"
        f"👤 Клиент: {client_name}\n"
        f"💰 Получено: {fmt_money(fee)}\n\n"
        f"Используйте <b>/court</b> для суда",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(client_uid, f"⚖️ <b>Ваш адвокат:</b> {lawyer_name}\n\nИспользуйте <b>/court</b> для начала суда!", parse_mode="HTML")
    except:
        pass

@dp.message(Command("court"))
async def cmd_court(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 Вы в тюрьме!")
    await cleanup_old_cases()
    my_case_id = None
    for case_id, case in active_cases.items():
        if case["criminal"] == uid or case["lawyer"] == uid:
            my_case_id = case_id
            break
    if not my_case_id:
        return await m.answer("❌ Нет активных дел!")
    case = active_cases[my_case_id]
    if case["lawyer"] is None:
        return await m.answer("❌ Сначала наймите адвоката!")
    await m.answer("🏛️ <b>СУДЕБНОЕ ЗАСЕДАНИЕ...</b>", parse_mode="HTML")
    await asyncio.sleep(3)
    verdict = random.random() < 0.5
    if verdict:
        lawyer_fee = case["paid_fee"]
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2",
                cid, case["criminal"]
            )
        del active_cases[my_case_id]
        await m.answer(
            f"⚖️ <b>ВЕРДИКТ: НЕВИНОВЕН!</b>\n\n"
            f"✅ Штраф 25% аннулирован! 🎉\n"
            f"💸 Оплата адвокату ({fmt_money(lawyer_fee)}) остаётся у него",
            parse_mode="HTML"
        )
    else:
        lawyer_fee = case["paid_fee"]
        await send_to_jail(cid, case["criminal"], JAIL_TIME_HOURS)
        del active_cases[my_case_id]
        await m.answer(
            f"⚖️ <b>ВЕРДИКТ: ВИНОВЕН!</b>\n\n"
            f"😔 Адвокат проиграл\n\n"
            f"🔒 Тюрьма: {JAIL_TIME_HOURS} часа\n"
            f"⚠️ После выхода — штраф 25% от капитала\n"
            f"💸 Услуги адвоката ({fmt_money(lawyer_fee)}) не возвращаются\n\n"
            f"Используйте /jail_pay",
            parse_mode="HTML"
        )

@dp.message(Command("jail"))
async def cmd_jail(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    info = await get_jail_info(cid, uid)
    if not info or time.time() >= info['release_time']:
        if info:
            await release_from_jail(cid, uid)
        return await m.answer("✅ Вы не в тюрьме!")
    remaining = int(info['release_time'] - time.time())
    remaining_hours = int(remaining / 3600) + 1
    total_fine = remaining_hours * info['fine_per_hour']
    async with pool.acquire() as conn:
        jail_fine = await conn.fetchrow(
            "SELECT fine_amount FROM jail_fines WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE",
            cid, uid
        )
    fine_text = ""
    if jail_fine:
        fine_text = f"\n⚠️ Штраф после выхода: <b>{fmt_money(jail_fine['fine_amount'])}</b> (25% от капитала)"
    await m.answer(
        f"🔒 <b>Вы в тюрьме!</b>\n\n"
        f"⏰ Осталось: <b>{format_time(remaining)}</b>\n"
        f"💰 Штраф/час: {fmt_money(info['fine_per_hour'])}\n"
        f"💸 Досрочный выход: <b>{fmt_money(total_fine)}</b>{fine_text}\n\n"
        f"<b>/jail_pay</b> — досрочный выход\n"
        f"Или ждите окончания срока",
        parse_mode="HTML"
    )

@dp.message(Command("jail_pay"))
async def cmd_jail_pay(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    info = await get_jail_info(cid, uid)
    if not info or time.time() >= info['release_time']:
        if info:
            await release_from_jail(cid, uid)
        return await m.answer("✅ Вы не в тюрьме!")
    remaining_seconds = info['release_time'] - time.time()
    remaining_hours = int(remaining_seconds / 3600) + 1
    total_fine = remaining_hours * info['fine_per_hour']
    user_bal = (await get_user(cid, uid))['balance']
    bank_dep = (await get_bank(cid, uid))['deposit']
    total_available = user_bal + bank_dep
    
    async with pool.acquire() as conn:
        jail_fine = await conn.fetchrow(
            "SELECT fine_amount FROM jail_fines WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE",
            cid, uid
        )
    
    jail_fine_amount = jail_fine['fine_amount'] if jail_fine else 0
    total_needed = total_fine + jail_fine_amount
    
    if total_available < total_needed:
        return await m.answer(
            f"❌ Недостаточно средств для досрочного выхода!\n"
            f"Нужно: {fmt_money(total_needed)}\n"
            f"  • За выход: {fmt_money(total_fine)}\n"
            f"  • Штраф 25%: {fmt_money(jail_fine_amount)}\n"
            f"На руках: {fmt_money(max(0, user_bal))}\n"
            f"В банке: {fmt_money(bank_dep)}\n\n"
            f"Пополните баланс или ждите окончания срока",
            parse_mode="HTML"
        )
    
    pay_from_main = min(total_fine, max(0, user_bal))
    remaining_to_pay = total_fine - pay_from_main
    if pay_from_main > 0:
        await update_balance(cid, uid, -pay_from_main)
    if remaining_to_pay > 0:
        await update_bank(cid, uid, -remaining_to_pay)
    
    user_now = await get_user(cid, uid)
    bank_now = await get_bank(cid, uid)
    paid_from_balance = min(jail_fine_amount, user_now['balance'])
    remaining_fine = jail_fine_amount - paid_from_balance
    if paid_from_balance > 0:
        await update_balance(cid, uid, -paid_from_balance)
    if remaining_fine > 0 and bank_now['deposit'] > 0:
        paid_from_bank = min(remaining_fine, bank_now['deposit'])
        await update_bank(cid, uid, -paid_from_bank)
        remaining_fine -= paid_from_bank
    
    if remaining_fine > 0:
        user_after = await get_user(cid, uid)
        if user_after['balance'] < JAIL_DEBT_THRESHOLD:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE jail_fines SET fine_amount=$1, debt_time=$2, paid=FALSE WHERE chat_id=$3 AND user_id=$4",
                    remaining_fine, time.time(), cid, uid
                )
            await release_from_jail(cid, uid)
            await m.answer(
                f"✅ Досрочный выход!\n\n"
                f"💰 Оплачено: {fmt_money(total_fine + jail_fine_amount - remaining_fine)}\n"
                f"⛔ <b>Образовался долг: {fmt_money(remaining_fine)}</b>\n"
                f"⏰ У вас есть 2 часа на погашение!\n\n"
                f"Иначе заберут профессию/бизнес/машину!",
                parse_mode="HTML"
            )
        else:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2",
                    cid, uid
                )
            await release_from_jail(cid, uid)
            await m.answer(
                f"✅ Досрочный выход!\n\n"
                f"💰 Оплачено: {fmt_money(total_fine + jail_fine_amount)}\n"
                f"Вы свободны!",
                parse_mode="HTML"
            )
    else:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2",
                cid, uid
            )
        await release_from_jail(cid, uid)
        await m.answer(
            f"✅ Досрочный выход!\n\n"
            f"💰 Оплачено: {fmt_money(total_fine + jail_fine_amount)}\n"
            f"Вы свободны!",
            parse_mode="HTML"
        )

@dp.message(Command("daily"))
async def cmd_daily(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя получать бонусы!")
    user = await get_user(cid, uid)
    if user['balance'] < 0:
        return await m.answer(f"⛔ У вас долг {fmt_money(abs(user['balance']))}!")
    await save_username(cid, uid, m.from_user.full_name)
    ct = time.time()
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT last_claim, streak FROM daily_bonus WHERE chat_id=$1 AND user_id=$2", cid, uid)
        lc, sk = (r['last_claim'], r['streak']) if r else (0, 0)
        if ct - lc < 86400:
            return await m.answer(f"⏰ Через {format_time(86400 - (ct - lc))}")
        sk = sk + 1 if ct - lc < 172800 else 1
        bn = random.randint(100, 300) * min(sk, 7)
        await update_balance(cid, uid, bn)
        await conn.execute("INSERT INTO daily_bonus VALUES ($1,$2,$3,$4) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_claim=$3, streak=$4", cid, uid, ct, sk)
    await m.answer(f"🎁 Бонус за {sk} дн.: <b>{fmt_money(bn)}</b>", parse_mode="HTML")

@dp.message(Command("dice"))
async def cmd_dice(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer(" В тюрьме нельзя играть!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("🎲 <b>/dice сумма</b>\n\n4,5,6 — победа x2\n1,2,3 — проигрыш", parse_mode="HTML")
    try:
        bet = int(args[1])
    except:
        return await m.answer(" Число!")
    if bet < DICE_MIN_BET:
        return await m.answer(f" Мин: {DICE_MIN_BET}")
    ub = await get_user(cid, uid)
    if ub['balance'] < bet:
        return await m.answer(f"❌ Мало ({fmt_money(ub['balance'])})")
    await update_balance(cid, uid, -bet)
    dice = random.randint(1, 6)
    await m.answer(f" <b>Бросаем...</b>\nСтавка: {fmt_money(bet)}", parse_mode="HTML")
    await asyncio.sleep(1)
    if dice >= DICE_WIN_THRESHOLD:
        win = bet * DICE_WIN_MULTIPLIER
        await update_balance(cid, uid, win)
        await m.answer(f"🎲 <b>{dice}</b>\n\n🎉 <b>ПОБЕДА!</b>\n+{fmt_money(win)} (x2)", parse_mode="HTML")
    else:
        await m.answer(f"🎲 <b>{dice}</b>\n\n💀 <b>Проигрыш</b>", parse_mode="HTML")

@dp.message(Command("buy_ticket"))
async def cmd_buy_ticket(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя!")
    ub = await get_user(cid, uid)
    if ub['balance'] < LOTTERY_PRICE:
        return await m.answer(f"❌ Нужно {fmt_money(LOTTERY_PRICE)}")
    await update_balance(cid, uid, -LOTTERY_PRICE)
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO lottery_tickets (chat_id, user_id, buy_time) VALUES ($1,$2,$3)", cid, uid, time.time())
    await m.answer("🎟️ Билет куплен! Розыгрыш через 12ч.")

@dp.message(Command("info"))
async def cmd_info(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    await save_username(cid, uid, m.from_user.full_name)
    u = await get_user(cid, uid)
    p = await get_profile(cid, uid)
    c = await get_car(cid, uid)
    bd = await get_bank(cid, uid)
    edu = await get_education(cid, uid)
    loan = await get_loan(cid, uid)
    in_jail = await is_in_jail(cid, uid)
    async with pool.acquire() as conn:
        bc = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
        ic = await conn.fetchval("SELECT COUNT(*) FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
        jail_fine = await conn.fetchrow("SELECT fine_amount FROM jail_fines WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE", cid, uid)
    j = JOBS[p['job_key']]
    cc = len(edu['completed_courses']) + (1 if edu['has_mba'] else 0)
    t = (
        f"📊 <b>Карточка игрока</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>{m.from_user.full_name}</b>\n"
        f"💰 Баланс: {fmt_money(u['balance'])}\n"
        f" Банк: {fmt_money(bd['deposit'])}\n"
        f"💼 Профессия: {j['name']} (Ур.{p['level']})\n"
        f" Машины: {c or 'нет'}\n"
        f"🏢 Бизнесов: {bc}\n"
        f"🎒 Предметов: {ic}\n"
        f"🎓 Курсов: {cc}"
    )
    if in_jail:
        t += "\n🔒 <b>В ТЮРЬМЕ!</b>"
    if u['balance'] < 0:
        t += f"\n ДОЛГ: {fmt_money(abs(u['balance']))}"
    if jail_fine:
        t += f"\n⚠️ Штраф после тюрьмы: {fmt_money(jail_fine['fine_amount'])}"
    if edu['has_mba']:
        t += "\n🎯 MBA (+50% к зарплате)"
    if p['has_coffee']:
        t += "\n Кофе-машина (-10% кулдаун)"
    if loan['amount'] > 0:
        t += f"\n💳 Кредит: {fmt_money(loan['amount'] + loan['interest'])}"
    t += "\n━━━━━━━━━━━━━━━━━━━━"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("shop"))
async def cmd_shop(m: Message):
    t = "🛒 <b>Магазин улучшений:</b>\n\n"
    for k, v in SHOP_ITEMS.items():
        t += f"🔹 {v['name']} — {fmt_money(v['price'])} → /buy {k}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buy"))
async def cmd_buy(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2 or args[1] not in SHOP_ITEMS:
        return await m.answer("/shop")
    it = SHOP_ITEMS[args[1]]
    u = await get_user(cid, uid)
    if u['balance'] < it['price']:
        return await m.answer(f"❌ Нужно {fmt_money(it['price'])}")
    await update_balance(cid, uid, -it['price'])
    if it['type'] == 'level_up':
        p = await get_profile(cid, uid)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET level=$1 WHERE chat_id=$2 AND user_id=$3", p['level']+1, cid, uid)
        await m.answer(f"✅ Уровень повышен до {p['level']+1}!", parse_mode="HTML")
    elif it['type'] == 'cooldown_reduce':
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET has_coffee=TRUE WHERE chat_id=$1 AND user_id=$2", cid, uid)
        await m.answer(" Кофе-машина куплена! Кулдаун -10%", parse_mode="HTML")

@dp.message(Command("market"))
async def cmd_market(m: Message):
    t = "🏪 <b>Рынок:</b>\n\n📦 <b>Кейсы:</b>\n"
    for k, v in MARKET.items():
        if v["type"] == "case":
            t += f"🔹 {v['name']} — {fmt_money(v['price'])} → /buy_market {k}\n"
    t += "\n <b>Бизнесы:</b>\n"
    for k, v in MARKET.items():
        if v["type"] == "business":
            t += f"🔹 {v['name']} — {fmt_money(v['price'])} → /buy_market {k}\n"
            t += f"    💰 Доход: {fmt_money(v['income'])}/сутки\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buy_market"))
async def cmd_buy_market(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer(" В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2 or args[1] not in MARKET:
        return await m.answer("/market")
    it = MARKET[args[1]]
    u = await get_user(cid, uid)
    if u['balance'] < it['price']:
        return await m.answer(f"❌ Нужно {fmt_money(it['price'])}")
    await update_balance(cid, uid, -it['price'])
    if it['type'] == 'case':
        r = random.randint(1, 100)
        if r <= 5:
            pr, rar = "🎸 Золотая Скрипка", "legendary"
        elif r <= 25:
            pr, rar = "💎 Алмаз", "rare"
        else:
            pr, rar = "📄 Бумага", "common"
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,'card',$4)", cid, uid, pr, rar)
        await m.answer(f"📦 Выпало: <b>{pr}</b> ({rar})", parse_mode="HTML")
    elif it['type'] == 'business':
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO businesses (chat_id, user_id, business_name, income) VALUES ($1,$2,$3,$4)", cid, uid, it['name'], it['income'])
        await m.answer(f"✅ Куплен <b>{it['name']}</b>!", parse_mode="HTML")

@dp.message(Command("collect"))
async def cmd_collect(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer(" В тюрьме нельзя!")
    now = time.time()
    tot = 0
    collected = []
    waiting = []
    async with pool.acquire() as conn:
        bz = await conn.fetch("SELECT * FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if not bz:
            return await m.answer("❌ У вас нет бизнесов.\n🏪 Купите в /market")
        
        for b in bz:
            time_since = now - b['last_collect_time']
            if time_since > 86400:
                tot += b['income']
                collected.append(f"✅ {b['business_name']}: +{fmt_money(b['income'])}")
                await conn.execute("UPDATE businesses SET last_collect_time=$1 WHERE id=$2", now, b['id'])
            else:
                remaining = 86400 - time_since
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                waiting.append(f"⏳ {b['business_name']} — через {hours}ч {minutes}мин")
    
    if tot > 0:
        msg = f"💼 <b>Прибыль собрана!</b>\n\n" + "\n".join(collected) + f"\n\n💰 Итого: <b>+{fmt_money(tot)}</b>"
        if waiting:
            msg += f"\n\n⏳ <b>Следующий сбор:</b>\n" + "\n".join(waiting)
        await m.answer(msg, parse_mode="HTML")
    else:
        msg = "⏳ <b>Рано собирать!</b>\n\n" + "\n".join(waiting)
        await m.answer(msg, parse_mode="HTML")

@dp.message(Command("cars"))
async def cmd_cars(m: Message):
    t = "🚗 <b>Автосалон:</b>\n\n"
    for k, v in CARS.items():
        t += f"🔸 {v['name']} — {fmt_money(v['price'])} → /buycar {k}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buycar"))
async def cmd_buycar(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer(" В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2 or args[1] not in CARS:
        return await m.answer("/cars")
    c = CARS[args[1]]
    u = await get_user(cid, uid)
    if u['balance'] < c['price']:
        return await m.answer(f" Нужно {fmt_money(c['price'])}")
    await update_balance(cid, uid, -c['price'])
    await set_car(cid, uid, args[1], c['name'])
    await m.answer(f"🎉 Куплена <b>{c['name']}</b>!", parse_mode="HTML")

@dp.message(Command("mycar"))
async def cmd_mycar(m: Message):
    c = await get_car(m.chat.id, m.from_user.id)
    await m.answer(f"🅿️ <b>Твои машины:</b>\n{c}" if c else "🅿️ Пусто. /cars", parse_mode="HTML")

@dp.message(Command("inv"))
async def cmd_inv(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    async with pool.acquire() as conn:
        its = await conn.fetch("SELECT item_name, rarity FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
    if not its:
        return await m.answer("🎒 Пусто.")
    t = "🎒 <b>Инвентарь:</b>\n\n"
    for i in its:
        em = "" if i['rarity'] == "legendary" else "🔵" if i['rarity'] == "rare" else "🟢"
        t += f"{em} {i['item_name']}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("rating"))
async def cmd_rating(m: Message):
    cid = m.chat.id
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT u.user_id, u.balance, us.username FROM users u LEFT JOIN usernames us ON u.chat_id=us.chat_id AND u.user_id=us.user_id WHERE u.chat_id=$1 ORDER BY u.balance DESC LIMIT 10", cid)
    t = "🏆 <b>Рейтинг богачей:</b>\n\n"
    for i, r in enumerate(rows, 1):
        uname = r['username'] or f"User{r['user_id']}"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        t += f"{medal} <b>{uname}</b> — {fmt_money(r['balance'])}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("give"))
async def cmd_give(m: Message):
    cid = m.chat.id
    if m.from_user.id not in ADMIN_IDS:
        return
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message:
        return await m.answer("/give сумма (ответ)")
    try:
        amt = int(args[1])
    except:
        return await m.answer("❌ Число!")
    await update_balance(cid, m.reply_to_message.from_user.id, amt)
    await m.answer(f"✅ Выдано {fmt_money(amt)}.")

@dp.message(Command("bank"))
async def cmd_bank(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    bd = await get_bank(cid, uid)
    interest, _ = await calc_interest(bd['deposit'], bd['last_interest_time'])
    t = (
        f"🏦 <b>Банк «Сарапулка»</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 На счету: <b>{fmt_money(bd['deposit'])}</b>\n"
        f"📈 Начислено процентов: <b>+{fmt_money(interest)}</b>\n"
        f"💹 Ставка: 1% в сутки\n\n"
        f" /deposit сумма — положить\n"
        f"📤 /withdraw сумма — снять\n\n"
        f"⚠️ Деньги в банке нельзя украсть!\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("deposit"))
async def cmd_deposit(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("/deposit сумма")
    try:
        amt = int(args[1])
    except:
        return await m.answer("❌ Число!")
    if amt < 100:
        return await m.answer("❌ Мин. 100")
    u = await get_user(cid, uid)
    if u['balance'] < amt:
        return await m.answer(f"❌ Мало ({fmt_money(u['balance'])})")
    await update_balance(cid, uid, -amt)
    await update_bank(cid, uid, amt)
    bd = await get_bank(cid, uid)
    await m.answer(f" Вклад: <b>{fmt_money(amt)}</b>\nНа счету: <b>{fmt_money(bd['deposit'])}</b>", parse_mode="HTML")

@dp.message(Command("withdraw"))
async def cmd_withdraw(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("/withdraw сумма")
    try:
        amt = int(args[1])
    except:
        return await m.answer("❌ Число!")
    bd = await get_bank(cid, uid)
    interest, new_time = await calc_interest(bd['deposit'], bd['last_interest_time'])
    if bd['deposit'] < amt:
        return await m.answer(f"❌ На счету {fmt_money(bd['deposit'])}")
    async with pool.acquire() as conn:
        await conn.execute("UPDATE bank SET deposit=deposit-$1, last_interest_time=$2 WHERE chat_id=$3 AND user_id=$4", amt, new_time, cid, uid)
    if interest > 0 and bd['deposit'] - amt > 0:
        await update_bank(cid, uid, interest)
        await update_balance(cid, uid, interest)
    await update_balance(cid, uid, amt)
    nb = await get_bank(cid, uid)
    t = f"📤 Снято: <b>{fmt_money(amt)}</b>"
    if interest > 0:
        t += f"\n📈 Проценты: +{fmt_money(interest)}"
    t += f"\nОстаток: <b>{fmt_money(nb['deposit'])}</b>"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("credit"))
async def cmd_credit(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        return await m.answer(
            "💳 <b>Взять кредит</b>\n\n"
            "Использование: <b>/credit сумма</b>\n\n"
            "• Макс: 10x баланса\n"
            "• 2% в день\n"
            "• Срок: 7 дней\n"
            "• Просрочка = арест",
            parse_mode="HTML"
        )
    try:
        amount = int(args[1])
    except:
        return await m.answer("❌ Число!")
    if amount < 100:
        return await m.answer(" Мин: 100")
    loan = await get_loan(cid, uid)
    if loan['amount'] > 0:
        return await m.answer(f"❌ Уже есть кредит! Долг: {fmt_money(loan['amount'])}")
    user = await get_user(cid, uid)
    max_loan = user['balance'] * CREDIT_MULTIPLIER
    if amount > max_loan:
        return await m.answer(f"❌ Макс: {fmt_money(max_loan)}")
    taken_at = time.time()
    due_date = taken_at + (CREDIT_TERM_DAYS * 86400)
    await update_loan(cid, uid, amount, 0, taken_at, due_date)
    await update_balance(cid, uid, amount)
    await m.answer(
        f"💳 <b>Кредит оформлен!</b>\n\n"
        f"💰 Получено: {fmt_money(amount)}\n"
        f"📈 Процент: 2% в день\n"
        f"⏰ Вернуть до: {format_date(due_date)}\n\n"
        f"⚠️ Просрочка = АРЕСТ ИМУЩЕСТВА!",
        parse_mode="HTML"
    )

@dp.message(Command("debt"))
async def cmd_debt(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    loan = await get_loan(cid, uid)
    if loan['amount'] == 0:
        return await m.answer("✅ Нет кредитов!")
    total_debt = loan['amount'] + loan['interest']
    days_left = int((loan['due_date'] - time.time()) / 86400)
    if days_left < 0:
        days_text = "🚔 ПРОСРОЧЕНО!"
    elif days_left <= 2:
        days_text = f"️ Осталось: {days_left} дн."
    else:
        days_text = f"Осталось: {days_left} дн."
    await m.answer(
        f"💳 <b>Ваш долг</b>\n\n"
        f"📊 Основной: {fmt_money(loan['amount'])}\n"
        f"📈 Проценты: {fmt_money(loan['interest'])}\n"
        f"💰 Итого: <b>{fmt_money(total_debt)}</b>\n\n"
        f"{days_text}\n\n"
        f"/repay сумма\n"
        f"/repay_all",
        parse_mode="HTML"
    )

@dp.message(Command("repay"))
async def cmd_repay(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("💳 <b>/repay сумма</b>", parse_mode="HTML")
    try:
        amount = int(args[1])
    except:
        return await m.answer("❌ Число!")
    if amount <= 0:
        return await m.answer("❌ >0!")
    loan = await get_loan(cid, uid)
    if loan['amount'] == 0:
        return await m.answer("✅ Нет кредитов!")
    user = await get_user(cid, uid)
    if user['balance'] < amount:
        return await m.answer(f"❌ Мало ({fmt_money(user['balance'])})")
    total_debt = loan['amount'] + loan['interest']
    if amount > total_debt:
        amount = total_debt
    remaining = amount
    interest_paid = min(remaining, loan['interest'])
    remaining -= interest_paid
    principal_paid = min(remaining, loan['amount'])
    new_interest = loan['interest'] - interest_paid
    new_amount = loan['amount'] - principal_paid
    await update_balance(cid, uid, -amount)
    if new_amount <= 0:
        await clear_loan(cid, uid)
        await m.answer(
            f"✅ Кредит погашен!\n"
            f"Списано: {fmt_money(amount)}\n"
            f"Проценты: {fmt_money(interest_paid)}\n"
            f"Долг: {fmt_money(principal_paid)}",
            parse_mode="HTML"
        )
    else:
        await update_loan(cid, uid, new_amount, new_interest, loan['taken_at'], loan['due_date'])
        await m.answer(
            f"✅ Частично погашено!\n"
            f"Списано: {fmt_money(amount)}\n"
            f"Остаток: <b>{fmt_money(new_amount + new_interest)}</b>",
            parse_mode="HTML"
        )

@dp.message(Command("repay_all"))
async def cmd_repay_all(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    loan = await get_loan(cid, uid)
    if loan['amount'] == 0:
        return await m.answer("✅ Нет кредитов!")
    total_debt = loan['amount'] + loan['interest']
    user = await get_user(cid, uid)
    if user['balance'] < total_debt:
        return await m.answer(f"❌ Нужно: {fmt_money(total_debt)}\nУ вас: {fmt_money(user['balance'])}")
    await update_balance(cid, uid, -total_debt)
    await clear_loan(cid, uid)
    await m.answer(f"✅ Кредит погашен!\nСписано: <b>{fmt_money(total_debt)}</b>", parse_mode="HTML")

@dp.message(Command("bailout"))
async def cmd_bailout(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    loan = await get_loan(cid, uid)
    if loan['amount'] == 0:
        return await m.answer("✅ Нет кредитов.\nЕсли арестованы — начинайте заново через /work!")
    total_debt = loan['amount'] + loan['interest']
    await m.answer(
        f"🚔 <b>Выкуп</b>\n\n"
        f"Долг: {fmt_money(total_debt)}\n"
        f"Выкуп: {fmt_money(int(total_debt * 2))}\n\n"
        f"⚠️ Только ДО ареста!\n"
        f"/repay_all",
        parse_mode="HTML"
    )

@dp.message(Command("craft"))
async def cmd_craft(m: Message):
    t = "🔨 <b>Крафт:</b>\n\n"
    for k, v in CRAFT_RECIPES.items():
        req = ", ".join([f"{c}× {n}" for n, c in v["requires"].items()])
        t += f"🔹 {v['name']} ({req}) → /craft_item {k}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("craft_item"))
async def cmd_craft_item(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("/craft_item diamond")
    ik = args[1]
    if ik not in CRAFT_RECIPES:
        return await m.answer("❌ Неизвестный рецепт")
    rec = CRAFT_RECIPES[ik]
    async with pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
    inv = {}
    for i in items:
        inv[i['item_name']] = inv.get(i['item_name'], 0) + 1
    for rn, rc in rec["requires"].items():
        if inv.get(rn, 0) < rc:
            return await m.answer(f"❌ Нужно {rc}× {rn} (есть {inv.get(rn, 0)})")
    async with pool.acquire() as conn:
        for rn, rc in rec["requires"].items():
            await conn.execute("DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3 LIMIT $4)", cid, uid, rn, rc)
        await conn.execute("INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,'crafted',$4)", cid, uid, rec["name"], rec["rarity"])
    await m.answer(f"✅ Скрафчено: <b>{rec['name']}</b>", parse_mode="HTML")

@dp.message(Command("trade"))
async def cmd_trade(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 4 or not m.reply_to_message:
        return await m.answer("/trade @user предмет кол-во (ответ)")
    tid = m.reply_to_message.from_user.id
    iname = args[2]
    try:
        cnt = int(args[3])
    except:
        return await m.answer("❌ Число!")
    if cnt <= 0 or tid == uid:
        return await m.answer("❌ Ошибка")
    async with pool.acquire() as conn:
        have = await conn.fetchval("SELECT COUNT(*) FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3", cid, uid, iname)
    if have < cnt:
        return await m.answer(f"❌ Нет {cnt}× {iname}")
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT item_name, item_type, rarity FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3 LIMIT $4", cid, uid, iname, cnt)
        await conn.execute("DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3 LIMIT $4)", cid, uid, iname, cnt)
        for row in rows:
            await conn.execute("INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,$4,$5)", cid, tid, row['item_name'], row['item_type'], row['rarity'])
    await m.answer(f"✅ Передано {cnt}× {iname}", parse_mode="HTML")

@dp.message(Command("education"))
async def cmd_education(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    edu = await get_education(cid, uid)
    t = "🎓 <b>Образование:</b>\n\n"
    for k, c in COURSES.items():
        done = k in edu['completed_courses'] or (k == 'mba' and edu['has_mba'])
        st = "✅" if done else "🔒"
        t += f"{st} {c['name']} — {fmt_money(c['price'])} → /buy_course {k}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buy_course"))
async def cmd_buy_course(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2 or args[1] not in COURSES:
        return await m.answer("/education")
    ck = args[1]
    c = COURSES[ck]
    edu = await get_education(cid, uid)
    if ck in edu['completed_courses'] or (ck == 'mba' and edu['has_mba']):
        return await m.answer("✅ Уже пройдено")
    u = await get_user(cid, uid)
    if u['balance'] < c['price']:
        return await m.answer(f"❌ Нужно {fmt_money(c['price'])}")
    await update_balance(cid, uid, -c['price'])
    exam_sessions[f"{cid}_{uid}"] = {"course": ck, "question": 0, "correct": 0}
    q = c['questions'][0]
    answers_text = ' | '.join([f'{i+1}. {a}' for i, a in enumerate(q['a'])])
    await m.answer(
        f"✅ Курс оплачен!\n\n"
        f"📝 <b>Экзамен:</b> нужно 2 из 3\n\n"
        f"Вопрос 1:\n"
        f"<b>{q['q']}</b>\n\n"
        f"{answers_text}\n\n"
        f"Напишите номер (1, 2, 3)",
        parse_mode="HTML"
    )

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_exam_answer(m: Message):
    if m.chat.type not in ['group', 'supergroup']:
        return
    cid, uid = m.chat.id, m.from_user.id
    ek = f"{cid}_{uid}"
    if ek not in exam_sessions:
        return
    ex = exam_sessions[ek]
    c = COURSES[ex['course']]
    try:
        ans = int(m.text) - 1
    except:
        return await m.answer("❌ Номер (1, 2, 3)")
    if ans < 0 or ans > 2:
        return await m.answer("❌ Номер (1, 2, 3)")
    q = c['questions'][ex['question']]
    if ans == q['correct']:
        ex['correct'] += 1
        await m.answer("✅ Верно!")
    else:
        await m.answer(f"❌ Неверно! Ответ: {q['a'][q['correct']]}")
    ex['question'] += 1
    if ex['question'] < 3:
        q = c['questions'][ex['question']]
        answers_text = ' | '.join([f'{i+1}. {a}' for i, a in enumerate(q['a'])])
        await m.answer(
            f"Вопрос {ex['question']+1}:\n"
            f"<b>{q['q']}</b>\n\n"
            f"{answers_text}\n\n"
            f"Напишите номер (1, 2, 3)",
            parse_mode="HTML"
        )
    else:
        if ex['correct'] >= 2:
            await complete_course(cid, uid, ex['course'])
            await m.answer(f"🎉 <b>Сдано!</b> Курс <b>{c['name']}</b> завершён!", parse_mode="HTML")
        else:
            await m.answer(f"😔 <b>Провал.</b> {ex['correct']}/3\n/buy_course {ex['course']}", parse_mode="HTML")
        del exam_sessions[ek]

@dp.message(Command("fix_income"))
async def cmd_fix_income(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return await m.answer("❌ Только для админов!")
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT business_name, income FROM businesses GROUP BY business_name, income ORDER BY income")
        old = "📋 <b>БЫЛО:</b>\n" + "\n".join([f"• {r['business_name']}: {r['income']}" for r in rows])
        await conn.execute("UPDATE businesses SET income = 83 WHERE business_name LIKE '%Газетн%'")
        await conn.execute("UPDATE businesses SET income = 333 WHERE business_name LIKE '%Шаурм%'")
        await conn.execute("UPDATE businesses SET income = 833 WHERE business_name LIKE '%Кофейн%'")
        await conn.execute("UPDATE businesses SET income = 2500 WHERE business_name LIKE '%Крипто%'")
        await conn.execute("UPDATE businesses SET income = 8333 WHERE business_name LIKE '%Отел%'")
        rows = await conn.fetch("SELECT business_name, income FROM businesses GROUP BY business_name, income ORDER BY income")
        new = "📋 <b>СТАЛО:</b>\n" + "\n".join([f"• {r['business_name']}: {r['income']}" for r in rows])
    await m.answer(f"{old}\n\n✅ Обновлено!\n\n{new}", parse_mode="HTML")

@dp.message(Command("pay_mafia"))
async def cmd_pay_mafia(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    async with pool.acquire() as conn:
        threat = await conn.fetchrow(
            "SELECT * FROM mafia_threats WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE AND deadline > $3",
            cid, uid, time.time()
        )
        if not threat:
            return await m.answer("❌ У вас нет активных угроз от мафии!")
        ransom = threat['ransom_amount']
        user = await get_user(cid, uid)
        bank = await get_bank(cid, uid)
        total_available = user['balance'] + bank['deposit']
        if total_available < ransom:
            return await m.answer(
                f"❌ Недостаточно средств!\n"
                f"Нужно: {fmt_money(ransom)}\n"
                f"У вас: {fmt_money(total_available)}\n\n"
                f"🕴️ Мафия заберёт ваш актив через {format_time(int(threat['deadline'] - time.time()))}"
            )
        paid_from_balance = min(ransom, user['balance'])
        remaining = ransom - paid_from_balance
        if paid_from_balance > 0:
            await update_balance(cid, uid, -paid_from_balance)
        if remaining > 0:
            await update_bank(cid, uid, -remaining)
        await conn.execute("UPDATE mafia_threats SET paid=TRUE WHERE id=$1", threat['id'])
        await m.answer(
            f"✅ <b>Выкуп оплачен!</b>\n\n"
            f"💰 Списано: <b>{fmt_money(ransom)}</b>\n"
            f"🕴️ Мафия ушла довольной...\n\n"
            f"💡 Совет: храните деньги в банке, чтобы снизить риск повторного визита!",
            parse_mode="HTML"
        )

def create_deck():
    suits = ['♠', '♥', '♦', '♣']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    deck = [(r, s) for s in suits for r in ranks]
    random.shuffle(deck)
    return deck

def card_value(card):
    r = card[0]
    if r in ['J', 'Q', 'K']:
        return 10
    if r == 'A':
        return 11
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
async def blackjack_start(m: Message, state: FSMContext):
    cid, uid = m.chat.id, m.from_user.id
    if cid in bj_tables:
        return await m.answer("🎰 Игра идёт!")
    u = await get_user(cid, uid)
    if u['balance'] < BJ_MIN_BALANCE:
        return await m.answer(f"❌ Нужно {BJ_MIN_BALANCE}+ ({fmt_money(u['balance'])})")
    bj_tables[cid] = {"players": {uid: {"name": m.from_user.first_name, "bet": 0, "cards": [], "stand": False, "busted": False}}, "order": [uid], "stage": "waiting", "creator": uid}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"bj_join_{cid}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"bj_cancel_{cid}")]
    ])
    await m.answer(
        f" <b>Игорёчек открывает стол!</b>\n\n"
        f" {m.from_user.first_name}\n"
        f"👥 1/{BJ_MAX_PLAYERS}\n"
        f"⏳ {BJ_WAIT_TIME} сек\n\n"
        f"Нажмите кнопку!",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(BlackjackStates.waiting)
    await asyncio.sleep(BJ_WAIT_TIME)
    if cid not in bj_tables:
        return
    t = bj_tables[cid]
    if len(t["players"]) < 2:
        await m.answer("😔 Мало игроков.")
        del bj_tables[cid]
        await state.clear()
        return
    t["stage"] = "betting"
    pl = ", ".join(p["name"] for p in t["players"].values())
    for uid in t["order"]:
        bk = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="100", callback_data=f"bet_100_{cid}"), InlineKeyboardButton(text="200", callback_data=f"bet_200_{cid}")],
            [InlineKeyboardButton(text="500", callback_data=f"bet_500_{cid}"), InlineKeyboardButton(text="1000", callback_data=f"bet_1000_{cid}")]
        ])
        try:
            await bot.send_message(uid, f"🎩 <b>Ваша ставка?</b>", reply_markup=bk, parse_mode="HTML")
        except:
            await m.answer(f"⚠️ {t['players'][uid]['name']}, напишите в ЛС!")
    await m.answer(f"🎩 <b>Игроки:</b> {pl}\n\n💰 Проверьте личку!", parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith("bj_join_"))
async def blackjack_join(cb: types.CallbackQuery, state: FSMContext):
    cid = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    if cid not in bj_tables:
        return await cb.answer("Стол закрыт!", show_alert=True)
    t = bj_tables[cid]
    if t["stage"] != "waiting":
        return await cb.answer("Началась!", show_alert=True)
    if uid in t["players"]:
        return await cb.answer("Вы уже тут!", show_alert=True)
    if len(t["players"]) >= BJ_MAX_PLAYERS:
        return await cb.answer("Мест нет!", show_alert=True)
    u = await get_user(cid, uid)
    if u['balance'] < BJ_MIN_BALANCE:
        return await cb.answer(f"Нужно {BJ_MIN_BALANCE}+", show_alert=True)
    t["players"][uid] = {"name": cb.from_user.first_name, "bet": 0, "cards": [], "stand": False, "busted": False}
    t["order"].append(uid)
    await cb.answer("✅ Присоединились!")
    pl = "\n".join([f"• {p['name']}" for p in t["players"].values()])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"bj_join_{cid}")],
        [InlineKeyboardButton(text=" Отменить", callback_data=f"bj_cancel_{cid}")]
    ])
    try:
        await cb.message.edit_text(f"🎩 <b>Игроки ({len(t['players'])}/{BJ_MAX_PLAYERS}):\n{pl}\n\n Ждём...</b>", reply_markup=kb, parse_mode="HTML")
    except:
        pass

@dp.callback_query(lambda c: c.data.startswith("bj_cancel_"))
async def blackjack_cancel(cb: types.CallbackQuery, state: FSMContext):
    cid = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    if cid not in bj_tables:
        return await cb.answer("Завершена!", show_alert=True)
    t = bj_tables[cid]
    if uid != t["creator"]:
        return await cb.answer("Только создатель!", show_alert=True)
    if t["stage"] == "playing":
        return await cb.answer("Игра началась!", show_alert=True)
    refunded = []
    for pid, pd in t["players"].items():
        if pd["bet"] > 0:
            await update_balance(cid, pid, pd["bet"])
            refunded.append(f"• {pd['name']}: +{fmt_money(pd['bet'])}")
    del bj_tables[cid]
    await state.clear()
    rt = "\n".join(refunded) if refunded else "Никто не поставил"
    try:
        await cb.message.edit_text(f"❌ <b>Отменена!</b>\n\n {cb.from_user.first_name}\n\n Возврат:\n{rt}", parse_mode="HTML")
    except:
        pass
    await cb.answer("✅ Отменена!")

@dp.callback_query(lambda c: c.data.startswith("bet_"))
async def blackjack_bet(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split("_")
    bet = int(parts[1])
    cid = int(parts[2])
    uid = cb.from_user.id
    if cid not in bj_tables:
        return await cb.answer("Нет игры!", show_alert=True)
    t = bj_tables[cid]
    if uid not in t["players"]:
        return await cb.answer("Не в игре!", show_alert=True)
    if t["players"][uid]["bet"] > 0:
        return await cb.answer("Ставка есть!", show_alert=True)
    u = await get_user(cid, uid)
    if u['balance'] < bet:
        return await cb.answer(f"Мало ({fmt_money(u['balance'])})", show_alert=True)
    await update_balance(cid, uid, -bet)
    t["players"][uid]["bet"] = bet
    try:
        await cb.message.edit_text(f"✅ Ставка: <b>{bet}</b>. Ждём...", parse_mode="HTML")
    except:
        pass
    await cb.answer(f"Ставка {bet} принята!")
    if all(p["bet"] > 0 for p in t["players"].values()):
        await blackjack_deal(cid, state)

async def blackjack_deal(cid, state):
    t = bj_tables[cid]
    t["deck"] = create_deck()
    for uid in t["order"]:
        t["players"][uid]["cards"] = [t["deck"].pop(), t["deck"].pop()]
    t["dealer"] = [t["deck"].pop(), t["deck"].pop()]
    t["stage"] = "playing"
    pi = "\n".join([f"👤 {p['name']}: {p['bet']}" for p in t["players"].values()])
    await bot.send_message(cid, f"🎩 <b>Карты розданы!</b>\n\n🤖 Мои: {show_cards(t['dealer'], True)}\n\n{pi}\n\n Ходит: <b>{t['players'][t['order'][0]]['name']}</b>", parse_mode="HTML")
    await state.set_state(BlackjackStates.playing)
    await blackjack_player_turn(cid, t["order"][0], state)

async def blackjack_player_turn(cid, uid, state):
    t = bj_tables[cid]
    p = t["players"][uid]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Ещё", callback_data=f"hit_{uid}_{cid}"), InlineKeyboardButton(text="✋ Хватит", callback_data=f"stand_{uid}_{cid}")]
    ])
    await bot.send_message(uid, f"🎩 <b>Ваш ход!</b>\n\n🃏 Ваши: {show_cards(p['cards'])}\n🔢 Сумма: <b>{calc_score(p['cards'])}</b>\n💰 Ставка: {p['bet']}\n\n🎴 Карта Игорёчка: {t['dealer'][0][0]}{t['dealer'][0][1]}", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith("hit_") or c.data.startswith("stand_"))
async def blackjack_hit_stand(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split("_")
    act = parts[0]
    uid = int(parts[1])
    cid = int(parts[2])
    if cid not in bj_tables:
        return await cb.answer("Нет игры!", show_alert=True)
    t = bj_tables[cid]
    p = t["players"][uid]
    if act == "hit":
        c = t["deck"].pop()
        p["cards"].append(c)
        sc = calc_score(p["cards"])
        await cb.message.edit_text(f"🎩 Взял карту!\n\n +{c[0]}{c[1]}\n📊 {show_cards(p['cards'])}\n🔢 Сумма: <b>{sc}</b>", parse_mode="HTML")
        if sc > 21:
            p["stand"] = True
            p["busted"] = True
            await cb.message.answer(f"💥 <b>Перебор ({sc})!</b>", parse_mode="HTML")
            await blackjack_next_turn(cid, state)
        elif sc == 21:
            p["stand"] = True
            await cb.message.answer(f"🎉 <b>21!</b>")
            await blackjack_next_turn(cid, state)
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" Ещё", callback_data=f"hit_{uid}_{cid}"), InlineKeyboardButton(text="✋ Хватит", callback_data=f"stand_{uid}_{cid}")]
            ])
            await cb.message.answer(f"💰 Сумма: {sc}. Ещё?", reply_markup=kb)
    elif act == "stand":
        p["stand"] = True
        await cb.message.edit_text(f"✋ Остановился на <b>{calc_score(p['cards'])}</b>", parse_mode="HTML")
        await blackjack_next_turn(cid, state)

async def blackjack_next_turn(cid, state):
    t = bj_tables[cid]
    nxt = next((u for u in t["order"] if not t["players"][u]["stand"]), None)
    if nxt:
        await bot.send_message(cid, f"🎮 Ходит: <b>{t['players'][nxt]['name']}</b>", parse_mode="HTML")
        await blackjack_player_turn(cid, nxt, state)
    else:
        await blackjack_dealer_play(cid, state)

async def blackjack_dealer_play(cid, state):
    t = bj_tables[cid]
    await bot.send_message(cid, f"🎩 <b>Ход Игорёчка!</b>\n\n🤖 Мои: {show_cards(t['dealer'])}", parse_mode="HTML")
    while calc_score(t["dealer"]) < BJ_DEALER_STOP:
        await asyncio.sleep(1)
        c = t["deck"].pop()
        t["dealer"].append(c)
        await bot.send_message(cid, f"🎩 Берёт: <b>{c[0]}{c[1]}</b> → <b>{calc_score(t['dealer'])}</b>", parse_mode="HTML")
    ds = calc_score(t["dealer"])
    res = []
    for uid in t["order"]:
        p = t["players"][uid]
        ps = calc_score(p["cards"])
        bet = p["bet"]
        if p["busted"]:
            res.append(f"❌ {p['name']}: перебор ({ps})")
        elif ds > 21:
            await update_balance(cid, uid, bet*2)
            res.append(f"🎉 {p['name']}: Игорёчек перебрал! +{bet}")
        elif ps > ds:
            await update_balance(cid, uid, bet*2)
            res.append(f"🏆 {p['name']}: победа! +{bet}")
        elif ps == ds:
            await update_balance(cid, uid, bet)
            res.append(f"🤝 {p['name']}: ничья")
        else:
            res.append(f"😢 {p['name']}: проигрыш")
    if ds > 21:
        fn = "😱 Перебрал!"
    elif any("победа" in r for r in res):
        fn = "🎉 Поздравляем!"
    elif any("проигрыш" in r for r in res):
        fn = "🎩 Забирает ставки!"
    else:
        fn = " Ничья!"
    await bot.send_message(cid, f"🎩 <b>{fn}</b>\n\n🤖 Карты: {show_cards(t['dealer'])} ({ds})\n\n📊 Результаты:\n" + "\n".join(res), parse_mode="HTML")
    del bj_tables[cid]
    await state.clear()

@dp.message()
async def auto_register(m: Message):
    if m.chat.type not in ['group', 'supergroup']:
        return
    await get_user(m.chat.id, m.from_user.id)

@dp.message(F.new_chat_members)
async def on_user_join(m: Message):
    cid = m.chat.id
    for user in m.new_chat_members:
        if user.is_bot:
            if user.id == int(API_TOKEN.split(':')[0]):
                await m.answer(" Привет! Я экономический бот. /start")
            continue
        await get_user(cid, user.id)
        await save_username(cid, user.id, user.full_name)

async def main():
    await init_db()
    print("🤖 Бот запущен!")
    await start_web_server()
    asyncio.create_task(polling_health_check())
    asyncio.create_task(auto_lottery_loop())
    asyncio.create_task(loan_interest_loop())
    asyncio.create_task(rob_debt_check_loop())
    asyncio.create_task(mafia_threat_loop())
    asyncio.create_task(mafia_check_loop())
    asyncio.create_task(jail_fine_check_loop())
    await dp.start_polling(bot, timeout=30, drop_pending_updates=True, allowed_updates=["message", "callback_query", "my_chat_member"])

if __name__ == "__main__":
    asyncio.run(main())
