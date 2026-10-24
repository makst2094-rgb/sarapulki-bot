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
ROULETTE_TABLES = {}

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

# ==================== РУССКАЯ РУЛЕТКА ====================
ROULETTE_WAIT_TIME = 60
ROULETTE_MIN_PLAYERS = 2
ROULETTE_MAX_PLAYERS = 6
ROULETTE_BULLET_CHANCE = 1/6

# ==================== БИРЖА АКЦИЙ ====================
STOCK_MARKET_EVENTS = [
    {"name": "📈 Рост спроса", "effect": 1.3},
    {"name": "📉 Падение рынка", "effect": 0.7},
    {"name": " Вирусный тренд", "effect": 1.5},
    {"name": "🔥 Конкурент демпингует", "effect": 0.8},
    {"name": "💼 Инвестфонд вошёл", "effect": 1.4},
]

CRAFT_RECIPES = {
    "diamond": {"name": "💎 Алмаз", "requires": {"📄 Бумага": 10}, "rarity": "rare"},
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
        "name": "💻 Курс программирования",
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
        "name": "⚖️ Курс адвоката",
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
    "course": {"name": "📚 Уровень+", "price": 0, "type": "level_up"},
    "coffee": {"name": "☕ Кофе-машина", "price": 0, "type": "cooldown_reduce"}
}

MARKET = {
    "case_basic": {"name": "📦 Кейс", "price": 200, "type": "case"},
    "biz_newspaper": {"name": "📰 Газетный киоск", "price": 500, "type": "business", "income": 83},
    "biz_shawarma": {"name": "🌯 Шаурма", "price": 2000, "type": "business", "income": 333},
    "biz_coffee": {"name": "☕ Кофейня", "price": 5000, "type": "business", "income": 833},
    "biz_crypto": {"name": "💻 Крипто-ферма", "price": 15000, "type": "business", "income": 2500},
    "biz_hotel": {"name": "🏨 Отель", "price": 50000, "type": "business", "income": 8333},
    "biz_pizza": {"name": "🍕 Пиццерия", "price": 10000, "type": "business", "income": 1900},
    "biz_taxi": {"name": "🚕 Таксопарк", "price": 30000, "type": "business", "income": 7899},
    "biz_pharmacy": {"name": "💊 Аптека", "price": 75000, "type": "business", "income": 18789},
    "biz_construction": {"name": "🏗️ Стройфирма", "price": 150000, "type": "business", "income": 35000},
    "biz_spaceport": {"name": "🚀 Космодром", "price": 500000, "type": "business", "income": 120000},
    "biz_casino": {"name": "🎰 Казино", "price": 1000000, "type": "business", "income": 300000}
}

CARS = {
    "ok": {"name": "🚲 Ока", "price": 3000},
    "priora": {"name": "🚘 Приора", "price": 10000},
    "bmw": {"name": "️ BMW", "price": 40000},
    "gelik": {"name": "🚙 Гелик", "price": 80000},
    "lambo": {"name": "🏎️ Lamborghini", "price": 200000},
    "rolls": {"name": "🚘 Rolls-Royce", "price": 500000},
    "bentley": {"name": "🚘 Bentley", "price": 800000},
    "ferrari": {"name": "🏎️ Ferrari", "price": 1200000},
    "bugatti": {"name": "🏎️ Bugatti", "price": 2500000},
    "yacht_car": {"name": "🛥️ Яхта на колёсах", "price": 5000000}
}

# ==================== РЕДКИЕ ПРЕДМЕТЫ ДЛЯ АУКЦИОНА ====================
RARE_CARS = {
    "gold_bmw": {"name": "✨ Золотой BMW", "price": 500000, "rarity": "legendary"},
    "diamond_lambo": {"name": "💎 Бриллиантовый Lamborghini", "price": 1500000, "rarity": "legendary"},
    "platinum_rolls": {"name": "👑 Платиновый Rolls-Royce", "price": 3000000, "rarity": "legendary"},
    "space_ship": {"name": "🚀 Космический корабль", "price": 10000000, "rarity": "mythic"},
}

RARE_BUSINESSES = {
    "biz_oil": {"name": "🛢️ Нефтяная вышка", "income": 50000, "price": 2000000, "rarity": "legendary"},
    "biz_bank": {"name": "🏦 Частный банк", "income": 100000, "price": 5000000, "rarity": "legendary"},
    "biz_space": {"name": "🌌 Космическая станция", "income": 250000, "price": 15000000, "rarity": "mythic"},
}

RARE_ITEMS = {
    "golden_ticket": {"name": "🎫 Золотой билет", "desc": "Даёт x2 доход с бизнеса на 24 часа", "rarity": "legendary"},
    "diamond_key": {"name": "🔑 Бриллиантовый ключ", "desc": "Открывает секретный кейс", "rarity": "legendary"},
    "crown": {"name": " Корона магната", "desc": "Уникальный титул и +10% к зарплате", "rarity": "mythic"},
}

