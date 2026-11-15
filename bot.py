import asyncio
import logging
import random
import time
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
import asyncpg
from aiohttp import web

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "-1002595597314").strip())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not API_TOKEN:
    raise ValueError("❌ Не найден BOT_TOKEN в переменных окружения!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
pool = None
exam_sessions = {}
active_cases = {}

# --- ГОРОДА ---
CITIES_LIST = [
    {"id": 1, "name": "Москва", "emoji": "🏛️", "work_bonus": 0.20, "desc": "+20% к зарплате", "bonus_type": "work", "bonus_value": 20},
    {"id": 2, "name": "Сарапул", "emoji": "🏘️", "market_discount": 0.15, "desc": "-15% на покупки", "bonus_type": "market", "bonus_value": 15},
    {"id": 3, "name": "Санкт-Петербург", "emoji": "🏛️", "rob_bonus": 0.10, "desc": "+10% к шансу ограбления", "bonus_type": "rob", "bonus_value": 10},
]

# --- КОНСТАНТЫ ---
TAX_RATE_PERCENT = 10
PRESIDENT_DECREE_DURATION = 168
PRIME_MINISTER_DECREE_DURATION = 168
MAYOR_ELECTION_DURATION = 86400
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
MAX_BUSINESSES_PER_TYPE = 10
FEDERAL_SALARY_PRESIDENT = 50000
FEDERAL_SALARY_PRIME = 30000
FEDERAL_SOCIAL_AID = 1000
FEDERAL_INFRASTRUCTURE = 20000
CITY_SALARY_MAYOR = 20000
CITY_UTILITIES = 5000
CITY_SOCIAL_PROGRAMS = 3000
MIN_TREASURY_BALANCE = 10000

COURSES = {
    "miner": {"name": "📘 Курс шахтёра", "price": 500, "required_for": "miner", "questions": [
        {"q": "Что нужно надевать в шахте?", "a": ["каска", "шлем", "защита"], "correct": 0},
        {"q": "Сколько тонн весит вагонетка?", "a": ["1", "5", "10"], "correct": 1},
        {"q": "Главный инструмент шахтёра?", "a": ["лопата", "отбойный молоток", "кирка"], "correct": 2},
    ]},
    "coder": {"name": "💻 Курс программирования", "price": 2000, "required_for": "coder", "questions": [
        {"q": "Язык для веб-разработки?", "a": ["Python", "HTML", "C++"], "correct": 1},
        {"q": "Что такое баг?", "a": ["ошибка", "функция", "переменная"], "correct": 0},
        {"q": "Сколько бит в байте?", "a": ["4", "8", "16"], "correct": 1},
    ]},
    "trader": {"name": "📈 Курс трейдинга", "price": 5000, "required_for": "trader", "questions": [
        {"q": "Что такое бычий рынок?", "a": ["рост", "падение", "стабильность"], "correct": 0},
        {"q": "Диверсификация это?", "a": ["риск", "распределение", "прибыль"], "correct": 1},
        {"q": "Ликвидность актива?", "a": ["скорость продажи", "цена", "объём"], "correct": 0},
    ]},
    "lawyer": {"name": "⚖️ Курс адвоката", "price": 3000, "required_for": None, "questions": [
        {"q": "Что такое презумпция невиновности?", "a": ["виновен пока не доказано", "невиновен пока не доказано", "все равны"], "correct": 1},
        {"q": "Срок давности уголовного дела?", "a": ["5 лет", "10 лет", "зависит от тяжести"], "correct": 2},
        {"q": "Кто защищает обвиняемого?", "a": ["прокурор", "адвокат", "судья"], "correct": 1},
    ]},
    "mba": {"name": "🎓 MBA", "price": 15000, "required_for": None, "questions": [
        {"q": "ROI это?", "a": ["возврат инвестиций", "риск", "доход"], "correct": 0},
        {"q": "EBITDA показывает?", "a": ["прибыль", "убыток", "оборот"], "correct": 0},
        {"q": "Стратегия роста?", "a": ["сокращение", "инвестиции", "стагнация"], "correct": 1},
    ]},
}

JOBS = {
    "novice": {"name": "👶 Новичок", "base_pay": 25, "cooldown": 3600},
    "miner": {"name": "⛏️ Шахтёр", "base_pay": 50, "cooldown": 3600},
    "coder": {"name": "💻 Программист", "base_pay": 100, "cooldown": 7200},
    "trader": {"name": "📊 Трейдер", "base_pay": 200, "cooldown": 10800},
}

SHOP_ITEMS = {
    "course": {"name": "📚 Уровень+", "price": 0, "type": "level_up"},
    "coffee": {"name": "☕ Кофе-машина", "price": 0, "type": "cooldown_reduce"},
}

MARKET = {
    "case_basic": {"name": "📦 Кейс", "price": 200, "type": "case"},
    "biz_newspaper": {"name": "📰 Газетный киоск", "price": 500, "type": "business", "income": 83},
    "biz_shawarma": {"name": "🌯 Шаурма", "price": 2000, "type": "business", "income": 333},
    "biz_coffee": {"name": "☕ Кофейня", "price": 5000, "type": "business", "income": 833},
    "biz_pizza": {"name": "🍕 Пиццерия", "price": 10000, "type": "business", "income": 1900},
    "biz_crypto": {"name": "💻 Крипто-ферма", "price": 15000, "type": "business", "income": 2500},
    "biz_taxi": {"name": "🚕 Таксопарк", "price": 30000, "type": "business", "income": 7899},
    "biz_hotel": {"name": "🏨 Отель", "price": 50000, "type": "business", "income": 8333},
    "biz_pharmacy": {"name": "💊 Аптека", "price": 75000, "type": "business", "income": 18789},
    "biz_construction": {"name": "🏗️ Стройфирма", "price": 150000, "type": "business", "income": 35000},
    "biz_spaceport": {"name": "🚀 Космодром", "price": 500000, "type": "business", "income": 120000},
    "biz_casino": {"name": "🎰 Казино", "price": 1000000, "type": "business", "income": 300000},
    "biz_oil": {"name": "🛢️ Нефтяная вышка", "price": 5000000, "type": "business", "income": 1500000},
    "biz_bank": {"name": "🏦 Частный банк", "price": 15000000, "type": "business", "income": 4500000},
    "biz_factory": {"name": "🏭 Завод", "price": 50000000, "type": "business", "income": 15000000},
    "biz_airline": {"name": "✈️ Авиакомпания", "price": 150000000, "type": "business", "income": 45000000},
    "biz_tech": {"name": "💡 IT-корпорация", "price": 500000000, "type": "business", "income": 150000000},
    "biz_empire": {"name": "👑 Бизнес-империя", "price": 1000000000, "type": "business", "income": 300000000},
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
    "yacht_car": {"name": "🛥️ Яхта", "price": 5000000},
}

CRAFT_RECIPES = {
    "diamond": {"name": "💎 Алмаз", "requires": {"📄 Бумага": 10}, "rarity": "rare"},
    "scriptka": {"name": "🎸 Золотая Скрипка", "requires": {"💎 Алмаз": 5}, "rarity": "legendary"},
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

PROJECT_TYPES = {
    "park": {"name": "🌳 Парк", "cost": 15000, "desc": "Благоустройство парка"},
    "road": {"name": "🛣️ Дороги", "cost": 25000, "desc": "Ремонт дорог"},
    "school": {"name": "🏫 Школа", "cost": 40000, "desc": "Строительство школы"},
    "hospital": {"name": "🏥 Больница", "cost": 50000, "desc": "Ремонт больницы"},
    "stadium": {"name": "🏟️ Стадион", "cost": 60000, "desc": "Строительство стадиона"},
    "library": {"name": "📚 Библиотека", "cost": 20000, "desc": "Открытие библиотеки"},
    "monument": {"name": "🗿 Монумент", "cost": 10000, "desc": "Установка монумента"},
    "festival": {"name": "🎉 Фестиваль", "cost": 30000, "desc": "Городской фестиваль"},
}


def pluralize(n, forms):
    n = abs(n) % 100
    n1 = n % 10
    if 10 < n < 20:
        return forms[2]
    if 1 < n1 < 5:
        return forms[1]
    if n1 == 1:
        return forms[0]
    return forms[2]


def fmt_money(amount):
    return f"{amount} {pluralize(amount, ['сарапулка', 'сарапулки', 'сарапулок'])}"


def format_time(seconds):
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours} ч {minutes} мин"
    return f"{minutes} мин"


def format_date(timestamp):
    return time.strftime('%d.%m.%Y', time.localtime(timestamp))


async def safe_name(cid, uid):
    try:
        member = await bot.get_chat_member(cid, uid)
        return member.user.full_name
    except Exception:
        return f"User{uid}"


# --- БАЗА ДАННЫХ ---
async def init_db():
    global pool
    if not DATABASE_URL:
        raise ValueError("❌ Не найден DATABASE_URL (PostgreSQL) в переменных окружения!")
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10, command_timeout=30)

    async with pool.acquire() as conn:
        tables = [
            "CREATE TABLE IF NOT EXISTS users (chat_id BIGINT, user_id BIGINT, balance BIGINT DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS profiles (chat_id BIGINT, user_id BIGINT, job_key TEXT DEFAULT 'novice', level INTEGER DEFAULT 1, last_work_time DOUBLE PRECISION DEFAULT 0, coffee_level INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS inventory (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, item_name TEXT, item_type TEXT, rarity TEXT DEFAULT 'common')",
            "CREATE TABLE IF NOT EXISTS businesses (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, business_name TEXT, income BIGINT, last_collect_time DOUBLE PRECISION DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS garage (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, car_key TEXT, car_name TEXT)",
            "CREATE TABLE IF NOT EXISTS daily_bonus (chat_id BIGINT, user_id BIGINT, last_claim DOUBLE PRECISION DEFAULT 0, streak INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS robbery (chat_id BIGINT, user_id BIGINT, last_robbery DOUBLE PRECISION DEFAULT 0, debt_amount BIGINT DEFAULT 0, debt_time DOUBLE PRECISION DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS lottery_tickets (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, buy_time DOUBLE PRECISION)",
            "CREATE TABLE IF NOT EXISTS usernames (chat_id BIGINT, user_id BIGINT, username TEXT, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS bank (chat_id BIGINT, user_id BIGINT, deposit BIGINT DEFAULT 0, last_interest_time DOUBLE PRECISION DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS education (chat_id BIGINT, user_id BIGINT, completed_courses TEXT[] DEFAULT '{}', has_mba BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS loans (chat_id BIGINT, user_id BIGINT, amount BIGINT DEFAULT 0, interest BIGINT DEFAULT 0, taken_at DOUBLE PRECISION DEFAULT 0, due_date DOUBLE PRECISION DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS jail (chat_id BIGINT, user_id BIGINT, release_time DOUBLE PRECISION DEFAULT 0, fine_per_hour INTEGER DEFAULT 50, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS jail_fines (chat_id BIGINT, user_id BIGINT, fine_amount BIGINT DEFAULT 0, debt_time DOUBLE PRECISION DEFAULT 0, paid BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS achievements (chat_id BIGINT, user_id BIGINT, achievement_id TEXT, unlocked_at DOUBLE PRECISION DEFAULT 0, PRIMARY KEY (chat_id, user_id, achievement_id))",
            "CREATE TABLE IF NOT EXISTS debts (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, lender_id BIGINT NOT NULL, borrower_id BIGINT NOT NULL, amount BIGINT NOT NULL, fee BIGINT NOT NULL, created_at DOUBLE PRECISION NOT NULL, deadline DOUBLE PRECISION NOT NULL, status TEXT DEFAULT 'active', reminder_sent BOOLEAN DEFAULT FALSE)",
            "CREATE TABLE IF NOT EXISTS state_debts (chat_id BIGINT NOT NULL, user_id BIGINT NOT NULL, amount BIGINT NOT NULL DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS cities (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, bonus_desc TEXT NOT NULL, bonus_type TEXT NOT NULL, bonus_value INTEGER DEFAULT 10)",
            "CREATE TABLE IF NOT EXISTS player_cities (chat_id BIGINT NOT NULL, user_id BIGINT NOT NULL, city_id INTEGER NOT NULL, moved_at DOUBLE PRECISION DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS city_treasury (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, amount BIGINT DEFAULT 0, PRIMARY KEY (chat_id, city_id))",
            "CREATE TABLE IF NOT EXISTS mayors (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, user_id BIGINT NOT NULL, elected_at DOUBLE PRECISION NOT NULL, expires_at DOUBLE PRECISION NOT NULL, approval_rating INTEGER DEFAULT 50, PRIMARY KEY (chat_id, city_id))",
            "CREATE TABLE IF NOT EXISTS mayor_candidates (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, user_id BIGINT NOT NULL, votes BIGINT DEFAULT 0, election_id TEXT NOT NULL, status TEXT DEFAULT 'active', UNIQUE(chat_id, city_id, user_id, election_id))",
            "CREATE TABLE IF NOT EXISTS mayor_votes (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, voter_id BIGINT NOT NULL, candidate_id BIGINT NOT NULL, election_id TEXT NOT NULL, PRIMARY KEY (chat_id, city_id, voter_id, election_id))",
            "CREATE TABLE IF NOT EXISTS city_decrees (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, mayor_id BIGINT NOT NULL, decree_type TEXT NOT NULL, active_until DOUBLE PRECISION NOT NULL)",
            "CREATE TABLE IF NOT EXISTS state_treasury (chat_id BIGINT PRIMARY KEY, amount BIGINT DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS federal_roles (chat_id BIGINT NOT NULL, role TEXT NOT NULL, user_id BIGINT NOT NULL, elected_at DOUBLE PRECISION NOT NULL, expires_at DOUBLE PRECISION NOT NULL, approval_rating INTEGER DEFAULT 50, PRIMARY KEY (chat_id, role))",
            "CREATE TABLE IF NOT EXISTS federal_candidates (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, role TEXT NOT NULL, user_id BIGINT NOT NULL, votes BIGINT DEFAULT 0, election_id TEXT NOT NULL, UNIQUE (chat_id, role, user_id, election_id))",
            "CREATE TABLE IF NOT EXISTS federal_votes (chat_id BIGINT NOT NULL, role TEXT NOT NULL, voter_id BIGINT NOT NULL, candidate_id BIGINT NOT NULL, election_id TEXT NOT NULL, PRIMARY KEY (chat_id, role, voter_id, election_id))",
            "CREATE TABLE IF NOT EXISTS federal_elections_start (chat_id BIGINT NOT NULL, role TEXT NOT NULL, election_id TEXT NOT NULL, started_at DOUBLE PRECISION NOT NULL, PRIMARY KEY (chat_id, role, election_id))",
            "CREATE TABLE IF NOT EXISTS mayor_elections_start (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, election_id TEXT NOT NULL, started_at DOUBLE PRECISION NOT NULL, PRIMARY KEY (chat_id, city_id, election_id))",
            "CREATE TABLE IF NOT EXISTS federal_decrees (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, role TEXT NOT NULL, decree_type TEXT NOT NULL, active_until DOUBLE PRECISION NOT NULL, UNIQUE (chat_id, role, decree_type))",
            "CREATE TABLE IF NOT EXISTS mayor_reports (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, mayor_id BIGINT NOT NULL, budget_allocated BIGINT DEFAULT 0, budget_spent BIGINT DEFAULT 0, report_deadline DOUBLE PRECISION NOT NULL, status TEXT DEFAULT 'pending', created_at DOUBLE PRECISION NOT NULL)",
            "CREATE TABLE IF NOT EXISTS impeachment_votes (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, role TEXT NOT NULL, voter_id BIGINT NOT NULL, voted_at DOUBLE PRECISION NOT NULL, UNIQUE(chat_id, role, voter_id))",
            "CREATE TABLE IF NOT EXISTS mayor_projects (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, mayor_id BIGINT NOT NULL, project_type TEXT NOT NULL, budget BIGINT NOT NULL, description TEXT DEFAULT '', status TEXT DEFAULT 'active', started_at DOUBLE PRECISION NOT NULL, deadline DOUBLE PRECISION NOT NULL, completed_at DOUBLE PRECISION, fail_count INTEGER DEFAULT 0, reviewed_by BIGINT, review_result TEXT)",
        ]
        for t in tables:
            await conn.execute(t)

        await conn.execute("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS coffee_level INTEGER DEFAULT 0")
        print("✅ База данных готова")


# --- БАЗОВЫЕ ФУНКЦИИ ---
async def save_username(cid, uid, name):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO usernames (chat_id, user_id, username) VALUES ($1,$2,$3) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET username=$3", cid, uid, name)


