import asyncio
import logging
import random
import time
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncpg
from aiohttp import web

API_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]
DATABASE_URL = os.environ.get("DATABASE_URL", "")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "-1002595597314"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
pool = None

exam_sessions = {}
active_cases = {}

# ═══════════════════════════════════════════
# ГОРОДА
# ═══════════════════════════════════════════
CITIES_LIST = [
    {"id": 1, "name": "Москва", "emoji": "🏛️", "work_bonus": 0.20, "desc": "+20% к зарплате", "bonus_type": "work", "bonus_value": 20},
    {"id": 2, "name": "Сарапул", "emoji": "🏘️", "market_discount": 0.15, "desc": "-15% на покупки", "bonus_type": "market", "bonus_value": 15},
    {"id": 3, "name": "Сыктывкар", "emoji": "🌲", "rob_bonus": 0.10, "desc": "+10% к шансу ограбления", "bonus_type": "rob", "bonus_value": 10},
]

# ═══════════════════════════════════════════
# КОНСТАНТЫ
# ═══════════════════════════════════════════
TAX_RATE_PERCENT = 5
CITY_ASSIGNMENT_DAYS = 7
PRESIDENT_DECREE_DURATION = 168
PRIME_MINISTER_DECREE_DURATION = 168
MAYOR_ELECTION_HOURS = 24
MAYOR_ELECTION_DURATION = MAYOR_ELECTION_HOURS * 3600
FEDERAL_ELECTION_DURATION = 86400
PRESIDENT_ELECTION_FEE = 50000
PRESIDENT_VOTE_COST = 1000
PRESIDENT_WIN_BONUS = 50000
PRESIDENT_TERM_DAYS = 90
PRIME_MINISTER_ELECTION_FEE = 40000
PRIME_MINISTER_VOTE_COST = 800
PRIME_MINISTER_WIN_BONUS = 40000
PRIME_MINISTER_TERM_DAYS = 90
CITY_MOVE_COOLDOWN = 86400
CITY_MOVE_COST = 10000
MAYOR_ELECTION_FEE = 30000
MAYOR_TERM_DAYS = 60
MAYOR_VOTE_COST = 500
MAYOR_WIN_BONUS = 30000
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
DICE_MIN_BET = 10
DICE_WIN_PERCENT = 50
DICE_WIN_MULTIPLIER = 2
DEBT_MIN_AMOUNT = 1000
DEBT_MAX_AMOUNT = 10000000
DEBT_MIN_DAYS = 1
DEBT_MAX_DAYS = 7
DEBT_FEE_PERCENT = 5
DEBT_PENALTY_PERCENT = 20
JAIL_TIME_HOURS = 2
JAIL_FINE_PER_HOUR = 50
LAWYER_MIN_FEE = 500
JAIL_FINE_RATE = 0.25
JAIL_DEBT_THRESHOLD = 500
JAIL_DEBT_TIMEOUT = 7200

COURSES = {
    "miner": {"name": "📘 Курс шахтёра", "price": 500, "required_for": "miner", "questions": [
        {"q": "Что нужно надевать в шахте?", "a": ["каска", "шлем", "защита"], "correct": 0},
        {"q": "Сколько тонн весит вагонетка?", "a": ["1", "5", "10"], "correct": 1},
        {"q": "Главный инструмент шахтёра?", "a": ["лопата", "отбойный молоток", "кирка"], "correct": 2}
    ]},
    "coder": {"name": "💻 Курс программирования", "price": 2000, "required_for": "coder", "questions": [
        {"q": "Язык для веб-разработки?", "a": ["Python", "HTML", "C++"], "correct": 1},
        {"q": "Что такое баг?", "a": ["ошибка", "функция", "переменная"], "correct": 0},
        {"q": "Сколько бит в байте?", "a": ["4", "8", "16"], "correct": 1}
    ]},
    "trader": {"name": "📈 Курс трейдинга", "price": 5000, "required_for": "trader", "questions": [
        {"q": "Что такое бычий рынок?", "a": ["рост", "падение", "стабильность"], "correct": 0},
        {"q": "Диверсификация это?", "a": ["риск", "распределение", "прибыль"], "correct": 1},
        {"q": "Ликвидность актива?", "a": ["скорость продажи", "цена", "объём"], "correct": 0}
    ]},
    "lawyer": {"name": "⚖️ Курс адвоката", "price": 3000, "required_for": None, "questions": [
        {"q": "Что такое презумпция невиновности?", "a": ["виновен пока не доказано", "невиновен пока не доказано", "все равны"], "correct": 1},
        {"q": "Срок давности уголовного дела?", "a": ["5 лет", "10 лет", "зависит от тяжести"], "correct": 2},
        {"q": "Кто защищает обвиняемого?", "a": ["прокурор", "адвокат", "судья"], "correct": 1}
    ]},
    "mba": {"name": "🎓 MBA", "price": 15000, "required_for": None, "questions": [
        {"q": "ROI это?", "a": ["возврат инвестиций", "риск", "доход"], "correct": 0},
        {"q": "EBITDA показывает?", "a": ["прибыль", "убыток", "оборот"], "correct": 0},
        {"q": "Стратегия роста?", "a": ["сокращение", "инвестиции", "стагнация"], "correct": 1}
    ]}
}

JOBS = {
    "novice": {"name": "👶 Новичок", "base_pay": 25, "cooldown": 3600},
    "miner": {"name": "⛏️ Шахтёр", "base_pay": 50, "cooldown": 3600},
    "coder": {"name": "💻 Программист", "base_pay": 100, "cooldown": 7200},
    "trader": {"name": "📊 Трейдер", "base_pay": 200, "cooldown": 10800}
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
    "bmw": {"name": "🚗 BMW", "price": 40000},
    "gelik": {"name": "🚙 Гелик", "price": 80000},
    "lambo": {"name": "🏎️ Lamborghini", "price": 200000},
    "rolls": {"name": "🚘 Rolls-Royce", "price": 500000},
    "bentley": {"name": "🚘 Bentley", "price": 800000},
    "ferrari": {"name": "🏎️ Ferrari", "price": 1200000},
    "bugatti": {"name": "🏎️ Bugatti", "price": 2500000},
    "yacht_car": {"name": "🛥️ Яхта на колёсах", "price": 5000000}
}

CRAFT_RECIPES = {
    "diamond": {"name": "💎 Алмаз", "requires": {"📄 Бумага": 10}, "rarity": "rare"},
    "scriptka": {"name": "🎸 Золотая Скрипка", "requires": {"💎 Алмаз": 5}, "rarity": "legendary"}
}

ACHIEVEMENTS = {
    "first_1000": {"name": "💰 Первая тысяча", "desc": "Накопи 1 000 сарапулок", "icon": "💵"},
    "first_10k": {"name": "💰 Десятка", "desc": "Накопи 10 000 сарапулок", "icon": "🥈"},
    "first_100k": {"name": "💰 Сотня", "desc": "Накопи 100 000 сарапулок", "icon": "🥇"},
    "millionaire": {"name": "💰 Миллионер", "desc": "Накопи 1 000 000 сарапулок", "icon": "💎"},
    "first_business": {"name": "🏪 Первый бизнес", "desc": "Купи первый бизнес", "icon": "🏪"},
    "business_empire": {"name": "👑 Бизнес-империя", "desc": "Владей 10 бизнесами", "icon": "👑"},
    "first_car": {"name": "🚗 Первая машина", "desc": "Купи первую машину", "icon": "🚗"},
    "car_collector": {"name": "🏆 Автоколлекционер", "desc": "Купи 5 разных машин", "icon": "🏆"},
    "first_course": {"name": "🎓 Студент", "desc": "Пройди первый курс", "icon": "🎓"},
    "all_courses": {"name": "🎓 Профессор", "desc": "Пройди все курсы", "icon": "🎓"},
    "mba_graduate": {"name": "🎓 MBA", "desc": "Получи степень MBA", "icon": "🎯"},
}

def pluralize(n, forms):
    n = abs(n) % 100
    n1 = n % 10
    if n > 10 and n < 20: return forms[2]
    if n1 > 1 and n1 < 5: return forms[1]
    if n1 == 1: return forms[0]
    return forms[2]

def fmt_money(amount):
    return f"{amount} {pluralize(amount, ['сарапулка', 'сарапулки', 'сарапулок'])}"

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0: return f"{hours} ч {minutes} мин"
    return f"{minutes} мин"