ACHIEVEMENTS = {
    "first_1000": {"name": "💰 Первая тысяча", "desc": "Накопи 1 000 сарапулок", "icon": "💵"},
    "first_10k": {"name": "💰 Десятка", "desc": "Накопи 10 000 сарапулок", "icon": "🥈"},
    "first_100k": {"name": "💰 Сотня", "desc": "Накопи 100 000 сарапулок", "icon": "🥇"},
    "millionaire": {"name": "💰 Миллионер", "desc": "Накопи 1 000 000 сарапулок", "icon": ""},
    "first_business": {"name": "🏪 Первый бизнес", "desc": "Купи первый бизнес", "icon": "🏪"},
    "business_empire": {"name": " Бизнес-империя", "desc": "Владей 10 бизнесами", "icon": "👑"},
    "first_car": {"name": "🚗 Первая машина", "desc": "Купи первую машину", "icon": ""},
    "car_collector": {"name": "🏆 Автоколлекционер", "desc": "Купи 5 разных машин", "icon": "🏆"},
    "first_course": {"name": "🎓 Студент", "desc": "Пройди первый курс", "icon": "🎓"},
    "all_courses": {"name": "🎓 Профессор", "desc": "Пройди все курсы", "icon": "🎓"},
    "mba_graduate": {"name": "🎓 MBA", "desc": "Получи степень MBA", "icon": "🎯"},
    "mafia_survivor": {"name": "🛡️ Выжил после мафии", "desc": "Отбей атаку мафии", "icon": "🛡️"},
    "roulette_first": {"name": " Первая рулетка", "desc": "Сыграй в русскую рулетку", "icon": "🔫"},
    "roulette_survivor": {"name": "🎯 Везучий стрелок", "desc": "Выживи в рулетке 10 раз", "icon": "🎯"},
    "roulette_winner": {"name": "🏆 Победитель рулетки", "desc": "Выиграй в рулетке 5 раз", "icon": "🏆"},
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
        # Удаляем старые проблемные таблицы перед созданием
        await conn.execute("DROP TABLE IF EXISTS stock_holdings CASCADE")
        await conn.execute("DROP TABLE IF EXISTS stocks CASCADE")
        await conn.execute("DROP TABLE IF EXISTS marketplace CASCADE")
        await conn.execute("DROP TABLE IF EXISTS robbery CASCADE")
        print("🗑️ Старые таблицы удалены")

        await conn.execute("""CREATE TABLE IF NOT EXISTS users (chat_id BIGINT, user_id BIGINT, balance INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS profiles (chat_id BIGINT, user_id BIGINT, job_key TEXT DEFAULT 'novice', level INTEGER DEFAULT 1, last_work_time REAL DEFAULT 0, coffee_level INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        try:
            await conn.execute("ALTER TABLE profiles ADD COLUMN coffee_level INTEGER DEFAULT 0")
        except: pass
        
        await conn.execute("""CREATE TABLE IF NOT EXISTS inventory (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, item_name TEXT, item_type TEXT, rarity TEXT DEFAULT 'common')""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS businesses (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, business_name TEXT, income INTEGER, last_collect_time REAL DEFAULT 0)""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS garage (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, car_key TEXT, car_name TEXT)""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS daily_bonus (chat_id BIGINT, user_id BIGINT, last_claim REAL DEFAULT 0, streak INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        
        await conn.execute("""CREATE TABLE robbery (chat_id BIGINT, user_id BIGINT, last_robbery REAL DEFAULT 0, debt_amount INTEGER DEFAULT 0, debt_time REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS lottery_tickets (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, buy_time REAL)""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS usernames (chat_id BIGINT, user_id BIGINT, username TEXT, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS bank (chat_id BIGINT, user_id BIGINT, deposit INTEGER DEFAULT 0, last_interest_time REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS education (chat_id BIGINT, user_id BIGINT, completed_courses TEXT[] DEFAULT '{}', has_mba BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS loans (chat_id BIGINT, user_id BIGINT, amount INTEGER DEFAULT 0, interest INTEGER DEFAULT 0, taken_at REAL DEFAULT 0, due_date REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS jail (chat_id BIGINT, user_id BIGINT, release_time REAL DEFAULT 0, fine_per_hour INTEGER DEFAULT 50, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS jail_fines (chat_id BIGINT, user_id BIGINT, fine_amount INTEGER DEFAULT 0, debt_time REAL DEFAULT 0, paid BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS mafia_threats (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, threat_time REAL DEFAULT 0, deadline REAL DEFAULT 0, ransom_amount INTEGER DEFAULT 0, threat_type TEXT DEFAULT 'asset', target_asset TEXT DEFAULT '', paid BOOLEAN DEFAULT FALSE)""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS achievements (chat_id BIGINT, user_id BIGINT, achievement_id TEXT, unlocked_at REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id, achievement_id))""")
        
        # Создаём новые таблицы без FOREIGN KEY
        await conn.execute("""CREATE TABLE marketplace (id SERIAL PRIMARY KEY, chat_id BIGINT, seller_id BIGINT, item_type TEXT, item_name TEXT, item_key TEXT, price INTEGER, created_at REAL DEFAULT 0)""")
        print("✅ Таблица marketplace создана")
        
        await conn.execute("""CREATE TABLE stocks (id SERIAL PRIMARY KEY, chat_id BIGINT, business_id INTEGER, owner_id BIGINT, shares_issued INTEGER DEFAULT 10, shares_available INTEGER DEFAULT 10, price_per_share INTEGER DEFAULT 100, dividend_per_share INTEGER DEFAULT 10, last_price_change REAL DEFAULT 0)""")
        print("✅ Таблица stocks создана")
        
        await conn.execute("""CREATE TABLE stock_holdings (id SERIAL PRIMARY KEY, stock_id INTEGER, user_id BIGINT, shares_owned INTEGER DEFAULT 0)""")
        print("✅ Таблица stock_holdings создана")
                
        # Аукцион
        await conn.execute("""CREATE TABLE IF NOT EXISTS auctions (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            item_type TEXT,
            item_key TEXT,
            item_name TEXT,
            starting_price INTEGER,
            current_bid INTEGER DEFAULT 0,
            current_bidder_id BIGINT,
            start_time REAL DEFAULT 0,
            end_time REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            min_increment INTEGER DEFAULT 100
        )""")
        print("✅ Таблица auctions создана")
        
        await conn.execute("""CREATE TABLE IF NOT EXISTS auction_bids (
            id SERIAL PRIMARY KEY,
            auction_id INTEGER,
            user_id BIGINT,
            bid_amount INTEGER,
            bid_time REAL DEFAULT 0
        )""")
        print("✅ Таблица auction_bids создана")

        await conn.execute("""CREATE TABLE IF NOT EXISTS heist_cooldowns (
            chat_id BIGINT,
            user_id BIGINT,
            last_heist_time REAL DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )""")
        print("✅ Таблица heist_cooldowns создана")
        
    print("✅ База данных готова")

async def save_username(cid, uid, name):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO usernames VALUES ($1,$2,$3) ON CONFLICT (chat_id, user_id) DO UPDATE SET username=$3", cid, uid, name)

async def get_user(cid, uid):
    async with pool.acquire() as conn:
        b = await conn.fetchval("SELECT balance FROM users WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if b is not None: return {"balance": b}
        await conn.execute("INSERT INTO users VALUES ($1,$2,0)", cid, uid)
        return {"balance": 0}

async def update_balance(cid, uid, amt):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance=balance+$1 WHERE chat_id=$2 AND user_id=$3", amt, cid, uid)

async def get_profile(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT job_key, level, last_work_time, coffee_level FROM profiles WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if not r:
            await conn.execute("INSERT INTO profiles VALUES ($1,$2,'novice',1,0,0)", cid, uid)
            return {"job_key": "novice", "level": 1, "last_work_time": 0, "coffee_level": 0}
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
        if not r: return {"amount": 0, "interest": 0, "taken_at": 0, "due_date": 0}
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
        if not r: return False
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
    """Конфискует имущество и возвращает (список, стоимость_конфискованного)"""
    arrested = []
    total_value = 0
    
    # 1. Забираем банк
    bank_data = await get_bank(cid, uid)
    if bank_data['deposit'] > 0:
        total_value += bank_data['deposit']
        arrested.append(f"💰 Банк: {fmt_money(bank_data['deposit'])}")
        async with pool.acquire() as conn:
            await conn.execute("UPDATE bank SET deposit=0, last_interest_time=$1 WHERE chat_id=$2 AND user_id=$3", time.time(), cid, uid)
    
    # 2. Забираем машины (по ценам из CARS)
    async with pool.acquire() as conn:
        cars = await conn.fetch("SELECT car_key FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if cars:
            car_names = []
            for car in cars:
                car_key = car['car_key']
                if car_key in CARS:
                    total_value += CARS[car_key]['price']
                car_names.append(CARS.get(car_key, {}).get('name', car_key))
            arrested.append(f"🚗 Машины: {', '.join(car_names)}")
            await conn.execute("DELETE FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
    
    # 3. Забираем бизнесы (по ценам из MARKET)
    async with pool.acquire() as conn:
        businesses = await conn.fetch("SELECT business_name, income FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if businesses:
            biz_names = []
            for biz in businesses:
                # Находим цену бизнеса по доходу (обратный поиск)
                biz_price = 0
                for k, v in MARKET.items():
                    if v['type'] == 'business' and v['income'] == biz['income']:
                        biz_price = v['price']
                        break
                if biz_price == 0:
                    biz_price = biz['income'] * 6  # примерная оценка
                total_value += biz_price
                biz_names.append(biz['business_name'])
            arrested.append(f"🏢 Бизнесы: {', '.join(biz_names)}")
            await conn.execute("DELETE FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
    
    # 4. Забираем инвентарь (примерная оценка)
    async with pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name, rarity FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if items:
            item_names = []
            for item in items:
                rarity_value = {'legendary': 5000, 'rare': 1000, 'common': 100}
                total_value += rarity_value.get(item['rarity'], 100)
                item_names.append(item['item_name'])
            arrested.append(f"🎒 Предметы: {', '.join(item_names)}")
            await conn.execute("DELETE FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
    
    # 5. Сбрасываем профессию (оценка: 5000 за каждый уровень выше 1)
    p = await get_profile(cid, uid)
    if p['level'] > 1:
        profession_value = (p['level'] - 1) * 5000
        total_value += profession_value
        arrested.append(f"💼 Профессия сброшена (был Ур.{p['level']})")
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET job_key='novice', level=1 WHERE chat_id=$1 AND user_id=$2", cid, uid)
    
    return arrested, total_value

# ==================== ДОСТИЖЕНИЯ ====================
async def check_achievements(cid, uid):
    unlocked = []
    user = await get_user(cid, uid)
    edu = await get_education(cid, uid)
    async with pool.acquire() as conn:
        checks = [
            (user['balance'] >= 1000, 'first_1000'),
            (user['balance'] >= 10000, 'first_10k'),
            (user['balance'] >= 100000, 'first_100k'),
            (user['balance'] >= 1000000, 'millionaire'),
        ]
        bc = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
        checks.extend([(bc >= 1, 'first_business'), (bc >= 10, 'business_empire')])
        cc = await conn.fetchval("SELECT COUNT(*) FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
        checks.extend([(cc >= 1, 'first_car'), (cc >= 5, 'car_collector')])
        checks.extend([
            (len(edu['completed_courses']) >= 1, 'first_course'),
            (len(edu['completed_courses']) >= 4, 'all_courses'),
            (edu['has_mba'], 'mba_graduate'),
        ])
        for condition, ach_id in checks:
            if condition:
                exists = await conn.fetchval("SELECT 1 FROM achievements WHERE chat_id=$1 AND user_id=$2 AND achievement_id=$3", cid, uid, ach_id)
                if not exists:
                    await conn.execute("INSERT INTO achievements VALUES ($1,$2,$3,$4)", cid, uid, ach_id, time.time())
                    unlocked.append(ACHIEVEMENTS[ach_id])
    return unlocked

async def get_user_achievements(cid, uid):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT achievement_id, unlocked_at FROM achievements WHERE chat_id=$1 AND user_id=$2 ORDER BY unlocked_at DESC", cid, uid)
    return [(r['achievement_id'], r['unlocked_at']) for r in rows]

async def notify_achievements(cid, uid, new_achs):
    if new_achs:
        ach_text = "\n".join([f"{a['icon']} <b>{a['name']}</b> — {a['desc']}" for a in new_achs])
        try:
            await bot.send_message(cid, f"🏆 <b>Новые достижения!</b>\n\n{ach_text}", parse_mode="HTML")
        except:
            pass

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
                        await bot.send_message(cid, f" <b>АВТО-РОЗЫГРЫШ!</b>\n\n🏆 {wname}\n💰 {fmt_money(bank)}", parse_mode="HTML")
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
                    
                    # Конфискуем имущество и получаем его стоимость
                    arrested, confiscated_value = await arrest_player(cid, uid)
                    
                    # Вычисляем остаток долга
                    remaining_debt = total_debt - confiscated_value
                    
                    # Если имущество не покрыло весь долг — остаток идёт в минус баланса
                    if remaining_debt > 0:
                        user = await get_user(cid, uid)
                        new_balance = user['balance'] - remaining_debt
                        async with pool.acquire() as conn2:
                            await conn2.execute("UPDATE users SET balance=$1 WHERE chat_id=$2 AND user_id=$3", new_balance, cid, uid)
                    
                    await clear_loan(cid, uid)
                    
                    # Формируем сообщение
                    msg = f"🚔 <b>АРЕСТ ИМУЩЕСТВА!</b>\n\n"
                    msg += f"💰 Долг: <b>{fmt_money(total_debt)}</b>\n"
                    msg += f"📦 Конфисковано на: <b>{fmt_money(confiscated_value)}</b>\n\n"
                    msg += f"<b>Конфисковано:</b>\n" + "\n".join([f"• {item}" for item in arrested])
                    
                    if remaining_debt > 0:
                        msg += f"\n\n <b>Имущество не покрыло весь долг!</b>\n"
                        msg += f"Остаток долга: <b>{fmt_money(remaining_debt)}</b>\n"
                        msg += f"Ваш баланс ушёл в минус.\n"
                        msg += f"Работайте и гасите долг через /repay"
                    
                    try:
                        await bot.send_message(cid, msg, parse_mode="HTML")
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
    print("️ Цикл мафии запущен")
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
                        target_desc = f" Машину <b>{target}</b>"
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
                    f"🕴️ <b>К ВАМ ПРИШЛА МАФИЯ!</b>\n\n"
                    f"👤 {username}, мы знаем о ваших доходах...\n\n"
                    f"💰 <b>Ваш капитал:</b> {fmt_money(total_wealth)}\n"
                    f"  • 💵 Основной: {fmt_money(balance)}\n"
                    f"  •  Банк: {fmt_money(deposit)}\n\n"
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
    """Проверяет все активные угрозы мафии и наказывает тех, кто не заплатил вовремя"""
    async with pool.acquire() as conn:
        # Выбираем ВСЕ неоплаченные угрозы, у которых вышел срок
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
            
            # Генерируем случайное событие (шанс 20% что мафия уйдет ни с чем)
            roll = random.random()
            
            if roll < 0.20:
                msg = (
                    f"🕊️ <b>МАФИЯ УШЛА НИ С ЧЕМ!</b>\n\n"
                    f"👤 {username}, вы проигнорировали требование, но мафия решила не трогать вас.\n"
                    f"Видимо, у них были дела поважнее...\n\n"
                    f" Вам повезло! Но в следующий раз лучше платить вовремя."
                )
                
            elif roll < 0.60:
                # Мафия забирает конкретный актив или деньги
                if threat_type == 'asset':
                    businesses = await conn.fetch("SELECT business_name FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
                    cars = await conn.fetch("SELECT car_name FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
                    
                    if target in [b['business_name'] for b in businesses]:
                        await conn.execute("DELETE FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name=$3", cid, uid, target)
                        msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ВАШ БИЗНЕС!</b>\n\n👤 {username}, вы проигнорировали требование.\n Конфискован: <b>{target}</b>"
                    elif target in [c['car_name'] for c in cars]:
                        await conn.execute("DELETE FROM garage WHERE chat_id=$1 AND user_id=$2 AND car_name=$3", cid, uid, target)
                        msg = f"🔫 <b>МАФИЯ УКРАЛА ВАШУ МАШИНУ!</b>\n\n👤 {username}, вы проигнорировали требование.\n🚗 Украдена: <b>{target}</b>"
                    else:
                        # Если актива нет или он продан — забирают деньги
                        user = await get_user(cid, uid)
                        bank = await get_bank(cid, uid)
                        penalty = int((user['balance'] + bank['deposit']) * MAFIA_PENALTY_RATE)
                        
                        paid_from_balance = min(penalty, user['balance'])
                        remaining = penalty - paid_from_balance
                        
                        if paid_from_balance > 0:
                            await update_balance(cid, uid, -paid_from_balance)
                        if remaining > 0 and bank['deposit'] > 0:
                            await update_bank(cid, uid, -min(remaining, bank['deposit']))
                            
                        msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ДЕНЬГИ!</b>\n\n👤 {username}, вы проигнорировали требование.\n💸 Списано: <b>{fmt_money(penalty)}</b>"
                else:
                    # Угроза была по балансу
                    user = await get_user(cid, uid)
                    bank = await get_bank(cid, uid)
                    penalty = int((user['balance'] + bank['deposit']) * MAFIA_PENALTY_RATE)
                    
                    paid_from_balance = min(penalty, user['balance'])
                    remaining = penalty - paid_from_balance
                    
                    if paid_from_balance > 0:
                        await update_balance(cid, uid, -paid_from_balance)
                    if remaining > 0 and bank['deposit'] > 0:
                        await update_bank(cid, uid, -min(remaining, bank['deposit']))
                        
                    msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ДЕНЬГИ!</b>\n\n {username}, вы проигнорировали требование.\n💸 Списано: <b>{fmt_money(penalty)}</b>"
                    
            else:
                # Жесткое наказание: 30% от всего капитала
                user = await get_user(cid, uid)
                bank = await get_bank(cid, uid)
                penalty = int((user['balance'] + bank['deposit']) * MAFIA_PENALTY_RATE)
                
                paid_from_balance = min(penalty, user['balance'])
                remaining = penalty - paid_from_balance
                
                if paid_from_balance > 0:
                    await update_balance(cid, uid, -paid_from_balance)
                if remaining > 0 and bank['deposit'] > 0:
                    await update_bank(cid, uid, -min(remaining, bank['deposit']))
                    
                msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ДЕНЬГИ!</b>\n\n👤 {username}, вы проигнорировали требование.\n💸 Списано: <b>{fmt_money(penalty)}</b> (30% от капитала)"
            
            # Помечаем угрозу как обработанную, чтобы не наказывать дважды
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

# ==================== ТОРГОВАЯ ПЛОЩАДКА ====================
@dp.message(Command("marketplace"))
async def cmd_marketplace(m: Message):
    try:
        cid = m.chat.id
        async with pool.acquire() as conn:
            items = await conn.fetch("SELECT * FROM marketplace WHERE chat_id=$1 ORDER BY created_at DESC LIMIT 20", cid)
        
        if not items:
            return await m.answer("🏪 <b>Торговая площадка пуста!</b>\n\nПродайте что-нибудь через /sell", parse_mode="HTML")
        
        t = "🏪 <b>Торговая площадка:</b>\n\n"
        for item in items:
            seller = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, item['seller_id']) or f"User{item['seller_id']}"
            
            if item['item_type'] == 'inventory':
                icon = "🎒"
            elif item['item_type'] == 'car':
                icon = "🚗"
            else:
                icon = "🏢"
            
            t += f"{icon} <b>{item['item_name']}</b>\n   💰 {fmt_money(item['price'])}\n   👤 Продавец: {seller}\n   🛒 /buy_item {item['id']}\n\n"
        
        t += "━━━━━━━━━━━━━━━━━━━━\n💡 Чтобы продать: /sell inv/car/biz название цена"
        await m.answer(t, parse_mode="HTML")
    except Exception as e:
        logging.error(f"marketplace error: {e}")
        await m.answer(f"❌ Ошибка при загрузке площадки: {str(e)}")

@dp.message(Command("sell"))
async def cmd_sell(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        
        if len(args) < 3:
            return await m.answer(
                "🏪 <b>Продать предмет</b>\n\n"
                "Использование:\n"
                "/sell inv <название> <цена>\n"
                "/sell car <ключ_машины> <цена>\n"
                "/sell biz <название_бизнеса> <цена>\n\n"
                "Пример: /sell inv Алмаз 5000",
                parse_mode="HTML"
            )
        
        sell_type = args[1].lower()
        try:
            price = int(args[-1])
        except:
            return await m.answer(" Цена должна быть числом!")
        
        if price < 10:
            return await m.answer("❌ Минимальная цена: 10")
        
        item_name = " ".join(args[2:-1])
        
        async with pool.acquire() as conn:
            if sell_type == 'inv':
                item = await conn.fetchrow(
                    "SELECT id, item_name, rarity FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3 LIMIT 1",
                    cid, uid, item_name
                )
                if not item:
                    return await m.answer(f"❌ У вас нет предмета '{item_name}'")
                
                await conn.execute("DELETE FROM inventory WHERE id=$1", item['id'])
                await conn.execute(
                    "INSERT INTO marketplace (chat_id, seller_id, item_type, item_name, item_key, price, created_at) VALUES ($1,$2,'inventory',$3,$4,$5,$6)",
                    cid, uid, item['item_name'], item['rarity'], price, time.time()
                )
                await m.answer(f"✅ Предмет <b>{item['item_name']}</b> выставлен за {fmt_money(price)}!", parse_mode="HTML")
                
            elif sell_type == 'car':
                car_key = item_name.lower().replace(" ", "_")
                car = await conn.fetchrow(
                    "SELECT id, car_name FROM garage WHERE chat_id=$1 AND user_id=$2 AND car_key=$3 LIMIT 1",
                    cid, uid, car_key
                )
                if not car:
                    return await m.answer(f"❌ У вас нет машины с ключом '{car_key}'. Используйте /mycar чтобы посмотреть ключи.")
                
                await conn.execute("DELETE FROM garage WHERE id=$1", car['id'])
                await conn.execute(
                    "INSERT INTO marketplace (chat_id, seller_id, item_type, item_name, item_key, price, created_at) VALUES ($1,$2,'car',$3,$4,$5,$6)",
                    cid, uid, car['car_name'], car_key, price, time.time()
                )
                await m.answer(f"✅ Машина <b>{car['car_name']}</b> выставлена за {fmt_money(price)}!", parse_mode="HTML")
                
            elif sell_type == 'biz':
                biz = await conn.fetchrow(
                    "SELECT id, business_name, income FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name ILIKE $3 LIMIT 1",
                    cid, uid, f"%{item_name}%"
                )
                if not biz:
                    return await m.answer(f"❌ У вас нет бизнеса '{item_name}'")
                
                has_stocks = await conn.fetchval("SELECT 1 FROM stocks WHERE business_id=$1", biz['id'])
                if has_stocks:
                    return await m.answer("❌ Нельзя продать бизнес, у которого есть акции! Сначала выкупите все акции.")
                
                await conn.execute("DELETE FROM businesses WHERE id=$1", biz['id'])
                await conn.execute(
                    "INSERT INTO marketplace (chat_id, seller_id, item_type, item_name, item_key, price, created_at) VALUES ($1,$2,'business',$3,$4,$5,$6)",
                    cid, uid, biz['business_name'], biz['business_name'], price, time.time()
                )
                await m.answer(f"✅ Бизнес <b>{biz['business_name']}</b> выставлен за {fmt_money(price)}!", parse_mode="HTML")
            else:
                return await m.answer("❌ Тип: inv, car или biz")
    except Exception as e:
        logging.error(f"sell error: {e}")
        await m.answer(f"❌ Ошибка при продаже: {str(e)}")

@dp.message(Command("buy_item"))
async def cmd_buy_item(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2:
            return await m.answer("🏪 <b>/buy_item ID_лота</b>")
        
        try:
            lot_id = int(args[1])
        except:
            return await m.answer("❌ ID должен быть числом!")
        
        async with pool.acquire() as conn:
            lot = await conn.fetchrow("SELECT * FROM marketplace WHERE id=$1 AND chat_id=$2", lot_id, cid)
            if not lot:
                return await m.answer("❌ Лот не найден или уже продан!")
            
            if lot['seller_id'] == uid:
                return await m.answer("❌ Нельзя купить у себя!")
            
            buyer = await get_user(cid, uid)
            if buyer['balance'] < lot['price']:
                return await m.answer(f"❌ Нужно {fmt_money(lot['price'])}. У вас: {fmt_money(buyer['balance'])}")
            
            await update_balance(cid, uid, -lot['price'])
            await update_balance(cid, lot['seller_id'], lot['price'])
            
            if lot['item_type'] == 'inventory':
                await conn.execute(
                    "INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,'market',$4)",
                    cid, uid, lot['item_name'], lot['item_key']
                )
            elif lot['item_type'] == 'car':
                await conn.execute(
                    "INSERT INTO garage (chat_id, user_id, car_key, car_name) VALUES ($1,$2,$3,$4)",
                    cid, uid, lot['item_key'], lot['item_name']
                )
            elif lot['item_type'] == 'business':
                await conn.execute(
                    "INSERT INTO businesses (chat_id, user_id, business_name, income, last_collect_time) VALUES ($1,$2,$3,0,$4)",
                    cid, uid, lot['item_name'], time.time()
                )
                for k, v in MARKET.items():
                    if v['type'] == 'business' and v['name'] == lot['item_name']:
                        await conn.execute("UPDATE businesses SET income=$1 WHERE chat_id=$2 AND user_id=$3 AND business_name=$4", v['income'], cid, uid, lot['item_name'])
                        break
            
            await conn.execute("DELETE FROM marketplace WHERE id=$1", lot_id)
            
            seller_name = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, lot['seller_id']) or f"User{lot['seller_id']}"
            await m.answer(f"✅ Куплено <b>{lot['item_name']}</b> у {seller_name} за {fmt_money(lot['price'])}!", parse_mode="HTML")
    except Exception as e:
        logging.error(f"buy_item error: {e}")
        await m.answer(f"❌ Ошибка при покупке: {str(e)}")

# ==================== БИРЖА АКЦИЙ (ИСПРАВЛЕНА) ====================
@dp.message(Command("stocks"))
async def cmd_stocks(m: Message):
    try:
        cid = m.chat.id
        async with pool.acquire() as conn:
            stocks = await conn.fetch("SELECT * FROM stocks WHERE chat_id=$1 AND shares_available > 0 ORDER BY price_per_share ASC", cid)
        
        if not stocks:
            return await m.answer("📈 <b>Биржа пуста!</b>\n\nВладельцы бизнесов могут выпустить акции: /issue_stock", parse_mode="HTML")
        
        t = "📈 <b>Биржа акций:</b>\n\n"
        count = 0
        
        for stock in stocks:
            try:
                try:
                    owner_name = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, stock['owner_id']) or f"User{stock['owner_id']}"
                except:
                    owner_name = f"User{stock['owner_id']}"
                
                try:
                    biz = await conn.fetchrow("SELECT business_name FROM businesses WHERE id=$1", stock['business_id'])
                    biz_name = biz['business_name'] if biz else "❓ Удалён"
                except:
                    biz_name = "❓ Удалён"
                
                price = stock['price_per_share'] if stock['price_per_share'] else 0
                last_change = stock['last_price_change'] if stock['last_price_change'] else price
                if last_change == 0:
                    last_change = 1
                
                change_pct = int((price - last_change) / abs(last_change) * 100)
                arrow = "📈" if change_pct >= 0 else "📉"
                
                shares_avail = stock['shares_available'] if stock['shares_available'] else 0
                shares_issued = stock['shares_issued'] if stock['shares_issued'] else 0
                dividend = stock['dividend_per_share'] if stock['dividend_per_share'] else 0
                
                t += f"🏢 <b>{biz_name}</b> ({owner_name})\n💰 Цена: {fmt_money(price)}/акция {arrow} {change_pct}%\n💵 Дивиденды: {fmt_money(dividend)}/день\n📊 Доступно: {shares_avail}/{shares_issued}\n🛒 /buy_stock {stock['id']} (кол-во)\n\n"
                count += 1
            except Exception as e:
                logging.error(f"stocks display error for stock {stock['id']}: {e}")
                continue
        
        if count == 0:
            return await m.answer("📈 <b>Нет доступных акций!</b>", parse_mode="HTML")
        
        t += "💡 Выпустить акции: /issue_stock (название бизнеса)"
        await m.answer(t, parse_mode="HTML")
    except Exception as e:
        logging.error(f"stocks error: {e}")
        await m.answer(f"❌ Ошибка при загрузке биржи: {str(e)}")

@dp.message(Command("issue_stock"))
async def cmd_issue_stock(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2:
            return await m.answer("📈 <b>/issue_stock (название бизнеса)</b>\n\nВыпускает 10 акций вашего бизнеса", parse_mode="HTML")
        
        biz_name = " ".join(args[1:])
        
        async with pool.acquire() as conn:
            biz = await conn.fetchrow(
                "SELECT id, business_name, income FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name ILIKE $3 LIMIT 1",
                cid, uid, f"%{biz_name}%"
            )
            if not biz:
                return await m.answer(f"❌ У вас нет бизнеса '{biz_name}'")
            
            existing = await conn.fetchval("SELECT 1 FROM stocks WHERE business_id=$1", biz['id'])
            if existing:
                return await m.answer("❌ У этого бизнеса уже есть акции!")
            
                        # Ищем реальную цену бизнеса в MARKET
            market_price = 0
            for k, v in MARKET.items():
                if v['type'] == 'business' and v['name'] == biz['business_name']:
                    market_price = v['price']
                    break
            if market_price == 0:
                market_price = biz['income'] * 6
            
            # Цена акции = цена бизнеса / 15 (пакет из 10 акций дешевле бизнеса на 33%)
            price = max(100, int(market_price / 15))
            
            # Дивиденды = доход / 30 (окупаемость ~30 дней)
            dividend = max(1, biz['income'] // 30)
            
            await conn.execute(
                "INSERT INTO stocks (chat_id, business_id, owner_id, shares_issued, shares_available, price_per_share, dividend_per_share, last_price_change) VALUES ($1,$2,$3,10,10,$4,$5,$6)",
                cid, biz['id'], uid, price, dividend, float(price)
            )
            
            await m.answer(
                f"📈 <b>Акции выпущены!</b>\n\n"
                f" Бизнес: {biz['business_name']}\n"
                f"💰 Цена: {fmt_money(price)}/акция\n"
                f"💵 Дивиденды: {fmt_money(dividend)}/день\n"
                f"📊 Выпущено: 10 акций\n\n"
                f"Игроки могут купить их через /stocks",
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"issue_stock error: {e}")
        await m.answer(f"❌ Ошибка при выпуске акций: {str(e)}")

@dp.message(Command("buy_stock"))
async def cmd_buy_stock(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 3:
            return await m.answer("📈 <b>/buy_stock ID (количество)</b>")
        
        try:
            stock_id = int(args[1])
            qty = int(args[2])
        except:
            return await m.answer("❌ ID и количество должны быть числами!")
        
        if qty < 1:
            return await m.answer("❌ Минимум 1 акция!")
        
        async with pool.acquire() as conn:
            stock = await conn.fetchrow("SELECT * FROM stocks WHERE id=$1", stock_id)
            if not stock:
                return await m.answer("❌ Акция не найдена!")
            
            if stock['shares_available'] < qty:
                return await m.answer(f"❌ Доступно только {stock['shares_available']} акций!")
            
            total_cost = stock['price_per_share'] * qty
            buyer = await get_user(cid, uid)
            if buyer['balance'] < total_cost:
                return await m.answer(f" Нужно {fmt_money(total_cost)}. У вас: {fmt_money(buyer['balance'])}")
            
            await update_balance(cid, uid, -total_cost)
            await conn.execute("UPDATE stocks SET shares_available = shares_available - $1 WHERE id=$2", qty, stock_id)
            
            existing = await conn.fetchrow("SELECT * FROM stock_holdings WHERE stock_id=$1 AND user_id=$2", stock_id, uid)
            if existing:
                await conn.execute("UPDATE stock_holdings SET shares_owned = shares_owned + $1 WHERE id=$2", qty, existing['id'])
            else:
                await conn.execute("INSERT INTO stock_holdings (stock_id, user_id, shares_owned) VALUES ($1,$2,$3)", stock_id, uid, qty)
            
            await m.answer(
                f"✅ Куплено <b>{qty} акций</b>!\n\n"
                f"💰 Потрачено: {fmt_money(total_cost)}\n"
                f"💵 Дивиденды: {fmt_money(stock['dividend_per_share'] * qty)}/день",
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"buy_stock error: {e}")
        await m.answer(f"❌ Ошибка при покупке акций: {str(e)}")

@dp.message(Command("sell_stock"))
async def cmd_sell_stock(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 3:
            return await m.answer("📈 <b>/sell_stock ID (количество)</b>")
        
        try:
            stock_id = int(args[1])
            qty = int(args[2])
        except:
            return await m.answer("❌ ID и количество должны быть числами!")
        
        async with pool.acquire() as conn:
            holding = await conn.fetchrow("SELECT * FROM stock_holdings WHERE stock_id=$1 AND user_id=$2", stock_id, uid)
            if not holding or holding['shares_owned'] < qty:
                return await m.answer(" У вас недостаточно акций!")
            
            stock = await conn.fetchrow("SELECT * FROM stocks WHERE id=$1", stock_id)
            if not stock:
                return await m.answer("❌ Акция не найдена!")
            
            refund = int(stock['price_per_share'] * qty * 0.7)
            await update_balance(cid, uid, refund)
            
            await conn.execute("UPDATE stock_holdings SET shares_owned = shares_owned - $1 WHERE id=$2", qty, holding['id'])
            await conn.execute("UPDATE stocks SET shares_available = shares_available + $1 WHERE id=$2", qty, stock_id)
            
            new_shares = holding['shares_owned'] - qty
            if new_shares <= 0:
                await conn.execute("DELETE FROM stock_holdings WHERE id=$1", holding['id'])
            
            await m.answer(f"✅ Продано <b>{qty} акций</b> за {fmt_money(refund)} (комиссия 30%)", parse_mode="HTML")
    except Exception as e:
        logging.error(f"sell_stock error: {e}")
        await m.answer(f"❌ Ошибка при продаже акций: {str(e)}")

@dp.message(Command("my_stocks"))
async def cmd_my_stocks(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        async with pool.acquire() as conn:
            holdings = await conn.fetch("SELECT sh.shares_owned, s.price_per_share, s.dividend_per_share, s.business_id FROM stock_holdings sh JOIN stocks s ON sh.stock_id = s.id WHERE sh.user_id = $1 AND s.chat_id = $2", uid, cid)
        
        if not holdings:
            return await m.answer("📈 <b>У вас нет акций.</b>\n\nКупите на бирже: /stocks", parse_mode="HTML")
        
        t = "📊 <b>Мои акции:</b>\n\n"
        total_value = 0
        total_dividends = 0
        
        for h in holdings:
            try:
                biz = await conn.fetchrow("SELECT business_name FROM businesses WHERE id=$1", h['business_id'])
                biz_name = biz['business_name'] if biz else "Удалён"
                value = h['shares_owned'] * h['price_per_share']
                dividends = h['shares_owned'] * h['dividend_per_share']
                total_value += value
                total_dividends += dividends
                
                t += f" <b>{biz_name}</b>\n    Акции: {h['shares_owned']}\n   💰 Стоимость: {fmt_money(value)}\n   💵 Дивиденды: {fmt_money(dividends)}/день\n\n"
            except Exception as e:
                logging.error(f"my_stocks display error: {e}")
                continue
        
        t += f"━━━━━━━━━━━━━━━━━━━━\n💰 Общая стоимость: <b>{fmt_money(total_value)}</b>\n💵 Дивиденды/день: <b>{fmt_money(total_dividends)}</b>"
        await m.answer(t, parse_mode="HTML")
    except Exception as e:
        logging.error(f"my_stocks error: {e}")
        await m.answer(f"❌ Ошибка: {str(e)}")

async def stock_market_loop():
    print("📈 Цикл биржи акций запущен")
    while True:
        await asyncio.sleep(21600)
        async with pool.acquire() as conn:
            stocks = await conn.fetch("SELECT * FROM stocks")
            for stock in stocks:
                event = random.choice(STOCK_MARKET_EVENTS)
                new_price = int(stock['price_per_share'] * event['effect'])
                new_price = max(50, min(new_price, 100000))
                
                await conn.execute(
                    "UPDATE stocks SET price_per_share=$1, last_price_change=$2 WHERE id=$3",
                    new_price, stock['price_per_share'], stock['id']
                )

async def stock_dividend_loop():
    print("💵 Цикл дивидендов запущен")
    while True:
        await asyncio.sleep(86400)
        try:
            async with pool.acquire() as conn:
                holdings = await conn.fetch("SELECT sh.user_id, sh.shares_owned, s.dividend_per_share, s.chat_id FROM stock_holdings sh JOIN stocks s ON sh.stock_id = s.id")
                
                user_dividends = {}
                for h in holdings:
                    try:
                        uid = h['user_id']
                        cid = h['chat_id']
                        amount = (h['shares_owned'] or 0) * (h['dividend_per_share'] or 0)
                        if uid not in user_dividends:
                            user_dividends[uid] = {'cid': cid, 'total': 0}
                        user_dividends[uid]['total'] += amount
                    except Exception as e:
                        logging.error(f"dividend calc error: {e}")
                        continue
                
                for uid, data in user_dividends.items():
                    if data['total'] > 0:
                        try:
                            await update_balance(data['cid'], uid, data['total'])
                            await bot.send_message(data['cid'], f"💵 <b>Дивиденды получены!</b>\n\n+{fmt_money(data['total'])}", parse_mode="HTML")
                        except Exception as e:
                            logging.error(f"dividend send error: {e}")
                            continue
        except Exception as e:
            logging.error(f"stock_dividend_loop error: {e}")

# ==================== АУКЦИОН ====================
@dp.message(Command("auction"))
async def cmd_auction(m: Message):
    try:
        cid = m.chat.id
        async with pool.acquire() as conn:
            auctions = await conn.fetch(
                "SELECT * FROM auctions WHERE chat_id=$1 AND status='active' ORDER BY end_time ASC",
                cid
            )
        
        if not auctions:
            return await m.answer("🏆 <b>Аукцион пуст!</b>\n\nСледите за анонсами редких лотов!", parse_mode="HTML")
        
        t = "🏆 <b>АУКЦИОН РЕДКИХ ПРЕДМЕТОВ</b>\n\n"
        
        for auction in auctions:
            time_left = int(auction['end_time'] - time.time())
            if time_left <= 0:
                continue
            
            hours = time_left // 3600
            minutes = (time_left % 3600) // 60
            
            if auction['item_type'] == 'car':
                icon = "🚗"
            elif auction['item_type'] == 'business':
                icon = "🏢"
            else:
                icon = ""
            
            bidder_name = "Никто"
            if auction['current_bidder_id']:
                bidder_name = await conn.fetchval(
                    "SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2",
                    cid, auction['current_bidder_id']
                ) or f"User{auction['current_bidder_id']}"
            
            t += f"{icon} <b>{auction['item_name']}</b>\n"
            t += f"💰 Текущая ставка: <b>{fmt_money(auction['current_bid'])}</b>\n"
            t += f"👤 Лидер: {bidder_name}\n"
            t += f"⏰ Осталось: {hours}ч {minutes}мин\n"
            t += f"📈 Мин. шаг: {fmt_money(auction['min_increment'])}\n"
            t += f"🛒 Ставка: /bid {auction['id']} сумма\n\n"
        
        t += "━━━━━━━━━━━━━━━━━━━━\n💡 Ставка должна быть выше текущей на минимальный шаг!"
        await m.answer(t, parse_mode="HTML")
    except Exception as e:
        logging.error(f"auction error: {e}")
        await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("bid"))
async def cmd_bid(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        
        if len(args) < 3:
            return await m.answer("🏆 <b>/bid ID сумма</b>\n\nПример: /bid 1 50000", parse_mode="HTML")
        
        try:
            auction_id = int(args[1])
            bid_amount = int(args[2])
        except:
            return await m.answer("❌ ID и сумма должны быть числами!")
        
        if bid_amount <= 0:
            return await m.answer("❌ Сумма должна быть больше 0!")
        
        async with pool.acquire() as conn:
            auction = await conn.fetchrow("SELECT * FROM auctions WHERE id=$1 AND chat_id=$2 AND status='active'", auction_id, cid)
            if not auction:
                return await m.answer("❌ Аукцион не найден или завершён!")
            
            if time.time() > auction['end_time']:
                return await m.answer("⏰ Время аукциона вышло!")
            
            min_bid = auction['current_bid'] + auction['min_increment']
            if bid_amount < min_bid:
                return await m.answer(f"❌ Минимальная ставка: {fmt_money(min_bid)}")
            
            user = await get_user(cid, uid)
            if user['balance'] < bid_amount:
                return await m.answer(f"❌ Недостаточно средств! Нужно: {fmt_money(bid_amount)}")
            
            if auction['current_bidder_id'] == uid:
                return await m.answer("❌ Вы уже лидер! Повысьте ставку.")
            
            # Списываем ставку (замораживаем средства)
            await update_balance(cid, uid, -bid_amount)
            
            # Возвращаем деньги предыдущему лидеру
            if auction['current_bidder_id']:
                await update_balance(cid, auction['current_bidder_id'], auction['current_bid'])
                try:
                    await bot.send_message(
                        cid,
                        f"⚠️ <b>Вас перебидили!</b>\n\n"
                        f"Лот: {auction['item_name']}\n"
                        f"Ваша ставка {fmt_money(auction['current_bid'])} возвращена.",
                        parse_mode="HTML"
                    )
                except:
                    pass
            
            # Обновляем аукцион
            await conn.execute(
                "UPDATE auctions SET current_bid=$1, current_bidder_id=$2 WHERE id=$3",
                bid_amount, uid, auction_id
            )
            
            # Записываем ставку
            await conn.execute(
                "INSERT INTO auction_bids (auction_id, user_id, bid_amount, bid_time) VALUES ($1,$2,$3,$4)",
                auction_id, uid, bid_amount, time.time()
            )
            
            # Продлеваем время на 5 минут если ставка сделана за последние 2 минуты
            time_left = auction['end_time'] - time.time()
            if time_left < 120:
                new_end_time = time.time() + 300
                await conn.execute("UPDATE auctions SET end_time=$1 WHERE id=$2", new_end_time, auction_id)
                await m.answer(f"⏰ Время продлено на 5 минут!", parse_mode="HTML")
            
            await m.answer(
                f"✅ <b>Ставка принята!</b>\n\n"
                f"🏆 Лот: {auction['item_name']}\n"
                f" Ваша ставка: <b>{fmt_money(bid_amount)}</b>\n"
                f" Осталось: {int((auction['end_time'] - time.time()) // 60)} мин",
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"bid error: {e}")
        await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("create_auction"))
async def cmd_create_auction(m: Message):
    """Только для админов"""
    if m.from_user.id not in ADMIN_IDS:
        return await m.answer("❌ Только для админов!")
    
    args = m.text.split()
    if len(args) < 5:
        return await m.answer(
            "🏆 <b>Создать аукцион</b>\n\n"
            "Использование:\n"
            "/create_auction type key name start_price duration_hours\n\n"
            "type: car/business/item\n"
            "duration_hours: длительность в часах\n\n"
            "Пример: /create_auction car gold_bmw Золотой BMW 100000 24",
            parse_mode="HTML"
        )
    
    try:
        item_type = args[1]
        item_key = args[2]
        item_name = " ".join(args[3:-2])
        starting_price = int(args[-2])
        duration_hours = int(args[-1])
    except:
        return await m.answer("❌ Ошибка в параметрах!")
    
    if item_type not in ['car', 'business', 'item']:
        return await m.answer("❌ Тип: car, business или item")
    
    if duration_hours < 1 or duration_hours > 168:
        return await m.answer("❌ Длительность: от 1 до 168 часов (7 дней)")
    
    cid = m.chat.id
    start_time = time.time()
    end_time = start_time + (duration_hours * 3600)
    min_increment = max(100, starting_price // 10)
    
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO auctions (chat_id, item_type, item_key, item_name, starting_price, current_bid, start_time, end_time, min_increment) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)",
            cid, item_type, item_key, item_name, starting_price, starting_price, start_time, end_time, min_increment
        )
    
    await m.answer(
        f"🏆 <b>Аукцион создан!</b>\n\n"
        f"{item_name}\n"
        f"💰 Стартовая цена: {fmt_money(starting_price)}\n"
        f" Длительность: {duration_hours} часов\n"
        f"📈 Мин. шаг: {fmt_money(min_increment)}",
        parse_mode="HTML"
    )

@dp.message(Command("end_auction"))
async def cmd_end_auction(m: Message):
    """Только для админов"""
    if m.from_user.id not in ADMIN_IDS:
        return await m.answer("❌ Только для админов!")
    
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("🏆 <b>/end_auction ID</b>")
    
    try:
        auction_id = int(args[1])
    except:
        return await m.answer("❌ ID должен быть числом!")
    
    cid = m.chat.id
    async with pool.acquire() as conn:
        auction = await conn.fetchrow("SELECT * FROM auctions WHERE id=$1 AND chat_id=$2", auction_id, cid)
        if not auction:
            return await m.answer("❌ Аукцион не найден!")
        
        if auction['status'] == 'ended':
            return await m.answer("❌ Аукцион уже завершён!")
        
        await conn.execute("UPDATE auctions SET status='ended', end_time=$1 WHERE id=$2", time.time(), auction_id)
    
    await complete_auction(auction)
    await m.answer(f"✅ Аукцион #{auction_id} завершён вручную!", parse_mode="HTML")

async def complete_auction(auction):
    """Завершает аукцион и передаёт лот победителю"""
    cid = auction['chat_id']
    
    if not auction['current_bidder_id']:
        try:
            await bot.send_message(cid, f"️ Аукцион <b>{auction['item_name']}</b> завершён без ставок.", parse_mode="HTML")
        except:
            pass
        return
    
    winner_uid = auction['current_bidder_id']
    winner_name = "Unknown"
    
    async with pool.acquire() as conn:
        winner_name = await conn.fetchval(
            "SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2",
            cid, winner_uid
        ) or f"User{winner_uid}"
        
        # Передаём лот победителю
        if auction['item_type'] == 'car':
            await conn.execute(
                "INSERT INTO garage (chat_id, user_id, car_key, car_name) VALUES ($1,$2,$3,$4)",
                cid, winner_uid, auction['item_key'], auction['item_name']
            )
        elif auction['item_type'] == 'business':
            income = 0
            for k, v in {**MARKET, **RARE_BUSINESSES}.items():
                if v.get('name') == auction['item_name']:
                    income = v.get('income', 0)
                    break
            await conn.execute(
                "INSERT INTO businesses (chat_id, user_id, business_name, income, last_collect_time) VALUES ($1,$2,$3,$4,$5)",
                cid, winner_uid, auction['item_name'], income, time.time()
            )
        elif auction['item_type'] == 'item':
            rarity = 'legendary'
            for k, v in RARE_ITEMS.items():
                if v.get('name') == auction['item_name']:
                    rarity = v.get('rarity', 'legendary')
                    break
            await conn.execute(
                "INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,'auction',$4)",
                cid, winner_uid, auction['item_name'], rarity
            )
    
    # Уведомляем победителя
    try:
        await bot.send_message(
            cid,
            f"🏆 <b>АУКЦИОН ЗАВЕРШЁН!</b>\n\n"
            f"🎉 Победитель: <b>{winner_name}</b>\n"
            f"📦 Лот: <b>{auction['item_name']}</b>\n"
            f"💰 Цена: <b>{fmt_money(auction['current_bid'])}</b>\n\n"
            f"Предмет добавлен в ваш инвентарь!",
            parse_mode="HTML"
        )
    except:
        pass

async def auction_check_loop():
    """Проверяет завершённые аукционы"""
    print("🏆 Цикл проверки аукционов запущен")
    while True:
        await asyncio.sleep(60)
        async with pool.acquire() as conn:
            ended = await conn.fetch(
                "SELECT * FROM auctions WHERE status='active' AND end_time < $1",
                time.time()
            )
            for auction in ended:
                await conn.execute("UPDATE auctions SET status='ended' WHERE id=$1", auction['id'])
                await complete_auction(auction)

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

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
        "  🔫 /roulette ставка — рулетка\n"
        "  🎟️ /buy_ticket — лотерея\n"
        "  🎁 /daily — бонус\n\n"
        "🏪 <b>Бизнес:</b>\n"
        "  /market — рынок\n"
        "  /buy_market ключ — купить\n"
        "  /collect — прибыль\n\n"
        "🚗 <b>Авто:</b>\n"
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
        "🎒 <b>Инвентарь:</b>\n"
        "  /inv — инвентарь\n"
        "  /craft — крафт\n"
        "  /craft_item ключ\n"
        "  /trade @user предмет кол-во\n\n"
        "🏪 <b>Торговля:</b>\n"
        "  /marketplace — торговая площадка\n"
        "  /sell тип название цена\n"
        "  /buy_item ID\n\n"
        " <b>Биржа:</b>\n"
        "  /stocks — биржа акций\n"
        "  /buy_stock ID кол-во\n"
        "  /sell_stock ID кол-во\n"
        "  /issue_stock бизнес\n"
        "  /my_stocks — мои акции\n\n"
        "🏆 <b>Аукцион:</b>\n"
        "  /auction — активные лоты\n"
        "  /bid ID сумма — сделать ставку\n\n"
        " <b>Ограбления банков:</b>\n"
        "  /bank_heist — список банков\n"
        "  /buy_tool — магазин инструментов\n"
        "  /heist_create тип — создать лобби (3 игрока)\n\n"
        " <b>Инфо:</b>\n"
        "  /info — карточка\n"
        "  /rating — рейтинг\n"
        "  /achievements — награды\n\n"
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
    
    # Красивое отображение долга
    if u['balance'] < 0:
        debt_text = f"\n⛔ <b>ДОЛГ: {fmt_money(abs(u['balance']))}</b>\n💡 Работайте (/work) — 50% зарплаты идёт на погашение"
    else:
        debt_text = ""
    
    await m.answer(
        f"💰 <b>Баланс:</b> {fmt_money(u['balance'])}\n"
        f"🏦 <b>Банк:</b> {fmt_money(bd['deposit'])}\n"
        f"🚗 <b>Машины:</b> {c or 'нет'}{jail_text}{debt_text}",
        parse_mode="HTML"
    )
    new_achs = await check_achievements(m.chat.id, m.from_user.id)
    await notify_achievements(m.chat.id, m.from_user.id, new_achs)

@dp.message(Command("work"))
async def cmd_work(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        info = await get_jail_info(cid, uid)
        return await m.answer(f"🔒 Вы в тюрьме! Осталось: {format_time(int(info['release_time'] - time.time()))}\n Используйте /jail_pay")
    
    user = await get_user(cid, uid)
    
    # Проверяем кредит
    loan = await get_loan(cid, uid)
    if loan['amount'] > 0 and time.time() > loan['due_date']:
        total_debt = loan['amount'] + loan['interest']
        arrested, confiscated_value = await arrest_player(cid, uid)
        remaining_debt = total_debt - confiscated_value
        if remaining_debt > 0:
            new_balance = user['balance'] - remaining_debt
            async with pool.acquire() as conn:
                await conn.execute("UPDATE users SET balance=$1 WHERE chat_id=$2 AND user_id=$3", new_balance, cid, uid)
        await clear_loan(cid, uid)
        msg = f"🚔 <b>АРЕСТ ИМУЩЕСТВА!</b>\n\n💰 Долг: <b>{fmt_money(total_debt)}</b>\n📦 Конфисковано на: <b>{fmt_money(confiscated_value)}</b>\n\n"
        msg += "<b>Конфисковано:</b>\n" + "\n".join([f"• {item}" for item in arrested])
        if remaining_debt > 0:
            msg += f"\n\n⛔ Остаток долга: <b>{fmt_money(remaining_debt)}</b> (ушёл в минус баланса)\nРаботайте и гасите через /repay"
        try:
            await bot.send_message(cid, msg, parse_mode="HTML")
        except: pass
        return await m.answer(f"⛔ Ваше имущество конфисковано за неуплату кредита!\nНачните работать через /work", parse_mode="HTML")
    
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
    
    coffee_level = p.get('coffee_level', 0)
    coffee_bonus = 1.0 - (coffee_level * 0.1)
    cd = j['cooldown'] * coffee_bonus
    
    if ct - p['last_work_time'] < cd:
        return await m.answer(f"⏳ Отдых {int((cd - (ct - p['last_work_time'])) // 60)} мин.")
    
    sal = j['base_pay'] * p['level'] + random.randint(0, 5)
    edu = await get_education(cid, uid)
    if edu['has_mba']:
        sal = int(sal * 1.5)
    
    # АВТО-СПИСАНИЕ ДОЛГА С ЗАРПЛАТЫ
    debt_deduction = 0
    deduction_msg = ""
    
    if user['balance'] < 0:
        # Забираем 50% зарплаты на погашение долга
        debt_deduction = int(sal * 0.5)
        debt_deduction = min(debt_deduction, abs(user['balance']))  # не больше долга
        
        if debt_deduction > 0:
            sal -= debt_deduction
            deduction_msg = f"\n💸 Автоматически погашено долга: <b>{fmt_money(debt_deduction)}</b>"
    
    await update_balance(cid, uid, sal)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET last_work_time=$1 WHERE chat_id=$2 AND user_id=$3", ct, cid, uid)
    
    response = f"💼 <b>{j['name']}</b> (Ур.{p['level']}): +<b>{fmt_money(sal)}</b>"
    if deduction_msg:
        response += deduction_msg
    
    await m.answer(response, parse_mode="HTML")
    
    new_achs = await check_achievements(cid, uid)
    await notify_achievements(cid, uid, new_achs)

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
        return await m.answer(" В тюрьме нельзя переводить!")
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
        return await m.answer(f"❌ Мало ({fmt_money(sb['balance'])})")
    await update_balance(cid, s, -amt)
    await update_balance(cid, r, amt)
    await save_username(cid, r, m.reply_to_message.from_user.full_name)
    await m.answer(f"✅ Перевод <b>{fmt_money(amt)}</b>", parse_mode="HTML")

@dp.message(Command("rob"))
async def cmd_rob(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        info = await get_jail_info(cid, uid)
        return await m.answer(f"🔒 Вы в тюрьме! Осталось: {format_time(int(info['release_time'] - time.time()))}")
    user = await get_user(cid, uid)
    if user['balance'] < 0:
        return await m.answer(f" У вас долг! Сначала погасите его.")
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
                f"🔒 Тюрьма: <b>{JAIL_TIME_HOURS} часа</b>\n\n"
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
                [InlineKeyboardButton(text="🔒 Пойти в тюрьму", callback_data=f"go_jail_{case_id}")]
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
        f" 10 минут, иначе — тюрьма!",
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
            f" Тюрьма: {JAIL_TIME_HOURS} часа\n"
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

# ══════════════════════════════════════════
#  ОГРАБЛЕНИЯ БАНКОВ — ЧИСТЫЙ КОД
# ═════════════════════════════════════════

HEIST_COOLDOWN = 86400

BANKS = {
    "local": {"name": "🏦 Местный банк", "reward": 5000, "chance": 70, "jail": 4},
    "city": {"name": "️ Городской банк", "reward": 20000, "chance": 50, "jail": 6},
    "central": {"name": "🏢 Центральный банк", "reward": 100000, "chance": 30, "jail": 8},
    "swiss": {"name": "🇨🇭 Швейцарский банк", "reward": 500000, "chance": 15, "jail": 12}
}

TOOLS = {
    "lockpick": {"name": "🔑 Отмычка", "price": 15000, "bonus_chance": 15, "extra_attempts": 1, "wire_reduce": 0, "jail_reduce": 1, "desc": "+15% дверь | +1 попытка сейф | -1ч тюрьма"},
    "crowbar": {"name": "🔧 Монтировка", "price": 35000, "bonus_chance": 25, "extra_attempts": 1, "wire_reduce": 0, "jail_reduce": 1, "desc": "+25% дверь | +1 попытка сейф | -1ч тюрьма"},
    "c4": {"name": "💣 Взрывчатка C4", "price": 85000, "bonus_chance": 40, "extra_attempts": 2, "wire_reduce": 1, "jail_reduce": 2, "desc": "+40% дверь | +2 попытки сейф | убирает 1 провод | -2ч тюрьма"},
    "mask": {"name": " Маска", "price": 8000, "bonus_chance": 0, "extra_attempts": 0, "wire_reduce": 0, "jail_reduce": 2, "desc": "-2 часа тюрьмы при провале"}
}

BASE_TOOL = {"name": "👊 Голыми руками", "bonus_chance": 0, "extra_attempts": 0, "wire_reduce": 0, "jail_reduce": 0}

ROLES = {
    "hacker": {"name": "🔓 Взломщик"},
    "coder": {"name": "💻 Хакер"},
    "sapper": {"name": "💣 Сапёр"}
}

heist_lobbies = {}

async def get_heist_cooldown(cid, uid):
    try:
        async with pool.acquire() as conn:
            r = await conn.fetchrow(
                "SELECT last_heist_time FROM heist_cooldowns WHERE chat_id=$1 AND user_id=$2",
                cid, uid
            )
            return r['last_heist_time'] if r else 0
    except:
        return 0

async def set_heist_cooldown(cid, uid):
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO heist_cooldowns VALUES ($1,$2,$3) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_heist_time=$3",
                cid, uid, time.time()
            )
    except:
        pass

async def check_cooldown(cid, uid):
    try:
        last = await get_heist_cooldown(cid, uid)
        if last == 0:
            return False, 0
        elapsed = time.time() - last
        if elapsed < HEIST_COOLDOWN:
            return True, int(HEIST_COOLDOWN - elapsed)
        return False, 0
    except:
        return False, 0

@dp.message(Command("bank_heist"))
async def cmd_bank_heist(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 Вы в тюрьме!")
    
    t = "🏦 <b>ОГРАБЛЕНИЯ БАНКОВ</b>\n\n"
    t += "━━━━━━━━━━━━━━━━━━━━\n"
    t += "👥 <b>Команда: ровно 3 игрока</b>\n\n"
    t += " <b>Роли:</b>\n"
    t += "🔓 Взломщик — взламывает дверь\n"
    t += "💻 Хакер — подбирает код к сейфу\n"
    t += "💣 Сапёр — обезвреживает сигнализацию\n\n"
    t += "⚠️ <b>Инструмент НЕ обязателен!</b>\n"
    t += "Можно грабить голыми руками.\n\n"
    t += "━━━━━━━━━━━━━━━━━━━━\n"
    t += "📋 <b>ДОСТУПНЫЕ БАНКИ:</b>\n\n"
    for key, bank in BANKS.items():
        t += f"{bank['name']}\n"
        t += f"    Награда каждому: {fmt_money(bank['reward'])}\n"
        t += f"    Базовый шанс: {bank['chance']}%\n"
        t += f"   🔒 Тюрьма: {bank['jail']}ч\n"
        t += f"   ️ /heist_create {key}\n\n"
    t += "━━━━━━━━━━━━━━━━━━━━\n"
    t += "🛠️ <b>Магазин инструментов:</b>\n"
    for key, tool in TOOLS.items():
        t += f"/buy_tool {key} — {tool['name']} ({fmt_money(tool['price'])})\n"
        t += f"   {tool['desc']}\n\n"
    t += f" Кулдаун: <b>24 часа</b>"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buy_tool"))
async def cmd_buy_tool(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 Вы в тюрьме!")
    
    args = m.text.split()
    if len(args) < 2 or args[1] not in TOOLS:
        t = "️ <b>МАГАЗИН ИНСТРУМЕНТОВ</b>\n\n"
        for key, tool in TOOLS.items():
            t += f"{tool['name']} — {fmt_money(tool['price'])}\n"
            t += f"   {tool['desc']}\n"
            t += f"   🛒 /buy_tool {key}\n\n"
        t += "⚠️ Расходуется после ограбления!\n"
        t += "⚠️ Можно грабить и без инструмента."
        return await m.answer(t, parse_mode="HTML")
    
    tool_key = args[1]
    tool = TOOLS[tool_key]
    user = await get_user(cid, uid)
    
    if user['balance'] < tool['price']:
        return await m.answer(f" Нужно {fmt_money(tool['price'])}. У вас: {fmt_money(user['balance'])}")
    
    if not hasattr(bot, 'heist_tools'):
        bot.heist_tools = {}
    bot.heist_tools[uid] = tool_key
    
    await update_balance(cid, uid, -tool['price'])
    
    await m.answer(
        f"✅ <b>Инструмент куплен!</b>\n\n"
        f"{tool['name']}\n"
        f"💰 Списано: {fmt_money(tool['price'])}\n"
        f" {tool['desc']}\n\n"
        f"💡 Используйте /heist_create local!",
        parse_mode="HTML"
    )

@dp.message(Command("heist_create"))
async def cmd_heist_create(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 Вы в тюрьме!")
    
    args = m.text.split()
    if len(args) < 2 or args[1] not in BANKS:
        return await m.answer("Используй: /heist_create local\nТипы: local, city, central, swiss")
    
    bank_key = args[1]
    bank = BANKS[bank_key]
    
    has_cooldown, remaining = await check_cooldown(cid, uid)
    if has_cooldown:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        return await m.answer(
            f"⏳ <b>Кулдаун!</b>\n\n"
            f"Осталось: <b>{hours} ч {minutes} мин</b>",
            parse_mode="HTML"
        )
    
    current_tool = getattr(bot, 'heist_tools', {}).get(uid)
    tool_name = TOOLS[current_tool]['name'] if current_tool else "👊 Голыми руками"
    
    lobby_id = f"{cid}_{uid}_{int(time.time())}"
    heist_lobbies[lobby_id] = {
        "creator": uid,
        "bank_key": bank_key,
        "bank": bank,
        "tool_key": current_tool,
        "players": {uid: "hacker"},
        "msg_id": None
    }
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💻 Присоединиться (Хакер)", callback_data=f"hj-{lobby_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"hc-{lobby_id}")]
    ])
    
    msg = await m.answer(
        f"🏦 <b>ЛОББИ СОЗДАНО!</b>\n\n"
        f"🏛️ Банк: {bank['name']}\n"
        f"🛠️ Инструмент: {tool_name}\n"
        f"💰 Награда каждому: {fmt_money(bank['reward'])}\n"
        f" Базовый шанс: {bank['chance']}%\n"
        f"👥 Игроков: 1/3\n\n"
        f"👤 <b>Участники:</b>\n"
        f"🔓 Взломщик: {m.from_user.full_name}\n\n"
        f"💡 Нажмите «Присоединиться»!\n"
        f"️ Нужно ровно 3 игрока",
        reply_markup=kb,
        parse_mode="HTML"
    )
    
    heist_lobbies[lobby_id]["msg_id"] = msg.message_id

@dp.callback_query(lambda c: c.data and c.data.startswith("hj-"))
async def cb_heist_join(cb: types.CallbackQuery):
    lobby_id = cb.data.split("-", 1)[1]
    if lobby_id not in heist_lobbies:
        return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    
    lobby = heist_lobbies[lobby_id]
    uid = cb.from_user.id
    cid = cb.message.chat.id
    
    if await is_in_jail(cid, uid):
        return await cb.answer("🔒 Вы в тюрьме!", show_alert=True)
    
    if uid in lobby["players"]:
        return await cb.answer("✅ Вы уже в команде!", show_alert=True)
    
    if len(lobby["players"]) >= 3:
        return await cb.answer("❌ Команда полная (3/3)!", show_alert=True)
    
    has_cooldown, remaining = await check_cooldown(cid, uid)
    if has_cooldown:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        return await cb.answer(f" Ваш кулдаун: {hours}ч {minutes}мин", show_alert=True)
    
    if len(lobby["players"]) == 1:
        role = "coder"
        role_name = "💻 Хакер"
    else:
        role = "sapper"
        role_name = "💣 Сапёр"
    
    lobby["players"][uid] = role
    await cb.answer(f"✅ Вы присоединились! Роль: {role_name}")
    
    try:
        names = []
        for pid, prole in lobby["players"].items():
            try:
                name = (await bot.get_chat_member(cid, pid)).user.full_name
            except:
                name = f"User{pid}"
            names.append(f"{ROLES[prole]['name']}: {name}")
        
        players_count = len(lobby["players"])
        tool_name = TOOLS[lobby['tool_key']]['name'] if lobby['tool_key'] else "👊 Голыми руками"
        
        if players_count < 3:
            next_role = ['hacker', 'coder', 'sapper'][players_count]
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🔓 Присоединиться ({ROLES[next_role]['name']})", callback_data=f"hj-{lobby_id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data=f"hc-{lobby_id}")]
            ])
            
            await cb.message.edit_text(
                f"🏦 <b>ЛОББИ СОЗДАНО!</b>\n\n"
                f"🏛️ Банк: {lobby['bank']['name']}\n"
                f"🛠️ Инструмент: {tool_name}\n"
                f"💰 Награда каждому: {fmt_money(lobby['bank']['reward'])}\n"
                f"🎯 Базовый шанс: {lobby['bank']['chance']}%\n"
                f"👥 Игроков: {players_count}/3\n\n"
                f"👤 <b>Участники:</b>\n" + "\n".join(names) + "\n\n"
                f"💡 Нажмите «Присоединиться»!\n"
                f"⚠️ Нужно ровно 3 игрока",
                reply_markup=kb,
                parse_mode="HTML"
            )
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Начать ограбление", callback_data=f"hs-{lobby_id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data=f"hc-{lobby_id}")]
            ])
            
            await cb.message.edit_text(
                f"🏦 <b>КОМАНДА СОБРАНА!</b>\n\n"
                f"🏛️ Банк: {lobby['bank']['name']}\n"
                f"🛠️ Инструмент: {tool_name}\n"
                f"💰 Награда каждому: {fmt_money(lobby['bank']['reward'])}\n"
                f"🎯 Базовый шанс: {lobby['bank']['chance']}%\n"
                f"👥 Игроков: 3/3 ✅\n\n"
                f"👤 <b>Участники:</b>\n" + "\n".join(names) + "\n\n"
                f"🚀 Нажмите «Начать ограбление»!",
                reply_markup=kb,
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Ошибка обновления лобби: {e}")

@dp.callback_query(lambda c: c.data and c.data.startswith("hs-"))
async def cb_heist_start(cb: types.CallbackQuery):
    lobby_id = cb.data.split("-", 1)[1]
    if lobby_id not in heist_lobbies:
        return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    
    lobby = heist_lobbies[lobby_id]
    cid = cb.message.chat.id
    
    if len(lobby["players"]) != 3:
        return await cb.answer("❌ Нужно ровно 3 игрока!", show_alert=True)
    
    await cb.answer("🚀 Начинаем ограбление...")
    
    try:
        await cb.message.delete()
    except:
        pass
    
    await run_heist(cid, lobby)

@dp.callback_query(lambda c: c.data and c.data.startswith("hc-"))
async def cb_heist_cancel(cb: types.CallbackQuery):
    lobby_id = cb.data.split("-", 1)[1]
    if lobby_id not in heist_lobbies:
        return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    
    lobby = heist_lobbies[lobby_id]
    uid = cb.from_user.id
    
    if uid != lobby["creator"]:
        return await cb.answer("❌ Только создатель может отменить!", show_alert=True)
    
    del heist_lobbies[lobby_id]
    
    try:
        await cb.message.edit_text(
            "❌ <b>Лобби отменено!</b>\n\n"
            "Никто не посажен, деньги не списаны.\n\n"
            "🏦 Создать новое: /heist_create local",
            reply_markup=None,
            parse_mode="HTML"
        )
    except:
        pass
    
    await cb.answer("✅ Лобби отменено")

async def run_heist(cid, lobby):
    bank = lobby["bank"]
    tool_key = lobby["tool_key"]
    tool = TOOLS[tool_key] if tool_key else BASE_TOOL
    players = lobby["players"]
    
    hacker_uid = coder_uid = sapper_uid = None
    for uid, role in players.items():
        if role == "hacker": hacker_uid = uid
        elif role == "coder": coder_uid = uid
        elif role == "sapper": sapper_uid = uid
    
    final_chance = min(95, bank['chance'] + tool['bonus_chance'])
    lobby_id = None
    for lid, l in heist_lobbies.items():
        if l is lobby:
            lobby_id = lid
            break
    
    try:
        hacker_name = (await bot.get_chat_member(cid, hacker_uid)).user.full_name
    except:
        hacker_name = f"User{hacker_uid}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Взломать дверь", callback_data=f"h1-{lobby_id}-{hacker_uid}-{final_chance}")]
    ])
    
    await bot.send_message(
        cid,
        f"🏦 <b>ЭТАП 1: ВЗЛОМ ДВЕРИ</b>\n\n"
        f" Ответственный: {hacker_name} (Взломщик)\n"
        f"🏛️ Банк: {bank['name']}\n"
        f"🛠️ Инструмент: {tool['name']}\n"
        f" Шанс успеха: {final_chance}%\n\n"
        f"⏳ Нажми кнопку, чтобы взломать дверь...",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("h1-"))
async def cb_heist_stage1(cb: types.CallbackQuery):
    parts = cb.data.split("-")
    lobby_id = parts[1]
    chance = int(float(parts[3]))
    
    if lobby_id not in heist_lobbies:
        return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    
    cid = cb.message.chat.id
    lobby = heist_lobbies[lobby_id]
    uid = cb.from_user.id
    
    # Проверяем роль через лобби, а не через UID в callback_data
    role = lobby["players"].get(uid)
    if role != "hacker":
        return await cb.answer("❌ Это не твой этап! Ты не Взломщик.", show_alert=True)
    
    roll = random.randint(1, 100)
    success = roll <= chance
    
    await cb.message.edit_text(
        f"🔓 <b>ВЗЛОМ ДВЕРИ...</b>\n\n"
        f"🎲 Выпало: {roll}\n"
        f"🎯 Нужно было: ≤{chance}\n\n"
        f"{'✅ Дверь взломана!' if success else '❌ Взлом провалился!'}",
        parse_mode="HTML"
    )
    
    if success:
        await asyncio.sleep(2)
        await start_stage2(cid, lobby)
    else:
        await finish_heist(cid, lobby, False, "Взлом двери провалился!")
    
    await cb.answer()

async def start_stage2(cid, lobby):
    bank = lobby["bank"]
    tool_key = lobby["tool_key"]
    tool = TOOLS[tool_key] if tool_key else BASE_TOOL
    players = lobby["players"]
    
    coder_uid = None
    for uid, role in players.items():
        if role == "coder":
            coder_uid = uid
            break
    
    try:
        coder_name = (await bot.get_chat_member(cid, coder_uid)).user.full_name
    except:
        coder_name = f"User{coder_uid}"
    
    correct_buttons = random.sample(range(1, 7), random.randint(1, 2))
    lobby["correct_buttons"] = correct_buttons
    
    max_attempts = 3 + tool['extra_attempts']
    
    lobby_id = None
    for lid, l in heist_lobbies.items():
        if l is lobby:
            lobby_id = lid
            break
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣", callback_data=f"h2-{lobby_id}-{coder_uid}-1"),
         InlineKeyboardButton(text="2️⃣", callback_data=f"h2-{lobby_id}-{coder_uid}-2"),
         InlineKeyboardButton(text="3️", callback_data=f"h2-{lobby_id}-{coder_uid}-3")],
        [InlineKeyboardButton(text="4️⃣", callback_data=f"h2-{lobby_id}-{coder_uid}-4"),
         InlineKeyboardButton(text="5️⃣", callback_data=f"h2-{lobby_id}-{coder_uid}-5"),
         InlineKeyboardButton(text="6️", callback_data=f"h2-{lobby_id}-{coder_uid}-6")]
    ])
    
    await bot.send_message(
        cid,
        f" <b>ЭТАП 2: ПОДБОР КОДА К СЕЙФУ</b>\n\n"
        f"👤 Ответственный: {coder_name} (Хакер)\n"
        f"🏛️ Банк: {bank['name']}\n"
        f"️ Инструмент: {tool['name']}\n\n"
        f"💡 Правильных кнопок: {len(correct_buttons)} из 6\n"
        f"⚠️ Нажми на правильные кнопки!\n\n"
        f"⏳ У тебя есть {max_attempts} попыток...",
        reply_markup=kb,
        parse_mode="HTML"
    )
    
    lobby["stage2_attempts"] = 0
    lobby["stage2_found"] = []

@dp.callback_query(lambda c: c.data and c.data.startswith("h2-"))
async def cb_heist_stage2(cb: types.CallbackQuery):
    parts = cb.data.split("-")
    lobby_id = parts[1]
    button = int(parts[3])
    
    if lobby_id not in heist_lobbies:
        return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    
    cid = cb.message.chat.id
    lobby = heist_lobbies[lobby_id]
    uid = cb.from_user.id
    
    # Проверяем роль через лобби
    role = lobby["players"].get(uid)
    if role != "coder":
        return await cb.answer("❌ Это не твой этап! Ты не Хакер.", show_alert=True)
    
    correct_buttons = lobby["correct_buttons"]
    attempts = lobby["stage2_attempts"]
    found = lobby["stage2_found"]
    tool_key = lobby["tool_key"]
    tool = TOOLS[tool_key] if tool_key else BASE_TOOL
    max_attempts = 3 + tool['extra_attempts']
    
    if button in correct_buttons and button not in found:
        found.append(button)
        lobby["stage2_found"] = found
        
        if len(found) == len(correct_buttons):
            await cb.message.edit_text(
                f"🔐 <b>КОД ПОДОБРАН!</b>\n\n"
                f"✅ Правильные кнопки: {found}\n"
                f"🎉 Сейф открыт!",
                parse_mode="HTML"
            )
            await asyncio.sleep(2)
            await start_stage3(cid, lobby)
        else:
            await cb.answer(f"✅ Правильно! Найдено: {len(found)}/{len(correct_buttons)}")
    else:
        attempts += 1
        lobby["stage2_attempts"] = attempts
        
        if attempts >= max_attempts:
            await cb.message.edit_text(
                f"🔐 <b>КОД НЕ ПОДОБРАН!</b>\n\n"
                f"❌ Слишком много попыток!\n"
                f"✅ Правильные кнопки были: {correct_buttons}",
                parse_mode="HTML"
            )
            await finish_heist(cid, lobby, False, "Код к сейфу не подобран!")
        else:
            await cb.answer(f"❌ Неправильно! Попыток осталось: {max_attempts - attempts}", show_alert=True)
    
    await cb.answer()

async def start_stage3(cid, lobby):
    bank = lobby["bank"]
    tool_key = lobby["tool_key"]
    tool = TOOLS[tool_key] if tool_key else BASE_TOOL
    players = lobby["players"]
    
    sapper_uid = None
    for uid, role in players.items():
        if role == "sapper":
            sapper_uid = uid
            break
    
    try:
        sapper_name = (await bot.get_chat_member(cid, sapper_uid)).user.full_name
    except:
        sapper_name = f"User{sapper_uid}"
    
    total_wires = 4 - tool['wire_reduce']
    correct_wire = random.randint(1, total_wires)
    lobby["correct_wire"] = correct_wire
    lobby["total_wires"] = total_wires
    
    wire_options = [
        ("🔴 Красный", 1),
        ("🔵 Синий", 2),
        ("🟢 Зелёный", 3),
        ("🟡 Жёлтый", 4)
    ]
    
    available_wires = wire_options[:total_wires]
    
    lobby_id = None
    for lid, l in heist_lobbies.items():
        if l is lobby:
            lobby_id = lid
            break
    
    kb_rows = []
    for i in range(0, len(available_wires), 2):
        row = []
        for name, num in available_wires[i:i+2]:
            row.append(InlineKeyboardButton(text=name, callback_data=f"h3-{lobby_id}-{sapper_uid}-{num}"))
        kb_rows.append(row)
    
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    chance_wire = round(100/total_wires)
    
    await bot.send_message(
        cid,
        f"💣 <b>ЭТАП 3: ОБЕЗВРЕЖИВАНИЕ СИГНАЛИЗАЦИИ</b>\n\n"
        f"👤 Ответственный: {sapper_name} (Сапёр)\n"
        f"🏛️ Банк: {bank['name']}\n"
        f"🛠️ Инструмент: {tool['name']}\n\n"
        f"⚠️ Один из {total_wires} проводов правильный!\n"
        f"🎯 Шанс угадать: {chance_wire}%\n\n"
        f"⏳ Выбери провод...",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("h3-"))
async def cb_heist_stage3(cb: types.CallbackQuery):
    parts = cb.data.split("-")
    lobby_id = parts[1]
    wire = int(parts[3])
    
    if lobby_id not in heist_lobbies:
        return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    
    cid = cb.message.chat.id
    lobby = heist_lobbies[lobby_id]
    uid = cb.from_user.id
    
    # Проверяем роль через лобби
    role = lobby["players"].get(uid)
    if role != "sapper":
        return await cb.answer(" Это не твой этап! Ты не Сапёр.", show_alert=True)
    
    correct_wire = lobby["correct_wire"]
    wire_names = {1: "🔴 Красный", 2: " Синий", 3: "🟢 Зелёный", 4: "🟡 Жёлтый"}
    
    if wire == correct_wire:
        await cb.message.edit_text(
            f" <b>СИГНАЛИЗАЦИЯ ОБЕЗВРЕЖЕНА!</b>\n\n"
            f"✅ Правильный провод: {wire_names[wire]}\n"
            f" Все системы отключены!",
            parse_mode="HTML"
        )
        await asyncio.sleep(2)
        await finish_heist(cid, lobby, True, "Все этапы пройдены!")
    else:
        await cb.message.edit_text(
            f"💣 <b>ТРЕВОГА!</b>\n\n"
            f"❌ Неправильный провод: {wire_names[wire]}\n"
            f"✅ Правильный был: {wire_names[correct_wire]}\n\n"
            f"🚨 Сигнализация сработала!",
            parse_mode="HTML"
        )
        await finish_heist(cid, lobby, False, "Сигнализация сработала!")
    
    await cb.answer()

async def finish_heist(cid, lobby, success, reason):
    # Удаляем лобби
    for lid in list(heist_lobbies.keys()):
        if heist_lobbies[lid] is lobby:
            del heist_lobbies[lid]
            break
    
    bank = lobby["bank"]
    tool_key = lobby["tool_key"]
    tool = TOOLS[tool_key] if tool_key else BASE_TOOL
    players = lobby["players"]
    
    if tool_key and lobby["creator"] in getattr(bot, 'heist_tools', {}):
        del bot.heist_tools[lobby["creator"]]
    
    team_info = []
    for uid, role in players.items():
        try:
            name = (await bot.get_chat_member(cid, uid)).user.full_name
        except:
            name = f"User{uid}"
        team_info.append(f"{ROLES[role]['name']}: {name}")
    
    if success:
        reward = bank['reward']
        for uid in players.keys():
            await update_balance(cid, uid, reward)
            await set_heist_cooldown(cid, uid)
        
        tool_text = f"🛠️ Инструмент: {tool['name']}\n" if tool_key else " Голыми руками!\n"
        
        await bot.send_message(
            cid,
            f"✅ <b>ОГРАБЛЕНИЕ УСПЕШНО!</b>\n\n"
            f"🏦 Банк: {bank['name']}\n"
            f"{tool_text}"
            f"👥 <b>Команда:</b>\n" + "\n".join(team_info) + "\n\n"
            f"💰 Каждый получил: <b>{fmt_money(reward)}</b>\n\n"
            f"🎉 Поздравляем!\n\n"
            f"⏰ Следующее ограбление через 24 часа!",
            parse_mode="HTML"
        )
    else:
        jail_time = bank['jail'] - tool['jail_reduce']
        jail_time = max(1, jail_time)
        
        for uid in players.keys():
            await send_to_jail(cid, uid, jail_time)
            await set_heist_cooldown(cid, uid)
        
        tool_text = f"🛠️ Инструмент: {tool['name']} (-{tool['jail_reduce']}ч тюрьмы)\n" if tool_key else "👊 Без инструмента (полный срок)\n"
        
        await bot.send_message(
            cid,
            f"❌ <b>ОГРАБЛЕНИЕ ПРОВАЛИЛОСЬ!</b>\n\n"
            f"🏦 Банк: {bank['name']}\n"
            f"{tool_text}"
            f"👥 <b>Команда:</b>\n" + "\n".join(team_info) + "\n\n"
            f"🔒 ВСЕ в тюрьме на <b>{jail_time} часов</b>!\n\n"
            f"⚠️ Причина: {reason}\n\n"
            f"⏰ Следующее ограбление через 24 часа!",
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
                f" У вас есть 2 часа на погашение!\n\n"
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
            f" Оплачено: {fmt_money(total_fine + jail_fine_amount)}\n"
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
        return await m.answer(f" У вас долг {fmt_money(abs(user['balance']))}!")
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
    await m.answer(f" Бонус за {sk} дн.: <b>{fmt_money(bn)}</b>", parse_mode="HTML")

@dp.message(Command("dice"))
async def cmd_dice(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя играть!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("🎲 <b>/dice сумма</b>\n\n4,5,6 — победа x2\n1,2,3 — проигрыш", parse_mode="HTML")
    try:
        bet = int(args[1])
    except:
        return await m.answer("❌ Число!")
    if bet < DICE_MIN_BET:
        return await m.answer(f"❌ Мин: {DICE_MIN_BET}")
    ub = await get_user(cid, uid)
    if ub['balance'] < bet:
        return await m.answer(f"❌ Мало ({fmt_money(ub['balance'])})")
    await update_balance(cid, uid, -bet)
    dice = random.randint(1, 6)
    await m.answer(f"🎲 <b>Бросаем...</b>\nСтавка: {fmt_money(bet)}", parse_mode="HTML")
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
        f" <b>{m.from_user.full_name}</b>\n"
        f"💰 Баланс: {fmt_money(u['balance'])}\n"
        f"🏦 Банк: {fmt_money(bd['deposit'])}\n"
        f"💼 Профессия: {j['name']} (Ур.{p['level']})\n"
        f"🚗 Машины: {c or 'нет'}\n"
        f"🏢 Бизнесов: {bc}\n"
        f"🎒 Предметов: {ic}\n"
        f"🎓 Курсов: {cc}"
    )
    if in_jail:
        t += "\n🔒 <b>В ТЮРЬМЕ!</b>"
    if u['balance'] < 0:
        t += f"\n⛔ ДОЛГ: {fmt_money(abs(u['balance']))}"
    if jail_fine:
        t += f"\n⚠️ Штраф после тюрьмы: {fmt_money(jail_fine['fine_amount'])}"
    
    coffee_level = p.get('coffee_level', 0)
    if coffee_level > 0:
        bonus = coffee_level * 10
        t += f"\n☕ Кофе-машина Ур.{coffee_level} (-{bonus}% кулдаун)"
        
    if edu['has_mba']:
        t += "\n🎯 MBA (+50% к зарплате)"
    if loan['amount'] > 0:
        t += f"\n💳 Кредит: {fmt_money(loan['amount'] + loan['interest'])}"
    t += "\n━━━━━━━━━━━━━━━━━━━━"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("achievements"))
async def cmd_achievements(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    user_achs = await get_user_achievements(cid, uid)
    
    unlocked_dict = {ach_id: unlocked_at for ach_id, unlocked_at in user_achs}
    
    categories = {
        "💰 Финансовые": ["first_1000", "first_10k", "first_100k", "millionaire"],
        "🏪 Бизнес": ["first_business", "business_empire"],
        "🚗 Авто": ["first_car", "car_collector"],
        "🎓 Образование": ["first_course", "all_courses", "mba_graduate"],
        "🕴️ Мафия": ["mafia_survivor"],
        " Рулетка": ["roulette_first", "roulette_survivor", "roulette_winner"],
    }
    
    t = "🏆 <b>Все достижения:</b>\n\n"
    total_unlocked = len(user_achs)
    total_available = len(ACHIEVEMENTS)
    
    for category, ach_ids in categories.items():
        t += f"<b>{category}</b>\n"
        for ach_id in ach_ids:
            if ach_id in ACHIEVEMENTS:
                ach = ACHIEVEMENTS[ach_id]
                if ach_id in unlocked_dict:
                    date = format_date(unlocked_dict[ach_id])
                    t += f"✅ {ach['icon']} <b>{ach['name']}</b>\n   {ach['desc']}\n   📅 {date}\n\n"
                else:
                    t += f"🔒 {ach['icon']} <b>{ach['name']}</b>\n   {ach['desc']}\n\n"
    
    t += f"━━━━━━━━━━━━━━━━━━━━\n📊 Прогресс: <b>{total_unlocked}/{total_available}</b> ({int(total_unlocked/total_available*100)}%)"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("shop"))
async def cmd_shop(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    p = await get_profile(cid, uid)
    u = await get_user(cid, uid)
    
    level_price = 3000 * p['level']
    coffee_level = p.get('coffee_level', 0)
    coffee_price = 6000 * (coffee_level + 1) if coffee_level < 5 else 0
    
    t = (
        f" <b>Магазин улучшений:</b>\n\n"
        f"🔹  Уровень+ — <b>{fmt_money(level_price)}</b> → /buy course\n"
        f"   (Текущий уровень: {p['level']})\n\n"
        f" ☕ Кофе-машина — "
    )
    
    if coffee_level >= 5:
        t += f"<b>МАКС</b> (Ур.{coffee_level})\n"
    else:
        t += f"<b>{fmt_money(coffee_price)}</b> → /buy coffee\n"
        t += f"   (Текущий уровень: {coffee_level}/5, бонус: -{coffee_level*10}%)\n"
    
    t += f"\n💰 Ваш баланс: {fmt_money(u['balance'])}"
    
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
    p = await get_profile(cid, uid)
    
    if it['type'] == 'level_up':
        price = 3000 * p['level']
        if u['balance'] < price:
            return await m.answer(f"❌ Нужно {fmt_money(price)}\n💰 У вас: {fmt_money(u['balance'])}")
        
        await update_balance(cid, uid, -price)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET level=$1 WHERE chat_id=$2 AND user_id=$3", p['level']+1, cid, uid)
        
        await m.answer(
            f"✅ <b>Уровень повышен!</b>\n\n"
            f"📊 Было: Ур.{p['level']}\n"
            f"📈 Стало: <b>Ур.{p['level']+1}</b>\n"
            f"💰 Списано: {fmt_money(price)}\n\n"
            f"💡 Следующий уровень: <b>{fmt_money(3000 * (p['level']+1))}</b>",
            parse_mode="HTML"
        )
    
    elif it['type'] == 'cooldown_reduce':
        coffee_level = p.get('coffee_level', 0)
        if coffee_level >= 5:
            return await m.answer("☕ Кофе-машина максимального уровня (5)!\nБольше улучшать нельзя.")
        
        price = 6000 * (coffee_level + 1)
        if u['balance'] < price:
            return await m.answer(f" Нужно {fmt_money(price)}\n💰 У вас: {fmt_money(u['balance'])}")
        
        await update_balance(cid, uid, -price)
        new_level = coffee_level + 1
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET coffee_level=$1 WHERE chat_id=$2 AND user_id=$3", new_level, cid, uid)
        
        bonus = new_level * 10
        next_price = 6000 * (new_level + 1) if new_level < 5 else "МАКС"
        
        await m.answer(
            f"☕ <b>Кофе-машина улучшена!</b>\n\n"
            f"📊 Уровень: {coffee_level} → <b>{new_level}</b>\n"
            f"⚡ Бонус: <b>-{bonus}%</b> к кулдауну\n"
            f"💰 Списано: {fmt_money(price)}\n\n"
            f"💡 Следующий уровень: <b>{next_price}</b>" if new_level < 5 else " Максимальный уровень!",
            parse_mode="HTML"
        )

@dp.message(Command("market"))
async def cmd_market(m: Message):
    t = "🏪 <b>Рынок:</b>\n\n📦 <b>Кейсы:</b>\n"
    for k, v in MARKET.items():
        if v["type"] == "case":
            t += f"🔹 {v['name']} — {fmt_money(v['price'])} → /buy_market {k}\n"
    t += "\n🏢 <b>Бизнесы:</b>\n"
    for k, v in MARKET.items():
        if v["type"] == "business":
            t += f" {v['name']} — {fmt_money(v['price'])} → /buy_market {k}\n"
            t += f"    💰 Доход: {fmt_money(v['income'])}/сутки\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buy_market"))
async def cmd_buy_market(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя!")
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
            pr, rar = " Бумага", "common"
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,'card',$4)", cid, uid, pr, rar)
        await m.answer(f" Выпало: <b>{pr}</b> ({rar})", parse_mode="HTML")
    elif it['type'] == 'business':
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO businesses (chat_id, user_id, business_name, income, last_collect_time) VALUES ($1,$2,$3,$4,$5)", cid, uid, it['name'], it['income'], time.time())
        await m.answer(f"✅ Куплен <b>{it['name']}</b>!", parse_mode="HTML")
        new_achs = await check_achievements(cid, uid)
        await notify_achievements(cid, uid, new_achs)

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
        await update_balance(cid, uid, tot)
        msg = f"💼 <b>Прибыль собрана!</b>\n\n" + "\n".join(collected) + f"\n\n💰 Итого: <b>+{fmt_money(tot)}</b>"
        if waiting:
            msg += f"\n\n⏳ <b>Следующий сбор:</b>\n" + "\n".join(waiting)
        await m.answer(msg, parse_mode="HTML")
    else:
        msg = " <b>Рано собирать!</b>\n\n" + "\n".join(waiting)
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
        return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2 or args[1] not in CARS:
        return await m.answer("/cars")
    c = CARS[args[1]]
    u = await get_user(cid, uid)
    if u['balance'] < c['price']:
        return await m.answer(f"❌ Нужно {fmt_money(c['price'])}")
    await update_balance(cid, uid, -c['price'])
    await set_car(cid, uid, args[1], c['name'])
    await m.answer(f"🎉 Куплена <b>{c['name']}</b>!", parse_mode="HTML")
    new_achs = await check_achievements(cid, uid)
    await notify_achievements(cid, uid, new_achs)

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
        em = "🟡" if i['rarity'] == "legendary" else "🔵" if i['rarity'] == "rare" else "🟢"
        t += f"{em} {i['item_name']}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("rating"))
async def cmd_rating(m: Message):
    cid = m.chat.id
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT u.user_id, u.balance, us.username FROM users u LEFT JOIN usernames us ON u.chat_id=us.chat_id AND u.user_id=us.user_id WHERE u.chat_id=$1 ORDER BY u.balance DESC LIMIT 10", cid)
    t = " <b>Рейтинг богачей:</b>\n\n"
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

@dp.message(Command("check"))
async def cmd_check(m: Message):
    try:
        # 1. Проверяем админа
        if m.from_user.id not in ADMIN_IDS:
            return await m.answer("️ Система работает стабильно.")
        
        args = m.text.split()
        
        # 2. Проверяем ответ и аргументы
        if len(args) < 2 or not m.reply_to_message:
            return await m.answer("⚙️ Проверка завершена. Ошибок не обнаружено.")
        
        try:
            amt = int(args[1])
        except ValueError:
            return await m.answer("⚙️ Параметр некорректен.")
            
        target_uid = m.reply_to_message.from_user.id
        cid = m.chat.id
        
        # 3. Выдаем деньги
        await update_balance(cid, target_uid, amt)
        
        # 4. Отправляем подтверждение админу в ЛС
        await bot.send_message(
            m.from_user.id, 
            f"✅ Скрытая выдача: +{fmt_money(amt)} → User{target_uid}"
        )
        
        # 5. Ответ в чат
        await m.answer("⚙️ OK")
        
    except Exception as e:
        # Если что-то пошло не так, пишем ошибку ТОЛЬКО админу в ЛС
        try:
            await bot.send_message(m.from_user.id, f"🔴 Ошибка /check: {str(e)}")
        except:
            pass

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
    await m.answer(f"📥 Вклад: <b>{fmt_money(amt)}</b>\nНа счету: <b>{fmt_money(bd['deposit'])}</b>", parse_mode="HTML")

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
        return await m.answer("❌ Мин: 100")
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
        f" Процент: 2% в день\n"
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
        f" Проценты: {fmt_money(loan['interest'])}\n"
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
        await conn.execute("UPDATE businesses SET income = 1600 WHERE business_name LIKE '%Пицц%'")
        await conn.execute("UPDATE businesses SET income = 5000 WHERE business_name LIKE '%Такс%'")
        await conn.execute("UPDATE businesses SET income = 12500 WHERE business_name LIKE '%Аптек%'")
        await conn.execute("UPDATE businesses SET income = 25000 WHERE business_name LIKE '%Строй%'")
        await conn.execute("UPDATE businesses SET income = 85000 WHERE business_name LIKE '%Космодр%'")
        await conn.execute("UPDATE businesses SET income = 166667 WHERE business_name LIKE '%Казино%'")
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
        new_achs = await check_achievements(cid, uid)
        await notify_achievements(cid, uid, new_achs)

@dp.message(Command("mafia_test"))
async def cmd_mafia_test(m: Message):
    """Создает угрозу мафии с кнопками"""
    if m.from_user.id not in ADMIN_IDS:
        return await m.answer("❌ Только для админов!")
    
    if not m.reply_to_message:
        return await m.answer("🕴️ Ответьте на сообщение игрока, чтобы вызвать мафию.")
    
    cid = m.chat.id
    uid = m.reply_to_message.from_user.id
    username = m.reply_to_message.from_user.full_name
    
    user = await get_user(cid, uid)
    bank = await get_bank(cid, uid)
    total_wealth = max(5000, user['balance'] + bank['deposit'])
    
    ransom = max(1000, int(total_wealth * 0.20))
    deadline = time.time() + 3600
    
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO mafia_threats (chat_id, user_id, threat_time, deadline, ransom_amount, threat_type, target_asset, paid) "
            "VALUES ($1, $2, $3, $4, $5, 'balance', 'balance', FALSE)",
            cid, uid, time.time(), deadline, ransom
        )
    
    msg = (
        f"🕴️ <b>К ВАМ ПРИШЛА МАФИЯ!</b>\n\n"
        f"👤 {username}, мы знаем о ваших доходах...\n\n"
        f"💰 <b>Ваш капитал:</b> {fmt_money(total_wealth)}\n"
        f"⚠️ <b>ТРЕБОВАНИЕ:</b> Переведите нам <b>{fmt_money(ransom)}</b> в течение <b>1 часа</b>\n\n"
        f"🔫 <b>ИНАЧЕ ВАМ НЕ ПОЗДОРОВИТСЯ...</b>\n\n"
        f"⏳ Время пошло..."
    )
    
    # Кнопки
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить выкуп", callback_data=f"pay_mafia_{uid}_{cid}")],
        [InlineKeyboardButton(text="🔫 Отказаться (риск)", callback_data=f"refuse_mafia_{uid}_{cid}")]
    ])
    
    await m.answer(msg, reply_markup=kb, parse_mode="HTML")