async def get_user(cid, uid):
    async with pool.acquire() as conn:
        b = await conn.fetchval("SELECT balance FROM users WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if b is not None:
            return {"balance": b}
        await conn.execute("INSERT INTO users (chat_id, user_id, balance) VALUES ($1,$2,0) ON CONFLICT DO NOTHING", cid, uid)
        return {"balance": 0}


async def update_balance(cid, uid, amt):
    await get_user(cid, uid)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance=balance+$1 WHERE chat_id=$2 AND user_id=$3", amt, cid, uid)


async def get_profile(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT job_key, level, last_work_time, coffee_level FROM profiles WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if not r:
            await conn.execute("INSERT INTO profiles (chat_id, user_id, job_key, level, last_work_time, coffee_level) VALUES ($1,$2,'novice',1,0,0) ON CONFLICT DO NOTHING", cid, uid)
            return {"job_key": "novice", "level": 1, "last_work_time": 0, "coffee_level": 0}
        d = dict(r)
        if d['job_key'] not in JOBS:
            d['job_key'] = 'novice'
        d['coffee_level'] = d.get('coffee_level') or 0
        return d


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
            now = time.time()
            await conn.execute("INSERT INTO bank (chat_id, user_id, deposit, last_interest_time) VALUES ($1,$2,0,$3) ON CONFLICT DO NOTHING", cid, uid, now)
            return {"deposit": 0, "last_interest_time": now}
        return dict(r)


async def update_bank(cid, uid, amt):
    await get_bank(cid, uid)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE bank SET deposit=deposit+$1 WHERE chat_id=$2 AND user_id=$3", amt, cid, uid)


async def calc_interest(dep, lt):
    days = (time.time() - (lt or time.time())) / 86400
    return int(dep * BANK_INTEREST_RATE * days), time.time()


async def get_education(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT completed_courses, has_mba FROM education WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if not r:
            await conn.execute("INSERT INTO education (chat_id, user_id, completed_courses, has_mba) VALUES ($1,$2,'{}',FALSE) ON CONFLICT DO NOTHING", cid, uid)
            return {"completed_courses": [], "has_mba": False}
        return {"completed_courses": r['completed_courses'] or [], "has_mba": r['has_mba']}


async def complete_course(cid, uid, ck):
    await get_education(cid, uid)
    async with pool.acquire() as conn:
        if ck == "mba":
            await conn.execute("UPDATE education SET has_mba=TRUE WHERE chat_id=$1 AND user_id=$2", cid, uid)
        else:
            await conn.execute(
                "UPDATE education SET completed_courses=array_append(completed_courses,$1) "
                "WHERE chat_id=$2 AND user_id=$3 AND NOT ($1 = ANY(completed_courses))", ck, cid, uid)


async def get_loan(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT amount, interest, taken_at, due_date FROM loans WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if not r:
            return {"amount": 0, "interest": 0, "taken_at": 0, "due_date": 0}
        return dict(r)


async def update_loan(cid, uid, amount, interest, taken_at, due_date):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO loans (chat_id, user_id, amount, interest, taken_at, due_date) VALUES ($1,$2,$3,$4,$5,$6) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET amount=$3, interest=$4, taken_at=$5, due_date=$6",
            cid, uid, amount, interest, taken_at, due_date)


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
        await conn.execute(
            "INSERT INTO jail (chat_id, user_id, release_time, fine_per_hour) VALUES ($1,$2,$3,$4) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET release_time=$3, fine_per_hour=$4",
            cid, uid, release_time, JAIL_FINE_PER_HOUR)
    return release_time


async def release_from_jail(cid, uid):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM jail WHERE chat_id=$1 AND user_id=$2", cid, uid)


async def find_lawyers_in_chat(cid):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT e.user_id, u.username FROM education e "
            "JOIN usernames u ON e.chat_id = u.chat_id AND e.user_id = u.user_id "
            "WHERE e.chat_id = $1 AND 'lawyer' = ANY(e.completed_courses)", cid)
        return [(r['user_id'], r['username']) for r in rows]


async def cleanup_old_cases():
    now = time.time()
    to_delete = [case_id for case_id, case in active_cases.items() if now - case.get("created", now) > 600]
    for case_id in to_delete:
        active_cases.pop(case_id, None)


async def auto_cleanup_timer(case_id):
    await asyncio.sleep(600)
    active_cases.pop(case_id, None)


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
        cars = await conn.fetch("SELECT car_key, car_name FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if cars:
            car_names = [CARS.get(c['car_key'], {}).get('name', c['car_name']) for c in cars]
            total_value += sum(CARS.get(c['car_key'], {}).get('price', 0) for c in cars)
            arrested.append(f"🚗 Машины: {', '.join(car_names)}")
            await conn.execute("DELETE FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)

    async with pool.acquire() as conn:
        businesses = await conn.fetch("SELECT business_name, income FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if businesses:
            biz_names = [b['business_name'] for b in businesses]
            for biz in businesses:
                total_value += (biz['income'] or 0) * 180
            arrested.append(f"🏢 Бизнесы: {', '.join(biz_names)}")
            await conn.execute("DELETE FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)

    async with pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name, rarity FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if items:
            item_names = [i['item_name'] for i in items]
            total_value += sum({'legendary': 5000, 'rare': 1000, 'common': 100}.get(i['rarity'], 100) for i in items)
            arrested.append(f"🎒 Предметы: {', '.join(item_names)}")
            await conn.execute("DELETE FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)

    p = await get_profile(cid, uid)
    if p['level'] > 1:
        total_value += (p['level'] - 1) * 5000
        arrested.append(f"💼 Профессия сброшена (был Ур.{p['level']})")
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET job_key='novice', level=1 WHERE chat_id=$1 AND user_id=$2", cid, uid)

    return arrested, total_value


# --- ДОСТИЖЕНИЯ ---
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
                    await conn.execute("INSERT INTO achievements (chat_id, user_id, achievement_id, unlocked_at) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING", cid, uid, ach_id, time.time())
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
        except Exception:
            pass


# --- ВЕБ-СЕРВЕР И ФОНОВЫЕ ЗАДАЧИ ---
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
        try:
            now = time.time()
            async with pool.acquire() as conn:
                chats = await conn.fetch("SELECT DISTINCT chat_id FROM lottery_tickets")
                for row in chats:
                    cid = row['chat_id']
                    tickets = await conn.fetch("SELECT id, user_id FROM lottery_tickets WHERE chat_id=$1 AND buy_time <= $2", cid, now - LOTTERY_INTERVAL)
                    if len(tickets) >= 2:
                        winner = random.choice(tickets)
                        bank = len(tickets) * LOTTERY_PRICE
                        await update_balance(cid, winner['user_id'], bank)
                        wname = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, winner['user_id']) or f"User{winner['user_id']}"
                        await conn.execute("DELETE FROM lottery_tickets WHERE chat_id=$1", cid)
                        try:
                            await bot.send_message(cid, f"🎉 <b>АВТО-РОЗЫГРЫШ!</b>\n\n🏆 {wname}\n💰 {fmt_money(bank)}", parse_mode="HTML")
                        except Exception:
                            pass
        except Exception as e:
            print(f"Ошибка лотереи: {e}")


async def loan_interest_loop():
    print("💳 Цикл кредитов запущен")
    while True:
        await asyncio.sleep(86400)
        try:
            async with pool.acquire() as conn:
                loans = await conn.fetch("SELECT chat_id, user_id, amount, interest, taken_at, due_date FROM loans WHERE amount>0")
            for loan in loans:
                cid, uid = loan['chat_id'], loan['user_id']
                total_debt = loan['amount'] + loan['interest']
                if time.time() > loan['due_date']:
                    user = await get_user(cid, uid)
                    if user['balance'] < total_debt:
                        arrested, confiscated_value = await arrest_player(cid, uid)
                        remaining_debt = total_debt - confiscated_value
                        current_bal = (await get_user(cid, uid))['balance']
                        if remaining_debt > 0 and current_bal > 0:
                            pay = min(current_bal, remaining_debt)
                            await update_balance(cid, uid, -pay)
                            remaining_debt -= pay
                        msg = f"🚔 <b>АРЕСТ ИМУЩЕСТВА!</b>\n\n💰 Долг: <b>{fmt_money(total_debt)}</b>\n📦 Конфисковано: <b>{fmt_money(confiscated_value)}</b>\n\n"
                        msg += "<b>Конфисковано:</b>\n" + ("\n".join([f"• {item}" for item in arrested]) or "• Нечего изъять")
                        if remaining_debt > 0:
                            msg += f"\n\n⛔ Остаток долга: <b>{fmt_money(remaining_debt)}</b>"
                        try:
                            await bot.send_message(cid, msg, parse_mode="HTML")
                        except Exception:
                            pass
                        await clear_loan(cid, uid)
                    else:
                        await update_balance(cid, uid, -total_debt)
                        await clear_loan(cid, uid)
                        try:
                            await bot.send_message(cid, f"✅ Кредит погашен автоматически со счета. Списано: {fmt_money(total_debt)}", parse_mode="HTML")
                        except Exception:
                            pass
                else:
                    daily_interest = int(loan['amount'] * CREDIT_DAILY_RATE)
                    await update_loan(cid, uid, loan['amount'], loan['interest'] + daily_interest, loan['taken_at'], loan['due_date'])
        except Exception as e:
            print(f"Ошибка кредитов: {e}")


async def jail_fine_check_loop():
    print("⚖️ Цикл проверки штрафов запущен")
    while True:
        await asyncio.sleep(300)
        try:
            async with pool.acquire() as conn:
                fines = await conn.fetch("SELECT * FROM jail_fines WHERE paid=FALSE AND fine_amount > 0")
            for fine in fines:
                cid, uid = fine['chat_id'], fine['user_id']
                if await is_in_jail(cid, uid):
                    continue
                user = await get_user(cid, uid)
                bank = await get_bank(cid, uid)
                total_available = user['balance'] + bank['deposit']
                if total_available >= fine['fine_amount']:
                    paid_from_balance = min(fine['fine_amount'], max(0, user['balance']))
                    remaining = fine['fine_amount'] - paid_from_balance
                    if paid_from_balance > 0:
                        await update_balance(cid, uid, -paid_from_balance)
                    if remaining > 0 and bank['deposit'] > 0:
                        await update_bank(cid, uid, -min(remaining, bank['deposit']))
                    async with pool.acquire() as conn:
                        await conn.execute("UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2", cid, uid)
                    continue

                if fine['debt_time'] > 0 and time.time() - fine['debt_time'] > JAIL_DEBT_TIMEOUT:
                    if user['balance'] < JAIL_DEBT_THRESHOLD:
                        arrested, _ = await arrest_player(cid, uid)
                        async with pool.acquire() as conn:
                            await conn.execute("UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2", cid, uid)
                        username = await safe_name(cid, uid)
                        try:
                            msg = f"🚔 <b>АРЕСТ ЗА НЕОПЛАЧЕННЫЙ ШТРАФ!</b>\n\n👤 {username}\n\n<b>Конфисковано:</b>\n" + "\n".join([f"• {i}" for i in arrested])
                            await bot.send_message(cid, msg, parse_mode="HTML")
                        except Exception:
                            pass
        except Exception as e:
            print(f"Ошибка штрафов: {e}")


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
            if collected >= total_debt:
                break
            car_price = next((data['price'] for data in CARS.values() if data['name'] == car['car_name']), 0)
            if car_price > 0:
                await conn.execute("DELETE FROM garage WHERE id=$1", car['id'])
                collected += car_price
                seized_items.append(f"🚗 {car['car_name']} ({fmt_money(car_price)})")

        if collected < total_debt:
            businesses = await conn.fetch("SELECT id, business_name FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, borrower_id)
            for biz in businesses:
                if collected >= total_debt:
                    break
                biz_price = next((data['price'] for data in MARKET.values() if data.get('type') == 'business' and data['name'] == biz['business_name']), 50000)
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
    async with pool.acquire() as conn:
        if remaining > 0:
            await conn.execute(
                "INSERT INTO state_debts (chat_id, user_id, amount) VALUES ($1,$2,$3) "
                "ON CONFLICT (chat_id, user_id) DO UPDATE SET amount=state_debts.amount+$3", cid, borrower_id, remaining)
        await conn.execute("UPDATE debts SET status='collected' WHERE id=$1", debt['id'])
    await update_balance(cid, lender_id, debt_amount)

    b_name = await safe_name(cid, borrower_id)
    seized_text = "\n".join(seized_items) if seized_items else "Ничего не найдено"
    try:
        await bot.send_message(cid, f"🚨 <b>КОЛЛЕКТОРЫ ЯВИЛИСЬ!</b>\n\n👤 {b_name}\n📜 Долг: {fmt_money(debt_amount)} + {fmt_money(penalty)} штраф\n\n🗑️ <b>Изъято:</b>\n{seized_text}", parse_mode="HTML")
    except Exception:
        pass


# --- РАСХОДЫ КАЗНЫ ---
async def federal_expenses_loop():
    print("🏛️ Цикл федеральных расходов запущен")
    while True:
        await asyncio.sleep(86400)
        try:
            async with pool.acquire() as conn:
                chats = await conn.fetch("SELECT DISTINCT chat_id FROM state_treasury")
            for row in chats:
                cid = row['chat_id']
                treasury = await get_state_treasury(cid)
                if treasury < MIN_TREASURY_BALANCE:
                    continue

                president = await get_federal_role(cid, 'president')
                prime = await get_federal_role(cid, 'prime_minister')
                total_expenses = 0

                if president:
                    await update_balance(cid, president['user_id'], FEDERAL_SALARY_PRESIDENT)
                    total_expenses += FEDERAL_SALARY_PRESIDENT
                if prime:
                    await update_balance(cid, prime['user_id'], FEDERAL_SALARY_PRIME)
                    total_expenses += FEDERAL_SALARY_PRIME

                async with pool.acquire() as conn:
                    players = await conn.fetch("SELECT user_id, balance FROM users WHERE chat_id=$1 AND balance < 0", cid)
                social_aid = len(players) * FEDERAL_SOCIAL_AID
                if social_aid > 0 and treasury >= social_aid:
                    for player in players:
                        aid = min(FEDERAL_SOCIAL_AID, abs(player['balance']))
                        await update_balance(cid, player['user_id'], aid)
                    total_expenses += social_aid

                if treasury >= FEDERAL_INFRASTRUCTURE:
                    total_expenses += FEDERAL_INFRASTRUCTURE

                if total_expenses > 0:
                    await update_state_treasury(cid, -total_expenses)
        except Exception as e:
            print(f"Ошибка федеральных расходов: {e}")


async def city_expenses_loop():
    print("🏙️ Цикл городских расходов запущен")
    while True:
        await asyncio.sleep(86400)
        try:
            async with pool.acquire() as conn:
                treasuries = await conn.fetch("SELECT DISTINCT chat_id, city_id FROM city_treasury")
            for row in treasuries:
                cid = row['chat_id']
                city_id = row['city_id']
                treasury = await get_city_treasury(cid, city_id)
                if treasury < MIN_TREASURY_BALANCE:
                    continue

                city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
                if not city:
                    continue

                total_expenses = 0
                mayor = await get_mayor(cid, city_id)
                if mayor:
                    await update_balance(cid, mayor['user_id'], CITY_SALARY_MAYOR)
                    total_expenses += CITY_SALARY_MAYOR

                if treasury >= CITY_UTILITIES:
                    total_expenses += CITY_UTILITIES

                async with pool.acquire() as conn:
                    residents = await conn.fetch(
                        "SELECT u.user_id, u.balance FROM users u "
                        "JOIN player_cities pc ON u.chat_id = pc.chat_id AND u.user_id = pc.user_id "
                        "WHERE pc.chat_id=$1 AND pc.city_id=$2 AND u.balance < 0", cid, city_id)
                social_expenses = len(residents) * CITY_SOCIAL_PROGRAMS
                if social_expenses > 0 and treasury >= social_expenses:
                    for resident in residents:
                        aid = min(CITY_SOCIAL_PROGRAMS, abs(resident['balance']))
                        await update_balance(cid, resident['user_id'], aid)
                    total_expenses += social_expenses

                if total_expenses > 0:
                    await update_city_treasury(cid, city_id, -total_expenses)
        except Exception as e:
            print(f"Ошибка городских расходов: {e}")


# --- ГОРОДА И ПОЛИТИКА ---
async def init_cities():
    try:
        async with pool.acquire() as conn:
            for city in CITIES_LIST:
                await conn.execute(
                    "INSERT INTO cities (id, name, bonus_desc, bonus_type, bonus_value) VALUES ($1,$2,$3,$4,$5) "
                    "ON CONFLICT (id) DO NOTHING", city['id'], city['name'], city['desc'], city['bonus_type'], city['bonus_value'])
            await conn.execute("SELECT setval(pg_get_serial_sequence('cities','id'), (SELECT MAX(id) FROM cities))")
        print(f"🏙️ Инициализировано {len(CITIES_LIST)} городов")
    except Exception as e:
        print(f"❌ Ошибка инициализации городов: {e}")


async def get_player_city(cid, uid):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT city_id, moved_at FROM player_cities WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if not row:
            return None
        for city in CITIES_LIST:
            if city['id'] == row['city_id']:
                city_copy = city.copy()
                city_copy['moved_at'] = row['moved_at']
                return city_copy
        return None
    except Exception:
        return None


async def set_player_city(cid, uid, city_id):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO player_cities (chat_id, user_id, city_id, moved_at) VALUES ($1,$2,$3,$4) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET city_id=$3, moved_at=$4", cid, uid, city_id, time.time())


async def get_city_treasury(cid, city_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT amount FROM city_treasury WHERE chat_id=$1 AND city_id=$2", cid, city_id)
        return row['amount'] if row else 0
    except Exception:
        return 0


async def update_city_treasury(cid, city_id, amount):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO city_treasury (chat_id, city_id, amount) VALUES ($1,$2,$3) "
            "ON CONFLICT (chat_id, city_id) DO UPDATE SET amount = city_treasury.amount + $3", cid, city_id, amount)


async def update_state_treasury(cid, amount):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO state_treasury (chat_id, amount) VALUES ($1,$2) "
            "ON CONFLICT (chat_id) DO UPDATE SET amount = state_treasury.amount + $2", cid, amount)


async def get_state_treasury(cid):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT amount FROM state_treasury WHERE chat_id=$1", cid)
    return row['amount'] if row else 0


async def get_mayor(cid, city_id):
    try:
        async with pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM mayors WHERE chat_id=$1 AND city_id=$2 AND expires_at > $3", cid, city_id, time.time())
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
        existing = await conn.fetchrow("SELECT * FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND user_id=$3 AND election_id=$4", cid, city_id, uid, election_id)
        if existing:
            return False, "❌ Уже выдвинут!"
        await update_balance(cid, uid, -MAYOR_ELECTION_FEE)
        await conn.execute("INSERT INTO mayor_candidates (chat_id, city_id, user_id, election_id) VALUES ($1,$2,$3,$4)", cid, city_id, uid, election_id)
        existing_start = await conn.fetchrow("SELECT * FROM mayor_elections_start WHERE chat_id=$1 AND city_id=$2 AND election_id=$3", cid, city_id, election_id)
        if not existing_start:
            await conn.execute("INSERT INTO mayor_elections_start (chat_id, city_id, election_id, started_at) VALUES ($1,$2,$3,$4)", cid, city_id, election_id, time.time())
    return True, f"✅ Выдвинут!\n💸 {fmt_money(MAYOR_ELECTION_FEE)}"


async def vote_for_mayor(cid, uid, city_id, candidate_num):
    user = await get_user(cid, uid)
    if user['balance'] < MAYOR_VOTE_COST:
        return False, f"❌ Голос стоит {MAYOR_VOTE_COST}"

    election_id = await get_current_election_id(cid, city_id)
    async with pool.acquire() as conn:
        candidates = await conn.fetch("SELECT id, user_id, votes FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3 ORDER BY id ASC", cid, city_id, election_id)
        if not candidates:
            return False, "❌ Нет кандидатов!"
        if candidate_num < 1 or candidate_num > len(candidates):
            return False, f"❌ 1-{len(candidates)}"

        target_candidate = candidates[candidate_num - 1]
        already_voted = await conn.fetchrow("SELECT * FROM mayor_votes WHERE chat_id=$1 AND city_id=$2 AND voter_id=$3 AND election_id=$4", cid, city_id, uid, election_id)
        if already_voted:
            return False, "❌ Уже голосовал!"
        if target_candidate['user_id'] == uid:
            return False, "❌ Нельзя за себя!"

        await update_balance(cid, uid, -MAYOR_VOTE_COST)
        await update_city_treasury(cid, city_id, MAYOR_VOTE_COST)
        await conn.execute("INSERT INTO mayor_votes (chat_id, city_id, voter_id, candidate_id, election_id) VALUES ($1,$2,$3,$4,$5)", cid, city_id, uid, target_candidate['id'], election_id)
        await conn.execute("UPDATE mayor_candidates SET votes = votes + 1 WHERE id=$1", target_candidate['id'])
    return True, f"✅ Голос принят!\n💸 {MAYOR_VOTE_COST}"


async def finalize_mayor_election(cid, city_id):
    election_id = await get_current_election_id(cid, city_id)
    async with pool.acquire() as conn:
        candidates = await conn.fetch("SELECT * FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3 ORDER BY votes DESC, id ASC", cid, city_id, election_id)
        if not candidates:
            return None

        winner = candidates[0]
        expires_at = time.time() + MAYOR_TERM_DAYS * 86400
        await conn.execute(
            "INSERT INTO mayors (chat_id, city_id, user_id, elected_at, expires_at, approval_rating) VALUES ($1,$2,$3,$4,$5,50) "
            "ON CONFLICT (chat_id, city_id) DO UPDATE SET user_id=$3, elected_at=$4, expires_at=$5, approval_rating=50",
            cid, city_id, winner['user_id'], time.time(), expires_at)

        await conn.execute("DELETE FROM mayor_votes WHERE chat_id=$1 AND city_id=$2 AND election_id=$3", cid, city_id, election_id)
        await conn.execute("DELETE FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3", cid, city_id, election_id)
        await conn.execute("DELETE FROM mayor_elections_start WHERE chat_id=$1 AND city_id=$2 AND election_id=$3", cid, city_id, election_id)

    try:
        await update_balance(cid, winner['user_id'], MAYOR_ELECTION_FEE + MAYOR_WIN_BONUS)
    except Exception as e:
        print(f"Ошибка бонуса: {e}")

    return {"user_id": winner['user_id'], "votes": winner['votes'], "bonus": MAYOR_WIN_BONUS}


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
        existing = await conn.fetchrow("SELECT * FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND user_id=$3 AND election_id=$4", cid, role, uid, election_id)
        if existing:
            return False, "❌ Уже выдвинут!"
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
    if user['balance'] < cost:
        return False, f"❌ Голос стоит {fmt_money(cost)}"

    election_id = await get_current_federal_election_id(cid, role)
    async with pool.acquire() as conn:
        candidates = await conn.fetch("SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND election_id=$3 ORDER BY id ASC", cid, role, election_id)
        if not candidates:
            return False, "❌ Нет кандидатов!"
        if candidate_num < 1 or candidate_num > len(candidates):
            return False, f"❌ 1-{len(candidates)}"

        target_candidate = candidates[candidate_num - 1]
        if target_candidate['user_id'] == uid:
            return False, "❌ Нельзя за себя!"
        already_voted = await conn.fetchrow("SELECT * FROM federal_votes WHERE chat_id=$1 AND role=$2 AND voter_id=$3 AND election_id=$4", cid, role, uid, election_id)
        if already_voted:
            return False, "❌ Уже голосовал!"

        await update_balance(cid, uid, -cost)
        await update_state_treasury(cid, cost)
        await conn.execute("INSERT INTO federal_votes (chat_id, role, voter_id, candidate_id, election_id) VALUES ($1,$2,$3,$4,$5)", cid, role, uid, target_candidate['id'], election_id)
        await conn.execute("UPDATE federal_candidates SET votes = votes + 1 WHERE id=$1", target_candidate['id'])
    return True, f"✅ Голос принят!\n💸 {fmt_money(cost)}"


async def finalize_federal_election(cid, role):
    election_id = await get_current_federal_election_id(cid, role)
    async with pool.acquire() as conn:
        candidates = await conn.fetch("SELECT * FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND election_id=$3 ORDER BY votes DESC, id ASC", cid, role, election_id)
        if not candidates:
            return None

        winner = candidates[0]
        term_days = PRESIDENT_TERM_DAYS if role == 'president' else PRIME_MINISTER_TERM_DAYS
        win_bonus = PRESIDENT_WIN_BONUS if role == 'president' else PRIME_MINISTER_WIN_BONUS
        election_fee = PRESIDENT_ELECTION_FEE if role == 'president' else PRIME_MINISTER_ELECTION_FEE

        expires_at = time.time() + term_days * 86400
        await conn.execute(
            "INSERT INTO federal_roles (chat_id, role, user_id, elected_at, expires_at, approval_rating) VALUES ($1,$2,$3,$4,$5,50) "
            "ON CONFLICT (chat_id, role) DO UPDATE SET user_id=$3, elected_at=$4, expires_at=$5, approval_rating=50",
            cid, role, winner['user_id'], time.time(), expires_at)

        await conn.execute("DELETE FROM federal_votes WHERE chat_id=$1 AND role=$2 AND election_id=$3", cid, role, election_id)
        await conn.execute("DELETE FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND election_id=$3", cid, role, election_id)
        await conn.execute("DELETE FROM federal_elections_start WHERE chat_id=$1 AND role=$2 AND election_id=$3", cid, role, election_id)

    try:
        await update_balance(cid, winner['user_id'], election_fee + win_bonus)
    except Exception as e:
        print(f"Ошибка бонуса: {e}")

    return {"user_id": winner['user_id'], "votes": winner['votes'], "bonus": win_bonus}


async def get_federal_role(cid, role):
    try:
        async with pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM federal_roles WHERE chat_id=$1 AND role=$2 AND expires_at > $3", cid, role, time.time())
    except Exception:
        return None


async def is_mayor(cid, uid, city_id):
    mayor = await get_mayor(cid, city_id)
    return bool(mayor and mayor['user_id'] == uid)


async def is_federal_official(cid, uid, role):
    official = await get_federal_role(cid, role)
    return bool(official and official['user_id'] == uid)


async def get_active_decree(cid, city_id, decree_type):
    try:
        async with pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM city_decrees WHERE chat_id=$1 AND city_id=$2 AND decree_type=$3 AND active_until > $4", cid, city_id, decree_type, time.time())
    except Exception:
        return None


async def get_active_federal_decree(cid, role, decree_type):
    try:
        async with pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM federal_decrees WHERE chat_id=$1 AND role=$2 AND decree_type=$3 AND active_until > $4", cid, role, decree_type, time.time())
    except Exception:
        return None


async def apply_income_tax(cid, uid, gross_income):
    tax_cut = await get_active_federal_decree(cid, 'president', 'tax_cut')
    tax_boost_president = await get_active_federal_decree(cid, 'president', 'tax_boost')
    tax_boost_prime = await get_active_federal_decree(cid, 'prime_minister', 'tax_boost')

    if tax_cut:
        tax_rate = 5
    elif tax_boost_president or tax_boost_prime:
        tax_rate = 15
    else:
        tax_rate = TAX_RATE_PERCENT

    tax_amount = int(gross_income * tax_rate / 100)
    net_income = gross_income - tax_amount

    player_city = await get_player_city(cid, uid)
    if player_city:
        city_tax = int(tax_amount * 0.7)
        federal_tax = tax_amount - city_tax
        await update_city_treasury(cid, player_city['id'], city_tax)
        await update_state_treasury(cid, federal_tax)
        receiver = f"казну г. {player_city['name']} ({fmt_money(city_tax)}) + фед. ({fmt_money(federal_tax)})"
    else:
        await update_state_treasury(cid, tax_amount)
        receiver = "фед. казну"

    return net_income, tax_amount, receiver, tax_rate


async def apply_business_tax(cid, uid, gross_profit):
    tax_cut = await get_active_federal_decree(cid, 'president', 'tax_cut')
    tax_boost_president = await get_active_federal_decree(cid, 'president', 'tax_boost')
    tax_boost_prime = await get_active_federal_decree(cid, 'prime_minister', 'tax_boost')

    if tax_cut:
        tax_rate = 8
    elif tax_boost_president or tax_boost_prime:
        tax_rate = 18
    else:
        tax_rate = 12

    tax_amount = int(gross_profit * tax_rate / 100)
    net_profit = gross_profit - tax_amount

    city_tax = int(tax_amount * 0.6)
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
        await conn.execute("INSERT INTO city_decrees (chat_id, city_id, mayor_id, decree_type, active_until) VALUES ($1,$2,$3,$4,$5)", cid, city_id, mayor_id, decree_type, active_until)
    return True, f"✅ Указ издан! {duration_hours} часов.\n💸 Списано: {cost}"


def get_decree_cost(decree_type):
    costs = {'work_bonus': 5000, 'tool_discount': 3000, 'business_bonus': 8000, 'car_discount': 4000, 'city_event': 10000}
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
            "INSERT INTO federal_decrees (chat_id, role, decree_type, active_until) VALUES ($1,$2,$3,$4) "
            "ON CONFLICT (chat_id, role, decree_type) DO UPDATE SET active_until=$4", cid, role, decree_type, active_until)

    role_name = "Президент" if role == 'president' else "Премьер-министр"
    return True, f"✅ Указ {role_name} издан!\n⏰ {duration} часов."


def get_federal_decree_name(decree_type):
    names = {
        'amnesty': '🕊️ Амнистия',
        'tax_cut': '📉 Снижение налога до 5%',
        'tax_boost': '📈 Повышение до 15%',
        'emergency': '🚨 ЧП',
        'subsidy': '💰 Субсидии (+10%)',
        'investment': '🏗️ Инвестиции (+5000)',
    }
    return names.get(decree_type, 'Неизвестный указ')


# --- ПРОВЕРКА ВЫБОРОВ И СРОКОВ ---
async def check_all_elections_and_terms():
    print("🏛️ Единая проверка сроков и выборов запущена")
    while True:
        await asyncio.sleep(3600)
        try:
            now = time.time()
            async with pool.acquire() as conn:
                expired_mayors = await conn.fetch("SELECT chat_id, city_id FROM mayors WHERE expires_at <= $1", now)
                expired_mayor_elections = await conn.fetch("SELECT chat_id, city_id, election_id FROM mayor_elections_start WHERE started_at < $1", now - MAYOR_ELECTION_DURATION)
                expired_federal = await conn.fetch("SELECT chat_id, role FROM federal_roles WHERE expires_at <= $1", now)
                expired_federal_elections = await conn.fetch("SELECT chat_id, role, election_id FROM federal_elections_start WHERE started_at < $1", now - FEDERAL_ELECTION_DURATION)

            for mayor_data in expired_mayors:
                cid = mayor_data['chat_id']
                city_id = mayor_data['city_id']
                async with pool.acquire() as conn:
                    await conn.execute("DELETE FROM mayors WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                    await conn.execute("DELETE FROM mayor_elections_start WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
                if city:
                    try:
                        await bot.send_message(cid, f"🏛️ <b>СРОК МЭРА В {city['emoji']} {city['name']} ИСТЁК!</b>\n\n⏳ Открыто окно для новых выборов на 24 часа.\nИспользуйте /mayor_nominate", parse_mode="HTML")
                    except Exception:
                        pass

            for elec in expired_mayor_elections:
                cid = elec['chat_id']
                city_id = elec['city_id']
                result = await finalize_mayor_election(cid, city_id)
                city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
                if city:
                    if result:
                        winner_name = await safe_name(cid, result['user_id'])
                        msg = f"🎉 <b>ВЫБОРЫ МЭРА В {city['emoji']} {city['name']} ЗАВЕРШЕНЫ!</b>\n\n👤 Победитель: {winner_name}\n🗳️ Голосов: {result['votes']}\n⏰ Срок: {MAYOR_TERM_DAYS} дней"
                    else:
                        msg = f"🏛️ <b>ВЫБОРЫ МЭРА В {city['emoji']} {city['name']} ЗАВЕРШЕНЫ</b>\n\n❌ Никто не баллотировался."
                    try:
                        await bot.send_message(cid, msg, parse_mode="HTML")
                    except Exception:
                        pass

            for role_data in expired_federal:
                cid = role_data['chat_id']
                role = role_data['role']
                async with pool.acquire() as conn:
                    await conn.execute("DELETE FROM federal_roles WHERE chat_id=$1 AND role=$2", cid, role)
                    await conn.execute("DELETE FROM federal_elections_start WHERE chat_id=$1 AND role=$2", cid, role)
                role_name = "Президент" if role == 'president' else "Премьер-министр"
                emoji = "🏛️" if role == 'president' else "💼"
                cmd = 'president' if role == 'president' else 'prime'
                try:
                    await bot.send_message(cid, f"{emoji} <b>СРОК ПОЛНОМОЧИЙ {role_name.upper()} ИСТЁК!</b>\n\n⏳ Открыто окно для новых выборов на 24 часа.\nИспользуйте /{cmd}_nominate", parse_mode="HTML")
                except Exception:
                    pass

            for elec in expired_federal_elections:
                cid = elec['chat_id']
                role = elec['role']
                result = await finalize_federal_election(cid, role)
                role_name = "Президент" if role == 'president' else "Премьер-министр"
                emoji = "🏛️" if role == 'president' else "💼"
                term = PRESIDENT_TERM_DAYS if role == 'president' else PRIME_MINISTER_TERM_DAYS
                if result:
                    winner_name = await safe_name(cid, result['user_id'])
                    msg = f"{emoji} <b>ВЫБОРЫ {role_name.upper()} ЗАВЕРШЕНЫ!</b>\n\n👤 Победитель: {winner_name}\n🗳️ Голосов: {result['votes']}\n⏰ Срок: {term} дней"
                else:
                    msg = f"{emoji} <b>ВЫБОРЫ {role_name.upper()} ЗАВЕРШЕНЫ</b>\n\n❌ Никто не баллотировался."
                try:
                    await bot.send_message(cid, msg, parse_mode="HTML")
                except Exception:
                    pass
        except Exception as e:
            print(f"Ошибка проверки выборов и сроков: {e}")


# --- ПРОВЕРКА ПРОСРОЧЕННЫХ ПРОЕКТОВ ---
async def check_overdue_projects():
    print("⏰ Цикл проверки проектов мэров запущен")
    while True:
        await asyncio.sleep(1800)
        try:
            async with pool.acquire() as conn:
                overdue = await conn.fetch("SELECT * FROM mayor_projects WHERE status='active' AND deadline < $1", time.time())
            for proj in overdue:
                cid = proj['chat_id']
                city_id = proj['city_id']
                mayor_id = proj['mayor_id']
                fail_count = (proj['fail_count'] or 0) + 1
                city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
                city_name = city['name'] if city else f"город #{city_id}"
                mayor_name = await safe_name(cid, mayor_id)

                if fail_count >= 2:
                    await send_to_jail(cid, mayor_id, 6)
                    async with pool.acquire() as conn:
                        await conn.execute("DELETE FROM mayors WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                        await conn.execute("UPDATE mayor_projects SET status='failed', fail_count=$1, review_result='Авто-снятие' WHERE id=$2", fail_count, proj['id'])
                    msg = f"🚨 <b>МЭР АВТОМАТИЧЕСКИ СНЯТ!</b>\n\n🏙️ {city_name}\n👤 {mayor_name}\n⚠️ 2-й провал (просрочка)\n🔒 Тюрьма: 6 часов\n📉 Должность: ВАКАНТНО"
                else:
                    fine = int(proj['budget'] * 0.50)
                    await update_balance(cid, mayor_id, -fine)
                    async with pool.acquire() as conn:
                        await conn.execute("UPDATE mayors SET approval_rating = GREATEST(0, approval_rating - 20) WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                        await conn.execute("UPDATE mayor_projects SET status='failed', fail_count=$1, review_result='Авто-штраф' WHERE id=$2", fail_count, proj['id'])
                    msg = f"⏰ <b>ПРОЕКТ ПРОСРОЧЕН!</b>\n\n🏙️ {city_name}\n👤 Мэр: {mayor_name}\n💸 Авто-штраф: {fmt_money(fine)}\n📉 Рейтинг: -20%\n⚠️ Провалов: {fail_count}/2"
                try:
                    await bot.send_message(cid, msg, parse_mode="HTML")
                except Exception:
                    pass
        except Exception as e:
            print(f"Ошибка проверки проектов: {e}")


# --- МЕНЮ С КНОПКАМИ ---
@dp.message(Command("start", "help"))
async def cmd_start(m: Message):
    await get_user(m.chat.id, m.from_user.id)
    await save_username(m.chat.id, m.from_user.id, m.from_user.full_name)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Финансы", callback_data="menu_finance"), InlineKeyboardButton(text="💼 Работа", callback_data="menu_work")],
        [InlineKeyboardButton(text="🏪 Бизнес", callback_data="menu_business"), InlineKeyboardButton(text="🚗 Авто", callback_data="menu_cars")],
        [InlineKeyboardButton(text="🎓 Образование", callback_data="menu_edu"), InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        [InlineKeyboardButton(text="🏛️ Политика", callback_data="menu_politics"), InlineKeyboardButton(text="📊 Инфо", callback_data="menu_info")],
    ])
    await m.answer(f"🎩 <b>Добро пожаловать в мир Сарапулок!</b>\n\n👤 {m.from_user.full_name}\n\nВыберите раздел:", reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(lambda c: c.data and c.data.startswith("menu_"))
async def callback_menu(callback: CallbackQuery):
    uid = callback.from_user.id
    cid = callback.message.chat.id
    action = callback.data.replace("menu_", "")

    try:
        if action == "finance":
            u = await get_user(cid, uid)
            bd = await get_bank(cid, uid)
            text = (f"💰 <b>ФИНАНСЫ</b>\n\n💵 Баланс: <b>{fmt_money(u['balance'])}</b>\n🏦 Банк: <b>{fmt_money(bd['deposit'])}</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/balance\n/bank\n/deposit сумма\n/withdraw сумма\n/pay сумма\n/credit сумма\n/debt\n/repay сумма\n/repay_all\n/debt_give\n/debt_return\n/debt_list")
        elif action == "work":
            p = await get_profile(cid, uid)
            j = JOBS[p['job_key']]
            text = (f"💼 <b>РАБОТА</b>\n\n🔹 {j['name']} (Ур.{p['level']})\n💰 {fmt_money(j['base_pay'] * p['level'])}/ч\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/work\n/jobs\n/job ключ\n/shop\n/buy course\n/buy coffee")
        elif action == "business":
            async with pool.acquire() as conn:
                bc = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
            text = (f"🏪 <b>БИЗНЕС</b>\n\n🏢 У вас: <b>{bc}</b> бизнес(ов)\n⚠️ Лимит одного типа: <b>{MAX_BUSINESSES_PER_TYPE}</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/market — открыть магазин\n/buy_market ключ — купить\n/collect — собрать прибыль\n/my_businesses — мои бизнесы\n/inv — инвентарь\n/craft — крафт\n/craft_item ключ\n/trade предмет кол-во (ответ)")
        elif action == "cars":
            c = await get_car(cid, uid)
            text = (f"🚗 <b>АВТОСАЛОН</b>\n\n🅿️ {c or 'нет'}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/cars — каталог\n/buycar ключ — купить\n/mycar — мои машины")
        elif action == "edu":
            edu = await get_education(cid, uid)
            cc = len(edu['completed_courses']) + (1 if edu['has_mba'] else 0)
            text = (f"🎓 <b>ОБРАЗОВАНИЕ</b>\n\n📚 Пройдено: <b>{cc}</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/education — список курсов\n/buy_course ключ — купить курс\nКурсы: miner, coder, trader, lawyer, mba")
        elif action == "games":
            text = ("🎮 <b>ИГРЫ</b>\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n"
                    "🎲 /dice сумма — кости (шанс 50%)\n🎟️ /buy_ticket — лотерея (50 сарапулок)\n🎁 /daily — ежедневный бонус\n🔫 /rob (ответ) — ограбление")
        elif action == "politics":
            president = await get_federal_role(cid, 'president')
            president_text = "👤 ВАКАНТНО"
            if president:
                p_name = await safe_name(cid, president['user_id'])
                days_left = int((president['expires_at'] - time.time()) / 86400)
                president_text = f"👤 {p_name} ({days_left} дн.)"

            prime = await get_federal_role(cid, 'prime_minister')
            prime_text = "👤 ВАКАНТНО"
            if prime:
                pr_name = await safe_name(cid, prime['user_id'])
                days_left = int((prime['expires_at'] - time.time()) / 86400)
                prime_text = f"👤 {pr_name} ({days_left} дн.)"

            state_treasury = await get_state_treasury(cid)
            mayors_text = ""
            for city in CITIES_LIST:
                mayor = await get_mayor(cid, city['id'])
                city_treasury = await get_city_treasury(cid, city['id'])
                if mayor:
                    m_name = await safe_name(cid, mayor['user_id'])
                    days_left = int((mayor['expires_at'] - time.time()) / 86400)
                    mayors_text += f"{city['emoji']} {city['name']}: {m_name} ({days_left} дн.) | Казна: {city_treasury}\n"
                else:
                    mayors_text += f"{city['emoji']} {city['name']}: ВАКАНТНО | Казна: {city_treasury}\n"

            text = (f"🏛️ <b>ПОЛИТИКА</b>\n\n🇷🇺 Президент: {president_text}\n💼 Премьер: {prime_text}\n🏛️ Фед. казна: {fmt_money(state_treasury)}\n\n"
                    f"🏙️ <b>Мэры:</b>\n{mayors_text}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n📋 <b>Города:</b>\n/city list\n/city choose [город]\n/city move [город]\n/city info\n/city residents\n\n"
                    f"🏛️ <b>Мэр:</b>\n/mayor_nominate (30к)\n/mayor_vote (500)\n/mayor_decree\n/mayor_report\n/mayor_finalize\n/city_decrees\n/mayor_project\n/project_done\n/project_check [город] approve/reject\n/project_status\n\n"
                    f"🇷🇺 <b>Президент (90 дней):</b>\n/president_nominate (50к)\n/president_vote (1000)\n/president_decree\n/president_decrees\n/president_finalize\n\n"
                    f"💼 <b>Премьер (90 дней):</b>\n/prime_nominate (40к)\n/prime_vote (800)\n/prime_decree\n/prime_decrees\n/prime_finalize\n\n"
                    f"⚖️ <b>Импичмент:</b>\n/impeach president\n/impeach prime\n\n💰 <b>Бюджет:</b>\n/budget")
        elif action == "info":
            u = await get_user(cid, uid)
            p = await get_profile(cid, uid)
            in_jail = await is_in_jail(cid, uid)
            jail_text = "\n🔒 <b>В ТЮРЬМЕ!</b>" if in_jail else ""
            debt_text = f"\n⛔ ДОЛГ: {fmt_money(abs(u['balance']))}" if u['balance'] < 0 else ""
            text = (f"📊 <b>КАРТОЧКА ИГРОКА</b>\n\n👤 {callback.from_user.full_name}\n💰 Баланс: {fmt_money(u['balance'])}\n"
                    f"💼 Профессия: {JOBS[p['job_key']]['name']} (Ур.{p['level']}){jail_text}{debt_text}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/info\n/rating\n/achievements\n/budget")
        else:
            return await callback.answer()

        await callback.message.edit_text(text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка меню: {e}")
    await callback.answer()


# --- МАРКЕТ ---
@dp.message(Command("market"))
async def cmd_market(m: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Кейсы", callback_data="market_cases")],
        [InlineKeyboardButton(text="🏢 Малый бизнес", callback_data="market_small")],
        [InlineKeyboardButton(text="🏭 Средний бизнес", callback_data="market_medium")],
        [InlineKeyboardButton(text="🏗️ Крупный бизнес", callback_data="market_large")],
        [InlineKeyboardButton(text="👑 Элитный бизнес", callback_data="market_elite")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="menu_business")],
    ])
    await m.answer(
        "🏪 <b>МАГАЗИН БИЗНЕСА</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>Категории:</b>\n\n"
        "📦 <b>Кейсы</b> — случайные предметы\n"
        "🏢 <b>Малый бизнес</b> — от 500 до 15к\n"
        "🏭 <b>Средний бизнес</b> — от 30к до 150к\n"
        "🏗️ <b>Крупный бизнес</b> — от 500к до 15М\n"
        "👑 <b>Элитный бизнес</b> — от 50М до 1МЛРД\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Лимит: <b>10 бизнесов</b> одного типа\n"
        "💡 Купи бизнес → /collect раз в 24ч → прибыль!",
        reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(lambda c: c.data and c.data.startswith("market_"))
async def callback_market(callback: CallbackQuery):
    action = callback.data.replace("market_", "")
    try:
        if action == "cases":
            text = "📦 <b>КЕЙСЫ</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"
            for k, v in MARKET.items():
                if v["type"] == "case":
                    text += f"🔹 {v['name']}\n   💰 Цена: {fmt_money(v['price'])}\n   🛒 /buy_market {k}\n\n"
            text += "━━━━━━━━━━━━━━━━━━━━\n🎁 Шансы:\n🟡 Легендарный: 5%\n🔵 Редкий: 20%\n🟢 Обычный: 75%"
            await callback.message.edit_text(text, parse_mode="HTML")
        elif action in ("small", "medium", "large", "elite"):
            ranges = {
                "small": (0, 15000, "МАЛЫЙ БИЗНЕС", "Идеально для начинающих!"),
                "medium": (15000, 150000, "СРЕДНИЙ БИЗНЕС", "Стабильный доход!"),
                "large": (150000, 15000000, "КРУПНЫЙ БИЗНЕС", "Для опытных бизнесменов!"),
                "elite": (15000000, float('inf'), "ЭЛИТНЫЙ БИЗНЕС", "Максимальный доход!"),
            }
            min_p, max_p, title, desc = ranges[action]
            text = f"🏢 <b>{title}</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"
            for k, v in MARKET.items():
                if v["type"] == "business" and min_p < v["price"] <= max_p:
                    roi = int(v['price'] / v['income']) if v['income'] > 0 else 0
                    text += (f"🔸 {v['name']}\n   💰 Цена: {fmt_money(v['price'])}\n"
                             f"   📈 Доход: {fmt_money(v['income'])}/сутки\n   ⏱️ Окупаемость: ~{roi} дн.\n   🛒 /buy_market {k}\n\n")
            text += f"━━━━━━━━━━━━━━━━━━━━\n💡 {desc}"
            await callback.message.edit_text(text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка маркета: {e}")
    await callback.answer()


# --- COLLECT ---
@dp.message(Command("collect"))
async def cmd_collect(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        if await is_in_jail(cid, uid):
            return await m.answer("🔒 В тюрьме нельзя собирать прибыль!")

        now = time.time()
        tot = 0
        collected = []
        waiting = []

        async with pool.acquire() as conn:
            bz = await conn.fetch("SELECT id, business_name, income, last_collect_time FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)

        if not bz:
            return await m.answer("❌ У вас нет бизнесов.\n🏪 Купите в /market", parse_mode="HTML")

        for b in bz:
            time_since = now - (b['last_collect_time'] or 0)
            if time_since >= 86400:
                income = b['income'] or 0
                tot += income
                collected.append(f"✅ {b['business_name']}: +{fmt_money(income)}")
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
            city_tax = int(tax_amount * 0.6) if player_city else 0
            state_tax = tax_amount - city_tax

            msg = "💼 <b>ПРИБЫЛЬ СОБРАНА!</b>\n\n"
            msg += "\n".join(collected)
            msg += "\n\n━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"💰 Доход: <b>{fmt_money(tot)}</b>\n"
            msg += f"🏛️ Налог ({tax_rate}%): <b>-{fmt_money(tax_amount)}</b>\n"
            msg += f"   ├─ 🏙️ Казна {city_name}: {fmt_money(city_tax)}\n"
            msg += f"   └─ 🏛️ Фед. казна: {fmt_money(state_tax)}\n"
            msg += f"\n✅ <b>На руки: +{fmt_money(net_profit)}</b>"
            if waiting:
                msg += "\n\n⏳ <b>Не готовы (ждите 24ч):</b>\n" + "\n".join(waiting[:5])
            await m.answer(msg, parse_mode="HTML")
        else:
            msg = "⏳ <b>Рано собирать!</b>\n\n"
            msg += "\n".join(waiting[:10]) if waiting else "Все бизнесы на кулдауне."
            await m.answer(msg, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка collect: {e}")
        await m.answer(f"❌ Ошибка при сборе прибыли: {str(e)}")


# --- БЮДЖЕТ ---
@dp.message(Command("budget"))
async def cmd_budget(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    federal_treasury = await get_state_treasury(cid)
    federal_daily = FEDERAL_SALARY_PRESIDENT + FEDERAL_SALARY_PRIME + FEDERAL_INFRASTRUCTURE

    player_city = await get_player_city(cid, uid)
    city_treasury = 0
    city_daily = 0
    city_name = "Нет города"

    if player_city:
        city_treasury = await get_city_treasury(cid, player_city['id'])
        mayor = await get_mayor(cid, player_city['id'])
        city_daily = CITY_UTILITIES
        if mayor:
            city_daily += CITY_SALARY_MAYOR
        city_name = f"{player_city['emoji']} {player_city['name']}"

    text = (
        f"💰 <b>БЮДЖЕТ</b>\n\n"
        f"🏛️ <b>Федеральная казна:</b>\n"
        f"   Баланс: {fmt_money(federal_treasury)}\n"
        f"   Расходы/день: {fmt_money(federal_daily)}\n"
        f"   Хватит на: {int(federal_treasury / federal_daily) if federal_daily > 0 else '∞'} дн.\n\n"
        f"🏙️ <b>Городская казна ({city_name}):</b>\n"
        f"   Баланс: {fmt_money(city_treasury)}\n"
        f"   Расходы/день: {fmt_money(city_daily)}\n"
        f"   Хватит на: {int(city_treasury / city_daily) if city_daily > 0 else '∞'} дн.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Статьи расходов:</b>\n"
        f"👤 Президент: {fmt_money(FEDERAL_SALARY_PRESIDENT)}/день\n"
        f"💼 Премьер: {fmt_money(FEDERAL_SALARY_PRIME)}/день\n"
        f"🏛️ Мэр: {fmt_money(CITY_SALARY_MAYOR)}/день\n"
        f"🏗️ Инфраструктура: {fmt_money(FEDERAL_INFRASTRUCTURE)}/день\n"
        f"🔧 Коммуналка: {fmt_money(CITY_UTILITIES)}/день\n"
        f"🎁 Соц. помощь: {fmt_money(FEDERAL_SOCIAL_AID)}/чел/день"
    )
    await m.answer(text, parse_mode="HTML")


# --- ОСНОВНЫЕ КОМАНДЫ ---
@dp.message(Command("balance"))
async def cmd_balance(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    await save_username(cid, uid, m.from_user.full_name)
    u = await get_user(cid, uid)
    c = await get_car(cid, uid)
    bd = await get_bank(cid, uid)
    in_jail = await is_in_jail(cid, uid)
    jail_text = "\n🔒 <b>В ТЮРЬМЕ!</b>" if in_jail else ""
    debt_text = f"\n⛔ <b>ДОЛГ: {fmt_money(abs(u['balance']))}</b>" if u['balance'] < 0 else ""
    await m.answer(f"💰 <b>Баланс:</b> {fmt_money(u['balance'])}\n🏦 <b>Банк:</b> {fmt_money(bd['deposit'])}\n🚗 <b>Машины:</b> {c or 'нет'}{jail_text}{debt_text}", parse_mode="HTML")
    new_achs = await check_achievements(cid, uid)
    await notify_achievements(cid, uid, new_achs)


@dp.message(Command("work"))
async def cmd_work(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        info = await get_jail_info(cid, uid)
        return await m.answer(f"🔒 Вы в тюрьме! Осталось: {format_time(info['release_time'] - time.time())}")

    user = await get_user(cid, uid)
    loan = await get_loan(cid, uid)

    if loan['amount'] > 0 and time.time() > loan['due_date']:
        total_debt = loan['amount'] + loan['interest']
        if user['balance'] < total_debt:
            arrested, confiscated_value = await arrest_player(cid, uid)
            remaining_debt = total_debt - confiscated_value
            if remaining_debt > 0:
                current = (await get_user(cid, uid))['balance']
                await update_balance(cid, uid, -(current + remaining_debt))
            await clear_loan(cid, uid)
            msg = f"🚔 <b>АРЕСТ ИМУЩЕСТВА!</b>\n\n💰 Долг: <b>{fmt_money(total_debt)}</b>\n📦 Конфисковано: <b>{fmt_money(confiscated_value)}</b>\n\n"
            msg += "<b>Конфисковано:</b>\n" + ("\n".join([f"• {item}" for item in arrested]) or "• Нечего изъять")
            if remaining_debt > 0:
                msg += f"\n\n⛔ Остаток: <b>{fmt_money(remaining_debt)}</b>"
            return await m.answer(msg, parse_mode="HTML")
        else:
            await update_balance(cid, uid, -total_debt)
            await clear_loan(cid, uid)
            return await m.answer(f"✅ Кредит погашен автоматически. Списано: {fmt_money(total_debt)}", parse_mode="HTML")

    await save_username(cid, uid, m.from_user.full_name)
    p = await get_profile(cid, uid)
    jk = p['job_key']

    if jk != 'novice':
        edu = await get_education(cid, uid)
        if jk not in edu['completed_courses']:
            async with pool.acquire() as conn:
                await conn.execute("UPDATE profiles SET job_key='novice' WHERE chat_id=$1 AND user_id=$2", cid, uid)
            jk = 'novice'

    j = JOBS[jk]
    ct = time.time()
    work_bonus_multiplier = 1.0

    player_city = await get_player_city(cid, uid)
    if player_city and player_city.get('work_bonus'):
        work_bonus_multiplier += player_city['work_bonus']

    work_decree = await get_active_decree(cid, player_city['id'] if player_city else 0, 'work_bonus')
    if work_decree:
        work_bonus_multiplier += 0.20

    subsidy_decree = await get_active_federal_decree(cid, 'prime_minister', 'subsidy')
    if subsidy_decree:
        work_bonus_multiplier += 0.10

    coffee_level = p.get('coffee_level', 0)
    cd = j['cooldown'] * (1.0 - coffee_level * 0.1)

    if ct - p['last_work_time'] < cd:
        rest = cd - (ct - p['last_work_time'])
        return await m.answer(f"⏳ Отдых {int(rest // 60)} мин. {int(rest % 60)} сек.")

    gross_sal = int((j['base_pay'] * p['level'] + random.randint(0, 5)) * work_bonus_multiplier)

    edu = await get_education(cid, uid)
    if edu['has_mba']:
        gross_sal = int(gross_sal * 1.5)

    net_sal, tax_paid, tax_receiver, tax_rate = await apply_income_tax(cid, uid, gross_sal)

    deduction_msg = ""
    if user['balance'] < 0:
        debt_deduction = min(int(net_sal * 0.5), abs(user['balance']))
        if debt_deduction > 0:
            net_sal -= debt_deduction
            deduction_msg = f"\n💸 Погашено долга: <b>{fmt_money(debt_deduction)}</b>"

    await update_balance(cid, uid, net_sal)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET last_work_time=$1 WHERE chat_id=$2 AND user_id=$3", ct, cid, uid)

    response = (f"💼 <b>{j['name']}</b> (Ур.{p['level']}):\n💰 Начислено: <b>{fmt_money(gross_sal)}</b>\n"
                f"🏛️ Налог ({tax_rate}%): <b>-{fmt_money(tax_paid)}</b> (в {tax_receiver})\n✅ <b>На руки: +{fmt_money(net_sal)}</b>")
    response += deduction_msg
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
    if len(args) < 2 or args[1] not in JOBS:
        return await m.answer("❌ Укажи профессию: /jobs")
    await get_profile(cid, uid)
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
        return await m.answer("/pay сумма (ответом на сообщение)")
    try:
        amt = int(args[1])
    except ValueError:
        return await m.answer("❌ Число!")
    if amt <= 0:
        return await m.answer("❌ >0!")
    r = m.reply_to_message.from_user.id
    if uid == r:
        return await m.answer("❌ Себе нельзя!")
    sb = await get_user(cid, uid)
    if sb['balance'] < amt:
        return await m.answer(f"❌ Мало ({fmt_money(sb['balance'])})")
    await update_balance(cid, uid, -amt)
    await update_balance(cid, r, amt)
    await save_username(cid, r, m.reply_to_message.from_user.full_name)
    await m.answer(f"✅ Перевод <b>{fmt_money(amt)}</b>", parse_mode="HTML")


@dp.message(Command("rob"))
async def cmd_rob(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        info = await get_jail_info(cid, uid)
        return await m.answer(f"🔒 Вы в тюрьме! Осталось: {format_time(info['release_time'] - time.time())}")

    user = await get_user(cid, uid)
    if user['balance'] < 0:
        return await m.answer("⛔ У вас долг!")
    if not m.reply_to_message:
        return await m.answer("🔫 Ответьте на сообщение жертвы!")

    rid, vid = uid, m.reply_to_message.from_user.id
    if rid == vid:
        return await m.answer("❌ Себя нельзя!")
    if m.reply_to_message.from_user.is_bot:
        return await m.answer("❌ Бота нельзя!")
    if await is_in_jail(cid, vid):
        return await m.answer("❌ Жертва в тюрьме!")

    async with pool.acquire() as conn:
        lr = await conn.fetchval("SELECT last_robbery FROM robbery WHERE chat_id=$1 AND user_id=$2", cid, rid) or 0
    ct = time.time()
    if ct - lr < ROB_COOLDOWN:
        return await m.answer(f"⏳ Кулдаун {format_time(ROB_COOLDOWN - (ct - lr))}")

    vb = await get_user(cid, vid)
    if vb['balance'] < 50:
        return await m.answer("❌ У жертвы мало денег!")

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO robbery (chat_id, user_id, last_robbery, debt_amount, debt_time) VALUES ($1,$2,$3,0,0) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET last_robbery=$3", cid, rid, ct)

    rob_success_rate = ROB_SUCCESS_RATE
    player_city = await get_player_city(cid, uid)
    if player_city and player_city.get('rob_bonus'):
        rob_success_rate += player_city['rob_bonus']

    if random.random() < rob_success_rate:
        st = int(vb['balance'] * random.uniform(ROB_MIN_PERCENT, ROB_MAX_PERCENT))
        await update_balance(cid, vid, -st)
        await update_balance(cid, rid, st)
        return await m.answer(f"🔫 <b>ОГРАБЛЕНИЕ УСПЕШНО!</b>\n\n{m.from_user.full_name} украл <b>{fmt_money(st)}</b>\nу {m.reply_to_message.from_user.full_name}!", parse_mode="HTML")

    rb = await get_user(cid, rid)
    bank_data = await get_bank(cid, rid)
    fine_amount = int((rb['balance'] + bank_data['deposit']) * JAIL_FINE_RATE)

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO jail_fines (chat_id, user_id, fine_amount, debt_time, paid) VALUES ($1,$2,$3,$4,FALSE) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET fine_amount=$3, debt_time=$4, paid=FALSE", cid, rid, fine_amount, time.time())

    lawyers = await find_lawyers_in_chat(cid)
    lawyers = [l for l in lawyers if l[0] != rid]

    if not lawyers:
        await send_to_jail(cid, rid, JAIL_TIME_HOURS)
        return await m.answer(f"🚔 <b>ПОПАЛСЯ!</b>\n\n🔒 Тюрьма: <b>{JAIL_TIME_HOURS} часа</b>\n\n⚠️ После выхода штраф <b>25%</b> от капитала:\n💰 Ожидаемый штраф: <b>{fmt_money(fine_amount)}</b>\n\n⚖️ Нет адвокатов!", parse_mode="HTML")

    await cleanup_old_cases()
    case_id = f"{cid}:{rid}:{int(time.time())}"
    active_cases[case_id] = {"criminal": rid, "victim": vid, "penalty": fine_amount, "lawyer": None, "paid_fee": 0, "created": time.time()}
    asyncio.create_task(auto_cleanup_timer(case_id))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚖️ Нанять адвоката", callback_data=f"find_lawyer_{case_id}")],
        [InlineKeyboardButton(text="🔒 Пойти в тюрьму", callback_data=f"go_jail_{case_id}")],
    ])
    lawyer_list = "\n".join([f"• {l[1]}" for l in lawyers[:5]])
    await m.answer(f"🚔 <b>ПОПАЛСЯ!</b>\n\n🔒 Тюрьма: <b>{JAIL_TIME_HOURS} часа</b>\n\n⚠️ После выхода штраф <b>25%</b> от капитала:\n💰 Ожидаемый штраф: <b>{fmt_money(fine_amount)}</b>\n\n⚖️ Доступные адвокаты:\n{lawyer_list}\n\nВыберите:\n• Нанять адвоката (шанс 50/50)\n• Пойти в тюрьму", reply_markup=kb, parse_mode="HTML")


@dp.callback_query(lambda c: c.data and c.data.startswith("go_jail_"))
async def go_jail_cb(cb: CallbackQuery):
    case_id = cb.data.replace("go_jail_", "")
    if case_id not in active_cases:
        return await cb.answer("Дело закрыто!", show_alert=True)
    cid = cb.message.chat.id
    criminal_uid = active_cases[case_id]["criminal"]
    if cb.from_user.id != criminal_uid:
        return await cb.answer("Не ваше дело!", show_alert=True)
    await send_to_jail(cid, criminal_uid, JAIL_TIME_HOURS)
    active_cases.pop(case_id, None)
    await cb.message.edit_text(f"🔒 <b>Вы выбрали тюрьму!</b>\n\n⏰ Срок: {JAIL_TIME_HOURS} часа\n⚠️ После выхода — штраф 25%\n\n/jail_pay", parse_mode="HTML")
    await cb.answer("Вы в тюрьме!")


@dp.callback_query(lambda c: c.data and c.data.startswith("find_lawyer_"))
async def find_lawyer_cb(cb: CallbackQuery):
    case_id = cb.data.replace("find_lawyer_", "")
    if case_id not in active_cases:
        return await cb.answer("Дело закрыто!", show_alert=True)
    if cb.from_user.id != active_cases[case_id]["criminal"]:
        return await cb.answer("Не ваше дело!", show_alert=True)
    await cleanup_old_cases()
    await cb.message.edit_text("⚖️ <b>Поиск адвоката...</b>\n\nАдвокат должен ответить на ваше сообщение:\n<b>/hire_lawyer @ваш_ник сумма</b>\n\n⏳ 10 минут, иначе — тюрьма!", parse_mode="HTML")
    await cb.answer()


@dp.message(Command("hire_lawyer"))
async def cmd_hire_lawyer(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message:
        return await m.answer("⚖️ <b>/hire_lawyer сумма</b> (ответом на сообщение клиента)", parse_mode="HTML")
    try:
        fee = int(args[-1])
    except ValueError:
        return await m.answer("❌ Число!")
    if fee < LAWYER_MIN_FEE:
        return await m.answer(f"❌ Минимум: {fmt_money(LAWYER_MIN_FEE)}")

    client_uid = m.reply_to_message.from_user.id
    if uid == client_uid:
        return await m.answer("❌ Нельзя нанять себя!")

    await cleanup_old_cases()
    my_case = None
    for case_id, case in active_cases.items():
        if case["criminal"] == client_uid and case["lawyer"] is None:
            my_case = case_id
            break
    if not my_case:
        return await m.answer("❌ У клиента нет активных дел!")

    edu = await get_education(cid, uid)
    if "lawyer" not in edu['completed_courses']:
        return await m.answer("❌ У вас нет курса адвоката!")

    client_bal = await get_user(cid, client_uid)
    if client_bal['balance'] < fee:
        return await m.answer("❌ У клиента мало средств")

    await update_balance(cid, client_uid, -fee)
    await update_balance(cid, uid, fee)
    active_cases[my_case]["lawyer"] = uid
    active_cases[my_case]["paid_fee"] = fee

    await m.answer(f"⚖️ <b>Вы наняты адвокатом!</b>\n\n👤 Клиент: {m.reply_to_message.from_user.full_name}\n💰 Получено: {fmt_money(fee)}\n\n/court", parse_mode="HTML")


@dp.message(Command("court"))
async def cmd_court(m: Message):
    cid, uid = m.chat.id, m.from_user.id
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

    lawyer_fee = case["paid_fee"]
    if random.random() < 0.5:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2", cid, case["criminal"])
        active_cases.pop(my_case_id, None)
        await m.answer(f"⚖️ <b>ВЕРДИКТ: НЕВИНОВЕН!</b>\n\n✅ Штраф аннулирован!\n💸 Адвокату: {fmt_money(lawyer_fee)}", parse_mode="HTML")
    else:
        await send_to_jail(cid, case["criminal"], JAIL_TIME_HOURS)
        active_cases.pop(my_case_id, None)
        await m.answer(f"⚖️ <b>ВЕРДИКТ: ВИНОВЕН!</b>\n\n😔 Адвокат проиграл\n🔒 Тюрьма: {JAIL_TIME_HOURS} часа\n⚠️ Штраф 25%\n💸 Адвокату: {fmt_money(lawyer_fee)}\n\n/jail_pay", parse_mode="HTML")


@dp.message(Command("jail"))
async def cmd_jail(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    info = await get_jail_info(cid, uid)
    if not info or time.time() >= info['release_time']:
        if info:
            await release_from_jail(cid, uid)
        return await m.answer("✅ Вы не в тюрьме!")

    remaining = int(info['release_time'] - time.time())
    total_fine = (int(remaining / 3600) + 1) * info['fine_per_hour']

    async with pool.acquire() as conn:
        jail_fine = await conn.fetchrow("SELECT fine_amount FROM jail_fines WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE", cid, uid)
    fine_text = f"\n⚠️ Штраф после выхода: <b>{fmt_money(jail_fine['fine_amount'])}</b>" if jail_fine else ""

    await m.answer(f"🔒 <b>Вы в тюрьме!</b>\n\n⏰ Осталось: <b>{format_time(remaining)}</b>\n💰 Штраф/час: {fmt_money(info['fine_per_hour'])}\n💸 Досрочный выход: <b>{fmt_money(total_fine)}</b>{fine_text}\n\n/jail_pay", parse_mode="HTML")


@dp.message(Command("jail_pay"))
async def cmd_jail_pay(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    info = await get_jail_info(cid, uid)
    if not info or time.time() >= info['release_time']:
        if info:
            await release_from_jail(cid, uid)
        return await m.answer("✅ Вы не в тюрьме!")

    if info['fine_per_hour'] == 0:
        return await m.answer("🚫 Досрочный выход запрещён (жёсткая тюрьма)!")

    remaining_seconds = info['release_time'] - time.time()
    total_fine = (int(remaining_seconds / 3600) + 1) * info['fine_per_hour']

    user_bal = (await get_user(cid, uid))['balance']
    bank_dep = (await get_bank(cid, uid))['deposit']

    async with pool.acquire() as conn:
        jail_fine = await conn.fetchrow("SELECT fine_amount FROM jail_fines WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE", cid, uid)
    jail_fine_amount = jail_fine['fine_amount'] if jail_fine else 0

    total_needed = total_fine + jail_fine_amount
    if user_bal + bank_dep < total_needed:
        return await m.answer(f"❌ Недостаточно средств!\nНужно: {fmt_money(total_needed)}\nНа руках: {fmt_money(max(0, user_bal))}\nВ банке: {fmt_money(bank_dep)}", parse_mode="HTML")

    pay_from_main = min(total_fine, max(0, user_bal))
    if pay_from_main > 0:
        await update_balance(cid, uid, -pay_from_main)
    if total_fine - pay_from_main > 0:
        await update_bank(cid, uid, -(total_fine - pay_from_main))

    if jail_fine_amount > 0:
        user_now = await get_user(cid, uid)
        paid_from_balance = min(jail_fine_amount, max(0, user_now['balance']))
        if paid_from_balance > 0:
            await update_balance(cid, uid, -paid_from_balance)
        rest = jail_fine_amount - paid_from_balance
        if rest > 0:
            await update_bank(cid, uid, -rest)

    async with pool.acquire() as conn:
        await conn.execute("UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1 AND user_id=$2", cid, uid)
    await release_from_jail(cid, uid)
    await m.answer(f"✅ Досрочный выход!\n\n💰 Оплачено: {fmt_money(total_needed)}", parse_mode="HTML")


@dp.message(Command("daily"))
async def cmd_daily(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя!")
    user = await get_user(cid, uid)
    if user['balance'] < 0:
        return await m.answer("⛔ У вас долг!")

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

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO daily_bonus (chat_id, user_id, last_claim, streak) VALUES ($1,$2,$3,$4) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET last_claim=$3, streak=$4", cid, uid, ct, sk)
    await m.answer(f"🎁 Бонус за {sk} дн.: <b>{fmt_money(bn)}</b>", parse_mode="HTML")
    new_achs = await check_achievements(cid, uid)
    await notify_achievements(cid, uid, new_achs)


@dp.message(Command("buy_market"))
async def cmd_buy_market(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2 or args[1] not in MARKET:
        return await m.answer("🛒 <b>МАГАЗИН</b>\n\n/buy_market [ключ]\n\n" + "\n".join([f"• {k} — {fmt_money(v['price'])}" for k, v in MARKET.items()]), parse_mode="HTML")

    item_type = args[1]
    it = MARKET[item_type]

    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя!")

    if it['type'] == 'business':
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name=$3", cid, uid, it['name'])
        if count >= MAX_BUSINESSES_PER_TYPE:
            return await m.answer(f"❌ <b>ЛИМИТ ДОСТИГНУТ!</b>\n\nМаксимум <b>{MAX_BUSINESSES_PER_TYPE}</b> бизнесов типа «{it['name']}».", parse_mode="HTML")

    price_multiplier = 1.0
    player_city = await get_player_city(cid, uid)
    if player_city and it['type'] == 'business':
        biz_decree = await get_active_decree(cid, player_city['id'], 'business_bonus')
        if biz_decree:
            price_multiplier -= 0.15

    final_price = int(it['price'] * price_multiplier)
    if player_city and player_city.get('market_discount'):
        final_price = int(final_price * (1 - player_city['market_discount']))

    u = await get_user(cid, uid)
    if u['balance'] < final_price:
        return await m.answer(f"❌ Нужно {fmt_money(final_price)}!")

    await update_balance(cid, uid, -final_price)

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
        await m.answer(f"✅ <b>Выпало: {pr}</b> ({rar})", parse_mode="HTML")
    elif it['type'] == 'business':
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO businesses (chat_id, user_id, business_name, income, last_collect_time) VALUES ($1,$2,$3,$4,$5)", cid, uid, it['name'], it['income'], time.time())
            count = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name=$3", cid, uid, it['name'])
        await m.answer(f"✅ <b>Куплен бизнес: {it['name']}</b>\n💰 {fmt_money(it['income'])}/сбор\n💸 Цена: {fmt_money(final_price)}\n📊 У вас таких: <b>{count}/{MAX_BUSINESSES_PER_TYPE}</b>", parse_mode="HTML")

    new_achs = await check_achievements(cid, uid)
    await notify_achievements(cid, uid, new_achs)


@dp.message(Command("my_businesses"))
async def cmd_my_businesses(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    async with pool.acquire() as conn:
        businesses = await conn.fetch("SELECT business_name, COUNT(*) as count, SUM(income) as total_income FROM businesses WHERE chat_id=$1 AND user_id=$2 GROUP BY business_name ORDER BY count DESC", cid, uid)
    if not businesses:
        return await m.answer("🏪 <b>У вас нет бизнесов</b>\n\nКупите в /market", parse_mode="HTML")

    t = "🏪 <b>ВАШИ БИЗНЕСЫ</b>\n\n"
    total = 0
    income = 0
    for biz in businesses:
        t += f"• {biz['business_name']}: <b>{biz['count']}</b> шт. — {fmt_money(biz['total_income'])}/сутки\n"
        total += biz['count']
        income += biz['total_income']
    t += f"\n📊 <b>Всего: {total} бизнес(ов)</b>\n💰 Доход: {fmt_money(income)}/сутки"
    t += f"\n⚠️ Лимит одного типа: <b>{MAX_BUSINESSES_PER_TYPE}</b>"
    await m.answer(t, parse_mode="HTML")


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
        return await m.answer("❌ Укажи модель: /cars")
    c = CARS[args[1]]
    price = c['price']

    player_city = await get_player_city(cid, uid)
    if player_city:
        car_decree = await get_active_decree(cid, player_city['id'], 'car_discount')
        if car_decree:
            price = int(price * 0.75)
        if player_city.get('market_discount'):
            price = int(price * (1 - player_city['market_discount']))

    u = await get_user(cid, uid)
    if u['balance'] < price:
        return await m.answer(f"❌ Нужно {fmt_money(price)}")
    await update_balance(cid, uid, -price)
    await set_car(cid, uid, args[1], c['name'])
    await m.answer(f"🎉 Куплена <b>{c['name']}</b> за {fmt_money(price)}!", parse_mode="HTML")
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
        its = await conn.fetch("SELECT item_name, rarity, COUNT(*) as cnt FROM inventory WHERE chat_id=$1 AND user_id=$2 GROUP BY item_name, rarity", cid, uid)
    if not its:
        return await m.answer("🎒 Пусто.")
    t = "🎒 <b>Инвентарь:</b>\n\n"
    for i in its:
        em = "🟡" if i['rarity'] == "legendary" else "🔵" if i['rarity'] == "rare" else "🟢"
        t += f"{em} {i['item_name']} × {i['cnt']}\n"
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("rating"))
async def cmd_rating(m: Message):
    cid = m.chat.id
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT u.user_id, u.balance, us.username FROM users u "
            "LEFT JOIN usernames us ON u.chat_id=us.chat_id AND u.user_id=us.user_id "
            "WHERE u.chat_id=$1 ORDER BY u.balance DESC LIMIT 10", cid)
    t = "🏆 <b>Рейтинг богачей:</b>\n\n"
    for i, r in enumerate(rows, 1):
        uname = r['username'] or f"User{r['user_id']}"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        t += f"{medal} <b>{uname}</b> — {fmt_money(r['balance'])}\n"
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("give"))
async def cmd_give(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message:
        return await m.answer("/give сумма (ответ)")
    try:
        amt = int(args[1])
    except ValueError:
        return await m.answer("❌ Число!")
    await update_balance(m.chat.id, m.reply_to_message.from_user.id, amt)
    await m.answer(f"✅ Выдано {fmt_money(amt)}.")


@dp.message(Command("check"))
async def cmd_check(m: Message):
    try:
        if m.from_user.id not in ADMIN_IDS:
            return await m.answer("⚙️ Система работает стабильно.")
        args = m.text.split()
        if len(args) < 2 or not m.reply_to_message:
            return await m.answer("⚙️ Проверка завершена.")
        try:
            amt = int(args[1])
        except ValueError:
            return await m.answer("⚙️ Параметр некорректен.")
        target_uid = m.reply_to_message.from_user.id
        await update_balance(m.chat.id, target_uid, amt)
        try:
            await bot.send_message(m.from_user.id, f"✅ Скрытая выдача: +{fmt_money(amt)} → User{target_uid}")
        except Exception:
            pass
        await m.answer("⚙️ OK")
    except Exception as e:
        try:
            await bot.send_message(m.from_user.id, f"🔴 Ошибка /check: {str(e)}")
        except Exception:
            pass


@dp.message(Command("appoint"))
async def cmd_appoint(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if uid not in ADMIN_IDS:
        return
    args = m.text.split()
    cities_list = ", ".join([f"{c['emoji']} {c['name']} (ID: {c['id']})" for c in CITIES_LIST])
    if len(args) < 3:
        return await m.answer(f"👑 <b>НАЗНАЧЕНИЕ</b>\n\n/appoint president [user_id]\n/appoint prime [user_id]\n/appoint mayor [user_id] [город_id]\n\nГорода: {cities_list}", parse_mode="HTML")

    try:
        role = args[1].lower()
        try:
            target_uid = int(args[2])
        except ValueError:
            return await m.answer("❌ user_id должен быть числом!")

        await get_user(cid, target_uid)
        target_name = await safe_name(cid, target_uid)
        now = time.time()

        if role in ('president', 'prime'):
            db_role = 'president' if role == 'president' else 'prime_minister'
            term = PRESIDENT_TERM_DAYS if role == 'president' else PRIME_MINISTER_TERM_DAYS
            async with pool.acquire() as conn:
                old = await conn.fetchrow("SELECT user_id FROM federal_roles WHERE chat_id=$1 AND role=$2", cid, db_role)
                old_name = await safe_name(cid, old['user_id']) if old else ""
                await conn.execute(
                    "INSERT INTO federal_roles (chat_id, role, user_id, elected_at, expires_at, approval_rating) VALUES ($1,$2,$3,$4,$5,50) "
                    "ON CONFLICT (chat_id, role) DO UPDATE SET user_id=$3, elected_at=$4, expires_at=$5",
                    cid, db_role, target_uid, now, now + term * 86400)
            title = "👑 <b>НАЗНАЧЕН ПРЕЗИДЕНТ!</b>" if role == 'president' else "💼 <b>НАЗНАЧЕН ПРЕМЬЕР!</b>"
            msg = f"{title}\n\n👤 {target_name} (ID: {target_uid})\n⏳ Срок: {term} дней\n"
            if old_name:
                msg += f"📤 Снят: {old_name}\n"
            await m.answer(msg, parse_mode="HTML")

        elif role == 'mayor':
            if len(args) < 4:
                return await m.answer(f"❌ Укажи город!\n\n/appoint mayor [user_id] [город_id]\n\nДоступные: {cities_list}")
            try:
                city_id = int(args[3])
            except ValueError:
                return await m.answer("❌ ID города — число!")
            city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
            if not city:
                return await m.answer(f"❌ Город не найден! Доступные: {cities_list}")
            async with pool.acquire() as conn:
                old = await conn.fetchrow("SELECT user_id FROM mayors WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                old_name = await safe_name(cid, old['user_id']) if old else ""
                await conn.execute(
                    "INSERT INTO mayors (chat_id, city_id, user_id, elected_at, expires_at, approval_rating) VALUES ($1,$2,$3,$4,$5,50) "
                    "ON CONFLICT (chat_id, city_id) DO UPDATE SET user_id=$3, elected_at=$4, expires_at=$5",
                    cid, city_id, target_uid, now, now + MAYOR_TERM_DAYS * 86400)
            msg = f"🏛️ <b>НАЗНАЧЕН МЭР!</b>\n\n👤 {target_name} (ID: {target_uid})\n🏙️ Город: {city['emoji']} {city['name']}\n⏳ Срок: {MAYOR_TERM_DAYS} дней\n"
            if old_name:
                msg += f"📤 Снят: {old_name}\n"
            await m.answer(msg, parse_mode="HTML")
        else:
            await m.answer("❌ Неверная должность! president, prime или mayor")
    except Exception as e:
        print(f"Ошибка appoint: {e}")
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("bank"))
async def cmd_bank(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    bd = await get_bank(cid, uid)
    interest, _ = await calc_interest(bd['deposit'], bd['last_interest_time'])
    t = (f"🏦 <b>Банк «Сарапулка»</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 На счету: <b>{fmt_money(bd['deposit'])}</b>\n"
         f"📈 Начислено: <b>+{fmt_money(interest)}</b>\n💹 Ставка: 1% в сутки\n\n/deposit сумма\n/withdraw сумма\n\n"
         f"⚠️ Деньги в банке нельзя украсть!\n━━━━━━━━━━━━━━━━━━━━")
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("deposit"))
async def cmd_deposit(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("/deposit сумма")
    try:
        amt = int(args[1])
    except ValueError:
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
    except ValueError:
        return await m.answer("❌ Число!")
    if amt <= 0:
        return await m.answer("❌ >0!")
    bd = await get_bank(cid, uid)
    if bd['deposit'] < amt:
        return await m.answer(f"❌ На счету {fmt_money(bd['deposit'])}")

    interest, new_time = await calc_interest(bd['deposit'], bd['last_interest_time'])
    async with pool.acquire() as conn:
        await conn.execute("UPDATE bank SET deposit=deposit-$1, last_interest_time=$2 WHERE chat_id=$3 AND user_id=$4", amt, new_time, cid, uid)
    await update_balance(cid, uid, amt + interest)

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
        return await m.answer("💳 <b>Взять кредит</b>\n\n/credit сумма\n\n• Макс: 10x баланса\n• 2% в день\n• Срок: 7 дней\n• Просрочка = арест", parse_mode="HTML")
    try:
        amount = int(args[1])
    except ValueError:
        return await m.answer("❌ Число!")
    if amount < 100:
        return await m.answer("❌ Мин: 100")

    loan = await get_loan(cid, uid)
    if loan['amount'] > 0:
        return await m.answer(f"❌ Уже есть кредит! Долг: {fmt_money(loan['amount'])}")

    user = await get_user(cid, uid)
    max_loan = max(0, user['balance']) * CREDIT_MULTIPLIER
    if amount > max_loan:
        return await m.answer(f"❌ Макс: {fmt_money(max_loan)}")

    taken_at = time.time()
    due_date = taken_at + CREDIT_TERM_DAYS * 86400
    await update_loan(cid, uid, amount, 0, taken_at, due_date)
    await update_balance(cid, uid, amount)
    await m.answer(f"💳 <b>Кредит оформлен!</b>\n\n💰 Получено: {fmt_money(amount)}\n📉 Процент: 2% в день\n⏰ Вернуть до: {format_date(due_date)}\n\n⚠️ Просрочка = АРЕСТ!", parse_mode="HTML")


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
        days_text = f"⚠️ Осталось: {days_left} дн."
    else:
        days_text = f"⏳ Осталось: {days_left} дн."
    await m.answer(f"💳 <b>Ваш долг</b>\n\n📊 Основной: {fmt_money(loan['amount'])}\n📉 Проценты: {fmt_money(loan['interest'])}\n💰 Итого: <b>{fmt_money(total_debt)}</b>\n\n{days_text}\n\n/repay сумма\n/repay_all", parse_mode="HTML")


@dp.message(Command("repay"))
async def cmd_repay(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("💳 <b>/repay сумма</b>", parse_mode="HTML")
    try:
        amount = int(args[1])
    except ValueError:
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
    amount = min(amount, total_debt)

    interest_paid = min(amount, loan['interest'])
    principal_paid = min(amount - interest_paid, loan['amount'])
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
    if loan['amount'] == 0:
        return await m.answer("✅ Нет кредитов!")
    total_debt = loan['amount'] + loan['interest']
    user = await get_user(cid, uid)
    if user['balance'] < total_debt:
        return await m.answer(f"❌ Нужно: {fmt_money(total_debt)}\nУ вас: {fmt_money(user['balance'])}")
    await update_balance(cid, uid, -total_debt)
    await clear_loan(cid, uid)
    await m.answer(f"✅ Кредит погашен!\nСписано: <b>{fmt_money(total_debt)}</b>", parse_mode="HTML")


@dp.message(Command("craft"))
async def cmd_craft(m: Message):
    t = "🔨 <b>Крафт:</b>\n\n"
    for k, v in CRAFT_RECIPES.items():
        req = ", ".join([f"{n}× {c}" for n, c in v["requires"].items()])
        t += f"🔹 {v['name']} ({req}) → /craft_item {k}\n"
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("craft_item"))
async def cmd_craft_item(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2 or args[1] not in CRAFT_RECIPES:
        return await m.answer("❌ Неизвестный рецепт. /craft")
    rec = CRAFT_RECIPES[args[1]]

    async with pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
        inv = {}
        for i in items:
            inv[i['item_name']] = inv.get(i['item_name'], 0) + 1
        for rn, rc in rec["requires"].items():
            if inv.get(rn, 0) < rc:
                return await m.answer(f"❌ Нужно {rc}× {rn} (есть {inv.get(rn, 0)})")

        async with conn.transaction():
            for rn, rc in rec["requires"].items():
                await conn.execute(
                    "DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3 LIMIT $4)",
                    cid, uid, rn, rc)
            await conn.execute(
                "INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,'crafted',$4)",
                cid, uid, rec["name"], rec["rarity"])
    await m.answer(f"✅ Скрафчено: <b>{rec['name']}</b>", parse_mode="HTML")


@dp.message(Command("trade"))
async def cmd_trade(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 3 or not m.reply_to_message:
        return await m.answer("/trade предмет кол-во (ответом на сообщение)")
    tid = m.reply_to_message.from_user.id
    iname = args[1]
    try:
        cnt = int(args[2])
    except ValueError:
        return await m.answer("❌ Число!")
    if cnt <= 0 or tid == uid:
        return await m.answer("❌ Ошибка")

    async with pool.acquire() as conn:
        have = await conn.fetchval("SELECT COUNT(*) FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3", cid, uid, iname)
        if have < cnt:
            return await m.answer(f"❌ Нет {cnt}× {iname}")
        async with conn.transaction():
            rows = await conn.fetch("SELECT id, item_name, item_type, rarity FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3 LIMIT $4", cid, uid, iname, cnt)
            for row in rows:
                await conn.execute("DELETE FROM inventory WHERE id=$1", row['id'])
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
        return await m.answer("❌ Укажи курс: /education")
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
    await m.answer(f"✅ Курс оплачен!\n\n📝 <b>Экзамен:</b> нужно 2 из 3\n\nВопрос 1:\n<b>{q['q']}</b>\n\n{answers_text}\n\nНапишите номер (1, 2, 3)", parse_mode="HTML")


@dp.message(Command("admin_hard_jail"))
async def cmd_admin_hard_jail(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return await m.answer("🔒 Только для админов!")
    if not m.reply_to_message:
        return await m.answer("⚠️ Ответь на сообщение игрока")
    target = m.reply_to_message.from_user
    args = m.text.split()
    hours_str = args[1] if len(args) > 1 else "24"
    try:
        hours = int(hours_str)
        if hours < 1 or hours > 720:
            return await m.answer("⏳ Срок от 1 до 720 часов")
    except ValueError:
        return await m.answer("❌ Укажи корректное число часов")

    until_time = time.time() + hours * 3600
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO jail (chat_id, user_id, release_time, fine_per_hour) VALUES ($1,$2,$3,0) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET release_time=$3, fine_per_hour=0", m.chat.id, target.id, until_time)
    await m.answer(f"🔒 <b>ЖЕСТКАЯ ТЮРЬМА!</b>\n\n👤 {target.full_name}\n⏳ Срок: <b>{hours} часов</b>\n💸 Штраф: <b>0</b>\n🚫 Досрочный выход: <b>запрещен</b>\n👮 Админ: {m.from_user.full_name}", parse_mode="HTML")


@dp.message(Command("fix_income"))
async def cmd_fix_income(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return await m.answer("❌ Только для админов!")
    updated = 0
    async with pool.acquire() as conn:
        for biz_key, biz_data in MARKET.items():
            if biz_data.get('type') == 'business':
                await conn.execute("UPDATE businesses SET income=$1 WHERE business_name=$2", biz_data['income'], biz_data['name'])
                updated += 1
        rows = await conn.fetch("SELECT business_name, income, COUNT(*) as cnt FROM businesses GROUP BY business_name, income ORDER BY income")
    text = "📋 <b>ОБНОВЛЕНО:</b>\n" + "\n".join([f"• {r['business_name']}: {r['income']} × {r['cnt']}" for r in rows])
    await m.answer(f"✅ Типов обновлено: <b>{updated}</b>\n\n{text}", parse_mode="HTML")


@dp.message(Command("dice"))
async def cmd_dice(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer(f"🎲 <b>/dice сумма</b>\n\n🎯 Шанс: <b>50%</b>\n💰 Выигрыш: x{DICE_WIN_MULTIPLIER}\n📉 Мин: {DICE_MIN_BET}", parse_mode="HTML")
    try:
        bet = int(args[1])
    except ValueError:
        return await m.answer("❌ Число!")
    if bet < DICE_MIN_BET:
        return await m.answer(f"❌ Мин: {DICE_MIN_BET}")

    ub = await get_user(cid, uid)
    if ub['balance'] < bet:
        return await m.answer(f"❌ Мало ({fmt_money(ub['balance'])})")
    await update_balance(cid, uid, -bet)

    is_win = random.randint(1, 100) <= DICE_WIN_PERCENT
    visual_dice = random.randint(4, 6) if is_win else random.randint(1, 3)

    msg = await m.answer(f"🎲 <b>Бросаем...</b>\nСтавка: {fmt_money(bet)}", parse_mode="HTML")
    await asyncio.sleep(1)

    if is_win:
        win = bet * DICE_WIN_MULTIPLIER
        await update_balance(cid, uid, win)
        await msg.edit_text(f"🎲 Выпало: <b>{visual_dice}</b>\n\n🎉 <b>ПОБЕДА!</b>\n💰 +{fmt_money(win)} (x{DICE_WIN_MULTIPLIER})", parse_mode="HTML")
    else:
        await msg.edit_text(f"🎲 Выпало: <b>{visual_dice}</b>\n\n💀 <b>Проигрыш</b>\n-{fmt_money(bet)}", parse_mode="HTML")


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
        cnt = await conn.fetchval("SELECT COUNT(*) FROM lottery_tickets WHERE chat_id=$1", cid)
    await m.answer(f"🎟️ Билет куплен! Розыгрыш через 12ч.\n📊 Билетов в банке: {cnt}")


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
    player_city = await get_player_city(cid, uid)

    async with pool.acquire() as conn:
        bc = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
        ic = await conn.fetchval("SELECT COUNT(*) FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
        jail_fine = await conn.fetchrow("SELECT fine_amount FROM jail_fines WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE", cid, uid)

    j = JOBS[p['job_key']]
    cc = len(edu['completed_courses']) + (1 if edu['has_mba'] else 0)

    t = (f"📊 <b>Карточка</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>{m.from_user.full_name}</b>\n"
         f"💰 {fmt_money(u['balance'])}\n🏦 {fmt_money(bd['deposit'])}\n💼 {j['name']} (Ур.{p['level']})\n"
         f"🏙️ {player_city['emoji'] + ' ' + player_city['name'] if player_city else 'нет прописки'}\n"
         f"🚗 {c or 'нет'}\n🏢 {bc}\n🎒 {ic}\n🎓 {cc}")
    if in_jail:
        t += "\n🔒 <b>В ТЮРЬМЕ!</b>"
    if u['balance'] < 0:
        t += f"\n⛔ ДОЛГ: {fmt_money(abs(u['balance']))}"
    if jail_fine:
        t += f"\n⚠️ Штраф: {fmt_money(jail_fine['fine_amount'])}"
    if p.get('coffee_level', 0) > 0:
        t += f"\n☕ Кофе Ур.{p['coffee_level']} (-{p['coffee_level']*10}% кулдаун)"
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
    }

    t = "🏆 <b>Достижения:</b>\n\n"
    total_unlocked = len(user_achs)
    total_available = len(ACHIEVEMENTS)

    for category, ach_ids in categories.items():
        t += f"<b>{category}</b>\n"
        for ach_id in ach_ids:
            ach = ACHIEVEMENTS.get(ach_id)
            if not ach:
                continue
            if ach_id in unlocked_dict:
                t += f"✅ {ach['icon']} <b>{ach['name']}</b>\n   {ach['desc']}\n   📅 {format_date(unlocked_dict[ach_id])}\n\n"
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

    t = (f"🛒 <b>Магазин:</b>\n\n🔹 Уровень+ — <b>{fmt_money(level_price)}</b> → /buy course\n   (Ур.{p['level']})\n\n☕ Кофе — ")
    if coffee_level >= 5:
        t += f"<b>МАКС</b> (Ур.{coffee_level})\n"
    else:
        t += f"<b>{fmt_money(coffee_price)}</b> → /buy coffee\n   (Ур.{coffee_level}/5, -{coffee_level*10}%)\n"
    t += f"\n💰 Баланс: {fmt_money(u['balance'])}"
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("buy"))
async def cmd_buy(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2 or args[1] not in SHOP_ITEMS:
        return await m.answer("❌ /buy course или /buy coffee (/shop)")

    it = SHOP_ITEMS[args[1]]
    u = await get_user(cid, uid)
    p = await get_profile(cid, uid)

    if it['type'] == 'level_up':
        price = 3000 * p['level']
        if u['balance'] < price:
            return await m.answer(f"❌ Нужно {fmt_money(price)}")
        await update_balance(cid, uid, -price)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET level=$1 WHERE chat_id=$2 AND user_id=$3", p['level'] + 1, cid, uid)
        await m.answer(f"✅ <b>Уровень повышен!</b>\n\n📊 Ур.{p['level']} → <b>Ур.{p['level']+1}</b>\n💰 {fmt_money(price)}\n\n💡 Следующий: <b>{fmt_money(3000 * (p['level']+1))}</b>", parse_mode="HTML")

    elif it['type'] == 'cooldown_reduce':
        coffee_level = p.get('coffee_level', 0)
        if coffee_level >= 5:
            return await m.answer("☕ Максимальный уровень!")
        price = 6000 * (coffee_level + 1)
        if u['balance'] < price:
            return await m.answer(f"❌ Нужно {fmt_money(price)}")
        await update_balance(cid, uid, -price)
        new_level = coffee_level + 1
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET coffee_level=$1 WHERE chat_id=$2 AND user_id=$3", new_level, cid, uid)
        text = f"☕ <b>Кофе улучшена!</b>\n\n📊 Ур.{coffee_level} → <b>{new_level}</b>\n⚡ -{new_level*10}% кулдаун\n💰 {fmt_money(price)}"
        if new_level < 5:
            text += f"\n\n💡 Следующий: <b>{fmt_money(6000 * (new_level + 1))}</b>"
        else:
            text += "\n\n🏆 Максимум!"
        await m.answer(text, parse_mode="HTML")


# --- АДМИН-ПАНЕЛЬ ---
@dp.message(Command("admin_panel"))
async def cmd_admin_panel(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 Банки игроков", callback_data="new_banks"), InlineKeyboardButton(text="👑 Назначить", callback_data="new_appoint")],
        [InlineKeyboardButton(text="🗳️ Голоса", callback_data="admin_votes"), InlineKeyboardButton(text="➖ Снять", callback_data="admin_remove_votes")],
        [InlineKeyboardButton(text="➕ Добавить", callback_data="admin_add_votes"), InlineKeyboardButton(text="💰 Выдать", callback_data="admin_give_money")],
        [InlineKeyboardButton(text="🏙️ Казна городов", callback_data="admin_city_treasury"), InlineKeyboardButton(text="🏛️ Фед. казна", callback_data="admin_state_treasury")],
        [InlineKeyboardButton(text="👥 Топ игроков", callback_data="admin_players")],
    ])
    await m.answer("🔒 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:", reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(lambda c: c.data and c.data.startswith("new_"))
async def callback_admin_new(callback: CallbackQuery):
    try:
        if callback.from_user.id not in ADMIN_IDS:
            return await callback.answer("❌ Доступ запрещён", show_alert=True)
        action = callback.data.replace("new_", "")
        cid = callback.message.chat.id
        cities_list = ", ".join([f"{c['emoji']} {c['name']} (ID: {c['id']})" for c in CITIES_LIST])

        if action == "banks":
            async with pool.acquire() as conn:
                players = await conn.fetch(
                    "SELECT u.user_id, u.balance, COALESCE(b.deposit, 0) as deposit FROM users u "
                    "LEFT JOIN bank b ON u.chat_id = b.chat_id AND u.user_id = b.user_id "
                    "WHERE u.chat_id = $1 ORDER BY (u.balance + COALESCE(b.deposit, 0)) DESC LIMIT 20", cid)
            text = "🏦 <b>БАНКИ ИГРОКОВ (ТОП-20)</b>\n\n"
            for i, p in enumerate(players, 1):
                name = await safe_name(cid, p['user_id'])
                text += (f"<b>{i}. {name}</b>\n   💵 Наличные: <b>{fmt_money(p['balance'])}</b>\n"
                         f"   🏦 В банке: <b>{fmt_money(p['deposit'])}</b>\n   💰 Всего: <b>{fmt_money(p['balance'] + p['deposit'])}</b>\n"
                         f"   🆔 ID: <code>{p['user_id']}</code>\n\n")
            text += f"━━━━━━━━━━━━━━━━━━━━\n/appoint president [id]\n/appoint prime [id]\n/appoint mayor [id] [город]\n\n<b>Города:</b>\n{cities_list}"
            await callback.message.edit_text(text[:4000], parse_mode="HTML")

        elif action == "appoint":
            await callback.message.edit_text(
                f"👑 <b>НАЗНАЧЕНИЕ НА ДОЛЖНОСТЬ</b>\n\n"
                f"🇷🇺 <b>Президент (90 дней):</b>\n<code>/appoint president [user_id]</code>\n\n"
                f"💼 <b>Премьер-министр (90 дней):</b>\n<code>/appoint prime [user_id]</code>\n\n"
                f"🏛️ <b>Мэр города (60 дней):</b>\n<code>/appoint mayor [user_id] [город_id]</code>\n\n"
                f"<b>Доступные города:</b>\n{cities_list}\n\n"
                f"⚠️ Старый чиновник будет снят автоматически", parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        print(f"Ошибка new_admin: {e}")
        await callback.answer("Ошибка", show_alert=True)


@dp.callback_query(lambda c: c.data and c.data.startswith("admin_"))
async def callback_admin_panel(callback: CallbackQuery):
    try:
        if callback.from_user.id not in ADMIN_IDS:
            return await callback.answer("❌ Доступ запрещён", show_alert=True)
        action = callback.data.replace("admin_", "")
        cid = callback.message.chat.id

        if action == "votes":
            text = "🗳️ <b>ГОЛОСА</b>\n\n"
            found = False
            for city in CITIES_LIST:
                election_id = await get_current_election_id(cid, city['id'])
                async with pool.acquire() as conn:
                    cands = await conn.fetch("SELECT user_id, votes FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3 ORDER BY votes DESC", cid, city['id'], election_id)
                if cands:
                    found = True
                    text += f"🏛️ <b>Мэр {city['emoji']} {city['name']}:</b>\n"
                    for i, c in enumerate(cands, 1):
                        name = await safe_name(cid, c['user_id'])
                        text += f"{i}. {name} — {c['votes']}\n"
                    text += "\n"

            for role, title in (('president', '🇷🇺 <b>Президент:</b>'), ('prime_minister', '💼 <b>Премьер:</b>')):
                election_id = await get_current_federal_election_id(cid, role)
                async with pool.acquire() as conn:
                    cands = await conn.fetch("SELECT user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND election_id=$3 ORDER BY votes DESC", cid, role, election_id)
                if cands:
                    found = True
                    text += title + "\n"
                    for i, c in enumerate(cands, 1):
                        name = await safe_name(cid, c['user_id'])
                        text += f"{i}. {name} — {c['votes']}\n"
                    text += "\n"

            if not found:
                text += "❌ Нет выборов"
            await callback.message.edit_text(text[:4000], parse_mode="HTML")

        elif action == "remove_votes":
            await callback.message.edit_text("➖ <b>СНЯТИЕ</b>\n\n/sys_remove [тип] [номер] [кол-во] [город_id]\n\nПримеры:\n/sys_remove mayor 2 5 1\n/sys_remove president 1 10\n/sys_remove prime 3 3\n\nТипы: mayor, president, prime", parse_mode="HTML")
        elif action == "add_votes":
            await callback.message.edit_text("➕ <b>ДОБАВЛЕНИЕ</b>\n\n/sys_add [тип] [номер] [кол-во] [город_id]\n\nПримеры:\n/sys_add mayor 2 5 1\n/sys_add president 1 10\n/sys_add prime 3 3\n\nТипы: mayor, president, prime", parse_mode="HTML")
        elif action == "give_money":
            await callback.message.edit_text("💰 <b>ВЫДАЧА</b>\n\n/sys_give [user_id] [сумма]\n\nПример:\n/sys_give 123456789 10000", parse_mode="HTML")
        elif action == "city_treasury":
            text = "🏙️ <b>КАЗНА</b>\n\n"
            for city in CITIES_LIST:
                amount = await get_city_treasury(cid, city['id'])
                text += f"{city['emoji']} {city['name']}: <b>{fmt_money(amount)}</b>\n"
            await callback.message.edit_text(text, parse_mode="HTML")
        elif action == "state_treasury":
            amount = await get_state_treasury(cid)
            await callback.message.edit_text(f"🏛️ <b>ФЕД. КАЗНА</b>\n\n💰 <b>{fmt_money(amount)}</b>", parse_mode="HTML")
        elif action == "players":
            async with pool.acquire() as conn:
                players = await conn.fetch("SELECT user_id, balance FROM users WHERE chat_id=$1 ORDER BY balance DESC LIMIT 20", cid)
            text = "👥 <b>ТОП-20</b>\n\n"
            for i, p in enumerate(players, 1):
                name = await safe_name(cid, p['user_id'])
                text += f"{i}. {name} — {fmt_money(p['balance'])}\n"
            await callback.message.edit_text(text[:4000], parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        print(f"Ошибка callback_admin: {e}")
        await callback.answer("Ошибка", show_alert=True)


async def _manage_votes(m: Message, add: bool):
    if m.from_user.id not in ADMIN_IDS:
        return
    args = m.text.split()
    cmd = "sys_add" if add else "sys_remove"
    if len(args) < 4:
        return await m.answer(f"/{cmd} [тип] [номер] [кол-во] [город_id]\n\n/{cmd} mayor 2 5 1\n/{cmd} president 1 10\n/{cmd} prime 3 3", parse_mode="HTML")

    election_type = args[1].lower()
    try:
        candidate_num = int(args[2])
        votes_change = int(args[3])
    except ValueError:
        return await m.answer("❌ Числа!")
    if votes_change <= 0:
        return await m.answer("❌ >0!")

    cid = m.chat.id if m.chat.type != 'private' else ADMIN_CHAT_ID

    if election_type == 'mayor':
        if len(args) < 5:
            return await m.answer("❌ Укажи город_id: " + ", ".join([f"{c['name']}={c['id']}" for c in CITIES_LIST]))
        try:
            city_id = int(args[4])
        except ValueError:
            return await m.answer("❌ город_id — число!")
        election_id = await get_current_election_id(cid, city_id)
        table = 'mayor_candidates'
        role_name = 'мэра'
        async with pool.acquire() as conn:
            candidates = await conn.fetch("SELECT id, user_id, votes FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3 ORDER BY id ASC", cid, city_id, election_id)
    elif election_type in ('president', 'prime'):
        role = 'president' if election_type == 'president' else 'prime_minister'
        election_id = await get_current_federal_election_id(cid, role)
        table = 'federal_candidates'
        role_name = 'президента' if election_type == 'president' else 'премьера'
        async with pool.acquire() as conn:
            candidates = await conn.fetch("SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role=$2 AND election_id=$3 ORDER BY id ASC", cid, role, election_id)
    else:
        return await m.answer("❌ Неверный тип!")

    if not candidates:
        return await m.answer("❌ Нет кандидатов!")
    if candidate_num < 1 or candidate_num > len(candidates):
        return await m.answer(f"❌ 1-{len(candidates)}")

    candidate = candidates[candidate_num - 1]
    if add:
        new_votes = candidate['votes'] + votes_change
    else:
        if candidate['votes'] < votes_change:
            return await m.answer(f"❌ Только {candidate['votes']}")
        new_votes = candidate['votes'] - votes_change

    async with pool.acquire() as conn:
        await conn.execute(f"UPDATE {table} SET votes=$1 WHERE id=$2", new_votes, candidate['id'])

    candidate_name = await safe_name(cid, candidate['user_id'])
    sign = "+" if add else "-"
    emoji = "📈" if add else "📉"
    title = "ДОБАВЛЕНЫ" if add else "СНЯТЫ"
    await m.answer(f"✅ <b>ГОЛОСА {title}!</b>\n\n👤 {candidate_name}\n🗳️ {role_name}\n{emoji} {sign}{votes_change}\n🔢 {new_votes}", parse_mode="HTML")


@dp.message(Command("sys_add"))
async def cmd_sys_add(m: Message):
    try:
        await _manage_votes(m, True)
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("sys_remove"))
async def cmd_sys_remove(m: Message):
    try:
        await _manage_votes(m, False)
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("sys_give"))
async def cmd_sys_give(m: Message):
    try:
        if m.from_user.id not in ADMIN_IDS:
            return
        args = m.text.split()
        if len(args) < 3:
            return await m.answer("/sys_give [user_id] [сумма]")
        target_uid = int(args[1])
        amount = int(args[2])
        cid = m.chat.id if m.chat.type != 'private' else ADMIN_CHAT_ID
        await update_balance(cid, target_uid, amount)
        await m.answer(f"✅ Выдано {fmt_money(amount)} игроку {target_uid}")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


# --- ГОРОДА ---
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
        t += "/city choose [название]"
        return await m.answer(t, parse_mode="HTML")

    if subcmd == "info":
        player_city = await get_player_city(cid, uid)
        if not player_city:
            return await m.answer("❌ Нет города!\n/city choose [город]")
        mayor = await get_mayor(cid, player_city['id'])
        treasury = await get_city_treasury(cid, player_city['id'])
        t = f"{player_city['emoji']} <b>{player_city['name']}</b>\n\n📊 {player_city['desc']}\n💰 Казна: {fmt_money(treasury)}\n\n"
        if mayor:
            mayor_name = await safe_name(cid, mayor['user_id'])
            days_left = int((mayor['expires_at'] - time.time()) / 86400)
            t += f"🏛️ Мэр: {mayor_name}\n📊 Рейтинг: {mayor['approval_rating']}%\n⏰ {days_left} дн."
        else:
            t += "🏛️ Мэр: ВАКАНТНО"
        return await m.answer(t, parse_mode="HTML")

    if subcmd == "choose":
        if len(args) < 3:
            return await m.answer("⚠️ /city choose Москва")
        city_name = " ".join(args[2:])
        existing = await get_player_city(cid, uid)
        if existing:
            return await m.answer(f"❌ Уже в <b>{existing['name']}</b>!\n/city move", parse_mode="HTML")
        city = next((c for c in CITIES_LIST if c['name'].lower() == city_name.lower()), None)
        if not city:
            return await m.answer("❌ Не найден! /city list")
        await get_user(cid, uid)
        await set_player_city(cid, uid, city['id'])
        return await m.answer(f"🎉 <b>Добро пожаловать в {city['emoji']} {city['name']}!</b>\n\n📊 {city['desc']}", parse_mode="HTML")

    if subcmd == "move":
        if len(args) < 3:
            return await m.answer("⚠️ /city move Москва")
        city_name = " ".join(args[2:])
        existing = await get_player_city(cid, uid)
        if not existing:
            return await m.answer("❌ Сначала /city choose")

        cooldown_left = CITY_MOVE_COOLDOWN - (time.time() - existing['moved_at'])
        if cooldown_left > 0:
            hours = int(cooldown_left / 3600)
            return await m.answer(f"⏳ Переезд доступен через {hours} ч.")

        city = next((c for c in CITIES_LIST if c['name'].lower() == city_name.lower()), None)
        if not city:
            return await m.answer("❌ Не найден! /city list")
        if city['id'] == existing['id']:
            return await m.answer("❌ Уже здесь!")

        user = await get_user(cid, uid)
        if user['balance'] < CITY_MOVE_COST:
            return await m.answer(f"❌ Нужно {fmt_money(CITY_MOVE_COST)}")
        await update_balance(cid, uid, -CITY_MOVE_COST)
        await set_player_city(cid, uid, city['id'])
        return await m.answer(f"🚚 <b>ПЕРЕЕЗД!</b>\n\n{city['emoji']} {city['name']}\n📊 {city['desc']}", parse_mode="HTML")

    if subcmd == "residents":
        player_city = await get_player_city(cid, uid)
        if not player_city:
            return await m.answer("❌ Нет города!")
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM player_cities WHERE chat_id=$1 AND city_id=$2", cid, player_city['id'])
            residents = await conn.fetch("SELECT user_id FROM player_cities WHERE chat_id=$1 AND city_id=$2 LIMIT 20", cid, player_city['id'])
        if not residents:
            return await m.answer("🏙️ Никого нет!")
        t = f"{player_city['emoji']} <b>Жители {player_city['name']}:</b>\n\n"
        for i, r in enumerate(residents, 1):
            name = await safe_name(cid, r['user_id'])
            t += f"{i}. {name}\n"
        t += f"\n📊 Всего: {total}"
        return await m.answer(t, parse_mode="HTML")

    await m.answer("❓ /city")


# --- МЭР ---
@dp.message(Command("mayor_nominate"))
async def cmd_mayor_nominate(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        player_city = await get_player_city(cid, uid)
        if not player_city:
            return await m.answer("❌ Нет города! /city choose")
        success, msg = await nominate_mayor(cid, uid, player_city['id'])
        await m.answer(msg, parse_mode="HTML")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("mayor_vote"))
async def cmd_mayor_vote(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        player_city = await get_player_city(cid, uid)
        if not player_city:
            return await m.answer("❌ Нет города! /city choose")

        if len(args) < 2:
            election_id = await get_current_election_id(cid, player_city['id'])
            async with pool.acquire() as conn:
                candidates = await conn.fetch("SELECT user_id, votes FROM mayor_candidates WHERE chat_id=$1 AND city_id=$2 AND election_id=$3 ORDER BY id ASC", cid, player_city['id'], election_id)
            if not candidates:
                return await m.answer(f"🏛️ <b>Выборы в {player_city['emoji']} {player_city['name']}</b>\n\n❌ Нет кандидатов.\n/mayor_nominate", parse_mode="HTML")
            t = f"🏛️ <b>Кандидаты {player_city['emoji']} {player_city['name']}:</b>\n\n"
            for i, c in enumerate(candidates, 1):
                name = await safe_name(cid, c['user_id'])
                t += f"{i}. {name} ({c['votes']})\n"
            t += f"\n💰 {MAYOR_VOTE_COST}\n/mayor_vote [номер]"
            return await m.answer(t, parse_mode="HTML")

        try:
            candidate_num = int(args[1])
        except ValueError:
            return await m.answer("❌ Число!")
        success, msg = await vote_for_mayor(cid, uid, player_city['id'], candidate_num)
        await m.answer(msg, parse_mode="HTML")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("mayor_finalize"))
async def cmd_mayor_finalize(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        if uid not in ADMIN_IDS:
            return await m.answer("❌ Только админ может завершить выборы досрочно!")
        player_city = await get_player_city(cid, uid)
        if not player_city:
            return await m.answer("❌ Нет города!")
        result = await finalize_mayor_election(cid, player_city['id'])
        if result is None:
            return await m.answer("🏛️ <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
        name = await safe_name(cid, result['user_id'])
        return await m.answer(f"🎉 <b>НОВЫЙ МЭР!</b>\n\n🏛️ {player_city['emoji']} {player_city['name']}\n👤 {name}\n🗳️ {result['votes']}\n💰 +{fmt_money(result['bonus'])}\n⏰ {MAYOR_TERM_DAYS} дн.\n\n/city info", parse_mode="HTML")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("mayor_decree"))
async def cmd_mayor_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city:
        return await m.answer("❌ Нет города!")
    if not await is_mayor(cid, uid, player_city['id']):
        return await m.answer("❌ Только мэр!")

    args = m.text.split()
    if len(args) < 2:
        treasury = await get_city_treasury(cid, player_city['id'])
        return await m.answer(f"🏛️ <b>УКАЗЫ МЭРА</b>\n\n/mayor_decree work (+20% работа, 5к)\n/mayor_decree tools (-30% инструменты, 3к)\n/mayor_decree business (-15% бизнес, 8к)\n/mayor_decree cars (-25% авто, 4к)\n/mayor_decree event (праздник, 10к)\n\n💰 Казна: {fmt_money(treasury)}", parse_mode="HTML")

    decree_map = {'work': 'work_bonus', 'tools': 'tool_discount', 'business': 'business_bonus', 'cars': 'car_discount', 'event': 'city_event'}
    decree_type = decree_map.get(args[1].lower())
    if not decree_type:
        return await m.answer("❌ Неизвестный указ!")
    success, msg = await create_decree(cid, player_city['id'], uid, decree_type)
    await m.answer(msg, parse_mode="HTML")


@dp.message(Command("city_decrees"))
async def cmd_city_decrees(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city:
        return await m.answer("❌ Нет города!")
    async with pool.acquire() as conn:
        decrees = await conn.fetch("SELECT * FROM city_decrees WHERE chat_id=$1 AND city_id=$2 AND active_until > $3", cid, player_city['id'], time.time())
    if not decrees:
        return await m.answer(f"🏛️ <b>{player_city['emoji']} {player_city['name']}</b>\n\n❌ Нет указов", parse_mode="HTML")
    t = f"🏛️ <b>Указы {player_city['emoji']} {player_city['name']}:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {get_decree_name(d['decree_type'])}\n  ⏰ {hours_left} ч.\n\n"
    await m.answer(t, parse_mode="HTML")


# --- ФЕДЕРАЛЬНАЯ ПОЛИТИКА ---
@dp.message(Command("president_nominate"))
async def cmd_president_nominate(m: Message):
    try:
        success, msg = await nominate_federal(m.chat.id, m.from_user.id, 'president')
        await m.answer(msg, parse_mode="HTML")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("president_vote"))
async def cmd_president_vote(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2:
            election_id = await get_current_federal_election_id(cid, 'president')
            async with pool.acquire() as conn:
                candidates = await conn.fetch("SELECT user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='president' AND election_id=$2 ORDER BY id ASC", cid, election_id)
            if not candidates:
                return await m.answer("🏛️ <b>Выборы Президента</b>\n\n❌ Нет кандидатов.\n/president_nominate", parse_mode="HTML")
            t = "🏛️ <b>Кандидаты:</b>\n\n"
            for i, c in enumerate(candidates, 1):
                name = await safe_name(cid, c['user_id'])
                t += f"{i}. {name} ({c['votes']})\n"
            t += f"\n💰 {PRESIDENT_VOTE_COST}\n/president_vote [номер]"
            return await m.answer(t, parse_mode="HTML")
        try:
            candidate_num = int(args[1])
        except ValueError:
            return await m.answer("❌ Число!")
        success, msg = await vote_federal(cid, uid, 'president', candidate_num)
        await m.answer(msg, parse_mode="HTML")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("president_finalize"))
async def cmd_president_finalize(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        if uid not in ADMIN_IDS:
            return await m.answer("❌ Только админ!")
        result = await finalize_federal_election(cid, 'president')
        if result is None:
            return await m.answer("🏛️ <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
        name = await safe_name(cid, result['user_id'])
        return await m.answer(f"🎉 <b>НОВЫЙ ПРЕЗИДЕНТ!</b>\n\n👤 {name}\n🗳️ {result['votes']}\n💰 +{fmt_money(result['bonus'])}\n⏰ {PRESIDENT_TERM_DAYS} дн.", parse_mode="HTML")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("president_decree"))
async def cmd_president_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if not await is_federal_official(cid, uid, 'president'):
        return await m.answer("❌ Только Президент!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("🏛️ <b>УКАЗЫ</b>\n\n/president_decree amnesty\n/president_decree tax_cut\n/president_decree tax_boost\n/president_decree emergency", parse_mode="HTML")

    decree_type = args[1].lower()
    if decree_type not in ('amnesty', 'tax_cut', 'tax_boost', 'emergency'):
        return await m.answer("❌ Неизвестный указ!")

    if decree_type == 'amnesty':
        async with pool.acquire() as conn:
            jailed = await conn.fetch("SELECT user_id FROM jail WHERE chat_id=$1 AND release_time > $2", cid, time.time())
            count = len(jailed)
            if count > 0:
                await conn.execute("DELETE FROM jail WHERE chat_id=$1 AND release_time > $2", cid, time.time())
                await conn.execute("UPDATE jail_fines SET paid=TRUE WHERE chat_id=$1", cid)
        return await m.answer(f"🕊️ <b>АМНИСТИЯ!</b>\n\nОсвобождено: <b>{count}</b>", parse_mode="HTML")

    success, msg = await create_federal_decree(cid, uid, 'president', decree_type)
    await m.answer(msg, parse_mode="HTML")


@dp.message(Command("president_decrees"))
async def cmd_president_decrees(m: Message):
    cid = m.chat.id
    async with pool.acquire() as conn:
        decrees = await conn.fetch("SELECT * FROM federal_decrees WHERE chat_id=$1 AND role='president' AND active_until > $2", cid, time.time())
    if not decrees:
        return await m.answer("🏛️ <b>Указы Президента</b>\n\n❌ Нет активных", parse_mode="HTML")
    t = "🏛️ <b>Активные указы:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {get_federal_decree_name(d['decree_type'])}\n  ⏰ {hours_left} ч.\n\n"
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("prime_nominate"))
async def cmd_prime_nominate(m: Message):
    try:
        success, msg = await nominate_federal(m.chat.id, m.from_user.id, 'prime_minister')
        await m.answer(msg, parse_mode="HTML")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("prime_vote"))
async def cmd_prime_vote(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2:
            election_id = await get_current_federal_election_id(cid, 'prime_minister')
            async with pool.acquire() as conn:
                candidates = await conn.fetch("SELECT user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='prime_minister' AND election_id=$2 ORDER BY id ASC", cid, election_id)
            if not candidates:
                return await m.answer("💼 <b>Выборы Премьера</b>\n\n❌ Нет кандидатов.\n/prime_nominate", parse_mode="HTML")
            t = "💼 <b>Кандидаты:</b>\n\n"
            for i, c in enumerate(candidates, 1):
                name = await safe_name(cid, c['user_id'])
                t += f"{i}. {name} ({c['votes']})\n"
            t += f"\n💰 {PRIME_MINISTER_VOTE_COST}\n/prime_vote [номер]"
            return await m.answer(t, parse_mode="HTML")
        try:
            candidate_num = int(args[1])
        except ValueError:
            return await m.answer("❌ Число!")
        success, msg = await vote_federal(cid, uid, 'prime_minister', candidate_num)
        await m.answer(msg, parse_mode="HTML")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("prime_finalize"))
async def cmd_prime_finalize(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        if uid not in ADMIN_IDS:
            return await m.answer("❌ Только админ!")
        result = await finalize_federal_election(cid, 'prime_minister')
        if result is None:
            return await m.answer("💼 <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
        name = await safe_name(cid, result['user_id'])
        return await m.answer(f"🎉 <b>НОВЫЙ ПРЕМЬЕР!</b>\n\n👤 {name}\n🗳️ {result['votes']}\n💰 +{fmt_money(result['bonus'])}\n⏰ {PRIME_MINISTER_TERM_DAYS} дн.", parse_mode="HTML")
    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("prime_decree"))
async def cmd_prime_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if not await is_federal_official(cid, uid, 'prime_minister'):
        return await m.answer("❌ Только Премьер!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("💼 <b>УКАЗЫ</b>\n\n/prime_decree subsidy\n/prime_decree investment\n/prime_decree tax_cut\n/prime_decree tax_boost", parse_mode="HTML")

    decree_type = args[1].lower()
    if decree_type not in ('subsidy', 'investment', 'tax_cut', 'tax_boost'):
        return await m.answer("❌ Неизвестный указ!")

    if decree_type == 'investment':
        async with pool.acquire() as conn:
            cities = await conn.fetch("SELECT DISTINCT city_id FROM player_cities WHERE chat_id=$1", cid)
        for city_row in cities:
            await update_city_treasury(cid, city_row['city_id'], 5000)
        return await m.answer(f"🏗️ <b>ИНВЕСТИЦИИ!</b>\n\nКаждому городу + <b>5000</b>\nГородов: <b>{len(cities)}</b>", parse_mode="HTML")

    success, msg = await create_federal_decree(cid, uid, 'prime_minister', decree_type)
    await m.answer(msg, parse_mode="HTML")


@dp.message(Command("prime_decrees"))
async def cmd_prime_decrees(m: Message):
    cid = m.chat.id
    async with pool.acquire() as conn:
        decrees = await conn.fetch("SELECT * FROM federal_decrees WHERE chat_id=$1 AND role='prime_minister' AND active_until > $2", cid, time.time())
    if not decrees:
        return await m.answer("💼 <b>Указы Премьера</b>\n\n❌ Нет активных", parse_mode="HTML")
    t = "💼 <b>Активные указы:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {get_federal_decree_name(d['decree_type'])}\n  ⏰ {hours_left} ч.\n\n"
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("impeach"))
async def cmd_impeach(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("⚖️ <b>ИМПИЧМЕНТ</b>\n\n/impeach president — против Президента\n/impeach prime — против Премьера\n\nНужно 10 голосов", parse_mode="HTML")

    role = args[1].lower()
    if role not in ('president', 'prime'):
        return await m.answer("❌ Используй president или prime")
    db_role = 'president' if role == 'president' else 'prime_minister'

    official = await get_federal_role(cid, db_role)
    if not official:
        return await m.answer("❌ Сейчас нет действующего чиновника!")
    if official['user_id'] == uid:
        return await m.answer("❌ Нельзя голосовать против себя!")

    async with pool.acquire() as conn:
        already = await conn.fetchrow("SELECT 1 FROM impeachment_votes WHERE chat_id=$1 AND role=$2 AND voter_id=$3", cid, db_role, uid)
        if already:
            return await m.answer("❌ Ты уже голосовал за импичмент!")
        await conn.execute("INSERT INTO impeachment_votes (chat_id, role, voter_id, voted_at) VALUES ($1,$2,$3,$4)", cid, db_role, uid, time.time())
        votes = await conn.fetchval("SELECT COUNT(*) FROM impeachment_votes WHERE chat_id=$1 AND role=$2", cid, db_role)

    role_name = "Президент" if role == 'president' else "Премьер"
    if votes >= 10:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM federal_roles WHERE chat_id=$1 AND role=$2", cid, db_role)
            await conn.execute("DELETE FROM impeachment_votes WHERE chat_id=$1 AND role=$2", cid, db_role)
        official_name = await safe_name(cid, official['user_id'])
        await m.answer(f"⚖️ <b>ИМПИЧМЕНТ УСПЕШЕН!</b>\n\n👤 {role_name} {official_name} отстранён от должности!\n🗳️ Голосов: {votes}/10\n\n⏳ Новые выборы открыты", parse_mode="HTML")
    else:
        await m.answer(f"⚖️ Голос за импичмент {role_name} принят!\n📊 Голосов: {votes}/10", parse_mode="HTML")


# --- ДОЛГИ МЕЖДУ ИГРОКАМИ ---
@dp.message(Command("debt_give"))
async def cmd_debt_give(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 3:
        return await m.answer(f"📜 <b>ДАТЬ В ДОЛГ</b>\n\nОтветь на сообщение:\n/debt_give сумма дни\n\nПример: /debt_give 50000 3\nКомиссия: {DEBT_FEE_PERCENT}%", parse_mode="HTML")
    if not m.reply_to_message:
        return await m.answer("⚠️ Ответь на сообщение!")

    borrower_id = m.reply_to_message.from_user.id
    if borrower_id == uid:
        return await m.answer("❌ Нельзя себе!")
    if await is_in_jail(cid, borrower_id):
        return await m.answer("🔒 Заёмщик в тюрьме!")

    try:
        amount = int(args[1])
        days = int(args[2])
    except ValueError:
        return await m.answer("❌ Числа!")

    if amount < DEBT_MIN_AMOUNT or amount > DEBT_MAX_AMOUNT:
        return await m.answer(f"❌ От {fmt_money(DEBT_MIN_AMOUNT)} до {fmt_money(DEBT_MAX_AMOUNT)}")
    if days < DEBT_MIN_DAYS or days > DEBT_MAX_DAYS:
        return await m.answer(f"❌ {DEBT_MIN_DAYS}-{DEBT_MAX_DAYS} дн.")

    fee = int(amount * DEBT_FEE_PERCENT / 100)
    total = amount + fee
    lender = await get_user(cid, uid)
    if lender['balance'] < total:
        return await m.answer(f"❌ Нужно {fmt_money(total)}\nУ вас: {fmt_money(lender['balance'])}", parse_mode="HTML")

    deadline = time.time() + days * 86400
    await update_balance(cid, uid, -total)
    await update_balance(cid, borrower_id, amount)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO debts (chat_id, lender_id, borrower_id, amount, fee, created_at, deadline) VALUES ($1,$2,$3,$4,$5,$6,$7)",
            cid, uid, borrower_id, amount, fee, time.time(), deadline)

    borrower_name = m.reply_to_message.from_user.full_name
    await m.answer(f"📜 <b>РАСПИСКА</b>\n\n👤 {borrower_name}\n💰 {fmt_money(amount)}\n📅 {days} дн.\n🏦 Комиссия: {fmt_money(fee)}\n📤 Списано: {fmt_money(total)}\n\n⚠️ При просрочке — коллекторы (+{DEBT_PENALTY_PERCENT}%)!\n\nВернуть: /debt_return", parse_mode="HTML")


@dp.message(Command("debt_return"))
async def cmd_debt_return(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    async with pool.acquire() as conn:
        debt = await conn.fetchrow("SELECT * FROM debts WHERE chat_id=$1 AND borrower_id=$2 AND status='active' ORDER BY deadline ASC LIMIT 1", cid, uid)
    if not debt:
        return await m.answer("✅ Нет долгов!")

    user = await get_user(cid, uid)
    if user['balance'] < debt['amount']:
        return await m.answer(f"❌ Нужно {fmt_money(debt['amount'])}")

    await update_balance(cid, uid, -debt['amount'])
    await update_balance(cid, debt['lender_id'], debt['amount'])
    async with pool.acquire() as conn:
        await conn.execute("UPDATE debts SET status='returned' WHERE id=$1", debt['id'])
    new_bal = (await get_user(cid, uid))['balance']
    await m.answer(f"✅ <b>ДОЛГ ПОГАШЕН!</b>\n\n💰 {fmt_money(debt['amount'])}\n📊 Баланс: {fmt_money(new_bal)}", parse_mode="HTML")


@dp.message(Command("debt_list"))
async def cmd_debt_list(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    async with pool.acquire() as conn:
        i_owe = await conn.fetch("SELECT * FROM debts WHERE chat_id=$1 AND borrower_id=$2 AND status='active'", cid, uid)
        owed_me = await conn.fetch("SELECT * FROM debts WHERE chat_id=$1 AND lender_id=$2 AND status='active'", cid, uid)

    t = "📋 <b>ДОЛГИ</b>\n\n"
    if i_owe:
        t += "📤 <b>Я должен:</b>\n"
        for d in i_owe:
            name = await safe_name(cid, d['lender_id'])
            days = int((d['deadline'] - time.time()) / 86400)
            t += f"• {name}: {fmt_money(d['amount'])} ({days} дн.)\n"
    else:
        t += "✅ Я никому не должен\n"

    if owed_me:
        t += "\n📥 <b>Мне должны:</b>\n"
        for d in owed_me:
            name = await safe_name(cid, d['borrower_id'])
            days = int((d['deadline'] - time.time()) / 86400)
            t += f"• {name}: {fmt_money(d['amount'])} ({days} дн.)\n"
    else:
        t += "\n✅ Мне никто не должен"
    await m.answer(t, parse_mode="HTML")


# --- ПРОЕКТЫ МЭРА ---
@dp.message(Command("mayor_project"))
async def cmd_mayor_project(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city:
        return await m.answer("❌ Нет города!")
    if not await is_mayor(cid, uid, player_city['id']):
        return await m.answer("❌ Только мэр!")

    args = m.text.split(maxsplit=1)
    if len(args) < 2:
        proj_list = "\n".join([f"• /mayor_project {k} — {v['name']} ({fmt_money(v['cost'])})" for k, v in PROJECT_TYPES.items()])
        return await m.answer(f"🏗️ <b>ПРОЕКТЫ МЭРА</b>\n\nВыбери проект:\n{proj_list}\n\n⏰ Срок: 24 часа\n⚠️ 1-й провал = штраф 50%\n⚠️ 2-й провал = тюрьма + снятие", parse_mode="HTML")

    project_key = args[1].lower().strip()
    if project_key not in PROJECT_TYPES:
        return await m.answer("❌ Неизвестный проект!")
    project = PROJECT_TYPES[project_key]
    cost = project['cost']
    treasury = await get_city_treasury(cid, player_city['id'])
    if treasury < cost:
        return await m.answer(f"❌ В казне только {fmt_money(treasury)}! Нужно {fmt_money(cost)}")

    async with pool.acquire() as conn:
        active = await conn.fetchrow("SELECT 1 FROM mayor_projects WHERE chat_id=$1 AND city_id=$2 AND mayor_id=$3 AND status='active'", cid, player_city['id'], uid)
        if active:
            return await m.answer("⚠️ У тебя уже есть активный проект!")

    await update_city_treasury(cid, player_city['id'], -cost)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO mayor_projects (chat_id, city_id, mayor_id, project_type, budget, description, started_at, deadline) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
            cid, player_city['id'], uid, project_key, cost, project['desc'], time.time(), time.time() + 86400)

    await m.answer(f"🏗️ <b>ПРОЕКТ ЗАПУЩЕН!</b>\n\n🏙️ {player_city['emoji']} {player_city['name']}\n📋 {project['name']} — {project['desc']}\n💰 Бюджет: {fmt_money(cost)}\n⏰ Срок: 24 часа\n\nИспользуй <b>/project_done</b> чтобы завершить", parse_mode="HTML")


@dp.message(Command("project_done"))
async def cmd_project_done(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city:
        return await m.answer("❌ Нет города!")
    async with pool.acquire() as conn:
        project = await conn.fetchrow("SELECT * FROM mayor_projects WHERE chat_id=$1 AND city_id=$2 AND mayor_id=$3 AND status='active' ORDER BY started_at DESC LIMIT 1", cid, player_city['id'], uid)
        if not project:
            return await m.answer("❌ Нет активного проекта!")
        if time.time() > project['deadline']:
            return await m.answer("⏰ Срок уже истёк! Жди проверки.")
        await conn.execute("UPDATE mayor_projects SET status='completed', completed_at=$1 WHERE id=$2", time.time(), project['id'])
    await m.answer(f"✅ <b>ПРОЕКТ ЗАВЕРШЁН!</b>\n\n📋 {PROJECT_TYPES[project['project_type']]['name']}\n⏳ Ожидает проверки Президентом", parse_mode="HTML")


@dp.message(Command("project_check"))
async def cmd_project_check(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if not await is_federal_official(cid, uid, 'president'):
        return await m.answer("❌ Только Президент!")

    args = m.text.split()
    if len(args) < 2:
        return await m.answer("⚖️ <b>ПРОВЕРКА ПРОЕКТА</b>\n\n/project_check [город_id] [approve/reject]", parse_mode="HTML")
    try:
        city_id = int(args[1])
    except ValueError:
        return await m.answer("❌ ID города должен быть числом!")

    action = args[2].lower() if len(args) > 2 else None
    if action not in ('approve', 'reject'):
        return await m.answer("❌ Используй approve или reject!")

    city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
    if not city:
        return await m.answer("❌ Город не найден!")

    async with pool.acquire() as conn:
        project = await conn.fetchrow("SELECT * FROM mayor_projects WHERE chat_id=$1 AND city_id=$2 AND status IN ('active','completed') ORDER BY started_at DESC LIMIT 1", cid, city_id)
    if not project:
        return await m.answer(f"✅ В {city['emoji']} {city['name']} нет проектов!")

    mayor_name = await safe_name(cid, project['mayor_id'])
    project_info = PROJECT_TYPES.get(project['project_type'], {"name": "Неизвестно"})

    if action == 'approve':
        bonus = int(project['budget'] * 0.30)
        await update_city_treasury(cid, city_id, bonus)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE mayors SET approval_rating = LEAST(100, approval_rating + 15) WHERE chat_id=$1 AND city_id=$2", cid, city_id)
            await conn.execute("UPDATE mayor_projects SET status='approved', reviewed_by=$1, review_result='Одобрено' WHERE id=$2", uid, project['id'])
        msg = f"✅ <b>ПРОЕКТ ОДОБРЕН!</b>\n\n🏙️ {city['emoji']} {city['name']}\n📋 {project_info['name']}\n👤 Мэр: {mayor_name}\n💰 Возврат в казну: {fmt_money(bonus)}\n📈 Рейтинг мэра: +15%"
    else:
        fail_count = (project['fail_count'] or 0) + 1
        if fail_count >= 2:
            await send_to_jail(cid, project['mayor_id'], 6)
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM mayors WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                await conn.execute("UPDATE mayor_projects SET status='failed', fail_count=$1, reviewed_by=$2, review_result='Снят' WHERE id=$3", fail_count, uid, project['id'])
            msg = f"🔒 <b>МЭР СНЯТ С ДОЛЖНОСТИ!</b>\n\n🏙️ {city['emoji']} {city['name']}\n📋 {project_info['name']}\n👤 {mayor_name}\n⚠️ 2-й провал проекта!\n🔒 Тюрьма: 6 часов\n📉 Должность: ВАКАНТНО"
        else:
            fine = int(project['budget'] * 0.50)
            await update_balance(cid, project['mayor_id'], -fine)
            async with pool.acquire() as conn:
                await conn.execute("UPDATE mayors SET approval_rating = GREATEST(0, approval_rating - 20) WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                await conn.execute("UPDATE mayor_projects SET status='failed', fail_count=$1, reviewed_by=$2, review_result='Штраф' WHERE id=$3", fail_count, uid, project['id'])
            msg = f"❌ <b>ПРОЕКТ ОТКЛОНЁН!</b>\n\n🏙️ {city['emoji']} {city['name']}\n📋 {project_info['name']}\n👤 Мэр: {mayor_name}\n💸 Штраф: {fmt_money(fine)} (50% бюджета)\n📉 Рейтинг: -20%\n⚠️ Провалов: {fail_count}/2\n🔜 Следующий провал = тюрьма + снятие!"

    await m.answer(msg, parse_mode="HTML")


@dp.message(Command("project_status"))
async def cmd_project_status(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        player_city = await get_player_city(cid, uid)
        if not player_city:
            return await m.answer("❌ Нет города!")
        city_id = player_city['id']
        city_name = player_city['name']
        city_emoji = player_city['emoji']
    else:
        try:
            city_id = int(args[1])
        except ValueError:
            return await m.answer("❌ ID города должен быть числом!")
        city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
        if not city:
            return await m.answer("❌ Город не найден!")
        city_name = city['name']
        city_emoji = city['emoji']

    async with pool.acquire() as conn:
        projects = await conn.fetch("SELECT * FROM mayor_projects WHERE chat_id=$1 AND city_id=$2 ORDER BY started_at DESC LIMIT 5", cid, city_id)
    if not projects:
        return await m.answer(f"🏙️ {city_emoji} {city_name}\n\n📋 Нет проектов")

    t = f"🏙️ <b>{city_emoji} {city_name}</b>\n\n📋 <b>Проекты:</b>\n\n"
    for p in projects:
        proj_info = PROJECT_TYPES.get(p['project_type'], {"name": "Неизвестно"})
        status_emoji = {'active': '🔄', 'completed': '✅', 'approved': '🏆', 'failed': '❌'}.get(p['status'], '❓')
        time_left = int(p['deadline'] - time.time())
        if p['status'] == 'active' and time_left > 0:
            time_text = f"⏰ {time_left//3600}ч {(time_left%3600)//60}мин"
        elif p['status'] == 'active':
            time_text = "⚠️ ПРОСРОЧЕНО"
        else:
            time_text = ""
        t += f"{status_emoji} <b>{proj_info['name']}</b>\n   💰 {fmt_money(p['budget'])} {time_text}\n   📊 Статус: {p['status']}\n\n"
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("mayor_report"))
async def cmd_mayor_report(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city:
        return await m.answer("❌ Нет города!")
    if not await is_mayor(cid, uid, player_city['id']):
        return await m.answer("❌ Только мэр!")

    args = m.text.split(maxsplit=1)
    if len(args) < 2:
        return await m.answer("📊 <b>ОТЧЁТ</b>\n\n/mayor_report [описание]\n\nПример: /mayor_report Построен парк", parse_mode="HTML")
    description = args[1]

    async with pool.acquire() as conn:
        report = await conn.fetchrow("SELECT * FROM mayor_reports WHERE chat_id=$1 AND city_id=$2 AND mayor_id=$3 AND status='pending' ORDER BY created_at DESC LIMIT 1", cid, player_city['id'], uid)
    if not report:
        return await m.answer("❌ Нет заданий!")
    if time.time() > report['report_deadline']:
        return await m.answer("⏰ Срок истёк!")

    async with pool.acquire() as conn:
        await conn.execute("UPDATE mayor_reports SET status='submitted', budget_spent=budget_allocated WHERE id=$1", report['id'])
    await m.answer(f"📊 <b>ОТЧЁТ СДАН!</b>\n\n🏙️ {player_city['emoji']} {player_city['name']}\n💰 {fmt_money(report['budget_allocated'])}\n📋 {description}\n\n⏳ Ожидает проверки Президента...", parse_mode="HTML")


@dp.message(Command("president_check_mayor"))
async def cmd_president_check_mayor(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if not await is_federal_official(cid, uid, 'president'):
        return await m.answer("❌ Только Президент!")

    args = m.text.split()
    if len(args) < 2:
        cities_list = ", ".join([f"{c['name']}={c['id']}" for c in CITIES_LIST])
        return await m.answer(f"⚖️ <b>ПРОВЕРКА</b>\n\n/president_check_mayor [город_id] [approve/reject]\n\nГорода: {cities_list}", parse_mode="HTML")
    try:
        city_id = int(args[1])
    except ValueError:
        return await m.answer("❌ Число!")

    action = args[2].lower() if len(args) > 2 else None
    if action not in ('approve', 'reject'):
        return await m.answer("❌ approve или reject!")

    city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
    if not city:
        return await m.answer("❌ Город не найден!")

    async with pool.acquire() as conn:
        report = await conn.fetchrow("SELECT * FROM mayor_reports WHERE chat_id=$1 AND city_id=$2 AND status IN ('pending','submitted') ORDER BY created_at DESC LIMIT 1", cid, city_id)
    if not report:
        return await m.answer(f"✅ В {city['emoji']} {city['name']} нет отчётов!")

    mayor_name = await safe_name(cid, report['mayor_id'])

    if action == 'approve':
        remaining = report['budget_allocated'] - report['budget_spent']
        if remaining > 0:
            await update_city_treasury(cid, city_id, remaining)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE mayors SET approval_rating = LEAST(100, approval_rating + 10) WHERE chat_id=$1 AND city_id=$2", cid, city_id)
            await conn.execute("UPDATE mayor_reports SET status='approved' WHERE id=$1", report['id'])
        msg = f"✅ <b>ОТЧЁТ ОДОБРЕН!</b>\n\n🏙️ {city['emoji']} {city['name']}\n👤 {mayor_name}\n💰 Возврат: {fmt_money(remaining)}\n📈 Рейтинг: +10%"
    else:
        if random.choice(['fine', 'jail']) == 'fine':
            fine_amount = int(report['budget_allocated'] * 0.5)
            await update_balance(cid, report['mayor_id'], -fine_amount)
            async with pool.acquire() as conn:
                await conn.execute("UPDATE mayors SET approval_rating = GREATEST(0, approval_rating - 15) WHERE chat_id=$1 AND city_id=$2", cid, city_id)
            msg = f"❌ <b>ОТЧЁТ ОТКЛОНЁН!</b>\n\n🏙️ {city['emoji']} {city['name']}\n👤 {mayor_name}\n💸 Штраф: {fmt_money(fine_amount)}\n📉 Рейтинг: -15%"
        else:
            await send_to_jail(cid, report['mayor_id'], 4)
            async with pool.acquire() as conn:
                await conn.execute("UPDATE mayors SET approval_rating = GREATEST(0, approval_rating - 25) WHERE chat_id=$1 AND city_id=$2", cid, city_id)
            msg = f"🔒 <b>МЭР В ТЮРЬМЕ!</b>\n\n🏙️ {city['emoji']} {city['name']}\n👤 {mayor_name} на 4 ч\n📉 Рейтинг: -25%"
        async with pool.acquire() as conn:
            await conn.execute("UPDATE mayor_reports SET status='rejected' WHERE id=$1", report['id'])

    await m.answer(msg, parse_mode="HTML")


# --- ЭКЗАМЕНЫ (ответы текстом) ---
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_exam_answer(m: Message):
    if m.chat.type not in ('group', 'supergroup', 'private'):
        return
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    ek = f"{cid}_{uid}"
    if ek not in exam_sessions:
        return

    ex = exam_sessions[ek]
    c = COURSES[ex['course']]
    try:
        ans = int(m.text.strip()) - 1
    except ValueError:
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
    if ex['question'] < len(c['questions']):
        q = c['questions'][ex['question']]
        answers_text = ' | '.join([f'{i+1}. {a}' for i, a in enumerate(q['a'])])
        await m.answer(f"Вопрос {ex['question']+1}:\n<b>{q['q']}</b>\n\n{answers_text}\n\nНапишите номер (1, 2, 3)", parse_mode="HTML")
    else:
        if ex['correct'] >= 2:
            await complete_course(cid, uid, ex['course'])
            await m.answer(f"🎉 <b>Сдано!</b> Курс <b>{c['name']}</b> завершён!\n\n💼 Теперь доступна профессия: /job {ex['course']}", parse_mode="HTML")
            new_achs = await check_achievements(cid, uid)
            await notify_achievements(cid, uid, new_achs)
        else:
            await m.answer(f"😔 <b>Провал.</b> {ex['correct']}/3\n/buy_course {ex['course']}", parse_mode="HTML")
        exam_sessions.pop(ek, None)


# --- НОВЫЕ УЧАСТНИКИ ---
@dp.message(F.new_chat_members)
async def on_user_join(m: Message):
    cid = m.chat.id
    for user in m.new_chat_members:
        if user.is_bot:
            if user.id == bot.id:
                await m.answer("👋 Привет! Я экономический бот группы.\n\n🎩 Напиши /start чтобы открыть меню!")
            continue
        await get_user(cid, user.id)
        await save_username(cid, user.id, user.full_name)


# --- АВТО-РЕГИСТРАЦИЯ (ЛОВИТ ВСЁ ОСТАЛЬНОЕ) ---
@dp.message()
async def auto_register(m: Message):
    if m.chat.type not in ('group', 'supergroup'):
        return
    if not m.from_user or m.from_user.is_bot:
        return
    await get_user(m.chat.id, m.from_user.id)
    await save_username(m.chat.id, m.from_user.id, m.from_user.full_name)


# --- ГЛАВНАЯ ФУНКЦИЯ ---
async def main():
    print("🤖 Запуск бота...")
    await init_db()
    await init_cities()
    await start_web_server()

    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.get_me()
    print(f"✅ Бот: @{me.username}")

    asyncio.create_task(polling_health_check())
    asyncio.create_task(auto_lottery_loop())
    asyncio.create_task(loan_interest_loop())
    asyncio.create_task(jail_fine_check_loop())
    asyncio.create_task(check_expired_debts_loop())
    asyncio.create_task(check_all_elections_and_terms())
    asyncio.create_task(federal_expenses_loop())
    asyncio.create_task(city_expenses_loop())
    asyncio.create_task(check_overdue_projects())

    print("🎰 Лотерея | 💳 Кредиты | ⚖️ Штрафы | 🕵️ Долги | 🏛️ Выборы | 💰 Бюджеты | ⏰ Проекты")
    print("🚀 Бот запущен и готов к работе!")

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Бот остановлен")
