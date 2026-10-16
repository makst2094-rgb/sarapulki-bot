# ============================================================================
# 🤖 ЭКОНО весь `bot.py`:**

```python
# ============================================================================
# 🤖 ЭКОНОМИЧЕСКИЙ БОТ ДЛЯ TELEGRAM ГРУПП - ВЕРСИЯ 10.0 FULL
# ============================================================================
# Название: Сарапулки Economy Bot
# Версия: 10.0 Full Edition
МИЧЕСКИЙ БОТ ДЛЯ TELEGRAM ГРУПП - ВЕРСИЯ 10.0 FULL
# ============================================================================
# Название: Сарапулки Economy Bot
# Описание: Полноценная экономическая система с# Версия: 10.0 Full Edition
 изоляцией групп.
# Каждый чат имеет свою# Описание: Полноценная экономическая система с изоляцией групп.
# Каждый чат имеет свою независимую экономику.
# Основные функции:
# - Работа и профессии с системой образования
# - Бан независимую экономику.
# Основные функции:
# - Работа и профессии с системой образования
# - Банковская система с процентами (1% в сутки)
# - Блэкджек с Игорёчкомковская система с процентами (1% в сутки) (2-5 игроков, кнопки, отмена игры)
# - Система кредитов с арестом имущества при
# - Блэкджек с Игорёчком (2-5 игроков, кнопки, отмена игры) просрочке
# - Крафт предметов (А
# - Система кредитов с арестом имущества прилмаз, Золотая Скрипка)
 просрочке
# - Крафт предметов (А# - Трейд между игроками
# - Авто-лмаз, Золотая Скрипка)
лотерея каждые 12 часов
# - # - Трейд между игроками
# - Авто-5 бизнесов с окупаемостью 6 дней (можно покупать одинаковые)
# - Автосаллотерея каждые 12 часов
# - он (5 машин, можно покупать одинаковые)
#5 бизнесов с окупаемостью 6 дней (можно покупать одинаковые)
# - Автосал - Инвентарь и предметы с редкостью
он (5 машин, можно покупать одинаковые)
## - Рейтинг богачей
# - Ежедневные - Инвентарь и предметы с редкостью
 бонусы с множителем за серию
# - Ограбления (40% шанс успеха)
# - Игровые кости (5# - Рейтинг богачей
# - Ежедневные0/50)
# ============================================================================

import asyncio
import logging
import random
import time
import os

from aiogram import Bot, Dispatcher, types, F бонусы с множителем за серию
# - Ограбления (40% шанс успеха)
# - Игровые кости (50/50)
# ============================================================================

import asyncio
import logging
import random
import time
import os
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncpg


from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncpg
from aiohttp import web

# ==================== НАСТРОЙКИ БОТА ====================
API_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [from aiohttp import web

# ==================== НАСТРОЙКИ БОТА ====================
API_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]
DATABASE_URL = os.environ.get("DATABASE_URL", "")

logging.basicConfig(level=logging.INFO, format='int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]
DATABASE_URL = os.environ.get("DATABASE_URL", "")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
storage =%(asctime)s - %(name)s - %(levelname)s - MemoryStorage()
dp = Dispatcher(storage=storage)
pool = None

# ==================== СОСТОЯНИЯ %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
 FSM ====================
class BlackjackStates(StatesGroup):
pool = None

# ==================== СОСТОЯНИЯ    waiting = State()
    betting = State()
    playing = State()

bj_tables = {}
 FSM ====================
class BlackjackStates(StatesGroup):
    waiting = State()
    betting = State()
    playing = State()

bj_tables = {}
exam_sessions = {}

# ==================== РЕЦЕПexam_sessions = {}

# ==================== РЕЦЕПТЫ КРАФТА ====================
CRAFT_RECIPES = {
    "diamond": {"name": "💎 Алмаз", "requires": {" Бумага": 10}, "rarity": "rare"},
    "scriptka": {"name": "🎸 Золотая Скрипка", "requires": {"💎 Алмаз": 5}, "rarity": "legendary"}
}

# ==================== НАСТРОЙКИ ЭКОТЫ КРАФТА ====================
CRAFT_RECIPНОМИКИ ====================
LOTTERY_PRICE =ES = {
    "diamond": {"name": "💎 Алмаз", "requires": {" Бумага": 10}, "rarity": "rare"},
    "scriptka": {"name": "🎸 Золотая Скрипка", "requires": {"💎 Алмаз": 5}, "rarity": "legendary"}
}

# ==================== НАСТРОЙКИ ЭКОНОМИКИ ====================
LOTTERY_PRICE = 50
LOTTERY_INTERVAL = 12 50
LOTTERY_INTERVAL = 12 * 3600
BANK_INTEREST_RATE = 0.01
CREDIT_MULTIPLIER = 10
CREDIT_DAILY_RATE = 0 * 3600
BANK_INTEREST_RATE = 0.01
CREDIT_MULTIPLIER = 10
CREDIT_DAILY_RATE = 0.02
CREDIT_TERM_DAYS = 7
.02
CREDIT_TERM_DAYS = 7
ROB_SUCCESS_RATE = 0.4
ROB_COOLDOWN = 10800
ROROB_SUCCESS_RATE = 0.4
ROBB_MIN_PERCENT = 0.1
ROB_MAX_COOLDOWN = 10800
RO_PERCENT = 0.5
ROB_PENALB_MIN_PERCENT = 0.1
ROB_MAX_PERCENT = 0.5
ROB_PENALTY_RATE = 0.2
DICE_MIN_BET = 10
DICE_WIN_THRESHOLD = 4
DICE_WIN_MULTIPLIER = 2
BJTY_RATE = 0.2
DICE_MIN_BET = 10
DICE_WIN_THRESHOLD = 4
DICE_WIN_MULTIPLIER = 2
BJ_MIN_BALANCE = 100
BJ_MAX_PLAYERS = 5
BJ_WAIT_TIME = 60_MIN_BALANCE = 100
BJ_MAX_PLAY
BJ_DEALER_STOP = 17

# =================ERS = 5
BJ_WAIT_TIME = 60
BJ_DEALER_STOP = 17

# ==================== КУРСЫ ОБРАЗОВАНИЯ ====================
C=== КУРСЫ ОБРАЗОВАНИЯ ====================
COURSES = {
    "miner": {
        "name": "📘 Курс шахтёра",OURSES = {
    "miner": {
        "price": 200, "required_for": "name": "📘 Курс шахтёра", "price": 200, "required_for": "miner",
        "questions": [
            {" "miner",
        "questions": [
            {"q": "Что нужно надевать в шахте?", "a": ["каска", "шлем", "заq": "Что нужно надевать в шахте?", "щита"], "correct": 0},
            {"q": "Сколько тонн весит вагонетка?", "a": ["1", "5", "1a": ["каска", "шлем", "защита"], "correct": 0},
            {"q": "Сколько тонн весит вагонетка0"], "correct": 1},
            {"q?", "a": ["1", "5", "1": "Главный инструмент шахтёра?", "a": ["лопата", "отбойный молот0"], "correct": 1},
            {"q": "Главный инструмент шахтёра?", "a": ["лопата", "отбойный молоток", "кирка"], "correct": 2}
        ]
    },
    "coder": {
        "name": "💻 Курс программирования", "price": 1000, "requiredок", "кирка"], "correct": 2}
        ]
    },
    "coder": {
        "name": "💻 Курс программирования", "price": 1000, "required_for": "coder",
        "questions": [
            {"q": "Язык для веб-разработки?", "a": ["Python", "HTML", "C++"], "correct": 1},
            {"q": "Что такое баг?", "a": ["ошибка", "функция", "переменная"], "correct": 0},
            {"q": "Сколько бит в байте?", "a": ["4_for": "coder",
        "questions": [
            {"q": "Язык для веб-разработки?", "a": ["Python", "HTML", "C++"], "correct": 1},
            {"q": "Что такое баг?", "a": ["ошибка", "функция", "переменная"], "correct": 0},
            {"q": "Сколько бит в байте?", "a": ["4", "8", "16"], "correct": 1}
        ]
    },
    "tr", "8", "16"], "correct": 1}
        ]
    },
    "trader": {
        "name": "📈 Курс трейдинга", "price": 300ader": {
        "name": "📈 Курс трейдинга", "price": 3000, "required_for": "trader",
        "questions": [
            {"q": "Что такое бычий рынок?", "a": ["рост", "падение", "стабильность"], "correct":0, "required_for": "trader",
        "questions": [
            {"q": "Что такое бычий рынок?", "a": ["рост", " 0},
            {"q": "Диверпадение", "стабильность"], "correct":сификация это?", "a": ["риск", "распределение", "прибыль"], "correct": 1},
            {"q": "Л 0},
            {"q": "Диверсификация это?", "a": ["риск", "распределение", "прибыль"], "correct": 1},
            {"q": "Ликвидность актива?", "a": ["скорость продажииквидность актива?", "a": ["скорость продажи", "цена", "объём"], "correct": 0}
        ]
    },
    "", "цена", "объём"], "correct": 0}
        ]
    },
    "mba": {
        "name": "mba": {
        "name": " MBA", "price": 10000 MBA", "price": 10000, "required_for": None,
        "questions":, "required_for": None,
        "questions": [
            {"q": "ROI это?", "a [
            {"q": "ROI это?", "a": ["возврат инвестиций", "риск", "доход"], "correct": 0},
            {"": ["возврат инвестиций", "риск", "доход"], "correct": 0},
            {"q": "EBITDA показывает?", "a": ["прибыль", "убыток", "оборот"], "correct": 0},
            {"q": "Стратегия роста?", "a": ["сокращq": "EBITDA показывает?", "a": ["ение", "инвестиции", "стагнация"],прибыль", "убыток", "оборот"], "correct": 0},
            {"q": "Стратегия роста?", "a": ["сокращение", "инвестиции", "стагнация"], "correct": 1}
        ]
    "correct": 1}
        ]
    }
}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def pluralize(n, forms):
    n = abs(n) % 100
    n1 = n % 10
    if n > 10 and n < 20: return forms[2]
    }
}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def pluralize(n, forms):
    n = abs(n) % 100
    n1 = n % 10
    if n > 10 and n if n1 > 1 and n1 < 5 < 20: return forms[2]
   : return forms[1]
    if n1 == 1: return forms[0]
    return forms[2]

def fmt_money(amount):
    return f"{amount} {pluralize(amount, ['сара if n1 > 1 and n1 < 5: return forms[1]
    if n1 == 1: return forms[0]
    return forms[2]

def fmt_money(amount):
    return f"{amount} {pluralize(amount, ['сарапулка', 'сарапулки', 'сарапулка', 'сарапулки', 'сарапулок'])}"

def format_time(seconds):
пулок'])}"

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours} ч {minutes} мин" if hours > 0 else f"{minutes} мин"

def format_date(timestamp):
    return time.strftime('%d.%m.%Y', time.localtime(timestamp))

# ==================== КОНФИГУРАЦИЯ РАБОТЫ И РЫ    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours} ч {minutes} мин" if hours > 0 else f"{minutes} мин"

def format_date(timestamp):
    return time.strftime('%d.%m.%Y', time.localtime(timestamp))

# ==================== КОНФИГУРАЦИЯ РАБОТЫ И РЫНКА ====================
JOBS = {
   НКА ====================
JOBS = {
    "novice": {"name": "👶 Новичок", "base_pay": 10, "cooldown": 3600},
    "miner "novice": {"name": "👶 Нов": {"name": "⛏️ Шахтёр", "base_pay": 25, "cooldownичок", "base_pay": 10, "cooldown": 3600},
    "miner": {"name": "⛏️ Шахт": 3600},
    "coder":ёр", "base_pay": 25, "cooldown": 3600},
    "coder": {"name": "💻 Программист", "base_pay": 50, "cooldown": 72 {"name": "💻 Программист", "base00},
    "trader": {"name":_pay": 50, "cooldown": 72 "📈 Трейдер", "base_pay":00},
    "trader": {"name": "📈 Трейдер", "base_pay": 80, "cooldown": 1080 80, "cooldown": 10800}
}

SHOP_ITEMS = {
    "course": {"name": "📚 Курсы", "price": 500, "desc": "+1 уровень", "type": "level_up"},
   0}
}

SHOP_ITEMS = {
    "course": {"name": "📚 Курсы", "price": 500, "desc": "+1 уровень", "type": "level_up"},
    "coffee": {"name": "☕ Кофе-машина", "price": 1000, "coffee": {"name": "☕ Кофе- "desc": "-10% кулдаун", "машина", "price": 1000,type": "cooldown_reduce"}
}

# Бизнес "desc": "-10% кулдаун", "ы с окупаемостью ровно 6 дней (доход = цена / 6)
MARKtype": "cooldown_reduce"}
}

# БизнесET = {
    "case_basic": {"name":ы с окупаемостью ровно 6 дней "📦 Кейс", "price": 2 (доход = цена / 6)
MARKET = {
    "case_basic": {"name":00, "type": "case"},
    "biz_newspaper": {"name": "📰 "📦 Кейс", "price": 2 Газетный киоск", "price": 500, "type": "case"},
    "00, "type": "business", "income":biz_newspaper": {"name": "📰 85},
    "biz_shawarma": Газетный киоск", "price": 500, "type": "business", "income": {"name": "🌯 Шаурма", " 85},
    "biz_shawarma":price": 2000, "type": " {"name": "🌯 Шаурма", "price": 2000, "type": "business", "income": 335},
    "biz_coffee": {"name": "☕ Кофейня", "price": 5000, "type": "business", "income": 835},
    "biz_crypto": {"name": "💻 Крипто-ферма", "price": 15000, "type": "business", "income": 2500},
    "business", "income": 335},
    "biz_coffee": {"name": "☕ Кофейня", "price": 5000, "type": "business", "income": 835},
    "biz_crypto": {"name": "💻 Крипто-ферма", "price": 15000, "type": "business", "income": 2500},
    "biz_hotel": {"name": "🏨 Отель", "price": 50000, "biz_hotel": {"name": "🏨 Отель", "price": 50000, "type": "business", "income": 8335}
}

CARS = {
    "ok": {"name": "🚲 Ока", "price": 3000},
    "priora": {"name": "🚘 Приора", "price": 10000},
    "bmw": {"name": "🏎️ BMW", "price": 40000},
    "gelik": {"name": " Гелик", "price": 80000},
    "lambo": {"name": "🏎️ Lamborghini", "price": 200000}
}

# ==================== БАЗА ДАННЫХ ====================
async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10, command_timeout=3type": "business", "income": 8335}
}

CARS = {
    "ok": {"name": "🚲 Ока", "price": 3000},
    "priora": {"name": "🚘 Приора", "price": 10000},
    "bmw": {"name": "🏎️ BMW", "price": 40000},
    "gelik": {"name": " Гелик", "price": 80000},
    "lambo": {"name": "🏎️ Lamborghini", "price": 200000}
}

# ==================== БАЗА ДАННЫХ ====================
async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10, command_timeout=30)
    async with pool.acquire() as conn:
        await conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id BIGINT, user_id BIGINT, balance0)
    async with pool.acquire() as conn:
        await conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id BIGINT, user_id BIGINT, balance INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE IF INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user NOT EXISTS profiles (chat_id BIGINT, user_id BIGINT, job_key TEXT DEFAULT 'novice', level INTEGER DEFAULT 1, last_work_time REAL DEFAULT 0, has_coffee BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE IF NOT EXISTS inventory (id SERIAL PRIMARY KEY, chat_id))")
        await conn.execute("CREATE TABLE IF NOT EXISTS profiles (chat_id BIGINT, user_id BIGINT, job_key TEXT DEFAULT 'novice', level INTEGER DEFAULT 1, last_work_time REAL DEFAULT 0, has_coffee BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id_id BIGINT, user_id BIGINT, item_name TEXT, user_id))")
        await conn.execute("CREATE, item_type TEXT, rarity TEXT DEFAULT 'common')") TABLE IF NOT EXISTS inventory (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, item_name TEXT
        # id SERIAL PRIMARY KEY позволяет покупать несколько, item_type TEXT, rarity TEXT DEFAULT 'common')") одинаковых бизнесов и машин
        await conn.execute("
        # id SERIAL PRIMARY KEY позволяет покупать несколькоCREATE TABLE IF NOT EXISTS businesses (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, business_name одинаковых бизнесов и машин
        await conn.execute(" TEXT, income INTEGER, last_collect_time REAL DEFAULT 0CREATE TABLE IF NOT EXISTS businesses (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, business_name)")
        await conn.execute("CREATE TABLE IF NOT EXISTS TEXT, income INTEGER, last_collect_time REAL DEFAULT 0)")
        await conn.execute("CREATE TABLE IF NOT EXISTS garage (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, car_key TEXT, car_name TEXT garage (id SERIAL PRIMARY KEY, chat_id BIGINT,)")
        await conn.execute("CREATE TABLE IF NOT EXISTS daily_bonus (chat_id BIGINT, user_id BIG user_id BIGINT, car_key TEXT, car_name TEXT)")
        await conn.execute("CREATE TABLE IF NOT EXISTS daily_bonus (chat_id BIGINT, user_id BIGINT, last_claim REAL DEFAULT 0, streak INTEGER DEFAULTINT, last_claim REAL DEFAULT 0, streak INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id)) 0, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE IF NOT EXISTS")
        await conn.execute("CREATE TABLE IF NOT EXISTS robbery (chat_id BIGINT, user_id BIGINT, last_robbery REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))")
        await robbery (chat_id BIGINT, user_id BIGINT, last_robbery REAL DEFAULT 0, PRIMARY conn.execute("CREATE TABLE IF NOT EXISTS lottery_tickets (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIG KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE IF NOT EXISTS lottery_tickets (id SERIAL PRIMARY KEY, chat_id BIGINT, user_id BIGINT, buy_time REAL)")
        await conn.execute("INT, buy_time REAL)")
        await conn.execute("CREATE TABLE IF NOT EXISTS usernames (chat_id BIGINT, user_id BIGINT, username TEXT, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE IF NOT EXISTS bank (chat_id BIGINT,CREATE TABLE IF NOT EXISTS usernames (chat_id BIGINT, user_id BIGINT, username TEXT, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE IF NOT EXISTS bank (chat_id BIGINT, user_id BIGINT, deposit INTEGER DEFAULT 0, last_interest_time REAL DEFAULT 0, PRIMARY KEY (chat_id user_id BIGINT, deposit INTEGER DEFAULT 0, last, user_id))")
        await conn.execute("CREATE_interest_time REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE IF NOT EXISTS education (chat_id BIGINT, user_id BIGINT, completed_courses TEXT[] DEFAULT '{}', has_mba BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE IF NOT EXISTS loans (chat_id BIGINT, TABLE IF NOT EXISTS education (chat_id BIGINT, user_id BIGINT, completed_courses TEXT[] DEFAULT '{}', has_mba BOOLEAN DEFAULT FALSE, PRIMARY KEY (chat_id, user_id))")
        await conn.execute("CREATE TABLE IF NOT EXISTS loans (chat_id BIGINT, user_id BIGINT, amount INTEGER DEFAULT 0, interest INTEGER DEFAULT 0, taken_at REAL DEFAULT 0, due_date REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))")
    logger.info("✅ База данных готова")

async def save_username(cid, uid, name):
    async with pool.acquire() as conn user_id BIGINT, amount INTEGER DEFAULT 0, interest INTEGER DEFAULT 0, taken_at REAL DEFAULT 0, due_date REAL DEFAULT 0, PRIMARY KEY (chat_id, user_id))")
    logger.info("✅ База данных готова")

async def save_username(cid, uid, name):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO usernames VALUES (<LaTex>id_1</LaTex>1,<LaTex>id_2</LaTex>3) ON CONFLICT DO UPDATE SET username=<LaTex>id_3</LaTex>1 AND user_id=<LaTex>id_4</LaTex>1,<LaTex>id_5</LaTex>2,<LaTex>id_6</LaTex>3", cid, uid, name)

async def get_user(cid, uid):
    async with pool.acquire() as conn:
        b = await conn.fetchval("SELECT balance FROM users WHERE chat_id=<LaTex>id_7</LaTex>2", cid, uid)
        if b is not None: return {"balance": b}
        await conn.execute("INSERT INTO users VALUES (<LaTex>id_8</LaTex>balance": 0}

async def update_balance(cid,2,0)", cid, uid)
        return {"balance": 0}

async def update_balance(cid, uid, amt):
    async with pool.acquire() as uid, amt):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET balance conn:
        await conn.execute("UPDATE users SET balance=balance+<LaTex>id_9</LaTex>2 AND user_id=balance+<LaTex>id_10</LaTex>2 AND user_id=<LaTex>id_11</LaTex>1 AND user_id=<LaTex>id_12</LaTex>3", amt, cid, uid)

async def r:
            await conn.execute("INSERT INTO profiles VALUES get_profile(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT * FROM profiles WHERE chat_id=<LaTex>id_13</LaTex>2", cid, uid)
        if not r:
            await conn.execute("INSERT INTO profiles VALUES (<LaTex>id_14</LaTex>2,'novice',1,0,FALSE)", cid, uid)
            return {"job_key": "novice", "level": 1, "last_work_time": 0, "has_coffee": False}
        return dict(r)

async def add_car(cid, uid, key, name):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO garage (chat_id, user_id, car_key, car_name) VALUES (<LaTex>id_15</LaTex>2,<LaTex>id_16</LaTex>1,<LaTex>id_17</LaTex>1,<LaTex>id_18</LaTex>3,<LaTex>id_19</LaTex>4)", cid, uid, key, name)

async def get_cars(cid, uid):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT car_name FROM garage WHERE chat_id async with pool.acquire() as conn:
        rows ==<LaTex>id_20</LaTex>2", cid, uid) await conn.fetch("SELECT car_name FROM garage WHERE chat_id
        return [r['car_name'] for r in rows]

async def get_bank(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT deposit,last_interest_time FROM bank WHERE chat_id=<LaTex>id_21</LaTex>2", cid, uid)
        if not r:
=<LaTex>id_22</LaTex>2", cid, uid)
        return [r['car_name'] for r in rows]

async def get_bank(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT deposit,last_interest_time FROM bank WHERE chat_id=<LaTex>id_23</LaTex>2", cid, uid)
        if not r:
            await conn.execute("INSERT INTO bank VALUES (<LaTex>id_24</LaTex>            await conn.execute("INSERT INTO bank VALUES (<LaTex>id_25</LaTex>2,0,<LaTex>id_26</LaTex>3)", cid, uid, time.time())
            return {"deposit": 0, "last_interest_time": time.time()}
        return dict(r)())
            return {"deposit": 0, "last

async def update_bank(cid, uid, amt):
_interest_time": time.time()}
        return dict(r)

async def update_bank(cid, uid, amt):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE bank SET deposit=deposit+<LaTex>id_27</LaTex>2 AND user_id=<LaTex>id_28</LaTex>1 WHERE chat_id=<LaTex>id_29</LaTex>3", amt,, lt):
    days = (time.time() - cid, uid)

async def calc_interest(dep, lt):
    days = (time.time() - lt) / 86400
    return int(dep * BANK_INTEREST_RATE * days), time lt) / 86400
    return int(dep * BANK_INTEREST_RATE * days), time.time()

async def get_education(cid, uid):
    async with pool.acquire() as conn:
.time()

async def get_education(cid, uid        r = await conn.fetchrow("SELECT completed_courses,):
    async with pool.acquire() as conn:
has_mba FROM education WHERE chat_id=<LaTex>id_30</LaTex>2", cid, uid)
        if not r:
            await conn.execute("INSERT INTO education VALUES (<LaTex>id_31</LaTex>2,'{}',FALSE)", cid, uid)
            return {"completed_courses": [], "has_mba": False}
        return {"completed_courses": r        r = await conn.fetchrow("SELECT completed_courses,has_mba FROM education WHERE chat_id=<LaTex>id_32</LaTex>2", cid, uid)
        if not r:
            await conn.execute("INSERT INTO education VALUES (<LaTex>id_33</LaTex>2,'{}',FALSE)", cid, uid)
            return {"completed_courses": [], "has_mba": False}
        return {"completed_courses": r['completed_courses'] or [], "has_mba": r['completed_courses'] or [], "has_mba": r['has_mba']}

async def complete_course(cid, uid, ck):
    async with pool.acquire() as conn:
        if ck == "mba":
            await conn.execute("UPDATE education SET has_mba['has_mba']}

async def complete_course(cid, uid, ck):
    async with pool.acquire() as conn:
        if ck == "mba":
            await conn.execute("UPDATE education SET has_mba=TRUE WHERE chat_id=<LaTex>id_34</LaTex>2", cid, uid)
        else:
            await conn.execute("UPDATE education SET completed_courses=array_append(completed=TRUE WHERE chat_id=<LaTex>id_35</LaTex>2", cid, uid)
        else:
            await conn.execute("UPDATE education SET completed_courses=array_append(completed_courses,<LaTex>id_36</LaTex>2 AND user_id=<LaTex>id_37</LaTex>1) WHERE chat_id=<LaTex>id_38</LaTex>3", ck, cid, uid)

async def get_loan(cid, uid):
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT amount,interest,taken_at,due_date FROM loans WHERE chat_id=<LaTex>id_39</LaTex>2",("SELECT amount,interest,taken_at,due_date FROM loans WHERE chat_id=<LaTex>id_40</LaTex>2", cid, uid)
        if not r: return {"amount": 0, "interest": 0, "taken_at": 0, "due_date": 0 cid, uid)
        if not r: return {"}
        return dict(r)

async def update_loanamount": 0, "interest": 0, "taken_at": 0, "due_date": 0}
        return dict(r)

async def update_loan(cid, uid, amount, interest, taken_at, due(cid, uid, amount, interest, taken_at, due_date):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO loans (chat_id_date):
    async with pool.acquire() as conn:,user_id,amount,interest,taken_at,due_date
        await conn.execute("INSERT INTO loans (chat_id,user_id,amount,interest,taken_at,due_date) VALUES (<LaTex>id_41</LaTex>2,<LaTex>id_42</LaTex>4,<LaTex>id_43</LaTex>1,<LaTex>id_44</LaTex>3,<LaTex>id_45</LaTex>5,<LaTex>id_46</LaTex>3,interest=<LaTex>id_47</LaTex>6) ON CONFLICT (chat_id,user_id)_at=<LaTex>id_48</LaTex>6", cid, uid, amount, interest, taken_at, due_date)

 DO UPDATE SET amount=<LaTex>id_49</LaTex>4,taken_at=<LaTex>id_50</LaTex>6", cid, uid, amount, interest, taken_at, due_date)

async def clear_loan(cid, uid):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM loans WHERE chat_id=<LaTex>id_51</LaTex>async def clear_loan(cid, uid):
    async with pool.acquire() as conn:
        await conn.execute("2", cid, uid)

async def arrest_player(cidDELETE FROM loans WHERE chat_id=<LaTex>id_52</LaTex>, uid):
    arrested = []
    bank_data2", cid, uid)

async def arrest_player(cid = await get_bank(cid, uid)
    if bank, uid):
    arrested = []
    bank_data_data['deposit'] > 0:
        arrested.append = await get_bank(cid, uid)
    if bank_data['deposit'] > 0:
        arrested.append(f"💰 Банк: {fmt_money(bank_data['deposit'])}")
        async with pool.acquire() as(f"💰 Банк: {fmt_money(bank_data conn:
            await conn.execute("UPDATE bank SET deposit['deposit'])}")
        async with pool.acquire() as conn:
            await conn.execute("UPDATE bank SET deposit=0,last_interest_time=<LaTex>id_53</LaTex>2 AND user_id=<LaTex>id_54</LaTex>1 WHERE chat_id=<LaTex>id_55</LaTex>3", time.time(), cid, uid)
    cars = await get_cars(cid, uid)
    if cars:
        arrested.append(f uid)
    if cars:
        arrested.append(f"🚗 Машины: {', '.join(cars)}")
        async with pool.acquire() as conn"🚗 Машины: {', '.join(cars)}")
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM garage WHERE chat_id=<LaTex>id_56</LaTex>2", cid, uid:
            await conn.execute("DELETE FROM garage WHERE chat_id=<LaTex>id_57</LaTex>2", cid, uid)
    async with pool.acquire() as conn:
        businesses = await conn.fetch("SELECT business_name FROM businesses WHERE chat_id=<LaTex>id_58</LaTex>2", cid, uid)
        if businesses:
            biz_names)
    async with pool.acquire() as conn:
        businesses = await conn.fetch("SELECT business_name FROM businesses WHERE chat_id=<LaTex>id_59</LaTex>2", cid = ", ".join([b['business_name'] for b in businesses])
            arrested.append(f"🏢 Бизнесы: {biz_names}")
            await conn.execute("DELETE FROM businesses WHERE chat_id=<LaTex>id_60</LaTex>2", cid, uid)
    async with pool in businesses])
            arrested.append(f"🏢 Бизнесы: {biz_names}")
            await conn.execute("DELETE FROM businesses WHERE chat_id=<LaTex>id_61</LaTex>2", cid, uid)
    async with pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name FROM inventory WHERE chat_id=<LaTex>id_62</LaTex>2", cid, uid)
        if.acquire() as conn:
        items = await conn.fetch("SELECT item_name FROM inventory WHERE chat_id=<LaTex>id_63</LaTex>2", cid, uid)
        if items:
            item_names = ", ".join([i['item_name'] for i in items])
            arrested.append(f"🎒 Предметы: {item items:
            item_names = ", ".join([i_names}")
            await conn.execute("DELETE FROM inventory WHERE['item_name'] for i in items])
            arrested.append(f"🎒 Предметы: {item_names}")
            await conn.execute("DELETE FROM inventory WHERE chat_id=<LaTex>id_64</LaTex>2", cid, chat_id=<LaTex>id_65</LaTex>2", cid, uid)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET job_key='novice',level=1 WHERE chat_id=<LaTex>id_66</LaTex>2", cid, uid)
    arrested.append("💼 Профессия сброшена до Новичка")
    return arrested

# ==================== ВЕБ-СЕРВЕР И ФОНОВЫЕ ЗАДАЧИ ====================
async def handle_ping(request):
    return web.Response(text="🤖 Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web uid)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET job_key='novice',level=1 WHERE chat_id=<LaTex>id_67</LaTex>2", cid, uid)
    arrested.append("💼 Профессия сброшена до Новичка")
    return arrested

# ==================== ВЕБ-СЕРВЕР И ФОНОВЫЕ ЗАДАЧИ ====================
async def handle_ping(request):
    return web.Response(text="🤖 Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(run.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 80ner, '0.0.0.0',80))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    logger.info("🌐 port).start()
    logger.info("🌐 Web server started")

async def polling_health_check():
    while True:
        try:
            await asyncio Web server started")

async def polling_health_check():
    while True:
        try:
            await asyncio.sleep(300)
            await bot.sleep(300)
            await bot.get_me()
        except Exception as e:
            logger.error(f"Health check failed: {e}")

async def auto_lottery_loop():
    logger.info(".get_me()
        except Exception as e:
           🎰 Авто-лотерея запущена") logger.error(f"Health check failed: {e}")

async def auto_lottery_loop():
    logger.info("
    while True:
        await asyncio.sleep(3🎰 Авто-лотерея запущена")
    while True:
        await asyncio.sleep(3600)
        now = time.time()
        async with pool.acquire() as conn:
            chats600)
        now = time.time()
 = await conn.fetch("SELECT DISTINCT chat_id FROM lottery_tickets")
            for row in chats:
                cid =        async with pool.acquire() as conn:
            chats = await conn.fetch("SELECT DISTINCT chat_id FROM lottery_tickets")
            for row in chats:
                cid = row['chat_id']
                tickets = await conn.fetch("SELECT id,user_id FROM lottery_tickets WHERE chat_id=<LaTex>id_68</LaTex>1 AND buy_time<=<LaTex>id_69</LaTex>2", cid, now - LOTTERY_INTERVAL)
                if len(tickets) >=TERY_INTERVAL)
                if len(tickets) >= 2:
                    winner = random.choice(tickets) 2:
                    winner = random.choice(tickets)
                    bank = len(tickets) * LOTTERY
                    bank = len(tickets) * LOTTERY_PRICE
                    await update_balance(cid, winner['user_id_PRICE
                    await update_balance(cid, winner['user_id'], bank)
                    wname = await conn.fetchval'], bank)
                    wname = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=<LaTex>id_70</LaTex>1 AND user_id=<LaTex>id_71</LaTex>2", cid, winner['user_id']) or f"User{winner['user_id']}"']) or f"User{winner['user_id']}"
                    await conn.execute("DELETE FROM lottery_tickets WHERE chat
                    await conn.execute("DELETE FROM lottery_tickets WHERE chat_id=<LaTex>id_72</LaTex>1", cid)
                    try:
                        await bot.send_message(cid, f"🎊 < await bot.send_message(cid, f"🎊 <b>АВТО-РОЗЫГРЫШb>АВТО-РОЗЫГРЫШ!</b>\n\n🏆 {wname}\!</b>\n\n🏆 {wname}\n💰 {fmt_money(bank)}", parse_moden💰 {fmt_money(bank)}", parse_mode="HTML")
                    except: pass

async def loan="HTML")
                    except: pass

async def loan_interest_loop():
    logger.info("💳 Цик_interest_loop():
    logger.info("💳 Цикл кредитов запущен")
    while True:л кредитов запущен")
    while True:
        await asyncio.sleep(86400)
        await asyncio.sleep(86400)
        async with pool.acquire() as conn:
           
        async with pool.acquire() as conn:
            loans = await conn.fetch("SELECT chat_id,user_id, loans = await conn.fetch("SELECT chat_id,user_id,amount,interest,due_date FROM loans WHERE amount>0amount,interest,due_date FROM loans WHERE amount>0")
            for loan in loans:
                cid,")
            for loan in loans:
                cid, uid = loan['chat_id'], loan['user_id'] uid = loan['chat_id'], loan['user_id']
                if time.time() > loan['due_date']:
                if time.time() > loan['due_date']:
                    total_debt = loan['amount'] + loan
                    total_debt = loan['amount'] + loan['interest']
                    arrested = await arrest_player(cid,['interest']
                    arrested = await arrest_player(cid, uid)
                    await clear_loan(cid, uid)
 uid)
                    await clear_loan(cid, uid)
                    arrested_text = "\n".join([f"•                    arrested_text = "\n".join([f"• {item}" for item in arrested]) if arrested else " {item}" for item in arrested]) if arrested else "Нечего арестовать"
                    try:
Нечего арестовать"
                    try:
                        await bot.send_message(cid, f"🚔                        await bot.send_message(cid, f"🚔 <b>АРЕСТ ИМУЩЕСТВА!</ <b>АРЕСТ ИМУЩЕСТВА!</b>\n\nДолг был: <b>{b>\n\nДолг был: <b>{fmt_money(total_debt)}</b>\n\n<b>fmt_money(total_debt)}</b>\n\n<b>Конфисковано:</b>\n{arrestedКонфисковано:</b>\n{arrested_text}", parse_mode="HTML")
                    except: pass_text}", parse_mode="HTML")
                    except: pass
                else:
                    daily_interest = int(loan
                else:
                    daily_interest = int(loan['amount'] * CREDIT_DAILY_RATE)
                   ['amount'] * CREDIT_DAILY_RATE)
                    new_interest = loan['interest'] + daily_interest
                    new_interest = loan['interest'] + daily_interest
                    await update_loan(cid, uid, loan['amount'], new await update_loan(cid, uid, loan['amount'], new_interest, loan['taken_at'], loan['due_date'])_interest, loan['taken_at'], loan['due_date'])

# ==================== ОСНОВНЫЕ КОМАНД

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================
@dp.message(Command("start"))
Ы ====================
@dp.message(Command("start"))
async def cmd_start(m: Message):
    await saveasync def cmd_start(m: Message):
    await save_username(m.chat.id, m.from_user.id, m.from_username(m.chat.id, m.from_user.id, m.from_user.full_name)
    await m.answer("_user.full_name)
    await m.answer(" <b>Экономика группы!</b>\n <b>Экономика группы!</b>\n\n💰 /balance\n💼 /work\n\n💰 /balance\n💼 /work\n💸 /pay (ответ)\n🔫💸 /pay (ответ)\n🔫 /rob (ответ)\n🎁 /daily\n /rob (ответ)\n🎁 /daily\n🎲 /dice сумма\n🎟️ /🎲 /dice сумма\n🎟️ /buy_ticket\n🛒 /shop\n🏪buy_ticket\n🛒 /shop\n🏪 /market\n🚗 /cars\n /market\n🚗 /cars\n️ /mycar\n💼 /collect\n️ /mycar\n💼 /collect\n🎒 /inv\n📊 /info\n🎒 /inv\n📊 /info\n🏆 /rating\n🃏 /black🏆 /rating\n🃏 /blackjack\n🔨 /craft\n🔄 /tradejack\n🔨 /craft\n🔄 /trade\n🏦 /bank\n📥 /deposit\n🏦 /bank\n📥 /deposit\n📤 /withdraw\n🎓 /education\n📤 /withdraw\n🎓 /education\n📘 /buy_course\n💳 /credit сумма\n📘 /buy_course\n💳 /credit сумма\n📊 /debt\n\n📊 /debt\n /repay сумма\n✅ /repay_all\n /repay сумма\n✅ /repay_all\n🚔 /bailout", parse_mode="HTML🚔 /bailout", parse_mode="HTML")

@dp.message(Command("balance"))
async def")

@dp.message(Command("balance"))
async def cmd_balance(m: Message):
    await save_username(m cmd_balance(m: Message):
    await save_username(m.chat.id, m.from_user.id, m.from_user.full.chat.id, m.from_user.id, m.from_user.full_name)
    u = await get_user(m.chat.id_name)
    u = await get_user(m.chat.id, m.from_user.id)
    cars = await get, m.from_user.id)
    cars = await get_cars(m.chat.id, m.from_user.id)
_cars(m.chat.id, m.from_user.id)
    cars_text = ", ".join(cars) if cars    cars_text = ", ".join(cars) if cars else "нет"
    await m.answer(f" else "нет"
    await m.answer(f"💰 <b>{fmt_money(u['balance'])}</💰 <b>{fmt_money(u['balance'])}</b>\n🚗 {cars_text}", parse_modeb>\n🚗 {cars_text}", parse_mode="HTML")

@dp.message(Command("work"))
="HTML")

@dp.message(Command("work"))
async def cmd_work(m: Message):
    cid,async def cmd_work(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    uid = m.chat.id, m.from_user.id
    await save_username(cid, uid, m.from_user.full_name await save_username(cid, uid, m.from_user.full_name)
    p = await get_profile(cid, uid))
    p = await get_profile(cid, uid)
    jk = p['job_key']
   
    jk = p['job_key']
    if jk != 'novice':
        edu = if jk != 'novice':
        edu = await get_education(cid, uid)
        if j await get_education(cid, uid)
        if jk not in edu['completed_courses']:
            async withk not in edu['completed_courses']:
            async with pool.acquire() as conn:
                await conn.execute(" pool.acquire() as conn:
                await conn.execute("UPDATE profiles SET job_key='novice' WHERE chat_idUPDATE profiles SET job_key='novice' WHERE chat_id=<LaTex>id_73</LaTex>2", cid, uid)=<LaTex>id_74</LaTex>2", cid, uid)
            jk = 'novice'
            p
            jk = 'novice'
            p['job_key'] = 'novice'
    j['job_key'] = 'novice'
    j = JOBS[jk]
    ct = time.time = JOBS[jk]
    ct = time.time()
    cd = j['cooldown'] * (0()
    cd = j['cooldown'] * (0.9 if p['has_coffee'] else 1.9 if p['has_coffee'] else 1.0)
    if ct - p['last_work.0)
    if ct - p['last_work_time'] < cd:
        return await m.answer(f_time'] < cd:
        return await m.answer(f"⏳ Отдых {int((cd-(ct"⏳ Отдых {int((cd-(ct-p['last_work_time']))//60)} мин.")-p['last_work_time']))//60)} мин.")
    sal = j['base_pay'] * p['
    sal = j['base_pay'] * p['level'] + random.randint(0, 5)
level'] + random.randint(0, 5)
    edu = await get_education(cid, uid)
    edu = await get_education(cid, uid)
    if edu['has_mba']: sal = int(s    if edu['has_mba']: sal = int(sal * 1.5)
    await update_balanceal * 1.5)
    await update_balance(cid, uid, sal)
    async with pool.acquire(cid, uid, sal)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles() as conn:
        await conn.execute("UPDATE profiles SET last_work_time=<LaTex>id_75</LaTex>2 AND SET last_work_time=<LaTex>id_76</LaTex>2 AND user_id=<LaTex>id_77</LaTex>3", ct, cid, uid)
    await m.answer(f"💼 <b>{j    await m.answer(f"💼 <b>{j['name']}</b> (Ур.{p['level['name']}</b> (Ур.{p['level']}): +<b>{fmt_money(sal)}</b']}): +<b>{fmt_money(sal)}</b>", parse_mode="HTML")

@dp.message(Command(">", parse_mode="HTML")

@dp.message(Command("jobs"))
async def cmd_jobs(m: Message):
jobs"))
async def cmd_jobs(m: Message):
    t = "📋 <b>Вак    t = "📋 <b>Вакансии:</b>\n"
    for k,ансии:</b>\n"
    for k, v in JOBS.items(): t += f" v in JOBS.items(): t += f" {v['name']} ({v['base_pay {v['name']} ({v['base_pay']}/ч) → /job {k}\n"']}/ч) → /job {k}\n"
    await m.answer(t, parse_mode="HTML")
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("job"))
async def cmd

@dp.message(Command("job"))
async def cmd_change_job(m: Message):
    cid, uid =_change_job(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) <  m.text.split()
    if len(args) < 2 or args[1] not in JOBS: return2 or args[1] not in JOBS: return await m.answer("/jobs")
    if args[1 await m.answer("/jobs")
    if args[1] != 'novice':
        edu = await get] != 'novice':
        edu = await get_education(cid, uid)
        if args[1_education(cid, uid)
        if args[1] not in edu['completed_courses']: return await m.answer] not in edu['completed_courses']: return await m.answer(f"❌ Нужен курс: /buy_course {(f"❌ Нужен курс: /buy_course {args[1]}")
    async with pool.acquire()args[1]}")
    async with pool.acquire() as conn:
        await conn.execute("UPDATE profiles SET as conn:
        await conn.execute("UPDATE profiles SET job_key=<LaTex>id_78</LaTex>2 AND user_id job_key=<LaTex>id_79</LaTex>2 AND user_id=<LaTex>id_80</LaTex>3", args[1], cid, uid)
    await m.answer(f"✅ Теперь: <b>{    await m.answer(f"✅ Теперь: <b>{JOBS[args[1]]['name']}</b>",JOBS[args[1]]['name']}</b>", parse_mode="HTML")

@dp.message(Command("pay parse_mode="HTML")

@dp.message(Command("pay"))
async def cmd_pay(m: Message):
   "))
async def cmd_pay(m: Message):
    cid, uid = m.chat.id, m.from_user.id cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message:(args) < 2 or not m.reply_to_message: return await m.answer("/pay сумма (ответ)") return await m.answer("/pay сумма (ответ)")
    try: amt = int(args[1])

    try: amt = int(args[1])
    except: return await m.answer("❌ Число    except: return await m.answer("❌ Число!")
    if amt <= 0: return await m!")
    if amt <= 0: return await m.answer(">0!")
    s, r = uid.answer(">0!")
    s, r = uid, m.reply_to_message.from_user.id
    if s, m.reply_to_message.from_user.id
    if s == r: return await m.answer("Себе нельзя!") == r: return await m.answer("Себе нельзя!")
    sb = await get_user(cid, s)

    sb = await get_user(cid, s)
    if sb['balance'] < amt: return await m    if sb['balance'] < amt: return await m.answer(f"❌ Мало ({fmt_money(sb['balance.answer(f"❌ Мало ({fmt_money(sb['balance'])})")
    await update_balance(cid, s,'])})")
    await update_balance(cid, s, -amt)
    await update_balance(cid, r, -amt)
    await update_balance(cid, r, amt)
    await save_username(cid, r, m amt)
    await save_username(cid, r, m.reply_to_message.from_user.full_name)
    await m.reply_to_message.from_user.full_name)
    await m.answer(f"✅ Перевод <b>{fmt_money.answer(f"✅ Перевод <b>{fmt_money(amt)}</b>", parse_mode="HTML")

@(amt)}</b>", parse_mode="HTML")

@dp.message(Command("rob"))
async def cmd_robdp.message(Command("rob"))
async def cmd_rob(m: Message):
    cid, uid = m.chat(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if not m.reply.id, m.from_user.id
    if not m.reply_to_message: return await m.answer("🔫 Ответ_to_message: return await m.answer("🔫 Ответьте на жертву!")
    rid, vid = uidьте на жертву!")
    rid, vid = uid, m.reply_to_message.from_user.id
    if rid, m.reply_to_message.from_user.id
    if rid == vid: return await m.answer("❌ Себя == vid: return await m.answer("❌ Себя нельзя!")
    async with pool.acquire() as conn: нельзя!")
    async with pool.acquire() as conn:
        lr = await conn.fetchval("SELECT last_
        lr = await conn.fetchval("SELECT last_robbery FROM robbery WHERE chat_id=<LaTex>id_81</LaTex>1 AND user_id=<LaTex>id_82</LaTex>2", cid, rid) or 0
        ct = time.time()
        if ct - lr < ct = time.time()
        if ct - lr < ROB_COOLDOWN: return await m.answer(f" ROB_COOLDOWN: return await m.answer(f" Кулдаун {format_time(ROB Кулдаун {format_time(ROB_COOLDOWN - (ct - lr))}")
       _COOLDOWN - (ct - lr))}")
        await conn.execute("INSERT INTO robbery VALUES (<LaTex>id_83</LaTex>2 await conn.execute("INSERT INTO robbery VALUES (<LaTex>id_84</LaTex>2,<LaTex>id_85</LaTex>3) ON CONFLICT DO UPDATE SET last_robbery=<LaTex>id_86</LaTex>3", cid, rid, ct)
    vb = await get_user(cid, vid)
    if vb['balance'] < 50: return vb = await get_user(cid, vid)
    if vb['balance'] < 50: return await m.answer("У жертвы мало денег!")
    await m.answer("У жертвы мало денег!")
    if random.random() < ROB_SUCCESS_RATE:
        st if random.random() < ROB_SUCCESS_RATE:
        st = int(vb['balance'] * random.uniform(RO = int(vb['balance'] * random.uniform(ROB_MIN_PERCENT, ROB_MAX_PERCENT))
        await updateB_MIN_PERCENT, ROB_MAX_PERCENT))
        await update_balance(cid, vid, -st)
        await update_balance(cid, vid, -st)
        await update_balance(cid, rid, st)
        await m.answer_balance(cid, rid, st)
        await m.answer(f"🔫 Украл <b>{fmt(f"🔫 Украл <b>{fmt_money(st)}</b>!", parse_mode="HTML")
_money(st)}</b>!", parse_mode="HTML")
    else:
        rb = await get_user(cid,    else:
        rb = await get_user(cid, rid)
        pn = int(rb['balance'] * rid)
        pn = int(rb['balance'] * ROB_PENALTY_RATE)
        await update_balance ROB_PENALTY_RATE)
        await update_balance(cid, rid, -pn)
        await update_balance(cid, rid, -pn)
        await update_balance(cid, vid, pn)
        await m.answer(f(cid, vid, pn)
        await m.answer(f"🚔 Штраф <b>{fmt_money"🚔 Штраф <b>{fmt_money(pn)}</b>!", parse_mode="HTML")

(pn)}</b>!", parse_mode="HTML")

@dp.message(Command("daily"))
async def cmd_daily@dp.message(Command("daily"))
async def cmd_daily(m: Message):
    cid, uid = m.chat(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    await save_username(cid.id, m.from_user.id
    await save_username(cid, uid, m.from_user.full_name)
    ct, uid, m.from_user.full_name)
    ct = time.time()
    async with pool.acquire() as = time.time()
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT conn:
        r = await conn.fetchrow("SELECT last_claim,streak FROM daily_bonus WHERE chat_id=<LaTex>id_87</LaTex>1 AND user_id=<LaTex>id_88</LaTex>2", cid, uid)
        lc, sk = (r['last_claim'], r[' lc, sk = (r['last_claim'], r['streak']) if r else (0, 0)streak']) if r else (0, 0)
        if ct - lc < 8640
        if ct - lc < 86400: return await m.answer(f"⏰0: return await m.answer(f"⏰ Через {format_time(86400 - ( Через {format_time(86400 - (ct - lc))}")
        if ct - lc <ct - lc))}")
        if ct - lc < 172800: sk += 1 172800: sk += 1
        else: sk = 1
        bn =
        else: sk = 1
        bn = random.randint(100, 300) random.randint(100, 300) * min(sk, 7)
        await update_balance * min(sk, 7)
        await update_balance(cid, uid, bn)
        await conn.execute("(cid, uid, bn)
        await conn.execute("INSERT INTO daily_bonus VALUES (<LaTex>id_89</LaTex>2,<LaTex>id_90</LaTex>1,<LaTex>id_91</LaTex>3,<LaTex>id_92</LaTex>,<LaTex>id_93</LaTex>3,streak=<LaTex>id_94</LaTex>4", cid, uid, ct, sk)
    await m.answer(f"🎁 sk)
    await m.answer(f"🎁 Бонус за {sk} дн.: <b Бонус за {sk} дн.: <b>{fmt_money(bn)}</b>", parse_mode="HTML>{fmt_money(bn)}</b>", parse_mode="HTML")

@dp.message(Command("dice"))
async def")

@dp.message(Command("dice"))
async def cmd_dice(m: Message):
    cid, uid = cmd_dice(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) <  m.text.split()
    if len(args) < 2: return await m.answer("🎲 Использование2: return await m.answer("🎲 Использование: <b>/dice сумма</b>\n\nШ: <b>/dice сумма</b>\n\nШанс 50/50. Выпадает анс 50/50. Выпадает 1-6.\n4, 5, 61-6.\n4, 5, 6 — выигрыш x2\n1, 2,  — выигрыш x2\n1, 2, 3 — проигрыш", parse_mode="HTML")
3 — проигрыш", parse_mode="HTML")
    try: bet = int(args[1])
       try: bet = int(args[1])
    except: return await m.answer("❌ Ставка except: return await m.answer("❌ Ставка должна быть числом!")
    if bet < DICE должна быть числом!")
    if bet < DICE_MIN_BET: return await m.answer(f"❌_MIN_BET: return await m.answer(f"❌ Минимальная ставка: {DICE_MIN_BET} Минимальная ставка: {DICE_MIN_BET} сарапулок")
    ub = await get_user сарапулок")
    ub = await get_user(cid, uid)
    if ub['balance'] <(cid, uid)
    if ub['balance'] < bet: return await m.answer(f"❌ Нед bet: return await m.answer(f"❌ Недостаточно ({fmt_money(ub['balance'])})")остаточно ({fmt_money(ub['balance'])})")
    await update_balance(cid, uid, -bet)
    await update_balance(cid, uid, -bet)
    dice = random.randint(1, 6)
    dice = random.randint(1, 6)
    await m.answer(f"🎲 <b
    await m.answer(f"🎲 <b>Бросаем кубик...</b>\n\nСта>Бросаем кубик...</b>\n\nСтавка: {fmt_money(bet)}", parse_mode="вка: {fmt_money(bet)}", parse_mode="HTML")
    await asyncio.sleep(1)
   HTML")
    await asyncio.sleep(1)
    if dice >= DICE_WIN_THRESHOLD:
        win = if dice >= DICE_WIN_THRESHOLD:
        win = bet * DICE_WIN_MULTIPLIER
        await update_balance bet * DICE_WIN_MULTIPLIER
        await update_balance(cid, uid, win)
        await m.answer(f(cid, uid, win)
        await m.answer(f"🎲 <b>Выпало: {"🎲 <b>Выпало: {dice}</b>\n\n🎉 <b>dice}</b>\n\n🎉 <b>ПОБЕДА!</b>\nВыигрыш:ПОБЕДА!</b>\nВыигрыш: <b>{fmt_money(win)}</b> (x2 <b>{fmt_money(win)}</b> (x2)", parse_mode="HTML")
    else:
       )", parse_mode="HTML")
    else:
        await m.answer(f"🎲 <b>Вы await m.answer(f"🎲 <b>Выпало: {dice}</b>\n\n💀пало: {dice}</b>\n\n💀 <b>Проигрыш</b>\nПопр <b>Проигрыш</b>\nПопробуй ещё раз!", parse_mode="HTML")

@обуй ещё раз!", parse_mode="HTML")

@dp.message(Command("buy_ticket"))
async def cmd_buydp.message(Command("buy_ticket"))
async def cmd_buy_ticket(m: Message):
    cid, uid = m_ticket(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    await save_username.chat.id, m.from_user.id
    await save_username(cid, uid, m.from_user.full_name)
   (cid, uid, m.from_user.full_name)
    ub = await get_user(cid, uid)
    if ub = await get_user(cid, uid)
    if ub['balance'] < LOTTERY_PRICE: return ub['balance'] < LOTTERY_PRICE: return await m.answer(f"❌ Нужно {fmt_money( await m.answer(f"❌ Нужно {fmt_money(LOTTERY_PRICE)}")
    await update_balance(cidLOTTERY_PRICE)}")
    await update_balance(cid, uid, -LOTTERY_PRICE)
    async, uid, -LOTTERY_PRICE)
    async with pool.acquire() as conn:
        await conn.execute with pool.acquire() as conn:
        await conn.execute("INSERT INTO lottery_tickets (chat_id,user_id,b("INSERT INTO lottery_tickets (chat_id,user_id,buy_time) VALUES (<LaTex>id_95</LaTex>2,<LaTex>id_96</LaTex>1,<LaTex>id_97</LaTex>3)", cid, uid, time.time())
    await m.answer(f, uid, time.time())
    await m.answer(f"🎟️ Билет куплен! Роз"🎟️ Билет куплен! Розыгрыш через 12ч.", parse_mode="ыгрыш через 12ч.", parse_mode="HTML")

@dp.message(Command("info"))
asyncHTML")

@dp.message(Command("info"))
async def cmd_info(m: Message):
    cid, uid def cmd_info(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    await = m.chat.id, m.from_user.id
    await save_username(cid, uid, m.from_user.full_name) save_username(cid, uid, m.from_user.full_name)
    u = await get_user(cid, uid)

    u = await get_user(cid, uid)
    p = await get_profile(cid, uid)
       p = await get_profile(cid, uid)
    cars = await get_cars(cid, uid)
    cars = await get_cars(cid, uid)
    bd = await get_bank(cid, uid)
    edu bd = await get_bank(cid, uid)
    edu = await get_education(cid, uid)
    loan = await get_education(cid, uid)
    loan = await get_loan(cid, uid)
    async with = await get_loan(cid, uid)
    async with pool.acquire() as conn:
        bc = await conn pool.acquire() as conn:
        bc = await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE chat_id=<LaTex>id_98</LaTex>1 AND user_id=<LaTex>id_99</LaTex>2", cid, uid)
        ic = await conn.fetchval("SELECT COUNT(*) FROM        ic = await conn.fetchval("SELECT COUNT(*) FROM inventory WHERE chat_id=<LaTex>id_100</LaTex>2", inventory WHERE chat_id=<LaTex>id_101</LaTex>2", cid, uid)
    j = JOBS[p[' cid, uid)
    j = JOBS[p['job_key']]
    cc = len(edu['completedjob_key']]
    cc = len(edu['completed_courses']) + (1 if edu['has_mba']_courses']) + (1 if edu['has_mba'] else 0)
    cars_text = ", ".join else 0)
    cars_text = ", ".join(cars) if cars else "нет"
    t(cars) if cars else "нет"
    t = f"📊 <b>{m.from_user = f"📊 <b>{m.from_user.full_name}</b>\n💰 {fmt_money.full_name}</b>\n💰 {fmt_money(u['balance'])}\n🏦 Банк:(u['balance'])}\n🏦 Банк: {fmt_money(bd['deposit'])}\n {fmt_money(bd['deposit'])}\n {j['name']} (Ур.{p[' {j['name']} (Ур.{p['level']})\n🚗 {cars_text}\level']})\n🚗 {cars_text}\n🏢 {bc} биз.\nn🏢 {bc} биз.\n {ic} предм.\n🎓 { {ic} предм.\n🎓 {cc} курсов"
    if edu['has_mcc} курсов"
    if edu['has_mba']: t += "\n🎯 MBA (+ba']: t += "\n🎯 MBA (+50%)"
    if p['has_coffee50%)"
    if p['has_coffee']: t += "\n☕ Кофе"
   ']: t += "\n☕ Кофе"
    if loan['amount'] > 0:
        total if loan['amount'] > 0:
        total_debt = loan['amount'] + loan['interest']_debt = loan['amount'] + loan['interest']
        t += f"\n💳 Долг:
        t += f"\n💳 Долг: <b>{fmt_money(total_debt)}</b>" <b>{fmt_money(total_debt)}</b>"
    await m.answer(t, parse_mode="HTML")
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("shop"))
async def cmd

@dp.message(Command("shop"))
async def cmd_shop(m: Message):
    t = "_shop(m: Message):
    t = " <b>Улучшения:</b>\n" <b>Улучшения:</b>\n"
    for k, v in SHOP_ITEMS.items(): t
    for k, v in SHOP_ITEMS.items(): t += f"🔹 {v['name']} ({ += f"🔹 {v['name']} ({fmt_money(v['price'])}) → /buy {kfmt_money(v['price'])}) → /buy {k}\n"
    await m.answer(t, parse_mode}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buy"))
="HTML")

@dp.message(Command("buy"))
async def cmd_buy(m: Message):
    cid,async def cmd_buy(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2 or args[1] not in SHOP_ITEMS: return await m.answer("/shop")
    it = SHOP_ITEMS[args[1]]
    u = await get_user(cid, uid)
    if u['balance'] < it['price']: return await m.answer(f"❌ Нужно {fmt_money(it['price'])}") uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2 or args[1] not in SHOP_ITEMS: return await m.answer("/shop")
    it = SHOP_ITEMS[args[1]]
    u = await get_user(cid, uid)
    if u['balance'] < it['price']: return await m.answer(f"❌ Нужно {fmt_money(it['price'])}")
    await update_balance(cid, uid, -it['
    await update_balance(cid, uid, -it['price'])
    if it['type'] == 'levelprice'])
    if it['type'] == 'level_up':
        p = await get_profile(cid, uid_up':
        p = await get_profile(cid, uid)
        async with pool.acquire() as conn:
)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET level=<LaTex>id_102</LaTex>1 WHERE chat_id=<LaTex>id_103</LaTex>3", p[' chat_id=<LaTex>id_104</LaTex>3", p['level']+1, cid, uid)
        await mlevel']+1, cid, uid)
        await m.answer(f"✅ Уровень {p['level']+1}.answer(f"✅ Уровень {p['level']+1}!")
    elif it['type'] == 'cooldown_reduce!")
    elif it['type'] == 'cooldown_reduce':
        async with pool.acquire() as conn:
':
        async with pool.acquire() as conn:
            await conn.execute("UPDATE profiles SET has_coffee=            await conn.execute("UPDATE profiles SET has_coffee=TRUE WHERE chat_id=<LaTex>id_105</LaTex>2",TRUE WHERE chat_id=<LaTex>id_106</LaTex>2", cid, uid)
        await m.answer("✅ Ко cid, uid)
        await m.answer("✅ Кофе куплен!")

@dp.message(Command("market"))фе куплен!")

@dp.message(Command("market"))
async def cmd_market(m: Message):
    t
async def cmd_market(m: Message):
    t = "🏪 <b>Рынок:</ = "🏪 <b>Рынок:</b>\n\n📦 <b>Кейb>\n\n📦 <b>Кейсы:</b>\n"
    for k, vсы:</b>\n"
    for k, v in MARKET.items():
        if v["type"] == "case": t += f"🔹 {v in MARKET.items():
        if v["type"] == "case": t += f"🔹 {v['name']} ({fmt_money(v['price'])}) →['name']} ({fmt_money(v['price'])}) → /buy_market {k}\n"
    t += /buy_market {k}\n"
    t += "\n🏢 <b>Бизнесы ( "\n🏢 <b>Бизнесы (окупаемость 6 дней, можно покупать несколько):</b>\n"
    for k, v in MARKET.items():
        if v["type"] == "business":
            t += f"🔹 {v['name']} ({fmt_money(v['price'])}) → /buy_market {k}\n"
            t += f"   💰 Доход: {fmt_money(v['income'])}/сутки\n"
    await m.answer(t, parse_mode="HTML")

@окупаемость 6 дней, можно покупать несколько):</b>\n"
    for k, v in MARKET.items():
        if v["type"] == "business":
            t += f"🔹 {v['name']} ({fmt_money(v['price'])}) → /buy_market {k}\n"
            t += f"   💰 Доход: {fmt_money(v['income'])}/сутки\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buy_market"))
async def cmd_buydp.message(Command("buy_market"))
async def cmd_buy_market(m: Message):
    cid, uid = m_market(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2.text.split()
    if len(args) < 2 or args[1] not in MARKET: return or args[1] not in MARKET: return await m.answer("/market")
    it = MARKET[args await m.answer("/market")
    it = MARKET[args[1]]
    u = await get_user(cid,[1]]
    u = await get_user(cid, uid)
    if u['balance'] < it[' uid)
    if u['balance'] < it['price']: return await m.answer(f"❌ Нужноprice']: return await m.answer(f"❌ Нужно {fmt_money(it['price'])}")
    await update {fmt_money(it['price'])}")
    await update_balance(cid, uid, -it['price'])
   _balance(cid, uid, -it['price'])
    if it['type'] == 'case':
        r if it['type'] == 'case':
        r = random.randint(1, 100)
 = random.randint(1, 100)
        if r <= 5: pr, rar = "🎸 Золотая Скрипка", "        if r <= 5: pr, rar = "🎸 Золотая Скрипка", "legendary"
        elif r <= 25:legendary"
        elif r <= 25: pr, rar = "💎 Алмаз", " pr, rar = "💎 Алмаз", "rare"
        else: pr, rar = "rare"
        else: pr, rar = " Бумага", "common"
        async Бумага", "common"
        async with pool.acquire() as conn:
            await conn.execute with pool.acquire() as conn:
            await conn.execute("INSERT INTO inventory (chat_id,user_id,item("INSERT INTO inventory (chat_id,user_id,item_name,item_type,rarity) VALUES (<LaTex>id_107</LaTex>2,<LaTex>id_108</LaTex>1,<LaTex>id_109</LaTex>3,'card',<LaTex>id_110</LaTex>4)", cid, uid, pr, rar)
        await m.answer(f"📦 rar)
        await m.answer(f"📦 Выпало: <b>{pr}</b> ({ Выпало: <b>{pr}</b> ({rar})", parse_mode="HTML")
    elif it['rar})", parse_mode="HTML")
    elif it['type'] == 'business':
        async with pool.acquiretype'] == 'business':
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO() as conn:
            await conn.execute("INSERT INTO businesses (chat_id,user_id,business_name,in businesses (chat_id,user_id,business_name,income) VALUES (<LaTex>id_111</LaTex>2,<LaTex>id_112</LaTex>4)", cid, uid, it['name'], it['income'])come) VALUES (<LaTex>id_113</LaTex>2,<LaTex>id_114</LaTex>4)", cid, uid, it['name'], it['income'])
        await m.answer(f"✅ Куплен <
        await m.answer(f"✅ Куплен <b>{it['name']}</b>! Можете купитьb>{it['name']}</b>! Можете купить ещё такой же.", parse_mode="HTML")

@dp ещё такой же.", parse_mode="HTML")

@dp.message(Command("collect"))
async def cmd_collect(m:.message(Command("collect"))
async def cmd_collect(m: Message):
    cid, uid = m.chat.id, Message):
    cid, uid = m.chat.id, m.from_user.id
    now = time.time()
 m.from_user.id
    now = time.time()
    tot = 0
    collected = []
       tot = 0
    collected = []
    async with pool.acquire() as conn:
        bz = async with pool.acquire() as conn:
        bz = await conn.fetch("SELECT * FROM businesses WHERE chat_id=<LaTex>id_115</LaTex>1 AND user_id=<LaTex>id_116</LaTex>2", cid, uid)
        if not bz: return await m.answer("❌        if not bz: return await m.answer("❌ Нет бизнеса.")
        for b in bz:
            Нет бизнеса.")
        for b in bz:
            if now - b['last_collect_time'] > 8 if now - b['last_collect_time'] > 86400:
                tot += b['income6400:
                tot += b['income']
                collected.append(f"• {b['business']
                collected.append(f"• {b['business_name']}: +{fmt_money(b['income'])}")_name']}: +{fmt_money(b['income'])}")
                await conn.execute("UPDATE businesses SET last_collect_time=<LaTex>id_117</LaTex>2", now, b['id
                await conn.execute("UPDATE businesses SET last_collect_time=<LaTex>id_118</LaTex>2", now, b['id'])
    if tot > 0:
        await'])
    if tot > 0:
        await update_balance(cid, uid, tot)
        items = "\n".join(collected)
        await m.answer update_balance(cid, uid, tot)
        items = "\n".join(collected)
        await m.answer(f"💼 <b>Прибыль собрана!</b>\n\n{items}\n\n💰(f"💼 <b>Прибыль собрана!</b>\n\n{items}\n\n💰 Итого: <b>+{fmt_money(tot)}</ Итого: <b>+{fmt_money(tot)}</b>", parse_mode="HTML")
    else:
b>", parse_mode="HTML")
    else:
        await m.answer("⏳ Рано.")

@dp.message(Command("cars"))
async def cmd_c        await m.answer("⏳ Рано.")

@dp.message(Command("cars"))
async def cmd_cars(m: Message):
    t = "ars(m: Message):
    t = " <b>Автосалон (можно покупать <b>Автосалон (можно покупать одинаковые):</b>\n"
    for одинаковые):</b>\n"
    for k, v in CARS.items(): t += f" k, v in CARS.items(): t += f"🔸 {v['name']} ({fmt_money(v['price'])}) → /buycar {k}\🔸 {v['name']} ({fmt_money(v['price'])}) → /buycar {k}\n"
    await m.answer(t, parse_mode="n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buycar"))HTML")

@dp.message(Command("buycar"))
async def cmd_buycar(m: Message):
    cid, uid = m.chat.id, m.from
async def cmd_buycar(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
   _user.id
    args = m.text.split()
    if len(args) < 2 or args[1] if len(args) < 2 or args[1] not in CARS: return await m.answer("/ not in CARS: return await m.answer("/cars")
    c = CARS[args[1]]cars")
    c = CARS[args[1]]
    u = await get_user(cid, uid)

    u = await get_user(cid, uid)
    if u['balance'] < c['price']: return    if u['balance'] < c['price']: return await m.answer(f"❌ Нужно {fmt_money(c await m.answer(f"❌ Нужно {fmt_money(c['price'])}")
    await update_balance(cid, uid['price'])}")
    await update_balance(cid, uid, -c['price'])
    await add_car(cid, -c['price'])
    await add_car(cid, uid, args[1], c['name'])
, uid, args[1], c['name'])
    await m.answer(f"🎉 Куплена    await m.answer(f"🎉 Куплена <b>{c['name']}</b>! Можете <b>{c['name']}</b>! Можете купить ещё такую же.", parse_mode="HTML")

@ купить ещё такую же.", parse_mode="HTML")

@dp.message(Command("mycar"))
async def cmd_mdp.message(Command("mycar"))
async def cmd_mycar(m: Message):
    cars = await get_cars(m.chat.id, m.from_user.id)
ycar(m: Message):
    cars = await get_cars(m.chat.id, m.from_user.id)
    if cars:
        cars_text = "\n".join([f"🚗 {c}" for c    if cars:
        cars_text = "\n".join([f"🚗 {c}" for c in cars])
        await m.answer(f" in cars])
        await m.answer(f"️ Твой гараж:\n{cars_text️ Твой гараж:\n{cars_text}", parse_mode="HTML")
    else:
       }", parse_mode="HTML")
    else:
        await m.answer("🅿️ Пусто. await m.answer("🅿️ Пусто. /cars")

@dp.message(Command("inv"))
 /cars")

@dp.message(Command("inv"))
async def cmd_inv(m: Message):
    cid,async def cmd_inv(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    uid = m.chat.id, m.from_user.id
    async with pool.acquire() as conn:
        its = async with pool.acquire() as conn:
        its = await conn.fetch("SELECT item_name,rarity FROM inventory WHERE await conn.fetch("SELECT item_name,rarity FROM inventory WHERE chat_id=<LaTex>id_119</LaTex>2", cid, chat_id=<LaTex>id_120</LaTex>2", cid, uid)
    if not its: return await m.answer uid)
    if not its: return await m.answer("🎒 Пусто.")
    t =("🎒 Пусто.")
    t = "🎒 <b>Инвентарь "🎒 <b>Инвентарь:</b>\n"
    for i in its::</b>\n"
    for i in its:
        em = "🟡" if i['
        em = "🟡" if i['rarity']=="legendary" else "🔵" if i['rarity']=="rare" else "rarity']=="legendary" else "🔵" if i['rarity']=="rare" else ""
        t += f"{em} {i"
        t += f"{em} {i['item_name']}\n"
    await m.answer['item_name']}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command(t, parse_mode="HTML")

@dp.message(Command("rating"))
async def cmd_rating(m: Message):("rating"))
async def cmd_rating(m: Message):
    cid = m.chat.id
    async with pool
    cid = m.chat.id
    async with pool.acquire() as conn:
        rows = await conn.fetch.acquire() as conn:
        rows = await conn.fetch("SELECT u.user_id,u.balance,us.username FROM users("SELECT u.user_id,u.balance,us.username FROM users u LEFT JOIN usernames us ON u.chat_id=us.chat u LEFT JOIN usernames us ON u.chat_id=us.chat_id AND u.user_id=us.user_id WHERE u.chat_id AND u.user_id=us.user_id WHERE u.chat_id=<LaTex>id_121</LaTex>1 ORDER BY u.balance DESC LIMIT 10", cid)
    t = "🏆", cid)
    t = "🏆 <b>Рейтинг:</b>\n"
 <b>Рейтинг:</b>\n"
    for i, r in enumerate(rows, 1):    for i, r in enumerate(rows, 1):
        uname = r['username'] or f"User
        uname = r['username'] or f"User{r['user_id']}"
        t += f{r['user_id']}"
        t += f"{i}. <b>{uname}</b> — {"{i}. <b>{uname}</b> — {fmt_money(r['balance'])}\n"
    awaitfmt_money(r['balance'])}\n"
    await m.answer(t, parse_mode="HTML")

@dp m.answer(t, parse_mode="HTML")

@dp.message(Command("give"))
async def cmd_give.message(Command("give"))
async def cmd_give(m: Message):
    cid = m.chat.id
(m: Message):
    cid = m.chat.id
    if m.from_user.id not in ADMIN_IDS: return    if m.from_user.id not in ADMIN_IDS: return
    args = m.text.split()
    if len
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message:(args) < 2 or not m.reply_to_message: return await m.answer("/give сумма (ответ)")
 return await m.answer("/give сумма (ответ)")
    try: amt = int(args[1])
       try: amt = int(args[1])
    except: return await m.answer("❌ Число!")
    await update_balance(cid, m.reply_to_message except: return await m.answer("❌ Число!")
    await update_balance(cid, m.reply_to_message.from_user.id, amt)
    await m.answer(f.from_user.id, amt)
    await m.answer(f"✅ Выдано {fmt_money(amt)}.")"✅ Выдано {fmt_money(amt)}.")

@dp.message(Command("bank"))
async def cmd

@dp.message(Command("bank"))
async def cmd_bank(m: Message):
    cid, uid = m_bank(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    bd = await.chat.id, m.from_user.id
    bd = await get_bank(cid, uid)
    interest, _ = get_bank(cid, uid)
    interest, _ = await calc_interest(bd['deposit'], bd['last_interest_time'])
    t = f"🏦 < await calc_interest(bd['deposit'], bd['last_interest_time'])
    t = f"🏦 <b>Банк</b>\n💰 На счетуb>Банк</b>\n💰 На счету: <b>{fmt_money(bd['deposit'])}</: <b>{fmt_money(bd['deposit'])}</b>\n📈 Проценты: <b>+b>\n📈 Проценты: <b>+{fmt_money(interest)}</b>\n💹 {fmt_money(interest)}</b>\n💹 1% в сутки\n\n📥 /deposit1% в сутки\n\n📥 /deposit сумма\n📤 /withdraw сумма\n⚠ сумма\n📤 /withdraw сумма\n⚠️ Деньги в банке нельзя украсть!"
    await️ Деньги в банке нельзя украсть!"
    await m.answer(t, parse_mode="HTML")

@dp m.answer(t, parse_mode="HTML")

@dp.message(Command("deposit"))
async def cmd_deposit(m:.message(Command("deposit"))
async def cmd_deposit(m: Message):
    cid, uid = m.chat.id, Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split() m.from_user.id
    args = m.text.split()
    if len(args) < 2: return
    if len(args) < 2: return await m.answer("/deposit сумма")
    try await m.answer("/deposit сумма")
    try: amt = int(args[1])
   : amt = int(args[1])
    except: return await m.answer("❌ Число!")
    if amt < 100: return except: return await m.answer("❌ Число!")
    if amt < 100: return await m.answer("❌ Мин. 100 await m.answer("❌ Мин. 100")
    u = await get_user(cid, uid)")
    u = await get_user(cid, uid)
    if u['balance'] < amt: return await m.answer(f"❌ Мало ({fmt_money(u['balance'])})")
    await update_balance(cid,
    if u['balance'] < amt: return await m.answer(f"❌ Мало ({fmt_money(u['balance'])})")
    await update_balance(cid, uid, -amt)
    await update_bank(cid, uid, amt)
    bd = await get_bank(cid uid, -amt)
    await update_bank(cid, uid, amt)
    bd = await get_bank(cid, uid)
    await m.answer(f", uid)
    await m.answer(f" Вклад: <b>{fmt_money(amt)}</ Вклад: <b>{fmt_money(amt)}</b>. На счету: <b>{fmt_money(bdb>. На счету: <b>{fmt_money(bd['deposit'])}</b>", parse_mode="HTML")

@dp.message(Command("withdraw"))
async def cmd_with['deposit'])}</b>", parse_mode="HTML")

@dp.message(Command("withdraw"))
async def cmd_withdraw(m: Message):
    cid, uid = mdraw(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2.text.split()
    if len(args) < 2: return await m.answer("/withdraw сумма")
    try: return await m.answer("/withdraw сумма")
    try: amt = int(args[1])
   : amt = int(args[1])
    except: return await m.answer("❌ Число except: return await m.answer("❌ Число!")
    bd = await get_bank(cid, uid)!")
    bd = await get_bank(cid, uid)
    interest, new_time = await calc_interest(bd
    interest, new_time = await calc_interest(bd['deposit'], bd['last_interest_time'])
    if['deposit'], bd['last_interest_time'])
    if bd['deposit'] < amt: return await m.answer(f bd['deposit'] < amt: return await m.answer(f"❌ На счету {fmt_money(bd['deposit"❌ На счету {fmt_money(bd['deposit'])}")
    async with pool.acquire() as conn:'])}")
    async with pool.acquire() as conn:
        await conn.execute("UPDATE bank SET deposit=deposit
        await conn.execute("UPDATE bank SET deposit=deposit-<LaTex>id_122</LaTex>2 WHERE chat_id=<LaTex>id_123</LaTex>1,last_interest_time=<LaTex>id_124</LaTex>3 AND user_id=<LaTex>id_125</LaTex>4", amt, new_time, cid, uid)
    if interest > 0 and cid, uid)
    if interest > 0 and bd['deposit'] - amt > 0:
        bd['deposit'] - amt > 0:
        await update_bank(cid, uid, interest)
        await await update_bank(cid, uid, interest)
        await update_balance(cid, uid, interest)
    await update update_balance(cid, uid, interest)
    await update_balance(cid, uid, amt)
    nb = await_balance(cid, uid, amt)
    nb = await get_bank(cid, uid)
    t = f" get_bank(cid, uid)
    t = f"📤 Снято: <b>{fmt_money📤 Снято: <b>{fmt_money(amt)}</b>"
    if interest > 0(amt)}</b>"
    if interest > 0: t += f"\n📈 Проценты:: t += f"\n📈 Проценты: +{fmt_money(interest)}"
    t += +{fmt_money(interest)}"
    t += f"\nОстаток: <b>{fmt f"\nОстаток: <b>{fmt_money(nb['deposit'])}</b>"
    await m_money(nb['deposit'])}</b>"
    await m.answer(t, parse_mode="HTML")

@dp.message.answer(t, parse_mode="HTML")

@dp.message(Command("credit"))
async def cmd_credit(m: Message(Command("credit"))
async def cmd_credit(m: Message):
    cid, uid = m.chat.id, m):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
.from_user.id
    args = m.text.split()
    if len(args) < 2: return await m    if len(args) < 2: return await m.answer("💳 <b>Взять кредит</.answer("💳 <b>Взять кредит</b>\n\nИспользование: <b>/creditb>\n\nИспользование: <b>/credit сумма</b>\n\nУсловия:\n• Макс сумма</b>\n\nУсловия:\n• Максимум: 10x вашего баланса\n• Процентимум: 10x вашего баланса\n• Процент: 2% в день\n• Срок: 7: 2% в день\n• Срок: 7 дней\n• Штраф за просрочку: дней\n• Штраф за просрочку: АРЕСТ ИМУЩЕСТВА", parse_mode=" АРЕСТ ИМУЩЕСТВА", parse_mode="HTML")
    try: amount = int(args[HTML")
    try: amount = int(args[1])
    except: return await m.answer("1])
    except: return await m.answer("❌ Сумма должна быть числом!")
   ❌ Сумма должна быть числом!")
    if amount < 100: return await m.answer if amount < 100: return await m.answer("❌ Минимальный кредит: 100 сарапулок")
    loan = await get_loan("❌ Минимальный кредит: 100 сарапулок")
    loan = await get_loan(cid, uid)
    if loan['amount'] >(cid, uid)
    if loan['amount'] > 0: return await m.answer(f"❌ У вас уже есть кредит!\nДолг: {fmt 0: return await m.answer(f"❌ У вас уже есть кредит!\nДолг: {fmt_money(loan['amount'])}\nПроценты:_money(loan['amount'])}\nПроценты: {fmt_money(loan['interest'])}\n\nС {fmt_money(loan['interest'])}\n\nСначала погасите: /repay", parse_modeначала погасите: /repay", parse_mode="HTML")
    user = await get_user(cid,="HTML")
    user = await get_user(cid, uid)
    max_loan = user['balance'] * uid)
    max_loan = user['balance'] * CREDIT_MULTIPLIER
    if amount > max_loan: CREDIT_MULTIPLIER
    if amount > max_loan: return await m.answer(f"❌ Максимальный кредит return await m.answer(f"❌ Максимальный кредит: {fmt_money(max_loan)}")
    taken_at: {fmt_money(max_loan)}")
    taken_at = time.time()
    due_date = taken_at + = time.time()
    due_date = taken_at + (CREDIT_TERM_DAYS * 86400 (CREDIT_TERM_DAYS * 86400)
    await update_loan(cid, uid, amount,)
    await update_loan(cid, uid, amount, 0, taken_at, due_date)
    await 0, taken_at, due_date)
    await update_balance(cid, uid, amount)
    await m update_balance(cid, uid, amount)
    await m.answer(f"💳 <b>Кредит оформ.answer(f"💳 <b>Кредит оформлен!</b>\n\n💰 Получено: {лен!</b>\n\n💰 Получено: {fmt_money(amount)}\n📈 Процент:fmt_money(amount)}\n📈 Процент: 2% в день\n⏰ Вернуть 2% в день\n⏰ Вернуть до: {format_date(due_date)}\n\n до: {format_date(due_date)}\n\n⚠️ При просрочке — АРЕ⚠️ При просрочке — АРЕСТ ИМУЩЕСТВА!", parse_mode="HTML")СТ ИМУЩЕСТВА!", parse_mode="HTML")

@dp.message(Command("debt"))
async

@dp.message(Command("debt"))
async def cmd_debt(m: Message):
    cid, def cmd_debt(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    uid = m.chat.id, m.from_user.id
    loan = await get_loan(cid, uid)
    if loan = await get_loan(cid, uid)
    if loan['amount'] == 0: return await m.answer loan['amount'] == 0: return await m.answer("✅ У вас нет кредитов!")
    total_de("✅ У вас нет кредитов!")
    total_debt = loan['amount'] + loan['interest']
bt = loan['amount'] + loan['interest']
    days_left = int((loan['due_date'] -    days_left = int((loan['due_date'] - time.time()) / 86400)
 time.time()) / 86400)
    if days_left < 0: days_text = "    if days_left < 0: days_text = "🚔 ПРОСРОЧЕНО! ГРО🚔 ПРОСРОЧЕНО! ГРОЗИТ АРЕСТ ИМУЩЕСТВА!"
    elif days_left <= 2: days_text = fЗИТ АРЕСТ ИМУЩЕСТВА!"
    elif days_left <= 2: days_text = f"⚠️ Осталось: {days_left"⚠️ Осталось: {days_left} дн. Срочно погасите!"
} дн. Срочно погасите!"
    else: days_text = f"Осталось:    else: days_text = f"Осталось: {days_left} дн."
    await m.answer {days_left} дн."
    await m.answer(f"💳 <b>Ваш долг</b>\n\n📊 Основной долг: <b>{(f"💳 <b>Ваш долг</b>\n\n📊 Основной долг: <b>{fmt_money(loan['amount'])}</b>\nfmt_money(loan['amount'])}</b>\n Проценты: <b>{fmt_money(loan Проценты: <b>{fmt_money(loan['interest'])}</b>\n💰 Итого к['interest'])}</b>\n💰 Итого к возврату: <b>{fmt_money(total_debt)}</ возврату: <b>{fmt_money(total_debt)}</b>\n\n{days_text}\n\nПb>\n\n{days_text}\n\nПогасить: /repay сумма\nПогасогасить: /repay сумма\nПогасить всё: /repay_all", parse_mode="HTMLить всё: /repay_all", parse_mode="HTML")

@dp.message(Command("repay"))
async")

@dp.message(Command("repay"))
async def cmd_repay(m: Message):
    cid, def cmd_repay(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) args = m.text.split()
    if len(args) < 2: return await m.answer("💳 Использование < 2: return await m.answer("💳 Использование: <b>/repay сумма</b>", parse_mode: <b>/repay сумма</b>", parse_mode="HTML")
    try: amount = int(args[="HTML")
    try: amount = int(args[1])
    except: return await m.answer("❌ Сумма должна быть числом!")
   1])
    except: return await m.answer("❌ Сумма должна быть числом!")
    if amount <= 0: return await m.answer(" if amount <= 0: return await m.answer("❌ Сумма должна быть положительной!")
   ❌ Сумма должна быть положительной!")
    loan = await get_loan(cid, uid)
    if loan = await get_loan(cid, uid)
    if loan['amount'] == 0: return await m.answer loan['amount'] == 0: return await m.answer("✅ У вас нет кредитов!")
    user =("✅ У вас нет кредитов!")
    user = await get_user(cid, uid)
    if user[' await get_user(cid, uid)
    if user['balance'] < amount: return await m.answer(fbalance'] < amount: return await m.answer(f"❌ Недостаточно средств ({fmt_money(user['"❌ Недостаточно средств ({fmt_money(user['balance'])})")
    total_debt = loan['balance'])})")
    total_debt = loan['amount'] + loan['interest']
    if amount >amount'] + loan['interest']
    if amount > total_debt: amount = total_debt
    remaining total_debt: amount = total_debt
    remaining = amount
    interest_paid = min(remaining, loan = amount
    interest_paid = min(remaining, loan['interest'])
    remaining -= interest_paid
    principal['interest'])
    remaining -= interest_paid
    principal_paid = min(remaining, loan['amount'])
   _paid = min(remaining, loan['amount'])
    new_interest = loan['interest'] - interest_paid
    new_interest = loan['interest'] - interest_paid
    new_amount = loan['amount'] - principal_paid
    new_amount = loan['amount'] - principal_paid
    await update_balance(cid, uid, -amount)
    await update_balance(cid, uid, -amount)
    if new_amount <= 0:
        await clear_loan if new_amount <= 0:
        await clear_loan(cid, uid)
        await m.answer(f"✅(cid, uid)
        await m.answer(f"✅ <b>Кредит полностью погашен!</ <b>Кредит полностью погашен!</b>\n\nСписано: {fmt_money(amountb>\n\nСписано: {fmt_money(amount)}\nИз них проценты: {fmt_money(inter)}\nИз них проценты: {fmt_money(interest_paid)}\nОсновной долг: {fmt_moneyest_paid)}\nОсновной долг: {fmt_money(principal_paid)}", parse_mode="HTML")
   (principal_paid)}", parse_mode="HTML")
    else:
        await update_loan(cid, uid, new else:
        await update_loan(cid, uid, new_amount, new_interest, loan['taken_at'], loan['_amount, new_interest, loan['taken_at'], loan['due_date'])
        await m.answer(f"✅ <due_date'])
        await m.answer(f"✅ <b>Частичное погашение!</bb>Частичное погашение!</b>\n\nСписано: {fmt_money(amount)}\nОстаток долга: <b>{fmt>\n\nСписано: {fmt_money(amount)}\nОстаток долга: <b>{fmt_money(new_amount + new_interest)}</b>\n(ос_money(new_amount + new_interest)}</b>\n(основной: {fmt_money(new_amount)}, проценты:новной: {fmt_money(new_amount)}, проценты: {fmt_money(new_interest)})", parse_mode="HTML") {fmt_money(new_interest)})", parse_mode="HTML")

@dp.message(Command("repay_all"))
async

@dp.message(Command("repay_all"))
async def cmd_repay_all(m: Message):
    cid def cmd_repay_all(m: Message):
    cid, uid = m.chat.id, m.from_user.id
, uid = m.chat.id, m.from_user.id
    loan = await get_loan(cid, uid)
       loan = await get_loan(cid, uid)
    if loan['amount'] == 0: return await m if loan['amount'] == 0: return await m.answer("✅ У вас нет кредитов!")
    total.answer("✅ У вас нет кредитов!")
    total_debt = loan['amount'] + loan['interest']_debt = loan['amount'] + loan['interest']
    user = await get_user(cid, uid)

    user = await get_user(cid, uid)
    if user['balance'] < total_debt: return    if user['balance'] < total_debt: return await m.answer(f"❌ Недостаточно средств!\ await m.answer(f"❌ Недостаточно средств!\nНужно: {fmt_money(total_debt)}nНужно: {fmt_money(total_debt)}\nУ вас: {fmt_money(user['balance'])\nУ вас: {fmt_money(user['balance'])}\n\nИспользуйте /repay для частичного}\n\nИспользуйте /repay для частичного погашения", parse_mode="HTML")
    погашения", parse_mode="HTML")
    await update_balance(cid, uid, -total_debt) await update_balance(cid, uid, -total_debt)
    await clear_loan(cid, uid)
    await
    await clear_loan(cid, uid)
    await m.answer(f"✅ <b>Кредит полностью m.answer(f"✅ <b>Кредит полностью погашен!</b>\n\nС погашен!</b>\n\nСписано: <b>{fmt_money(total_debt)}</писано: <b>{fmt_money(total_debt)}</b>\n(основной долг: {fmt_moneyb>\n(основной долг: {fmt_money(loan['amount'])}, проценты: {fmt(loan['amount'])}, проценты: {fmt_money(loan['interest'])})", parse_mode="HTML_money(loan['interest'])})", parse_mode="HTML")

@dp.message(Command("bailout"))
")

@dp.message(Command("bailout"))
async def cmd_bailout(m: Message):
   async def cmd_bailout(m: Message):
    cid, uid = m.chat.id, m.from_user.id cid, uid = m.chat.id, m.from_user.id
    loan = await get_loan(cid, uid)

    loan = await get_loan(cid, uid)
    if loan['amount'] == 0: return    if loan['amount'] == 0: return await m.answer("✅ У вас нет активных кредитов.\ await m.answer("✅ У вас нет активных кредитов.\n\nЕсли имущество было арестовано — оно ужеn\nЕсли имущество было арестовано — оно уже конфисковано.\nНачинайте зарабатывать занов конфисковано.\nНачинайте зарабатывать заново через /work!", parse_mode="HTML")
   о через /work!", parse_mode="HTML")
    total_debt = loan['amount'] + loan['interest total_debt = loan['amount'] + loan['interest']
    bailout_cost = int(total_debt * ']
    bailout_cost = int(total_debt * 2)
    await m.answer(f"🚔2)
    await m.answer(f"🚔 <b>Информация о выкупе</b <b>Информация о выкупе</b>\n\nТекущий долг: <b>{fmt_money(total_debt)}</b>\nСтоимость выкупа>\n\nТекущий долг: <b>{fmt_money(total_debt)}</b>\nСтоимость выкупа: <b>{fmt_money(bailout_cost)}</b>\n\n⚠️ Выкуп возможен только ДО: <b>{fmt_money(bailout_cost)}</b>\n\n⚠️ Выкуп возможен только ДО ареста!\nПогасите долг через /rep ареста!\nПогасите долг через /repay_all чтобы избежать ареста.", parse_mode="HTMLay_all чтобы избежать ареста.", parse_mode="HTML")

@dp.message(Command("craft"))
async def")

@dp.message(Command("craft"))
async def cmd_craft(m: Message):
    t = " cmd_craft(m: Message):
    t = "🔨 <b>Крафт:</b>\n🔨 <b>Крафт:</b>\n"
    for k, v in CRAFT_RECIP"
    for k, v in CRAFT_RECIPES.items():
        req = ", ".join([fES.items():
        req = ", ".join([f"{c}× {n}" for n, c in"{c}× {n}" for n, c in v["requires"].items()])
        t += f v["requires"].items()])
        t += f"🔹 {v['name']} ({req})"🔹 {v['name']} ({req}) → /craft_item {k}\n"
    await → /craft_item {k}\n"
    await m.answer(t, parse_mode="HTML")

@dp m.answer(t, parse_mode="HTML")

@dp.message(Command("craft_item"))
async def cmd_craft.message(Command("craft_item"))
async def cmd_craft_item(m: Message):
    cid, uid = m_item(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2.text.split()
    if len(args) < 2: return await m.answer("/craft_item diamond"): return await m.answer("/craft_item diamond")
    ik = args[1]
    if ik
    ik = args[1]
    if ik not in CRAFT_RECIPES: return await m.answer not in CRAFT_RECIPES: return await m.answer("❌ Неизвестный рецепт")
    rec =("❌ Неизвестный рецепт")
    rec = CRAFT_RECIPES[ik]
    async with CRAFT_RECIPES[ik]
    async with pool.acquire() as conn:
        items = await conn pool.acquire() as conn:
        items = await conn.fetch("SELECT item_name FROM inventory WHERE chat_id=<LaTex>id_126</LaTex>1 AND user_id=<LaTex>id_127</LaTex>2", cid, uid)
    inv = {}
    for i in items: inv[i inv = {}
    for i in items: inv[i['item_name']] = inv.get(i['item_name'],['item_name']] = inv.get(i['item_name'], 0) + 1
    for rn, rc 0) + 1
    for rn, rc in rec["requires"].items():
        if inv.get in rec["requires"].items():
        if inv.get(rn, 0) < rc: return await m(rn, 0) < rc: return await m.answer(f"❌ Нужно {rc}× {rn.answer(f"❌ Нужно {rc}× {rn} (есть {inv.get(rn, 0} (есть {inv.get(rn, 0)})")
    async with pool.acquire() as conn:)})")
    async with pool.acquire() as conn:
        for rn, rc in rec["requires"].items
        for rn, rc in rec["requires"].items():
            await conn.execute("DELETE FROM inventory WHERE id():
            await conn.execute("DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE chat_id=<LaTex>id_128</LaTex>1 AND user_id=<LaTex>id_129</LaTex>3 LIMIT <LaTex>id_130</LaTex>2 AND item_name=<LaTex>id_131</LaTex>4)", cid, uid, rn, rc)
        await)", cid, uid, rn, rc)
        await conn.execute("INSERT INTO inventory (chat_id,user_id,item conn.execute("INSERT INTO inventory (chat_id,user_id,item_name,item_type,rarity) VALUES (<LaTex>id_132</LaTex>2,<LaTex>id_133</LaTex>1,<LaTex>id_134</LaTex>3,'crafted',<LaTex>id_135</LaTex>4)", cid, uid, rec["name"], rec["rarity"])
    await m.answername"], rec["rarity"])
    await m.answer(f"✅ Скрафчено: <b>{rec(f"✅ Скрафчено: <b>{rec['name']}</b>", parse_mode="HTML")

@['name']}</b>", parse_mode="HTML")

@dp.message(Command("trade"))
async def cmd_trade(mdp.message(Command("trade"))
async def cmd_trade(m: Message):
    cid, uid = m.chat.id: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split, m.from_user.id
    args = m.text.split()
    if len(args) < 4 or not()
    if len(args) < 4 or not m.reply_to_message: return await m.answer("/ m.reply_to_message: return await m.answer("/trade @user предмет кол-во (ответ)")
    tid = m.reply_to_message.from_user.id
    intrade @user предмет кол-во (ответ)")
    tid = m.reply_to_message.from_user.id
    iname = args[2]
    try: cntame = args[2]
    try: cnt = int(args[3])
    except: return = int(args[3])
    except: return await m.answer("❌ Число!")
    if await m.answer("❌ Число!")
    if cnt <= 0 or tid == uid: return await m cnt <= 0 or tid == uid: return await m.answer("❌ Ошибка")
    async with pool.answer("❌ Ошибка")
    async with pool.acquire() as conn:
        have = await conn.fetch.acquire() as conn:
        have = await conn.fetchval("SELECT COUNT(*) FROM inventory WHERE chat_id=<LaTex>id_136</LaTex>1 AND user_id=<LaTex>id_137</LaTex>3", cid AND user_id=<LaTex>id_138</LaTex>3", cid, uid, iname)
    if have < cnt, uid, iname)
    if have < cnt: return await m.answer(f"❌ Нет {cnt: return await m.answer(f"❌ Нет {cnt}× {iname}")
    async with pool.acquire()}× {iname}")
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT as conn:
        rows = await conn.fetch("SELECT item_name,item_type,rarity FROM inventory WHERE chat_id=<LaTex>id_139</LaTex>1 AND user_id=<LaTex>id_140</LaTex>3 LIMIT1 AND user_id=<LaTex>id_141</LaTex>3 LIMIT <LaTex>id_142</LaTex>4", cid, uid, iname, cnt)
        await conn.execute("DELETE FROM inventory WHERE id IN
        await conn.execute("DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE chat_id=<LaTex>id_143</LaTex>1 AND user_id=<LaTex>id_144</LaTex>3 LIMIT <LaTex>id_145</LaTex>2 AND item_name=<LaTex>id_146</LaTex>4)", cid, uid, iname, cnt)
        for cid, uid, iname, cnt)
        for row in rows:
            await conn.execute("INSERT INTO row in rows:
            await conn.execute("INSERT INTO inventory (chat_id,user_id,item_name,item_type,r inventory (chat_id,user_id,item_name,item_type,rarity) VALUES (<LaTex>id_147</LaTex>2,<LaTex>id_148</LaTex>4,<LaTex>id_149</LaTex>1,<LaTex>id_150</LaTex>3,<LaTex>id_151</LaTex>5)", cid, tid, row['item_name'], row5)", cid, tid, row['item_name'], row['item_type'], row['rarity'])
    await['item_type'], row['rarity'])
    await m.answer(f"✅ Передано {cnt}× { m.answer(f"✅ Передано {cnt}× {iname}", parse_mode="HTML")

@dp.message(Commandiname}", parse_mode="HTML")

@dp.message(Command("education"))
async def cmd_education(m: Message("education"))
async def cmd_education(m: Message):
    cid, uid = m.chat.id, m):
    cid, uid = m.chat.id, m.from_user.id
    edu = await get_education(cid.from_user.id
    edu = await get_education(cid, uid)
    t = "🎓 <, uid)
    t = "🎓 <b>Образование:</b>\n"
   b>Образование:</b>\n"
    for k, c in COURSES.items():
        done for k, c in COURSES.items():
        done = k in edu['completed_courses'] or (k==' = k in edu['completed_courses'] or (k=='mba' and edu['has_mba'])
       mba' and edu['has_mba'])
        st = "✅" if done else "🔒 st = "✅" if done else "🔒"
        t += f"{st} {c['"
        t += f"{st} {c['name']} ({fmt_money(c['price'])}) →name']} ({fmt_money(c['price'])}) → /buy_course {k}\n"
    await m /buy_course {k}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message.answer(t, parse_mode="HTML")

@dp.message(Command("buy_course"))
async def cmd_buy_course(m(Command("buy_course"))
async def cmd_buy_course(m: Message):
    cid, uid = m.chat.id: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split, m.from_user.id
    args = m.text.split()
    if len(args) < 2 or args()
    if len(args) < 2 or args[1] not in COURSES: return await m.answer[1] not in COURSES: return await m.answer("/education")
    ck = args[1]
    c = COURSES[ck]
    edu =("/education")
    ck = args[1]
    c = COURSES[ck]
    edu = await get_education(cid, uid)
    if ck await get_education(cid, uid)
    if ck in edu['completed_courses'] or (ck=='mba in edu['completed_courses'] or (ck=='mba' and edu['has_mba']): return await m.answer' and edu['has_mba']): return await m.answer("✅ Уже пройдено")
    u = await get("✅ Уже пройдено")
    u = await get_user(cid, uid)
    if u['balance']_user(cid, uid)
    if u['balance'] < c['price']: return await m.answer(f < c['price']: return await m.answer(f"❌ Нужно {fmt_money(c['price'])}")"❌ Нужно {fmt_money(c['price'])}")
    await update_balance(cid, uid, -c['
    await update_balance(cid, uid, -c['price'])
    exam_sessions[f"{cid}_{uid}price'])
    exam_sessions[f"{cid}_{uid}"] = {"course": ck, "question": 0"] = {"course": ck, "question": 0, "correct": 0}
    q = c, "correct": 0}
    q = c['questions'][0]
    await m.answer(f"['questions'][0]
    await m.answer(f"✅ Курс оплачен!\n\n📝 <b✅ Курс оплачен!\n\n📝 <b>Экзамен:</b> 2 из 3>Экзамен:</b> 2 из 3 верно.\n\nВопрос 1:\n<b верно.\n\nВопрос 1:\n<b>{q['q']}</b>\n\n{' | '.>{q['q']}</b>\n\n{' | '.join([f'{i+1}. {a}' forjoin([f'{i+1}. {a}' for i,a in enumerate(q['a'])])}\n i,a in enumerate(q['a'])])}\n\nНапишите номер (1, 2, 3\nНапишите номер (1, 2, 3)", parse_mode="HTML")

@dp.message(F.text)", parse_mode="HTML")

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_exam & ~F.text.startswith('/'))
async def handle_exam_answer(m: Message):
    if m.chat.type not_answer(m: Message):
    if m.chat.type not in ['group', 'supergroup']: return in ['group', 'supergroup']: return
    cid, uid = m.chat.id, m.from
    cid, uid = m.chat.id, m.from_user.id
    ek = f"{cid}_{uid}"_user.id
    ek = f"{cid}_{uid}"
    if ek not in exam_sessions: return
    if ek not in exam_sessions: return
    ex = exam_sessions[ek]
    c
    ex = exam_sessions[ek]
    c = COURSES[ex['course']]
    try: = COURSES[ex['course']]
    try: ans = int(m.text) - 1
    except ans = int(m.text) - 1
    except: return await m.answer("❌ Номер ответа: return await m.answer("❌ Номер ответа (1, 2, 3)")
    if (1, 2, 3)")
    if ans < 0 or ans > 2: return ans < 0 or ans > 2: return await m.answer("❌ Номер ответа (1,  await m.answer("❌ Номер ответа (1, 2, 3)")
    q = c['questions2, 3)")
    q = c['questions'][ex['question']]
    if ans == q[''][ex['question']]
    if ans == q['correct']:
        ex['correct'] += 1
correct']:
        ex['correct'] += 1
        await m.answer("✅ Верно!")
    else        await m.answer("✅ Верно!")
    else:
        await m.answer(f"❌ Невер:
        await m.answer(f"❌ Неверно! Ответ: {q['a'][q['correctно! Ответ: {q['a'][q['correct']]}")
    ex['question'] += 1']]}")
    ex['question'] += 1
    if ex['question'] < 3:

    if ex['question'] < 3:
        q = c['questions'][ex['question']]
        q = c['questions'][ex['question']]
        await m.answer(f"Вопрос {ex['        await m.answer(f"Вопрос {ex['question']+1}:\n<b>{q['q']}</question']+1}:\n<b>{q['q']}</b>\n\n{' | '.join([f'{ib>\n\n{' | '.join([f'{i+1}. {a}' for i,a in enumerate(q+1}. {a}' for i,a in enumerate(q['a'])])}\n\nНапишите номер (1['a'])])}\n\nНапишите номер (1, 2, 3)", parse_mode="HTML"), 2, 3)", parse_mode="HTML")
    else:
        if ex['correct'] >=
    else:
        if ex['correct'] >= 2:
            await complete_course(cid, uid, 2:
            await complete_course(cid, uid, ex['course'])
            await m.answer(f" ex['course'])
            await m.answer(f" <b>Сдано!</b> Курс <b>Сдано!</b> Курс <b>{c['name']}</b> завершён <b>{c['name']}</b> завершён!", parse_mode="HTML")
        else:
           !", parse_mode="HTML")
        else:
            await m.answer(f"😔 <b>Пров await m.answer(f"😔 <b>Провал.</b> Правильных: {ex['correctал.</b> Правильных: {ex['correct']}/3.\nПопробуйте: /buy']}/3.\nПопробуйте: /buy_course {ex['course']}", parse_mode="HTML")_course {ex['course']}", parse_mode="HTML")
        del exam_sessions[ek]

# =================
        del exam_sessions[ek]

# ==================== БЛЭКДЖЕК ====================
def=== БЛЭКДЖЕК ====================
def create_deck():
    suits = ['♠', ' create_deck():
    suits = ['♠', '♥', '♦', '♣']
    ranks♥', '♦', '♣']
    ranks = ['2', '3', '4', '5 = ['2', '3', '4', '5', '6', '7', '8', '9', '6', '7', '8', '9', '10', 'J', 'Q', '', '10', 'J', 'Q', 'K', 'A']
    deck = [(r,K', 'A']
    deck = [(r, s) for s in suits for r in ranks]
 s) for s in suits for r in ranks]
    random.shuffle(deck)
    return deck

def    random.shuffle(deck)
    return deck

def card_value(card):
    r = card[0] card_value(card):
    r = card[0]
    if r in ['J', 'Q', '
    if r in ['J', 'Q', 'K']: return 10
    if r ==K']: return 10
    if r == 'A': return 11
    return int(r 'A': return 11
    return int(r)

def calc_score(cards):
    score = sum)

def calc_score(cards):
    score = sum(card_value(c) for c in cards)
    a(card_value(c) for c in cards)
    aces = sum(1 for c in cards if c[ces = sum(1 for c in cards if c[0] == 'A')
    while score > 0] == 'A')
    while score > 21 and aces > 0:
        score21 and aces > 0:
        score -= 10
        aces -= 1
 -= 10
        aces -= 1
    return score

def show_cards(cards, hide_first=False    return score

def show_cards(cards, hide_first=False):
    if hide_first: return f"):
    if hide_first: return f" + {' '.join(f'{r}{s}' for + {' '.join(f'{r}{s}' for r,s in cards[1:])}"
    return ' r,s in cards[1:])}"
    return ' '.join(f'{r}{s}' for r,s in '.join(f'{r}{s}' for r,s in cards)

@dp.message(Command("blackjack"))
 cards)

@dp.message(Command("blackjack"))
async def blackjack_start(m: Message, state: FSMContextasync def blackjack_start(m: Message, state: FSMContext):
    cid, uid = m.chat.id, m):
    cid, uid = m.chat.id, m.from_user.id
    if cid in bj_tables: return.from_user.id
    if cid in bj_tables: return await m.answer("🎰 Игра идёт!")
    await m.answer("🎰 Игра идёт!")
    u = await get_user(cid, uid)
    if u = await get_user(cid, uid)
    if u['balance'] < BJ_MIN_BALANCE: return u['balance'] < BJ_MIN_BALANCE: return await m.answer(f"❌ Нужно {BJ_MIN_BAL await m.answer(f"❌ Нужно {BJ_MIN_BALANCE}+ ({fmt_money(u['balance'])})")ANCE}+ ({fmt_money(u['balance'])})")
    bj_tables[cid] = {"players": {
    bj_tables[cid] = {"players": {uid: {"name": m.from_user.first_name, "uid: {"name": m.from_user.first_name, "bet": 0, "cards": [], "stand":bet": 0, "cards": [], "stand": False, "busted": False}}, "order": [ False, "busted": False}}, "order": [uid], "stage": "waiting", "creator": uiduid], "stage": "waiting", "creator": uid}
    kb = InlineKeyboardMarkup(inline_keyboard=[[}
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Присоединиться",InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"bj_join_{cid}")], [Inline callback_data=f"bj_join_{cid}")], [InlineKeyboardButton(text="❌ Отменить игру", callback_dataKeyboardButton(text="❌ Отменить игру", callback_data=f"bj_cancel_{cid}")]])
    await m=f"bj_cancel_{cid}")]])
    await m.answer(f"🎩 <b>Игорё.answer(f"🎩 <b>Игорёчек открывает стол!</b>\n\n👤чек открывает стол!</b>\n\n👤 {m.from_user.first_name}\n👥  {m.from_user.first_name}\n👥 1/{BJ_MAX_PLAYERS}\n⏳ {1/{BJ_MAX_PLAYERS}\n⏳ {BJ_WAIT_TIME} сек\n\nНажмите кнопку!\nBJ_WAIT_TIME} сек\n\nНажмите кнопку!\nСоздатель может отменить игру.", reply_markup=Создатель может отменить игру.", reply_markup=kb, parse_mode="HTML")
    await state.setkb, parse_mode="HTML")
    await state.set_state(BlackjackStates.waiting)
    await asyncio_state(BlackjackStates.waiting)
    await asyncio.sleep(BJ_WAIT_TIME)
    if cid not in.sleep(BJ_WAIT_TIME)
    if cid not in bj_tables: return
    t = bj_tables[cid bj_tables: return
    t = bj_tables[cid]
    if len(t["players"]) < 2]
    if len(t["players"]) < 2:
        await m.answer("😔 Мало игроков.:
        await m.answer("😔 Мало игроков. Стол закрыт.")
        del bj_tables[c Стол закрыт.")
        del bj_tables[cid]
        await state.clear()
        return
id]
        await state.clear()
        return
    t["stage"] = "betting"
       t["stage"] = "betting"
    pl = ", ".join(p["name"] for p in pl = ", ".join(p["name"] for p in t["players"].values())
    for uid in t t["players"].values())
    for uid in t["order"]:
        if uid == t["creator"]:["order"]:
        if uid == t["creator"]:
            bk = InlineKeyboardMarkup(inline_keyboard=[[
            bk = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="100", callback_data=fInlineKeyboardButton(text="100", callback_data=f"bet_100_{cid}"), InlineKeyboard"bet_100_{cid}"), InlineKeyboardButton(text="200", callback_data=f"betButton(text="200", callback_data=f"bet_200_{cid}")], [InlineKeyboard_200_{cid}")], [InlineKeyboardButton(text="500", callback_data=f"betButton(text="500", callback_data=f"bet_500_{cid}"), InlineKeyboardButton(text_500_{cid}"), InlineKeyboardButton(text="1000", callback_data=f"bet_="1000", callback_data=f"bet_1000_{cid}")], [InlineKeyboard1000_{cid}")], [InlineKeyboardButton(text="❌ Отменить игру", callback_data=fButton(text="❌ Отменить игру", callback_data=f"bj_cancel_{cid}")]])
        else:"bj_cancel_{cid}")]])
        else:
            bk = InlineKeyboardMarkup(inline_keyboard=[[Inline
            bk = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="100", callback_data=f"KeyboardButton(text="100", callback_data=f"bet_100_{cid}"), InlineKeyboardButtonbet_100_{cid}"), InlineKeyboardButton(text="200", callback_data=f"bet_(text="200", callback_data=f"bet_200_{cid}")], [InlineKeyboardButton(text200_{cid}")], [InlineKeyboardButton(text="500", callback_data=f"bet_5="500", callback_data=f"bet_500_{cid}"), InlineKeyboardButton(text="100_{cid}"), InlineKeyboardButton(text="1000", callback_data=f"bet_10000", callback_data=f"bet_1000_{cid}")]])
        try:00_{cid}")]])
        try: await bot.send_message(uid, f"🎩 < await bot.send_message(uid, f"🎩 <b>Ваша ставка?</b>", reply_markup=bb>Ваша ставка?</b>", reply_markup=bk, parse_mode="HTML")
        except: awaitk, parse_mode="HTML")
        except: await m.answer(f"⚠️ {t['players m.answer(f"⚠️ {t['players'][uid]['name']}, напишите боту в'][uid]['name']}, напишите боту в ЛС!")
    await m.answer(f" ЛС!")
    await m.answer(f" <b>Игроки:</b> {pl <b>Игроки:</b> {pl}\n\n💰 Проверьте личку!", parse_mode}\n\n💰 Проверьте личку!", parse_mode="HTML")

@dp.callback_query(lambda c: c="HTML")

@dp.callback_query(lambda c: c.data.startswith("bj_join_"))
async def blackjack_join.data.startswith("bj_join_"))
async def blackjack_join(cb: types.CallbackQuery, state: FSMContext):
(cb: types.CallbackQuery, state: FSMContext):
    cid = int(cb.data.split("_")[2])
    cid = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    if cid not    uid = cb.from_user.id
    if cid not in bj_tables: return await cb.answer("Стол закры in bj_tables: return await cb.answer("Стол закрыт!", show_alert=True)
    t = bj_tablesт!", show_alert=True)
    t = bj_tables[cid]
    if t["stage"] != "[cid]
    if t["stage"] != "waiting": return await cb.answer("Началасьwaiting": return await cb.answer("Началась!", show_alert=True)
    if uid in t["!", show_alert=True)
    if uid in t["players"]: return await cb.answer("Вы уже тут!",players"]: return await cb.answer("Вы уже тут!", show_alert=True)
    if len(t["players"]) show_alert=True)
    if len(t["players"]) >= BJ_MAX_PLAYERS: return await cb.answer(" >= BJ_MAX_PLAYERS: return await cb.answer("Мест нет!", show_alert=True)
    u =Мест нет!", show_alert=True)
    u = await get_user(cid, uid)
    if u[' await get_user(cid, uid)
    if u['balance'] < BJ_MIN_BALANCE: return await cb.answerbalance'] < BJ_MIN_BALANCE: return await cb.answer(f"Нужно {BJ_MIN_BALANCE}+(f"Нужно {BJ_MIN_BALANCE}+ ({fmt_money(u['balance'])})", show_alert=True) ({fmt_money(u['balance'])})", show_alert=True)
    t["players"][uid] = {"name":
    t["players"][uid] = {"name": cb.from_user.first_name, "bet": 0, cb.from_user.first_name, "bet": 0, "cards": [], "stand": False, "busted "cards": [], "stand": False, "busted": False}
    t["order"].append(uid)": False}
    t["order"].append(uid)
    await cb.answer("✅ Присоединили
    await cb.answer("✅ Присоединились!")
    pl = "\n".join([fсь!")
    pl = "\n".join([f"• {p['name']}" for p in t"• {p['name']}" for p in t["players"].values()])
    kb = InlineKeyboard["players"].values()])
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ ПрMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"bj_join_{исоединиться", callback_data=f"bj_join_{cid}")], [InlineKeyboardButton(text="❌cid}")], [InlineKeyboardButton(text="❌ Отменить игру", callback_data=f"bj_cancel_{cid Отменить игру", callback_data=f"bj_cancel_{cid}")]])
    try: await cb.message.edit_text}")]])
    try: await cb.message.edit_text(f"🎩 <b>Игроки ({(f"🎩 <b>Игроки ({len(t['players'])}/{BJ_MAX_PLAYERS}):\len(t['players'])}/{BJ_MAX_PLAYERS}):\n{pl}\n\n⏳ Ждёмn{pl}\n\n⏳ Ждём...</b>", reply_markup=kb, parse_mode="...</b>", reply_markup=kb, parse_mode="HTML")
    except: pass

@dp.callback_queryHTML")
    except: pass

@dp.callback_query(lambda c: c.data.startswith("bj_cancel_"))
(lambda c: c.data.startswith("bj_cancel_"))
async def blackjack_cancel(cb: types.CallbackQuery, state:async def blackjack_cancel(cb: types.CallbackQuery, state: FSMContext):
    cid = int(cb.data.split("_ FSMContext):
    cid = int(cb.data.split("_")[2])
    uid = cb.from_user.id
")[2])
    uid = cb.from_user.id
    if cid not in bj_tables: return await cb.answer    if cid not in bj_tables: return await cb.answer("Игра уже завершена!", show_alert=True)
("Игра уже завершена!", show_alert=True)
    t = bj_tables[cid]
    if uid    t = bj_tables[cid]
    if uid != t["creator"]: return await cb.answer(" != t["creator"]: return await cb.answer("❌ Отменить может только создатель!", show_alert=True❌ Отменить может только создатель!", show_alert=True)
    if t["stage"] == "playing":)
    if t["stage"] == "playing": return await cb.answer("❌ Игра уже началась!", show return await cb.answer("❌ Игра уже началась!", show_alert=True)
    refunded = []
    for pid_alert=True)
    refunded = []
    for pid, pd in t["players"].items():
        if, pd in t["players"].items():
        if pd["bet"] > 0:
            await update pd["bet"] > 0:
            await update_balance(cid, pid, pd["bet"])
            refunded_balance(cid, pid, pd["bet"])
            refunded.append(f"• {pd['name']}: +{.append(f"• {pd['name']}: +{fmt_money(pd['bet'])}")
    del bjfmt_money(pd['bet'])}")
    del bj_tables[cid]
    await state.clear()
   _tables[cid]
    await state.clear()
    rt = "\n".join(refunded) if refunded else rt = "\n".join(refunded) if refunded else "Никто не успел поставить"
    try "Никто не успел поставить"
    try: await cb.message.edit_text(f"❌ <b: await cb.message.edit_text(f"❌ <b>Игра отменена!</b>\n\n>Игра отменена!</b>\n\n {cb.from_user.first_name}\n\n {cb.from_user.first_name}\n\n Возврат:\n{rt}", parse_mode=" Возврат:\n{rt}", parse_mode="HTML")
    except: pass
    await cbHTML")
    except: pass
    await cb.answer("✅ Игра отменена!")

@dp.callback.answer("✅ Игра отменена!")

@dp.callback_query(lambda c: c.data.startswith("bet_"))
_query(lambda c: c.data.startswith("bet_"))
async def blackjack_bet(cb: types.CallbackQuery, state:async def blackjack_bet(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split("_") FSMContext):
    parts = cb.data.split("_")
    bet = int(parts[1])
    cid
    bet = int(parts[1])
    cid = int(parts[2])
    uid = cb.from = int(parts[2])
    uid = cb.from_user.id
    if cid not in bj_tables: return_user.id
    if cid not in bj_tables: return await cb.answer("Нет игры!", show_alert=True)
 await cb.answer("Нет игры!", show_alert=True)
    t = bj_tables[cid]
    if uid    t = bj_tables[cid]
    if uid not in t["players"]: return await cb.answer(" not in t["players"]: return await cb.answer("Не в игре!", show_alert=True)
    if tНе в игре!", show_alert=True)
    if t["players"][uid]["bet"] > 0: return["players"][uid]["bet"] > 0: return await cb.answer("Ставка есть!", show_alert=True) await cb.answer("Ставка есть!", show_alert=True)
    u = await get_user(cid, uid)

    u = await get_user(cid, uid)
    if u['balance'] < bet: return await cb    if u['balance'] < bet: return await cb.answer(f"Мало ({fmt_money(u['balance']).answer(f"Мало ({fmt_money(u['balance'])})", show_alert=True)
    await update_balance(cid,})", show_alert=True)
    await update_balance(cid, uid, -bet)
    t["players"][uid uid, -bet)
    t["players"][uid]["bet"] = bet
    try: await]["bet"] = bet
    try: await cb.message.edit_text(f"✅ Ставка: <b cb.message.edit_text(f"✅ Ставка: <b>{bet}</b>. Ждём...", parse_mode=">{bet}</b>. Ждём...", parse_mode="HTML")
    except: pass
    await cbHTML")
    except: pass
    await cb.answer(f"Ставка {bet} принята!")
.answer(f"Ставка {bet} принята!")
    if all(p["bet"] > 0 for p    if all(p["bet"] > 0 for p in t["players"].values()): await blackjack_deal(cid in t["players"].values()): await blackjack_deal(cid, state)

async def blackjack_deal(cid, state, state)

async def blackjack_deal(cid, state):
    t = bj_tables[cid]
   ):
    t = bj_tables[cid]
    t["deck"] = create_deck()
    for uid t["deck"] = create_deck()
    for uid in t["order"]: t["players"][uid in t["order"]: t["players"][uid]["cards"] = [t["deck"].pop(), t]["cards"] = [t["deck"].pop(), t["deck"].pop()]
    t["dealer"] =["deck"].pop()]
    t["dealer"] = [t["deck"].pop(), t["deck"].pop [t["deck"].pop(), t["deck"].pop()]
    t["stage"] = "playing"
()]
    t["stage"] = "playing"
    pi = "\n".join([f"    pi = "\n".join([f" {p['name']}: {p['bet'] {p['name']}: {p['bet']}" for p in t["players"].values()])
}" for p in t["players"].values()])
    await bot.send_message(cid, f"🎩    await bot.send_message(cid, f"🎩 <b>Карты розданы!</b>\ <b>Карты розданы!</b>\n\n🤖 Мои: {show_cards(t['n\n🤖 Мои: {show_cards(t['dealer'], True)}\n\n{pi}\n\ndealer'], True)}\n\n{pi}\n\n🎮 Ходит: <b>{t['🎮 Ходит: <b>{t['players'][t['order'][0]]['name']}</bplayers'][t['order'][0]]['name']}</b>", parse_mode="HTML")
    await state.set_state>", parse_mode="HTML")
    await state.set_state(BlackjackStates.playing)
    await blackjack_player(BlackjackStates.playing)
    await blackjack_player_turn(cid, t["order"][0], state)

_turn(cid, t["order"][0], state)

async def blackjack_player_turn(cid, uid, state):
async def blackjack_player_turn(cid, uid, state):
    t = bj_tables[cid]
    p =    t = bj_tables[cid]
    p = t["players"][uid]
    kb = InlineKeyboard t["players"][uid]
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Markup(inline_keyboard=[[InlineKeyboardButton(text=" Ещё", callback_data=f"hit_{uid}_{cid Ещё", callback_data=f"hit_{uid}_{cid}"), InlineKeyboardButton(text="✋ Хватит}"), InlineKeyboardButton(text="✋ Хватит", callback_data=f"stand_{uid}_{cid}")", callback_data=f"stand_{uid}_{cid}")]])
    await bot.send_message(uid, f"]])
    await bot.send_message(uid, f" <b>Ваш ход!</b>\n <b>Ваш ход!</b>\n\n🃏 Ваши: {show_cards(p['cards\n🃏 Ваши: {show_cards(p['cards'])}\n🔢 Сумма: <b'])}\n🔢 Сумма: <b>{calc_score(p['cards'])}</b>\n>{calc_score(p['cards'])}</b>\n Ставка: {p['bet']}\n\n Ставка: {p['bet']}\n\n🎴 Карта Игорёчка: {t['dealer🎴 Карта Игорёчка: {t['dealer'][0][0]}{t['dealer'][0]['][0][0]}{t['dealer'][0][1]}", reply_markup=kb, parse_mode="HTML1]}", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith")

@dp.callback_query(lambda c: c.data.startswith("hit_") or c.data.startswith("stand_"))("hit_") or c.data.startswith("stand_"))
async def blackjack_hit_stand(cb: types.CallbackQuery,
async def blackjack_hit_stand(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split state: FSMContext):
    parts = cb.data.split("_")
    act = parts[0]
   ("_")
    act = parts[0]
    uid = int(parts[1])
    cid = int uid = int(parts[1])
    cid = int(parts[2])
    if cid not in bj_tables(parts[2])
    if cid not in bj_tables: return await cb.answer("Нет игры!", show: return await cb.answer("Нет игры!", show_alert=True)
    t = bj_tables[cid]_alert=True)
    t = bj_tables[cid]
    p = t["players"][uid]
   
    p = t["players"][uid]
    if act == "hit":
        c = t[" if act == "hit":
        c = t["deck"].pop()
        p["cards"].append(cdeck"].pop()
        p["cards"].append(c)
        sc = calc_score(p["cards"])
)
        sc = calc_score(p["cards"])
        await cb.message.edit_text(f"🎩 В        await cb.message.edit_text(f"🎩 Взял карту!\n\n🃏 +{cзял карту!\n\n🃏 +{c[0]}{c[1]}\n[0]}{c[1]}\n {show_cards(p['cards'])}\n {show_cards(p['cards'])}\n Сумма: <b>{sc}</b Сумма: <b>{sc}</b>", parse_mode="HTML")
        if sc > >", parse_mode="HTML")
        if sc > 21:
            p["stand"] = True
21:
            p["stand"] = True
            p["busted"] = True
            await cb            p["busted"] = True
            await cb.message.answer(f"💥 <b>Перебор ({.message.answer(f"💥 <b>Перебор ({sc})!</b>", parse_mode="HTML")
           sc})!</b>", parse_mode="HTML")
            await blackjack_next_turn(cid, state)
        elif sc await blackjack_next_turn(cid, state)
        elif sc == 21:
            p["stand"] = == 21:
            p["stand"] = True
            await cb.message.answer(f"🎉 True
            await cb.message.answer(f"🎉 <b>21!</b>")
            await blackjack <b>21!</b>")
            await blackjack_next_turn(cid, state)
        else:
           _next_turn(cid, state)
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🃏 Ещё", callback_data=f"hit_{uid}_{cid}"), InlineKeyboardButton(text="(text="🃏 Ещё", callback_data=f"hit_{uid}_{cid}"), InlineKeyboardButton(text=" Хватит", callback_data=f"stand_{uid Хватит", callback_data=f"stand_{uid}_{cid}")]])
            await cb.message.answer}_{cid}")]])
            await cb.message.answer(f"💰 Сумма: {sc}. Ещё(f"💰 Сумма: {sc}. Ещё?", reply_markup=kb)
    elif act == "?", reply_markup=kb)
    elif act == "stand":
        p["stand"] = True
       stand":
        p["stand"] = True
        await cb.message.edit_text(f"✋ Остановился await cb.message.edit_text(f"✋ Остановился на <b>{calc_score(p['cards'])}</b на <b>{calc_score(p['cards'])}</b>", parse_mode="HTML")
        await blackjack_next_turn>", parse_mode="HTML")
        await blackjack_next_turn(cid, state)

async def blackjack_next_turn(cid,(cid, state)

async def blackjack_next_turn(cid, state):
    t = bj_tables[cid]
 state):
    t = bj_tables[cid]
    nxt = next((u for u in t["order    nxt = next((u for u in t["order"] if not t["players"][u]["stand"]), None"] if not t["players"][u]["stand"]), None)
    if nxt:
        await bot.send_message)
    if nxt:
        await bot.send_message(cid, f"🎮 Ходит: <(cid, f"🎮 Ходит: <b>{t['players'][nxt]['name']}</b>{t['players'][nxt]['name']}</b>", parse_mode="HTML")
        await blackjack_playerb>", parse_mode="HTML")
        await blackjack_player_turn(cid, nxt, state)
    else:
_turn(cid, nxt, state)
    else:
        await blackjack_dealer_play(cid, state)

async        await blackjack_dealer_play(cid, state)

async def blackjack_dealer_play(cid, state):
    t def blackjack_dealer_play(cid, state):
    t = bj_tables[cid]
    await bot.send_message = bj_tables[cid]
    await bot.send_message(cid, f"🎩 <b>Ход(cid, f"🎩 <b>Ход Игорёчка!</b>\n\n🤖 Мои Игорёчка!</b>\n\n🤖 Мои: {show_cards(t['dealer'])}", parse_mode=": {show_cards(t['dealer'])}", parse_mode="HTML")
    while calc_score(t["dealer"]) <HTML")
    while calc_score(t["dealer"]) < BJ_DEALER_STOP:
        await asyncio.sleep(1 BJ_DEALER_STOP:
        await asyncio.sleep(1)
        c = t["deck"].pop()
)
        c = t["deck"].pop()
        t["dealer"].append(c)
        await bot        t["dealer"].append(c)
        await bot.send_message(cid, f"🎩 Берёт:.send_message(cid, f"🎩 Берёт: <b>{c[0]}{c[1]}</ <b>{c[0]}{c[1]}</b> → <b>{calc_score(t['dealer'])b> → <b>{calc_score(t['dealer'])}</b>", parse_mode="HTML")
    ds =}</b>", parse_mode="HTML")
    ds = calc_score(t["dealer"])
    res = []
 calc_score(t["dealer"])
    res = []
    for uid in t["order"]:
        p =    for uid in t["order"]:
        p = t["players"][uid]
        ps = calc_score t["players"][uid]
        ps = calc_score(p["cards"])
        bet = p["bet"](p["cards"])
        bet = p["bet"]
        if p["busted"]: res
        if p["busted"]: res.append(f"❌ {p['name']}: пере.append(f"❌ {p['name']}: перебор ({ps})")
        elif ds > 2бор ({ps})")
        elif ds > 21:
            await update_balance(cid, uid, bet1:
            await update_balance(cid, uid, bet*2)
            res.append(f"🎉*2)
            res.append(f"🎉 {p['name']}: Игорёчек перебрал {p['name']}: Игорёчек перебрал! +{bet}")
        elif ps > ds! +{bet}")
        elif ps > ds:
            await update_balance(cid, uid, bet:
            await update_balance(cid, uid, bet*2)
            res.append(f"🏆*2)
            res.append(f"🏆 {p['name']}: победа! +{bet {p['name']}: победа! +{bet}")
        elif ps == ds:
            await}")
        elif ps == ds:
            await update_balance(cid, uid, bet)
            res update_balance(cid, uid, bet)
            res.append(f"🤝 {p['name']}:.append(f"🤝 {p['name']}: ничья")
        else: res.append(f" ничья")
        else: res.append(f" {p['name']}: проигрыш")
    fn = "😱 Перебрал!" if ds {p['name']}: проигрыш")
    fn = "😱 Перебрал!" if ds > 21 else "🎉 Поздравля > 21 else "🎉 Поздравляем!" if any("победа" in r forем!" if any("победа" in r for r in res) else "🎩 Забирает r in res) else "🎩 Забирает ставки!" if any("проигрыш" in r for ставки!" if any("проигрыш" in r for r in res) else "🤝 Ничья r in res) else "🤝 Ничья!"
    await bot.send_message(cid, f"!"
    await bot.send_message(cid, f" <b>{fn}</b>\n\n <b>{fn}</b>\n\n Карты: {show_cards(t['dealer Карты: {show_cards(t['dealer'])} ({ds})\n\n📊 Результаты'])} ({ds})\n\n📊 Результаты:\n" + "\n".join(res), parse:\n" + "\n".join(res), parse_mode="HTML")
    del bj_tables[cid]_mode="HTML")
    del bj_tables[cid]
    await state.clear()

# ==================== АВ
    await state.clear()

# ==================== АВТО-РЕГИСТРАЦИЯ И ЗАПУСК =================ТО-РЕГИСТРАЦИЯ И ЗАПУСК ====================
@dp.message()
async def auto_register(m===
@dp.message()
async def auto_register(m: Message):
    if m.chat.type not in [': Message):
    if m.chat.type not in ['group', 'supergroup']: return
    await getgroup', 'supergroup']: return
    await get_user(m.chat.id, m.from_user.id)

@_user(m.chat.id, m.from_user.id)

@dp.message(F.new_chat_members)
async def on_userdp.message(F.new_chat_members)
async def on_user_join(m: Message):
    cid = m.chat.id_join(m: Message):
    cid = m.chat.id
    for user in m.new_chat_members:
       
    for user in m.new_chat_members:
        if user.is_bot:
            if user.id == int if user.is_bot:
            if user.id == int(API_TOKEN.split(':')[0]): await m.answer("(API_TOKEN.split(':')[0]): await m.answer(" Привет! Я экономический бот. / Привет! Я экономический бот. /start")
            continue
        await get_user(cid,start")
            continue
        await get_user(cid, user.id)
        await save_username(cid, user.id user.id)
        await save_username(cid, user.id, user.full_name)

async def main():
, user.full_name)

async def main():
    await init_db()
    logger.info("    await init_db()
    logger.info(" Бот запущен!")
    await start_web Бот запущен!")
    await start_web_server()
    asyncio.create_task(polling_health_check())_server()
    asyncio.create_task(polling_health_check())
    asyncio.create_task(auto_lottery_loop())
   
    asyncio.create_task(auto_lottery_loop())
    asyncio.create_task(loan_interest_loop())
    await dp asyncio.create_task(loan_interest_loop())
    await dp.start_polling(bot, timeout=30, drop_pending.start_polling(bot, timeout=30, drop_pending_updates=True, allowed_updates=["message", "callback_query",_updates=True, allowed_updates=["message", "callback_query", "my_chat_member"])

if __name__ == "my_chat_member"])

if __name__ == "__main__":
    asyncio.run(main())
``` "__main__":
    asyncio.run(main())