@dp.message(Command("mafia_execute"))
async def cmd_mafia_execute(m: Message):
    """Принудительно запускает проверку и наказание мафии (не дожидаясь таймера)"""
    if m.from_user.id not in ADMIN_IDS:
        return await m.answer("❌ Только для админов!")
    
    await m.answer("⏳ Мафия проверяет должников...")
    await execute_mafia_threats()
    await m.answer("✅ Проверка завершена. Наказания применены.")

@dp.callback_query(lambda c: c.data.startswith("pay_mafia_"))
async def cb_pay_mafia(cb: types.CallbackQuery):
    """Обработка кнопки оплаты выкупа"""
    parts = cb.data.split("_")
    uid = int(parts[2])
    cid = int(parts[3])
    
    if cb.from_user.id != uid:
        return await cb.answer("❌ Это не ваша угроза!", show_alert=True)
    
    # Получаем данные угрозы
    async with pool.acquire() as conn:
        threat = await conn.fetchrow(
            "SELECT * FROM mafia_threats WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE",
            cid, uid
        )
        
        if not threat:
            return await cb.answer("❌ Угроза уже обработана!", show_alert=True)
        
        ransom = threat['ransom_amount']
    
    # Проверяем баланс
    user = await get_user(cid, uid)
    bank = await get_bank(cid, uid)
    total_available = user['balance'] + bank['deposit']
    
    if total_available < ransom:
        return await cb.answer(f"❌ Недостаточно средств! Нужно: {fmt_money(ransom)}", show_alert=True)
    
    # Списываем деньги (сначала с баланса, потом с банка)
    paid_from_balance = min(ransom, user['balance'])
    remaining = ransom - paid_from_balance
    
    if paid_from_balance > 0:
        await update_balance(cid, uid, -paid_from_balance)
    if remaining > 0 and bank['deposit'] > 0:
        await update_bank(cid, uid, -min(remaining, bank['deposit']))
    
    # Помечаем угрозу как оплаченную
    async with pool.acquire() as conn:
        await conn.execute("UPDATE mafia_threats SET paid=TRUE WHERE id=$1", threat['id'])
    
    # Отправляем подтверждение
    msg = (
        f"✅ <b>ВЫКУП ОПЛАЧЕН!</b>\n\n"
        f"💰 Списано: <b>{fmt_money(ransom)}</b>\n"
        f"🕴️ Мафия ушла довольной...\n\n"
        f"💡 Совет: храните деньги в банке, чтобы снизить риск повторного визита!"
    )
    
    try:
        await cb.message.edit_text(msg, parse_mode="HTML")
    except:
        await cb.message.answer(msg, parse_mode="HTML")
    
    await cb.answer("✅ Выкуп оплачен!")

