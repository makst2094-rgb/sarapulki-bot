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
bj_tables = {}
ROULETTE_TABLES = {}
active_contraband_runs = {}
contraband_cooldowns = {}
heist_lobbies = {}

class BlackjackStates(StatesGroup):
    waiting = State()
    betting = State()
    playing = State()

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

# Расходы казны (в день)
FEDERAL_SALARY_PRESIDENT = 5000
FEDERAL_SALARY_PRIME = 3000
FEDERAL_SOCIAL_AID = 100
FEDERAL_INFRASTRUCTURE = 2000
CITY_SALARY_MAYOR = 2000
CITY_UTILITIES = 500
CITY_SOCIAL_PROGRAMS = 300
MIN_TREASURY_BALANCE = 10000

# Мафия
MAFIA_BALANCE_THRESHOLD = 30000
MAFIA_BANK_THRESHOLD = 50000
MAFIA_CHECK_INTERVAL = 86400
MAFIA_CHANCE = 0.15
MAFIA_RANSOM_RATE = 0.20
MAFIA_PENALTY_RATE = 0.30
MAFIA_DEADLINE_HOURS = 1

# Рулетка
ROULETTE_WAIT_TIME = 60
ROULETTE_MIN_PLAYERS = 2
ROULETTE_MAX_PLAYERS = 6
ROULETTE_BULLET_CHANCE = 1/6

# Блэкджек
BJ_MIN_BALANCE = 50
BJ_MAX_PLAYERS = 5
BJ_WAIT_TIME = 60
BJ_DEALER_STOP = 17

# Биржа
STOCK_MARKET_EVENTS = [
    {"name": "📈 Рост спроса", "effect": 1.3},
    {"name": "📉 Падение рынка", "effect": 0.7},
    {"name": "🔥 Вирусный тренд", "effect": 1.5},
    {"name": "🔥 Конкурент демпингует", "effect": 0.8},
    {"name": "💼 Инвестфонд вошёл", "effect": 1.4},
]

# Контрабанда
CONTRABAND_COOLDOWN = 21600
CONTRABAND_ITEMS = {
    "docs": {"name": "📄 Фальшивые документы", "price": 5000, "reward": 12000, "fail_chance": 30, "penalty_percent": 10, "jail_hours": 2, "duration": 180},
    "fake_money": {"name": "💵 Фейковые деньги", "price": 15000, "reward": 40000, "fail_chance": 50, "penalty_percent": 25, "jail_hours": 4, "duration": 300},
    "drugs": {"name": "💊 Запрещенные вещества", "price": 50000, "reward": 150000, "fail_chance": 70, "penalty_percent": 50, "jail_hours": 8, "duration": 480},
    "weapons": {"name": "🔫 Оружие", "price": 100000, "reward": 350000, "fail_chance": 85, "penalty_percent": 75, "jail_hours": 12, "duration": 720, "seize_business": True}
}
CONTRABAND_ROLES = {
    "driver": {"name": "🚛 Водитель", "desc": "Снижает шанс провала на 15%"},
    "navigator": {"name": "🗺️ Навигатор", "desc": "Ускоряет рейс на 20%"},
    "guard": {"name": "🛡️ Охранник", "desc": "Дает шанс отбиться при проверке"},
    "coordinator": {"name": "📡 Связной", "desc": "Увеличивает награду на 10%"}
}

# Ограбления банков
HEIST_COOLDOWN = 86400
BANKS = {
    "local": {"name": "🏦 Местный банк", "reward": 5000, "chance": 70, "jail": 4},
    "city": {"name": "🏛️ Городской банк", "reward": 20000, "chance": 50, "jail": 6},
    "central": {"name": "🏛️ Центральный банк", "reward": 100000, "chance": 30, "jail": 8},
    "swiss": {"name": "🇨🇭 Швейцарский банк", "reward": 500000, "chance": 15, "jail": 12}
}
TOOLS = {
    "lockpick": {"name": "🔑 Отмычка", "price": 15000, "bonus_chance": 15, "extra_attempts": 1, "wire_reduce": 0, "jail_reduce": 1},
    "crowbar": {"name": "🔧 Монтировка", "price": 35000, "bonus_chance": 25, "extra_attempts": 1, "wire_reduce": 0, "jail_reduce": 1},
    "c4": {"name": "💣 Взрывчатка C4", "price": 85000, "bonus_chance": 40, "extra_attempts": 2, "wire_reduce": 1, "jail_reduce": 2},
    "mask": {"name": "🎭 Маска", "price": 8000, "bonus_chance": 0, "extra_attempts": 0, "wire_reduce": 0, "jail_reduce": 2}
}
BASE_TOOL = {"name": "👊 Голыми руками", "bonus_chance": 0, "extra_attempts": 0, "wire_reduce": 0, "jail_reduce": 0}
HEIST_ROLES = {"hacker": "🔓 Взломщик", "coder": "💻 Хакер", "sapper": "💣 Сапёр"}

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

# ═══════════════════════════════════════════
# БАЗА ДАННЫХ
# ═══════════════════════════════════════════
async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10, command_timeout=30)
    async with pool.acquire() as conn:
        for table in ["stock_holdings", "stocks", "marketplace", "robbery", "mafia_threats", "auctions", "auction_bids", "heist_cooldowns", "credits"]:
            await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        
        tables = [
            "CREATE TABLE IF NOT EXISTS users (chat_id BIGINT, user_id BIGINT, balance INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS profiles (chat_id BIGINT, user_id BIGINT, job_key TEXT DEFAULT 'novice', level INTEGER DEFAULT 1, last_work_time REAL DEFAULT 0, coffee_level INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS inventory (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, item_name TEXT, item_type TEXT, rarity TEXT DEFAULT 'common')",
            "CREATE TABLE IF NOT EXISTS businesses (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, business_name TEXT, income INTEGER, last_collect_time REAL DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS garage (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, car_key TEXT, car_name TEXT)",
            "CREATE TABLE IF NOT EXISTS daily_bonus (chat_id BIGINT, user_id BIGINT, last_claim REAL DEFAULT 0, streak INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS robbery (chat_id BIGINT, user_id BIGINT, last_robbery REAL DEFAULT 0, debt_amount INTEGER DEFAULT 0, debt_time REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS lottery_tickets (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, buy_time REAL)",
            "CREATE TABLE IF NOT EXISTS usernames (chat_id BIGINT, user_id BIGINT, username TEXT, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS bank (chat_id BIGINT, user_id BIGINT, deposit INTEGER DEFAULT 0, last_interest_time REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS education (chat_id BIGINT, user_id BIGINT, completed_courses TEXT[] DEFAULT '{}', has_mba BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS loans (chat_id BIGINT, user_id BIGINT, amount INTEGER DEFAULT 0, interest INTEGER DEFAULT 0, taken_at REAL DEFAULT 0, due_date REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS jail (chat_id BIGINT, user_id BIGINT, release_time REAL DEFAULT 0, fine_per_hour INTEGER DEFAULT 50, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS jail_fines (chat_id BIGINT, user_id BIGINT, fine_amount INTEGER DEFAULT 0, debt_time REAL DEFAULT 0, paid BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS achievements (chat_id BIGINT, user_id BIGINT, achievement_id TEXT, unlocked_at REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id, achievement_id))",
            "CREATE TABLE IF NOT EXISTS debts (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, lender_id BIGINT NOT NULL, borrower_id BIGINT NOT NULL, amount BIGINT NOT NULL, fee BIGINT NOT NULL, created_at REAL NOT NULL, deadline REAL NOT NULL, status TEXT DEFAULT 'active', reminder_sent BOOLEAN DEFAULT FALSE)",
            "CREATE TABLE IF NOT EXISTS state_debts (chat_id BIGINT NOT NULL, user_id BIGINT NOT NULL, amount BIGINT NOT NULL DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS cities (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, bonus_desc TEXT NOT NULL, bonus_type TEXT NOT NULL, bonus_value INTEGER DEFAULT 10)",
            "CREATE TABLE IF NOT EXISTS player_cities (chat_id BIGINT NOT NULL, user_id BIGINT NOT NULL, city_id INTEGER NOT NULL, moved_at REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
            "CREATE TABLE IF NOT EXISTS city_treasury (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, amount BIGINT DEFAULT 0, PRIMARY KEY (chat_id, city_id))",
            "CREATE TABLE IF NOT EXISTS mayors (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, user_id BIGINT NOT NULL, elected_at REAL NOT NULL, expires_at REAL NOT NULL, approval_rating INTEGER DEFAULT 50, PRIMARY KEY (chat_id, city_id))",
            "CREATE TABLE IF NOT EXISTS mayor_candidates (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, user_id BIGINT NOT NULL, votes BIGINT DEFAULT 0, election_id TEXT NOT NULL, status TEXT DEFAULT 'active', UNIQUE(chat_id, city_id, user_id, election_id))",
            "CREATE TABLE IF NOT EXISTS mayor_votes (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, voter_id BIGINT NOT NULL, candidate_id BIGINT NOT NULL, election_id TEXT NOT NULL, PRIMARY KEY (chat_id, city_id, voter_id, election_id))",
            "CREATE TABLE IF NOT EXISTS city_decrees (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, mayor_id BIGINT NOT NULL, decree_type TEXT NOT NULL, active_until REAL NOT NULL)",
            "CREATE TABLE IF NOT EXISTS state_treasury (chat_id BIGINT PRIMARY KEY, amount BIGINT DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS federal_roles (chat_id BIGINT NOT NULL, role TEXT NOT NULL, user_id BIGINT NOT NULL, elected_at REAL NOT NULL, expires_at REAL NOT NULL, approval_rating INTEGER DEFAULT 50, PRIMARY KEY (chat_id, role))",
            "CREATE TABLE IF NOT EXISTS federal_candidates (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, role TEXT NOT NULL, user_id BIGINT NOT NULL, votes BIGINT DEFAULT 0, election_id TEXT NOT NULL, UNIQUE (chat_id, role, user_id, election_id))",
            "CREATE TABLE IF NOT EXISTS federal_votes (chat_id BIGINT NOT NULL, role TEXT NOT NULL, voter_id BIGINT NOT NULL, candidate_id BIGINT NOT NULL, election_id TEXT NOT NULL, PRIMARY KEY (chat_id, role, voter_id, election_id))",
            "CREATE TABLE IF NOT EXISTS federal_elections_start (chat_id BIGINT NOT NULL, role TEXT NOT NULL, election_id TEXT NOT NULL, started_at REAL NOT NULL, PRIMARY KEY (chat_id, role, election_id))",
            "CREATE TABLE IF NOT EXISTS mayor_elections_start (chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, election_id TEXT NOT NULL, started_at REAL NOT NULL, PRIMARY KEY (chat_id, city_id, election_id))",
            "CREATE TABLE IF NOT EXISTS federal_decrees (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, role TEXT NOT NULL, decree_type TEXT NOT NULL, active_until REAL NOT NULL, UNIQUE (chat_id, role, decree_type))",
            "CREATE TABLE IF NOT EXISTS mayor_reports (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, mayor_id BIGINT NOT NULL, budget_allocated BIGINT DEFAULT 0, budget_spent BIGINT DEFAULT 0, report_deadline REAL NOT NULL, status TEXT DEFAULT 'pending', created_at REAL NOT NULL)",
            "CREATE TABLE IF NOT EXISTS impeachment_votes (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, role TEXT NOT NULL, voter_id BIGINT NOT NULL, voted_at REAL NOT NULL, UNIQUE(chat_id, role, voter_id))",
            "CREATE TABLE IF NOT EXISTS mayor_projects (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, city_id INTEGER NOT NULL, mayor_id BIGINT NOT NULL, project_type TEXT NOT NULL, budget BIGINT NOT NULL, description TEXT DEFAULT '', status TEXT DEFAULT 'active', started_at REAL NOT NULL, deadline REAL NOT NULL, completed_at REAL, fail_count INTEGER DEFAULT 0, reviewed_by BIGINT, review_result TEXT)",
            "CREATE TABLE IF NOT EXISTS mafia_threats (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, threat_time REAL DEFAULT 0, deadline REAL DEFAULT 0, ransom_amount INTEGER DEFAULT 0, threat_type TEXT DEFAULT 'asset', target_asset TEXT DEFAULT '', paid BOOLEAN DEFAULT FALSE)",
            "CREATE TABLE IF NOT EXISTS marketplace (id SERIAL PRIMARY KEY, chat_id BIGINT, seller_id BIGINT, item_type TEXT, item_name TEXT, item_key TEXT, price INTEGER, created_at REAL DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS stocks (id SERIAL PRIMARY KEY, chat_id BIGINT, business_id INTEGER, owner_id BIGINT, shares_issued INTEGER DEFAULT 10, shares_available INTEGER DEFAULT 10, price_per_share INTEGER DEFAULT 100, dividend_per_share INTEGER DEFAULT 10, last_price_change REAL DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS stock_holdings (id SERIAL PRIMARY KEY, stock_id INTEGER, user_id BIGINT, shares_owned INTEGER DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS auctions (id SERIAL PRIMARY KEY, chat_id BIGINT, item_type TEXT, item_key TEXT, item_name TEXT, starting_price INTEGER, current_bid INTEGER DEFAULT 0, current_bidder_id BIGINT, start_time REAL DEFAULT 0, end_time REAL DEFAULT 0, status TEXT DEFAULT 'active', min_increment INTEGER DEFAULT 100)",
            "CREATE TABLE IF NOT EXISTS auction_bids (id SERIAL PRIMARY KEY, auction_id INTEGER, user_id BIGINT, bid_amount INTEGER, bid_time REAL DEFAULT 0)",
            "CREATE TABLE IF NOT EXISTS heist_cooldowns (chat_id BIGINT, user_id BIGINT, last_heist_time REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))",
        ]
        for t in tables:
            await conn.execute(t)
        try:
            await conn.execute("ALTER TABLE profiles ADD COLUMN coffee_level INTEGER DEFAULT 0")
        except: pass
        print("✅ База данных готова")

# ═══════════════════════════════════════════
# БАЗОВЫЕ ФУНКЦИИ БД
# ═══════════════════════════════════════════
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
    to_delete = [cid for cid, case in active_cases.items() if now - int(cid.split("_")[-1]) > 600]
    for case_id in to_delete:
        parts = case_id.split("_")
        await send_to_jail(int(parts[0]), int(parts[1]), JAIL_TIME_HOURS)
        del active_cases[case_id]