def format_date(timestamp):
    return time.strftime('%d.%m.%Y', time.localtime(timestamp))

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10, command_timeout=30)
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS stock_holdings CASCADE")
        await conn.execute("DROP TABLE IF EXISTS stocks CASCADE")
        await conn.execute("DROP TABLE IF EXISTS marketplace CASCADE")
        await conn.execute("DROP TABLE IF EXISTS robbery CASCADE")
        print("🗑️ Старые таблицы удалены")
        
        await conn.execute("""CREATE TABLE IF NOT EXISTS users (chat_id BIGINT, user_id BIGINT, balance INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS profiles (chat_id BIGINT, user_id BIGINT, job_key TEXT DEFAULT 'novice', level INTEGER DEFAULT 1, last_work_time REAL DEFAULT 0, coffee_level INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        try: await conn.execute("ALTER TABLE profiles ADD COLUMN coffee_level INTEGER DEFAULT 0")
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
        await conn.execute("""CREATE TABLE IF NOT EXISTS achievements (chat_id BIGINT, user_id BIGINT, achievement_id TEXT, unlocked_at REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id, achievement_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS debts (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, lender_id BIGINT NOT NULL, borrower_id BIGINT NOT NULL, amount BIGINT NOT NULL, fee BIGINT NOT NULL, created_at REAL NOT NULL, deadline REAL NOT NULL, status TEXT DEFAULT 'active', reminder_sent BOOLEAN DEFAULT FALSE)""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS state_debts (chat_id BIGINT NOT NULL, user_id BIGINT NOT NULL, amount BIGINT NOT NULL DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS cities (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, bonus_desc TEXT NOT NULL, bonus_type TEXT NOT NULL, bonus_value INTEGER DEFAULT 10)""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS player_cities (chat_id BIGINT NOT NULL, user_id BIGINT NOT NULL, city_id INTEGER NOT NULL, moved_at REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS city_treasury (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, amount BIGINT DEFAULT 0, PRIMARY KEY (chat_id, city_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS mayors (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, user_id BIGINT NOT NULL, elected_at REAL NOT NULL, expires_at REAL NOT NULL, approval_rating INTEGER DEFAULT 50, PRIMARY KEY (chat_id, city_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS mayor_candidates (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, user_id BIGINT NOT NULL, votes BIGINT DEFAULT 0, election_id TEXT NOT NULL, status TEXT DEFAULT 'active', UNIQUE(chat_id, city_id, user_id, election_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS mayor_votes (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, voter_id BIGINT NOT NULL, candidate_id BIGINT NOT NULL, election_id TEXT NOT NULL, PRIMARY KEY (chat_id, city_id, voter_id, election_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS city_decrees (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, mayor_id BIGINT NOT NULL, decree_type TEXT NOT NULL, active_until REAL NOT NULL)""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS state_treasury (chat_id BIGINT PRIMARY KEY, amount BIGINT DEFAULT 0)""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS federal_roles (chat_id BIGINT NOT NULL, role TEXT NOT NULL, user_id BIGINT NOT NULL, elected_at REAL NOT NULL, expires_at REAL NOT NULL, approval_rating INTEGER DEFAULT 50, PRIMARY KEY (chat_id, role))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS federal_candidates (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, role TEXT NOT NULL, user_id BIGINT NOT NULL, votes BIGINT DEFAULT 0, election_id TEXT NOT NULL, UNIQUE (chat_id, role, user_id, election_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS federal_votes (chat_id BIGINT NOT NULL, role TEXT NOT NULL, voter_id BIGINT NOT NULL, candidate_id BIGINT NOT NULL, election_id TEXT NOT NULL, PRIMARY KEY (chat_id, role, voter_id, election_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS federal_elections_start (chat_id BIGINT NOT NULL, role TEXT NOT NULL, election_id TEXT NOT NULL, started_at REAL NOT NULL, PRIMARY KEY (chat_id, role, election_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS mayor_elections_start (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, election_id TEXT NOT NULL, started_at REAL NOT NULL, PRIMARY KEY (chat_id, city_id, election_id))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS federal_decrees (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, role TEXT NOT NULL, decree_type TEXT NOT NULL, active_until REAL NOT NULL, UNIQUE (chat_id, role, decree_type))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS active_federal_decrees (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, decree_type TEXT NOT NULL, issued_by BIGINT NOT NULL, issued_at REAL NOT NULL, expires_at REAL NOT NULL, UNIQUE (chat_id, decree_type))""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS mayor_reports (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, mayor_id BIGINT NOT NULL, budget_allocated BIGINT DEFAULT 0, budget_spent BIGINT DEFAULT 0, report_deadline REAL NOT NULL, status TEXT DEFAULT 'pending', created_at REAL NOT NULL)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS impeachment_votes (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            role TEXT NOT NULL,
            voter_id BIGINT NOT NULL,
            voted_at REAL NOT NULL,
            UNIQUE(chat_id, role, voter_id)
            )
        """)
        print("✅ Таблица impeachment_votes создана")
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
            if now - timestamp > 600: to_delete.append(case_id)
        except: to_delete.append(case_id)
    for case_id in to_delete:
        parts = case_id.split("_")
        cid = int(parts[0])
        rid = int(parts[1])
        await send_to_jail(cid, rid, JAIL_TIME_HOURS)
        try: await bot.send_message(cid, f"⏳ Время вышло!", parse_mode="HTML")
        except: pass
        del active_cases[case_id]

async def auto_cleanup_timer(case_id):
    await asyncio.sleep(600)
    if case_id in active_cases: await cleanup_old_cases()

async def arrest_player(cid, uid):
    arrested = []
    total_value = 0
    bank_data = await get_bank(cid, uid)
    if bank_data['deposit'] > 0:
        total_value += bank_data['deposit']
        arrested.append(f"💰 Банк: {fmt_money(bank_data['deposit'])}")
        async with pool.acquire() as conn:
            await conn.execute("UPDATE bank SET deposit=0, last_interest_time=$1 WHERE chat_id=$2 AND user_id=$3", time.time(), cid, uid)
    async with pool.acquire() as conn:
        cars = await conn.fetch("SELECT car_key FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if cars:
            car_names = []
            for car in cars:
                car_key = car['car_key']
                if car_key in CARS: total_value += CARS[car_key]['price']
                car_names.append(CARS.get(car_key, {}).get('name', car_key))
            arrested.append(f"🚗 Машины: {', '.join(car_names)}")
            await conn.execute("DELETE FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
    async with pool.acquire() as conn:
        businesses = await conn.fetch("SELECT business_name, income FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if businesses:
            biz_names = []
            for biz in businesses:
                biz_price = 0
                for k, v in MARKET.items():
                    if v['type'] == 'business' and v['income'] == biz['income']:
                        biz_price = v['price']
                        break
                if biz_price == 0: biz_price = biz['income'] * 6
                total_value += biz_price
                biz_names.append(biz['business_name'])
            arrested.append(f"🏢 Бизнесы: {', '.join(biz_names)}")
            await conn.execute("DELETE FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
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
    p = await get_profile(cid, uid)
    if p['level'] > 1:
        profession_value = (p['level'] - 1) * 5000
        total_value += profession_value
        arrested.append(f"💼 Профессия сброшена (был Ур.{p['level']})")
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET job_key='novice', level=1 WHERE chat_id=$1 AND user_id=$2", cid, uid)
    return arrested, total_value

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
        try: await bot.send_message(cid, f"🏆 <b>Новые достижения!</b>\n\n{ach_text}", parse_mode="HTML")
        except: pass

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
                tickets = await conn.fetch("SELECT id, user_id FROM lottery_tickets WHERE chat_id=$1 AND buy_time <=$2", cid, now - LOTTERY_INTERVAL)
                if len(tickets) >= 2:
                    winner = random.choice(tickets)
                    bank = len(tickets) * LOTTERY_PRICE
                    await update_balance(cid, winner['user_id'], bank)
                    wname = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, winner['user_id']) or f"User{winner['user_id']}"
                    await conn.execute("DELETE FROM lottery_tickets WHERE chat_id=$1", cid)
                    try: await bot.send_message(cid, f"🎉 <b>АВТО-РОЗЫГРЫШ!</b>\n\n🏆 {wname}\n💰 {fmt_money(bank)}", parse_mode="HTML")
                    except: pass

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
                    arrested, confiscated_value = await arrest_player(cid, uid)
                    remaining_debt = total_debt - confiscated_value
                    if remaining_debt > 0:
                        user = await get_user(cid, uid)
                        new_balance = user['balance'] - remaining_debt
                        async with pool.acquire() as conn2:
                            await conn2.execute("UPDATE users SET balance=$1 WHERE chat_id=$2 AND user_id=$3", new_balance, cid, uid)
                    await clear_loan(cid, uid)
                    msg = f"🚔 <b>АРЕСТ ИМУЩЕСТВА!</b>\n\n💰 Долг: <b>{fmt_money(total_debt)}</b>\n📦 Конфисковано на: <b>{fmt_money(confiscated_value)}</b>\n\n"
                    msg += "<b>Конфисковано:</b>\n" + "\n".join([f"• {item}" for item in arrested])
                    if remaining_debt > 0: msg += f"\n\n⛔ Остаток долга: <b>{fmt_money(remaining_debt)}</b>"
                    try: await bot.send_message(cid, msg, parse_mode="HTML")
                    except: pass
                else:
                    daily_interest = int(loan['amount'] * CREDIT_DAILY_RATE)
                    await update_loan(cid, uid, loan['amount'], loan['interest'] + daily_interest, loan['taken_at'], loan['due_date'])

async def jail_fine_check_loop():
    print("⚖️ Цикл проверки штрафов запущен")
    while True:
        await asyncio.sleep(300)
        async with pool.acquire() as conn:
            fines = await conn.fetch("SELECT * FROM jail_fines WHERE paid=FALSE AND fine_amount > 0")
            for fine in fines:
                cid, uid = fine['chat_id'], fine['user_id']
                in_jail = await is_in_jail(cid, uid)
                if in_jail: continue
                user = await get_user(cid, uid)
                bank = await get_bank(cid, uid)
                total_available = user['balance'] + bank['deposit']
                if total_available >= fine['fine_amount']:
                    paid_from_balance = min(fine['fine_amount'], user['balance'])
                    remaining = fine['fine_amount'] - paid_from_balance
                    if paid_from_balance > 0: await update_balance(cid, uid, -paid_from_balance)
                    if remaining > 0 and bank['deposit'] > 0: await update_bank(cid, uid, -min(remaining, bank['deposit']))
                    await conn.execute("UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2", cid, uid)
                    continue
                if fine['debt_time'] > 0 and time.time() - fine['debt_time'] > JAIL_DEBT_TIMEOUT:
                    if user['balance'] < JAIL_DEBT_THRESHOLD:
                        arrested, _ = await arrest_player(cid, uid)
                        await conn.execute("UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2", cid, uid)
                        username = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, uid) or f"User{uid}"
                        try:
                            msg = f"🚔 <b>АРЕСТ ЗА НЕОПЛАЧЕННЫЙ ШТРАФ!</b>\n\n👤 {username}\n\n<b>Конфисковано:</b>\n" + "\n".join([f"• {i}" for i in arrested])
                            await bot.send_message(cid, msg, parse_mode="HTML")
                        except: pass

async def check_expired_debts_loop():
    print("🕵️ Фоновая проверка долгов запущена")
    while True:
        await asyncio.sleep(3600)
        try:
            async with pool.acquire() as conn:
                debts = await conn.fetch("SELECT * FROM debts WHERE status='active' AND deadline < $1", time.time())
                for debt in debts:
                    await run_collectors(debt)
        except Exception as e:
            print(f"Ошибка проверки долгов: {e}")

async def run_collectors(debt):
    cid = debt['chat_id']
    borrower_id = debt['borrower_id']
    lender_id = debt['lender_id']
    debt_amount = debt['amount']
    penalty = int(debt_amount * DEBT_PENALTY_PERCENT / 100)
    total_debt = debt_amount + penalty
    collected = 0
    seized_items = []
    async with pool.acquire() as conn:
        cars = await conn.fetch("SELECT id, car_name FROM garage WHERE chat_id=$1 AND user_id=$2", cid, borrower_id)
        for car in cars:
            if collected >= total_debt: break
            car_price = 0
            for key, data in CARS.items():
                if data['name'] in car['car_name'] or car['car_name'] in data['name']:
                    car_price = data['price']
                    break
            if car_price > 0:
                await conn.execute("DELETE FROM garage WHERE id=$1", car['id'])
                collected += car_price
                seized_items.append(f"🚗 {car['car_name']} ({fmt_money(car_price)})")
        if collected < total_debt:
            businesses = await conn.fetch("SELECT id, business_name FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, borrower_id)
            for biz in businesses:
                if collected >= total_debt: break
                biz_price = 0
                for key, data in MARKET.items():
                    if data['name'] in biz['business_name'] or biz['business_name'] in data['name']:
                        biz_price = data['price']
                        break
                if biz_price == 0: biz_price = 50000
                if biz_price > 0:
                    await conn.execute("DELETE FROM businesses WHERE id=$1", biz['id'])
                    collected += biz_price
                    seized_items.append(f"🏪 {biz['business_name']} ({fmt_money(biz_price)})")
        user = await get_user(cid, borrower_id)
        if collected < total_debt and user['balance'] > 0:
            take = min(user['balance'], total_debt - collected)
            await update_balance(cid, borrower_id, -take)
            collected += take
            seized_items.append(f"💰 Баланс: {fmt_money(take)}")
        remaining = total_debt - collected
        if remaining > 0:
            await conn.execute("INSERT INTO state_debts VALUES ($1,$2,$3) ON CONFLICT (chat_id, user_id) DO UPDATE SET amount=state_debts.amount+$3", cid, borrower_id, remaining)
            await update_balance(cid, borrower_id, -remaining)
        await conn.execute("UPDATE debts SET status='collected' WHERE id=$1", debt['id'])
        await update_balance(cid, lender_id, debt_amount)
    try: b_name = (await bot.get_chat_member(cid, borrower_id)).user.full_name
    except: b_name = "Должник"
    try: l_name = (await bot.get_chat_member(cid, lender_id)).user.full_name
    except: l_name = "Кредитор"
    seized_text = "\n".join(seized_items) if seized_items else "Ничего не найдено"
    await bot.send_message(cid, f"🚨 <b>КОЛЛЕКТОРЫ ЯВИЛИСЬ!</b>\n\n👤 {b_name}\n📜 Долг: {fmt_money(debt_amount)} + {fmt_money(penalty)} штраф\n\n🗑️ <b>Изъято:</b>\n{seized_text}", parse_mode="HTML")
    await bot.send_message(cid, f"✅ <b>ДОЛГ ВОЗВРАЩЁН</b>\n\n👤 От {b_name}\n💰 Получено: {fmt_money(debt_amount)}", parse_mode="HTML")

async def check_all_elections_and_terms():
    print("🏛️ Единая проверка сроков и выборов запущена")
    while True:
        await asyncio.sleep(3600)
        try:
            async with pool.acquire() as conn:
                now = time.time()
                expired_mayors = await conn.fetch("SELECT chat_id, city_id FROM mayors WHERE expires_at <= $1", now)
                for mayor_data in expired_mayors:
                    cid = mayor_data['chat_id']
                    city_id = mayor_data['city_id']
                    await conn.execute("DELETE FROM mayors WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                    await conn.execute("DELETE FROM mayor_elections_start WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                    city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
                    if city:
                        try: await bot.send_message(cid, f"🏛️ <b>СРОК МЭРА В {city['emoji']} {city['name']} ИСТЁК!</b>\n\n⏳ Открыто окно для новых выборов на 24 часа.\nИспользуйте /mayor_nominate", parse_mode="HTML")
                        except: pass
                expired_mayor_elections = await conn.fetch("SELECT chat_id, city_id, election_id FROM mayor_elections_start WHERE started_at < $1", now - MAYOR_ELECTION_DURATION)
                for elec in expired_mayor_elections:
                    cid = elec['chat_id']
                    city_id = elec['city_id']
                    result = await finalize_mayor_election(cid, city_id)
                    await conn.execute("DELETE FROM mayor_elections_start WHERE chat_id=$1 AND city_id=$2 AND election_id=$3", cid, city_id, elec['election_id'])
                    city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
                    if city:
                        if result:
                            try: winner_name = (await bot.get_chat_member(cid, result['user_id'])).user.full_name
                            except: winner_name = f"User{result['user_id']}"
                            msg = f"🎉 <b>ВЫБОРЫ МЭРА В {city['emoji']} {city['name']} ЗАВЕРШЕНЫ!</b>\n\n👤 Победитель: {winner_name}\n🗳️ Голосов: {result['votes']}\n⏰ Срок: {MAYOR_TERM_DAYS} дней"
                        else: msg = f"🏛️ <b>ВЫБОРЫ МЭРА В {city['emoji']} {city['name']} ЗАВЕРШЕНЫ</b>\n\n❌ Никто не баллотировался."
                        try: await bot.send_message(cid, msg, parse_mode="HTML")
                        except: pass
                expired_federal = await conn.fetch("SELECT chat_id, role FROM federal_roles WHERE expires_at <= $1", now)
                for role_data in expired_federal:
                    cid = role_data['chat_id']
                    role = role_data['role']
                    await conn.execute("DELETE FROM federal_roles WHERE chat_id=$1 AND role=$2", cid, role)
                    await conn.execute("DELETE FROM federal_elections_start WHERE chat_id=$1 AND role=$2", cid, role)
                    role_name = "Президент" if role == 'president' else "Премьер-министр"
                    emoji = "🏛️" if role == 'president' else "💼"
                    try: await bot.send_message(cid, f"{emoji} <b>СРОК ПОЛНОМОЧИЙ {role_name.upper()} ИСТЁК!</b>\n\n⏳ Открыто окно для новых выборов на 24 часа.\nИспользуйте /{'president' if role=='president' else 'prime'}_nominate", parse_mode="HTML")
                    except: pass
                expired_federal_elections = await conn.fetch("SELECT chat_id, role, election_id FROM federal_elections_start WHERE started_at < $1", now - FEDERAL_ELECTION_DURATION)
                for elec in expired_federal_elections:
                    cid = elec['chat_id']
                    role = elec['role']
                    result = await finalize_federal_election(cid, role)
                    await conn.execute("DELETE FROM federal_elections_start WHERE chat_id=$1 AND role=$2 AND election_id=$3", cid, role, elec['election_id'])
                    role_name = "Президент" if role == 'president' else "Премьер-министр"
                    emoji = "🏛️" if role == 'president' else "💼"
                    if result:
                        try: winner_name = (await bot.get_chat_member(cid, result['user_id'])).user.full_name
                        except: winner_name = f"User{result['user_id']}"
                        msg = f"{emoji} <b>ВЫБОРЫ {role_name.upper()} ЗАВЕРШЕНЫ!</b>\n\n👤 Победитель: {winner_name}\n🗳️ Голосов: {result['votes']}\n⏰ Срок: {PRESIDENT_TERM_DAYS} дней"
                    else: msg = f"{emoji} <b>ВЫБОРЫ {role_name.upper()} ЗАВЕРШЕНЫ</b>\n\n❌ Никто не баллотировался."
                    try: await bot.send_message(cid, msg, parse_mode="HTML")
                    except: pass
        except Exception as e:
            print(f"Ошибка проверки выборов и сроков: {e}")

@dp.message(Command("start"))
async def cmd_start(m: Message):
    await save_username(m.chat.id, m.from_user.id, m.from_user.full_name)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Финансы", callback_data="menu_finance"), 
         InlineKeyboardButton(text="💼 Работа", callback_data="menu_work")],
        [InlineKeyboardButton(text="🏪 Бизнес", callback_data="menu_business"), 
         InlineKeyboardButton(text="🚗 Авто", callback_data="menu_cars")],
        [InlineKeyboardButton(text="🎓 Образование", callback_data="menu_edu"), 
         InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        [InlineKeyboardButton(text="🏛️ Политика", callback_data="menu_politics"), 
         InlineKeyboardButton(text="📊 Инфо", callback_data="menu_info")],
    ])
    await m.answer(
        f"🎩 <b>Добро пожаловать в мир Сарапулок!</b>\n\n"
        f"👤 {m.from_user.full_name}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Финансы:</b>\n"
        f"  /balance — мой баланс\n"
        f"  /pay сумма — перевод (ответ)\n"
        f"  /bank — банковский счёт\n"
        f"  /deposit сумма — вклад\n"
        f"  /withdraw сумма — снять\n"
        f"  /credit сумма — взять кредит\n"
        f"  /debt — долг\n"
        f"  /repay сумма — погасить\n\n"
        f"💼 <b>Работа:</b>\n"
        f"  /work — работать\n"
        f"  /jobs — вакансии\n"
        f"  /job ключ — сменить работу\n"
        f"  /shop — магазин улучшений\n\n"
        f"🔫 <b>Криминал:</b>\n"
        f"  /rob — ограбить (ответ)\n"
        f"  /hire_lawyer @user сумма\n"
        f"  /court — суд\n"
        f"  /jail — статус тюрьмы\n"
        f"  /jail_pay — оплатить штраф\n\n"
        f"🎮 <b>Игры:</b>\n"
        f"  🎲 /dice сумма — кости\n"
        f"  🎟️ /buy_ticket — лотерея\n"
        f"  🎁 /daily — бонус\n\n"
        f"🏪 <b>Бизнес:</b>\n"
        f"  /market — рынок\n"
        f"  /buy_market ключ — купить\n"
        f"  /collect — прибыль\n\n"
        f"🏙️ <b>Система городов:</b>\n"
        f"  /city list — список всех городов\n"
        f"  /city choose [город] — выбрать город\n"
        f"  /city move [город] — сменить город (1 день, 10к)\n"
        f"  /city info — информация о твоём городе\n"
        f"  /city residents — жители города\n\n"
        f"🏛️ <b>Мэр и город:</b>\n"
        f"  /mayor_nominate — выдвинуться в мэры (30к)\n"
        f"  /mayor_vote — проголосовать за мэра (500)\n"
        f"  /mayor_decree — указы мэра (только для мэра)\n"
        f"  /mayor_report — отчёт мэра\n"
        f"  /mayor_finalize — завершить выборы\n"
        f"  /city_decrees — активные указы города\n\n"
        f"🇷🇺 <b>Президент (90 дней):</b>\n"
        f"  /president_nominate — выдвинуться (50к)\n"
        f"  /president_vote — проголосовать (1000)\n"
        f"  /president_decree — указы Президента\n"
        f"  /president_decrees — активные указы\n"
        f"  /president_finalize — завершить выборы\n"
        f"  /president_check_mayor — проверить мэра\n\n"
        f"💼 <b>Премьер (90 дней):</b>\n"
        f"  /prime_nominate — выдвинуться (40к)\n"
        f"  /prime_vote — проголосовать (800)\n"
        f"  /prime_decree — указы Премьера\n"
        f"  /prime_decrees — активные указы\n"
        f"  /prime_finalize — завершить выборы\n\n"
        f"⚖️ <b>Импичмент:</b>\n"
        f"  /impeach president — против Президента\n"
        f"  /impeach prime — против Премьера\n\n"
        f"🚗 <b>Авто:</b>\n"
        f"  /cars — автосалон\n"
        f"  /buycar ключ — купить\n"
        f"  /mycar — мои машины\n\n"
        f"🎓 <b>Образование:</b>\n"
        f"  /education — курсы\n"
        f"  /buy_course ключ — купить\n\n"
        f"💳 <b>Кредиты:</b>\n"
        f"  /credit сумма — взять\n"
        f"  /debt — долг\n"
        f"  /repay сумма — погасить\n"
        f"  /repay_all — всё погасить\n\n"
        f"🛒 <b>Магазин:</b>\n"
        f"  /shop — улучшения\n"
        f"  /buy ключ — купить\n\n"
        f"🎒 <b>Инвентарь:</b>\n"
        f"  /inv — инвентарь\n"
        f"  /craft — крафт\n"
        f"  /craft_item ключ\n"
        f"  /trade @user предмет кол-во\n\n"
        f"💳 <b>ДОЛГИ:</b>\n"
        f"  /debt_give — Дать в долг\n"
        f"  /debt_return — Вернуть долг\n"
        f"  /debt_list — Мои долги\n\n"
        f"📊 <b>Инфо:</b>\n"
        f"  /info — карточка\n"
        f"  /rating — рейтинг\n"
        f"  /achievements — награды\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data.startswith("menu_"))
async def callback_menu(callback: CallbackQuery):
    uid = callback.from_user.id
    cid = callback.message.chat.id
    action = callback.data.replace("menu_", "")
    if action == "finance":
        u = await get_user(cid, uid)
        bd = await get_bank(cid, uid)
        text = f"💰 <b>ФИНАНСЫ</b>\n\n💵 Баланс: <b>{fmt_money(u['balance'])}</b>\n🏦 Банк: <b>{fmt_money(bd['deposit'])}</b>\n\n/balance\n/bank\n/deposit сумма\n/withdraw сумма\n/pay сумма\n/credit сумма\n/debt\n/repay сумма"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "work":
        p = await get_profile(cid, uid)
        j = JOBS[p['job_key']]
        text = f"💼 <b>РАБОТА</b>\n\n🔹 {j['name']} (Ур.{p['level']})\n💰 {fmt_money(j['base_pay'] * p['level'])}/ч\n\n/work\n/jobs\n/job ключ\n/shop"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "business":
        async with pool.acquire() as conn:
            bc = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
        text = f"🏪 <b>БИЗНЕС</b>\n\n🏢 У вас: <b>{bc}</b>\n\n/market\n/buy_market ключ\n/collect"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "cars":
        c = await get_car(cid, uid)
        text = f"🚗 <b>АВТОСАЛОН</b>\n\n🅿️ {c or 'нет'}\n\n/cars\n/buycar ключ\n/mycar"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "edu":
        edu = await get_education(cid, uid)
        cc = len(edu['completed_courses']) + (1 if edu['has_mba'] else 0)
        text = f"🎓 <b>ОБРАЗОВАНИЕ</b>\n\n📚 Пройдено: <b>{cc}</b>\n\n/education\n/buy_course ключ"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "games":
        text = f"🎮 <b>ИГРЫ</b>\n\n🎲 /dice сумма\n🎟️ /buy_ticket\n🎁 /daily"
        await callback.message.edit_text(text, parse_mode="HTML")

    elif action == "info":
        u = await get_user(cid, uid)
        p = await get_profile(cid, uid)
        in_jail = await is_in_jail(cid, uid)
        jail_text = "\n🔒 <b>В ТЮРЬМЕ!</b>" if in_jail else ""
        debt_text = f"\n⛔ ДОЛГ: {fmt_money(abs(u['balance']))}" if u['balance'] < 0 else ""
        text = f"📊 <b>КАРТОЧКА</b>\n\n👤 {callback.from_user.full_name}\n💰 {fmt_money(u['balance'])}\n💼 {JOBS[p['job_key']]['name']} (Ур.{p['level']}){jail_text}{debt_text}\n\n/info\n/rating\n/achievements"
        await callback.message.edit_text(text, parse_mode="HTML")
    
    elif action == "politics":
        # Получаем текущего Президента
        president = await get_federal_role(cid, 'president')
        president_text = "👤 ВАКАНТНО\n⏳ Выборы не проведены"
        if president:
            try:
                p_name = (await bot.get_chat_member(cid, president['user_id'])).user.full_name
            except:
                p_name = f"User{president['user_id']}"
            days_left = int((president['expires_at'] - time.time()) / 86400)
            president_text = f"👤 {p_name}\n📊 Рейтинг: {president['approval_rating']}%\n⏳ Осталось: {days_left} дн."
        
        # Получаем текущего Премьера
        prime = await get_federal_role(cid, 'prime_minister')
        prime_text = "👤 ВАКАНТНО\n⏳ Выборы не проведены"
        if prime:
            try:
                pr_name = (await bot.get_chat_member(cid, prime['user_id'])).user.full_name
            except:
                pr_name = f"User{prime['user_id']}"
            days_left = int((prime['expires_at'] - time.time()) / 86400)
            prime_text = f"👤 {pr_name}\n📊 Рейтинг: {prime['approval_rating']}%\n⏳ Осталось: {days_left} дн."
        
        # Федеральная казна
        state_treasury = await get_state_treasury(cid)
        
        # Мэры городов
        mayors_text = ""
        for city in CITIES_LIST:
            mayor = await get_mayor(cid, city['id'])
            city_treasury = await get_city_treasury(cid, city['id'])
            if mayor:
                try:
                    m_name = (await bot.get_chat_member(cid, mayor['user_id'])).user.full_name
                except:
                    m_name = f"User{mayor['user_id']}"
                days_left = int((mayor['expires_at'] - time.time()) / 86400)
                mayors_text += f"{city['emoji']} <b>{city['name']}</b>\n"
                mayors_text += f"   👤 Мэр: {m_name}\n"
                mayors_text += f"   📊 Рейтинг: {mayor['approval_rating']}%\n"
                mayors_text += f"   ⏳ Осталось: {days_left} дн.\n"
                mayors_text += f"   💰 Казна: {fmt_money(city_treasury)}\n\n"
            else:
                mayors_text += f"{city['emoji']} <b>{city['name']}</b>\n"
                mayors_text += f"   👤 Мэр: ВАКАНТНО\n"
                mayors_text += f"   💰 Казна: {fmt_money(city_treasury)}\n\n"
        
        text = (
            f"🏛️ <b>ПОЛИТИЧЕСКАЯ СИСТЕМА</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🇷🇺 <b>ПРЕЗИДЕНТ</b> (90 дней)\n"
            f"{president_text}\n\n"
            f"💼 <b>ПРЕМЬЕР-МИНИСТР</b> (90 дней)\n"
            f"{prime_text}\n\n"
            f"🏛️ <b>ФЕДЕРАЛЬНАЯ КАЗНА</b>\n"
            f"💰 {fmt_money(state_treasury)}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏙️ <b>МЭРЫ ГОРОДОВ</b>\n\n"
            f"{mayors_text}"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <b>Команды:</b>\n"
            f"/city list — города\n"
            f"/mayor_nominate — в мэры (30к)\n"
            f"/president_nominate — в Президенты (50к)\n"
            f"/prime_nominate — в Премьеры (40к)\n"
            f"/impeach president — импичмент Президента\n"
            f"/impeach prime — импичмент Премьера"
        )
        await callback.message.edit_text(text, parse_mode="HTML")
    
    await callback.answer()

@dp.message(Command("balance"))
async def cmd_balance(m: Message):
    await save_username(m.chat.id, m.from_user.id, m.from_user.full_name)
    u = await get_user(m.chat.id, m.from_user.id)
    c = await get_car(m.chat.id, m.from_user.id)
    bd = await get_bank(m.chat.id, m.from_user.id)
    in_jail = await is_in_jail(m.chat.id, m.from_user.id)
    jail_text = "\n🔒 <b>В ТЮРЬМЕ!</b>" if in_jail else ""
    debt_text = f"\n⛔ <b>ДОЛГ: {fmt_money(abs(u['balance']))}</b>" if u['balance'] < 0 else ""
    await m.answer(f"💰 <b>Баланс:</b> {fmt_money(u['balance'])}\n🏦 <b>Банк:</b> {fmt_money(bd['deposit'])}\n🚗 <b>Машины:</b> {c or 'нет'}{jail_text}{debt_text}", parse_mode="HTML")
    new_achs = await check_achievements(m.chat.id, m.from_user.id)
    await notify_achievements(m.chat.id, m.from_user.id, new_achs)

@dp.message(Command("work"))
async def cmd_work(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        info = await get_jail_info(cid, uid)
        return await m.answer(f"🔒 Вы в тюрьме! Осталось: {format_time(int(info['release_time'] - time.time()))}")
    user = await get_user(cid, uid)
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
        msg = f"🚔 <b>АРЕСТ ИМУЩЕСТВА!</b>\n\n💰 Долг: <b>{fmt_money(total_debt)}</b>\n📦 Конфисковано: <b>{fmt_money(confiscated_value)}</b>\n\n"
        msg += "<b>Конфисковано:</b>\n" + "\n".join([f"• {item}" for item in arrested])
        if remaining_debt > 0: msg += f"\n\n⛔ Остаток: <b>{fmt_money(remaining_debt)}</b>"
        try: await bot.send_message(cid, msg, parse_mode="HTML")
        except: pass
        return await m.answer(f"⛔ Имущество конфисковано!", parse_mode="HTML")
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
    work_bonus_multiplier = 1.0
    player_city = await get_player_city(cid, uid)
    if player_city:
        city = next((c for c in CITIES_LIST if c['id'] == player_city['id']), None)
        if city and city.get('work_bonus'): work_bonus_multiplier += city['work_bonus']
        work_decree = await get_active_decree(cid, player_city['id'], 'work_bonus')
        if work_decree: work_bonus_multiplier += 0.20
        subsidy_decree = await get_active_federal_decree(cid, 'prime_minister', 'subsidy')
        if subsidy_decree: work_bonus_multiplier += 0.10
    coffee_level = p.get('coffee_level', 0)
    coffee_bonus = 1.0 - (coffee_level * 0.1)
    cd = j['cooldown'] * coffee_bonus
    if ct - p['last_work_time'] < cd:
        rest_seconds = cd - (ct - p['last_work_time'])
        return await m.answer(f"⏳ Отдых {int(rest_seconds // 60)} мин. {int(rest_seconds % 60)} сек.")
    gross_sal = j['base_pay'] * p['level'] + random.randint(0, 5)
    gross_sal = int(gross_sal * work_bonus_multiplier)
    edu = await get_education(cid, uid)
    if edu['has_mba']: gross_sal = int(gross_sal * 1.5)
    net_sal, tax_paid, tax_receiver, tax_rate = await apply_income_tax(cid, uid, gross_sal)
    debt_deduction = 0
    deduction_msg = ""
    if user['balance'] < 0:
        debt_deduction = int(net_sal * 0.5)
        debt_deduction = min(debt_deduction, abs(user['balance']))
        if debt_deduction > 0:
            net_sal -= debt_deduction
            deduction_msg = f"\n💸 Погашено долга: <b>{fmt_money(debt_deduction)}</b>"
    await update_balance(cid, uid, net_sal)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET last_work_time=$1 WHERE chat_id=$2 AND user_id=$3", ct, cid, uid)
    response = f"💼 <b>{j['name']}</b> (Ур.{p['level']}):\n💰 Начислено: <b>{fmt_money(gross_sal)}</b>\n🏛️ Налог ({tax_rate}%): <b>-{fmt_money(tax_paid)}</b> (в {tax_receiver})\n✅ <b>На руки: +{fmt_money(net_sal)}</b>"
    if deduction_msg: response += deduction_msg
    await m.answer(response, parse_mode="HTML")
    new_achs = await check_achievements(cid, uid)
    await notify_achievements(cid, uid, new_achs)

@dp.message(Command("jobs"))
async def cmd_jobs(m: Message):
    t = "💼 <b>Вакансии:</b>\n\n"
    for k, v in JOBS.items():
        t += f"🔹 {v['name']} — {fmt_money(v['base_pay'])}/ч → /job {k}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("job"))
async def cmd_change_job(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2 or args[1] not in JOBS: return await m.answer("/jobs")
    if args[1] != 'novice':
        edu = await get_education(cid, uid)
        if args[1] not in edu['completed_courses']: return await m.answer(f"❌ Нужен курс: /buy_course {args[1]}")
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET job_key=$1 WHERE chat_id=$2 AND user_id=$3", args[1], cid, uid)
    await m.answer(f"✅ Теперь: <b>{JOBS[args[1]]['name']}</b>", parse_mode="HTML")

@dp.message(Command("pay"))
async def cmd_pay(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя переводить!")
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message: return await m.answer("/pay сумма (ответ)")
    try: amt = int(args[1])
    except: return await m.answer("❌ Число!")
    if amt <= 0: return await m.answer("❌ >0!")
    s, r = uid, m.reply_to_message.from_user.id
    if s == r: return await m.answer("❌ Себе нельзя!")
    sb = await get_user(cid, s)
    if sb['balance'] < amt: return await m.answer(f"❌ Мало ({fmt_money(sb['balance'])})")
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
    if user['balance'] < 0: return await m.answer(f"⛔ У вас долг!")
    if not m.reply_to_message: return await m.answer("🔫 Ответьте на жертву!")
    rid, vid = uid, m.reply_to_message.from_user.id
    if rid == vid: return await m.answer("❌ Себя нельзя!")
    if await is_in_jail(cid, vid): return await m.answer("❌ Жертва в тюрьме!")
    async with pool.acquire() as conn:
        lr = await conn.fetchval("SELECT last_robbery FROM robbery WHERE chat_id=$1 AND user_id=$2", cid, rid) or 0
        ct = time.time()
        if ct - lr < ROB_COOLDOWN: return await m.answer(f"⏳ Кулдаун {format_time(ROB_COOLDOWN - (ct - lr))}")
        await conn.execute("INSERT INTO robbery (chat_id, user_id, last_robbery, debt_amount, debt_time) VALUES ($1,$2,$3,0,0) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_robbery=$3", cid, rid, ct)
    vb = await get_user(cid, vid)
    if vb['balance'] < 50: return await m.answer("❌ У жертвы мало денег!")
    rob_success_rate = ROB_SUCCESS_RATE
    player_city = await get_player_city(cid, uid)
    if player_city:
        city = next((c for c in CITIES_LIST if c['id'] == player_city['id']), None)
        if city and city.get('rob_bonus'): rob_success_rate += city['rob_bonus']
    if random.random() < rob_success_rate:
        st = int(vb['balance'] * random.uniform(ROB_MIN_PERCENT, ROB_MAX_PERCENT))
        await update_balance(cid, vid, -st)
        await update_balance(cid, rid, st)
        await m.answer(f"🔫 <b>ОГРАБЛЕНИЕ УСПЕШНО!</b>\n\n{m.from_user.full_name} украл <b>{fmt_money(st)}</b>\nу {m.reply_to_message.from_user.full_name}!", parse_mode="HTML")
    else:
        rb = await get_user(cid, rid)
        bank_data = await get_bank(cid, rid)
        total_wealth = rb['balance'] + bank_data['deposit']
        fine_amount = int(total_wealth * JAIL_FINE_RATE)
        async with pool.acquire() as conn2:
            await conn2.execute("INSERT INTO jail_fines (chat_id, user_id, fine_amount, debt_time, paid) VALUES ($1,$2,$3,$4,FALSE) ON CONFLICT (chat_id, user_id) DO UPDATE SET fine_amount=$3, debt_time=$4, paid=FALSE", cid, rid, fine_amount, time.time())
        lawyers = await find_lawyers_in_chat(cid)
        if not lawyers:
            await send_to_jail(cid, rid, JAIL_TIME_HOURS)
            await m.answer(f"🚔 <b>ПОПАЛСЯ!</b>\n\n🔒 Тюрьма: <b>{JAIL_TIME_HOURS} часа</b>\n\n⚠️ После выхода штраф <b>25%</b> от капитала:\n💰 Ожидаемый штраф: <b>{fmt_money(fine_amount)}</b>\n\n⚖️ Нет адвокатов!", parse_mode="HTML")
        else:
            case_id = f"{cid}_{rid}_{int(time.time())}"
            active_cases[case_id] = {"criminal": rid, "victim": vid, "penalty": fine_amount, "lawyer": None, "paid_fee": 0}
            asyncio.create_task(auto_cleanup_timer(case_id))
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚖️ Нанять адвоката", callback_data=f"find_lawyer_{case_id}")],
                [InlineKeyboardButton(text="🔒 Пойти в тюрьму", callback_data=f"go_jail_{case_id}")]
            ])
            lawyer_list = "\n".join([f"• @{l[1]}" for l in lawyers[:5]])
            await m.answer(f"🚔 <b>ПОПАЛСЯ!</b>\n\n🔒 Тюрьма: <b>{JAIL_TIME_HOURS} часа</b>\n\n⚠️ После выхода штраф <b>25%</b> от капитала:\n💰 Ожидаемый штраф: <b>{fmt_money(fine_amount)}</b>\n\n⚖️ Доступные адвокаты:\n{lawyer_list}\n\nВыберите:\n• Нанять адвоката (шанс 50/50)\n• Пойти в тюрьму", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith("go_jail_"))
async def go_jail_cb(cb: types.CallbackQuery):
    case_id = "_".join(cb.data.split("_")[2:])
    if case_id not in active_cases: return await cb.answer("Дело закрыто!", show_alert=True)
    cid = cb.message.chat.id
    criminal_uid = active_cases[case_id]["criminal"]
    if cb.from_user.id != criminal_uid: return await cb.answer("Не ваше дело!", show_alert=True)
    await send_to_jail(cid, criminal_uid, JAIL_TIME_HOURS)
    del active_cases[case_id]
    await cb.message.edit_text(f"🔒 <b>Вы выбрали тюрьму!</b>\n\n⏰ Срок: {JAIL_TIME_HOURS} часа\n⚠️ После выхода — штраф 25%\n\n/jail_pay", parse_mode="HTML")
    await cb.answer("Вы в тюрьме!")

@dp.callback_query(lambda c: c.data.startswith("find_lawyer_"))
async def find_lawyer_cb(cb: types.CallbackQuery):
    case_id = "_".join(cb.data.split("_")[2:])
    if case_id not in active_cases: return await cb.answer("Дело закрыто!", show_alert=True)
    cid = cb.message.chat.id
    if cb.from_user.id != active_cases[case_id]["criminal"]: return await cb.answer("Не ваше дело!", show_alert=True)
    await cleanup_old_cases()
    await cb.message.edit_text(f"⚖️ <b>Поиск адвоката...</b>\n\nАдвокат должен ответить:\n<b>/hire_lawyer @ваш_ник сумма</b>\n\n⏳ 10 минут, иначе — тюрьма!", parse_mode="HTML")

@dp.message(Command("hire_lawyer"))
async def cmd_hire_lawyer(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 3 or not m.reply_to_message: return await m.answer("⚖️ <b>/hire_lawyer @user сумма</b>", parse_mode="HTML")
    try: fee = int(args[2])
    except: return await m.answer("❌ Число!")
    if fee < LAWYER_MIN_FEE: return await m.answer(f"❌ Минимум: {fmt_money(LAWYER_MIN_FEE)}")
    client_uid = m.reply_to_message.from_user.id
    lawyer_uid = uid
    if lawyer_uid == client_uid: return await m.answer("❌ Нельзя нанять себя!")
    await cleanup_old_cases()
    my_case = None
    for case_id, case in active_cases.items():
        if case["criminal"] == client_uid and case["lawyer"] is None:
            my_case = case_id
            break
    if not my_case: return await m.answer("❌ У клиента нет активных дел!")
    edu = await get_education(cid, lawyer_uid)
    if "lawyer" not in edu['completed_courses']: return await m.answer("❌ У вас нет курса адвоката!")
    client_bal = await get_user(cid, client_uid)
    if client_bal['balance'] < fee: return await m.answer(f"❌ У клиента мало средств")
    await update_balance(cid, client_uid, -fee)
    await update_balance(cid, lawyer_uid, fee)
    active_cases[my_case]["lawyer"] = lawyer_uid
    active_cases[my_case]["paid_fee"] = fee
    client_name = m.reply_to_message.from_user.full_name
    lawyer_name = m.from_user.full_name
    await m.answer(f"⚖️ <b>Вы наняты адвокатом!</b>\n\n👤 Клиент: {client_name}\n💰 Получено: {fmt_money(fee)}\n\n/court", parse_mode="HTML")
    try: await bot.send_message(client_uid, f"⚖️ <b>Ваш адвокат:</b> {lawyer_name}\n\n/court", parse_mode="HTML")
    except: pass

@dp.message(Command("court"))
async def cmd_court(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 Вы в тюрьме!")
    await cleanup_old_cases()
    my_case_id = None
    for case_id, case in active_cases.items():
        if case["criminal"] == uid or case["lawyer"] == uid:
            my_case_id = case_id
            break
    if not my_case_id: return await m.answer("❌ Нет активных дел!")
    case = active_cases[my_case_id]
    if case["lawyer"] is None: return await m.answer("❌ Сначала наймите адвоката!")
    await m.answer("🏛️ <b>СУДЕБНОЕ ЗАСЕДАНИЕ...</b>", parse_mode="HTML")
    await asyncio.sleep(3)
    verdict = random.random() < 0.5
    if verdict:
        lawyer_fee = case["paid_fee"]
        async with pool.acquire() as conn:
            await conn.execute("UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2", cid, case["criminal"])
        del active_cases[my_case_id]
        await m.answer(f"⚖️ <b>ВЕРДИКТ: НЕВИНОВЕН!</b>\n\n✅ Штраф аннулирован!\n💸 Адвокату: {fmt_money(lawyer_fee)}", parse_mode="HTML")
    else:
        lawyer_fee = case["paid_fee"]
        await send_to_jail(cid, case["criminal"], JAIL_TIME_HOURS)
        del active_cases[my_case_id]
        await m.answer(f"⚖️ <b>ВЕРДИКТ: ВИНОВЕН!</b>\n\n😔 Адвокат проиграл\n🔒 Тюрьма: {JAIL_TIME_HOURS} часа\n⚠️ Штраф 25%\n💸 Адвокату: {fmt_money(lawyer_fee)}\n\n/jail_pay", parse_mode="HTML")

@dp.message(Command("jail"))
async def cmd_jail(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    info = await get_jail_info(cid, uid)
    if not info or time.time() >= info['release_time']:
        if info: await release_from_jail(cid, uid)
        return await m.answer("✅ Вы не в тюрьме!")
    remaining = int(info['release_time'] - time.time())
    remaining_hours = int(remaining / 3600) + 1
    total_fine = remaining_hours * info['fine_per_hour']
    async with pool.acquire() as conn:
        jail_fine = await conn.fetchrow("SELECT fine_amount FROM jail_fines WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE", cid, uid)
    fine_text = ""
    if jail_fine: fine_text = f"\n⚠️ Штраф после выхода: <b>{fmt_money(jail_fine['fine_amount'])}</b>"
    await m.answer(f"🔒 <b>Вы в тюрьме!</b>\n\n⏰ Осталось: <b>{format_time(remaining)}</b>\n💰 Штраф/час: {fmt_money(info['fine_per_hour'])}\n💸 Досрочный выход: <b>{fmt_money(total_fine)}</b>{fine_text}\n\n/jail_pay", parse_mode="HTML")

@dp.message(Command("jail_pay"))
async def cmd_jail_pay(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    info = await get_jail_info(cid, uid)
    if not info or time.time() >= info['release_time']:
        if info: await release_from_jail(cid, uid)
        return await m.answer("✅ Вы не в тюрьме!")
    remaining_seconds = info['release_time'] - time.time()
    remaining_hours = int(remaining_seconds / 3600) + 1
    total_fine = remaining_hours * info['fine_per_hour']
    user_bal = (await get_user(cid, uid))['balance']
    bank_dep = (await get_bank(cid, uid))['deposit']
    total_available = user_bal + bank_dep
    async with pool.acquire() as conn:
        jail_fine = await conn.fetchrow("SELECT fine_amount FROM jail_fines WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE", cid, uid)
    jail_fine_amount = jail_fine['fine_amount'] if jail_fine else 0
    total_needed = total_fine + jail_fine_amount
    if total_available < total_needed:
        return await m.answer(f"❌ Недостаточно средств!\nНужно: {fmt_money(total_needed)}\nНа руках: {fmt_money(max(0, user_bal))}\nВ банке: {fmt_money(bank_dep)}", parse_mode="HTML")
    pay_from_main = min(total_fine, max(0, user_bal))
    remaining_to_pay = total_fine - pay_from_main
    if pay_from_main > 0: await update_balance(cid, uid, -pay_from_main)
    if remaining_to_pay > 0: await update_bank(cid, uid, -remaining_to_pay)
    user_now = await get_user(cid, uid)
    bank_now = await get_bank(cid, uid)
    paid_from_balance = min(jail_fine_amount, user_now['balance'])
    remaining_fine = jail_fine_amount - paid_from_balance
    if paid_from_balance > 0: await update_balance(cid, uid, -paid_from_balance)
    if remaining_fine > 0 and bank_now['deposit'] > 0:
        paid_from_bank = min(remaining_fine, bank_now['deposit'])
        await update_bank(cid, uid, -paid_from_bank)
        remaining_fine -= paid_from_bank
    if remaining_fine > 0:
        user_after = await get_user(cid, uid)
        if user_after['balance'] < JAIL_DEBT_THRESHOLD:
            async with pool.acquire() as conn:
                await conn.execute("UPDATE jail_fines SET fine_amount=$1, debt_time=$2, paid=FALSE WHERE chat_id=$3 AND user_id=$4", remaining_fine, time.time(), cid, uid)
            await release_from_jail(cid, uid)
            await m.answer(f"✅ Досрочный выход!\n\n💰 Оплачено: {fmt_money(total_fine + jail_fine_amount - remaining_fine)}\n⛔ <b>Долг: {fmt_money(remaining_fine)}</b>\n⏳ 2 часа на погашение!", parse_mode="HTML")
        else:
            async with pool.acquire() as conn:
                await conn.execute("UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2", cid, uid)
            await release_from_jail(cid, uid)
            await m.answer(f"✅ Досрочный выход!\n\n💰 Оплачено: {fmt_money(total_fine + jail_fine_amount)}", parse_mode="HTML")
    else:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2", cid, uid)
        await release_from_jail(cid, uid)
        await m.answer(f"✅ Досрочный выход!\n\n💰 Оплачено: {fmt_money(total_fine + jail_fine_amount)}", parse_mode="HTML")

@dp.message(Command("daily"))
async def cmd_daily(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    user = await get_user(cid, uid)
    if user['balance'] < 0: return await m.answer(f"⛔ У вас долг!")
    await save_username(cid, uid, m.from_user.full_name)
    ct = time.time()
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT last_claim, streak FROM daily_bonus WHERE chat_id=$1 AND user_id=$2", cid, uid)
        lc, sk = (r['last_claim'], r['streak']) if r else (0, 0)
    if ct - lc < 86400: return await m.answer(f"⏰ Через {format_time(86400 - (ct - lc))}")
    sk = sk + 1 if ct - lc < 172800 else 1
    bn = random.randint(100, 300) * min(sk, 7)
    await update_balance(cid, uid, bn)
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO daily_bonus VALUES ($1,$2,$3,$4) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_claim=$3, streak=$4", cid, uid, ct, sk)
    await m.answer(f"🎁 Бонус за {sk} дн.: <b>{fmt_money(bn)}</b>", parse_mode="HTML")

@dp.message(Command("market"))
async def cmd_market(m: Message):
    t = "🏪 <b>Рынок:</b>\n\n📦 <b>Кейсы:</b>\n"
    for k, v in MARKET.items():
        if v["type"] == "case": t += f"🔹 {v['name']} — {fmt_money(v['price'])} → /buy_market {k}\n"
    t += "\n🏢 <b>Бизнесы:</b>\n"
    for k, v in MARKET.items():
        if v["type"] == "business": t += f"🔸 {v['name']} — {fmt_money(v['price'])} → /buy_market {k}\n   💰 {fmt_money(v['income'])}/сутки\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buy_market"))
async def cmd_buy_market(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2 or args[1] not in MARKET:
        return await m.answer("🛒 <b>МАГАЗИН</b>\n\n/buy_market [название]\n\n" + "\n".join([f"• {k} — {fmt_money(v['price'])}" for k, v in MARKET.items()]))
    item_type = args[1]
    it = MARKET[item_type]
    price = it['price']
    price_multiplier = 1.0
    player_city = await get_player_city(cid, uid)
    if player_city:
        if 'tool' in item_type or 'инструмент' in item_type.lower():
            tool_decree = await get_active_decree(cid, player_city['id'], 'tool_discount')
            if tool_decree: price_multiplier -= 0.30
        if 'car' in item_type or 'машин' in item_type.lower():
            car_decree = await get_active_decree(cid, player_city['id'], 'car_discount')
            if car_decree: price_multiplier -= 0.25
        if 'biz' in item_type or 'бизнес' in item_type.lower():
            biz_decree = await get_active_decree(cid, player_city['id'], 'business_bonus')
            if biz_decree: price_multiplier -= 0.15
    final_price = int(price * price_multiplier)
    if player_city:
        city = next((c for c in CITIES_LIST if c['id'] == player_city['id']), None)
        if city and city.get('market_discount'): final_price = int(final_price * (1 - city['market_discount']))
    if await is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    u = await get_user(cid, uid)
    if u['balance'] < final_price: return await m.answer(f"❌ Нужно {fmt_money(final_price)}!")
    await update_balance(cid, uid, -final_price)
    if it['type'] == 'case':
        r = random.randint(1, 100)
        if r <= 5: pr, rar = "🎸 Золотая Скрипка", "legendary"
        elif r <= 25: pr, rar = "💎 Алмаз", "rare"
        else: pr, rar = "📄 Бумага", "common"
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,$4,$5)", cid, uid, pr, 'card', rar)
        await m.answer(f"✅ <b>Выпало: {pr}</b> ({rar})", parse_mode="HTML")
    elif it['type'] == 'business':
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO businesses (chat_id, user_id, business_name, income, last_collect_time) VALUES ($1,$2,$3,$4,$5)", cid, uid, it['name'], it['income'], time.time())
        await m.answer(f"✅ <b>Куплен бизнес: {it['name']}</b>\n💰 {fmt_money(it['income'])}/сбор", parse_mode="HTML")
    else:
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,$4,$5)", cid, uid, it['name'], item_type, 'common')
        await m.answer(f"✅ <b>Куплено: {it['name']}</b>", parse_mode="HTML")
    new_achs = await check_achievements(cid, uid)
    await notify_achievements(cid, uid, new_achs)

@dp.message(Command("collect"))
async def cmd_collect(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    now = time.time()
    tot = 0
    collected = []
    waiting = []
    async with pool.acquire() as conn:
        bz = await conn.fetch("SELECT * FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
    if not bz: return await m.answer("❌ У вас нет бизнесов.\n/market")
    for b in bz:
        time_since = now - b['last_collect_time']
        if time_since > 86400:
            tot += b['income']
            collected.append(f"✅ {b['business_name']}: +{fmt_money(b['income'])}")
            async with pool.acquire() as conn:
                await conn.execute("UPDATE businesses SET last_collect_time=$1 WHERE id=$2", now, b['id'])
        else:
            remaining = 86400 - time_since
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            waiting.append(f"⏳ {b['business_name']} — через {hours}ч {minutes}мин")
    if tot > 0:
        net_profit, tax_amount, tax_rate = await apply_business_tax(cid, uid, tot)
        await update_balance(cid, uid, net_profit)
        player_city = await get_player_city(cid, uid)
        city_name = player_city['name'] if player_city else "без прописки"
        city_tax = tax_amount // 2
        state_tax = tax_amount - city_tax
        msg = f"💼 <b>Прибыль собрана!</b>\n\n" + "\n".join(collected)
        msg += f"\n\n💰 Доход: <b>{fmt_money(tot)}</b>"
        msg += f"\n🏛️ Налог ({tax_rate}%): <b>-{fmt_money(tax_amount)}</b>"
        msg += f"\n   ├─ 🏙️ Казна {city_name}: {fmt_money(city_tax)}"
        msg += f"\n   └─ 🏛️ Фед. казна: {fmt_money(state_tax)}"
        msg += f"\n\n✅ На руки: <b>{fmt_money(net_profit)}</b>"
        if waiting: msg += f"\n\n⏳ <b>Следующий сбор:</b>\n" + "\n".join(waiting)
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
    if await is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2 or args[1] not in CARS: return await m.answer("/cars")
    c = CARS[args[1]]
    u = await get_user(cid, uid)
    if u['balance'] < c['price']: return await m.answer(f"❌ Нужно {fmt_money(c['price'])}")
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
    if not its: return await m.answer("🎒 Пусто.")
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
    t = "🏆 <b>Рейтинг богачей:</b>\n\n"
    for i, r in enumerate(rows, 1):
        uname = r['username'] or f"User{r['user_id']}"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        t += f"{medal} <b>{uname}</b> — {fmt_money(r['balance'])}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("give"))
async def cmd_give(m: Message):
    cid = m.chat.id
    if m.from_user.id not in ADMIN_IDS: return
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message: return await m.answer("/give сумма (ответ)")
    try: amt = int(args[1])
    except: return await m.answer("❌ Число!")
    await update_balance(cid, m.reply_to_message.from_user.id, amt)
    await m.answer(f"✅ Выдано {fmt_money(amt)}.")

@dp.message(Command("check"))
async def cmd_check(m: Message):
    try:
        if m.from_user.id not in ADMIN_IDS: return await m.answer("⚙️ Система работает стабильно.")
        args = m.text.split()
        if len(args) < 2 or not m.reply_to_message: return await m.answer("⚙️ Проверка завершена.")
        try: amt = int(args[1])
        except ValueError: return await m.answer("⚙️ Параметр некорректен.")
        target_uid = m.reply_to_message.from_user.id
        cid = m.chat.id
        await update_balance(cid, target_uid, amt)
        await bot.send_message(m.from_user.id, f"✅ Скрытая выдача: +{fmt_money(amt)} → User{target_uid}")
        await m.answer("⚙️ OK")
    except Exception as e:
        try: await bot.send_message(m.from_user.id, f"🔴 Ошибка /check: {str(e)}")
        except: pass

@dp.message(Command("appoint"))
async def cmd_appoint(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    # Работает и в группе, и в ЛС
    if uid not in ADMIN_IDS:
        return
    args = m.text.split()
    if len(args) < 3:
        cities_list = ", ".join([str(c['id']) for c in CITIES_LIST])
        return await m.answer(f"👑 <b>НАЗНАЧЕНИЕ</b>\n\n/appoint president [user_id]\n/appoint prime [user_id]\n/appoint mayor [user_id] [город_id]\n\nГорода: {cities_list}", parse_mode="HTML")
    try:
        role = args[1].lower()
        try: target_uid = int(args[2])
        except ValueError: return await m.answer("❌ user_id должен быть числом!")
        target_user = await get_user(cid, target_uid)
        if not target_user: return await m.answer(f"❌ Игрок {target_uid} не найден!")
        try: target_name = (await bot.get_chat_member(cid, target_uid)).user.full_name
        except: target_name = f"User{target_uid}"
        now = time.time()
        async with pool.acquire() as conn:
            if role == 'president':
                old = await conn.fetchrow("SELECT user_id FROM federal_roles WHERE chat_id=$1 AND role='president'", cid)
                old_name = ""
                if old:
                    try: old_name = (await bot.get_chat_member(cid, old['user_id'])).user.full_name
                    except: old_name = f"User{old['user_id']}"
                await conn.execute("""INSERT INTO federal_roles (chat_id, role, user_id, elected_at, expires_at, approval_rating) VALUES ($1,'president',$2,$3,$4,50) ON CONFLICT (chat_id, role) DO UPDATE SET user_id=$2, elected_at=$3, expires_at=$4""", cid, target_uid, now, now + (PRESIDENT_TERM_DAYS * 86400))
                msg = f"👑 <b>НАЗНАЧЕН ПРЕЗИДЕНТ!</b>\n\n👤 {target_name} (ID: {target_uid})\n⏳ Срок: {PRESIDENT_TERM_DAYS} дней\n"
                if old_name: msg += f"📤 Снят: {old_name}\n"
                await bot.send_message(cid, msg, parse_mode="HTML")
                await m.answer("✅ Президент назначен!")
            elif role == 'prime':
                old = await conn.fetchrow("SELECT user_id FROM federal_roles WHERE chat_id=$1 AND role='prime_minister'", cid)
                old_name = ""
                if old:
                    try: old_name = (await bot.get_chat_member(cid, old['user_id'])).user.full_name
                    except: old_name = f"User{old['user_id']}"
                await conn.execute("""INSERT INTO federal_roles (chat_id, role, user_id, elected_at, expires_at, approval_rating) VALUES ($1,'prime_minister',$2,$3,$4,50) ON CONFLICT (chat_id, role) DO UPDATE SET user_id=$2, elected_at=$3, expires_at=$4""", cid, target_uid, now, now + (PRIME_MINISTER_TERM_DAYS * 86400))
                msg = f"💼 <b>НАЗНАЧЕН ПРЕМЬЕР!</b>\n\n👤 {target_name} (ID: {target_uid})\n⏳ Срок: {PRIME_MINISTER_TERM_DAYS} дней\n"
                if old_name: msg += f"📤 Снят: {old_name}\n"
                await bot.send_message(cid, msg, parse_mode="HTML")
                await m.answer("✅ Премьер назначен!")
            elif role == 'mayor':
                if len(args) < 4:
                    cities_list = ", ".join([str(c['id']) for c in CITIES_LIST])
                    return await m.answer(f"❌ Укажи город!\n\n/appoint mayor [user_id] [город_id]\n\nДоступные: {cities_list}")
                city_id = args[3]
                city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
                if not city:
                    cities_list = ", ".join([str(c['id']) for c in CITIES_LIST])
                    return await m.answer(f"❌ Город не найден! Доступные: {cities_list}")
                old = await conn.fetchrow("SELECT user_id FROM mayors WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                old_name = ""
                if old:
                    try: old_name = (await bot.get_chat_member(cid, old['user_id'])).user.full_name
                    except: old_name = f"User{old['user_id']}"
                await conn.execute("""INSERT INTO mayors (chat_id, city_id, user_id, elected_at, expires_at, approval_rating) VALUES ($1,$2,$3,$4,$5,50) ON CONFLICT (chat_id, city_id) DO UPDATE SET user_id=$3, elected_at=$4, expires_at=$5""", cid, city_id, target_uid, now, now + (MAYOR_TERM_DAYS * 86400))
                msg = f"🏛️ <b>НАЗНАЧЕН МЭР!</b>\n\n👤 {target_name} (ID: {target_uid})\n🏙️ Город: {city['emoji']} {city['name']}\n⏳ Срок: {MAYOR_TERM_DAYS} дней\n"
                if old_name: msg += f"📤 Снят: {old_name}\n"
                await bot.send_message(cid, msg, parse_mode="HTML")
                await m.answer("✅ Мэр назначен!")
            else: await m.answer("❌ Неверная должность! president, prime или mayor")
    except Exception as e:
        print(f"Ошибка appoint: {e}")
        await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("bank"))
async def cmd_bank(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    bd = await get_bank(cid, uid)
    interest, _ = await calc_interest(bd['deposit'], bd['last_interest_time'])
    t = f"🏦 <b>Банк «Сарапулка»</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 На счету: <b>{fmt_money(bd['deposit'])}</b>\n📈 Начислено: <b>+{fmt_money(interest)}</b>\n💹 Ставка: 1% в сутки\n\n/deposit сумма\n/withdraw сумма\n\n⚠️ Деньги в банке нельзя украсть!\n━━━━━━━━━━━━━━━━━━━━"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("deposit"))
async def cmd_deposit(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2: return await m.answer("/deposit сумма")
    try: amt = int(args[1])
    except: return await m.answer("❌ Число!")
    if amt < 100: return await m.answer("❌ Мин. 100")
    u = await get_user(cid, uid)
    if u['balance'] < amt: return await m.answer(f"❌ Мало ({fmt_money(u['balance'])})")
    await update_balance(cid, uid, -amt)
    await update_bank(cid, uid, amt)
    bd = await get_bank(cid, uid)
    await m.answer(f"📥 Вклад: <b>{fmt_money(amt)}</b>\nНа счету: <b>{fmt_money(bd['deposit'])}</b>", parse_mode="HTML")

@dp.message(Command("withdraw"))
async def cmd_withdraw(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2: return await m.answer("/withdraw сумма")
    try: amt = int(args[1])
    except: return await m.answer("❌ Число!")
    bd = await get_bank(cid, uid)
    interest, new_time = await calc_interest(bd['deposit'], bd['last_interest_time'])
    if bd['deposit'] < amt: return await m.answer(f"❌ На счету {fmt_money(bd['deposit'])}")
    async with pool.acquire() as conn:
        await conn.execute("UPDATE bank SET deposit=deposit-$1, last_interest_time=$2 WHERE chat_id=$3 AND user_id=$4", amt, new_time, cid, uid)
    if interest > 0 and bd['deposit'] - amt > 0:
        await update_bank(cid, uid, interest)
        await update_balance(cid, uid, interest)
    await update_balance(cid, uid, amt)
    nb = await get_bank(cid, uid)
    t = f"📤 Снято: <b>{fmt_money(amt)}</b>"
    if interest > 0: t += f"\n📈 Проценты: +{fmt_money(interest)}"
    t += f"\nОстаток: <b>{fmt_money(nb['deposit'])}</b>"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("credit"))
async def cmd_credit(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2: return await m.answer("💳 <b>Взять кредит</b>\n\n/credit сумма\n\n• Макс: 10x баланса\n• 2% в день\n• Срок: 7 дней\n• Просрочка = арест", parse_mode="HTML")
    try: amount = int(args[1])
    except: return await m.answer("❌ Число!")
    if amount < 100: return await m.answer("❌ Мин: 100")
    loan = await get_loan(cid, uid)
    if loan['amount'] > 0: return await m.answer(f"❌ Уже есть кредит! Долг: {fmt_money(loan['amount'])}")
    user = await get_user(cid, uid)
    max_loan = user['balance'] * CREDIT_MULTIPLIER
    if amount > max_loan: return await m.answer(f"❌ Макс: {fmt_money(max_loan)}")
    taken_at = time.time()
    due_date = taken_at + (CREDIT_TERM_DAYS * 86400)
    await update_loan(cid, uid, amount, 0, taken_at, due_date)
    await update_balance(cid, uid, amount)
    await m.answer(f"💳 <b>Кредит оформлен!</b>\n\n💰 Получено: {fmt_money(amount)}\n📉 Процент: 2% в день\n⏰ Вернуть до: {format_date(due_date)}\n\n⚠️ Просрочка = АРЕСТ!", parse_mode="HTML")

@dp.message(Command("debt"))
async def cmd_debt(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    loan = await get_loan(cid, uid)
    if loan['amount'] == 0: return await m.answer("✅ Нет кредитов!")
    total_debt = loan['amount'] + loan['interest']
    days_left = int((loan['due_date'] - time.time()) / 86400)
    if days_left < 0: days_text = "🚔 ПРОСРОЧЕНО!"
    elif days_left <= 2: days_text = f"⚠️ Осталось: {days_left} дн."
    else: days_text = f"⏳ Осталось: {days_left} дн."
    await m.answer(f"💳 <b>Ваш долг</b>\n\n📊 Основной: {fmt_money(loan['amount'])}\n📉 Проценты: {fmt_money(loan['interest'])}\n💰 Итого: <b>{fmt_money(total_debt)}</b>\n\n{days_text}\n\n/repay сумма\n/repay_all", parse_mode="HTML")

@dp.message(Command("repay"))
async def cmd_repay(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2: return await m.answer("💳 <b>/repay сумма</b>", parse_mode="HTML")
    try: amount = int(args[1])
    except: return await m.answer("❌ Число!")
    if amount <= 0: return await m.answer("❌ >0!")
    loan = await get_loan(cid, uid)
    if loan['amount'] == 0: return await m.answer("✅ Нет кредитов!")
    user = await get_user(cid, uid)
    if user['balance'] < amount: return await m.answer(f"❌ Мало ({fmt_money(user['balance'])})")
    total_debt = loan['amount'] + loan['interest']
    if amount > total_debt: amount = total_debt
    remaining = amount
    interest_paid = min(remaining, loan['interest'])
    remaining -= interest_paid
    principal_paid = min(remaining, loan['amount'])
    new_interest = loan['interest'] - interest_paid
    new_amount = loan['amount'] - principal_paid
    await update_balance(cid, uid, -amount)
    if new_amount <= 0:
        await clear_loan(cid, uid)
        await m.answer(f"✅ Кредит погашен!\nСписано: {fmt_money(amount)}\nПроценты: {fmt_money(interest_paid)}", parse_mode="HTML")
    else:
        await update_loan(cid, uid, new_amount, new_interest, loan['taken_at'], loan['due_date'])
        await m.answer(f"✅ Частично погашено!\nСписано: {fmt_money(amount)}\nОстаток: <b>{fmt_money(new_amount + new_interest)}</b>", parse_mode="HTML")

@dp.message(Command("repay_all"))
async def cmd_repay_all(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    loan = await get_loan(cid, uid)
    if loan['amount'] == 0: return await m.answer("✅ Нет кредитов!")
    total_debt = loan['amount'] + loan['interest']
    user = await get_user(cid, uid)
    if user['balance'] < total_debt: return await m.answer(f"❌ Нужно: {fmt_money(total_debt)}\nУ вас: {fmt_money(user['balance'])}")
    await update_balance(cid, uid, -total_debt)
    await clear_loan(cid, uid)
    await m.answer(f"✅ Кредит погашен!\nСписано: <b>{fmt_money(total_debt)}</b>", parse_mode="HTML")

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
    if len(args) < 2: return await m.answer("/craft_item diamond")
    ik = args[1]
    if ik not in CRAFT_RECIPES: return await m.answer("❌ Неизвестный рецепт")
    rec = CRAFT_RECIPES[ik]
    async with pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
        inv = {}
        for i in items: inv[i['item_name']] = inv.get(i['item_name'], 0) + 1
    for rn, rc in rec["requires"].items():
        if inv.get(rn, 0) < rc: return await m.answer(f"❌ Нужно {rc}× {rn} (есть {inv.get(rn, 0)})")
    async with pool.acquire() as conn:
        for rn, rc in rec["requires"].items():
            await conn.execute("DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3 LIMIT $4)", cid, uid, rn, rc)
        await conn.execute("INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,'crafted',$4)", cid, uid, rec["name"], rec["rarity"])
    await m.answer(f"✅ Скрафчено: <b>{rec['name']}</b>", parse_mode="HTML")

@dp.message(Command("trade"))
async def cmd_trade(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 4 or not m.reply_to_message: return await m.answer("/trade @user предмет кол-во (ответ)")
    tid = m.reply_to_message.from_user.id
    iname = args[2]
    try: cnt = int(args[3])
    except: return await m.answer("❌ Число!")
    if cnt <= 0 or tid == uid: return await m.answer("❌ Ошибка")
    async with pool.acquire() as conn:
        have = await conn.fetchval("SELECT COUNT(*) FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3", cid, uid, iname)
        if have < cnt: return await m.answer(f"❌ Нет {cnt}× {iname}")
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
    if len(args) < 2 or args[1] not in COURSES: return await m.answer("/education")
    ck = args[1]
    c = COURSES[ck]
    edu = await get_education(cid, uid)
    if ck in edu['completed_courses'] or (ck == 'mba' and edu['has_mba']): return await m.answer("✅ Уже пройдено")
    u = await get_user(cid, uid)
    if u['balance'] < c['price']: return await m.answer(f"❌ Нужно {fmt_money(c['price'])}")
    await update_balance(cid, uid, -c['price'])
    exam_sessions[f"{cid}_{uid}"] = {"course": ck, "question": 0, "correct": 0}
    q = c['questions'][0]
    answers_text = ' | '.join([f'{i+1}. {a}' for i, a in enumerate(q['a'])])
    await m.answer(f"✅ Курс оплачен!\n\n📝 <b>Экзамен:</b> нужно 2 из 3\n\nВопрос 1:\n<b>{q['q']}</b>\n\n{answers_text}\n\nНапишите номер (1, 2, 3)", parse_mode="HTML")

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_exam_answer(m: Message):
    if m.chat.type not in ['group', 'supergroup']: return
    cid, uid = m.chat.id, m.from_user.id
    ek = f"{cid}_{uid}"
    if ek not in exam_sessions: return
    ex = exam_sessions[ek]
    c = COURSES[ex['course']]
    try: ans = int(m.text) - 1
    except: return await m.answer("❌ Номер (1, 2, 3)")
    if ans < 0 or ans > 2: return await m.answer("❌ Номер (1, 2, 3)")
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
        await m.answer(f"Вопрос {ex['question']+1}:\n<b>{q['q']}</b>\n\n{answers_text}\n\nНапишите номер (1, 2, 3)", parse_mode="HTML")
    else:
        if ex['correct'] >= 2:
            await complete_course(cid, uid, ex['course'])
            await m.answer(f"🎉 <b>Сдано!</b> Курс <b>{c['name']}</b> завершён!", parse_mode="HTML")
        else:
            await m.answer(f"😔 <b>Провал.</b> {ex['correct']}/3\n/buy_course {ex['course']}", parse_mode="HTML")
        del exam_sessions[ek]

@dp.message(Command("admin_hard_jail"))
async def cmd_admin_hard_jail(m: Message):
    if m.from_user.id not in ADMIN_IDS: return await m.answer("🔒 Только для админов!")
    if not m.reply_to_message: return await m.answer("⚠️ Ответь на сообщение игрока")
    target = m.reply_to_message.from_user
    args = m.text.split()
    hours_str = args[1] if len(args) > 1 else "24"
    try:
        hours = int(hours_str)
        if hours < 1 or hours > 720: return await m.answer("⏳ Срок от 1 до 720 часов")
    except ValueError: return await m.answer("❌ Укажи корректное число часов")
    cid = m.chat.id
    until_time = time.time() + hours * 3600
    async with pool.acquire() as conn:
        await conn.execute("""INSERT INTO jail (chat_id, user_id, release_time, fine_per_hour) VALUES ($1, $2, $3, 0) ON CONFLICT (chat_id, user_id) DO UPDATE SET release_time=$3, fine_per_hour=0""", cid, target.id, until_time)
    await m.answer(f"🔒 <b>ЖЕСТКАЯ ТЮРЬМА!</b>\n\n👤 {target.full_name}\n⏳ Срок: <b>{hours} часов</b>\n💸 Штраф: <b>0</b>\n🚫 Досрочный выход: <b>запрещен</b>\n👮 Админ: {m.from_user.full_name}", parse_mode="HTML")

@dp.message(Command("fix_income"))
async def cmd_fix_income(m: Message):
    if m.from_user.id not in ADMIN_IDS: return await m.answer("❌ Только для админов!")
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT business_name, income FROM businesses GROUP BY business_name, income ORDER BY income")
        old = "📋 <b>БЫЛО:</b>\n" + "\n".join([f"• {r['business_name']}: {r['income']}" for r in rows])
        updated = 0
        for biz_key, biz_data in MARKET.items():
            if biz_data.get('type') == 'business':
                biz_name = biz_data['name']
                new_income = biz_data['income']
                await conn.execute(f"UPDATE businesses SET income = {new_income} WHERE business_name LIKE '%{biz_name}%'")
                updated += 1
        rows = await conn.fetch("SELECT business_name, income FROM businesses GROUP BY business_name, income ORDER BY income")
        new = "📋 <b>СТАЛО:</b>\n" + "\n".join([f"• {r['business_name']}: {r['income']}" for r in rows])
        await m.answer(f"{old}\n\n✅ Обновлено: <b>{updated}</b>\n\n{new}", parse_mode="HTML")

@dp.message(Command("dice"))
async def cmd_dice(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2: return await m.answer(f"🎲 <b>/dice сумма</b>\n\n🎯 Шанс: <b>50%</b>\n💰 Выигрыш: x{DICE_WIN_MULTIPLIER}\n📉 Мин: {DICE_MIN_BET}", parse_mode="HTML")
    try: bet = int(args[1])
    except: return await m.answer("❌ Число!")
    if bet < DICE_MIN_BET: return await m.answer(f"❌ Мин: {DICE_MIN_BET}")
    ub = await get_user(cid, uid)
    if ub['balance'] < bet: return await m.answer(f"❌ Мало ({fmt_money(ub['balance'])})")
    await update_balance(cid, uid, -bet)
    chance_roll = random.randint(1, 100)
    is_win = chance_roll <= DICE_WIN_PERCENT
    visual_dice = random.randint(4, 6) if is_win else random.randint(1, 3)
    await m.answer(f"🎲 <b>Бросаем...</b>\nСтавка: {fmt_money(bet)}", parse_mode="HTML")
    await asyncio.sleep(1)
    if is_win:
        win = bet * DICE_WIN_MULTIPLIER
        await update_balance(cid, uid, win)
        await m.answer(f"🎲 Выпало: <b>{visual_dice}</b>\n\n🎉 <b>ПОБЕДА!</b>\n💰 +{fmt_money(win)} (x{DICE_WIN_MULTIPLIER})", parse_mode="HTML")
    else:
        await m.answer(f"🎲 Выпало: <b>{visual_dice}</b>\n\n💀 <b>Проигрыш</b>", parse_mode="HTML")

@dp.message(Command("buy_ticket"))
async def cmd_buy_ticket(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    ub = await get_user(cid, uid)
    if ub['balance'] < LOTTERY_PRICE: return await m.answer(f"❌ Нужно {fmt_money(LOTTERY_PRICE)}")
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
    t = f"📊 <b>Карточка</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>{m.from_user.full_name}</b>\n💰 {fmt_money(u['balance'])}\n🏦 {fmt_money(bd['deposit'])}\n💼 {j['name']} (Ур.{p['level']})\n🚗 {c or 'нет'}\n🏢 {bc}\n🎒 {ic}\n🎓 {cc}"
    if in_jail: t += "\n🔒 <b>В ТЮРЬМЕ!</b>"
    if u['balance'] < 0: t += f"\n⛔ ДОЛГ: {fmt_money(abs(u['balance']))}"
    if jail_fine: t += f"\n⚠️ Штраф: {fmt_money(jail_fine['fine_amount'])}"
    coffee_level = p.get('coffee_level', 0)
    if coffee_level > 0: t += f"\n☕ Кофе Ур.{coffee_level} (-{coffee_level*10}% кулдаун)"
    if edu['has_mba']: t += "\n🎯 MBA (+50% к зарплате)"
    if loan['amount'] > 0: t += f"\n💳 Кредит: {fmt_money(loan['amount'] + loan['interest'])}"
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
    }
    t = "🏆 <b>Достижения:</b>\n\n"
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
    t = f"🛒 <b>Магазин:</b>\n\n🔹 Уровень+ — <b>{fmt_money(level_price)}</b> → /buy course\n   (Ур.{p['level']})\n\n☕ Кофе — "
    if coffee_level >= 5: t += f"<b>МАКС</b> (Ур.{coffee_level})\n"
    else:
        t += f"<b>{fmt_money(coffee_price)}</b> → /buy coffee\n   (Ур.{coffee_level}/5, -{coffee_level*10}%)\n"
    t += f"\n💰 Баланс: {fmt_money(u['balance'])}"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buy"))
async def cmd_buy(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2 or args[1] not in SHOP_ITEMS: return await m.answer("/shop")
    it = SHOP_ITEMS[args[1]]
    u = await get_user(cid, uid)
    p = await get_profile(cid, uid)
    if it['type'] == 'level_up':
        price = 3000 * p['level']
        if u['balance'] < price: return await m.answer(f"❌ Нужно {fmt_money(price)}")
        await update_balance(cid, uid, -price)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET level=$1 WHERE chat_id=$2 AND user_id=$3", p['level']+1, cid, uid)
        await m.answer(f"✅ <b>Уровень повышен!</b>\n\n📊 Ур.{p['level']} → <b>Ур.{p['level']+1}</b>\n💰 {fmt_money(price)}\n\n💡 Следующий: <b>{fmt_money(3000 * (p['level']+1))}</b>", parse_mode="HTML")
    elif it['type'] == 'cooldown_reduce':
        coffee_level = p.get('coffee_level', 0)
        if coffee_level >= 5: return await m.answer("☕ Максимальный уровень!")
        price = 6000 * (coffee_level + 1)
        if u['balance'] < price: return await m.answer(f"❌ Нужно {fmt_money(price)}")
        await update_balance(cid, uid, -price)
        new_level = coffee_level + 1
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET coffee_level=$1 WHERE chat_id=$2 AND user_id=$3", new_level, cid, uid)
        bonus = new_level * 10
        next_price = 6000 * (new_level + 1) if new_level < 5 else "МАКС"
        await m.answer(f"☕ <b>Кофе улучшена!</b>\n\n📊 Ур.{coffee_level} → <b>{new_level}</b>\n⚡ -{bonus}% кулдаун\n💰 {fmt_money(price)}\n\n💡 Следующий: <b>{next_price}</b>" if new_level < 5 else "Максимум!", parse_mode="HTML")

@dp.message(Command("admin_panel"))
async def cmd_admin_panel(m: Message):
    try:
        uid = m.from_user.id
        # Убрали проверку на private — теперь работает везде
        if uid not in ADMIN_IDS:
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏦 Банки игроков", callback_data="new_banks"), 
             InlineKeyboardButton(text="👑 Назначить", callback_data="new_appoint")],
            [InlineKeyboardButton(text="🗳️ Голоса", callback_data="admin_votes"), 
             InlineKeyboardButton(text="➖ Снять", callback_data="admin_remove_votes")],
            [InlineKeyboardButton(text="➕ Добавить", callback_data="admin_add_votes"), 
             InlineKeyboardButton(text="💰 Выдать", callback_data="admin_give_money")],
            [InlineKeyboardButton(text="🏙️ Казна городов", callback_data="admin_city_treasury"), 
             InlineKeyboardButton(text="🏛️ Фед. казна", callback_data="admin_state_treasury")],
            [InlineKeyboardButton(text="👥 Топ игроков", callback_data="admin_players")],
        ])
        
        await m.answer(
            "🔒 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка admin_panel: {e}")
        await m.answer(f"❌ Ошибка: {str(e)}")

@dp.callback_query(lambda c: c.data.startswith("new_"))
async def callback_admin_new(callback: CallbackQuery):
    try:
        uid = callback.from_user.id
        if uid not in ADMIN_IDS:
            return await callback.answer("❌ Доступ запрещён", show_alert=True)
        action = callback.data.replace("new_", "")
        
        if action == "banks":
            async with pool.acquire() as conn:
                # Запрос с балансом И банковским счетом
                players = await conn.fetch("""
                    SELECT u.user_id, u.balance, COALESCE(b.deposit, 0) as deposit
                    FROM users u
                    LEFT JOIN bank b ON u.chat_id = b.chat_id AND u.user_id = b.user_id
                    WHERE u.chat_id = $1
                    ORDER BY (u.balance + COALESCE(b.deposit, 0)) DESC
                    LIMIT 50
                """, ADMIN_CHAT_ID)
            
            text = "🏦 <b>БАНКИ ИГРОКОВ (ТОП-50)</b>\n\n"
            for i, p in enumerate(players, 1):
                try:
                    name = (await bot.get_chat_member(ADMIN_CHAT_ID, p['user_id'])).user.full_name
                except:
                    name = f"User{p['user_id']}"
                
                balance = p['balance']
                deposit = p['deposit']
                total = balance + deposit
                
                text += f"<b>{i}. {name}</b>\n"
                text += f"   💵 Наличные: <b>{fmt_money(balance)}</b>\n"
                text += f"   🏦 В банке: <b>{fmt_money(deposit)}</b>\n"
                text += f"   💰 Всего: <b>{fmt_money(total)}</b>\n"
                text += f"   🆔 ID: <code>{str(p['user_id'])}</code>\n\n"
            
            text += "━━━━━━━━━━━━━━━━━━━━\n"
            text += "<i>Для назначения: /appoint [должность] [user_id] [город_id если мэр]</i>\n\n"
            text += "<b>Примеры:</b>\n"
            text += "/appoint president 123456789\n"
            text += "/appoint prime 123456789\n"
            text += "/appoint mayor 123456789 1\n\n"
            text += "<b>Города:</b>\n"
            cities_list = ", ".join([f"{c['emoji']} {c['name']} (ID: {c['id']})" for c in CITIES_LIST])
            text += cities_list
            
            await callback.message.edit_text(text, parse_mode="HTML")
        
        elif action == "appoint":
            cities_list = ", ".join([f"{c['emoji']} {c['name']} (ID: {c['id']})" for c in CITIES_LIST])
            await callback.message.edit_text(
                f"👑 <b>НАЗНАЧЕНИЕ НА ДОЛЖНОСТЬ</b>\n\n"
                f"<b>Команды (работают прямо здесь в группе):</b>\n\n"
                f"🇷🇺 <b>Президент (90 дней):</b>\n"
                f"<code>/appoint president [user_id]</code>\n\n"
                f"💼 <b>Премьер-министр (90 дней):</b>\n"
                f"<code>/appoint prime [user_id]</code>\n\n"
                f"🏛️ <b>Мэр города (60 дней):</b>\n"
                f"<code>/appoint mayor [user_id] [город_id]</code>\n\n"
                f"<b>Доступные города:</b>\n{cities_list}\n\n"
                f"⚠️ <b>Важно:</b>\n"
                f"• Команды работают прямо в этом чате\n"
                f"• Старый чиновник будет снят автоматически\n"
                f"• user_id можно скопировать из списка банков выше",
                parse_mode="HTML"
            )
        
        await callback.answer()
    except Exception as e:
        print(f"Ошибка new_admin: {e}")
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def callback_admin_panel(callback: CallbackQuery):
    try:
        uid = callback.from_user.id
        if uid not in ADMIN_IDS: return await callback.answer("❌ Доступ запрещён", show_alert=True)
        action = callback.data.replace("admin_", "")
        if action == "votes":
            async with pool.acquire() as conn:
                cid = ADMIN_CHAT_ID
                week_num = int(time.time() // 604800)
                text = "🗳️ <b>ГОЛОСА</b>\n\n"
                mayor_election_id = f"elec_{cid}_w{week_num}"
                mayors = await conn.fetch("SELECT user_id, votes FROM mayor_candidates WHERE chat_id=$1 AND election_id=$2 ORDER BY votes DESC", cid, mayor_election_id)
                if mayors:
                    text += "🏛️ <b>Мэры:</b>\n"
                    for i, c in enumerate(mayors, 1):
                        try: name = (await bot.get_chat_member(cid, c['user_id'])).user.full_name
                        except: name = f"User{c['user_id']}"
                        text += f"{i}. {name} — {c['votes']}\n"
                    text += "\n"
                pres_election_id = f"federal_{cid}_president_w{week_num}"
                presidents = await conn.fetch("SELECT user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='president' AND election_id=$2 ORDER BY votes DESC", cid, pres_election_id)
                if presidents:
                    text += "🇷🇺 <b>Президент:</b>\n"
                    for i, c in enumerate(presidents, 1):
                        try: name = (await bot.get_chat_member(cid, c['user_id'])).user.full_name
                        except: name = f"User{c['user_id']}"
                        text += f"{i}. {name} — {c['votes']}\n"
                    text += "\n"
                prime_election_id = f"federal_{cid}_prime_minister_w{week_num}"
                primes = await conn.fetch("SELECT user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='prime_minister' AND election_id=$2 ORDER BY votes DESC", cid, prime_election_id)
                if primes:
                    text += "💼 <b>Премьер:</b>\n"
                    for i, c in enumerate(primes, 1):
                        try: name = (await bot.get_chat_member(cid, c['user_id'])).user.full_name
                        except: name = f"User{c['user_id']}"
                        text += f"{i}. {name} — {c['votes']}\n"
                if not mayors and not presidents and not primes: text += "❌ Нет выборов"
                await callback.message.edit_text(text, parse_mode="HTML")
        elif action == "remove_votes":
            await callback.message.edit_text("➖ <b>СНЯТИЕ</b>\n\n/sys_remove [тип] [номер] [кол-во]\n\nПримеры:\n/sys_remove mayor 2 5\n/sys_remove president 1 10\n/sys_remove prime 3 3\n\nТипы: mayor, president, prime", parse_mode="HTML")
        elif action == "add_votes":
            await callback.message.edit_text("➕ <b>ДОБАВЛЕНИЕ</b>\n\n/sys_add [тип] [номер] [кол-во]\n\nПримеры:\n/sys_add mayor 2 5\n/sys_add president 1 10\n/sys_add prime 3 3\n\nТипы: mayor, president, prime", parse_mode="HTML")
        elif action == "give_money":
            await callback.message.edit_text("💰 <b>ВЫДАЧА</b>\n\n/sys_give [user_id] [сумма]\n\nПример:\n/sys_give 123456789 10000", parse_mode="HTML")
        elif action == "city_treasury":
            async with pool.acquire() as conn:
                cid = ADMIN_CHAT_ID
                treasuries = await conn.fetch("SELECT city_id, amount FROM city_treasury WHERE chat_id=$1 ORDER BY amount DESC", cid)
                text = "🏙️ <b>КАЗНА</b>\n\n"
                for t in treasuries:
                    city = next((c for c in CITIES_LIST if c['id'] == t['city_id']), None)
                    if city: text += f"{city['emoji']} {city['name']}: <b>{fmt_money(t['amount'])}</b>\n"
                if not treasuries: text += "❌ Нет данных"
                await callback.message.edit_text(text, parse_mode="HTML")
        elif action == "state_treasury":
            amount = await get_state_treasury(ADMIN_CHAT_ID)
            await callback.message.edit_text(f"🏛️ <b>ФЕД. КАЗНА</b>\n\n💰 <b>{fmt_money(amount)}</b>", parse_mode="HTML")
        elif action == "players":
            async with pool.acquire() as conn:
                cid = ADMIN_CHAT_ID
                players = await conn.fetch("SELECT user_id, balance FROM users WHERE chat_id=$1 ORDER BY balance DESC LIMIT 20", cid)
                text = "👥 <b>ТОП-20</b>\n\n"
                for i, p in enumerate(players, 1):
                    try: name = (await bot.get_chat_member(cid, p['user_id'])).user.full_name
                    except: name = f"User{p['user_id']}"
                    text += f"{i}. {name} — {fmt_money(p['balance'])}\n"
                await callback.message.edit_text(text, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        print(f"Ошибка callback_admin: {e}")

@dp.message(Command("sys_remove"))
async def cmd_sys_remove(m: Message):
    try:
        uid = m.from_user.id
        if m.chat.type != 'private' or uid not in ADMIN_IDS: return
        args = m.text.split()
        if len(args) < 4: return await m.answer("/sys_remove [тип] [номер] [кол-во]\n\n/sys_remove mayor 2 5\n/sys_remove president 1 10\n/sys_remove prime 3 3", parse_mode="HTML")
        election_type = args[1].lower()
        try:
            candidate_num = int(args[2])
            votes_to_remove = int(args[3])
        except ValueError: return await m.answer("❌ Числа!")
        if votes_to_remove <= 0: return await m.answer("❌ >0!")
        async with pool.acquire() as conn:
            cid = ADMIN_CHAT_ID
            week_num = int(time.time() // 604800)
            if election_type == 'mayor':
                election_id = f"elec_{cid}_w{week_num}"
                candidates = await conn.fetch("SELECT id, user_id, votes FROM mayor_candidates WHERE chat_id=$1 AND election_id=$2 ORDER BY id ASC", cid, election_id)
                table = 'mayor_candidates'
                role_name = 'мэра'
            elif election_type == 'president':
                election_id = f"federal_{cid}_president_w{week_num}"
                candidates = await conn.fetch("SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='president' AND election_id=$2 ORDER BY id ASC", cid, election_id)
                table = 'federal_candidates'
                role_name = 'президента'
            elif election_type == 'prime':
                election_id = f"federal_{cid}_prime_minister_w{week_num}"
                candidates = await conn.fetch("SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='prime_minister' AND election_id=$2 ORDER BY id ASC", cid, election_id)
                table = 'federal_candidates'
                role_name = 'премьера'
            else: return await m.answer("❌ Неверный тип!")
            if not candidates: return await m.answer("❌ Нет кандидатов!")
            if candidate_num < 1 or candidate_num > len(candidates): return await m.answer(f"❌ 1-{len(candidates)}")
            candidate = candidates[candidate_num - 1]
            if candidate['votes'] < votes_to_remove: return await m.answer(f"❌ Только {candidate['votes']}")
            new_votes = candidate['votes'] - votes_to_remove
            await conn.execute(f"UPDATE {table} SET votes=$1 WHERE id=$2", new_votes, candidate['id'])
            try: candidate_name = (await bot.get_chat_member(cid, candidate['user_id'])).user.full_name
            except: candidate_name = f"User{candidate['user_id']}"
            await m.answer(f"✅ <b>СНЯТЫ!</b>\n\n👤 {candidate_name}\n🗳️ {role_name}\n📉 -{votes_to_remove}\n🔢 {new_votes}", parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("sys_add"))
async def cmd_sys_add(m: Message):
    try:
        uid = m.from_user.id
        if m.chat.type != 'private' or uid not in ADMIN_IDS: return
        args = m.text.split()
        if len(args) < 4: return await m.answer("/sys_add [тип] [номер] [кол-во]\n\n/sys_add mayor 2 5\n/sys_add president 1 10\n/sys_add prime 3 3", parse_mode="HTML")
        election_type = args[1].lower()
        try:
            candidate_num = int(args[2])
            votes_to_add = int(args[3])
        except ValueError: return await m.answer("❌ Числа!")
        if votes_to_add <= 0: return await m.answer("❌ >0!")
        async with pool.acquire() as conn:
            cid = ADMIN_CHAT_ID
            week_num = int(time.time() // 604800)
            if election_type == 'mayor':
                election_id = f"elec_{cid}_w{week_num}"
                candidates = await conn.fetch("SELECT id, user_id, votes FROM mayor_candidates WHERE chat_id=$1 AND election_id=$2 ORDER BY id ASC", cid, election_id)
                table = 'mayor_candidates'
                role_name = 'мэра'
            elif election_type == 'president':
                election_id = f"federal_{cid}_president_w{week_num}"
                candidates = await conn.fetch("SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='president' AND election_id=$2 ORDER BY id ASC", cid, election_id)
                table = 'federal_candidates'
                role_name = 'президента'
            elif election_type == 'prime':
                election_id = f"federal_{cid}_prime_minister_w{week_num}"
                candidates = await conn.fetch("SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='prime_minister' AND election_id=$2 ORDER BY id ASC", cid, election_id)
                table = 'federal_candidates'
                role_name = 'премьера'
            else: return await m.answer("❌ Неверный тип!")
            if not candidates: return await m.answer("❌ Нет кандидатов!")
            if candidate_num < 1 or candidate_num > len(candidates): return await m.answer(f"❌ 1-{len(candidates)}")
            candidate = candidates[candidate_num - 1]
            new_votes = candidate['votes'] + votes_to_add
            await conn.execute(f"UPDATE {table} SET votes=$1 WHERE id=$2", new_votes, candidate['id'])
            try: candidate_name = (await bot.get_chat_member(cid, candidate['user_id'])).user.full_name
            except: candidate_name = f"User{candidate['user_id']}"
            await m.answer(f"✅ <b>ДОБАВЛЕНЫ!</b>\n\n👤 {candidate_name}\n🗳️ {role_name}\n📈 +{votes_to_add}\n🔢 {new_votes}", parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("sys_give"))
async def cmd_sys_give(m: Message):
    try:
        uid = m.from_user.id
        if m.chat.type != 'private' or uid not in ADMIN_IDS: return
        args = m.text.split()
        if len(args) < 3: return await m.answer("/sys_give [user_id] [сумма]")
        target_uid = int(args[1])
        amount = int(args[2])
        await update_balance(ADMIN_CHAT_ID, target_uid, amount)
        await m.answer(f"✅ Выдано {fmt_money(amount)} игроку {target_uid}")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

async def init_cities():
    try:
        async with pool.acquire() as conn:
            for city in CITIES_LIST:
                await conn.execute("INSERT INTO cities (id, name, bonus_desc, bonus_type, bonus_value) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (id) DO NOTHING", city['id'], city['name'], city['desc'], city['bonus_type'], city['bonus_value'])
            print(f"🏙️ Инициализировано {len(CITIES_LIST)} городов")
    except Exception as e: print(f"❌ Ошибка инициализации городов: {e}")

async def get_player_city(cid, uid):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT city_id, moved_at FROM player_cities WHERE chat_id=$1 AND user_id=$2", cid, uid)
            if not row: return None
            city_id = row['city_id']
            for city in CITIES_LIST:
                if city['id'] == city_id:
                    city_copy = city.copy()
                    city_copy['moved_at'] = row['moved_at']
                    return city_copy
            return None
    except Exception: return None

async def set_player_city(cid, uid, city_id):
    async with pool.acquire() as conn:
        await conn.execute("""INSERT INTO player_cities (chat_id, user_id, city_id, moved_at) VALUES ($1, $2, $3, $4) ON CONFLICT (chat_id, user_id) DO UPDATE SET city_id=$3, moved_at=$4""", cid, uid, city_id, time.time())

async def get_city_treasury(cid, city_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT amount FROM city_treasury WHERE chat_id=$1 AND city_id=$2", cid, city_id)
            return row['amount'] if row else 0
    except Exception: return 0

async def update_city_treasury(cid, city_id, amount):
    async with pool.acquire() as conn:
        await conn.execute("""INSERT INTO city_treasury (chat_id, city_id, amount) VALUES ($1, $2, $3) ON CONFLICT (chat_id, city_id) DO UPDATE SET amount = city_treasury.amount + $3""", cid, city_id, amount)

async def update_state_treasury(cid, amount):
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT amount FROM state_treasury WHERE chat_id=$1", cid)
        if existing:
            new_amount = existing['amount'] + amount
            await conn.execute("UPDATE state_treasury SET amount=$1 WHERE chat_id=$2", new_amount, cid)
        else:
            await conn.execute("INSERT INTO state_treasury (chat_id, amount) VALUES ($1, $2)", cid, amount)

async def get_state_treasury(cid):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT amount FROM state_treasury WHERE chat_id=$1", cid)
        return row['amount'] if row else 0

async def get_mayor(cid, city_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM mayors WHERE chat_id=$1 AND city_id=$2 AND expires_at > $3", cid, city_id, time.time())
            return row
    except Exception: return None

async def get_current_election_id(cid, city_id):
    week_num = int(time.time() // 604800)
    return f"elec_{cid}_{city_id}_w{week_num}"

async def nominate_mayor(cid, uid, city_id):
    user = await get_user(cid, uid)
    if user['balance'] < MAYOR_ELECTION_FEE: return False, f"❌ Нужно {fmt_money(MAYOR_ELECTION_FEE)}"
    current_mayor = await get_mayor(cid, city_id)
    if current_mayor:
        days_left = int((current_mayor['expires_at'] - time.time()) / 86400)
        city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
        city_name = city['name'] if city else f"город #{city_id}"
        return False, f"❌ В {city_name} уже есть мэр! Срок: {days_left} дн."
    election_id = await get_current_election_id(cid, city_id)
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND user_id=$3 AND election_id=$4", cid, city_id, uid, election_id)
        if existing: return False, "❌ Уже выдвинут!"
        await update_balance(cid, uid, -MAYOR_ELECTION_FEE)
        await conn.execute("INSERT INTO mayor_candidates (chat_id, city_id, user_id, election_id) VALUES ($1,$2,$3,$4)", cid, city_id, uid, election_id)
        existing_start = await conn.fetchrow("SELECT * FROM mayor_elections_start WHERE chat_id=$1 AND city_id=$2 AND election_id=$3", cid, city_id, election_id)
        if not existing_start:
            await conn.execute("INSERT INTO mayor_elections_start (chat_id, city_id, election_id, started_at) VALUES ($1,$2,$3,$4)", cid, city_id, election_id, time.time())
    return True, f"✅ Выдвинут!\n💸 {fmt_money(MAYOR_ELECTION_FEE)}"

async def vote_for_mayor(cid, uid, city_id, candidate_num):
    user = await get_user(cid, uid)
    if user['balance'] < MAYOR_VOTE_COST: return False, f"❌ Голос стоит {MAYOR_VOTE_COST}"
    election_id = await get_current_election_id(cid, city_id)
    async with pool.acquire() as conn:
        candidates = await conn.fetch("SELECT id, user_id, votes FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3 ORDER BY id ASC", cid, city_id, election_id)
        if not candidates: return False, "❌ Нет кандидатов!"
        if candidate_num < 1 or candidate_num > len(candidates): return False, f"❌ 1-{len(candidates)}"
        target_candidate = candidates[candidate_num - 1]
        already_voted = await conn.fetchrow("SELECT * FROM mayor_votes WHERE chat_id=$1 AND city_id=$2 AND voter_id=$3 AND election_id=$4", cid, city_id, uid, election_id)
        if already_voted: return False, "❌ Уже голосовал!"
        if target_candidate['user_id'] == uid: return False, "❌ Нельзя за себя!"
        await update_balance(cid, uid, -MAYOR_VOTE_COST)
        await update_city_treasury(cid, city_id, MAYOR_VOTE_COST)
        await conn.execute("INSERT INTO mayor_votes (chat_id, city_id, voter_id, candidate_id, election_id) VALUES ($1,$2,$3,$4,$5)", cid, city_id, uid, target_candidate['id'], election_id)
        await conn.execute("UPDATE mayor_candidates SET votes = votes + 1 WHERE id=$1", target_candidate['id'])
    return True, f"✅ Голос принят!\n💸 {MAYOR_VOTE_COST}"

async def finalize_mayor_election(cid, city_id):
    election_id = await get_current_election_id(cid, city_id)
    async with pool.acquire() as conn:
        candidates = await conn.fetch("SELECT * FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3 ORDER BY votes DESC", cid, city_id, election_id)
        if not candidates:
            await conn.execute("DELETE FROM mayors WHERE chat_id=$1 AND city_id=$2", cid, city_id)
            return None
        winner = candidates[0]
        expires_at = time.time() + MAYOR_TERM_DAYS * 86400
        await conn.execute("""INSERT INTO mayors (chat_id, city_id, user_id, elected_at, expires_at, approval_rating) VALUES ($1,$2,$3,$4,$5,50) ON CONFLICT (chat_id, city_id) DO UPDATE SET user_id=$3, elected_at=$4, expires_at=$5, approval_rating=50""", cid, city_id, winner['user_id'], time.time(), expires_at)
        try: await update_balance(cid, winner['user_id'], MAYOR_ELECTION_FEE + MAYOR_WIN_BONUS)
        except Exception as e: print(f"Ошибка бонуса: {e}")
        await conn.execute("DELETE FROM mayor_votes WHERE chat_id=$1 AND city_id=$2 AND election_id=$3", cid, city_id, election_id)
        await conn.execute("DELETE FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3", cid, city_id, election_id)
    return {"user_id": winner['user_id'], "votes": winner['votes'], "bonus": MAYOR_WIN_BONUS}

async def get_current_federal_election_id(cid, role):
    week_num = int(time.time() // 604800)
    return f"federal_{cid}_{role}_w{week_num}"

async def nominate_federal(cid, uid, role):
    fee = PRESIDENT_ELECTION_FEE if role == 'president' else PRIME_MINISTER_ELECTION_FEE
    user = await get_user(cid, uid)
    if user['balance'] < fee: return False, f"❌ Нужно {fmt_money(fee)}"
    current_official = await get_federal_role(cid, role)
    if current_official:
        days_left = int((current_official['expires_at'] - time.time()) / 86400)
        role_name = "Президент" if role == 'president' else "Премьер"
        return False, f"❌ {role_name} у власти! {days_left} дн."
    election_id = await get_current_federal_election_id(cid, role)
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND user_id=$3 AND election_id=$4", cid, role, uid, election_id)
        if existing: return False, "❌ Уже выдвинут!"
        await update_balance(cid, uid, -fee)
        await conn.execute("INSERT INTO federal_candidates (chat_id, role, user_id, election_id) VALUES ($1,$2,$3,$4)", cid, role, uid, election_id)
        existing_start = await conn.fetchrow("SELECT * FROM federal_elections_start WHERE chat_id=$1 AND role=$2 AND election_id=$3", cid, role, election_id)
        if not existing_start:
            await conn.execute("INSERT INTO federal_elections_start (chat_id, role, election_id, started_at) VALUES ($1,$2,$3,$4)", cid, role, election_id, time.time())
    role_name = "Президент" if role == 'president' else "Премьер"
    return True, f"✅ Выдвинут в {role_name}!\n💸 {fmt_money(fee)}"

async def vote_federal(cid, uid, role, candidate_num):
    cost = PRESIDENT_VOTE_COST if role == 'president' else PRIME_MINISTER_VOTE_COST
    user = await get_user(cid, uid)
    if user['balance'] < cost: return False, f"❌ Голос стоит {fmt_money(cost)}"
    election_id = await get_current_federal_election_id(cid, role)
    async with pool.acquire() as conn:
        candidates = await conn.fetch("SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND election_id=$3 ORDER BY id ASC", cid, role, election_id)
        if not candidates: return False, "❌ Нет кандидатов!"
        if candidate_num < 1 or candidate_num > len(candidates): return False, f"❌ 1-{len(candidates)}"
        target_candidate = candidates[candidate_num - 1]
        if target_candidate['user_id'] == uid: return False, "❌ Нельзя за себя!"
        already_voted = await conn.fetchrow("SELECT * FROM federal_votes WHERE chat_id=$1 AND role=$2 AND voter_id=$3 AND election_id=$4", cid, role, uid, election_id)
        if already_voted: return False, "❌ Уже голосовал!"
        await update_balance(cid, uid, -cost)
        await update_state_treasury(cid, cost)
        await conn.execute("INSERT INTO federal_votes (chat_id, role, voter_id, candidate_id, election_id) VALUES ($1,$2,$3,$4,$5)", cid, role, uid, target_candidate['id'], election_id)
        await conn.execute("UPDATE federal_candidates SET votes = votes + 1 WHERE id=$1", target_candidate['id'])
    return True, f"✅ Голос принят!\n💸 {fmt_money(cost)}"

async def finalize_federal_election(cid, role):
    election_id = await get_current_federal_election_id(cid, role)
    async with pool.acquire() as conn:
        candidates = await conn.fetch("SELECT * FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND election_id=$3 ORDER BY votes DESC", cid, role, election_id)
        if not candidates:
            await conn.execute("DELETE FROM federal_roles WHERE chat_id=$1 AND role=$2", cid, role)
            return None
        winner = candidates[0]
        term_days = PRESIDENT_TERM_DAYS if role == 'president' else PRIME_MINISTER_TERM_DAYS
        win_bonus = PRESIDENT_WIN_BONUS if role == 'president' else PRIME_MINISTER_WIN_BONUS
        election_fee = PRESIDENT_ELECTION_FEE if role == 'president' else PRIME_MINISTER_ELECTION_FEE
        expires_at = time.time() + term_days * 86400
        await conn.execute("""INSERT INTO federal_roles (chat_id, role, user_id, elected_at, expires_at, approval_rating) VALUES ($1,$2,$3,$4,$5,50) ON CONFLICT (chat_id, role) DO UPDATE SET user_id=$3, elected_at=$4, expires_at=$5, approval_rating=50""", cid, role, winner['user_id'], time.time(), expires_at)
        try: await update_balance(cid, winner['user_id'], election_fee + win_bonus)
        except Exception as e: print(f"Ошибка бонуса: {e}")
        await conn.execute("DELETE FROM federal_votes WHERE chat_id=$1 AND role=$2 AND election_id=$3", cid, role, election_id)
        await conn.execute("DELETE FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND election_id=$3", cid, role, election_id)
    return {"user_id": winner['user_id'], "votes": winner['votes'], "bonus": win_bonus}

async def get_federal_role(cid, role):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM federal_roles WHERE chat_id=$1 AND role=$2 AND expires_at > $3", cid, role, time.time())
            return row
    except Exception: return None

async def is_mayor(cid, uid, city_id):
    mayor = await get_mayor(cid, city_id)
    if mayor and mayor['user_id'] == uid: return True
    return False

async def get_active_decree(cid, city_id, decree_type):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM city_decrees WHERE chat_id=$1 AND city_id=$2 AND decree_type=$3 AND active_until > $4", cid, city_id, decree_type, time.time())
            return row
    except Exception: return None

async def apply_income_tax(cid, uid, gross_income):
    tax_cut = await get_active_federal_decree(cid, 'president', 'tax_cut')
    tax_boost_president = await get_active_federal_decree(cid, 'president', 'tax_boost')
    tax_boost_prime = await get_active_federal_decree(cid, 'prime_minister', 'tax_boost')
    if tax_cut: tax_rate = 2
    elif tax_boost_president or tax_boost_prime: tax_rate = 10
    else: tax_rate = TAX_RATE_PERCENT
    tax_amount = int(gross_income * tax_rate / 100)
    net_income = gross_income - tax_amount
    player_city = await get_player_city(cid, uid)
    if player_city:
        await update_city_treasury(cid, player_city['id'], tax_amount)
        receiver = f"казну г. {player_city['name']}"
    else:
        await update_state_treasury(cid, tax_amount)
        receiver = "фед. казну"
    return net_income, tax_amount, receiver, tax_rate

async def apply_business_tax(cid, uid, gross_profit):
    tax_cut = await get_active_federal_decree(cid, 'president', 'tax_cut')
    tax_boost_president = await get_active_federal_decree(cid, 'president', 'tax_boost')
    tax_boost_prime = await get_active_federal_decree(cid, 'prime_minister', 'tax_boost')
    if tax_cut: tax_rate = 2
    elif tax_boost_president or tax_boost_prime: tax_rate = 10
    else: tax_rate = TAX_RATE_PERCENT
    tax_amount = int(gross_profit * tax_rate / 100)
    net_profit = gross_profit - tax_amount
    city_tax = tax_amount // 2
    state_tax = tax_amount - city_tax
    player_city = await get_player_city(cid, uid)
    if player_city:
        await update_city_treasury(cid, player_city['id'], city_tax)
        await update_state_treasury(cid, state_tax)
    else:
        await update_state_treasury(cid, tax_amount)
    return net_profit, tax_amount, tax_rate

async def is_federal_official(cid, uid, role):
    official = await get_federal_role(cid, role)
    if official and official['user_id'] == uid: return True
    return False

async def get_active_federal_decree(cid, role, decree_type):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM federal_decrees WHERE chat_id=$1 AND role=$2 AND decree_type=$3 AND active_until > $4", cid, role, decree_type, time.time())
            return row
    except Exception: return None

async def create_federal_decree(cid, uid, role, decree_type):
    if not await is_federal_official(cid, uid, role):
        role_name = "Президент" if role == 'president' else "Премьер"
        return False, f"❌ Только {role_name}!"
    existing = await get_active_federal_decree(cid, role, decree_type)
    if existing:
        hours_left = int((existing['active_until'] - time.time()) / 3600)
        return False, f"⚠️ Уже активен! {hours_left} ч."
    duration = PRESIDENT_DECREE_DURATION if role == 'president' else PRIME_MINISTER_DECREE_DURATION
    active_until = time.time() + (duration * 3600)
    async with pool.acquire() as conn:
        await conn.execute("""INSERT INTO federal_decrees (chat_id, role, decree_type, active_until) VALUES ($1,$2,$3,$4) ON CONFLICT (chat_id, role, decree_type) DO UPDATE SET active_until = $4""", cid, role, decree_type, active_until)
    role_name = "Президент" if role == 'president' else "Премьер"
    return True, f"✅ Указ {role_name}!\n⏰ {duration} часов."

def get_federal_decree_name(decree_type):
    names = {
        'amnesty': '🕊️ Амнистия',
        'tax_cut': '📉 Снижение налога до 2%',
        'tax_boost': '📈 Повышение до 10%',
        'emergency': '🚨 ЧП',
        'subsidy': '💰 Субсидии (+10%)',
        'investment': '🏗️ Инвестиции (+5000)',
    }
    return names.get(decree_type, 'Неизвестный')

@dp.message(Command("president_nominate"))
async def cmd_president_nominate(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        success, msg = await nominate_federal(cid, uid, 'president')
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("president_decree"))
async def cmd_president_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if not await is_federal_official(cid, uid, 'president'): return await m.answer("❌ Только Президент!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("🏛️ <b>УКАЗЫ</b>\n\n/president_decree amnesty\n/president_decree tax_cut\n/president_decree tax_boost\n/president_decree emergency", parse_mode="HTML")
    decree = args[1].lower()
    decree_map = {'amnesty': 'amnesty', 'tax_cut': 'tax_cut', 'tax_boost': 'tax_boost', 'emergency': 'emergency'}
    decree_type = decree_map.get(decree)
    if not decree_type: return await m.answer("❌ Неизвестный указ!")
    if decree_type == 'amnesty':
        try:
            async with pool.acquire() as conn:
                jailed = await conn.fetch("SELECT user_id FROM jail WHERE chat_id=$1 AND release_time > $2", cid, time.time())
                count = len(jailed)
                if count > 0:
                    await conn.execute("DELETE FROM jail WHERE chat_id=$1 AND release_time > $2", cid, time.time())
            return await m.answer(f"🕊️ <b>АМНИСТИЯ!</b>\n\nОсвобождено: <b>{count}</b>", parse_mode="HTML")
        except Exception as e: return await m.answer(f"❌ Ошибка: {str(e)}")
    success, msg = await create_federal_decree(cid, uid, 'president', decree_type)
    await m.answer(msg, parse_mode="HTML")

@dp.message(Command("president_decrees"))
async def cmd_president_decrees(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    try:
        async with pool.acquire() as conn:
            decrees = await conn.fetch("SELECT * FROM federal_decrees WHERE chat_id=$1 AND role='president' AND active_until > $2", cid, time.time())
    except Exception: return await m.answer("❌ Ошибка")
    if not decrees: return await m.answer("🏛️ <b>Указы Президента</b>\n\n❌ Нет активных")
    t = "🏛️ <b>Активные указы:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {get_federal_decree_name(d['decree_type'])}\n  ⏰ {hours_left} ч.\n\n"
    return await m.answer(t, parse_mode="HTML")

@dp.message(Command("prime_decree"))
async def cmd_prime_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if not await is_federal_official(cid, uid, 'prime_minister'): return await m.answer("❌ Только Премьер!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("💼 <b>УКАЗЫ</b>\n\n/prime_decree subsidy\n/prime_decree investment\n/prime_decree tax_cut\n/prime_decree tax_boost", parse_mode="HTML")
    decree = args[1].lower()
    decree_map = {'subsidy': 'subsidy', 'investment': 'investment', 'tax_cut': 'tax_cut', 'tax_boost': 'tax_boost'}
    decree_type = decree_map.get(decree)
    if not decree_type: return await m.answer("❌ Неизвестный указ!")
    if decree_type == 'investment':
        try:
            async with pool.acquire() as conn:
                cities = await conn.fetch("SELECT DISTINCT city_id FROM player_cities WHERE chat_id=$1", cid)
                for city_row in cities:
                    await update_city_treasury(cid, city_row['city_id'], 5000)
            return await m.answer(f"🏗️ <b>ИНВЕСТИЦИИ!</b>\n\nКаждому городу +<b>5000</b>\nГородов: <b>{len(cities)}</b>", parse_mode="HTML")
        except Exception as e: return await m.answer(f"❌ Ошибка: {str(e)}")
    success, msg = await create_federal_decree(cid, uid, 'prime_minister', decree_type)
    await m.answer(msg, parse_mode="HTML")

@dp.message(Command("prime_decrees"))
async def cmd_prime_decrees(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    try:
        async with pool.acquire() as conn:
            decrees = await conn.fetch("SELECT * FROM federal_decrees WHERE chat_id=$1 AND role='prime_minister' AND active_until > $2", cid, time.time())
    except Exception: return await m.answer("❌ Ошибка")
    if not decrees: return await m.answer("💼 <b>Указы Премьера</b>\n\n❌ Нет активных")
    t = "💼 <b>Активные указы:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {get_federal_decree_name(d['decree_type'])}\n  ⏰ {hours_left} ч.\n\n"
    return await m.answer(t, parse_mode="HTML")

@dp.message(Command("mayor_report"))
async def cmd_mayor_report(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    mayor = await get_mayor(cid, player_city['id'])
    if not mayor or mayor['user_id'] != uid: return await m.answer("❌ Только мэр!")
    args = m.text.split(maxsplit=1)
    if len(args) < 2:
        return await m.answer("📊 <b>ОТЧЁТ</b>\n\n/mayor_report [описание]\n\nПример: /mayor_report Построен парк", parse_mode="HTML")
    description = args[1]
    async with pool.acquire() as conn:
        report = await conn.fetchrow("""SELECT * FROM mayor_reports WHERE chat_id=$1 AND city_id=$2 AND mayor_id=$3 AND status='pending' ORDER BY created_at DESC LIMIT 1""", cid, player_city['id'], uid)
        if not report: return await m.answer("❌ Нет заданий!")
        if time.time() > report['report_deadline']: return await m.answer("⏰ Срок истёк!")
        await conn.execute("UPDATE mayor_reports SET status='submitted', budget_spent=budget_allocated WHERE id=$1", report['id'])
    msg = f"📊 <b>ОТЧЁТ СДАН!</b>\n\n🏙️ {player_city['emoji']} {player_city['name']}\n💰 {fmt_money(report['budget_allocated'])}\n📋 {description}\n\n⏳ Ожидает проверки..."
    await bot.send_message(cid, msg, parse_mode="HTML")
    await m.answer("✅ Отправлен!")

@dp.message(Command("president_check_mayor"))
async def cmd_president_check_mayor(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    president = await get_federal_role(cid, 'president')
    if not president or president['user_id'] != uid: return await m.answer("❌ Только Президент!")
    args = m.text.split()
    if len(args) < 2:
        cities_list = ", ".join([str(c['id']) for c in CITIES_LIST])
        return await m.answer(f"⚖️ <b>ПРОВЕРКА</b>\n\n/president_check_mayor [город_id] [approve/reject]\n\nГорода: {cities_list}", parse_mode="HTML")
    try: city_id = int(args[1])
    except ValueError: return await m.answer("❌ Число!")
    action = args[2].lower() if len(args) > 2 else None
    if action not in ['approve', 'reject']: return await m.answer("❌ approve или reject!")
    city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
    if not city: return await m.answer(f"❌ Город не найден!")
    async with pool.acquire() as conn:
        report = await conn.fetchrow("""SELECT * FROM mayor_reports WHERE chat_id=$1 AND city_id=$2 AND status IN ('pending','submitted') ORDER BY created_at DESC LIMIT 1""", cid, city_id)
        if not report: return await m.answer(f"✅ В {city['emoji']} {city['name']} нет отчётов!")
        mayor_name = ""
        try: mayor_name = (await bot.get_chat_member(cid, report['mayor_id'])).user.full_name
        except: mayor_name = f"User{report['mayor_id']}"
        if action == 'approve':
            remaining = report['budget_allocated'] - report['budget_spent']
            if remaining > 0: await update_city_treasury(cid, city_id, remaining)
            await conn.execute("""UPDATE mayors SET approval_rating = LEAST(100, approval_rating + 10) WHERE chat_id=$1 AND city_id=$2""", cid, city_id)
            await conn.execute("UPDATE mayor_reports SET status='approved' WHERE id=$1", report['id'])
            msg = f"✅ <b>ОДОБРЕН!</b>\n\n🏙️ {city['emoji']} {city['name']}\n👤 {mayor_name}\n💰 Возврат: {fmt_money(remaining)}\n📈 Рейтинг: +10%"
            await bot.send_message(cid, msg, parse_mode="HTML")
            await m.answer("✅ Одобрено!")
        elif action == 'reject':
            penalty_type = random.choice(['fine', 'jail'])
            if penalty_type == 'fine':
                fine_amount = int(report['budget_allocated'] * 0.5)
                await update_balance(cid, report['mayor_id'], -fine_amount)
                msg = f"❌ <b>ОТКЛОНЁН!</b>\n\n🏙️ {city['emoji']} {city['name']}\n👤 {mayor_name}\n💸 Штраф: {fmt_money(fine_amount)}\n📉 Рейтинг: -15%"
                await conn.execute("""UPDATE mayors SET approval_rating = GREATEST(0, approval_rating - 15) WHERE chat_id=$1 AND city_id=$2""", cid, city_id)
            else:
                jail_hours = 4
                await send_to_jail(cid, report['mayor_id'], jail_hours)
                msg = f"🔒 <b>В ТЮРЬМУ!</b>\n\n🏙️ {city['emoji']} {city['name']}\n👤 {mayor_name} на {jail_hours} ч\n📉 Рейтинг: -25%"
                await conn.execute("""UPDATE mayors SET approval_rating = GREATEST(0, approval_rating - 25) WHERE chat_id=$1 AND city_id=$2""", cid, city_id)
            await conn.execute("UPDATE mayor_reports SET status='rejected' WHERE id=$1", report['id'])
            await bot.send_message(cid, msg, parse_mode="HTML")
            await m.answer("✅ Наказание применено!")

@dp.message(Command("president_vote"))
async def cmd_president_vote(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2:
            election_id = await get_current_federal_election_id(cid, 'president')
            async with pool.acquire() as conn:
                candidates = await conn.fetch("SELECT user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='president' AND election_id=$2 ORDER BY id ASC", cid, election_id)
            if not candidates: return await m.answer("🏛️ <b>Выборы Президента</b>\n\n❌ Нет кандидатов.\n/president_nominate", parse_mode="HTML")
            t = "🏛️ <b>Кандидаты:</b>\n\n"
            for i, c in enumerate(candidates, 1):
                try: name = (await bot.get_chat_member(cid, c['user_id'])).user.full_name
                except: name = f"User{c['user_id']}"
                t += f"{i}. {name} ({c['votes']})\n"
            t += f"\n💰 {PRESIDENT_VOTE_COST}\n/president_vote [номер]"
            return await m.answer(t, parse_mode="HTML")
        try: candidate_num = int(args[1])
        except ValueError: return await m.answer("❌ Число!")
        success, msg = await vote_federal(cid, uid, 'president', candidate_num)
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("president_finalize"))
async def cmd_president_finalize(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        result = await finalize_federal_election(cid, 'president')
        if result is None: return await m.answer("🏛️ <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
        return await m.answer(f"🎉 <b>НОВЫЙ ПРЕЗИДЕНТ!</b>\n\n👤 ID: {result['user_id']}\n🗳️ {result['votes']}\n💰 +{result['bonus']}\n⏰ {PRESIDENT_TERM_DAYS} дн.", parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("prime_nominate"))
async def cmd_prime_nominate(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        success, msg = await nominate_federal(cid, uid, 'prime_minister')
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("prime_vote"))
async def cmd_prime_vote(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2:
            election_id = await get_current_federal_election_id(cid, 'prime_minister')
            async with pool.acquire() as conn:
                candidates = await conn.fetch("SELECT user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='prime_minister' AND election_id=$2 ORDER BY id ASC", cid, election_id)
            if not candidates: return await m.answer("💼 <b>Выборы Премьера</b>\n\n❌ Нет кандидатов.\n/prime_nominate", parse_mode="HTML")
            t = "💼 <b>Кандидаты:</b>\n\n"
            for i, c in enumerate(candidates, 1):
                try: name = (await bot.get_chat_member(cid, c['user_id'])).user.full_name
                except: name = f"User{c['user_id']}"
                t += f"{i}. {name} ({c['votes']})\n"
            t += f"\n💰 {PRIME_MINISTER_VOTE_COST}\n/prime_vote [номер]"
            return await m.answer(t, parse_mode="HTML")
        try: candidate_num = int(args[1])
        except ValueError: return await m.answer("❌ Число!")
        success, msg = await vote_federal(cid, uid, 'prime_minister', candidate_num)
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("prime_finalize"))
async def cmd_prime_finalize(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        result = await finalize_federal_election(cid, 'prime_minister')
        if result is None: return await m.answer("💼 <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
        return await m.answer(f"🎉 <b>НОВЫЙ ПРЕМЬЕР!</b>\n\n👤 ID: {result['user_id']}\n🗳️ {result['votes']}\n💰 +{result['bonus']}\n⏰ {PRIME_MINISTER_TERM_DAYS} дн.", parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("debt_give"))
async def cmd_debt_give(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 3:
        return await m.answer(f"📜 <b>ДАТЬ В ДОЛГ</b>\n\nОтветь на сообщение:\n/debt_give сумма дни\n\nПример: /debt_give 50000 3\nКомиссия: {DEBT_FEE_PERCENT}%", parse_mode="HTML")
    if not m.reply_to_message: return await m.answer("⚠️ Ответь на сообщение!")
    borrower_id = m.reply_to_message.from_user.id
    if borrower_id == uid: return await m.answer("❌ Нельзя себе!")
    if await is_in_jail(cid, borrower_id): return await m.answer("🔒 В тюрьме!")
    try:
        amount = int(args[1])
        days = int(args[2])
    except (ValueError, IndexError): return await m.answer("❌ Числа!")
    if amount < DEBT_MIN_AMOUNT: return await m.answer(f"❌ Мин: {fmt_money(DEBT_MIN_AMOUNT)}")
    if days < DEBT_MIN_DAYS or days > DEBT_MAX_DAYS: return await m.answer(f"❌ {DEBT_MIN_DAYS}-{DEBT_MAX_DAYS} дн.")
    fee = int(amount * DEBT_FEE_PERCENT / 100)
    total = amount + fee
    lender = await get_user(cid, uid)
    if lender['balance'] < total: return await m.answer(f"❌ Нужно {fmt_money(total)}\nУ вас: {fmt_money(lender['balance'])}", parse_mode="HTML")
    deadline = time.time() + days * 86400
    async with pool.acquire() as conn:
        await update_balance(cid, uid, -total)
        await update_balance(cid, borrower_id, amount)
        await conn.execute("INSERT INTO debts (chat_id, lender_id, borrower_id, amount, fee, created_at, deadline) VALUES ($1,$2,$3,$4,$5,$6,$7)", cid, uid, borrower_id, amount, fee, time.time(), deadline)
    try: borrower_name = (await bot.get_chat_member(cid, borrower_id)).user.full_name
    except: borrower_name = f"User{borrower_id}"
    await m.answer(f"📜 <b>РАСПИСКА</b>\n\n👤 {borrower_name}\n💰 {fmt_money(amount)}\n📅 {days} дн.\n🏦 Комиссия: {fmt_money(fee)}\n📤 Списано: {fmt_money(total)}\n\n⚠️ Коллекторы!", parse_mode="HTML")
    await bot.send_message(cid, f"📜 <b>ВЫ ВЗЯЛИ В ДОЛГ!</b>\n\n👤 {m.from_user.full_name}\n💰 {fmt_money(amount)}\n📅 {days} дн.\n⚠️ +{DEBT_PENALTY_PERCENT}% при просрочке!\n\n/debt_return", parse_mode="HTML")

@dp.message(Command("debt_return"))
async def cmd_debt_return(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    async with pool.acquire() as conn:
        debt = await conn.fetchrow("SELECT * FROM debts WHERE borrower_id=$1 AND status='active' ORDER BY deadline ASC LIMIT 1", uid)
        if not debt: return await m.answer("✅ Нет долгов!")
        user = await get_user(cid, uid)
        if user['balance'] < debt['amount']: return await m.answer(f"❌ Нужно {fmt_money(debt['amount'])}")
        await update_balance(cid, uid, -debt['amount'])
        await update_balance(cid, debt['lender_id'], debt['amount'])
        await conn.execute("UPDATE debts SET status='returned' WHERE id=$1", debt['id'])
    await m.answer(f"✅ <b>ДОЛГ ПОГАШЕН!</b>\n\n💰 {fmt_money(debt['amount'])}\n📊 {fmt_money((await get_user(cid, uid))['balance'])}", parse_mode="HTML")

@dp.message(Command("debt_list"))
async def cmd_debt_list(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    async with pool.acquire() as conn:
        i_owe = await conn.fetch("SELECT * FROM debts WHERE borrower_id=$1 AND status='active'", uid)
        owed_me = await conn.fetch("SELECT * FROM debts WHERE lender_id=$1 AND status='active'", uid)
    
    t = "📋 <b>ДОЛГИ</b>\n\n"
    
    if i_owe:
        t += "📤 <b>Я должен:</b>\n"
        for d in i_owe:
            try:
                lender = await bot.get_chat_member(cid, d['lender_id'])
                lender_name = lender.user.full_name
            except:
                lender_name = f"User{d['lender_id']}"
            t += f"• {lender_name}: {fmt_money(d['amount'])}\n"
    else:
        t += "✅ Я никому не должен\n"
    
    if owed_me:
        t += "\n📥 <b>Мне должны:</b>\n"
        for d in owed_me:
            try:
                borrower = await bot.get_chat_member(cid, d['borrower_id'])
                borrower_name = borrower.user.full_name
            except:
                borrower_name = f"User{d['borrower_id']}"
            t += f"• {borrower_name}: {fmt_money(d['amount'])}\n"
    else:
        t += "\n✅ Мне никто не должен"
    
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("mayor_decree"))
async def cmd_mayor_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    if not await is_mayor(cid, uid, player_city['id']): return await m.answer("❌ Только мэр!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer(f"🏛️ <b>УКАЗЫ МЭРА</b>\n\n/mayor_decree work (+20% работа, 5к)\n/mayor_decree tools (-30% инструменты, 3к)\n/mayor_decree business (+15% бизнес, 8к)\n/mayor_decree cars (-25% авто, 4к)\n/mayor_decree event (праздник, 10к)\n\n💰 Казна: {await get_city_treasury(cid, player_city['id'])}", parse_mode="HTML")
    decree = args[1].lower()
    decree_map = {'work': 'work_bonus', 'tools': 'tool_discount', 'business': 'business_bonus', 'cars': 'car_discount', 'event': 'city_event'}
    decree_type = decree_map.get(decree)
    if not decree_type: return await m.answer("❌ Неизвестный указ!")
    success, msg = await create_decree(cid, player_city['id'], uid, decree_type)
    await m.answer(msg, parse_mode="HTML")

@dp.message(Command("city_decrees"))
async def cmd_city_decrees(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    try:
        async with pool.acquire() as conn:
            decrees = await conn.fetch("SELECT * FROM city_decrees WHERE chat_id=$1 AND city_id=$2 AND active_until > $3", cid, player_city['id'], time.time())
    except Exception: return await m.answer("❌ Ошибка")
    if not decrees: return await m.answer(f"🏛️ <b>{player_city['emoji']} {player_city['name']}</b>\n\n❌ Нет указов")
    t = f"🏛️ <b>Указы {player_city['emoji']} {player_city['name']}:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {get_decree_name(d['decree_type'])}\n  ⏰ {hours_left} ч.\n\n"
    return await m.answer(t, parse_mode="HTML")

@dp.message(Command("city"))
async def cmd_city(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("🏙️ <b>ГОРОДА</b>\n\n/city list\n/city choose [город]\n/city move [город]\n/city info\n/city residents", parse_mode="HTML")
    subcmd = args[1].lower()
    if subcmd == "list":
        t = "🏙️ <b>ГОРОДА</b>\n\n"
        for city in CITIES_LIST:
            t += f"{city['emoji']} <b>{city['name']}</b>\n   {city['desc']}\n\n"
        t += "━━━━━━━━━━━━━━━━━━━━\n/city choose [название]"
        return await m.answer(t, parse_mode="HTML")
    if subcmd == "info":
        try:
            player_city = await get_player_city(cid, uid)
            if not player_city: return await m.answer("❌ Нет города!\n/city choose [город]")
            mayor = await get_mayor(cid, player_city['id'])
            treasury = await get_city_treasury(cid, player_city['id'])
            t = f"{player_city['emoji']} <b>{player_city['name']}</b>\n\n📊 {player_city['desc']}\n💰 Казна: {treasury}\n\n"
            if mayor:
                try: mayor_name = (await bot.get_chat_member(cid, mayor['user_id'])).user.full_name
                except: mayor_name = f"User{mayor['user_id']}"
                days_left = int((mayor['expires_at'] - time.time()) / 86400)
                t += f"🏛️ Мэр: {mayor_name}\n📊 Рейтинг: {mayor['approval_rating']}%\n⏰ {days_left} дн."
            else: t += "🏛️ Мэр: ВАКАНТНО"
            return await m.answer(t, parse_mode="HTML")
        except Exception as e: return await m.answer(f"❌ Ошибка: {str(e)}")
    if subcmd == "choose":
        if len(args) < 3: return await m.answer("⚠️ /city choose Москва")
        city_name = " ".join(args[2:])
        existing = await get_player_city(cid, uid)
        if existing: return await m.answer(f"❌ Уже в <b>{existing['name']}</b>!\n/city move", parse_mode="HTML")
        city = next((c for c in CITIES_LIST if c['name'].lower() == city_name.lower()), None)
        if not city: return await m.answer(f"❌ Не найден! /city list")
        await set_player_city(cid, uid, city['id'])
        return await m.answer(f"🎉 <b>Добро пожаловать в {city['emoji']} {city['name']}!</b>\n\n📊 {city['desc']}", parse_mode="HTML")
    if subcmd == "move":
        try:
            if len(args) < 3: return await m.answer("⚠️ /city move Москва")
            city_name = " ".join(args[2:])
            existing = await get_player_city(cid, uid)
            if not existing: return await m.answer("❌ Сначала /city choose")
            cooldown_left = CITY_MOVE_COOLDOWN - (time.time() - existing['moved_at'])
            if cooldown_left > 0:
                days = int(cooldown_left / 86400)
                hours = int((cooldown_left % 86400) / 3600)
                return await m.answer(f"⏳ Через {days} дн. {hours} ч.")
            city = next((c for c in CITIES_LIST if c['name'].lower() == city_name.lower()), None)
            if not city: return await m.answer(f"❌ Не найден! /city list")
            if city['id'] == existing['id']: return await m.answer("❌ Уже здесь!")
            user = await get_user(cid, uid)
            if user['balance'] < CITY_MOVE_COST: return await m.answer(f"❌ Нужно {CITY_MOVE_COST}")
            await update_balance(cid, uid, -CITY_MOVE_COST)
            await set_player_city(cid, uid, city['id'])
            return await m.answer(f"🚚 <b>ПЕРЕЕЗД!</b>\n\n{city['emoji']} {city['name']}\n📊 {city['desc']}", parse_mode="HTML")
        except Exception as e: return await m.answer(f"❌ Ошибка: {str(e)}")
    if subcmd == "residents":
        player_city = await get_player_city(cid, uid)
        if not player_city: return await m.answer("❌ Нет города!")
        try:
            async with pool.acquire() as conn:
                residents = await conn.fetch("SELECT user_id FROM player_cities WHERE chat_id=$1 AND city_id=$2 LIMIT 20", cid, player_city['id'])
        except Exception: return await m.answer("❌ Ошибка")
        if not residents: return await m.answer("🏙️ Никого нет!")
        t = f"{player_city['emoji']} <b>Жители {player_city['name']}:</b>\n\n"
        for i, r in enumerate(residents[:20], 1):
            try: name = (await bot.get_chat_member(cid, r['user_id'])).user.full_name
            except: name = f"User{r['user_id']}"
            t += f"{i}. {name}\n"
        t += f"\n📊 Всего: {len(residents)}"
        return await m.answer(t, parse_mode="HTML")
    await m.answer("❓ /city")

@dp.message(Command("mayor_nominate"))
async def cmd_mayor_nominate(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        player_city = await get_player_city(cid, uid)
        if not player_city: return await m.answer("❌ Нет города! /city choose")
        success, msg = await nominate_mayor(cid, uid, player_city['id'])
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("mayor_vote"))
async def cmd_mayor_vote(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2:
            player_city = await get_player_city(cid, uid)
            if not player_city: return await m.answer("❌ Нет города!")
            election_id = await get_current_election_id(cid, player_city['id'])
            async with pool.acquire() as conn:
                candidates = await conn.fetch("SELECT user_id, votes FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3 ORDER BY id ASC", cid, player_city['id'], election_id)
            if not candidates: return await m.answer(f"🏛️ <b>Выборы в {player_city['emoji']} {player_city['name']}</b>\n\n❌ Нет кандидатов.\n/mayor_nominate", parse_mode="HTML")
            t = f"🏛️ <b>Кандидаты {player_city['emoji']} {player_city['name']}:</b>\n\n"
            for i, c in enumerate(candidates, 1):
                try: name = (await bot.get_chat_member(cid, c['user_id'])).user.full_name
                except: name = f"User{c['user_id']}"
                t += f"{i}. {name} ({c['votes']})\n"
            t += f"\n💰 {MAYOR_VOTE_COST}\n/mayor_vote [номер]"
            return await m.answer(t, parse_mode="HTML")
        try: candidate_num = int(args[1])
        except ValueError: return await m.answer("❌ Число!")
        player_city = await get_player_city(cid, uid)
        if not player_city: return await m.answer("❌ Нет города!")
        success, msg = await vote_for_mayor(cid, uid, player_city['id'], candidate_num)
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("mayor_finalize"))
async def cmd_mayor_finalize(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        player_city = await get_player_city(cid, uid)
        if not player_city: return await m.answer("❌ Нет города!")
        result = await finalize_mayor_election(cid, player_city['id'])
        if result is None: return await m.answer(f"🏛️ <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
        return await m.answer(f"🎉 <b>НОВЫЙ МЭР!</b>\n\n🏛️ {player_city['emoji']} {player_city['name']}\n👤 ID: {result['user_id']}\n🗳️ {result['votes']}\n💰 +{result['bonus']}\n⏰ {MAYOR_TERM_DAYS} дн.\n\n/city info", parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message()
async def auto_register(m: Message):
    if m.chat.type not in ['group', 'supergroup']: return
    await get_user(m.chat.id, m.from_user.id)

@dp.message(F.new_chat_members)
async def on_user_join(m: Message):
    cid = m.chat.id
    for user in m.new_chat_members:
        if user.is_bot:
            if user.id == int(API_TOKEN.split(':')[0]): await m.answer("👋 Привет! /start")
            continue
        await get_user(cid, user.id)
        await save_username(cid, user.id, user.full_name)

# ═══════════════════════════════════════════
# ПОЛИТИЧЕСКАЯ СИСТЕМА
# ═══════════════════════════════════════════

# Функции городов
async def init_cities():
    try:
        async with pool.acquire() as conn:
            for city in CITIES_LIST:
                await conn.execute(
                    """INSERT INTO cities (id, name, bonus_desc, bonus_type, bonus_value)
                    VALUES ($1, $2, $3, $4, $5) ON CONFLICT (id) DO NOTHING""",
                    city['id'], city['name'], city['desc'], city['bonus_type'], city['bonus_value']
                )
            print(f"🏙️ Инициализировано {len(CITIES_LIST)} городов")
    except Exception as e:
        print(f"❌ Ошибка инициализации городов: {e}")

async def get_player_city(cid, uid):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT city_id, moved_at FROM player_cities WHERE chat_id=$1 AND user_id=$2",
                cid, uid
            )
            if not row:
                return None
            city_id = row['city_id']
            for city in CITIES_LIST:
                if city['id'] == city_id:
                    city_copy = city.copy()
                    city_copy['moved_at'] = row['moved_at']
                    return city_copy
            return None
    except Exception:
        return None

async def set_player_city(cid, uid, city_id):
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO player_cities (chat_id, user_id, city_id, moved_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (chat_id, user_id) DO UPDATE SET city_id=$3, moved_at=$4""",
            cid, uid, city_id, time.time()
        )

async def get_city_treasury(cid, city_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT amount FROM city_treasury WHERE chat_id=$1 AND city_id=$2",
                cid, city_id
            )
            return row['amount'] if row else 0
    except Exception:
        return 0

async def update_city_treasury(cid, city_id, amount):
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO city_treasury (chat_id, city_id, amount) VALUES ($1, $2, $3)
            ON CONFLICT (chat_id, city_id) DO UPDATE SET amount = city_treasury.amount + $3""",
            cid, city_id, amount
        )

async def update_state_treasury(cid, amount):
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT amount FROM state_treasury WHERE chat_id=$1", cid
        )
        if existing:
            new_amount = existing['amount'] + amount
            await conn.execute(
                "UPDATE state_treasury SET amount=$1 WHERE chat_id=$2",
                new_amount, cid
            )
        else:
            await conn.execute(
                "INSERT INTO state_treasury (chat_id, amount) VALUES ($1, $2)",
                cid, amount
            )

async def get_state_treasury(cid):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT amount FROM state_treasury WHERE chat_id=$1", cid
        )
        return row['amount'] if row else 0

async def get_mayor(cid, city_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mayors WHERE chat_id=$1 AND city_id=$2 AND expires_at > $3",
                cid, city_id, time.time()
            )
            return row
    except Exception:
        return None

async def get_current_election_id(cid, city_id):
    week_num = int(time.time() // 604800)
    return f"elec_{cid}_{city_id}_w{week_num}"

async def nominate_mayor(cid, uid, city_id):
    user = await get_user(cid, uid)
    if user['balance'] < MAYOR_ELECTION_FEE:
        return False, f"❌ Нужно {fmt_money(MAYOR_ELECTION_FEE)}"
    current_mayor = await get_mayor(cid, city_id)
    if current_mayor:
        days_left = int((current_mayor['expires_at'] - time.time()) / 86400)
        city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
        city_name = city['name'] if city else f"город #{city_id}"
        return False, f"❌ В {city_name} уже есть мэр! Срок: {days_left} дн."
    election_id = await get_current_election_id(cid, city_id)
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND user_id=$3 AND election_id=$4",
            cid, city_id, uid, election_id
        )
        if existing:
            return False, "❌ Уже выдвинут!"
        await update_balance(cid, uid, -MAYOR_ELECTION_FEE)
        await conn.execute(
            "INSERT INTO mayor_candidates (chat_id, city_id, user_id, election_id) VALUES ($1,$2,$3,$4)",
            cid, city_id, uid, election_id
        )
        existing_start = await conn.fetchrow(
            "SELECT * FROM mayor_elections_start WHERE chat_id=$1 AND city_id=$2 AND election_id=$3",
            cid, city_id, election_id
        )
        if not existing_start:
            await conn.execute(
                "INSERT INTO mayor_elections_start (chat_id, city_id, election_id, started_at) VALUES ($1,$2,$3,$4)",
                cid, city_id, election_id, time.time()
            )
    return True, f"✅ Выдвинут!\n💸 {fmt_money(MAYOR_ELECTION_FEE)}"

async def vote_for_mayor(cid, uid, city_id, candidate_num):
    user = await get_user(cid, uid)
    if user['balance'] < MAYOR_VOTE_COST:
        return False, f"❌ Голос стоит {MAYOR_VOTE_COST}"
    election_id = await get_current_election_id(cid, city_id)
    async with pool.acquire() as conn:
        candidates = await conn.fetch(
            "SELECT id, user_id, votes FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3 ORDER BY id ASC",
            cid, city_id, election_id
        )
        if not candidates:
            return False, "❌ Нет кандидатов!"
        if candidate_num < 1 or candidate_num > len(candidates):
            return False, f"❌ 1-{len(candidates)}"
        target_candidate = candidates[candidate_num - 1]
        if target_candidate['user_id'] == uid:
            return False, "❌ Нельзя за себя!"
        already_voted = await conn.fetchrow(
            "SELECT * FROM mayor_votes WHERE chat_id=$1 AND city_id=$2 AND voter_id=$3 AND election_id=$4",
            cid, city_id, uid, election_id
        )
        if already_voted:
            return False, "❌ Уже голосовал!"
        await update_balance(cid, uid, -MAYOR_VOTE_COST)
        await update_city_treasury(cid, city_id, MAYOR_VOTE_COST)
        await conn.execute(
            "INSERT INTO mayor_votes (chat_id, city_id, voter_id, candidate_id, election_id) VALUES ($1,$2,$3,$4,$5)",
            cid, city_id, uid, target_candidate['id'], election_id
        )
        await conn.execute(
            "UPDATE mayor_candidates SET votes = votes + 1 WHERE id=$1",
            target_candidate['id']
        )
    return True, f"✅ Голос принят!\n💸 {MAYOR_VOTE_COST}"

async def finalize_mayor_election(cid, city_id):
    election_id = await get_current_election_id(cid, city_id)
    async with pool.acquire() as conn:
        candidates = await conn.fetch(
            "SELECT * FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3 ORDER BY votes DESC",
            cid, city_id, election_id
        )
        if not candidates:
            await conn.execute("DELETE FROM mayors WHERE chat_id=$1 AND city_id=$2", cid, city_id)
            return None
        winner = candidates[0]
        expires_at = time.time() + MAYOR_TERM_DAYS * 86400
        await conn.execute(
            """INSERT INTO mayors (chat_id, city_id, user_id, elected_at, expires_at, approval_rating) 
               VALUES ($1,$2,$3,$4,$5,50)
               ON CONFLICT (chat_id, city_id) DO UPDATE SET 
                   user_id=$3, elected_at=$4, expires_at=$5, approval_rating=50""",
            cid, city_id, winner['user_id'], time.time(), expires_at
        )
        try:
            await update_balance(cid, winner['user_id'], MAYOR_ELECTION_FEE + MAYOR_WIN_BONUS)
        except Exception as e:
            print(f"Ошибка бонуса: {e}")
        await conn.execute("DELETE FROM mayor_votes WHERE chat_id=$1 AND city_id=$2 AND election_id=$3", cid, city_id, election_id)
        await conn.execute("DELETE FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3", cid, city_id, election_id)
    return {"user_id": winner['user_id'], "votes": winner['votes'], "bonus": MAYOR_WIN_BONUS}

# Федеральные выборы
async def get_current_federal_election_id(cid, role):
    week_num = int(time.time() // 604800)
    return f"federal_{cid}_{role}_w{week_num}"

async def nominate_federal(cid, uid, role):
    fee = PRESIDENT_ELECTION_FEE if role == 'president' else PRIME_MINISTER_ELECTION_FEE
    user = await get_user(cid, uid)
    if user['balance'] < fee:
        return False, f"❌ Нужно {fmt_money(fee)}"
    current_official = await get_federal_role(cid, role)
    if current_official:
        days_left = int((current_official['expires_at'] - time.time()) / 86400)
        role_name = "Президент" if role == 'president' else "Премьер"
        return False, f"❌ {role_name} у власти! {days_left} дн."
    election_id = await get_current_federal_election_id(cid, role)
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND user_id=$3 AND election_id=$4",
            cid, role, uid, election_id
        )
        if existing:
            return False, "❌ Уже выдвинут!"
        await update_balance(cid, uid, -fee)
        await conn.execute(
            "INSERT INTO federal_candidates (chat_id, role, user_id, election_id) VALUES ($1,$2,$3,$4)",
            cid, role, uid, election_id
        )
        existing_start = await conn.fetchrow(
            "SELECT * FROM federal_elections_start WHERE chat_id=$1 AND role=$2 AND election_id=$3",
            cid, role, election_id
        )
        if not existing_start:
            await conn.execute(
                "INSERT INTO federal_elections_start (chat_id, role, election_id, started_at) VALUES ($1,$2,$3,$4)",
                cid, role, election_id, time.time()
            )
    role_name = "Президент" if role == 'president' else "Премьер"
    return True, f"✅ Выдвинут в {role_name}!\n💸 {fmt_money(fee)}"

async def vote_federal(cid, uid, role, candidate_num):
    cost = PRESIDENT_VOTE_COST if role == 'president' else PRIME_MINISTER_VOTE_COST
    user = await get_user(cid, uid)
    if user['balance'] < cost:
        return False, f"❌ Голос стоит {fmt_money(cost)}"
    election_id = await get_current_federal_election_id(cid, role)
    async with pool.acquire() as conn:
        candidates = await conn.fetch(
            "SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND election_id=$3 ORDER BY id ASC",
            cid, role, election_id
        )
        if not candidates:
            return False, "❌ Нет кандидатов!"
        if candidate_num < 1 or candidate_num > len(candidates):
            return False, f"❌ 1-{len(candidates)}"
        target_candidate = candidates[candidate_num - 1]
        if target_candidate['user_id'] == uid:
            return False, "❌ Нельзя за себя!"
        already_voted = await conn.fetchrow(
            "SELECT * FROM federal_votes WHERE chat_id=$1 AND role=$2 AND voter_id=$3 AND election_id=$4",
            cid, role, uid, election_id
        )
        if already_voted:
            return False, "❌ Уже голосовал!"
        await update_balance(cid, uid, -cost)
        await update_state_treasury(cid, cost)
        await conn.execute(
            "INSERT INTO federal_votes (chat_id, role, voter_id, candidate_id, election_id) VALUES ($1,$2,$3,$4,$5)",
            cid, role, uid, target_candidate['id'], election_id
        )
        await conn.execute(
            "UPDATE federal_candidates SET votes = votes + 1 WHERE id=$1",
            target_candidate['id']
        )
    return True, f"✅ Голос принят!\n💸 {fmt_money(cost)}"

async def finalize_federal_election(cid, role):
    election_id = await get_current_federal_election_id(cid, role)
    async with pool.acquire() as conn:
        candidates = await conn.fetch(
            "SELECT * FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND election_id=$3 ORDER BY votes DESC",
            cid, role, election_id
        )
        if not candidates:
            await conn.execute("DELETE FROM federal_roles WHERE chat_id=$1 AND role=$2", cid, role)
            return None
        winner = candidates[0]
        term_days = PRESIDENT_TERM_DAYS if role == 'president' else PRIME_MINISTER_TERM_DAYS
        win_bonus = PRESIDENT_WIN_BONUS if role == 'president' else PRIME_MINISTER_WIN_BONUS
        election_fee = PRESIDENT_ELECTION_FEE if role == 'president' else PRIME_MINISTER_ELECTION_FEE
        expires_at = time.time() + term_days * 86400
        await conn.execute(
            """INSERT INTO federal_roles (chat_id, role, user_id, elected_at, expires_at, approval_rating) 
               VALUES ($1,$2,$3,$4,$5,50)
               ON CONFLICT (chat_id, role) DO UPDATE SET 
                   user_id=$3, elected_at=$4, expires_at=$5, approval_rating=50""",
            cid, role, winner['user_id'], time.time(), expires_at
        )
        try:
            await update_balance(cid, winner['user_id'], election_fee + win_bonus)
        except Exception as e:
            print(f"Ошибка бонуса: {e}")
        await conn.execute("DELETE FROM federal_votes WHERE chat_id=$1 AND role=$2 AND election_id=$3", cid, role, election_id)
        await conn.execute("DELETE FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND election_id=$3", cid, role, election_id)
    return {"user_id": winner['user_id'], "votes": winner['votes'], "bonus": win_bonus}

async def get_federal_role(cid, role):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM federal_roles WHERE chat_id=$1 AND role=$2 AND expires_at > $3",
                cid, role, time.time()
            )
            return row
    except Exception:
        return None

async def is_mayor(cid, uid, city_id):
    mayor = await get_mayor(cid, city_id)
    if mayor and mayor['user_id'] == uid:
        return True
    return False

async def is_federal_official(cid, uid, role):
    official = await get_federal_role(cid, role)
    if official and official['user_id'] == uid:
        return True
    return False

async def get_active_decree(cid, city_id, decree_type):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM city_decrees WHERE chat_id=$1 AND city_id=$2 AND decree_type=$3 AND active_until > $4",
                cid, city_id, decree_type, time.time()
            )
            return row
    except Exception:
        return None

async def get_active_federal_decree(cid, role, decree_type):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM federal_decrees WHERE chat_id=$1 AND role=$2 AND decree_type=$3 AND active_until > $4",
                cid, role, decree_type, time.time()
            )
            return row
    except Exception:
        return None

async def apply_income_tax(cid, uid, gross_income):
    tax_cut = await get_active_federal_decree(cid, 'president', 'tax_cut')
    tax_boost_president = await get_active_federal_decree(cid, 'president', 'tax_boost')
    tax_boost_prime = await get_active_federal_decree(cid, 'prime_minister', 'tax_boost')
    if tax_cut:
        tax_rate = 2
    elif tax_boost_president or tax_boost_prime:
        tax_rate = 10
    else:
        tax_rate = TAX_RATE_PERCENT
    tax_amount = int(gross_income * tax_rate / 100)
    net_income = gross_income - tax_amount
    player_city = await get_player_city(cid, uid)
    if player_city:
        await update_city_treasury(cid, player_city['id'], tax_amount)
        receiver = f"казну г. {player_city['name']}"
    else:
        await update_state_treasury(cid, tax_amount)
        receiver = "фед. казну"
    return net_income, tax_amount, receiver, tax_rate

async def apply_business_tax(cid, uid, gross_profit):
    tax_cut = await get_active_federal_decree(cid, 'president', 'tax_cut')
    tax_boost_president = await get_active_federal_decree(cid, 'president', 'tax_boost')
    tax_boost_prime = await get_active_federal_decree(cid, 'prime_minister', 'tax_boost')
    if tax_cut:
        tax_rate = 2
    elif tax_boost_president or tax_boost_prime:
        tax_rate = 10
    else:
        tax_rate = TAX_RATE_PERCENT
    tax_amount = int(gross_profit * tax_rate / 100)
    net_profit = gross_profit - tax_amount
    city_tax = tax_amount // 2
    state_tax = tax_amount - city_tax
    player_city = await get_player_city(cid, uid)
    if player_city:
        await update_city_treasury(cid, player_city['id'], city_tax)
        await update_state_treasury(cid, state_tax)
    else:
        await update_state_treasury(cid, tax_amount)
    return net_profit, tax_amount, tax_rate

async def create_decree(cid, city_id, mayor_id, decree_type, duration_hours=24):
    if not await is_mayor(cid, mayor_id, city_id):
        return False, "❌ Только мэр!"
    existing = await get_active_decree(cid, city_id, decree_type)
    if existing:
        hours_left = int((existing['active_until'] - time.time()) / 3600)
        return False, f"⚠️ Уже активен! {hours_left} ч."
    treasury = await get_city_treasury(cid, city_id)
    cost = get_decree_cost(decree_type)
    if treasury < cost:
        return False, f"❌ В казне нужно {cost}, есть: {treasury}"
    await update_city_treasury(cid, city_id, -cost)
    active_until = time.time() + (duration_hours * 3600)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO city_decrees (chat_id, city_id, mayor_id, decree_type, active_until) VALUES ($1,$2,$3,$4,$5)",
            cid, city_id, mayor_id, decree_type, active_until
        )
    return True, f"✅ Указ издан! {duration_hours} часов.\n💸 Списано: {cost}"

def get_decree_cost(decree_type):
    costs = {
        'work_bonus': 5000,
        'tool_discount': 3000,
        'business_bonus': 8000,
        'car_discount': 4000,
        'city_event': 10000,
    }
    return costs.get(decree_type, 5000)

def get_decree_name(decree_type):
    names = {
        'work_bonus': '🏭 Рабочая смена (+20% к работе)',
        'tool_discount': '🔧 Заводской бонус (-30% на инструменты)',
        'business_bonus': '📈 Бизнес-стимул (+15% к бизнесам)',
        'car_discount': '🚗 Авто-скидка (-25% на машины)',
        'city_event': '🎉 День города (бонус всем жителям)',
    }
    return names.get(decree_type, 'Неизвестный указ')

async def create_federal_decree(cid, uid, role, decree_type):
    if not await is_federal_official(cid, uid, role):
        role_name = "Президент" if role == 'president' else "Премьер-министр"
        return False, f"❌ Только {role_name}!"
    existing = await get_active_federal_decree(cid, role, decree_type)
    if existing:
        hours_left = int((existing['active_until'] - time.time()) / 3600)
        return False, f"⚠️ Уже активен! {hours_left} ч."
    duration = PRESIDENT_DECREE_DURATION if role == 'president' else PRIME_MINISTER_DECREE_DURATION
    active_until = time.time() + (duration * 3600)
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO federal_decrees (chat_id, role, decree_type, active_until) 
               VALUES ($1,$2,$3,$4)
               ON CONFLICT (chat_id, role, decree_type) DO UPDATE SET active_until = $4""",
            cid, role, decree_type, active_until
        )
    role_name = "Президент" if role == 'president' else "Премьер-министр"
    return True, f"✅ Указ {role_name} издан!\n⏰ {duration} часов."

def get_federal_decree_name(decree_type):
    names = {
        'amnesty': '🕊️ Амнистия',
        'tax_cut': '📉 Снижение налога до 2%',
        'tax_boost': '📈 Повышение до 10%',
        'emergency': '🚨 ЧП',
        'subsidy': '💰 Субсидии (+10%)',
        'investment': '🏗️ Инвестиции (+5000)',
    }
    return names.get(decree_type, 'Неизвестный указ')

# Команды городов
@dp.message(Command("city"))
async def cmd_city(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        return await m.answer(
            "🏙️ <b>ГОРОДА</b>\n\n"
            "/city list — список\n"
            "/city choose [город] — выбрать\n"
            "/city move [город] — переехать (1 день, 10к)\n"
            "/city info — инфо\n"
            "/city residents — жители",
            parse_mode="HTML"
        )
    subcmd = args[1].lower()
    if subcmd == "list":
        t = "🏙️ <b>ГОРОДА</b>\n\n"
        for city in CITIES_LIST:
            t += f"{city['emoji']} <b>{city['name']}</b>\n   {city['desc']}\n\n"
        t += "/city choose [название]"
        return await m.answer(t, parse_mode="HTML")
    if subcmd == "info":
        try:
            player_city = await get_player_city(cid, uid)
            if not player_city:
                return await m.answer("❌ Нет города!\n/city choose [город]")
            mayor = await get_mayor(cid, player_city['id'])
            treasury = await get_city_treasury(cid, player_city['id'])
            t = f"{player_city['emoji']} <b>{player_city['name']}</b>\n\n📊 {player_city['desc']}\n💰 Казна: {treasury}\n\n"
            if mayor:
                try: mayor_name = (await bot.get_chat_member(cid, mayor['user_id'])).user.full_name
                except: mayor_name = f"User{mayor['user_id']}"
                days_left = int((mayor['expires_at'] - time.time()) / 86400)
                t += f"🏛️ Мэр: {mayor_name}\n📊 Рейтинг: {mayor['approval_rating']}%\n⏰ {days_left} дн."
            else: t += "🏛️ Мэр: ВАКАНТНО"
            return await m.answer(t, parse_mode="HTML")
        except Exception as e: return await m.answer(f"❌ Ошибка: {str(e)}")
    if subcmd == "choose":
        if len(args) < 3: return await m.answer("⚠️ /city choose Москва")
        city_name = " ".join(args[2:])
        existing = await get_player_city(cid, uid)
        if existing: return await m.answer(f"❌ Уже в <b>{existing['name']}</b>!\n/city move", parse_mode="HTML")
        city = next((c for c in CITIES_LIST if c['name'].lower() == city_name.lower()), None)
        if not city: return await m.answer(f"❌ Не найден! /city list")
        await set_player_city(cid, uid, city['id'])
        return await m.answer(f"🎉 <b>Добро пожаловать в {city['emoji']} {city['name']}!</b>\n\n📊 {city['desc']}", parse_mode="HTML")
    if subcmd == "move":
        try:
            if len(args) < 3: return await m.answer("⚠️ /city move Москва")
            city_name = " ".join(args[2:])
            existing = await get_player_city(cid, uid)
            if not existing: return await m.answer("❌ Сначала /city choose")
            cooldown_left = CITY_MOVE_COOLDOWN - (time.time() - existing['moved_at'])
            if cooldown_left > 0:
                days = int(cooldown_left / 86400)
                hours = int((cooldown_left % 86400) / 3600)
                return await m.answer(f"⏳ Через {days} дн. {hours} ч.")
            city = next((c for c in CITIES_LIST if c['name'].lower() == city_name.lower()), None)
            if not city: return await m.answer(f"❌ Не найден! /city list")
            if city['id'] == existing['id']: return await m.answer("❌ Уже здесь!")
            user = await get_user(cid, uid)
            if user['balance'] < CITY_MOVE_COST: return await m.answer(f"❌ Нужно {CITY_MOVE_COST}")
            await update_balance(cid, uid, -CITY_MOVE_COST)
            await set_player_city(cid, uid, city['id'])
            return await m.answer(f"🚚 <b>ПЕРЕЕЗД!</b>\n\n{city['emoji']} {city['name']}\n📊 {city['desc']}", parse_mode="HTML")
        except Exception as e: return await m.answer(f"❌ Ошибка: {str(e)}")
    if subcmd == "residents":
        player_city = await get_player_city(cid, uid)
        if not player_city: return await m.answer("❌ Нет города!")
        try:
            async with pool.acquire() as conn:
                residents = await conn.fetch("SELECT user_id FROM player_cities WHERE chat_id=$1 AND city_id=$2 LIMIT 20", cid, player_city['id'])
        except Exception: return await m.answer("❌ Ошибка")
        if not residents: return await m.answer("🏙️ Никого нет!")
        t = f"{player_city['emoji']} <b>Жители {player_city['name']}:</b>\n\n"
        for i, r in enumerate(residents[:20], 1):
            try: name = (await bot.get_chat_member(cid, r['user_id'])).user.full_name
            except: name = f"User{r['user_id']}"
            t += f"{i}. {name}\n"
        t += f"\n📊 Всего: {len(residents)}"
        return await m.answer(t, parse_mode="HTML")
    await m.answer("❓ /city")

# Команды мэра
@dp.message(Command("mayor_nominate"))
async def cmd_mayor_nominate(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        player_city = await get_player_city(cid, uid)
        if not player_city: return await m.answer("❌ Нет города! /city choose")
        success, msg = await nominate_mayor(cid, uid, player_city['id'])
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("mayor_vote"))
async def cmd_mayor_vote(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2:
            player_city = await get_player_city(cid, uid)
            if not player_city: return await m.answer("❌ Нет города!")
            election_id = await get_current_election_id(cid, player_city['id'])
            async with pool.acquire() as conn:
                candidates = await conn.fetch("SELECT user_id, votes FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3 ORDER BY id ASC", cid, player_city['id'], election_id)
            if not candidates: return await m.answer(f"🏛️ <b>Выборы в {player_city['emoji']} {player_city['name']}</b>\n\n❌ Нет кандидатов.\n/mayor_nominate", parse_mode="HTML")
            t = f"🏛️ <b>Кандидаты {player_city['emoji']} {player_city['name']}:</b>\n\n"
            for i, c in enumerate(candidates, 1):
                try: name = (await bot.get_chat_member(cid, c['user_id'])).user.full_name
                except: name = f"User{c['user_id']}"
                t += f"{i}. {name} ({c['votes']})\n"
            t += f"\n💰 {MAYOR_VOTE_COST}\n/mayor_vote [номер]"
            return await m.answer(t, parse_mode="HTML")
        try: candidate_num = int(args[1])
        except ValueError: return await m.answer("❌ Число!")
        player_city = await get_player_city(cid, uid)
        if not player_city: return await m.answer("❌ Нет города!")
        success, msg = await vote_for_mayor(cid, uid, player_city['id'], candidate_num)
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("mayor_finalize"))
async def cmd_mayor_finalize(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        player_city = await get_player_city(cid, uid)
        if not player_city: return await m.answer("❌ Нет города!")
        result = await finalize_mayor_election(cid, player_city['id'])
        if result is None: return await m.answer(f"🏛️ <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
        return await m.answer(f"🎉 <b>НОВЫЙ МЭР!</b>\n\n🏛️ {player_city['emoji']} {player_city['name']}\n👤 ID: {result['user_id']}\n🗳️ {result['votes']}\n💰 +{result['bonus']}\n⏰ {MAYOR_TERM_DAYS} дн.\n\n/city info", parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("mayor_decree"))
async def cmd_mayor_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    if not await is_mayor(cid, uid, player_city['id']): return await m.answer("❌ Только мэр!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer(f"🏛️ <b>УКАЗЫ МЭРА</b>\n\n/mayor_decree work (+20% работа, 5к)\n/mayor_decree tools (-30% инструменты, 3к)\n/mayor_decree business (+15% бизнес, 8к)\n/mayor_decree cars (-25% авто, 4к)\n/mayor_decree event (праздник, 10к)\n\n💰 Казна: {await get_city_treasury(cid, player_city['id'])}", parse_mode="HTML")
    decree = args[1].lower()
    decree_map = {'work': 'work_bonus', 'tools': 'tool_discount', 'business': 'business_bonus', 'cars': 'car_discount', 'event': 'city_event'}
    decree_type = decree_map.get(decree)
    if not decree_type: return await m.answer("❌ Неизвестный указ!")
    success, msg = await create_decree(cid, player_city['id'], uid, decree_type)
    await m.answer(msg, parse_mode="HTML")

@dp.message(Command("city_decrees"))
async def cmd_city_decrees(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    try:
        async with pool.acquire() as conn:
            decrees = await conn.fetch("SELECT * FROM city_decrees WHERE chat_id=$1 AND city_id=$2 AND active_until > $3", cid, player_city['id'], time.time())
    except Exception: return await m.answer("❌ Ошибка")
    if not decrees: return await m.answer(f"🏛️ <b>{player_city['emoji']} {player_city['name']}</b>\n\n❌ Нет указов")
    t = f"🏛️ <b>Указы {player_city['emoji']} {player_city['name']}:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {get_decree_name(d['decree_type'])}\n  ⏰ {hours_left} ч.\n\n"
    return await m.answer(t, parse_mode="HTML")

# Федеральные команды
@dp.message(Command("president_nominate"))
async def cmd_president_nominate(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        success, msg = await nominate_federal(cid, uid, 'president')
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("president_vote"))
async def cmd_president_vote(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2:
            election_id = await get_current_federal_election_id(cid, 'president')
            async with pool.acquire() as conn:
                candidates = await conn.fetch("SELECT user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='president' AND election_id=$2 ORDER BY id ASC", cid, election_id)
            if not candidates: return await m.answer("🏛️ <b>Выборы Президента</b>\n\n❌ Нет кандидатов.\n/president_nominate", parse_mode="HTML")
            t = "🏛️ <b>Кандидаты:</b>\n\n"
            for i, c in enumerate(candidates, 1):
                try: name = (await bot.get_chat_member(cid, c['user_id'])).user.full_name
                except: name = f"User{c['user_id']}"
                t += f"{i}. {name} ({c['votes']})\n"
            t += f"\n💰 {PRESIDENT_VOTE_COST}\n/president_vote [номер]"
            return await m.answer(t, parse_mode="HTML")
        try: candidate_num = int(args[1])
        except ValueError: return await m.answer("❌ Число!")
        success, msg = await vote_federal(cid, uid, 'president', candidate_num)
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("president_finalize"))
async def cmd_president_finalize(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        result = await finalize_federal_election(cid, 'president')
        if result is None: return await m.answer("🏛️ <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
        return await m.answer(f"🎉 <b>НОВЫЙ ПРЕЗИДЕНТ!</b>\n\n👤 ID: {result['user_id']}\n🗳️ {result['votes']}\n💰 +{result['bonus']}\n⏰ {PRESIDENT_TERM_DAYS} дн.", parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("president_decree"))
async def cmd_president_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if not await is_federal_official(cid, uid, 'president'): return await m.answer("❌ Только Президент!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("🏛️ <b>УКАЗЫ</b>\n\n/president_decree amnesty\n/president_decree tax_cut\n/president_decree tax_boost\n/president_decree emergency", parse_mode="HTML")
    decree = args[1].lower()
    decree_map = {'amnesty': 'amnesty', 'tax_cut': 'tax_cut', 'tax_boost': 'tax_boost', 'emergency': 'emergency'}
    decree_type = decree_map.get(decree)
    if not decree_type: return await m.answer("❌ Неизвестный указ!")
    if decree_type == 'amnesty':
        try:
            async with pool.acquire() as conn:
                jailed = await conn.fetch("SELECT user_id FROM jail WHERE chat_id=$1 AND release_time > $2", cid, time.time())
                count = len(jailed)
                if count > 0:
                    await conn.execute("DELETE FROM jail WHERE chat_id=$1 AND release_time > $2", cid, time.time())
            return await m.answer(f"🕊️ <b>АМНИСТИЯ!</b>\n\nОсвобождено: <b>{count}</b>", parse_mode="HTML")
        except Exception as e: return await m.answer(f"❌ Ошибка: {str(e)}")
    success, msg = await create_federal_decree(cid, uid, 'president', decree_type)
    await m.answer(msg, parse_mode="HTML")

@dp.message(Command("president_decrees"))
async def cmd_president_decrees(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    try:
        async with pool.acquire() as conn:
            decrees = await conn.fetch("SELECT * FROM federal_decrees WHERE chat_id=$1 AND role='president' AND active_until > $2", cid, time.time())
    except Exception: return await m.answer("❌ Ошибка")
    if not decrees: return await m.answer("🏛️ <b>Указы Президента</b>\n\n❌ Нет активных")
    t = "🏛️ <b>Активные указы:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {get_federal_decree_name(d['decree_type'])}\n  ⏰ {hours_left} ч.\n\n"
    return await m.answer(t, parse_mode="HTML")

@dp.message(Command("prime_nominate"))
async def cmd_prime_nominate(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        success, msg = await nominate_federal(cid, uid, 'prime_minister')
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("prime_vote"))
async def cmd_prime_vote(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2:
            election_id = await get_current_federal_election_id(cid, 'prime_minister')
            async with pool.acquire() as conn:
                candidates = await conn.fetch("SELECT user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='prime_minister' AND election_id=$2 ORDER BY id ASC", cid, election_id)
            if not candidates: return await m.answer("💼 <b>Выборы Премьера</b>\n\n❌ Нет кандидатов.\n/prime_nominate", parse_mode="HTML")
            t = "💼 <b>Кандидаты:</b>\n\n"
            for i, c in enumerate(candidates, 1):
                try: name = (await bot.get_chat_member(cid, c['user_id'])).user.full_name
                except: name = f"User{c['user_id']}"
                t += f"{i}. {name} ({c['votes']})\n"
            t += f"\n💰 {PRIME_MINISTER_VOTE_COST}\n/prime_vote [номер]"
            return await m.answer(t, parse_mode="HTML")
        try: candidate_num = int(args[1])
        except ValueError: return await m.answer("❌ Число!")
        success, msg = await vote_federal(cid, uid, 'prime_minister', candidate_num)
        await m.answer(msg, parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("prime_finalize"))
async def cmd_prime_finalize(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        result = await finalize_federal_election(cid, 'prime_minister')
        if result is None: return await m.answer("💼 <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
        return await m.answer(f"🎉 <b>НОВЫЙ ПРЕМЬЕР!</b>\n\n👤 ID: {result['user_id']}\n🗳️ {result['votes']}\n💰 +{result['bonus']}\n⏰ {PRIME_MINISTER_TERM_DAYS} дн.", parse_mode="HTML")
    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("prime_decree"))
async def cmd_prime_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if not await is_federal_official(cid, uid, 'prime_minister'): return await m.answer("❌ Только Премьер!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("💼 <b>УКАЗЫ</b>\n\n/prime_decree subsidy\n/prime_decree investment\n/prime_decree tax_cut\n/prime_decree tax_boost", parse_mode="HTML")
    decree = args[1].lower()
    decree_map = {'subsidy': 'subsidy', 'investment': 'investment', 'tax_cut': 'tax_cut', 'tax_boost': 'tax_boost'}
    decree_type = decree_map.get(decree)
    if not decree_type: return await m.answer("❌ Неизвестный указ!")
    if decree_type == 'investment':
        try:
            async with pool.acquire() as conn:
                cities = await conn.fetch("SELECT DISTINCT city_id FROM player_cities WHERE chat_id=$1", cid)
                for city_row in cities:
                    await update_city_treasury(cid, city_row['city_id'], 5000)
            return await m.answer(f"🏗️ <b>ИНВЕСТИЦИИ!</b>\n\nКаждому городу +<b>5000</b>\nГородов: <b>{len(cities)}</b>", parse_mode="HTML")
        except Exception as e: return await m.answer(f"❌ Ошибка: {str(e)}")
    success, msg = await create_federal_decree(cid, uid, 'prime_minister', decree_type)
    await m.answer(msg, parse_mode="HTML")

@dp.message(Command("prime_decrees"))
async def cmd_prime_decrees(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    try:
        async with pool.acquire() as conn:
            decrees = await conn.fetch("SELECT * FROM federal_decrees WHERE chat_id=$1 AND role='prime_minister' AND active_until > $2", cid, time.time())
    except Exception: return await m.answer("❌ Ошибка")
    if not decrees: return await m.answer("💼 <b>Указы Премьера</b>\n\n❌ Нет активных")
    t = "💼 <b>Активные указы:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {get_federal_decree_name(d['decree_type'])}\n  ⏰ {hours_left} ч.\n\n"
    return await m.answer(t, parse_mode="HTML")

@dp.message(Command("impeach"))
async def cmd_impeach(m: Message):
    """Голосование за импичмент"""
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        return await m.answer(
            "⚖️ <b>ИМПИЧМЕНТ</b>\n\n"
            "Использование:\n"
            "/impeach president — против Президента\n"
            "/impeach prime — против Премьера\n\n"
            "Нужно 10 голосов за 7 дней",
            parse_mode="HTML"
        )
    role = args[1].lower()
    if role not in ['president', 'prime']:
        return await m.answer("❌ Используй president или prime")
    db_role = 'president' if role == 'president' else 'prime_minister'
    official = await get_federal_role(cid, db_role)
    if not official:
        return await m.answer("❌ Сейчас нет действующего чиновника!")
    if official['user_id'] == uid:
        return await m.answer("❌ Нельзя голосовать против себя!")
    async with pool.acquire() as conn:
        already_voted = await conn.fetchrow(
            "SELECT * FROM impeachment_votes WHERE chat_id=$1 AND role=$2 AND voter_id=$3",
            cid, db_role, uid
        )
        if already_voted:
            return await m.answer("❌ Ты уже голосовал за импичмент!")
        await conn.execute(
            "INSERT INTO impeachment_votes (chat_id, role, voter_id, voted_at) VALUES ($1,$2,$3,$4)",
            cid, db_role, uid, time.time()
        )
        votes = await conn.fetchval(
            "SELECT COUNT(*) FROM impeachment_votes WHERE chat_id=$1 AND role=$2",
            cid, db_role
        )
    role_name = "Президент" if role == 'president' else "Премьер"
    if votes >= 10:
        await conn.execute(
            "DELETE FROM federal_roles WHERE chat_id=$1 AND role=$2",
            cid, db_role
        )
        await conn.execute(
            "DELETE FROM impeachment_votes WHERE chat_id=$1 AND role=$2",
            cid, db_role
        )
        try:
            official_name = (await bot.get_chat_member(cid, official['user_id'])).user.full_name
        except:
            official_name = f"User{official['user_id']}"
        msg = (
            f"⚖️ <b>ИМПИЧМЕНТ УСПЕШЕН!</b>\n\n"
            f"👤 {role_name} {official_name} отстранён от должности!\n"
            f"🗳️ Голосов: {votes}/10\n\n"
            f"⏳ Новые выборы через 24 часа"
        )
        await bot.send_message(cid, msg, parse_mode="HTML")
        await m.answer("✅ Импичмент проведён!")
    else:
        await m.answer(
            f"⚖️ Голос за импичмент {role_name} принят!\n"
            f"📊 Голосов: {votes}/10",
            parse_mode="HTML"
        )

async def main():
    await init_db()
    print("🤖 Бот запущен!")
    await start_web_server()
    asyncio.create_task(polling_health_check())
    asyncio.create_task(auto_lottery_loop())
    asyncio.create_task(loan_interest_loop())
    asyncio.create_task(jail_fine_check_loop())
    asyncio.create_task(check_expired_debts_loop())
    asyncio.create_task(check_all_elections_and_terms())
    print("🎰 Лотерея")
    print("💳 Кредиты")
    print("⚖️ Штрафы")
    print("🕵️ Долги")
    print("🏛️ Выборы")
    await init_cities()  # ← ДОБАВЬ ЭТУ СТРОКУ!
    print("🏙️ Города")
    await dp.start_polling(bot, timeout=30, drop_pending_updates=True, allowed_updates=["message", "callback_query", "my_chat_member"])

if __name__ == "__main__":
    asyncio.run(main())