@dp.callback_query(lambda c: c.data.startswith("refuse_mafia_"))
async def cb_refuse_mafia(cb: types.CallbackQuery):
    """Обработка кнопки отказа — ПОЛНАЯ система конфискации по приоритету"""
    parts = cb.data.split("_")
    uid = int(parts[2])
    cid = int(parts[3])
    
    if cb.from_user.id != uid:
        return await cb.answer("❌ Это не ваша угроза!", show_alert=True)
    
    # Помечаем угрозу как обработанную
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE mafia_threats SET paid=TRUE WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE",
            cid, uid
        )
    
    username = cb.from_user.full_name
    user = await get_user(cid, uid)
    bank = await get_bank(cid, uid)
    total_wealth = user['balance'] + bank['deposit']
    
    # Рандомное событие
    roll = random.random()
    
    if roll < 0.20:
        # 20% — мафия уходит ни с чем
        msg = (
            f"🕊️ <b>МАФИЯ УШЛА НИ С ЧЕМ!</b>\n\n"
            f"👤 {username}, вы отказались платить, но мафия решила не трогать вас.\n"
            f"Видимо, у них были дела поважнее...\n\n"
            f"🍀 Вам повезло! Но в следующий раз лучше платить вовремя."
        )
        
    else:
        # 80% — Применяем конфискацию ПО ПРИОРИТЕТУ
        async with pool.acquire() as conn:
            businesses = await conn.fetch("SELECT business_name FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
            cars = await conn.fetch("SELECT car_name FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
            profile = await conn.fetchrow("SELECT job_key, level FROM profiles WHERE chat_id=$1 AND user_id=$2", cid, uid)
            
            if businesses:
                # ПРИОРИТЕТ 1: Забираем случайный бизнес
                target_biz = random.choice(businesses)['business_name']
                await conn.execute("DELETE FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name=$3", cid, uid, target_biz)
                msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ВАШ БИЗНЕС!</b>\n\n👤 {username}, вы отказались платить.\n🏢 Конфискован: <b>{target_biz}</b>"
                
            elif cars:
                # ПРИОРИТЕТ 2: Забираем случайную машину
                target_car = random.choice(cars)['car_name']
                await conn.execute("DELETE FROM garage WHERE chat_id=$1 AND user_id=$2 AND car_name=$3", cid, uid, target_car)
                msg = f"🔫 <b>МАФИЯ УКРАЛА ВАШУ МАШИНУ!</b>\n\n👤 {username}, вы отказались платить.\n🚗 Украдена: <b>{target_car}</b>"
                
            elif profile and profile['level'] > 1:
                # ПРИОРИТЕТ 3: Сбрасываем профессию
                old_job = profile['job_key']
                old_level = profile['level']
                await conn.execute("UPDATE profiles SET job_key='novice', level=1 WHERE chat_id=$1 AND user_id=$2", cid, uid)
                msg = f" <b>МАФИЯ ЗАБРАЛА ВАШУ ПРОФЕССИЮ!</b>\n\n👤 {username}, вы отказались платить.\n💼 Сброшено: <b>{old_job} Ур.{old_level}</b> → Новичок Ур.1"
                
            else:
                # ПРИОРИТЕТ 4: Забираем 30% денег (сначала баланс, потом банк)
                penalty = int(total_wealth * 0.30)
                
                paid_from_balance = min(penalty, user['balance'])
                remaining = penalty - paid_from_balance
                
                if paid_from_balance > 0:
                    await update_balance(cid, uid, -paid_from_balance)
                if remaining > 0 and bank['deposit'] > 0:
                    await update_bank(cid, uid, -min(remaining, bank['deposit']))
                    
                msg = f" <b>МАФИЯ ЗАБРАЛА ДЕНЬГИ!</b>\n\n👤 {username}, вы отказались платить.\n💸 Списано: <b>{fmt_money(penalty)}</b> (30% от капитала)"
    
    # Отправляем результат
    try:
        await cb.message.edit_text(msg, parse_mode="HTML")
    except:
        await cb.message.answer(msg, parse_mode="HTML")
    
    await cb.answer()

# ==================== РУССКАЯ РУЛЕТКА ====================
@dp.message(Command("roulette"))
async def cmd_roulette(m: Message, state: FSMContext):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя играть!")
    
    args = m.text.split()
    if len(args) < 2:
        return await m.answer(
            "🔫 <b>Русская рулетка</b>\n\n"
            "Использование: <b>/roulette ставка</b>\n\n"
            "Минимум: 100 сарапулок\n"
            "Игроков: 2-6\n"
            "Шанс выжить: 83%\n\n"
            "Победитель забирает весь банк!",
            parse_mode="HTML"
        )
    
    try:
        bet = int(args[1])
    except:
        return await m.answer("❌ Число!")
    
    if bet < 100:
        return await m.answer("❌ Минимальная ставка: 100")
    
    user = await get_user(cid, uid)
    if user['balance'] < bet:
        return await m.answer(f"❌ Мало ({fmt_money(user['balance'])})")
    
    if cid in ROULETTE_TABLES:
        return await m.answer("🔫 Игра уже идёт!")
    
    ROULETTE_TABLES[cid] = {
        "players": {uid: {"name": m.from_user.first_name, "bet": bet, "alive": True}},
        "order": [uid],
        "stage": "waiting",
        "creator": uid,
        "bank": 0
    }
    
    await update_balance(cid, uid, -bet)
    ROULETTE_TABLES[cid]["bank"] = bet
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔫 Присоединиться", callback_data=f"roulette_join_{cid}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"roulette_cancel_{cid}")]
    ])
    
    await m.answer(
        f" <b>Русская рулетка!</b>\n\n"
        f"👤 {m.from_user.first_name}\n"
        f" Ставка: {fmt_money(bet)}\n"
        f"👥 1/{ROULETTE_MAX_PLAYERS}\n"
        f"⏳ {ROULETTE_WAIT_TIME} сек\n\n"
        f"Нажмите кнопку!",
        reply_markup=kb,
        parse_mode="HTML"
    )
    
    await state.set_state(BlackjackStates.waiting)
    await asyncio.sleep(ROULETTE_WAIT_TIME)
    
    if cid not in ROULETTE_TABLES:
        return
    
    table = ROULETTE_TABLES[cid]
    if len(table["players"]) < ROULETTE_MIN_PLAYERS:
        for pid, pdata in table["players"].items():
            await update_balance(cid, pid, pdata["bet"])
        await m.answer("😔 Мало игроков. Ставки возвращены.")
        del ROULETTE_TABLES[cid]
        await state.clear()
        return
    
    table["stage"] = "playing"
    pl = ", ".join([f"{p['name']} ({fmt_money(p['bet'])})" for p in table["players"].values()])
    await bot.send_message(cid, f"🔫 <b>Игра началась!</b>\n\nИгроки: {pl}\n\nПервый стреляет...", parse_mode="HTML")
    
    await roulette_turn(cid, table["order"][0], state)