async def auto_cleanup_timer(case_id):
    await asyncio.sleep(600)
    if case_id in active_cases:
        await cleanup_old_cases()

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
            car_names = [CARS.get(c['car_key'], {}).get('name', c['car_key']) for c in cars]
            total_value += sum(CARS.get(c['car_key'], {}).get('price', 0) for c in cars)
            arrested.append(f"🚗 Машины: {', '.join(car_names)}")
            await conn.execute("DELETE FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
    async with pool.acquire() as conn:
        businesses = await conn.fetch("SELECT business_name, income FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
        if businesses:
            biz_names = [b['business_name'] for b in businesses]
            for biz in businesses:
                biz_price = next((v['price'] for v in MARKET.values() if v['type'] == 'business' and v['income'] == biz['income']), biz['income'] * 6)
                total_value += biz_price
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

# ═══════════════════════════════════════════
# ДОСТИЖЕНИЯ
# ═══════════════════════════════════════════
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
        except: pass

# ═══════════════════════════════════════════
# ВЕБ-СЕРВЕР И ФОНОВЫЕ ЗАДАЧИ
# ═══════════════════════════════════════════
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
                    try:
                        await bot.send_message(cid, f"🎉 <b>АВТО-РОЗЫГРЫШ!</b>\n\n🏆 {wname}\n💰 {fmt_money(bank)}", parse_mode="HTML")
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
                        async with pool.acquire() as conn2:
                            await conn2.execute("UPDATE users SET balance=$1 WHERE chat_id=$2 AND user_id=$3", user['balance'] - remaining_debt, cid, uid)
                    await clear_loan(cid, uid)
                    msg = f"🚔 <b>АРЕСТ ИМУЩЕСТВА!</b>\n\n💰 Долг: <b>{fmt_money(total_debt)}</b>\n📦 Конфисковано: <b>{fmt_money(confiscated_value)}</b>\n\n"
                    msg += "<b>Конфисковано:</b>\n" + "\n".join([f"• {item}" for item in arrested])
                    if remaining_debt > 0:
                        msg += f"\n\n⛔ Остаток: <b>{fmt_money(remaining_debt)}</b>"
                    try:
                        await bot.send_message(cid, msg, parse_mode="HTML")
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
                if await is_in_jail(cid, uid): continue
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
            car_price = next((data['price'] for data in CARS.values() if data['name'] in car['car_name'] or car['car_name'] in data['name']), 0)
            if car_price > 0:
                await conn.execute("DELETE FROM garage WHERE id=$1", car['id'])
                collected += car_price
                seized_items.append(f"🚗 {car['car_name']} ({fmt_money(car_price)})")
        if collected < total_debt:
            businesses = await conn.fetch("SELECT id, business_name FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, borrower_id)
            for biz in businesses:
                if collected >= total_debt: break
                biz_price = next((data['price'] for data in MARKET.values() if data['name'] in biz['business_name'] or biz['business_name'] in data['name']), 50000)
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

# ═══════════════════════════════════════════
# РАСХОДЫ КАЗНЫ
# ═══════════════════════════════════════════
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
                    if treasury < MIN_TREASURY_BALANCE: continue
                    president = await get_federal_role(cid, 'president')
                    prime = await get_federal_role(cid, 'prime_minister')
                    total_expenses = 0
                    if president:
                        await update_balance(cid, president['user_id'], FEDERAL_SALARY_PRESIDENT)
                        total_expenses += FEDERAL_SALARY_PRESIDENT
                    if prime:
                        await update_balance(cid, prime['user_id'], FEDERAL_SALARY_PRIME)
                        total_expenses += FEDERAL_SALARY_PRIME
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
                    if treasury < MIN_TREASURY_BALANCE: continue
                    city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
                    if not city: continue
                    total_expenses = 0
                    mayor = await get_mayor(cid, city_id)
                    if mayor:
                        await update_balance(cid, mayor['user_id'], CITY_SALARY_MAYOR)
                        total_expenses += CITY_SALARY_MAYOR
                    if treasury >= CITY_UTILITIES:
                        total_expenses += CITY_UTILITIES
                    residents = await conn.fetch("SELECT u.user_id, u.balance FROM users u JOIN player_cities pc ON u.chat_id = pc.chat_id AND u.user_id = pc.user_id WHERE pc.chat_id=$1 AND pc.city_id=$2 AND u.balance < 0", cid, city_id)
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

# ═══════════════════════════════════════════
# ФУНКЦИИ ГОРОДОВ И ПОЛИТИКИ
# ═══════════════════════════════════════════
async def init_cities():
    try:
        async with pool.acquire() as conn:
            for city in CITIES_LIST:
                await conn.execute("INSERT INTO cities (id, name, bonus_desc, bonus_type, bonus_value) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (id) DO NOTHING", city['id'], city['name'], city['desc'], city['bonus_type'], city['bonus_value'])
            print(f"🏙️ Инициализировано {len(CITIES_LIST)} городов")
    except Exception as e:
        print(f"❌ Ошибка инициализации городов: {e}")

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
        if existing: return False, "❌ Уже выдвинут!"
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
    if user['balance'] < cost:
        return False, f"❌ Голос стоит {fmt_money(cost)}"
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

async def is_federal_official(cid, uid, role):
    official = await get_federal_role(cid, role)
    if official and official['user_id'] == uid: return True
    return False

async def get_active_decree(cid, city_id, decree_type):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM city_decrees WHERE chat_id=$1 AND city_id=$2 AND decree_type=$3 AND active_until > $4", cid, city_id, decree_type, time.time())
            return row
    except Exception: return None

async def get_active_federal_decree(cid, role, decree_type):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM federal_decrees WHERE chat_id=$1 AND role=$2 AND decree_type=$3 AND active_until > $4", cid, role, decree_type, time.time())
            return row
    except Exception: return None

async def apply_income_tax(cid, uid, gross_income):
    tax_cut = await get_active_federal_decree(cid, 'president', 'tax_cut')
    tax_boost_president = await get_active_federal_decree(cid, 'president', 'tax_boost')
    tax_boost_prime = await get_active_federal_decree(cid, 'prime_minister', 'tax_boost')
    if tax_cut: tax_rate = 5
    elif tax_boost_president or tax_boost_prime: tax_rate = 15
    else: tax_rate = TAX_RATE_PERCENT
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
    if tax_cut: tax_rate = 8
    elif tax_boost_president or tax_boost_prime: tax_rate = 18
    else: tax_rate = 12
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
    names = {'work_bonus': '🏭 Рабочая смена (+20% к работе)', 'tool_discount': '🔧 Заводской бонус (-30% на инструменты)', 'business_bonus': '📈 Бизнес-стимул (+15% к бизнесам)', 'car_discount': '🚗 Авто-скидка (-25% на машины)', 'city_event': '🎉 День города (бонус всем жителям)'}
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
        await conn.execute("""INSERT INTO federal_decrees (chat_id, role, decree_type, active_until) VALUES ($1,$2,$3,$4) ON CONFLICT (chat_id, role, decree_type) DO UPDATE SET active_until = $4""", cid, role, decree_type, active_until)
    role_name = "Президент" if role == 'president' else "Премьер-министр"
    return True, f"✅ Указ {role_name} издан!\n⏰ {duration} часов."

def get_federal_decree_name(decree_type):
    names = {'amnesty': '🕊️ Амнистия', 'tax_cut': '📉 Снижение налога до 5%', 'tax_boost': '📈 Повышение до 15%', 'emergency': '🚨 ЧП', 'subsidy': '💰 Субсидии (+10%)', 'investment': '🏗️ Инвестиции (+5000)'}
    return names.get(decree_type, 'Неизвестный указ')

# ═══════════════════════════════════════════
# ПРОЕКТЫ МЭРА
# ═══════════════════════════════════════════
@dp.message(Command("mayor_project"))
async def cmd_mayor_project(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    mayor = await get_mayor(cid, player_city['id'])
    if not mayor or mayor['user_id'] != uid: return await m.answer("❌ Только мэр!")
    args = m.text.split(maxsplit=1)
    if len(args) < 2:
        proj_list = "\n".join([f"• /mayor_project {k} — {v['name']} ({fmt_money(v['cost'])})" for k, v in PROJECT_TYPES.items()])
        return await m.answer(f"🏗️ <b>ПРОЕКТЫ МЭРА</b>\n\nВыбери проект:\n{proj_list}\n\n⏰ Срок: 24 часа\n⚠️ 1-й провал = штраф 50%\n⚠️ 2-й провал = тюрьма + снятие", parse_mode="HTML")
    project_key = args[1].lower().strip()
    if project_key not in PROJECT_TYPES: return await m.answer("❌ Неизвестный проект!")
    project = PROJECT_TYPES[project_key]
    cost = project['cost']
    treasury = await get_city_treasury(cid, player_city['id'])
    if treasury < cost: return await m.answer(f"❌ В казне только {fmt_money(treasury)}! Нужно {fmt_money(cost)}")
    async with pool.acquire() as conn:
        active = await conn.fetchrow("SELECT * FROM mayor_projects WHERE chat_id=$1 AND city_id=$2 AND mayor_id=$3 AND status='active'", cid, player_city['id'], uid)
        if active: return await m.answer("⚠️ У тебя уже есть активный проект!")
    await update_city_treasury(cid, player_city['id'], -cost)
    deadline = time.time() + 86400
    async with pool.acquire() as conn:
        await conn.execute("""INSERT INTO mayor_projects (chat_id, city_id, mayor_id, project_type, budget, description, started_at, deadline) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""", cid, player_city['id'], uid, project_key, cost, project['desc'], time.time(), deadline)
    await m.answer(f"🏗️ <b>ПРОЕКТ ЗАПУЩЕН!</b>\n\n🏙️ {player_city['emoji']} {player_city['name']}\n📋 {project['name']} — {project['desc']}\n💰 Бюджет: {fmt_money(cost)}\n⏰ Срок: 24 часа\n\nИспользуй <b>/project_done</b> чтобы завершить", parse_mode="HTML")

@dp.message(Command("project_done"))
async def cmd_project_done(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    async with pool.acquire() as conn:
        project = await conn.fetchrow("""SELECT * FROM mayor_projects WHERE chat_id=$1 AND city_id=$2 AND mayor_id=$3 AND status='active' ORDER BY started_at DESC LIMIT 1""", cid, player_city['id'], uid)
        if not project: return await m.answer("❌ Нет активного проекта!")
        if time.time() > project['deadline']: return await m.answer("⏰ Срок уже истёк! Жди проверки Президента.")
        await conn.execute("UPDATE mayor_projects SET status='completed', completed_at=$1 WHERE id=$2", time.time(), project['id'])
    await m.answer(f"✅ <b>ПРОЕКТ ЗАВЕРШЁН!</b>\n\n📋 {PROJECT_TYPES[project['project_type']]['name']}\n⏳ Ожидает проверки Президентом", parse_mode="HTML")

@dp.message(Command("project_check"))
async def cmd_project_check(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    president = await get_federal_role(cid, 'president')
    if not president or president['user_id'] != uid: return await m.answer("❌ Только Президент!")
    args = m.text.split()
    if len(args) < 2: return await m.answer("⚖️ <b>ПРОВЕРКА ПРОЕКТА</b>\n\n/project_check [город_id] [approve/reject]", parse_mode="HTML")
    try: city_id = int(args[1])
    except ValueError: return await m.answer("❌ ID города должен быть числом!")
    action = args[2].lower() if len(args) > 2 else None
    if action not in ['approve', 'reject']: return await m.answer("❌ Используй approve или reject!")
    city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
    if not city: return await m.answer("❌ Город не найден!")
    async with pool.acquire() as conn:
        project = await conn.fetchrow("""SELECT * FROM mayor_projects WHERE chat_id=$1 AND city_id=$2 AND status IN ('active','completed') ORDER BY started_at DESC LIMIT 1""", cid, city_id)
        if not project: return await m.answer(f"✅ В {city['emoji']} {city['name']} нет проектов!")
        mayor_name = ""
        try: mayor_name = (await bot.get_chat_member(cid, project['mayor_id'])).user.full_name
        except: mayor_name = f"User{project['mayor_id']}"
        project_info = PROJECT_TYPES.get(project['project_type'], {"name": "Неизвестно"})
        if action == 'approve':
            bonus = int(project['budget'] * 0.30)
            await update_city_treasury(cid, city_id, bonus)
            await conn.execute("""UPDATE mayors SET approval_rating = LEAST(100, approval_rating + 15) WHERE chat_id=$1 AND city_id=$2""", cid, city_id)
            await conn.execute("UPDATE mayor_projects SET status='approved', reviewed_by=$1, review_result='Одобрено' WHERE id=$2", uid, project['id'])
            msg = f"✅ <b>ПРОЕКТ ОДОБРЕН!</b>\n\n🏙️ {city['emoji']} {city['name']}\n📋 {project_info['name']}\n👤 Мэр: {mayor_name}\n💰 Возврат в казну: {fmt_money(bonus)}\n📈 Рейтинг мэра: +15%"
            await bot.send_message(cid, msg, parse_mode="HTML")
            await m.answer("✅ Проект одобрен!")
        elif action == 'reject':
            fail_count = project['fail_count'] + 1
            if fail_count >= 2:
                await send_to_jail(cid, project['mayor_id'], 6)
                await conn.execute("DELETE FROM mayors WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                await conn.execute("UPDATE mayor_projects SET status='failed', fail_count=$1, reviewed_by=$2, review_result='Снят' WHERE id=$3", fail_count, uid, project['id'])
                msg = f"🔒 <b>МЭР СНЯТ С ДОЛЖНОСТИ!</b>\n\n🏙️ {city['emoji']} {city['name']}\n📋 {project_info['name']}\n👤 {mayor_name}\n⚠️ 2-й провал проекта!\n🔒 Тюрьма: 6 часов\n📉 Должность: ВАКАНТНО"
            else:
                fine = int(project['budget'] * 0.50)
                await update_balance(cid, project['mayor_id'], -fine)
                await conn.execute("""UPDATE mayors SET approval_rating = GREATEST(0, approval_rating - 20) WHERE chat_id=$1 AND city_id=$2""", cid, city_id)
                await conn.execute("UPDATE mayor_projects SET status='failed', fail_count=$1, reviewed_by=$2, review_result='Штраф' WHERE id=$3", fail_count, uid, project['id'])
                msg = f"❌ <b>ПРОЕКТ ОТКЛОНЁН!</b>\n\n🏙️ {city['emoji']} {city['name']}\n📋 {project_info['name']}\n👤 Мэр: {mayor_name}\n💸 Штраф: {fmt_money(fine)} (50% бюджета)\n📉 Рейтинг: -20%\n⚠️ Провалов: {fail_count}/2\n🔜 Следующий провал = тюрьма + снятие!"
            await bot.send_message(cid, msg, parse_mode="HTML")
            await m.answer("✅ Решение применено!")

@dp.message(Command("project_status"))
async def cmd_project_status(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        player_city = await get_player_city(cid, uid)
        if not player_city: return await m.answer("❌ Нет города!")
        city_id = player_city['id']
        city_name = player_city['name']
        city_emoji = player_city['emoji']
    else:
        try: city_id = int(args[1])
        except ValueError: return await m.answer("❌ ID города должен быть числом!")
        city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
        if not city: return await m.answer("❌ Город не найден!")
        city_name = city['name']
        city_emoji = city['emoji']
    async with pool.acquire() as conn:
        projects = await conn.fetch("""SELECT * FROM mayor_projects WHERE chat_id=$1 AND city_id=$2 ORDER BY started_at DESC LIMIT 5""", cid, city_id)
    if not projects: return await m.answer(f"🏙️ {city_emoji} {city_name}\n\n📋 Нет проектов")
    t = f"🏙️ <b>{city_emoji} {city_name}</b>\n\n📋 <b>Проекты:</b>\n\n"
    for p in projects:
        proj_info = PROJECT_TYPES.get(p['project_type'], {"name": "Неизвестно"})
        status_emoji = {'active': '🔄', 'completed': '✅', 'approved': '🏆', 'failed': '❌'}.get(p['status'], '❓')
        time_left = int(p['deadline'] - time.time())
        if time_left > 0 and p['status'] == 'active': time_text = f"⏰ {time_left//3600}ч {(time_left%3600)//60}мин"
        elif p['status'] == 'active': time_text = "⚠️ ПРОСРОЧЕНО"
        else: time_text = ""
        t += f"{status_emoji} <b>{proj_info['name']}</b>\n   💰 {fmt_money(p['budget'])} {time_text}\n   📊 Статус: {p['status']}\n\n"
    await m.answer(t, parse_mode="HTML")

async def check_overdue_projects():
    print("⏰ Цикл проверки проектов мэров запущен")
    while True:
        await asyncio.sleep(1800)
        try:
            async with pool.acquire() as conn:
                overdue = await conn.fetch("""SELECT * FROM mayor_projects WHERE status='active' AND deadline < $1""", time.time())
                for proj in overdue:
                    cid = proj['chat_id']
                    city_id = proj['city_id']
                    mayor_id = proj['mayor_id']
                    fail_count = proj['fail_count'] + 1
                    city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
                    city_name = city['name'] if city else f"город #{city_id}"
                    try: mayor_name = (await bot.get_chat_member(cid, mayor_id)).user.full_name
                    except: mayor_name = f"User{mayor_id}"
                    if fail_count >= 2:
                        await send_to_jail(cid, mayor_id, 6)
                        await conn.execute("DELETE FROM mayors WHERE chat_id=$1 AND city_id=$2", cid, city_id)
                        await conn.execute("UPDATE mayor_projects SET status='failed', fail_count=$1, review_result='Авто-снятие' WHERE id=$2", fail_count, proj['id'])
                        msg = f"🚨 <b>МЭР АВТОМАТИЧЕСКИ СНЯТ!</b>\n\n🏙️ {city_name}\n👤 {mayor_name}\n⚠️ 2-й провал (просрочка)\n🔒 Тюрьма: 6 часов\n📉 Должность: ВАКАНТНО"
                    else:
                        fine = int(proj['budget'] * 0.50)
                        await update_balance(cid, mayor_id, -fine)
                        await conn.execute("""UPDATE mayors SET approval_rating = GREATEST(0, approval_rating - 20) WHERE chat_id=$1 AND city_id=$2""", cid, city_id)
                        await conn.execute("UPDATE mayor_projects SET status='failed', fail_count=$1, review_result='Авто-штраф' WHERE id=$2", fail_count, proj['id'])
                        msg = f"⏰ <b>ПРОЕКТ ПРОСРОЧЕН!</b>\n\n🏙️ {city_name}\n👤 Мэр: {mayor_name}\n💸 Авто-штраф: {fmt_money(fine)}\n📉 Рейтинг: -20%\n⚠️ Провалов: {fail_count}/2"
                    try: await bot.send_message(cid, msg, parse_mode="HTML")
                    except: pass
        except Exception as e:
            print(f"Ошибка проверки проектов: {e}")

# ═══════════════════════════════════════════
# ПРОВЕРКА ВЫБОРОВ И СРОКОВ
# ═══════════════════════════════════════════
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

# ═══════════════════════════════════════════
# МАФИЯ
# ═══════════════════════════════════════════
async def mafia_threat_loop():
    print("🕴️ Цикл мафии запущен")
    while True:
        await asyncio.sleep(MAFIA_CHECK_INTERVAL)
        async with pool.acquire() as conn:
            users = await conn.fetch("SELECT u.chat_id, u.user_id, u.balance, COALESCE(b.deposit, 0) as deposit FROM users u LEFT JOIN bank b ON u.chat_id=b.chat_id AND u.user_id=b.user_id WHERE u.balance > $1 OR COALESCE(b.deposit, 0) > $2", MAFIA_BALANCE_THRESHOLD, MAFIA_BANK_THRESHOLD)
            for user in users:
                cid, uid = user['chat_id'], user['user_id']
                balance = user['balance'] or 0
                deposit = user['deposit'] or 0
                total_wealth = balance + deposit
                active_threat = await conn.fetchval("SELECT COUNT(*) FROM mafia_threats WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE AND deadline > $3", cid, uid, time.time())
                if active_threat > 0: continue
                if random.random() > MAFIA_CHANCE: continue
                ransom = int(total_wealth * MAFIA_RANSOM_RATE)
                deadline = time.time() + (MAFIA_DEADLINE_HOURS * 3600)
                businesses = await conn.fetch("SELECT business_name, income FROM businesses WHERE chat_id=$1 AND user_id=$2 ORDER BY income DESC", cid, uid)
                cars = await conn.fetch("SELECT car_key, car_name FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
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
                await conn.execute("INSERT INTO mafia_threats (chat_id, user_id, threat_time, deadline, ransom_amount, threat_type, target_asset) VALUES ($1,$2,$3,$4,$5,$6,$7)", cid, uid, time.time(), deadline, ransom, threat_type, target)
                username = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, uid) or f"User{uid}"
                msg = f"🕴️ <b>К ВАМ ПРИШЛА МАФИЯ!</b>\n\n👤 {username}, мы знаем о ваших доходах...\n\n💰 <b>Ваш капитал:</b> {fmt_money(total_wealth)}\n  • 💵 Основной: {fmt_money(balance)}\n  • 🏦 Банк: {fmt_money(deposit)}\n\n⚠️ <b>ТРЕБОВАНИЕ:</b>\nПереведите нам <b>{fmt_money(ransom)}</b> в течение <b>{MAFIA_DEADLINE_HOURS} часа</b>\n\n🔫 <b>ИНАЧЕ МЫ ЗАБЕРЁМ:</b>\n{target_desc}\n\n💳 Для оплаты напишите: <b>/pay_mafia</b>\n\n⏳ Время пошло..."
                try: await bot.send_message(cid, msg, parse_mode="HTML")
                except: pass

async def execute_mafia_threats():
    async with pool.acquire() as conn:
        expired = await conn.fetch("SELECT * FROM mafia_threats WHERE paid=FALSE AND deadline < $1", time.time())
        for threat in expired:
            cid, uid = threat['chat_id'], threat['user_id']
            threat_type = threat['threat_type']
            target = threat['target_asset']
            username = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, uid) or f"User{uid}"
            roll = random.random()
            if roll < 0.20:
                msg = f"🕊️ <b>МАФИЯ УШЛА НИ С ЧЕМ!</b>\n\n👤 {username}, вы проигнорировали требование, но мафия решила не трогать вас.\n\n🍀 Вам повезло! Но в следующий раз лучше платить вовремя."
            elif roll < 0.60:
                if threat_type == 'asset':
                    businesses = await conn.fetch("SELECT business_name FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
                    cars = await conn.fetch("SELECT car_name FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
                    if target in [b['business_name'] for b in businesses]:
                        await conn.execute("DELETE FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name=$3", cid, uid, target)
                        msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ВАШ БИЗНЕС!</b>\n\n👤 {username}, вы проигнорировали требование.\n🏢 Конфискован: <b>{target}</b>"
                    elif target in [c['car_name'] for c in cars]:
                        await conn.execute("DELETE FROM garage WHERE chat_id=$1 AND user_id=$2 AND car_name=$3", cid, uid, target)
                        msg = f"🔫 <b>МАФИЯ УКРАЛА ВАШУ МАШИНУ!</b>\n\n👤 {username}, вы проигнорировали требование.\n🚗 Украдена: <b>{target}</b>"
                    else:
                        user = await get_user(cid, uid)
                        bank = await get_bank(cid, uid)
                        penalty = int((user['balance'] + bank['deposit']) * MAFIA_PENALTY_RATE)
                        paid_from_balance = min(penalty, user['balance'])
                        remaining = penalty - paid_from_balance
                        if paid_from_balance > 0: await update_balance(cid, uid, -paid_from_balance)
                        if remaining > 0 and bank['deposit'] > 0: await update_bank(cid, uid, -min(remaining, bank['deposit']))
                        msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ДЕНЬГИ!</b>\n\n👤 {username}, вы проигнорировали требование.\n💸 Списано: <b>{fmt_money(penalty)}</b>"
                else:
                    user = await get_user(cid, uid)
                    bank = await get_bank(cid, uid)
                    penalty = int((user['balance'] + bank['deposit']) * MAFIA_PENALTY_RATE)
                    paid_from_balance = min(penalty, user['balance'])
                    remaining = penalty - paid_from_balance
                    if paid_from_balance > 0: await update_balance(cid, uid, -paid_from_balance)
                    if remaining > 0 and bank['deposit'] > 0: await update_bank(cid, uid, -min(remaining, bank['deposit']))
                    msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ДЕНЬГИ!</b>\n\n👤 {username}, вы проигнорировали требование.\n💸 Списано: <b>{fmt_money(penalty)}</b>"
            else:
                user = await get_user(cid, uid)
                bank = await get_bank(cid, uid)
                penalty = int((user['balance'] + bank['deposit']) * MAFIA_PENALTY_RATE)
                paid_from_balance = min(penalty, user['balance'])
                remaining = penalty - paid_from_balance
                if paid_from_balance > 0: await update_balance(cid, uid, -paid_from_balance)
                if remaining > 0 and bank['deposit'] > 0: await update_bank(cid, uid, -min(remaining, bank['deposit']))
                msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ДЕНЬГИ!</b>\n\n👤 {username}, вы проигнорировали требование.\n💸 Списано: <b>{fmt_money(penalty)}</b> (30% от капитала)"
            await conn.execute("UPDATE mafia_threats SET paid=TRUE WHERE id=$1", threat['id'])
            try: await bot.send_message(cid, msg, parse_mode="HTML")
            except: pass

async def mafia_check_loop():
    print("⏰ Цикл проверки мафии запущен")
    while True:
        await asyncio.sleep(300)
        await execute_mafia_threats()

# ═══════════════════════════════════════════
# БИРЖА АКЦИЙ
# ═══════════════════════════════════════════
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
                await conn.execute("UPDATE stocks SET price_per_share=$1, last_price_change=$2 WHERE id=$3", new_price, stock['price_per_share'], stock['id'])

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
                        if uid not in user_dividends: user_dividends[uid] = {'cid': cid, 'total': 0}
                        user_dividends[uid]['total'] += amount
                    except Exception as e: logging.error(f"dividend calc error: {e}")
                for uid, data in user_dividends.items():
                    if data['total'] > 0:
                        try:
                            await update_balance(data['cid'], uid, data['total'])
                            await bot.send_message(data['cid'], f"💵 <b>Дивиденды получены!</b>\n\n+{fmt_money(data['total'])}", parse_mode="HTML")
                        except Exception as e: logging.error(f"dividend send error: {e}")
        except Exception as e: logging.error(f"stock_dividend_loop error: {e}")

# ═══════════════════════════════════════════
# АУКЦИОН
# ═══════════════════════════════════════════
async def auction_check_loop():
    print("🏆 Цикл проверки аукционов запущен")
    while True:
        await asyncio.sleep(60)
        async with pool.acquire() as conn:
            ended = await conn.fetch("SELECT * FROM auctions WHERE status='active' AND end_time < $1", time.time())
            for auction in ended:
                await conn.execute("UPDATE auctions SET status='ended' WHERE id=$1", auction['id'])
                await complete_auction(auction)

async def complete_auction(auction):
    cid = auction['chat_id']
    if not auction['current_bidder_id']:
        try: await bot.send_message(cid, f"⚠️ Аукцион <b>{auction['item_name']}</b> завершён без ставок.", parse_mode="HTML")
        except: pass
        return
    winner_uid = auction['current_bidder_id']
    winner_name = "Unknown"
    async with pool.acquire() as conn:
        winner_name = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, winner_uid) or f"User{winner_uid}"
        if auction['item_type'] == 'car':
            await conn.execute("INSERT INTO garage (chat_id, user_id, car_key, car_name) VALUES ($1,$2,$3,$4)", cid, winner_uid, auction['item_key'], auction['item_name'])
        elif auction['item_type'] == 'business':
            income = 0
            for k, v in MARKET.items():
                if v.get('name') == auction['item_name']:
                    income = v.get('income', 0)
                    break
            await conn.execute("INSERT INTO businesses (chat_id, user_id, business_name, income, last_collect_time) VALUES ($1,$2,$3,$4,$5)", cid, winner_uid, auction['item_name'], income, time.time())
        elif auction['item_type'] == 'item':
            rarity = 'legendary'
            await conn.execute("INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,'auction',$4)", cid, winner_uid, auction['item_name'], rarity)
    try:
        await bot.send_message(cid, f"🏆 <b>АУКЦИОН ЗАВЕРШЁН!</b>\n\n🎉 Победитель: <b>{winner_name}</b>\n📦 Лот: <b>{auction['item_name']}</b>\n💰 Цена: <b>{fmt_money(auction['current_bid'])}</b>", parse_mode="HTML")
    except: pass

# ═══════════════════════════════════════════
# МЕНЮ
# ═══════════════════════════════════════════
@dp.message(Command("start"))
async def cmd_start(m: Message):
    await save_username(m.chat.id, m.from_user.id, m.from_user.full_name)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Финансы", callback_data="menu_finance"), InlineKeyboardButton(text="💼 Работа", callback_data="menu_work")],
        [InlineKeyboardButton(text="🏪 Бизнес", callback_data="menu_business"), InlineKeyboardButton(text="🚗 Авто", callback_data="menu_cars")],
        [InlineKeyboardButton(text="🎓 Образование", callback_data="menu_edu"), InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games")],
        [InlineKeyboardButton(text="🏛️ Политика", callback_data="menu_politics"), InlineKeyboardButton(text="📊 Инфо", callback_data="menu_info")],
    ])
    await m.answer(f"🎩 <b>Добро пожаловать в мир Сарапулок!</b>\n\n👤 {m.from_user.full_name}\n\nВыберите раздел:", reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith("menu_"))
async def callback_menu(callback: CallbackQuery):
    uid = callback.from_user.id
    cid = callback.message.chat.id
    action = callback.data.replace("menu_", "")
    
    if action == "finance":
        u = await get_user(cid, uid)
        bd = await get_bank(cid, uid)
        text = f"💰 <b>ФИНАНСЫ</b>\n\n💵 Баланс: <b>{fmt_money(u['balance'])}</b>\n🏦 Банк: <b>{fmt_money(bd['deposit'])}</b>\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/balance\n/bank\n/deposit сумма\n/withdraw сумма\n/pay сумма\n/credit сумма\n/debt\n/repay сумма\n/repay_all\n/debt_give\n/debt_return\n/debt_list"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "work":
        p = await get_profile(cid, uid)
        j = JOBS[p['job_key']]
        text = f"💼 <b>РАБОТА</b>\n\n🔹 {j['name']} (Ур.{p['level']})\n💰 {fmt_money(j['base_pay'] * p['level'])}/ч\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/work\n/jobs\n/job ключ\n/shop\n/buy course\n/buy coffee"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "business":
        async with pool.acquire() as conn:
            bc = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
        text = f"🏪 <b>БИЗНЕС</b>\n\n🏢 У вас: <b>{bc}</b> бизнес(ов)\n⚠️ Лимит одного типа: <b>{MAX_BUSINESSES_PER_TYPE}</b>\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/market\n/buy_market ключ\n/collect\n/my_businesses\n/inv\n/craft\n/craft_item ключ\n/trade @user предмет кол-во"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "cars":
        c = await get_car(cid, uid)
        text = f"🚗 <b>АВТОСАЛОН</b>\n\n🅿️ {c or 'нет'}\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/cars\n/buycar ключ\n/mycar"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "edu":
        edu = await get_education(cid, uid)
        cc = len(edu['completed_courses']) + (1 if edu['has_mba'] else 0)
        text = f"🎓 <b>ОБРАЗОВАНИЕ</b>\n\n📚 Пройдено: <b>{cc}</b>\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/education\n/buy_course ключ\nКурсы: miner, coder, trader, lawyer, mba"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "games":
        text = f"🎮 <b>ИГРЫ</b>\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n🎲 /dice сумма — кости (шанс 50%)\n🃏 /blackjack — блэкджек\n🔫 /roulette ставка — рулетка\n🎟️ /buy_ticket — лотерея (50 сарапулок)\n🎁 /daily — ежедневный бонус\n🏦 /bank_heist — ограбление банка\n🚛 /contraband — контрабанда"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "politics":
        president = await get_federal_role(cid, 'president')
        president_text = "👤 ВАКАНТНО"
        if president:
            try: p_name = (await bot.get_chat_member(cid, president['user_id'])).user.full_name
            except: p_name = f"User{president['user_id']}"
            days_left = int((president['expires_at'] - time.time()) / 86400)
            president_text = f"👤 {p_name} ({days_left} дн.)"
        prime = await get_federal_role(cid, 'prime_minister')
        prime_text = "👤 ВАКАНТНО"
        if prime:
            try: pr_name = (await bot.get_chat_member(cid, prime['user_id'])).user.full_name
            except: pr_name = f"User{prime['user_id']}"
            days_left = int((prime['expires_at'] - time.time()) / 86400)
            prime_text = f"👤 {pr_name} ({days_left} дн.)"
        state_treasury = await get_state_treasury(cid)
        mayors_text = ""
        for city in CITIES_LIST:
            mayor = await get_mayor(cid, city['id'])
            city_treasury = await get_city_treasury(cid, city['id'])
            if mayor:
                try: m_name = (await bot.get_chat_member(cid, mayor['user_id'])).user.full_name
                except: m_name = f"User{mayor['user_id']}"
                days_left = int((mayor['expires_at'] - time.time()) / 86400)
                mayors_text += f"{city['emoji']} {city['name']}: {m_name} ({days_left} дн.) | Казна: {city_treasury}\n"
            else:
                mayors_text += f"{city['emoji']} {city['name']}: ВАКАНТНО | Казна: {city_treasury}\n"
        text = f"🏛️ <b>ПОЛИТИКА</b>\n\n🇷🇺 Президент: {president_text}\n💼 Премьер: {prime_text}\n🏛️ Фед. казна: {fmt_money(state_treasury)}\n\n🏙️ <b>Мэры:</b>\n{mayors_text}\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Города:</b>\n/city list\n/city choose [город]\n/city move [город]\n/city info\n/city residents\n\n🏛️ <b>Мэр:</b>\n/mayor_nominate (30к)\n/mayor_vote (500)\n/mayor_decree\n/mayor_report\n/mayor_finalize\n/city_decrees\n/mayor_project\n/project_done\n/project_check [город] approve/reject\n/project_status\n\n🇷🇺 <b>Президент (90 дней):</b>\n/president_nominate (50к)\n/president_vote (1000)\n/president_decree\n/president_decrees\n/president_finalize\n\n💼 <b>Премьер (90 дней):</b>\n/prime_nominate (40к)\n/prime_vote (800)\n/prime_decree\n/prime_decrees\n/prime_finalize\n\n⚖️ <b>Импичмент:</b>\n/impeach president\n/impeach prime\n\n💰 <b>Бюджет:</b>\n/budget"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "info":
        u = await get_user(cid, uid)
        p = await get_profile(cid, uid)
        in_jail = await is_in_jail(cid, uid)
        jail_text = "\n🔒 <b>В ТЮРЬМЕ!</b>" if in_jail else ""
        debt_text = f"\n⛔ ДОЛГ: {fmt_money(abs(u['balance']))}" if u['balance'] < 0 else ""
        text = f"📊 <b>КАРТОЧКА ИГРОКА</b>\n\n👤 {callback.from_user.full_name}\n💰 Баланс: {fmt_money(u['balance'])}\n💼 Профессия: {JOBS[p['job_key']]['name']} (Ур.{p['level']}){jail_text}{debt_text}\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/info\n/rating\n/achievements\n/budget"
        await callback.message.edit_text(text, parse_mode="HTML")
    
    await callback.answer()

# ═══════════════════════════════════════════
# БЮДЖЕТ
# ═══════════════════════════════════════════
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
        if mayor: city_daily += CITY_SALARY_MAYOR
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

# ═══════════════════════════════════════════
# ОСНОВНЫЕ КОМАНДЫ
# ═══════════════════════════════════════════
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
    if it['type'] == 'business':
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name=$3", cid, uid, it['name'])
            if count >= MAX_BUSINESSES_PER_TYPE:
                return await m.answer(f"❌ <b>ЛИМИТ ДОСТИГНУТ!</b>\n\nВы можете владеть максимум <b>{MAX_BUSINESSES_PER_TYPE}</b> бизнесами типа \"{it['name']}\".", parse_mode="HTML")
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
            count = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name=$3", cid, uid, it['name'])
        await m.answer(f"✅ <b>Куплен бизнес: {it['name']}</b>\n💰 {fmt_money(it['income'])}/сбор\n📊 У вас таких: <b>{count}/{MAX_BUSINESSES_PER_TYPE}</b>", parse_mode="HTML")
    else:
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,$4,$5)", cid, uid, it['name'], item_type, 'common')
        await m.answer(f"✅ <b>Куплено: {it['name']}</b>", parse_mode="HTML")
    new_achs = await check_achievements(cid, uid)
    await notify_achievements(cid, uid, new_achs)

@dp.message(Command("my_businesses"))
async def cmd_my_businesses(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    async with pool.acquire() as conn:
        businesses = await conn.fetch("SELECT business_name, COUNT(*) as count FROM businesses WHERE chat_id=$1 AND user_id=$2 GROUP BY business_name ORDER BY count DESC", cid, uid)
    if not businesses: return await m.answer("🏪 <b>У вас нет бизнесов</b>\n\nКупите в /market", parse_mode="HTML")
    t = "🏪 <b>ВАШИ БИЗНЕСЫ</b>\n\n"
    total = 0
    for biz in businesses:
        t += f"• {biz['business_name']}: <b>{biz['count']}</b> шт.\n"
        total += biz['count']
    t += f"\n📊 <b>Всего: {total} бизнес(ов)</b>"
    t += f"\n⚠️ Лимит одного типа: <b>{MAX_BUSINESSES_PER_TYPE}</b>"
    await m.answer(t, parse_mode="HTML")

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
    if uid not in ADMIN_IDS: return
    args = m.text.split()
    if len(args) < 3:
        cities_list = ", ".join([f"{c['emoji']} {c['name']} (ID: {c['id']})" for c in CITIES_LIST])
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
                    cities_list = ", ".join([f"{c['emoji']} {c['name']} (ID: {c['id']})" for c in CITIES_LIST])
                    return await m.answer(f"❌ Укажи город!\n\n/appoint mayor [user_id] [город_id]\n\nДоступные: {cities_list}")
                city_id = args[3]
                city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
                if not city:
                    cities_list = ", ".join([f"{c['emoji']} {c['name']} (ID: {c['id']})" for c in CITIES_LIST])
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

# ═══════════════════════════════════════════
# АДМИНКА
# ═══════════════════════════════════════════
@dp.message(Command("admin_panel"))
async def cmd_admin_panel(m: Message):
    try:
        uid = m.from_user.id
        if uid not in ADMIN_IDS: return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏦 Банки игроков", callback_data="new_banks"), InlineKeyboardButton(text="👑 Назначить", callback_data="new_appoint")],
            [InlineKeyboardButton(text="🗳️ Голоса", callback_data="admin_votes"), InlineKeyboardButton(text="➖ Снять", callback_data="admin_remove_votes")],
            [InlineKeyboardButton(text="➕ Добавить", callback_data="admin_add_votes"), InlineKeyboardButton(text="💰 Выдать", callback_data="admin_give_money")],
            [InlineKeyboardButton(text="🏙️ Казна городов", callback_data="admin_city_treasury"), InlineKeyboardButton(text="🏛️ Фед. казна", callback_data="admin_state_treasury")],
            [InlineKeyboardButton(text="👥 Топ игроков", callback_data="admin_players")],
        ])
        await m.answer("🔒 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:", reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка admin_panel: {e}")
        await m.answer(f"❌ Ошибка: {str(e)}")

@dp.callback_query(lambda c: c.data.startswith("new_"))
async def callback_admin_new(callback: CallbackQuery):
    try:
        uid = callback.from_user.id
        if uid not in ADMIN_IDS: return await callback.answer("❌ Доступ запрещён", show_alert=True)
        action = callback.data.replace("new_", "")
        if action == "banks":
            async with pool.acquire() as conn:
                players = await conn.fetch("""SELECT u.user_id, u.balance, COALESCE(b.deposit, 0) as deposit FROM users u LEFT JOIN bank b ON u.chat_id = b.chat_id AND u.user_id = b.user_id WHERE u.chat_id = $1 ORDER BY (u.balance + COALESCE(b.deposit, 0)) DESC LIMIT 50""", ADMIN_CHAT_ID)
            text = "🏦 <b>БАНКИ ИГРОКОВ (ТОП-50)</b>\n\n"
            for i, p in enumerate(players, 1):
                try: name = (await bot.get_chat_member(ADMIN_CHAT_ID, p['user_id'])).user.full_name
                except: name = f"User{p['user_id']}"
                balance = p['balance']
                deposit = p['deposit']
                total = balance + deposit
                text += f"<b>{i}. {name}</b>\n   💵 Наличные: <b>{fmt_money(balance)}</b>\n   🏦 В банке: <b>{fmt_money(deposit)}</b>\n   💰 Всего: <b>{fmt_money(total)}</b>\n   🆔 ID: <code>{str(p['user_id'])}</code>\n\n"
            text += "━━━━━━━━━━━━━━━━━━━━\n<i>Для назначения: /appoint [должность] [user_id] [город_id если мэр]</i>\n\n"
            text += "<b>Примеры:</b>\n/appoint president 123456789\n/appoint prime 123456789\n/appoint mayor 123456789 1\n\n"
            text += "<b>Города:</b>\n"
            cities_list = ", ".join([f"{c['emoji']} {c['name']} (ID: {c['id']})" for c in CITIES_LIST])
            text += cities_list
            await callback.message.edit_text(text, parse_mode="HTML")
        elif action == "appoint":
            cities_list = ", ".join([f"{c['emoji']} {c['name']} (ID: {c['id']})" for c in CITIES_LIST])
            await callback.message.edit_text(f"👑 <b>НАЗНАЧЕНИЕ НА ДОЛЖНОСТЬ</b>\n\n<b>Команды (работают прямо здесь в группе):</b>\n\n🇷🇺 <b>Президент (90 дней):</b>\n<code>/appoint president [user_id]</code>\n\n💼 <b>Премьер-министр (90 дней):</b>\n<code>/appoint prime [user_id]</code>\n\n🏛️ <b>Мэр города (60 дней):</b>\n<code>/appoint mayor [user_id] [город_id]</code>\n\n<b>Доступные города:</b>\n{cities_list}\n\n⚠️ <b>Важно:</b>\n• Команды работают прямо в этом чате\n• Старый чиновник будет снят автоматически\n• user_id можно скопировать из списка банков выше", parse_mode="HTML")
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
                table = 'mayor_candidates'; role_name = 'мэра'
            elif election_type == 'president':
                election_id = f"federal_{cid}_president_w{week_num}"
                candidates = await conn.fetch("SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='president' AND election_id=$2 ORDER BY id ASC", cid, election_id)
                table = 'federal_candidates'; role_name = 'президента'
            elif election_type == 'prime':
                election_id = f"federal_{cid}_prime_minister_w{week_num}"
                candidates = await conn.fetch("SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='prime_minister' AND election_id=$2 ORDER BY id ASC", cid, election_id)
                table = 'federal_candidates'; role_name = 'премьера'
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
                table = 'mayor_candidates'; role_name = 'мэра'
            elif election_type == 'president':
                election_id = f"federal_{cid}_president_w{week_num}"
                candidates = await conn.fetch("SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='president' AND election_id=$2 ORDER BY id ASC", cid, election_id)
                table = 'federal_candidates'; role_name = 'президента'
            elif election_type == 'prime':
                election_id = f"federal_{cid}_prime_minister_w{week_num}"
                candidates = await conn.fetch("SELECT id, user_id, votes FROM federal_candidates WHERE chat_id=$1 AND role='prime_minister' AND election_id=$2 ORDER BY id ASC", cid, election_id)
                table = 'federal_candidates'; role_name = 'премьера'
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

# ═══════════════════════════════════════════
# КОМАНДЫ ГОРОДОВ И ПОЛИТИКИ
# ═══════════════════════════════════════════
@dp.message(Command("city"))
async def cmd_city(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2: return await m.answer("🏙️ <b>ГОРОДА</b>\n\n/city list\n/city choose [город]\n/city move [город]\n/city info\n/city residents", parse_mode="HTML")
    subcmd = args[1].lower()
    if subcmd == "list":
        t = "🏙️ <b>ГОРОДА</b>\n\n"
        for city in CITIES_LIST: t += f"{city['emoji']} <b>{city['name']}</b>\n   {city['desc']}\n\n"
        t += "/city choose [название]"
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
    if len(args) < 2: return await m.answer("🏛️ <b>УКАЗЫ</b>\n\n/president_decree amnesty\n/president_decree tax_cut\n/president_decree tax_boost\n/president_decree emergency", parse_mode="HTML")
    decree = args[1].lower()
    decree_map = {'amnesty': 'amnesty', 'tax_cut': 'tax_cut', 'tax_boost': 'tax_boost', 'emergency': 'emergency'}
    decree_type = decree_map.get(decree)
    if not decree_type: return await m.answer("❌ Неизвестный указ!")
    if decree_type == 'amnesty':
        try:
            async with pool.acquire() as conn:
                jailed = await conn.fetch("SELECT user_id FROM jail WHERE chat_id=$1 AND release_time > $2", cid, time.time())
                count = len(jailed)
                if count > 0: await conn.execute("DELETE FROM jail WHERE chat_id=$1 AND release_time > $2", cid, time.time())
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
    if len(args) < 2: return await m.answer("💼 <b>УКАЗЫ</b>\n\n/prime_decree subsidy\n/prime_decree investment\n/prime_decree tax_cut\n/prime_decree tax_boost", parse_mode="HTML")
    decree = args[1].lower()
    decree_map = {'subsidy': 'subsidy', 'investment': 'investment', 'tax_cut': 'tax_cut', 'tax_boost': 'tax_boost'}
    decree_type = decree_map.get(decree)
    if not decree_type: return await m.answer("❌ Неизвестный указ!")
    if decree_type == 'investment':
        try:
            async with pool.acquire() as conn:
                cities = await conn.fetch("SELECT DISTINCT city_id FROM player_cities WHERE chat_id=$1", cid)
                for city_row in cities: await update_city_treasury(cid, city_row['city_id'], 5000)
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
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2: return await m.answer("⚖️ <b>ИМПИЧМЕНТ</b>\n\n/impeach president — против Президента\n/impeach prime — против Премьера\n\nНужно 10 голосов за 7 дней", parse_mode="HTML")
    role = args[1].lower()
    if role not in ['president', 'prime']: return await m.answer("❌ Используй president или prime")
    db_role = 'president' if role == 'president' else 'prime_minister'
    official = await get_federal_role(cid, db_role)
    if not official: return await m.answer("❌ Сейчас нет действующего чиновника!")
    if official['user_id'] == uid: return await m.answer("❌ Нельзя голосовать против себя!")
    async with pool.acquire() as conn:
        already_voted = await conn.fetchrow("SELECT * FROM impeachment_votes WHERE chat_id=$1 AND role=$2 AND voter_id=$3", cid, db_role, uid)
        if already_voted: return await m.answer("❌ Ты уже голосовал за импичмент!")
        await conn.execute("INSERT INTO impeachment_votes (chat_id, role, voter_id, voted_at) VALUES ($1,$2,$3,$4)", cid, db_role, uid, time.time())
        votes = await conn.fetchval("SELECT COUNT(*) FROM impeachment_votes WHERE chat_id=$1 AND role=$2", cid, db_role)
    role_name = "Президент" if role == 'president' else "Премьер"
    if votes >= 10:
        await conn.execute("DELETE FROM federal_roles WHERE chat_id=$1 AND role=$2", cid, db_role)
        await conn.execute("DELETE FROM impeachment_votes WHERE chat_id=$1 AND role=$2", cid, db_role)
        try: official_name = (await bot.get_chat_member(cid, official['user_id'])).user.full_name
        except: official_name = f"User{official['user_id']}"
        msg = f"⚖️ <b>ИМПИЧМЕНТ УСПЕШЕН!</b>\n\n👤 {role_name} {official_name} отстранён от должности!\n🗳️ Голосов: {votes}/10\n\n⏳ Новые выборы через 24 часа"
        await bot.send_message(cid, msg, parse_mode="HTML")
        await m.answer("✅ Импичмент проведён!")
    else:
        await m.answer(f"⚖️ Голос за импичмент {role_name} принят!\n📊 Голосов: {votes}/10", parse_mode="HTML")

@dp.message(Command("debt_give"))
async def cmd_debt_give(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 3: return await m.answer(f"📜 <b>ДАТЬ В ДОЛГ</b>\n\nОтветь на сообщение:\n/debt_give сумма дни\n\nПример: /debt_give 50000 3\nКомиссия: {DEBT_FEE_PERCENT}%", parse_mode="HTML")
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
            except: lender_name = f"User{d['lender_id']}"
            t += f"• {lender_name}: {fmt_money(d['amount'])}\n"
    else: t += "✅ Я никому не должен\n"
    if owed_me:
        t += "\n📥 <b>Мне должны:</b>\n"
        for d in owed_me:
            try:
                borrower = await bot.get_chat_member(cid, d['borrower_id'])
                borrower_name = borrower.user.full_name
            except: borrower_name = f"User{d['borrower_id']}"
            t += f"• {borrower_name}: {fmt_money(d['amount'])}\n"
    else: t += "\n✅ Мне никто не должен"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("mayor_report"))
async def cmd_mayor_report(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = await get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    mayor = await get_mayor(cid, player_city['id'])
    if not mayor or mayor['user_id'] != uid: return await m.answer("❌ Только мэр!")
    args = m.text.split(maxsplit=1)
    if len(args) < 2: return await m.answer("📊 <b>ОТЧЁТ</b>\n\n/mayor_report [описание]\n\nПример: /mayor_report Построен парк", parse_mode="HTML")
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

# ═══════════════════════════════════════════
# ТОРГОВАЯ ПЛОЩАДКА
# ═══════════════════════════════════════════
@dp.message(Command("marketplace"))
async def cmd_marketplace(m: Message):
    try:
        cid = m.chat.id
        async with pool.acquire() as conn:
            items = await conn.fetch("SELECT * FROM marketplace WHERE chat_id=$1 ORDER BY created_at DESC LIMIT 20", cid)
        if not items: return await m.answer("🏪 <b>Торговая площадка пуста!</b>\n\nПродайте что-нибудь через /sell", parse_mode="HTML")
        t = "🏪 <b>Торговая площадка:</b>\n\n"
        for item in items:
            seller = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, item['seller_id']) or f"User{item['seller_id']}"
            if item['item_type'] == 'inventory': icon = "🎒"
            elif item['item_type'] == 'car': icon = "🚗"
            else: icon = "🏢"
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
            return await m.answer("🏪 <b>Продать предмет</b>\n\nИспользование:\n/sell inv <название> <цена>\n/sell car <ключ_машины> <цена>\n/sell biz <название_бизнеса> <цена>\n\nПример: /sell inv Алмаз 5000", parse_mode="HTML")
        sell_type = args[1].lower()
        try: price = int(args[-1])
        except: return await m.answer("❌ Цена должна быть числом!")
        if price < 10: return await m.answer("❌ Минимальная цена: 10")
        item_name = " ".join(args[2:-1])
        async with pool.acquire() as conn:
            if sell_type == 'inv':
                item = await conn.fetchrow("SELECT id, item_name, rarity FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3 LIMIT 1", cid, uid, item_name)
                if not item: return await m.answer(f"❌ У вас нет предмета '{item_name}'")
                await conn.execute("DELETE FROM inventory WHERE id=$1", item['id'])
                await conn.execute("INSERT INTO marketplace (chat_id, seller_id, item_type, item_name, item_key, price, created_at) VALUES ($1,$2,'inventory',$3,$4,$5,$6)", cid, uid, item['item_name'], item['rarity'], price, time.time())
                await m.answer(f"✅ Предмет <b>{item['item_name']}</b> выставлен за {fmt_money(price)}!", parse_mode="HTML")
            elif sell_type == 'car':
                car_key = item_name.lower().replace(" ", "_")
                car = await conn.fetchrow("SELECT id, car_name FROM garage WHERE chat_id=$1 AND user_id=$2 AND car_key=$3 LIMIT 1", cid, uid, car_key)
                if not car: return await m.answer(f"❌ У вас нет машины с ключом '{car_key}'. Используйте /mycar чтобы посмотреть ключи.")
                await conn.execute("DELETE FROM garage WHERE id=$1", car['id'])
                await conn.execute("INSERT INTO marketplace (chat_id, seller_id, item_type, item_name, item_key, price, created_at) VALUES ($1,$2,'car',$3,$4,$5,$6)", cid, uid, car['car_name'], car_key, price, time.time())
                await m.answer(f"✅ Машина <b>{car['car_name']}</b> выставлена за {fmt_money(price)}!", parse_mode="HTML")
            elif sell_type == 'biz':
                biz = await conn.fetchrow("SELECT id, business_name, income FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name ILIKE $3 LIMIT 1", cid, uid, f"%{item_name}%")
                if not biz: return await m.answer(f"❌ У вас нет бизнеса '{item_name}'")
                has_stocks = await conn.fetchval("SELECT 1 FROM stocks WHERE business_id=$1", biz['id'])
                if has_stocks: return await m.answer("❌ Нельзя продать бизнес, у которого есть акции! Сначала выкупите все акции.")
                await conn.execute("DELETE FROM businesses WHERE id=$1", biz['id'])
                await conn.execute("INSERT INTO marketplace (chat_id, seller_id, item_type, item_name, item_key, price, created_at) VALUES ($1,$2,'business',$3,$4,$5,$6)", cid, uid, biz['business_name'], biz['business_name'], price, time.time())
                await m.answer(f"✅ Бизнес <b>{biz['business_name']}</b> выставлен за {fmt_money(price)}!", parse_mode="HTML")
            else: return await m.answer("❌ Тип: inv, car или biz")
    except Exception as e:
        logging.error(f"Ошибка в cmd_sell: {e}")
        await m.answer(f"❌ Ошибка при продаже: {str(e)}")

@dp.message(Command("buy_item"))
async def cmd_buy_item(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2: return await m.answer("🏪 <b>/buy_item ID_лота</b>")
        try: lot_id = int(args[1])
        except: return await m.answer("❌ ID должен быть числом!")
        async with pool.acquire() as conn:
            lot = await conn.fetchrow("SELECT * FROM marketplace WHERE id=$1 AND chat_id=$2", lot_id, cid)
            if not lot: return await m.answer("❌ Лот не найден или уже продан!")
            if lot['seller_id'] == uid: return await m.answer("❌ Нельзя купить у себя!")
            buyer = await get_user(cid, uid)
            if buyer['balance'] < lot['price']: return await m.answer(f"❌ Нужно {fmt_money(lot['price'])}. У вас: {fmt_money(buyer['balance'])}")
            await update_balance(cid, uid, -lot['price'])
            await update_balance(cid, lot['seller_id'], lot['price'])
            if lot['item_type'] == 'inventory':
                await conn.execute("INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,'market',$4)", cid, uid, lot['item_name'], lot['item_key'])
            elif lot['item_type'] == 'car':
                await conn.execute("INSERT INTO garage (chat_id, user_id, car_key, car_name) VALUES ($1,$2,$3,$4)", cid, uid, lot['item_key'], lot['item_name'])
            elif lot['item_type'] == 'business':
                await conn.execute("INSERT INTO businesses (chat_id, user_id, business_name, income, last_collect_time) VALUES ($1,$2,$3,0,$4)", cid, uid, lot['item_name'], time.time())
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

# ═══════════════════════════════════════════
# БИРЖА АКЦИЙ
# ═══════════════════════════════════════════
@dp.message(Command("stocks"))
async def cmd_stocks(m: Message):
    try:
        cid = m.chat.id
        async with pool.acquire() as conn:
            stocks = await conn.fetch("SELECT * FROM stocks WHERE chat_id=$1 AND shares_available > 0 ORDER BY price_per_share ASC", cid)
        if not stocks: return await m.answer("📈 <b>Биржа пуста!</b>\n\nВладельцы бизнесов могут выпустить акции: /issue_stock", parse_mode="HTML")
        t = "📈 <b>Биржа акций:</b>\n\n"
        count = 0
        for stock in stocks:
            try:
                owner_name = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, stock['owner_id']) or f"User{stock['owner_id']}"
                biz = await conn.fetchrow("SELECT business_name FROM businesses WHERE id=$1", stock['business_id'])
                biz_name = biz['business_name'] if biz else "❓ Удалён"
                price = stock['price_per_share'] if stock['price_per_share'] else 0
                last_change = stock['last_price_change'] if stock['last_price_change'] else price
                if last_change == 0: last_change = 1
                change_pct = int((price - last_change) / abs(last_change) * 100)
                arrow = "📈" if change_pct >= 0 else "📉"
                shares_avail = stock['shares_available'] if stock['shares_available'] else 0
                shares_issued = stock['shares_issued'] if stock['shares_issued'] else 0
                dividend = stock['dividend_per_share'] if stock['dividend_per_share'] else 0
                t += f"🏢 <b>{biz_name}</b> ({owner_name})\n💰 Цена: {fmt_money(price)}/акция {arrow} {change_pct}%\n💵 Дивиденды: {fmt_money(dividend)}/день\n📊 Доступно: {shares_avail}/{shares_issued}\n🛒 /buy_stock {stock['id']} (кол-во)\n\n"
                count += 1
            except Exception as e: logging.error(f"stocks display error for stock {stock['id']}: {e}")
        if count == 0: return await m.answer("📈 <b>Нет доступных акций!</b>", parse_mode="HTML")
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
        if len(args) < 2: return await m.answer("📈 <b>/issue_stock (название бизнеса)</b>\n\nВыпускает 10 акций вашего бизнеса", parse_mode="HTML")
        biz_name = " ".join(args[1:])
        async with pool.acquire() as conn:
            biz = await conn.fetchrow("SELECT id, business_name, income FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name ILIKE $3 LIMIT 1", cid, uid, f"%{biz_name}%")
            if not biz: return await m.answer(f"❌ У вас нет бизнеса '{biz_name}'")
            existing = await conn.fetchval("SELECT 1 FROM stocks WHERE business_id=$1", biz['id'])
            if existing: return await m.answer("❌ У этого бизнеса уже есть акции!")
            market_price = 0
            for k, v in MARKET.items():
                if v['type'] == 'business' and v['name'] == biz['business_name']:
                    market_price = v['price']
                    break
            if market_price == 0: market_price = biz['income'] * 6
            price = max(100, int(market_price / 15))
            dividend = max(1, biz['income'] // 30)
            await conn.execute("INSERT INTO stocks (chat_id, business_id, owner_id, shares_issued, shares_available, price_per_share, dividend_per_share, last_price_change) VALUES ($1,$2,$3,10,10,$4,$5,$6)", cid, biz['id'], uid, price, dividend, float(price))
            await m.answer(f"📈 <b>Акции выпущены!</b>\n\n🏢 Бизнес: {biz['business_name']}\n💰 Цена: {fmt_money(price)}/акция\n💵 Дивиденды: {fmt_money(dividend)}/день\n📊 Выпущено: 10 акций\n\nИгроки могут купить их через /stocks", parse_mode="HTML")
    except Exception as e:
        logging.error(f"issue_stock error: {e}")
        await m.answer(f"❌ Ошибка при выпуске акций: {str(e)}")

@dp.message(Command("buy_stock"))
async def cmd_buy_stock(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 3: return await m.answer("📈 <b>/buy_stock ID (количество)</b>")
        try:
            stock_id = int(args[1])
            qty = int(args[2])
        except: return await m.answer("❌ ID и количество должны быть числами!")
        if qty < 1: return await m.answer("❌ Минимум 1 акция!")
        async with pool.acquire() as conn:
            stock = await conn.fetchrow("SELECT * FROM stocks WHERE id=$1", stock_id)
            if not stock: return await m.answer("❌ Акция не найдена!")
            if stock['shares_available'] < qty: return await m.answer(f"❌ Доступно только {stock['shares_available']} акций!")
            total_cost = stock['price_per_share'] * qty
            buyer = await get_user(cid, uid)
            if buyer['balance'] < total_cost: return await m.answer(f"❌ Нужно {fmt_money(total_cost)}. У вас: {fmt_money(buyer['balance'])}")
            await update_balance(cid, uid, -total_cost)
            await conn.execute("UPDATE stocks SET shares_available = shares_available - $1 WHERE id=$2", qty, stock_id)
            existing = await conn.fetchrow("SELECT * FROM stock_holdings WHERE stock_id=$1 AND user_id=$2", stock_id, uid)
            if existing: await conn.execute("UPDATE stock_holdings SET shares_owned = shares_owned + $1 WHERE id=$2", qty, existing['id'])
            else: await conn.execute("INSERT INTO stock_holdings (stock_id, user_id, shares_owned) VALUES ($1,$2,$3)", stock_id, uid, qty)
            await m.answer(f"✅ Куплено <b>{qty} акций</b>!\n\n💰 Потрачено: {fmt_money(total_cost)}\n💵 Дивиденды: {fmt_money(stock['dividend_per_share'] * qty)}/день", parse_mode="HTML")
    except Exception as e:
        logging.error(f"buy_stock error: {e}")
        await m.answer(f"❌ Ошибка при покупке акций: {str(e)}")

@dp.message(Command("sell_stock"))
async def cmd_sell_stock(m: Message):
    try:
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 3: return await m.answer("📈 <b>/sell_stock ID (количество)</b>")
        try:
            stock_id = int(args[1])
            qty = int(args[2])
        except: return await m.answer("❌ ID и количество должны быть числами!")
        async with pool.acquire() as conn:
            holding = await conn.fetchrow("SELECT * FROM stock_holdings WHERE stock_id=$1 AND user_id=$2", stock_id, uid)
            if not holding or holding['shares_owned'] < qty: return await m.answer("❌ У вас недостаточно акций!")
            stock = await conn.fetchrow("SELECT * FROM stocks WHERE id=$1", stock_id)
            if not stock: return await m.answer("❌ Акция не найдена!")
            refund = int(stock['price_per_share'] * qty * 0.7)
            await update_balance(cid, uid, refund)
            await conn.execute("UPDATE stock_holdings SET shares_owned = shares_owned - $1 WHERE id=$2", qty, holding['id'])
            await conn.execute("UPDATE stocks SET shares_available = shares_available + $1 WHERE id=$2", qty, stock_id)
            new_shares = holding['shares_owned'] - qty
            if new_shares <= 0: await conn.execute("DELETE FROM stock_holdings WHERE id=$1", holding['id'])
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
        if not holdings: return await m.answer("📈 <b>У вас нет акций.</b>\n\nКупите на бирже: /stocks", parse_mode="HTML")
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
                t += f"🏢 <b>{biz_name}</b>\n   📊 Акции: {h['shares_owned']}\n   💰 Стоимость: {fmt_money(value)}\n   💵 Дивиденды: {fmt_money(dividends)}/день\n\n"
            except Exception as e: logging.error(f"my_stocks display error: {e}")
        t += f"━━━━━━━━━━━━━━━━━━━━\n💰 Общая стоимость: <b>{fmt_money(total_value)}</b>\n💵 Дивиденды/день: <b>{fmt_money(total_dividends)}</b>"
        await m.answer(t, parse_mode="HTML")
    except Exception as e:
        logging.error(f"my_stocks error: {e}")
        await m.answer(f"❌ Ошибка: {str(e)}")

# ═══════════════════════════════════════════
# АУКЦИОН
# ═══════════════════════════════════════════
@dp.message(Command("auction"))
async def cmd_auction(m: Message):
    try:
        cid = m.chat.id
        async with pool.acquire() as conn:
            auctions = await conn.fetch("SELECT * FROM auctions WHERE chat_id=$1 AND status='active' ORDER BY end_time ASC", cid)
        if not auctions: return await m.answer("🏆 <b>Аукцион пуст!</b>\n\nСледите за анонсами редких лотов!", parse_mode="HTML")
        t = "🏆 <b>АУКЦИОН РЕДКИХ ПРЕДМЕТОВ</b>\n\n"
        for auction in auctions:
            time_left = int(auction['end_time'] - time.time())
            if time_left <= 0: continue
            hours = time_left // 3600
            minutes = (time_left % 3600) // 60
            if auction['item_type'] == 'car': icon = "🚗"
            elif auction['item_type'] == 'business': icon = "🏢"
            else: icon = "🎁"
            bidder_name = "Никто"
            if auction['current_bidder_id']:
                bidder_name = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, auction['current_bidder_id']) or f"User{auction['current_bidder_id']}"
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
        if len(args) < 3: return await m.answer("🏆 <b>/bid ID сумма</b>\n\nПример: /bid 1 50000", parse_mode="HTML")
        try:
            auction_id = int(args[1])
            bid_amount = int(args[2])
        except: return await m.answer("❌ ID и сумма должны быть числами!")
        if bid_amount <= 0: return await m.answer("❌ Сумма должна быть больше 0!")
        async with pool.acquire() as conn:
            auction = await conn.fetchrow("SELECT * FROM auctions WHERE id=$1 AND chat_id=$2 AND status='active'", auction_id, cid)
            if not auction: return await m.answer("❌ Аукцион не найден или завершён!")
            if time.time() > auction['end_time']: return await m.answer("⏰ Время аукциона вышло!")
            min_bid = auction['current_bid'] + auction['min_increment']
            if bid_amount < min_bid: return await m.answer(f"❌ Минимальная ставка: {fmt_money(min_bid)}")
            user = await get_user(cid, uid)
            if user['balance'] < bid_amount: return await m.answer(f"❌ Недостаточно средств! Нужно: {fmt_money(bid_amount)}")
            if auction['current_bidder_id'] == uid: return await m.answer("❌ Вы уже лидер! Повысьте ставку.")
            await update_balance(cid, uid, -bid_amount)
            if auction['current_bidder_id']:
                await update_balance(cid, auction['current_bidder_id'], auction['current_bid'])
                try:
                    await bot.send_message(cid, f"⚠️ <b>Вас перебидили!</b>\n\nЛот: {auction['item_name']}\nВаша ставка {fmt_money(auction['current_bid'])} возвращена.", parse_mode="HTML")
                except: pass
            await conn.execute("UPDATE auctions SET current_bid=$1, current_bidder_id=$2 WHERE id=$3", bid_amount, uid, auction_id)
            await conn.execute("INSERT INTO auction_bids (auction_id, user_id, bid_amount, bid_time) VALUES ($1,$2,$3,$4)", auction_id, uid, bid_amount, time.time())
            time_left = auction['end_time'] - time.time()
            if time_left < 120:
                new_end_time = time.time() + 300
                await conn.execute("UPDATE auctions SET end_time=$1 WHERE id=$2", new_end_time, auction_id)
                await m.answer(f"⏰ Время продлено на 5 минут!", parse_mode="HTML")
            await m.answer(f"✅ <b>Ставка принята!</b>\n\n🏆 Лот: {auction['item_name']}\n💰 Ваша ставка: <b>{fmt_money(bid_amount)}</b>\n⏰ Осталось: {int((auction['end_time'] - time.time()) // 60)} мин", parse_mode="HTML")
    except Exception as e:
        logging.error(f"bid error: {e}")
        await m.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("create_auction"))
async def cmd_create_auction(m: Message):
    if m.from_user.id not in ADMIN_IDS: return await m.answer("❌ Только для админов!")
    args = m.text.split()
    if len(args) < 5:
        return await m.answer("🏆 <b>Создать аукцион</b>\n\nИспользование:\n/create_auction type key name start_price duration_hours\n\ntype: car/business/item\nduration_hours: длительность в часах\n\nПример: /create_auction car gold_bmw Золотой BMW 100000 24", parse_mode="HTML")
    try:
        item_type = args[1]
        item_key = args[2]
        item_name = " ".join(args[3:-2])
        starting_price = int(args[-2])
        duration_hours = int(args[-1])
    except: return await m.answer("❌ Ошибка в параметрах!")
    if item_type not in ['car', 'business', 'item']: return await m.answer("❌ Тип: car, business или item")
    if duration_hours < 1 or duration_hours > 168: return await m.answer("❌ Длительность: от 1 до 168 часов (7 дней)")
    cid = m.chat.id
    start_time = time.time()
    end_time = start_time + (duration_hours * 3600)
    min_increment = max(100, starting_price // 10)
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO auctions (chat_id, item_type, item_key, item_name, starting_price, current_bid, start_time, end_time, min_increment) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)", cid, item_type, item_key, item_name, starting_price, starting_price, start_time, end_time, min_increment)
    await m.answer(f"🏆 <b>Аукцион создан!</b>\n\n{item_name}\n💰 Стартовая цена: {fmt_money(starting_price)}\n⏰ Длительность: {duration_hours} часов\n📈 Мин. шаг: {fmt_money(min_increment)}", parse_mode="HTML")

@dp.message(Command("end_auction"))
async def cmd_end_auction(m: Message):
    if m.from_user.id not in ADMIN_IDS: return await m.answer("❌ Только для админов!")
    args = m.text.split()
    if len(args) < 2: return await m.answer("🏆 <b>/end_auction ID</b>")
    try: auction_id = int(args[1])
    except: return await m.answer("❌ ID должен быть числом!")
    cid = m.chat.id
    async with pool.acquire() as conn:
        auction = await conn.fetchrow("SELECT * FROM auctions WHERE id=$1 AND chat_id=$2", auction_id, cid)
        if not auction: return await m.answer("❌ Аукцион не найден!")
        if auction['status'] == 'ended': return await m.answer("❌ Аукцион уже завершён!")
        await conn.execute("UPDATE auctions SET status='ended', end_time=$1 WHERE id=$2", time.time(), auction_id)
    await complete_auction(auction)
    await m.answer(f"✅ Аукцион #{auction_id} завершён вручную!", parse_mode="HTML")

# ═══════════════════════════════════════════
# ОГРАБЛЕНИЯ БАНКОВ
# ═══════════════════════════════════════════
@dp.message(Command("bank_heist"))
async def cmd_bank_heist(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 Вы в тюрьме!")
    t = "🏦 <b>ОГРАБЛЕНИЯ БАНКОВ</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"
    t += "👥 <b>Команда: ровно 3 игрока</b>\n\n📋 <b>Роли:</b>\n🔓 Взломщик → 💻 Хакер → 💣 Сапёр\n\n⚠️ Инструмент НЕ обязателен!\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>БАНКИ:</b>\n\n"
    for key, bank in BANKS.items():
        t += f"{bank['name']}\n   💰 Награда: {fmt_money(bank['reward'])}\n   🎯 Шанс: {bank['chance']}%\n   🔒 Тюрьма: {bank['jail']}ч\n   🏃 /heist_create {key}\n\n"
    t += "━━━━━━━━━━━━━━━━━━━━\n🛠️ <b>Инструменты:</b>\n"
    for key, tool in TOOLS.items():
        t += f"/buy_tool {key} — {tool['name']} ({fmt_money(tool['price'])})\n"
    t += f"\n⏰ Кулдаун: <b>24 часа</b>"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buy_tool"))
async def cmd_buy_tool(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 Вы в тюрьме!")
    args = m.text.split()
    if len(args) < 2 or args[1] not in TOOLS:
        t = "🛠️ <b>МАГАЗИН</b>\n\n"
        for key, tool in TOOLS.items():
            t += f"{tool['name']} — {fmt_money(tool['price'])}\n   🛒 /buy_tool {key}\n\n"
        return await m.answer(t, parse_mode="HTML")
    tool_key = args[1]
    tool = TOOLS[tool_key]
    user = await get_user(cid, uid)
    if user['balance'] < tool['price']: return await m.answer(f"❌ Нужно {fmt_money(tool['price'])}. У вас: {fmt_money(user['balance'])}")
    if not hasattr(bot, 'heist_tools'): bot.heist_tools = {}
    bot.heist_tools[uid] = tool_key
    await update_balance(cid, uid, -tool['price'])
    await m.answer(f"✅ Куплен: {tool['name']}\n💰 Списано: {fmt_money(tool['price'])}", parse_mode="HTML")

@dp.message(Command("heist_create"))
async def cmd_heist_create(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 Вы в тюрьме!")
    args = m.text.split()
    if len(args) < 2 or args[1] not in BANKS: return await m.answer("Используй: /heist_create local\nТипы: local, city, central, swiss")
    bank = BANKS[args[1]]
    has_cd, rem = await check_cooldown(cid, uid)
    if has_cd:
        h, mn = rem // 3600, (rem % 3600) // 60
        return await m.answer(f"⏳ Кулдаун: {h}ч {mn}мин")
    tool_key = getattr(bot, 'heist_tools', {}).get(uid)
    t_name = TOOLS[tool_key]['name'] if tool_key else "👊 Голыми руками"
    lobby_id = random.randint(100000, 999999)
    heist_lobbies[lobby_id] = {"id": lobby_id, "creator": uid, "bank": bank, "tool_key": tool_key, "players": {uid: "hacker"}}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💻 Присоединиться", callback_data=f"join_{lobby_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{lobby_id}")]
    ])
    msg = await m.answer(f"🏦 <b>ЛОББИ #{lobby_id}</b>\n\n🏛️ {bank['name']}\n🛠️ {t_name}\n💰 {fmt_money(bank['reward'])}\n🎯 Шанс: {bank['chance']}%\n👥 1/3\n\n🔓 {m.from_user.full_name}", reply_markup=kb, parse_mode="HTML")
    heist_lobbies[lobby_id]["msg_id"] = msg.message_id

async def get_heist_cooldown(cid, uid):
    try:
        async with pool.acquire() as conn:
            r = await conn.fetchrow("SELECT last_heist_time FROM heist_cooldowns WHERE chat_id=$1 AND user_id=$2", cid, uid)
            return r['last_heist_time'] if r else 0
    except: return 0

async def check_cooldown(cid, uid):
    try:
        last = await get_heist_cooldown(cid, uid)
        if last == 0: return False, 0
        elapsed = time.time() - last
        if elapsed < HEIST_COOLDOWN: return True, int(HEIST_COOLDOWN - elapsed)
        return False, 0
    except: return False, 0

@dp.callback_query(lambda c: c.data and c.data.startswith("join_"))
async def cb_join(cb: types.CallbackQuery):
    try: lobby_id = int(cb.data.split("_")[1])
    except: return await cb.answer("❌ Ошибка", show_alert=True)
    if lobby_id not in heist_lobbies: return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    lobby = heist_lobbies[lobby_id]
    uid, cid = cb.from_user.id, cb.message.chat.id
    if await is_in_jail(cid, uid): return await cb.answer("🔒 Вы в тюрьме!", show_alert=True)
    if uid in lobby["players"]: return await cb.answer("✅ Вы уже в команде!", show_alert=True)
    if len(lobby["players"]) >= 3: return await cb.answer("❌ Команда полная!", show_alert=True)
    has_cd, rem = await check_cooldown(cid, uid)
    if has_cd: return await cb.answer(f"⏳ Кулдаун: {rem//3600}ч", show_alert=True)
    role = "coder" if len(lobby["players"]) == 1 else "sapper"
    lobby["players"][uid] = role
    await cb.answer(f"✅ Роль: {HEIST_ROLES[role]}")
    try:
        names = []
        for pid, prole in lobby["players"].items():
            try: name = (await bot.get_chat_member(cid, pid)).user.full_name
            except: name = f"User{pid}"
            names.append(f"{HEIST_ROLES[prole]}: {name}")
        t_name = TOOLS[lobby['tool_key']]['name'] if lobby['tool_key'] else "👊 Голыми руками"
        p_count = len(lobby["players"])
        if p_count < 3:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💻 Присоединиться", callback_data=f"join_{lobby_id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{lobby_id}")]
            ])
            await cb.message.edit_text(f"🏦 <b>ЛОББИ #{lobby_id}</b>\n\n🏛️ {lobby['bank']['name']}\n🛠️ {t_name}\n💰 {fmt_money(lobby['bank']['reward'])}\n👥 {p_count}/3\n\n" + "\n".join(names), reply_markup=kb, parse_mode="HTML")
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Начать", callback_data=f"start_{lobby_id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{lobby_id}")]
            ])
            await cb.message.edit_text(f"🏦 <b>ЛОББИ #{lobby_id} — ГОТОВО!</b>\n\n🏛️ {lobby['bank']['name']}\n🛠️ {t_name}\n💰 {fmt_money(lobby['bank']['reward'])}\n👥 3/3 ✅\n\n" + "\n".join(names), reply_markup=kb, parse_mode="HTML")
    except Exception as e: print(f"Ошибка join: {e}")

@dp.callback_query(lambda c: c.data and c.data.startswith("cancel_"))
async def cb_cancel(cb: types.CallbackQuery):
    try: lobby_id = int(cb.data.split("_")[1])
    except: return await cb.answer("❌", show_alert=True)
    if lobby_id not in heist_lobbies: return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    lobby = heist_lobbies[lobby_id]
    if cb.from_user.id != lobby["creator"]: return await cb.answer("❌ Только создатель!", show_alert=True)
    del heist_lobbies[lobby_id]
    try: await cb.message.edit_text("❌ Лобби отменено", reply_markup=None)
    except: pass
    await cb.answer("✅ Отменено")

@dp.callback_query(lambda c: c.data and c.data.startswith("start_"))
async def cb_start(cb: types.CallbackQuery):
    try: lobby_id = int(cb.data.split("_")[1])
    except: return await cb.answer("❌", show_alert=True)
    if lobby_id not in heist_lobbies: return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    lobby = heist_lobbies[lobby_id]
    cid = cb.message.chat.id
    if len(lobby["players"]) != 3: return await cb.answer("❌ Нужно 3 игрока!", show_alert=True)
    await cb.answer("🚀 Старт!")
    try: await cb.message.delete()
    except: pass
    await run_stage1(cid, lobby)

async def run_stage1(cid, lobby):
    bank = lobby["bank"]
    tool_key = lobby["tool_key"]
    tool = TOOLS[tool_key] if tool_key else BASE_TOOL
    players = lobby["players"]
    hacker_uid = [uid for uid, r in players.items() if r == "hacker"][0]
    chance = min(95, bank['chance'] + tool['bonus_chance'])
    try: name = (await bot.get_chat_member(cid, hacker_uid)).user.full_name
    except: name = f"User{hacker_uid}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔓 Взломать", callback_data=f"s1_{lobby['id']}_{hacker_uid}_{chance}")]])
    await bot.send_message(cid, f"🏦 <b>ЭТАП 1: ВЗЛОМ ДВЕРИ</b>\n\n👤 {name} (Взломщик)\n🏛️ {bank['name']}\n🛠️ {tool['name']}\n🎯 Шанс: {chance}%\n\n👇 Нажми кнопку!", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(lambda c: c.data and c.data.startswith("s1_"))
async def cb_stage1(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    try:
        lobby_id = int(parts[1])
        player_uid = int(parts[2])
        chance = int(float(parts[3]))
    except: return await cb.answer("❌ Ошибка", show_alert=True)
    if cb.from_user.id != player_uid: return await cb.answer("❌ Не твой этап!", show_alert=True)
    if lobby_id not in heist_lobbies: return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    cid = cb.message.chat.id
    lobby = heist_lobbies[lobby_id]
    roll = random.randint(1, 100)
    success = roll <= chance
    await cb.message.edit_text(f"🔓 <b>ВЗЛОМ...</b>\n\n🎲 {roll} из 100\n🎯 Нужно ≤{chance}\n\n{'✅ Успех!' if success else '❌ Провал!'}", parse_mode="HTML")
    if success:
        await asyncio.sleep(2)
        await run_stage2(cid, lobby)
    else:
        await finish_heist(cid, lobby, False, "Взлом двери провалился")
    await cb.answer()

async def run_stage2(cid, lobby):
    bank = lobby["bank"]
    tool_key = lobby["tool_key"]
    tool = TOOLS[tool_key] if tool_key else BASE_TOOL
    players = lobby["players"]
    coder_uid = [uid for uid, r in players.items() if r == "coder"][0]
    try: name = (await bot.get_chat_member(cid, coder_uid)).user.full_name
    except: name = f"User{coder_uid}"
    correct = [random.randint(1, 6)]
    lobby["correct_buttons"] = correct
    lobby["stage2_attempts"] = 0
    max_att = 3 + tool['extra_attempts']
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣", callback_data=f"s2_{lobby['id']}_{coder_uid}_1"), InlineKeyboardButton(text="2️⃣", callback_data=f"s2_{lobby['id']}_{coder_uid}_2"), InlineKeyboardButton(text="3️⃣", callback_data=f"s2_{lobby['id']}_{coder_uid}_3")],
        [InlineKeyboardButton(text="4️⃣", callback_data=f"s2_{lobby['id']}_{coder_uid}_4"), InlineKeyboardButton(text="5️⃣", callback_data=f"s2_{lobby['id']}_{coder_uid}_5"), InlineKeyboardButton(text="6️⃣", callback_data=f"s2_{lobby['id']}_{coder_uid}_6")]
    ])
    await bot.send_message(cid, f"🔐 <b>ЭТАП 2: КОД К СЕЙФУ</b>\n\n👤 {name} (Хакер)\n🏛️ {bank['name']}\n🛠️ {tool['name']}\n\n💡 Угадай 1 правильную кнопку из 6\n⏳ Попыток: {max_att}", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(lambda c: c.data and c.data.startswith("s2_"))
async def cb_stage2(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    try:
        lobby_id = int(parts[1])
        player_uid = int(parts[2])
        button = int(parts[3])
    except: return await cb.answer("❌", show_alert=True)
    if cb.from_user.id != player_uid: return await cb.answer("❌ Не твой этап!", show_alert=True)
    if lobby_id not in heist_lobbies: return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    cid = cb.message.chat.id
    lobby = heist_lobbies[lobby_id]
    correct = lobby["correct_buttons"]
    attempts = lobby["stage2_attempts"]
    tool_key = lobby["tool_key"]
    tool = TOOLS[tool_key] if tool_key else BASE_TOOL
    max_att = 3 + tool['extra_attempts']
    if button == correct[0]:
        await cb.message.edit_text(f"🔐 <b>КОД ПОДОБРАН!</b>\n✅ Кнопка: {button}\n🔓 Сейф открыт!", parse_mode="HTML")
        await asyncio.sleep(2)
        await run_stage3(cid, lobby)
    else:
        attempts += 1
        lobby["stage2_attempts"] = attempts
        if attempts >= max_att:
            await cb.message.edit_text(f"🔐 <b>ПРОВАЛ!</b>\n❌ Попытки кончились\n✅ Была кнопка: {correct[0]}", parse_mode="HTML")
            await finish_heist(cid, lobby, False, "Код не подобран")
        else:
            await cb.answer(f"❌ Неверно! Осталось: {max_att - attempts}", show_alert=True)
    await cb.answer()

async def run_stage3(cid, lobby):
    bank = lobby["bank"]
    tool_key = lobby["tool_key"]
    tool = TOOLS[tool_key] if tool_key else BASE_TOOL
    players = lobby["players"]
    sapper_uid = [uid for uid, r in players.items() if r == "sapper"][0]
    try: name = (await bot.get_chat_member(cid, sapper_uid)).user.full_name
    except: name = f"User{sapper_uid}"
    total_wires = 4 - tool['wire_reduce']
    correct_wire = random.randint(1, total_wires)
    lobby["correct_wire"] = correct_wire
    lobby["total_wires"] = total_wires
    wires = [("🔴 Красный", 1), ("🔵 Синий", 2), ("🟢 Зелёный", 3), ("🟡 Жёлтый", 4)][:total_wires]
    kb_rows = []
    for i in range(0, len(wires), 2):
        kb_rows.append([InlineKeyboardButton(text=n, callback_data=f"s3_{lobby['id']}_{sapper_uid}_{num}") for n, num in wires[i:i+2]])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    chance = round(100/total_wires)
    await bot.send_message(cid, f"💣 <b>ЭТАП 3: СИГНАЛИЗАЦИЯ</b>\n\n👤 {name} (Сапёр)\n🏛️ {bank['name']}\n🛠️ {tool['name']}\n\n⚡ {total_wires} проводов, 1 правильный\n🎯 Шанс: {chance}%", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(lambda c: c.data and c.data.startswith("s3_"))
async def cb_stage3(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    try:
        lobby_id = int(parts[1])
        player_uid = int(parts[2])
        wire = int(parts[3])
    except: return await cb.answer("❌", show_alert=True)
    if cb.from_user.id != player_uid: return await cb.answer("❌ Не твой этап!", show_alert=True)
    if lobby_id not in heist_lobbies: return await cb.answer("❌ Лобби не найдено!", show_alert=True)
    cid = cb.message.chat.id
    lobby = heist_lobbies[lobby_id]
    correct_wire = lobby["correct_wire"]
    names = {1: "🔴 Красный", 2: "🔵 Синий", 3: "🟢 Зелёный", 4: "🟡 Жёлтый"}
    if wire == correct_wire:
        await cb.message.edit_text(f"💣 <b>ОБЕЗВРЕЖЕНО!</b>\n✅ Провод: {names[wire]}\n🎉 Успех!", parse_mode="HTML")
        await asyncio.sleep(2)
        await finish_heist(cid, lobby, True, "Все этапы пройдены")
    else:
        await cb.message.edit_text(f"💣 <b>ТРЕВОГА!</b>\n❌ {names[wire]}\n✅ Было: {names[correct_wire]}\n🚨 Провал!", parse_mode="HTML")
        await finish_heist(cid, lobby, False, "Сигнализация сработала")
    await cb.answer()

async def finish_heist(cid, lobby, success, reason):
    lobby_id = lobby["id"]
    if lobby_id in heist_lobbies: del heist_lobbies[lobby_id]
    bank = lobby["bank"]
    tool_key = lobby["tool_key"]
    tool = TOOLS[tool_key] if tool_key else BASE_TOOL
    players = lobby["players"]
    if tool_key and lobby["creator"] in getattr(bot, 'heist_tools', {}):
        del bot.heist_tools[lobby["creator"]]
    team = []
    for uid, role in players.items():
        try: name = (await bot.get_chat_member(cid, uid)).user.full_name
        except: name = f"User{uid}"
        team.append(f"{HEIST_ROLES[role]}: {name}")
    now = time.time()
    if success:
        reward = bank['reward']
        async with pool.acquire() as conn:
            for uid in players.keys():
                await update_balance(cid, uid, reward)
                await conn.execute("INSERT INTO heist_cooldowns VALUES ($1,$2,$3) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_heist_time=$3", cid, uid, now)
        await bot.send_message(cid, f"✅ <b>УСПЕХ!</b>\n\n🏦 {bank['name']}\n🛠️ {tool['name']}\n👥 {', '.join(team)}\n\n💰 Каждый: <b>{fmt_money(reward)}</b>\n\n⏰ Кулдаун 24ч", parse_mode="HTML")
    else:
        jail = max(1, bank['jail'] - tool['jail_reduce'])
        until_time = now + jail * 3600
        async with pool.acquire() as conn:
            for uid in players.keys():
                await conn.execute("INSERT INTO jail (chat_id, user_id, release_time, fine_per_hour) VALUES ($1,$2,$3,$4) ON CONFLICT (chat_id, user_id) DO UPDATE SET release_time=$3, fine_per_hour=$4", cid, uid, until_time, JAIL_FINE_PER_HOUR)
                await conn.execute("INSERT INTO heist_cooldowns VALUES ($1,$2,$3) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_heist_time=$3", cid, uid, now)
        await bot.send_message(cid, f"❌ <b>ПРОВАЛ!</b>\n\n🏦 {bank['name']}\n👥 {', '.join(team)}\n\n🔒 Все в тюрьме на <b>{jail}ч</b>\n⚠️ {reason}\n⏰ Кулдаун 24ч", parse_mode="HTML")

# ═══════════════════════════════════════════
# КОНТРАБАНДА
# ═══════════════════════════════════════════
async def apply_smart_fine(cid, uid, percent):
    user = await get_user(cid, uid)
    balance = user.get('balance', 0)
    deposit = user.get('deposit', user.get('bank_balance', user.get('savings', 0)))
    total = balance + deposit
    fine = int(total * percent / 100)
    if fine <= 0: return 0
    if balance >= deposit:
        await update_balance(cid, uid, -fine)
    else:
        try:
            async with pool.acquire() as conn:
                await conn.execute("UPDATE users SET balance = GREATEST(balance - $1, 0) WHERE chat_id=$2 AND user_id=$3", fine, cid, uid)
        except:
            await update_balance(cid, uid, -fine)
    return fine

@dp.message(Command("contraband"))
async def cmd_contraband_info(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 Вы в тюрьме!")
    t = "🚛 <b>КОНТРАБАНДА</b>\n\n"
    t += "⚠️ <b>Высокий риск, высокая награда!</b>\nНужна команда из 4 человек.\n\n"
    t += "━━━━━━━━━━━━━━━━━━━━\n📦 <b>ТОВАРЫ:</b>\n\n"
    for key, item in CONTRABAND_ITEMS.items():
        t += f"{item['name']}\n"
        t += f"   💰 Цена: {fmt_money(item['price'])}\n"
        t += f"   🎁 Награда: {fmt_money(item['reward'])}\n"
        t += f"   ⚠️ Шанс провала: {item['fail_chance']}%\n"
        t += f"   💸 Штраф: {item['penalty_percent']}% баланса\n"
        t += f"   ⏱️ Время: {item['duration']//60} мин\n"
        t += f"   🏃 /contraband_start {key}\n\n"
    t += "━━━━━━━━━━━━━━━━━━━━\n"
    t += "👥 <b>Собрать команду:</b>\n"
    t += "Ответь на 3 игроков сообщением:\n"
    t += "/contraband_team\n\n"
    t += "⏰ Кулдаун: <b>6 часов</b>"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("contraband_team"))
async def cmd_contraband_team(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 Вы в тюрьме!")
    if not m.reply_to_message:
        return await m.answer("⚠️ Ответь на сообщение одного из напарников, а двух других укажи через @\nПример: ответь на Петю и напиши\n`/contraband_team @вася @миша`", parse_mode="HTML")
    team = [uid, m.reply_to_message.from_user.id]
    args = m.text.split()[1:]
    for arg in args:
        username = arg.lstrip('@')
        if not username: continue
        try:
            chat_member = await bot.get_chat_member(cid, f"@{username}")
            team.append(chat_member.user.id)
        except Exception as e:
            try:
                user_id = int(username)
                chat_member = await bot.get_chat_member(cid, user_id)
                team.append(chat_member.user.id)
            except:
                return await m.answer(f"❌ Не нашёл игрока <b>@{username}</b>\n\nПроверь:\n• Правильно ли написан username\n• Игрок точно в этом чате\n• У него есть @username в Telegram", parse_mode="HTML")
    team = list(dict.fromkeys(team))
    if len(team) != 4:
        return await m.answer(f"❌ Нужно ровно 4 человека (включая тебя).\nСейчас: {len(team)}\n\nФормат: ответь на 1 игрока + укажи 2 через @", parse_mode="HTML")
    for member_uid in team:
        if member_uid == uid: continue
        if await is_in_jail(cid, member_uid):
            try: name = (await bot.get_chat_member(cid, member_uid)).user.full_name
            except: name = f"User{member_uid}"
            return await m.answer(f"🔒 {name} сейчас в тюрьме!")
        if member_uid in contraband_cooldowns and contraband_cooldowns[member_uid] > time.time():
            try: name = (await bot.get_chat_member(cid, member_uid)).user.full_name
            except: name = f"User{member_uid}"
            return await m.answer(f"⏳ У {name} кулдаун на контрабанду!")
    run_id = f"run_{cid}_{uid}_{int(time.time())}"
    active_contraband_runs[run_id] = {"id": run_id, "leader": uid, "team": team, "status": "forming", "item": None}
    team_names = []
    for member_uid in team:
        try: name = (await bot.get_chat_member(cid, member_uid)).user.full_name
        except: name = f"User{member_uid}"
        team_names.append(name)
    await m.answer(f"🚛 <b>КОМАНДА СОБРАНА!</b>\n\n👥 Участники:\n" + "\n".join([f"• {name}" for name in team_names]) + "\n\n📋 Лидер, выбери товар:\n/contraband_start docs\n/contraband_start fake_money\n/contraband_start drugs\n/contraband_start weapons", parse_mode="HTML")

@dp.message(Command("contraband_start"))
async def cmd_contraband_start(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2 or args[1] not in CONTRABAND_ITEMS: return await m.answer("⚠️ Укажи товар: docs, fake_money, drugs, weapons")
    run = None
    for r in active_contraband_runs.values():
        if r["leader"] == uid and r["status"] == "forming":
            run = r
            break
    if not run: return await m.answer("❌ У тебя нет собранной команды! Используй /contraband_team")
    item_key = args[1]
    item = CONTRABAND_ITEMS[item_key]
    user = await get_user(cid, uid)
    if user['balance'] < item['price']: return await m.answer(f"❌ Нужно {fmt_money(item['price'])}. У тебя: {fmt_money(user['balance'])}")
    await update_balance(cid, uid, -item['price'])
    run["item"] = item_key
    run["status"] = "active"
    run["start_time"] = time.time()
    roles_list = list(CONTRABAND_ROLES.keys())
    random.shuffle(roles_list)
    run["roles"] = {uid: roles_list[i] for i, uid in enumerate(run["team"])}
    fail_chance = item['fail_chance']
    duration = item['duration']
    reward = item['reward']
    for member_uid, role in run["roles"].items():
        if role == "driver": fail_chance -= 15
        elif role == "navigator": duration = int(duration * 0.8)
        elif role == "coordinator": reward = int(reward * 1.1)
    fail_chance = max(5, fail_chance)
    run["fail_chance"] = fail_chance
    run["duration"] = duration
    run["reward"] = reward
    run["checks_passed"] = 0
    run["total_checks"] = duration // 60
    await m.answer("🚛 <b>РЕЙС НАЧАЛСЯ!</b> Каждую минуту будет проверка. Не выходите из чата!", parse_mode="HTML")
    team_info = []
    for member_uid in run["team"]:
        try: name = (await bot.get_chat_member(cid, member_uid)).user.full_name
        except: name = f"User{member_uid}"
        role_name = CONTRABAND_ROLES[run["roles"][member_uid]]['name']
        team_info.append(f"{role_name}: {name}")
    await bot.send_message(cid, f"🚛 <b>РЕЙС НАЧАЛСЯ!</b>\n\n📦 Товар: {item['name']}\n⏱️ Длительность: {duration//60} мин\n⚠️ Шанс провала: {fail_chance}%\n🎁 Награда: {fmt_money(reward)}\n\n👥 <b>Команда:</b>\n" + "\n".join(team_info) + "\n\n⏳ Проверки начались...", parse_mode="HTML")
    asyncio.create_task(contraband_check_loop(cid, run))

@dp.message(Command("contraband_status"))
async def cmd_contraband_status(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    for run in active_contraband_runs.values():
        if uid in run["team"] and run["status"] == "active":
            item = CONTRABAND_ITEMS[run["item"]]
            elapsed = time.time() - run["start_time"]
            remaining = run["duration"] - elapsed
            progress = int(elapsed / run["duration"] * 100)
            return await m.answer(f"🚛 <b>АКТИВНЫЙ РЕЙС</b>\n\n📦 Товар: {item['name']}\n⏱️ Осталось: {int(remaining)//60} мин\n📊 Прогресс: {progress}%\n✅ Проверок пройдено: {run['checks_passed']}/{run['total_checks']}", parse_mode="HTML")
    await m.answer("❌ У тебя нет активного рейса")

async def contraband_check_loop(cid, run):
    for _ in range(run["total_checks"]):
        await asyncio.sleep(60)
        if run["status"] != "active": return
        if random.randint(1, 100) <= run["fail_chance"]:
            await contraband_failed(cid, run, "Наткнулись на усиленный патруль!")
            return
        run["checks_passed"] += 1
    await contraband_success(cid, run)

async def contraband_success(cid, run):
    item = CONTRABAND_ITEMS[run["item"]]
    team = run["team"]
    reward = run["reward"]
    reward_per_person = reward // len(team)
    for member_uid in team:
        await update_balance(cid, member_uid, reward_per_person)
        contraband_cooldowns[member_uid] = time.time() + CONTRABAND_COOLDOWN
    del active_contraband_runs[run["id"]]
    await bot.send_message(cid, f"✅ <b>РЕЙС УСПЕШЕН!</b>\n\n📦 Товар: {item['name']}\n💰 Каждый получил: <b>{fmt_money(reward_per_person)}</b>\n\n⏰ Кулдаун: 6 часов", parse_mode="HTML")

async def contraband_failed(cid, run, reason):
    item = CONTRABAND_ITEMS[run["item"]]
    team = run["team"]
    penalty_percent = item['penalty_percent']
    jail_hours = item['jail_hours']
    for member_uid in team:
        fine = await apply_smart_fine(cid, member_uid, penalty_percent)
        await send_to_jail(cid, member_uid, jail_hours)
        contraband_cooldowns[member_uid] = time.time() + CONTRABAND_COOLDOWN
        if item.get('seize_business'):
            try:
                async with pool.acquire() as conn:
                    biz = await conn.fetchrow("SELECT id FROM businesses WHERE chat_id=$1 AND user_id=$2 LIMIT 1", cid, member_uid)
                    if biz: await conn.execute("DELETE FROM businesses WHERE id=$1", biz['id'])
            except: pass
    del active_contraband_runs[run["id"]]
    seize_text = "🗑️ Изъят 1 бизнес\n" if item.get('seize_business') else ""
    await bot.send_message(cid, f"❌ <b>РЕЙС ПРОВАЛЕН!</b>\n\n📦 Товар: {item['name']}\n⚠️ Причина: {reason}\n\n🔒 Все в тюрьме на <b>{jail_hours} часов</b>\n💸 Штраф: <b>{penalty_percent}% баланса</b>\n{seize_text}⏰ Кулдаун: 6 часов", parse_mode="HTML")

# ═══════════════════════════════════════════
# МАФИЯ
# ═══════════════════════════════════════════
@dp.message(Command("pay_mafia"))
async def cmd_pay_mafia(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    async with pool.acquire() as conn:
        threat = await conn.fetchrow("SELECT * FROM mafia_threats WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE AND deadline > $3", cid, uid, time.time())
        if not threat: return await m.answer("❌ У вас нет активных угроз от мафии!")
        ransom = threat['ransom_amount']
    user = await get_user(cid, uid)
    bank = await get_bank(cid, uid)
    total_available = user['balance'] + bank['deposit']
    if total_available < ransom:
        return await m.answer(f"❌ Недостаточно средств!\nНужно: {fmt_money(ransom)}\nУ вас: {fmt_money(total_available)}\n\n🕴️ Мафия заберёт ваш актив через {format_time(int(threat['deadline'] - time.time()))}")
    paid_from_balance = min(ransom, user['balance'])
    remaining = ransom - paid_from_balance
    if paid_from_balance > 0: await update_balance(cid, uid, -paid_from_balance)
    if remaining > 0: await update_bank(cid, uid, -remaining)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE mafia_threats SET paid=TRUE WHERE id=$1", threat['id'])
    await m.answer(f"✅ <b>ВЫКУП ОПЛАЧЕН!</b>\n\n💰 Списано: <b>{fmt_money(ransom)}</b>\n🕴️ Мафия ушла довольной...\n\n💡 Совет: храните деньги в банке, чтобы снизить риск повторного визита!", parse_mode="HTML")
    new_achs = await check_achievements(cid, uid)
    await notify_achievements(cid, uid, new_achs)

@dp.message(Command("mafia_test"))
async def cmd_mafia_test(m: Message):
    if m.from_user.id not in ADMIN_IDS: return await m.answer("❌ Только для админов!")
    if not m.reply_to_message: return await m.answer("🕴️ Ответьте на сообщение игрока, чтобы вызвать мафию.")
    cid = m.chat.id
    uid = m.reply_to_message.from_user.id
    username = m.reply_to_message.from_user.full_name
    user = await get_user(cid, uid)
    bank = await get_bank(cid, uid)
    total_wealth = max(5000, user['balance'] + bank['deposit'])
    ransom = max(1000, int(total_wealth * 0.20))
    deadline = time.time() + 3600
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO mafia_threats (chat_id, user_id, threat_time, deadline, ransom_amount, threat_type, target_asset, paid) VALUES ($1, $2, $3, $4, $5, 'balance', 'balance', FALSE)", cid, uid, time.time(), deadline, ransom)
    msg = f"🕴️ <b>К ВАМ ПРИШЛА МАФИЯ!</b>\n\n👤 {username}, мы знаем о ваших доходах...\n\n💰 <b>Ваш капитал:</b> {fmt_money(total_wealth)}\n⚠️ <b>ТРЕБОВАНИЕ:</b> Переведите нам <b>{fmt_money(ransom)}</b> в течение <b>1 часа</b>\n\n🔫 <b>ИНАЧЕ ВАМ НЕ ПОЗДОРОВИТСЯ...</b>\n\n⏳ Время пошло..."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить выкуп", callback_data=f"pay_mafia_{uid}_{cid}")],
        [InlineKeyboardButton(text="🔫 Отказаться (риск)", callback_data=f"refuse_mafia_{uid}_{cid}")]
    ])
    await m.answer(msg, reply_markup=kb, parse_mode="HTML")

@dp.message(Command("mafia_execute"))
async def cmd_mafia_execute(m: Message):
    if m.from_user.id not in ADMIN_IDS: return await m.answer("❌ Только для админов!")
    await m.answer("⏳ Мафия проверяет должников...")
    await execute_mafia_threats()
    await m.answer("✅ Проверка завершена. Наказания применены.")

@dp.callback_query(lambda c: c.data.startswith("pay_mafia_"))
async def cb_pay_mafia(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    uid = int(parts[2])
    cid = int(parts[3])
    if cb.from_user.id != uid: return await cb.answer("❌ Это не ваша угроза!", show_alert=True)
    async with pool.acquire() as conn:
        threat = await conn.fetchrow("SELECT * FROM mafia_threats WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE", cid, uid)
        if not threat: return await cb.answer("❌ Угроза уже обработана!", show_alert=True)
        ransom = threat['ransom_amount']
    user = await get_user(cid, uid)
    bank = await get_bank(cid, uid)
    total_available = user['balance'] + bank['deposit']
    if total_available < ransom: return await cb.answer(f"❌ Недостаточно средств! Нужно: {fmt_money(ransom)}", show_alert=True)
    paid_from_balance = min(ransom, user['balance'])
    remaining = ransom - paid_from_balance
    if paid_from_balance > 0: await update_balance(cid, uid, -paid_from_balance)
    if remaining > 0 and bank['deposit'] > 0: await update_bank(cid, uid, -min(remaining, bank['deposit']))
    async with pool.acquire() as conn:
        await conn.execute("UPDATE mafia_threats SET paid=TRUE WHERE id=$1", threat['id'])
    msg = f"✅ <b>ВЫКУП ОПЛАЧЕН!</b>\n\n💰 Списано: <b>{fmt_money(ransom)}</b>\n🕴️ Мафия ушла довольной...\n\n💡 Совет: храните деньги в банке, чтобы снизить риск повторного визита!"
    try: await cb.message.edit_text(msg, parse_mode="HTML")
    except: await cb.message.answer(msg, parse_mode="HTML")
    await cb.answer("✅ Выкуп оплачен!")

@dp.callback_query(lambda c: c.data.startswith("refuse_mafia_"))
async def cb_refuse_mafia(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    uid = int(parts[2])
    cid = int(parts[3])
    if cb.from_user.id != uid: return await cb.answer("❌ Это не ваша угроза!", show_alert=True)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE mafia_threats SET paid=TRUE WHERE chat_id=$1 AND user_id=$2 AND paid=FALSE", cid, uid)
    username = cb.from_user.full_name
    user = await get_user(cid, uid)
    bank = await get_bank(cid, uid)
    total_wealth = user['balance'] + bank['deposit']
    roll = random.random()
    if roll < 0.20:
        msg = f"🕊️ <b>МАФИЯ УШЛА НИ С ЧЕМ!</b>\n\n👤 {username}, вы отказались платить, но мафия решила не трогать вас.\n\n🍀 Вам повезло! Но в следующий раз лучше платить вовремя."
    else:
        async with pool.acquire() as conn:
            businesses = await conn.fetch("SELECT business_name FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
            cars = await conn.fetch("SELECT car_name FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
            profile = await conn.fetchrow("SELECT job_key, level FROM profiles WHERE chat_id=$1 AND user_id=$2", cid, uid)
            if businesses:
                target_biz = random.choice(businesses)['business_name']
                await conn.execute("DELETE FROM businesses WHERE chat_id=$1 AND user_id=$2 AND business_name=$3", cid, uid, target_biz)
                msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ВАШ БИЗНЕС!</b>\n\n👤 {username}, вы отказались платить.\n🏢 Конфискован: <b>{target_biz}</b>"
            elif cars:
                target_car = random.choice(cars)['car_name']
                await conn.execute("DELETE FROM garage WHERE chat_id=$1 AND user_id=$2 AND car_name=$3", cid, uid, target_car)
                msg = f"🔫 <b>МАФИЯ УКРАЛА ВАШУ МАШИНУ!</b>\n\n👤 {username}, вы отказались платить.\n🚗 Украдена: <b>{target_car}</b>"
            elif profile and profile['level'] > 1:
                old_job = profile['job_key']
                old_level = profile['level']
                await conn.execute("UPDATE profiles SET job_key='novice', level=1 WHERE chat_id=$1 AND user_id=$2", cid, uid)
                msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ВАШУ ПРОФЕССИЮ!</b>\n\n👤 {username}, вы отказались платить.\n💼 Сброшено: <b>{old_job} Ур.{old_level}</b> → Новичок Ур.1"
            else:
                penalty = int(total_wealth * 0.30)
                paid_from_balance = min(penalty, user['balance'])
                remaining = penalty - paid_from_balance
                if paid_from_balance > 0: await update_balance(cid, uid, -paid_from_balance)
                if remaining > 0 and bank['deposit'] > 0: await update_bank(cid, uid, -min(remaining, bank['deposit']))
                msg = f"🔫 <b>МАФИЯ ЗАБРАЛА ДЕНЬГИ!</b>\n\n👤 {username}, вы отказались платить.\n💸 Списано: <b>{fmt_money(penalty)}</b> (30% от капитала)"
    try: await cb.message.edit_text(msg, parse_mode="HTML")
    except: await cb.message.answer(msg, parse_mode="HTML")
    await cb.answer()

# ═══════════════════════════════════════════
# РУССКАЯ РУЛЕТКА
# ═══════════════════════════════════════════
@dp.message(Command("roulette"))
async def cmd_roulette(m: Message, state: FSMContext):
    cid, uid = m.chat.id, m.from_user.id
    if await is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя играть!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("🔫 <b>Русская рулетка</b>\n\nИспользование: <b>/roulette ставка</b>\n\nМинимум: 100 сарапулок\nИгроков: 2-6\nШанс выжить: 83%\n\nПобедитель забирает весь банк!", parse_mode="HTML")
    try: bet = int(args[1])
    except: return await m.answer("❌ Число!")
    if bet < 100: return await m.answer("❌ Минимальная ставка: 100")
    user = await get_user(cid, uid)
    if user['balance'] < bet: return await m.answer(f"❌ Мало ({fmt_money(user['balance'])})")
    if cid in ROULETTE_TABLES: return await m.answer("🔫 Игра уже идёт!")
    ROULETTE_TABLES[cid] = {"players": {uid: {"name": m.from_user.first_name, "bet": bet, "alive": True}}, "order": [uid], "stage": "waiting", "creator": uid, "bank": 0}
    await update_balance(cid, uid, -bet)
    ROULETTE_TABLES[cid]["bank"] = bet
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔫 Присоединиться", callback_data=f"roulette_join_{cid}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"roulette_cancel_{cid}")]
    ])
    await m.answer(f"🔫 <b>Русская рулетка!</b>\n\n👤 {m.from_user.first_name}\n💰 Ставка: {fmt_money(bet)}\n👥 1/{ROULETTE_MAX_PLAYERS}\n⏳ {ROULETTE_WAIT_TIME} сек\n\nНажмите кнопку!", reply_markup=kb, parse_mode="HTML")
    await state.set_state(BlackjackStates.waiting)
    await asyncio.sleep(ROULETTE_WAIT_TIME)
    if cid not in ROULETTE_TABLES: return
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
    if cid not in ROULETTE_TABLES: return await cb.answer("Игра завершена!", show_alert=True)
    table = ROULETTE_TABLES[cid]
    if table["stage"] != "waiting": return await cb.answer("Игра началась!", show_alert=True)
    if uid in table["players"]: return await cb.answer("Вы уже участвуете!", show_alert=True)
    if len(table["players"]) >= ROULETTE_MAX_PLAYERS: return await cb.answer("Мест нет!", show_alert=True)
    user = await get_user(cid, uid)
    bet = table["players"][table["order"][0]]["bet"]
    if user['balance'] < bet: return await cb.answer(f"❌ Нужно {fmt_money(bet)}", show_alert=True)
    await update_balance(cid, uid, -bet)
    table["players"][uid] = {"name": cb.from_user.first_name, "bet": bet, "alive": True}
    table["order"].append(uid)
    table["bank"] += bet
    await cb.answer("✅ Вы участвуете!")
    pl = "\n".join([f"• {p['name']}" for p in table["players"].values()])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔫 Присоединиться", callback_data=f"roulette_join_{cid}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"roulette_cancel_{cid}")]
    ])
    try:
        await cb.message.edit_text(f"🔫 <b>Русская рулетка!</b>\n\nИгроки ({len(table['players'])}/{ROULETTE_MAX_PLAYERS}):\n{pl}\n\n💰 Банк: {fmt_money(table['bank'])}\n⏳ Ждём...", reply_markup=kb, parse_mode="HTML")
    except: pass

@dp.callback_query(lambda c: c.data.startswith("roulette_cancel_"))
async def roulette_cancel(cb: types.CallbackQuery, state: FSMContext):
    cid = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    if cid not in ROULETTE_TABLES: return await cb.answer("Игра завершена!", show_alert=True)
    table = ROULETTE_TABLES[cid]
    if uid != table["creator"]: return await cb.answer("Только создатель!", show_alert=True)
    if table["stage"] == "playing": return await cb.answer("Игра началась!", show_alert=True)
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
        if next_player: await roulette_turn(cid, next_player, state)
        else: await roulette_end(cid, state)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔫 Стрелять!", callback_data=f"roulette_shoot_{uid}_{cid}")]])
    await bot.send_message(uid, f"🔫 <b>Ваш ход!</b>\n\nНажмите кнопку, чтобы выстрелить в себя.\nШанс выжить: 83%\n\n💰 Банк: {fmt_money(table['bank'])}", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith("roulette_shoot_"))
async def roulette_shoot(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split("_")
    uid = int(parts[2])
    cid = int(parts[3])
    if cid not in ROULETTE_TABLES: return await cb.answer("Игра завершена!", show_alert=True)
    table = ROULETTE_TABLES[cid]
    if uid != cb.from_user.id: return await cb.answer("Не ваш ход!", show_alert=True)
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
        await bot.send_message(cid, f"🏆 <b>ПОБЕДИТЕЛЬ!</b>\n\n👤 {table['players'][winner_uid]['name']}\n💰 Забирает: <b>{fmt_money(winner_share)}</b>\n\n🔫 Игра окончена!", parse_mode="HTML")
    else:
        for uid in winners:
            await update_balance(cid, uid, table["players"][uid]["bet"])
        await bot.send_message(cid, f"🤝 <b>НИЧЬЯ!</b>\n\nВыжившие: {', '.join([table['players'][u]['name'] for u in winners])}\nСтавки возвращены.\n\n🔫 Игра окончена!", parse_mode="HTML")
    del ROULETTE_TABLES[cid]
    await state.clear()

# ═══════════════════════════════════════════
# БЛЭКДЖЕК
# ═══════════════════════════════════════════
def create_deck():
    suits = ['♠', '♥', '♦', '♣']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    deck = [(r, s) for s in suits for r in ranks]
    random.shuffle(deck)
    return deck

def card_value(card):
    r = card[0]
    if r in ['J', 'Q', 'K']: return 10
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
    if hide_first: return f"🂠 + {' '.join(f'{r}{s}' for r,s in cards[1:])}"
    return ' '.join(f'{r}{s}' for r,s in cards)

@dp.message(Command("blackjack"))
async def blackjack_start(m: Message, state: FSMContext):
    cid, uid = m.chat.id, m.from_user.id
    if cid in bj_tables: return await m.answer("🎰 Игра идёт!")
    u = await get_user(cid, uid)
    if u['balance'] < BJ_MIN_BALANCE: return await m.answer(f"❌ Нужно {BJ_MIN_BALANCE}+ ({fmt_money(u['balance'])})")
    bj_tables[cid] = {"players": {uid: {"name": m.from_user.first_name, "bet": 0, "cards": [], "stand": False, "busted": False}}, "order": [uid], "stage": "waiting", "creator": uid}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"bj_join_{cid}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"bj_cancel_{cid}")]
    ])
    await m.answer(f"🎩 <b>Игорёчек открывает стол!</b>\n\n👤 {m.from_user.first_name}\n👥 1/{BJ_MAX_PLAYERS}\n⏳ {BJ_WAIT_TIME} сек\n\nНажмите кнопку!", reply_markup=kb, parse_mode="HTML")
    await state.set_state(BlackjackStates.waiting)
    await asyncio.sleep(BJ_WAIT_TIME)
    if cid not in bj_tables: return
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
        try: await bot.send_message(uid, f"🎩 <b>Ваша ставка?</b>", reply_markup=bk, parse_mode="HTML")
        except: await m.answer(f"⚠️ {t['players'][uid]['name']}, напишите в ЛС!")
    await m.answer(f"🎩 <b>Игроки:</b> {pl}\n\n💰 Проверьте личку!", parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith("bj_join_"))
async def blackjack_join(cb: types.CallbackQuery, state: FSMContext):
    cid = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    if cid not in bj_tables: return await cb.answer("Стол закрыт!", show_alert=True)
    t = bj_tables[cid]
    if t["stage"] != "waiting": return await cb.answer("Началась!", show_alert=True)
    if uid in t["players"]: return await cb.answer("Вы уже тут!", show_alert=True)
    if len(t["players"]) >= BJ_MAX_PLAYERS: return await cb.answer("Мест нет!", show_alert=True)
    u = await get_user(cid, uid)
    if u['balance'] < BJ_MIN_BALANCE: return await cb.answer(f"❌ Нужно {BJ_MIN_BALANCE}+", show_alert=True)
    t["players"][uid] = {"name": cb.from_user.first_name, "bet": 0, "cards": [], "stand": False, "busted": False}
    t["order"].append(uid)
    await cb.answer("✅ Присоединились!")
    pl = "\n".join([f"• {p['name']}" for p in t["players"].values()])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"bj_join_{cid}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"bj_cancel_{cid}")]
    ])
    try: await cb.message.edit_text(f"🎩 <b>Игроки ({len(t['players'])}/{BJ_MAX_PLAYERS}):\n{pl}\n\n⏳ Ждём...</b>", reply_markup=kb, parse_mode="HTML")
    except: pass

@dp.callback_query(lambda c: c.data.startswith("bj_cancel_"))
async def blackjack_cancel(cb: types.CallbackQuery, state: FSMContext):
    cid = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    if cid not in bj_tables: return await cb.answer("Завершена!", show_alert=True)
    t = bj_tables[cid]
    if uid != t["creator"]: return await cb.answer("Только создатель!", show_alert=True)
    if t["stage"] == "playing": return await cb.answer("Игра началась!", show_alert=True)
    refunded = []
    for pid, pd in t["players"].items():
        if pd["bet"] > 0:
            await update_balance(cid, pid, pd["bet"])
            refunded.append(f"• {pd['name']}: +{fmt_money(pd['bet'])}")
    del bj_tables[cid]
    await state.clear()
    rt = "\n".join(refunded) if refunded else "Никто не поставил"
    try: await cb.message.edit_text(f"❌ <b>Отменена!</b>\n\n👤 {cb.from_user.first_name}\n\n💰 Возврат:\n{rt}", parse_mode="HTML")
    except: pass
    await cb.answer("✅ Отменена!")

@dp.callback_query(lambda c: c.data.startswith("bet_"))
async def blackjack_bet(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split("_")
    bet = int(parts[1])
    cid = int(parts[2])
    uid = cb.from_user.id
    if cid not in bj_tables: return await cb.answer("Нет игры!", show_alert=True)
    t = bj_tables[cid]
    if uid not in t["players"]: return await cb.answer("Не в игре!", show_alert=True)
    if t["players"][uid]["bet"] > 0: return await cb.answer("Ставка есть!", show_alert=True)
    u = await get_user(cid, uid)
    if u['balance'] < bet: return await cb.answer(f"❌ Мало ({fmt_money(u['balance'])})", show_alert=True)
    await update_balance(cid, uid, -bet)
    t["players"][uid]["bet"] = bet
    try: await cb.message.edit_text(f"✅ Ставка: <b>{bet}</b>. Ждём...", parse_mode="HTML")
    except: pass
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
    if cid not in bj_tables: return await cb.answer("Нет игры!", show_alert=True)
    t = bj_tables[cid]
    p = t["players"][uid]
    if act == "hit":
        c = t["deck"].pop()
        p["cards"].append(c)
        sc = calc_score(p["cards"])
        await cb.message.edit_text(f"🃏 Взял карту!\n\n🃏 +{c[0]}{c[1]}\n📊 {show_cards(p['cards'])}\n🔢 Сумма: <b>{sc}</b>", parse_mode="HTML")
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
                [InlineKeyboardButton(text="🃏 Ещё", callback_data=f"hit_{uid}_{cid}"), InlineKeyboardButton(text="✋ Хватит", callback_data=f"stand_{uid}_{cid}")]
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
        if p["busted"]: res.append(f"❌ {p['name']}: перебор ({ps})")
        elif ds > 21:
            await update_balance(cid, uid, bet * 2)
            res.append(f"🎉 {p['name']}: Игорёчек перебрал! +{bet}")
        elif ps > ds:
            await update_balance(cid, uid, bet * 2)
            res.append(f"🏆 {p['name']}: победа! +{bet}")
        elif ps == ds:
            await update_balance(cid, uid, bet)
            res.append(f"🤝 {p['name']}: ничья")
        else: res.append(f"😢 {p['name']}: проигрыш")
    if ds > 21: fn = "😱 Перебрал!"
    elif any("победа" in r for r in res): fn = "🎉 Поздравляем!"
    elif any("проигрыш" in r for r in res): fn = "🎩 Забирает ставки!"
    else: fn = "🤝 Ничья!"
    await bot.send_message(cid, f"🎩 <b>{fn}</b>\n\n🤖 Карты: {show_cards(t['dealer'])} ({ds})\n\n📋 Результаты:\n" + "\n".join(res), parse_mode="HTML")
    del bj_tables[cid]
    await state.clear()

# ═══════════════════════════════════════════
# АВТО-РЕГИСТРАЦИЯ
# ═══════════════════════════════════════════
@dp.message()
async def auto_register(m: Message):
    if m.chat.type not in ['group', 'supergroup']: return
    await get_user(m.chat.id, m.from_user.id)

@dp.message(F.new_chat_members)
async def on_user_join(m: Message):
    cid = m.chat.id
    for user in m.new_chat_members:
        if user.is_bot:
            if user.id == int(API_TOKEN.split(':')[0]): await m.answer("👋 Привет! Я экономический бот. /start")
            continue
        await get_user(cid, user.id)
        await save_username(cid, user.id, user.full_name)

# ═══════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════
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
    asyncio.create_task(federal_expenses_loop())
    asyncio.create_task(city_expenses_loop())
    asyncio.create_task(check_overdue_projects())
    asyncio.create_task(mafia_check_loop())
    asyncio.create_task(mafia_threat_loop())
    asyncio.create_task(stock_market_loop())
    asyncio.create_task(stock_dividend_loop())
    asyncio.create_task(auction_check_loop())
    print("🎰 Лотерея")
    print("💳 Кредиты")
    print("⚖️ Штрафы")
    print("🕵️ Долги")
    print("🏛️ Выборы")
    print("💰 Федеральные расходы")
    print("🏙️ Городские расходы")
    print("⏰ Проекты мэров")
    print("🕴️ Мафия")
    print("📈 Биржа")
    print("🏆 Аукцион")
    await init_cities()
    print("🏙️ Города")
    await dp.start_polling(bot, timeout=30, drop_pending_updates=True, allowed_updates=["message", "callback_query", "my_chat_member"])

if __name__ == "__main__":
    asyncio.run(main())