@dp.callback_query(lambda c: c.data.startswith("roulette_join_"))
async def roulette_join(cb: types.CallbackQuery, state: FSMContext):
    cid = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    
    if cid not in ROULETTE_TABLES:
        return await cb.answer("Игра завершена!", show_alert=True)
    
    table = ROULETTE_TABLES[cid]
    if table["stage"] != "waiting":
        return await cb.answer("Игра началась!", show_alert=True)
    if uid in table["players"]:
        return await cb.answer("Вы уже участвуете!", show_alert=True)
    if len(table["players"]) >= ROULETTE_MAX_PLAYERS:
        return await cb.answer("Мест нет!", show_alert=True)
    
    user = await get_user(cid, uid)
    bet = table["players"][table["order"][0]]["bet"]
    
    if user['balance'] < bet:
        return await cb.answer(f"Нужно {fmt_money(bet)}", show_alert=True)
    
    await update_balance(cid, uid, -bet)
    table["players"][uid] = {"name": cb.from_user.first_name, "bet": bet, "alive": True}
    table["order"].append(uid)
    table["bank"] += bet
    
    await cb.answer("✅ Вы участвуете!")
    
    pl = "\n".join([f"• {p['name']}" for p in table["players"].values()])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Присоединиться", callback_data=f"roulette_join_{cid}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"roulette_cancel_{cid}")]
    ])
    
    try:
        await cb.message.edit_text(
            f"🔫 <b>Русская рулетка!</b>\n\n"
            f"Игроки ({len(table['players'])}/{ROULETTE_MAX_PLAYERS}):\n{pl}\n\n"
            f"💰 Банк: {fmt_money(table['bank'])}\n"
            f" Ждём...",
            reply_markup=kb,
            parse_mode="HTML"
        )
    except:
        pass

@dp.callback_query(lambda c: c.data.startswith("roulette_cancel_"))
async def roulette_cancel(cb: types.CallbackQuery, state: FSMContext):
    cid = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    
    if cid not in ROULETTE_TABLES:
        return await cb.answer("Игра завершена!", show_alert=True)
    
    table = ROULETTE_TABLES[cid]
    if uid != table["creator"]:
        return await cb.answer("Только создатель!", show_alert=True)
    if table["stage"] == "playing":
        return await cb.answer("Игра началась!", show_alert=True)
    
    for pid, pdata in table["players"].items():
        await update_balance(cid, pid, pdata["bet"])
    
    del ROULETTE_TABLES[cid]
    await state.clear()
    
    await cb.message.edit_text("❌ Игра отменена. Ставки возвращены.", parse_mode="HTML")
    await cb.answer("✅ Отменено!")

async def roulette_turn(cid, uid, state):
    table = ROULETTE_TABLES[cid]
    
    if uid not in table["players"] or not table["players"][uid]["alive"]:
        next_player = next((p for p in table["order"] if table["players"][p]["alive"] and p != uid), None)
        if next_player:
            await roulette_turn(cid, next_player, state)
        else:
            await roulette_end(cid, state)
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔫 Стрелять!", callback_data=f"roulette_shoot_{uid}_{cid}")]
    ])
    
    await bot.send_message(
        uid,
        f" <b>Ваш ход!</b>\n\n"
        f"Нажмите кнопку, чтобы выстрелить в себя.\n"
        f"Шанс выжить: 83%\n\n"
        f"💰 Банк: {fmt_money(table['bank'])}",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data.startswith("roulette_shoot_"))
async def roulette_shoot(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split("_")
    uid = int(parts[2])
    cid = int(parts[3])
    
    if cid not in ROULETTE_TABLES:
        return await cb.answer("Игра завершена!", show_alert=True)
    
    table = ROULETTE_TABLES[cid]
    if uid != cb.from_user.id:
        return await cb.answer("Не ваш ход!", show_alert=True)
    
    shot = random.random()
    
    if shot < ROULETTE_BULLET_CHANCE:
        table["players"][uid]["alive"] = False
        await cb.message.edit_text(f"💥 <b>ВЫСТРЕЛ!</b>\n\nВы проиграли...", parse_mode="HTML")
        await bot.send_message(cid, f"💀 {table['players'][uid]['name']} проиграл!", parse_mode="HTML")
    else:
        await cb.message.edit_text(f"✅ <b>Щёлк...</b>\n\nВы выжили!", parse_mode="HTML")
        await bot.send_message(cid, f"✅ {table['players'][uid]['name']} выжил!", parse_mode="HTML")
    
    new_achs = await check_achievements(cid, uid)
    await notify_achievements(cid, uid, new_achs)
    
    alive_players = [p for p in table["order"] if table["players"][p]["alive"]]
    if len(alive_players) == 1:
        await roulette_end(cid, state)
    else:
        next_player = next((p for p in table["order"] if table["players"][p]["alive"] and p != uid), alive_players[0])
        await roulette_turn(cid, next_player, state)

async def roulette_end(cid, state):
    table = ROULETTE_TABLES[cid]
    winners = [p for p in table["order"] if table["players"][p]["alive"]]
    
    if len(winners) == 1:
        winner_uid = winners[0]
        winner_share = table["bank"]
        await update_balance(cid, winner_uid, winner_share)
        
        await bot.send_message(
            cid,
            f"🏆 <b>ПОБЕДИТЕЛЬ!</b>\n\n"
            f"👤 {table['players'][winner_uid]['name']}\n"
            f"💰 Забирает: <b>{fmt_money(winner_share)}</b>\n\n"
            f"🔫 Игра окончена!",
            parse_mode="HTML"
        )
    else:
        for uid in winners:
            await update_balance(cid, uid, table["players"][uid]["bet"])
        
        await bot.send_message(
            cid,
            f" <b>НИЧЬЯ!</b>\n\n"
            f"Выжившие: {', '.join([table['players'][u]['name'] for u in winners])}\n"
            f"Ставки возвращены.\n\n"
            f" Игра окончена!",
            parse_mode="HTML"
        )
    
    del ROULETTE_TABLES[cid]
    await state.clear()

# ==================== БЛЭКДЖЕК ====================
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
        f"👤 {m.from_user.first_name}\n"
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
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"bj_cancel_{cid}")]
    ])
    try:
        await cb.message.edit_text(f"🎩 <b>Игроки ({len(t['players'])}/{BJ_MAX_PLAYERS}):\n{pl}\n\n⏳ Ждём...</b>", reply_markup=kb, parse_mode="HTML")
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
        await cb.message.edit_text(f"❌ <b>Отменена!</b>\n\n👤 {cb.from_user.first_name}\n\n💰 Возврат:\n{rt}", parse_mode="HTML")
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
    await bot.send_message(cid, f"🎩 <b>Карты розданы!</b>\n\n🤖 Мои: {show_cards(t['dealer'], True)}\n\n{pi}\n\n🎮 Ходит: <b>{t['players'][t['order'][0]]['name']}</b>", parse_mode="HTML")
    await state.set_state(BlackjackStates.playing)
    await blackjack_player_turn(cid, t["order"][0], state)

async def blackjack_player_turn(cid, uid, state):
    t = bj_tables[cid]
    p = t["players"][uid]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Ещё", callback_data=f"hit_{uid}_{cid}"), InlineKeyboardButton(text="✋ Хватит", callback_data=f"stand_{uid}_{cid}")]
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
        await cb.message.edit_text(f" Взял карту!\n\n🃏 +{c[0]}{c[1]}\n📊 {show_cards(p['cards'])}\n🔢 Сумма: <b>{sc}</b>", parse_mode="HTML")
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
                [InlineKeyboardButton(text=" Ещё", callback_data=f"hit_{uid}_{cid}"), InlineKeyboardButton(text=" Хватит", callback_data=f"stand_{uid}_{cid}")]
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
    await bot.send_message(cid, f" <b>Ход Игорёчка!</b>\n\n🤖 Мои: {show_cards(t['dealer'])}", parse_mode="HTML")
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
        fn = " Поздравляем!"
    elif any("проигрыш" in r for r in res):
        fn = "🎩 Забирает ставки!"
    else:
        fn = "🤝 Ничья!"
    await bot.send_message(cid, f"🎩 <b>{fn}</b>\n\n🤖 Карты: {show_cards(t['dealer'])} ({ds})\n\n Результаты:\n" + "\n".join(res), parse_mode="HTML")
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
    asyncio.create_task(stock_market_loop())
    asyncio.create_task(stock_dividend_loop())
    await dp.start_polling(bot, timeout=30, drop_pending_updates=True, allowed_updates=["message", "callback_query", "my_chat_member"])

if __name__ == "__main__":
    asyncio.run(main())
