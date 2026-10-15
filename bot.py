# ============================================================================
# 🤖 ЭКОНОМИЧЕСКИЙ БОТ ДЛЯ TELEGRAM ГРУПП - ПОЛНАЯ ВЕРСИЯ 6.0
# ============================================================================
# Автор: Создан для группы "Сарапулки"
# Версия: 6.0 Ultimate Edition
# Дата создания: 2026
# Описание: Полноценная экономическая система с изоляцией групп
# 
# Основные функции:
# - Работа и профессии с системой образования
# - Банковская система с процентами
# - Блэкджек с Игорёчком (2-5 игроков, кнопки)
# - Система кредитов с арестом имущества
# - Крафт предметов
# - Трейд между игроками
# - Авто-лотерея каждые 12 часов
# - Бизнесы и недвижимость
# - Автосалон
# - Инвентарь и предметы
# - Рейтинг богачей
# - Ежедневные бонусы
# - Ограбления
# - Игровые кости (50/50)
# ============================================================================


# ==================== ИМПОРТ БИБЛИОТЕК ====================
# Основные библиотеки для работы бота
import asyncio
import logging
import random
import time
import os

# Aiogram - фреймворк для Telegram ботов версии 3.x
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# База данных PostgreSQL
import asyncpg

# Веб-сервер для UptimeRobot и health checks
from aiohttp import web


# ==================== НАСТРОЙКИ БОТА ====================
# Токен бота берется из переменных окружения Render
# Получается от @BotFather при создании бота
API_TOKEN = os.environ.get("BOT_TOKEN", "")

# ID администраторов (через запятую)
# Используется для команды /give и других админских функций
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]

# URL базы данных PostgreSQL
# Формат: postgresql://user:password@host:port/database
DATABASE_URL = os.environ.get("DATABASE_URL", "")


# ==================== ИНИЦИАЛИЗАЦИЯ ЛОГГЕРА ====================
# Настройка логирования для отладки и мониторинга
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создание экземпляров бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
pool = None  # Пул соединений с базой данных


# ==================== СОСТОЯНИЯ FSM ====================
class BlackjackStates(StatesGroup):
    """
    Состояния для игры в Блэкджек
    
    Атрибуты:
        waiting - Ожидание игроков (60 секунд)
        betting - Фаза ставок
        playing - Активная игра
    """
    waiting = State()    # Ожидание игроков
    betting = State()    # Ставки
    playing = State()    # Игра


# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
# Активные столы Блэкджека (ключ: chat_id)
bj_tables = {}

# Активные сессии экзаменов (ключ: chat_id_user_id)
exam_sessions = {}


# ==================== РЕЦЕПТЫ КРАФТА ====================
# Система крафта позволяет создавать редкие предметы из обычных
CRAFT_RECIPES = {
    "diamond": {
        "name": "💎 Алмаз",
        "requires": {"📄 Бумага": 10},
        "rarity": "rare"
    },
    "scriptka": {
        "name": "🎸 Золотая Скрипка",
        "requires": {"💎 Алмаз": 5},
        "rarity": "legendary"
    }
}


# ==================== НАСТРОЙКИ ЛОТЕРЕИ ====================
LOTTERY_PRICE = 50              # Цена одного лотерейного билета
LOTTERY_INTERVAL = 12 * 3600    # Интервал розыгрыша (12 часов в секундах)


# ==================== НАСТРОЙКИ БАНКА ====================
BANK_INTEREST_RATE = 0.01  # Процентная ставка: 1% в сутки


# ==================== КУРСЫ ОБРАЗОВАНИЯ ====================
# Система образования позволяет получать профессии и повышать зарплату
COURSES = {
    "miner": {
        "name": "📘 Курс шахтёра",
        "price": 200,
        "required_for": "miner",
        "questions": [
            {"q": "Что нужно надевать в шахте?", "a": ["каска", "шлем", "защита"], "correct": 0},
            {"q": "Сколько тонн весит вагонетка?", "a": ["1", "5", "10"], "correct": 1},
            {"q": "Главный инструмент шахтёра?", "a": ["лопата", "отбойный молоток", "кирка"], "correct": 2}
        ]
    },
    "coder": {
        "name": " Курс программирования",
        "price": 1000,
        "required_for": "coder",
        "questions": [
            {"q": "Язык для веб-разработки?", "a": ["Python", "HTML", "C++"], "correct": 1},
            {"q": "Что такое баг?", "a": ["ошибка", "функция", "переменная"], "correct": 0},
            {"q": "Сколько бит в байте?", "a": ["4", "8", "16"], "correct": 1}
        ]
    },
    "trader": {
        "name": "📈 Курс трейдинга",
        "price": 3000,
        "required_for": "trader",
        "questions": [
            {"q": "Что такое бычий рынок?", "a": ["рост", "падение", "стабильность"], "correct": 0},
            {"q": "Диверсификация это?", "a": ["риск", "распределение", "прибыль"], "correct": 1},
            {"q": "Ликвидность актива?", "a": ["скорость продажи", "цена", "объём"], "correct": 0}
        ]
    },
    "mba": {
        "name": "🎓 MBA",
        "price": 10000,
        "required_for": None,
        "questions": [
            {"q": "ROI это?", "a": ["возврат инвестиций", "риск", "доход"], "correct": 0},
            {"q": "EBITDA показывает?", "a": ["прибыль", "убыток", "оборот"], "correct": 0},
            {"q": "Стратегия роста?", "a": ["сокращение", "инвестиции", "стагнация"], "correct": 1}
        ]
    }
}


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def pluralize(n, forms):
    """
    Функция склонения русских слов
    
    Args:
        n: Число для склонения
        forms: Список из 3 форм слова (1, 2-4, 5-20)
        
    Returns:
        Правильно склоненное слово
        
    Пример:
        pluralize(5, ['яблоко', 'яблока', 'яблок']) -> 'яблок'
        pluralize(21, ['сарапулка', 'сарапулки', 'сарапулок']) -> 'сарапулка'
    """
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
    """
    Форматирование суммы денег с правильным склонением
    
    Args:
        amount: Сумма в сарапулках
        
    Returns:
        Строка с отформатированной суммой
        
    Пример:
        fmt_money(5) -> '5 сарапулок'
        fmt_money(21) -> '21 сарапулка'
    """
    word = pluralize(amount, ['сарапулка', 'сарапулки', 'сарапулок'])
    return f"{amount} {word}"


# ==================== КОНФИГУРАЦИЯ РАБОТЫ ====================
# Профессии с базовой зарплатой и кулдауном
JOBS = {
    "novice": {
        "name": "👶 Новичок",
        "base_pay": 10,
        "cooldown": 3600  # 1 час
    },
    "miner": {
        "name": "⛏️ Шахтёр",
        "base_pay": 25,
        "cooldown": 3600  # 1 час
    },
    "coder": {
        "name": "💻 Программист",
        "base_pay": 50,
        "cooldown": 7200  # 2 часа
    },
    "trader": {
        "name": "📈 Трейдер",
        "base_pay": 80,
        "cooldown": 10800  # 3 часа
    }
}


# ==================== МАГАЗИН УЛУЧШЕНИЙ ====================
SHOP_ITEMS = {
    "course": {
        "name": " Курсы",
        "price": 500,
        "desc": "+1 уровень профессии",
        "type": "level_up"
    },
    "coffee": {
        "name": "☕ Кофе-машина",
        "price": 1000,
        "desc": "-10% время отдыха",
        "type": "cooldown_reduce"
    }
}


# ==================== РЫНОК (БИЗНЕСЫ И КЕЙСЫ) ====================
# 5 бизнесов с разной доходностью
MARKET = {
    "case_basic": {
        "name": "📦 Обычный кейс",
        "price": 200,
        "type": "case"
    },
    "biz_newspaper": {
        "name": " Газетный киоск",
        "price": 500,
        "type": "business",
        "income": 50  # Окупаемость: 10 дней
    },
    "biz_shawarma": {
        "name": "🌯 Ларёк с шаурмой",
        "price": 2000,
        "type": "business",
        "income": 150  # Окупаемость: 13 дней
    },
    "biz_coffee": {
        "name": "☕ Кофейня",
        "price": 5000,
        "type": "business",
        "income": 450  # Окупаемость: 11 дней
    },
    "biz_crypto": {
        "name": "💻 Крипто-ферма",
        "price": 15000,
        "type": "business",
        "income": 1200  # Окупаемость: 12.5 дней
    },
    "biz_hotel": {
        "name": "🏨 Отель",
        "price": 50000,
        "type": "business",
        "income": 4500  # Окупаемость: 11 дней
    }
}


# ==================== АВТОСАЛОН ====================
CARS = {
    "ok": {
        "name": "🚲 Ока",
        "price": 3000,
        "desc": "Едет и едет."
    },
    "priora": {
        "name": " Приора",
        "price": 10000,
        "desc": "Музыка громче двигателя."
    },
    "bmw": {
        "name": "🏎️ BMW X5",
        "price": 40000,
        "desc": "Для важных дел."
    },
    "gelik": {
        "name": "🚙 Гелик",
        "price": 80000,
        "desc": "Чёрный, тонированный."
    },
    "lambo": {
        "name": "🏎️ Lamborghini",
        "price": 200000,
        "desc": "Король дороги."
    }
}


# ============================================================================
# БАЗА ДАННЫХ
# ============================================================================

async def init_db():
    """
    Инициализация базы данных PostgreSQL
    
    Создает все необходимые таблицы если их нет.
    Используется пул соединений для оптимизации производительности.
    """
    global pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=30,
        max_inactive_connection_lifetime=300
    )
    
    async with pool.acquire() as conn:
        # Таблица пользователей (баланс)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id BIGINT,
                user_id BIGINT,
                balance INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Таблица профилей (профессия, уровень, кулдаун)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                chat_id BIGINT,
                user_id BIGINT,
                job_key TEXT DEFAULT 'novice',
                level INTEGER DEFAULT 1,
                last_work_time REAL DEFAULT 0,
                has_coffee BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Таблица инвентаря (предметы)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT,
                user_id BIGINT,
                item_name TEXT,
                item_type TEXT,
                rarity TEXT DEFAULT 'common'
            )
        """)
        
        # Таблица бизнесов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT,
                user_id BIGINT,
                business_name TEXT,
                income INTEGER,
                last_collect_time REAL DEFAULT 0
            )
        """)
        
        # Таблица гаража (машины)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS garage (
                chat_id BIGINT,
                user_id BIGINT,
                car_key TEXT,
                car_name TEXT,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Таблица ежедневных бонусов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_bonus (
                chat_id BIGINT,
                user_id BIGINT,
                last_claim REAL DEFAULT 0,
                streak INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Таблица ограблений (кулдаун)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS robbery (
                chat_id BIGINT,
                user_id BIGINT,
                last_robbery REAL DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Таблица лотерейных билетов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS lottery_tickets (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT,
                user_id BIGINT,
                buy_time REAL
            )
        """)
        
        # Таблица имен пользователей
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS usernames (
                chat_id BIGINT,
                user_id BIGINT,
                username TEXT,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Таблица банка (депозиты)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bank (
                chat_id BIGINT,
                user_id BIGINT,
                deposit INTEGER DEFAULT 0,
                last_interest_time REAL DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Таблица образования (пройденные курсы)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS education (
                chat_id BIGINT,
                user_id BIGINT,
                completed_courses TEXT[] DEFAULT '{}',
                has_mba BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Таблица кредитов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                chat_id BIGINT,
                user_id BIGINT,
                amount INTEGER DEFAULT 0,
                interest INTEGER DEFAULT 0,
                taken_at REAL DEFAULT 0,
                due_date REAL DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
    print("✅ База данных готова")


async def save_username(chat_id, user_id, username):
    """
    Сохранение имени пользователя в базу данных
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        username: Имя пользователя
    """
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO usernames (chat_id, user_id, username) VALUES ($1, $2, $3) ON CONFLICT (chat_id, user_id) DO UPDATE SET username = $3",
            chat_id, user_id, username
        )


async def get_user(chat_id, user_id):
    """
    Получение данных пользователя
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        
    Returns:
        Словарь с балансом пользователя
    """
    async with pool.acquire() as conn:
        balance = await conn.fetchval(
            "SELECT balance FROM users WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )
        if balance is not None:
            return {"balance": balance}
        await conn.execute(
            "INSERT INTO users (chat_id, user_id, balance) VALUES ($1, $2, 0)",
            chat_id, user_id
        )
        return {"balance": 0}


async def update_balance(chat_id, user_id, amount):
    """
    Обновление баланса пользователя
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        amount: Сумма для добавления (может быть отрицательной)
    """
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET balance = balance + $1 WHERE chat_id = $2 AND user_id = $3",
            amount, chat_id, user_id
        )


async def get_profile(chat_id, user_id):
    """
    Получение профиля пользователя
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        
    Returns:
        Словарь с данными профиля
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT job_key, level, last_work_time, has_coffee FROM profiles WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )
        if not row:
            await conn.execute(
                "INSERT INTO profiles (chat_id, user_id, job_key, level, last_work_time, has_coffee) VALUES ($1, $2, 'novice', 1, 0, FALSE)",
                chat_id, user_id
            )
            return {"job_key": "novice", "level": 1, "last_work_time": 0, "has_coffee": False}
        return dict(row)


async def set_car(chat_id, user_id, car_key, car_name):
    """
    Установка машины пользователю
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        car_key: Ключ машины
        car_name: Название машины
    """
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO garage (chat_id, user_id, car_key, car_name) VALUES ($1, $2, $3, $4) ON CONFLICT (chat_id, user_id) DO UPDATE SET car_key = $3, car_name = $4",
            chat_id, user_id, car_key, car_name
        )


async def get_car(chat_id, user_id):
    """
    Получение машины пользователя
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        
    Returns:
        Название машины или None
    """
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT car_name FROM garage WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )


async def get_bank(chat_id, user_id):
    """
    Получение данных банка пользователя
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        
    Returns:
        Словарь с данными банка
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT deposit, last_interest_time FROM bank WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )
        if not row:
            await conn.execute(
                "INSERT INTO bank (chat_id, user_id, deposit, last_interest_time) VALUES ($1, $2, 0, $3)",
                chat_id, user_id, time.time()
            )
            return {"deposit": 0, "last_interest_time": time.time()}
        return dict(row)


async def update_bank(chat_id, user_id, amount):
    """
    Обновление депозита в банке
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        amount: Сумма для добавления
    """
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE bank SET deposit = deposit + $1 WHERE chat_id = $2 AND user_id = $3",
            amount, chat_id, user_id
        )


async def calc_interest(deposit, last_time):
    """
    Расчет накопленных процентов
    
    Args:
        deposit: Сумма депозита
        last_time: Время последнего начисления
        
    Returns:
        Кортеж (проценты, текущее время)
    """
    now = time.time()
    days_passed = (now - last_time) / 86400
    interest = int(deposit * BANK_INTEREST_RATE * days_passed)
    return interest, now


async def get_education(chat_id, user_id):
    """
    Получение данных об образовании пользователя
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        
    Returns:
        Словарь с данными об образовании
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT completed_courses, has_mba FROM education WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )
        if not row:
            await conn.execute(
                "INSERT INTO education (chat_id, user_id, completed_courses, has_mba) VALUES ($1, $2, '{}', FALSE)",
                chat_id, user_id
            )
            return {"completed_courses": [], "has_mba": False}
        return {"completed_courses": row['completed_courses'] or [], "has_mba": row['has_mba']}


async def complete_course(chat_id, user_id, course_key):
    """
    Завершение курса образования
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        course_key: Ключ курса
    """
    async with pool.acquire() as conn:
        if course_key == "mba":
            await conn.execute(
                "UPDATE education SET has_mba = TRUE WHERE chat_id = $1 AND user_id = $2",
                chat_id, user_id
            )
        else:
            await conn.execute(
                "UPDATE education SET completed_courses = array_append(completed_courses, $1) WHERE chat_id = $2 AND user_id = $3",
                course_key, chat_id, user_id
            )


async def get_loan(cid, uid):
    """
    Получить данные о кредите
    
    Args:
        cid: ID чата
        uid: ID пользователя
        
    Returns:
        Словарь с данными кредита
    """
    async with pool.acquire() as conn:
        r = await conn.fetchrow(
            "SELECT amount, interest, taken_at, due_date FROM loans WHERE chat_id=$1 AND user_id=$2",
            cid, uid
        )
        if not r:
            return {"amount": 0, "interest": 0, "taken_at": 0, "due_date": 0}
        return dict(r)


async def update_loan(cid, uid, amount, interest, taken_at, due_date):
    """
    Обновить кредит
    
    Args:
        cid: ID чата
        uid: ID пользователя
        amount: Сумма кредита
        interest: Накопленные проценты
        taken_at: Время взятия кредита
        due_date: Срок возврата
    """
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO loans (chat_id, user_id, amount, interest, taken_at, due_date) 
               VALUES ($1,$2,$3,$4,$5,$6)
               ON CONFLICT (chat_id, user_id) 
               DO UPDATE SET amount=$3, interest=$4, taken_at=$5, due_date=$6""",
            cid, uid, amount, interest, taken_at, due_date
        )


async def clear_loan(cid, uid):
    """
    Удалить кредит (полное погашение)
    
    Args:
        cid: ID чата
        uid: ID пользователя
    """
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM loans WHERE chat_id=$1 AND user_id=$2", cid, uid)


async def arrest_player(cid, uid):
    """
    Арест имущества и счетов игрока при просрочке кредита
    
    Конфискует:
    - Деньги в банке
    - Машину
    - Бизнесы
    - Предметы инвентаря
    - Сбрасывает профессию до новичка
    
    Args:
        cid: ID чата
        uid: ID пользователя
        
    Returns:
        Список конфискованного имущества
    """
    arrested = []
    
    # Арест банковского счёта
    bank_data = await get_bank(cid, uid)
    if bank_data['deposit'] > 0:
        arrested.append(f"💰 Банк: {fmt_money(bank_data['deposit'])}")
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE bank SET deposit=0, last_interest_time=$1 WHERE chat_id=$2 AND user_id=$3",
                time.time(), cid, uid
            )
    
    # Арест машины
    car = await get_car(cid, uid)
    if car:
        arrested.append(f"🚗 Машина: {car}")
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM garage WHERE chat_id=$1 AND user_id=$2", cid, uid)
    
    # Арест бизнесов
    async with pool.acquire() as conn:
        businesses = await conn.fetch(
            "SELECT business_name FROM businesses WHERE chat_id=$1 AND user_id=$2",
            cid, uid
        )
        if businesses:
            biz_names = ", ".join([b['business_name'] for b in businesses])
            arrested.append(f"🏢 Бизнесы: {biz_names}")
            await conn.execute("DELETE FROM businesses WHERE chat_id=$1 AND user_id=$2", cid, uid)
    
    # Арест инвентаря
    async with pool.acquire() as conn:
        items = await conn.fetch(
            "SELECT item_name FROM inventory WHERE chat_id=$1 AND user_id=$2",
            cid, uid
        )
        if items:
            item_names = ", ".join([i['item_name'] for i in items])
            arrested.append(f"🎒 Предметы: {item_names}")
            await conn.execute("DELETE FROM inventory WHERE chat_id=$1 AND user_id=$2", cid, uid)
    
    # Сброс профессии
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE profiles SET job_key='novice', level=1 WHERE chat_id=$1 AND user_id=$2",
            cid, uid
        )
    arrested.append("💼 Профессия сброшена до Новичка")
    
    return arrested


# ============================================================================
# ВЕБ-СЕРВЕР И ЗДОРОВЬЕ БОТА
# ============================================================================

async def handle_ping(request):
    """
    Обработчик ping-запросов от UptimeRobot
    
    Returns:
        Web response с текстом "Bot is alive!"
    """
    return web.Response(text="🤖 Bot is alive!")


async def start_web_server():
    """
    Запуск веб-сервера для UptimeRobot
    
    Сервер слушает на порту из переменной окружения PORT (по умолчанию 8080)
    """
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    print("🌐 Web server started")


async def polling_health_check():
    """
    Проверка здоровья бота каждые 5 минут
    
    Отправляет запрос getMe к Telegram API для проверки связи
    """
    while True:
        try:
            await asyncio.sleep(300)
            await bot.get_me()
            print("✅ Health check OK")
        except Exception as e:
            print(f"❌ Health check failed: {e}")


async def auto_lottery_loop():
    """
    Автоматический розыгрыш лотереи каждые 12 часов
    
    Проверяет все чаты с лотерейными билетами и проводит розыгрыш
    """
    print(" Авто-лотерея запущена")
    while True:
        await asyncio.sleep(3600)
        now = time.time()
        async with pool.acquire() as conn:
            chats = await conn.fetch("SELECT DISTINCT chat_id FROM lottery_tickets")
            for row in chats:
                cid = row['chat_id']
                tickets = await conn.fetch(
                    "SELECT id, user_id FROM lottery_tickets WHERE chat_id=$1 AND buy_time<=$2",
                    cid, now - LOTTERY_INTERVAL
                )
                if len(tickets) >= 2:
                    winner = random.choice(tickets)
                    bank = len(tickets) * LOTTERY_PRICE
                    await update_balance(cid, winner['user_id'], bank)
                    wname = await conn.fetchval(
                        "SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2",
                        cid, winner['user_id']
                    ) or f"User{winner['user_id']}"
                    await conn.execute("DELETE FROM lottery_tickets WHERE chat_id=$1", cid)
                    try:
                        await bot.send_message(
                            cid,
                            f"🎊 <b>АВТО-РОЗЫГРЫШ!</b>\n\n🏆 {wname}\n💰 {fmt_money(bank)}",
                            parse_mode="HTML"
                        )
                    except:
                        pass


async def loan_interest_loop():
    """
    Ежедневное начисление процентов по кредитам и арест при просрочке
    
    Каждый день:
    - Начисляет 2% процентов на сумму долга
    - При просрочке (>7 дней) арестует имущество игрока
    """
    print("💳 Цикл кредитов запущен")
    while True:
        await asyncio.sleep(86400)  # раз в 24 часа
        async with pool.acquire() as conn:
            loans = await conn.fetch(
                "SELECT chat_id, user_id, amount, interest, due_date FROM loans WHERE amount>0"
            )
            for loan in loans:
                cid, uid = loan['chat_id'], loan['user_id']
                
                # Проверяем срок
                if time.time() > loan['due_date']:
                    # ПРОСРОЧКА — АРЕСТ ИМУЩЕСТВА
                    total_debt = loan['amount'] + loan['interest']
                    arrested = await arrest_player(cid, uid)
                    await clear_loan(cid, uid)
                    
                    arrested_text = "\n".join([f"• {item}" for item in arrested]) if arrested else "Нечего арестовать"
                    
                    try:
                        await bot.send_message(
                            cid,
                            f" <b>АРЕСТ ИМУЩЕСТВА!</b>\n\n"
                            f"Долг был: <b>{fmt_money(total_debt)}</b>\n\n"
                            f"<b>Конфисковано:</b>\n{arrested_text}\n\n"
                            f"️ Погашайте кредиты вовремя через /repay!",
                            parse_mode="HTML"
                        )
                    except:
                        pass
                else:
                    # Начисляем проценты (2% в день)
                    daily_interest = int(loan['amount'] * 0.02)
                    new_interest = loan['interest'] + daily_interest
                    await update_loan(
                        cid, uid,
                        loan['amount'], new_interest,
                        loan['taken_at'], loan['due_date']
                    )


# ============================================================================
# ОСНОВНЫЕ КОМАНДЫ
# ============================================================================

@dp.message(Command("start"))
async def cmd_start(m: Message):
    """
    Команда /start - главное меню бота
    
    Показывает список всех доступных команд
    """
    await save_username(m.chat.id, m.from_user.id, m.from_user.full_name)
    await m.answer(
        " <b>Экономика группы!</b>\n\n"
        "💰 /balance — мой баланс\n"
        "💼 /work — работать\n"
        "💸 /pay сумма (ответ) — перевести\n"
        "🔫 /rob (ответ) — ограбить\n"
        "🎁 /daily — ежедневный бонус\n"
        "🎲 /dice сумма — кости 50/50\n"
        "🎟️ /buy_ticket — лотерейный билет\n"
        "🛒 /shop — улучшения\n"
        "🏪 /market — бизнесы и кейсы\n"
        "🚗 /cars — автосалон\n"
        "🅿️ /mycar — моя тачка\n"
        "💼 /collect — прибыль с бизнеса\n"
        " /inv — инвентарь\n"
        "📊 /info — моя карточка\n"
        "🏆 /rating — рейтинг богачей\n"
        "🃏 /blackjack — Блэкджек с Игорёчком\n"
        "🔨 /craft — крафт предметов\n"
        "🔄 /trade — обмен с игроком\n"
        " /bank — банковский счёт\n"
        "📥 /deposit — положить в банк\n"
        "📤 /withdraw — снять из банка\n"
        "🎓 /education — образование\n"
        "📘 /buy_course — купить курс\n"
        "💳 /credit сумма — взять кредит\n"
        "📊 /debt — посмотреть долг\n"
        "💸 /repay сумма — погасить часть долга\n"
        "✅ /repay_all — погасить весь долг\n"
        "🚔 /bailout — информация о выкупе",
        parse_mode="HTML"
    )


@dp.message(Command("balance"))
async def cmd_balance(m: Message):
    """
    Команда /balance - проверка баланса
    
    Показывает текущий баланс и машину игрока
    """
    await save_username(m.chat.id, m.from_user.id, m.from_user.full_name)
    u = await get_user(m.chat.id, m.from_user.id)
    c = await get_car(m.chat.id, m.from_user.id)
    await m.answer(
        f"💰 <b>{fmt_money(u['balance'])}</b>\n {c or 'нет'}",
        parse_mode="HTML"
    )


@dp.message(Command("work"))
async def cmd_work(m: Message):
    """
    Команда /work - работа
    
    Начисляет зарплату в зависимости от профессии и уровня.
    Проверяет кулдаун и наличие курса для профессии.
    """
    cid, uid = m.chat.id, m.from_user.id
    await save_username(cid, uid, m.from_user.full_name)
    
    p = await get_profile(cid, uid)
    jk = p['job_key']
    
    # Проверяем наличие курса для профессии
    if jk != 'novice':
        edu = await get_education(cid, uid)
        if jk not in edu['completed_courses']:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE profiles SET job_key='novice' WHERE chat_id=$1 AND user_id=$2",
                    cid, uid
                )
            jk = 'novice'
            p['job_key'] = 'novice'
    
    j = JOBS[jk]
    ct = time.time()
    cd = j['cooldown'] * (0.9 if p['has_coffee'] else 1.0)
    
    if ct - p['last_work_time'] < cd:
        remaining = int((cd - (ct - p['last_work_time'])) // 60)
        return await m.answer(f"⏳ Отдых {remaining} мин.")
    
    sal = j['base_pay'] * p['level'] + random.randint(0, 5)
    edu = await get_education(cid, uid)
    if edu['has_mba']:
        sal = int(sal * 1.5)
    
    await update_balance(cid, uid, sal)
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE profiles SET last_work_time=$1 WHERE chat_id=$2 AND user_id=$3",
            ct, cid, uid
        )
    
    await m.answer(
        f"💼 <b>{j['name']}</b> (Ур.{p['level']}): +<b>{fmt_money(sal)}</b>",
        parse_mode="HTML"
    )


@dp.message(Command("jobs"))
async def cmd_jobs(m: Message):
    """
    Команда /jobs - список вакансий
    
    Показывает все доступные профессии с зарплатой и кулдауном
    """
    t = "📋 <b>Вакансии:</b>\n"
    for k, v in JOBS.items():
        t += f" {v['name']} ({v['base_pay']}/ч) → /job {k}\n"
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("job"))
async def cmd_change_job(m: Message):
    """
    Команда /job - смена работы
    
    Args:
        Аргумент: ключ профессии (novice, miner, coder, trader)
    """
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    
    if len(args) < 2 or args[1] not in JOBS:
        return await m.answer("/jobs")
    
    if args[1] != 'novice':
        edu = await get_education(cid, uid)
        if args[1] not in edu['completed_courses']:
            return await m.answer(f"❌ Нужен курс: /buy_course {args[1]}")
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE profiles SET job_key=$1 WHERE chat_id=$2 AND user_id=$3",
            args[1], cid, uid
        )
    await m.answer(f"✅ Теперь: <b>{JOBS[args[1]]['name']}</b>", parse_mode="HTML")


@dp.message(Command("pay"))
async def cmd_pay(m: Message):
    """
    Команда /pay - перевод денег
    
    Args:
        Аргумент: сумма перевода
        Ответ на сообщение: получатель
    """
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    
    if len(args) < 2 or not m.reply_to_message:
        return await m.answer("/pay сумма (ответ)")
    
    try:
        amt = int(args[1])
    except:
        return await m.answer("Число!")
    
    if amt <= 0:
        return await m.answer(">0!")
    
    s, r = uid, m.reply_to_message.from_user.id
    if s == r:
        return await m.answer("Себе нельзя!")
    
    sb = await get_user(cid, s)
    if sb['balance'] < amt:
        return await m.answer(f"❌ Мало ({fmt_money(sb['balance'])})")
    
    await update_balance(cid, s, -amt)
    await update_balance(cid, r, amt)
    await save_username(cid, r, m.reply_to_message.from_user.full_name)
    await m.answer(f"✅ Перевод <b>{fmt_money(amt)}</b>", parse_mode="HTML")


@dp.message(Command("rob"))
async def cmd_rob(m: Message):
    """
    Команда /rob - ограбление
    
    Шанс успеха: 40%
    При успехе: крадет 10-50% баланса жертвы
    При провале: штраф 20% баланса грабителя
    Кулдаун: 3 часа
    """
    cid, uid = m.chat.id, m.from_user.id
    
    if not m.reply_to_message:
        return await m.answer("Ответьте на жертву!")
    
    rid, vid = uid, m.reply_to_message.from_user.id
    if rid == vid:
        return await m.answer("Себя нельзя!")
    
    async with pool.acquire() as conn:
        lr = await conn.fetchval(
            "SELECT last_robbery FROM robbery WHERE chat_id=$1 AND user_id=$2",
            cid, rid
        ) or 0
        ct = time.time()
        
        if ct - lr < 10800:
            return await m.answer(f"⏳ Кулдаун {int((10800-(ct-lr))//3600)} ч.")
        
        await conn.execute(
            "INSERT INTO robbery VALUES ($1,$2,$3) ON CONFLICT DO UPDATE SET last_robbery=$3",
            cid, rid, ct
        )
    
    vb = await get_user(cid, vid)
    if vb['balance'] < 50:
        return await m.answer("У жертвы мало денег!")
    
    if random.random() < 0.4:
        st = int(vb['balance'] * random.uniform(0.1, 0.5))
        await update_balance(cid, vid, -st)
        await update_balance(cid, rid, st)
        await m.answer(f" Украл <b>{fmt_money(st)}</b>!", parse_mode="HTML")
    else:
        rb = await get_user(cid, rid)
        pn = int(rb['balance'] * 0.2)
        await update_balance(cid, rid, -pn)
        await update_balance(cid, vid, pn)
        await m.answer(f"🚔 Штраф <b>{fmt_money(pn)}</b>!", parse_mode="HTML")


@dp.message(Command("daily"))
async def cmd_daily(m: Message):
    """
    Команда /daily - ежедневный бонус
    
    Базовый бонус: 100-300 сарапулок
    Множитель за серию: до 7x
    Кулдаун: 24 часа
    """
    cid, uid = m.chat.id, m.from_user.id
    await save_username(cid, uid, m.from_user.full_name)
    
    ct = time.time()
    async with pool.acquire() as conn:
        r = await conn.fetchrow(
            "SELECT last_claim, streak FROM daily_bonus WHERE chat_id=$1 AND user_id=$2",
            cid, uid
        )
        lc, sk = (r['last_claim'], r['streak']) if r else (0, 0)
        
        if ct - lc < 86400:
            return await m.answer(f" Через {int((86400-(ct-lc))//3600)} ч.")
        
        if ct - lc < 172800:
            sk += 1
        else:
            sk = 1
        
        bn = random.randint(100, 300) * min(sk, 7)
        await update_balance(cid, uid, bn)
        await conn.execute(
            "INSERT INTO daily_bonus VALUES ($1,$2,$3,$4) ON CONFLICT DO UPDATE SET last_claim=$3, streak=$4",
            cid, uid, ct, sk
        )
    
    await m.answer(f"🎁 Бонус за {sk} дн.: <b>{fmt_money(bn)}</b>", parse_mode="HTML")


@dp.message(Command("dice"))
async def cmd_dice(m: Message):
    """
    Команда /dice - игра в кости 50/50
    
    Механика:
    - Бросается кубик (1-6)
    - 4, 5, 6 — выигрыш x2
    - 1, 2, 3 — проигрыш
    - Минимальная ставка: 10 сарапулок
    """
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    
    if len(args) < 2:
        return await m.answer(
            "🎲 Использование: <b>/dice сумма</b>\n\n"
            "Шанс 50/50. Выпадает 1-6.\n"
            "4, 5, 6 — выигрыш x2\n"
            "1, 2, 3 — проигрыш",
            parse_mode="HTML"
        )
    
    try:
        bet = int(args[1])
    except:
        return await m.answer("❌ Ставка должна быть числом!")
    
    if bet < 10:
        return await m.answer("❌ Минимальная ставка: 10 сарапулок")
    
    ub = await get_user(cid, uid)
    if ub['balance'] < bet:
        return await m.answer(f"❌ Недостаточно ({fmt_money(ub['balance'])})")
    
    await update_balance(cid, uid, -bet)
    dice = random.randint(1, 6)
    
    await m.answer(f"🎲 <b>Бросаем кубик...</b>\n\nСтавка: {fmt_money(bet)}", parse_mode="HTML")
    await asyncio.sleep(1)
    
    if dice >= 4:
        win = bet * 2
        await update_balance(cid, uid, win)
        await m.answer(
            f"🎲 <b>Выпало: {dice}</b>\n\n"
            f"🎉 <b>ПОБЕДА!</b>\n"
            f"Выигрыш: <b>{fmt_money(win)}</b> (x2)",
            parse_mode="HTML"
        )
    else:
        await m.answer(
            f"🎲 <b>Выпало: {dice}</b>\n\n"
            f"💀 <b>Проигрыш</b>\n"
            f"Попробуй ещё раз!",
            parse_mode="HTML"
        )


@dp.message(Command("buy_ticket"))
async def cmd_buy_ticket(m: Message):
    """
    Команда /buy_ticket - покупка лотерейного билета
    
    Цена: 50 сарапулок
    Розыгрыш: каждые 12 часов автоматически
    """
    cid, uid = m.chat.id, m.from_user.id
    await save_username(cid, uid, m.from_user.full_name)
    
    ub = await get_user(cid, uid)
    if ub['balance'] < LOTTERY_PRICE:
        return await m.answer(f"❌ Нужно {fmt_money(LOTTERY_PRICE)}")
    
    await update_balance(cid, uid, -LOTTERY_PRICE)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO lottery_tickets (chat_id, user_id, buy_time) VALUES ($1,$2,$3)",
            cid, uid, time.time()
        )
    
    await m.answer(f"🎟️ Билет куплен! Розыгрыш через 12ч.", parse_mode="HTML")


@dp.message(Command("info"))
async def cmd_info(m: Message):
    """
    Команда /info - карточка игрока
    
    Показывает всю статистику игрока:
    - Баланс и банк
    - Профессия и уровень
    - Машина
    - Бизнесы и инвентарь
    - Курсы и MBA
    - Долг по кредиту
    """
    cid, uid = m.chat.id, m.from_user.id
    await save_username(cid, uid, m.from_user.full_name)
    
    u = await get_user(cid, uid)
    p = await get_profile(cid, uid)
    c = await get_car(cid, uid)
    bd = await get_bank(cid, uid)
    edu = await get_education(cid, uid)
    loan = await get_loan(cid, uid)
    
    async with pool.acquire() as conn:
        bc = await conn.fetchval(
            "SELECT COUNT(*) FROM businesses WHERE chat_id=$1 AND user_id=$2",
            cid, uid
        )
        ic = await conn.fetchval(
            "SELECT COUNT(*) FROM inventory WHERE chat_id=$1 AND user_id=$2",
            cid, uid
        )
    
    j = JOBS[p['job_key']]
    cc = len(edu['completed_courses']) + (1 if edu['has_mba'] else 0)
    
    t = f" <b>{m.from_user.full_name}</b>\n"
    t += f" {fmt_money(u['balance'])}\n"
    t += f"🏦 Банк: {fmt_money(bd['deposit'])}\n"
    t += f"💼 {j['name']} (Ур.{p['level']})\n"
    t += f"🚗 {c or 'нет'}\n"
    t += f"🏢 {bc} биз.\n"
    t += f"🎒 {ic} предм.\n"
    t += f"🎓 {cc} курсов"
    
    if edu['has_mba']:
        t += "\n🎯 MBA (+50%)"
    if p['has_coffee']:
        t += "\n☕ Кофе"
    if loan['amount'] > 0:
        total_debt = loan['amount'] + loan['interest']
        t += f"\n💳 Долг: <b>{fmt_money(total_debt)}</b>"
    
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("shop"))
async def cmd_shop(m: Message):
    """
    Команда /shop - магазин улучшений
    
    Доступные улучшения:
    - Курсы (+1 уровень профессии)
    - Кофе-машина (-10% кулдаун работы)
    """
    t = " <b>Улучшения:</b>\n"
    for k, v in SHOP_ITEMS.items():
        t += f"🔹 {v['name']} ({fmt_money(v['price'])}) → /buy {k}\n"
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("buy"))
async def cmd_buy(m: Message):
    """
    Команда /buy - покупка улучшений
    
    Args:
        Аргумент: ключ улучшения (course, coffee)
    """
    cid, uid = m.chat.id, m.from_user.id
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
            await conn.execute(
                "UPDATE profiles SET level=$1 WHERE chat_id=$2 AND user_id=$3",
                p['level']+1, cid, uid
            )
        await m.answer(f"✅ Уровень {p['level']+1}!")
    elif it['type'] == 'cooldown_reduce':
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE profiles SET has_coffee=TRUE WHERE chat_id=$1 AND user_id=$2",
                cid, uid
            )
        await m.answer("✅ Кофе куплен!")


@dp.message(Command("market"))
async def cmd_market(m: Message):
    """
    Команда /market - рынок
    
    Показывает кейсы и бизнесы с ценами и доходом
    """
    t = "🏪 <b>Рынок:</b>\n\n📦 <b>Кейсы:</b>\n"
    for k, v in MARKET.items():
        if v["type"] == "case":
            t += f"🔹 {v['name']} ({fmt_money(v['price'])}) → /buy_market {k}\n"
    
    t += "\n🏢 <b>Бизнесы:</b>\n"
    for k, v in MARKET.items():
        if v["type"] == "business":
            t += f"🔹 {v['name']} ({fmt_money(v['price'])}) → /buy_market {k}\n"
            t += f"   💰 Доход: {fmt_money(v['income'])}/сутки\n"
    
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("buy_market"))
async def cmd_buy_market(m: Message):
    """
    Команда /buy_market - покупка на рынке
    
    Args:
        Аргумент: ключ товара (case_basic, biz_newspaper, и т.д.)
    """
    cid, uid = m.chat.id, m.from_user.id
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
            await conn.execute(
                "INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,'card',$4)",
                cid, uid, pr, rar
            )
        await m.answer(f"📦 Выпало: <b>{pr}</b> ({rar})", parse_mode="HTML")
    
    elif it['type'] == 'business':
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO businesses (chat_id, user_id, business_name, income) VALUES ($1,$2,$3,$4)",
                cid, uid, it['name'], it['income']
            )
        await m.answer(f"✅ Куплен <b>{it['name']}</b>!", parse_mode="HTML")


@dp.message(Command("collect"))
async def cmd_collect(m: Message):
    """
    Команда /collect - сбор прибыли с бизнеса
    
    Прибыль начисляется раз в 24 часа
    """
    cid, uid = m.chat.id, m.from_user.id
    now = time.time()
    tot = 0
    collected = []
    
    async with pool.acquire() as conn:
        bz = await conn.fetch(
            "SELECT * FROM businesses WHERE chat_id=$1 AND user_id=$2",
            cid, uid
        )
        if not bz:
            return await m.answer("❌ Нет бизнеса.")
        
        for b in bz:
            if now - b['last_collect_time'] > 86400:
                tot += b['income']
                collected.append(f"• {b['business_name']}: +{fmt_money(b['income'])}")
                await conn.execute(
                    "UPDATE businesses SET last_collect_time=$1 WHERE id=$2",
                    now, b['id']
                )
    
    if tot > 0:
        await update_balance(cid, uid, tot)
        items = "\n".join(collected)
        await m.answer(
            f"💼 <b>Прибыль собрана!</b>\n\n{items}\n\n💰 Итого: <b>+{fmt_money(tot)}</b>",
            parse_mode="HTML"
        )
    else:
        await m.answer("⏳ Рано.")


@dp.message(Command("cars"))
async def cmd_cars(m: Message):
    """
    Команда /cars - автосалон
    
    Показывает все доступные машины с ценами
    """
    t = "🚗 <b>Автосалон:</b>\n"
    for k, v in CARS.items():
        t += f"🔸 {v['name']} ({fmt_money(v['price'])}) → /buycar {k}\n"
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("buycar"))
async def cmd_buycar(m: Message):
    """
    Команда /buycar - покупка машины
    
    Args:
        Аргумент: ключ машины (ok, priora, bmw, gelik, lambo)
    """
    cid, uid = m.chat.id, m.from_user.id
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


@dp.message(Command("mycar"))
async def cmd_mycar(m: Message):
    """
    Команда /mycar - моя машина
    
    Показывает текущую машину игрока
    """
    c = await get_car(m.chat.id, m.from_user.id)
    await m.answer(f"🅿️ {c}" if c else "️ Пусто. /cars")


@dp.message(Command("inv"))
async def cmd_inv(m: Message):
    """
    Команда /inv - инвентарь
    
    Показывает все предметы игрока с редкостью
    """
    cid, uid = m.chat.id, m.from_user.id
    
    async with pool.acquire() as conn:
        its = await conn.fetch(
            "SELECT item_name, rarity FROM inventory WHERE chat_id=$1 AND user_id=$2",
            cid, uid
        )
    
    if not its:
        return await m.answer("🎒 Пусто.")
    
    t = "🎒 <b>Инвентарь:</b>\n"
    for i in its:
        em = "" if i['rarity']=="legendary" else "🔵" if i['rarity']=="rare" else "🟢"
        t += f"{em} {i['item_name']}\n"
    
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("rating"))
async def cmd_rating(m: Message):
    """
    Команда /rating - рейтинг богачей
    
    Показывает топ-10 игроков по балансу в чате
    """
    cid = m.chat.id
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT u.user_id, u.balance, us.username FROM users u LEFT JOIN usernames us ON u.chat_id=us.chat_id AND u.user_id=us.user_id WHERE u.chat_id=$1 ORDER BY u.balance DESC LIMIT 10",
            cid
        )
    
    t = " <b>Рейтинг:</b>\n"
    for i, r in enumerate(rows, 1):
        t += f"{i}. <b>{r['username'] or f'User{r[\"user_id\"]}'}</b> — {fmt_money(r['balance'])}\n"
    
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("give"))
async def cmd_give(m: Message):
    """
    Команда /give - выдача денег (только для админов)
    
    Args:
        Аргумент: сумма
        Ответ на сообщение: получатель
    """
    cid = m.chat.id
    
    if m.from_user.id not in ADMIN_IDS:
        return
    
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message:
        return await m.answer("/give сумма (ответ)")
    
    try:
        amt = int(args[1])
    except:
        return await m.answer("Число!")
    
    await update_balance(cid, m.reply_to_message.from_user.id, amt)
    await m.answer(f"✅ Выдано {fmt_money(amt)}.")


@dp.message(Command("bank"))
async def cmd_bank(m: Message):
    """
    Команда /bank - информация о банковском счёте
    
    Показывает баланс, накопленные проценты и ставки
    """
    cid, uid = m.chat.id, m.from_user.id
    bd = await get_bank(cid, uid)
    interest, _ = await calc_interest(bd['deposit'], bd['last_interest_time'])
    
    t = f"🏦 <b>Банк</b>\n"
    t += f" На счету: <b>{fmt_money(bd['deposit'])}</b>\n"
    t += f"📈 Проценты: <b>+{fmt_money(interest)}</b>\n"
    t += f"💹 1% в сутки\n\n"
    t += f"📥 /deposit сумма\n"
    t += f"📤 /withdraw сумма\n"
    t += f"⚠️ Деньги в банке нельзя украсть!"
    
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("deposit"))
async def cmd_deposit(m: Message):
    """
    Команда /deposit - положить деньги в банк
    
    Args:
        Аргумент: сумма (минимум 100)
    """
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    
    if len(args) < 2:
        return await m.answer("/deposit сумма")
    
    try:
        amt = int(args[1])
    except:
        return await m.answer("Число!")
    
    if amt < 100:
        return await m.answer("Мин. 100")
    
    u = await get_user(cid, uid)
    if u['balance'] < amt:
        return await m.answer(f" Мало ({fmt_money(u['balance'])})")
    
    await update_balance(cid, uid, -amt)
    await update_bank(cid, uid, amt)
    bd = await get_bank(cid, uid)
    
    await m.answer(
        f" Вклад: <b>{fmt_money(amt)}</b>. На счету: <b>{fmt_money(bd['deposit'])}</b>",
        parse_mode="HTML"
    )


@dp.message(Command("withdraw"))
async def cmd_withdraw(m: Message):
    """
    Команда /withdraw - снять деньги из банка
    
    Args:
        Аргумент: сумма
    """
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    
    if len(args) < 2:
        return await m.answer("/withdraw сумма")
    
    try:
        amt = int(args[1])
    except:
        return await m.answer("Число!")
    
    bd = await get_bank(cid, uid)
    interest, new_time = await calc_interest(bd['deposit'], bd['last_interest_time'])
    
    if bd['deposit'] < amt:
        return await m.answer(f"❌ На счету {fmt_money(bd['deposit'])}")
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE bank SET deposit=deposit-$1, last_interest_time=$2 WHERE chat_id=$3 AND user_id=$4",
            amt, new_time, cid, uid
        )
    
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
    """
    Команда /credit - взять кредит
    
    Условия:
    - Максимум: 10x баланса
    - Процент: 2% в день
    - Срок: 7 дней
    - При просрочке: арест имущества
    """
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    
    if len(args) < 2:
        return await m.answer(
            "💳 <b>Взять кредит</b>\n\n"
            "Использование: <b>/credit сумма</b>\n\n"
            "Условия:\n"
            "• Максимум: 10x вашего баланса\n"
            "• Процент: 2% в день\n"
            "• Срок: 7 дней\n"
            "• Штраф за просрочку: АРЕСТ ИМУЩЕСТВА",
            parse_mode="HTML"
        )
    
    try:
        amount = int(args[1])
    except:
        return await m.answer("❌ Сумма должна быть числом!")
    
    if amount < 100:
        return await m.answer("❌ Минимальный кредит: 100 сарапулок")
    
    loan = await get_loan(cid, uid)
    if loan['amount'] > 0:
        return await m.answer(
            f"❌ У вас уже есть кредит!\n"
            f"Долг: {fmt_money(loan['amount'])}\n"
            f"Проценты: {fmt_money(loan['interest'])}\n\n"
            f"Сначала погасите: /repay",
            parse_mode="HTML"
        )
    
    user = await get_user(cid, uid)
    max_loan = user['balance'] * 10
    
    if amount > max_loan:
        return await m.answer(f" Максимальный кредит: {fmt_money(max_loan)}")
    
    taken_at = time.time()
    due_date = taken_at + (7 * 86400)
    
    await update_loan(cid, uid, amount, 0, taken_at, due_date)
    await update_balance(cid, uid, amount)
    
    await m.answer(
        f" <b>Кредит оформлен!</b>\n\n"
        f"💰 Получено: {fmt_money(amount)}\n"
        f"📈 Процент: 2% в день\n"
        f"⏰ Вернуть до: {time.strftime('%d.%m.%Y', time.localtime(due_date))}\n\n"
        f"⚠️ При просрочке — АРЕСТ ИМУЩЕСТВА!",
        parse_mode="HTML"
    )


@dp.message(Command("debt"))
async def cmd_debt(m: Message):
    """
    Команда /debt - посмотреть долг
    
    Показывает основной долг, проценты и срок
    """
    cid, uid = m.chat.id, m.from_user.id
    loan = await get_loan(cid, uid)
    
    if loan['amount'] == 0:
        return await m.answer("✅ У вас нет кредитов!")
    
    total_debt = loan['amount'] + loan['interest']
    days_left = int((loan['due_date'] - time.time()) / 86400)
    
    if days_left < 0:
        days_text = "🚔 ПРОСРОЧЕНО! ГРОЗИТ АРЕСТ ИМУЩЕСТВА!"
    elif days_left <= 2:
        days_text = f"⚠️ Осталось: {days_left} дн. Срочно погасите!"
    else:
        days_text = f"Осталось: {days_left} дн."
    
    await m.answer(
        f"💳 <b>Ваш долг</b>\n\n"
        f"📊 Основной долг: <b>{fmt_money(loan['amount'])}</b>\n"
        f"📈 Проценты: <b>{fmt_money(loan['interest'])}</b>\n"
        f"💰 Итого к возврату: <b>{fmt_money(total_debt)}</b>\n\n"
        f"{days_text}\n\n"
        f"Погасить: /repay сумма\n"
        f"Погасить всё: /repay_all",
        parse_mode="HTML"
    )


@dp.message(Command("repay"))
async def cmd_repay(m: Message):
    """
    Команда /repay - погасить часть долга
    
    Сначала списываются проценты, потом основной долг
    """
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    
    if len(args) < 2:
        return await m.answer("💳 Использование: <b>/repay сумма</b>", parse_mode="HTML")
    
    try:
        amount = int(args[1])
    except:
        return await m.answer("❌ Сумма должна быть числом!")
    
    if amount <= 0:
        return await m.answer("❌ Сумма должна быть положительной!")
    
    loan = await get_loan(cid, uid)
    if loan['amount'] == 0:
        return await m.answer("✅ У вас нет кредитов!")
    
    user = await get_user(cid, uid)
    if user['balance'] < amount:
        return await m.answer(f"❌ Недостаточно средств ({fmt_money(user['balance'])})")
    
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
            f"✅ <b>Кредит полностью погашен!</b>\n\n"
            f"Списано: {fmt_money(amount)}\n"
            f"Из них проценты: {fmt_money(interest_paid)}\n"
            f"Основной долг: {fmt_money(principal_paid)}",
            parse_mode="HTML"
        )
    else:
        await update_loan(cid, uid, new_amount, new_interest, loan['taken_at'], loan['due_date'])
        await m.answer(
            f"✅ <b>Частичное погашение!</b>\n\n"
            f"Списано: {fmt_money(amount)}\n"
            f"Остаток долга: <b>{fmt_money(new_amount + new_interest)}</b>\n"
            f"(основной: {fmt_money(new_amount)}, проценты: {fmt_money(new_interest)})",
            parse_mode="HTML"
        )


@dp.message(Command("repay_all"))
async def cmd_repay_all(m: Message):
    """
    Команда /repay_all - погасить весь долг
    
    Списывает всю сумму долга сразу
    """
    cid, uid = m.chat.id, m.from_user.id
    loan = await get_loan(cid, uid)
    
    if loan['amount'] == 0:
        return await m.answer("✅ У вас нет кредитов!")
    
    total_debt = loan['amount'] + loan['interest']
    user = await get_user(cid, uid)
    
    if user['balance'] < total_debt:
        return await m.answer(
            f"❌ Недостаточно средств!\n"
            f"Нужно: {fmt_money(total_debt)}\n"
            f"У вас: {fmt_money(user['balance'])}\n\n"
            f"Используйте /repay для частичного погашения",
            parse_mode="HTML"
        )
    
    await update_balance(cid, uid, -total_debt)
    await clear_loan(cid, uid)
    
    await m.answer(
        f"✅ <b>Кредит полностью погашен!</b>\n\n"
        f"Списано: <b>{fmt_money(total_debt)}</b>\n"
        f"(основной долг: {fmt_money(loan['amount'])}, проценты: {fmt_money(loan['interest'])})",
        parse_mode="HTML"
    )


@dp.message(Command("bailout"))
async def cmd_bailout(m: Message):
    """
    Команда /bailout - информация о выкупе
    
    Показывает стоимость выкупа (200% от долга)
    """
    cid, uid = m.chat.id, m.from_user.id
    loan = await get_loan(cid, uid)
    
    if loan['amount'] == 0:
        return await m.answer(
            "✅ У вас нет активных кредитов.\n\n"
            "Если имущество было арестовано — оно уже конфисковано.\n"
            "Начинайте зарабатывать заново через /work!",
            parse_mode="HTML"
        )
    
    total_debt = loan['amount'] + loan['interest']
    bailout_cost = int(total_debt * 2)
    
    await m.answer(
        f"🚔 <b>Информация о выкупе</b>\n\n"
        f"Текущий долг: <b>{fmt_money(total_debt)}</b>\n"
        f"Стоимость выкупа: <b>{fmt_money(bailout_cost)}</b>\n\n"
        f"⚠️ Выкуп возможен только ДО ареста!\n"
        f"Погасите долг через /repay_all чтобы избежать ареста.",
        parse_mode="HTML"
    )


@dp.message(Command("craft"))
async def cmd_craft(m: Message):
    """
    Команда /craft - список рецептов крафта
    
    Показывает все доступные рецепты с требованиями
    """
    t = "🔨 <b>Крафт:</b>\n"
    for k, v in CRAFT_RECIPES.items():
        req = ", ".join([f"{c}× {n}" for n, c in v["requires"].items()])
        t += f"🔹 {v['name']} ({req}) → /craft_item {k}\n"
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("craft_item"))
async def cmd_craft_item(m: Message):
    """
    Команда /craft_item - крафт предмета
    
    Args:
        Аргумент: ключ рецепта (diamond, scriptka)
    """
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    
    if len(args) < 2:
        return await m.answer("/craft_item diamond")
    
    ik = args[1]
    if ik not in CRAFT_RECIPES:
        return await m.answer("❌ Неизвестный рецепт")
    
    rec = CRAFT_RECIPES[ik]
    
    async with pool.acquire() as conn:
        items = await conn.fetch(
            "SELECT item_name FROM inventory WHERE chat_id=$1 AND user_id=$2",
            cid, uid
        )
    
    inv = {}
    for i in items:
        inv[i['item_name']] = inv.get(i['item_name'], 0) + 1
    
    for rn, rc in rec["requires"].items():
        if inv.get(rn, 0) < rc:
            return await m.answer(f"❌ Нужно {rc}× {rn} (есть {inv.get(rn, 0)})")
    
    async with pool.acquire() as conn:
        for rn, rc in rec["requires"].items():
            await conn.execute(
                "DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3 LIMIT $4)",
                cid, uid, rn, rc
            )
        await conn.execute(
            "INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,'crafted',$4)",
            cid, uid, rec["name"], rec["rarity"]
        )
    
    await m.answer(f"✅ Скрафчено: <b>{rec['name']}</b>", parse_mode="HTML")


@dp.message(Command("trade"))
async def cmd_trade(m: Message):
    """
    Команда /trade - обмен предметами между игроками
    
    Args:
        Аргумент 1: @user (ответ на сообщение)
        Аргумент 2: название предмета
        Аргумент 3: количество
    """
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    
    if len(args) < 4 or not m.reply_to_message:
        return await m.answer("/trade @user предмет кол-во (ответ)")
    
    tid = m.reply_to_message.from_user.id
    iname = args[2]
    
    try:
        cnt = int(args[3])
    except:
        return await m.answer("Число!")
    
    if cnt <= 0 or tid == uid:
        return await m.answer("❌ Ошибка")
    
    async with pool.acquire() as conn:
        have = await conn.fetchval(
            "SELECT COUNT(*) FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3",
            cid, uid, iname
        )
    
    if have < cnt:
        return await m.answer(f" Нет {cnt}× {iname}")
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT item_name, item_type, rarity FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3 LIMIT $4",
            cid, uid, iname, cnt
        )
        await conn.execute(
            "DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE chat_id=$1 AND user_id=$2 AND item_name=$3 LIMIT $4)",
            cid, uid, iname, cnt
        )
        for row in rows:
            await conn.execute(
                "INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1,$2,$3,$4,$5)",
                cid, tid, row['item_name'], row['item_type'], row['rarity']
            )
    
    await m.answer(f"✅ Передано {cnt}× {iname}", parse_mode="HTML")


@dp.message(Command("education"))
async def cmd_education(m: Message):
    """
    Команда /education - список курсов
    
    Показывает все доступные курсы с ценами и статусом прохождения
    """
    cid, uid = m.chat.id, m.from_user.id
    edu = await get_education(cid, uid)
    
    t = "🎓 <b>Образование:</b>\n"
    for k, c in COURSES.items():
        done = k in edu['completed_courses'] or (k=='mba' and edu['has_mba'])
        st = "✅" if done else "🔒"
        t += f"{st} {c['name']} ({fmt_money(c['price'])}) → /buy_course {k}\n"
    
    await m.answer(t, parse_mode="HTML")


@dp.message(Command("buy_course"))
async def cmd_buy_course(m: Message):
    """
    Команда /buy_course - покупка курса и начало экзамена
    
    Args:
        Аргумент: ключ курса (miner, coder, trader, mba)
    """
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    
    if len(args) < 2 or args[1] not in COURSES:
        return await m.answer("/education")
    
    ck = args[1]
    c = COURSES[ck]
    edu = await get_education(cid, uid)
    
    if ck in edu['completed_courses'] or (ck=='mba' and edu['has_mba']):
        return await m.answer("✅ Уже пройдено")
    
    u = await get_user(cid, uid)
    if u['balance'] < c['price']:
        return await m.answer(f"❌ Нужно {fmt_money(c['price'])}")
    
    await update_balance(cid, uid, -c['price'])
    exam_sessions[f"{cid}_{uid}"] = {"course": ck, "question": 0, "correct": 0}
    
    q = c['questions'][0]
    await m.answer(
        f"✅ Курс оплачен!\n\n"
        f"📝 <b>Экзамен:</b> 2 из 3 верно.\n\n"
        f"Вопрос 1:\n"
        f"<b>{q['q']}</b>\n\n"
        f"{' | '.join([f'{i+1}. {a}' for i,a in enumerate(q['a'])])}\n\n"
        f"Напишите номер (1, 2, 3)",
        parse_mode="HTML"
    )


@dp.message(F.text & ~F.text.startswith('/'))
async def handle_exam_answer(m: Message):
    """
    Обработка ответов на экзамене
    
    Фильтр: только текстовые сообщения без команд
    """
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
        return await m.answer("❌ Номер ответа (1, 2, 3)")
    
    if ans < 0 or ans > 2:
        return await m.answer("❌ Номер ответа (1, 2, 3)")
    
    q = c['questions'][ex['question']]
    
    if ans == q['correct']:
        ex['correct'] += 1
        await m.answer("✅ Верно!")
    else:
        await m.answer(f"❌ Неверно! Ответ: {q['a'][q['correct']]}")
    
    ex['question'] += 1
    
    if ex['question'] < 3:
        q = c['questions'][ex['question']]
        await m.answer(
            f"Вопрос {ex['question']+1}:\n"
            f"<b>{q['q']}</b>\n\n"
            f"{' | '.join([f'{i+1}. {a}' for i,a in enumerate(q['a'])])}\n\n"
            f"Напишите номер (1, 2, 3)",
            parse_mode="HTML"
        )
    else:
        if ex['correct'] >= 2:
            await complete_course(cid, uid, ex['course'])
            await m.answer(
                f"🎉 <b>Сдано!</b> Курс <b>{c['name']}</b> завершён!",
                parse_mode="HTML"
            )
        else:
            await m.answer(
                f"😔 <b>Провал.</b> Правильных: {ex['correct']}/3.\n"
                f"Попробуйте: /buy_course {ex['course']}",
                parse_mode="HTML"
            )
        del exam_sessions[ek]


# ============================================================================
# БЛЭКДЖЕК С КНОПКОЙ ОТМЕНЫ
# ============================================================================

def create_deck():
    """
    Создание и перемешивание колоды карт
    
    Returns:
        Список кортежей (ранг, масть)
    """
    suits = ['♠', '♥', '♦', '♣']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    deck = [(r, s) for s in suits for r in ranks]
    random.shuffle(deck)
    return deck


def card_value(card):
    """
    Подсчет стоимости карты
    
    Args:
        card: Кортеж (ранг, масть)
        
    Returns:
        Числовое значение карты
    """
    r = card[0]
    if r in ['J', 'Q', 'K']:
        return 10
    if r == 'A':
        return 11
    return int(r)


def calc_score(cards):
    """
    Подсчет очков руки с учетом тузов
    
    Args:
        cards: Список карт
        
    Returns:
        Сумма очков
    """
    score = sum(card_value(c) for c in cards)
    aces = sum(1 for c in cards if c[0] == 'A')
    while score > 21 and aces > 0:
        score -= 10
        aces -= 1
    return score


def show_cards(cards, hide_first=False):
    """
    Отображение карт
    
    Args:
        cards: Список карт
        hide_first: Скрыть первую карту дилера
        
    Returns:
        Строка с картами
    """
    if hide_first:
        return f" + {' '.join(f'{r}{s}' for r,s in cards[1:])}"
    return ' '.join(f'{r}{s}' for r,s in cards)


@dp.message(Command("blackjack"))
async def blackjack_start(m: Message, state: FSMContext):
    """
    Команда /blackjack - начало игры
    
    Создает стол, ждет игроков 60 секунд, затем переходит к ставкам.
    Минимальный баланс: 100 сарапулок
    """
    cid, uid = m.chat.id, m.from_user.id
    
    if cid in bj_tables:
        return await m.answer("🎰 Игра идёт!")
    
    u = await get_user(cid, uid)
    if u['balance'] < 100:
        return await m.answer(f" Нужно 100+ ({fmt_money(u['balance'])})")
    
    bj_tables[cid] = {
        "players": {
            uid: {
                "name": m.from_user.first_name,
                "bet": 0,
                "cards": [],
                "stand": False,
                "busted": False
            }
        },
        "order": [uid],
        "stage": "waiting",
        "creator": uid
    }
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"bj_join_{cid}")],
        [InlineKeyboardButton(text="❌ Отменить игру", callback_data=f"bj_cancel_{cid}")]
    ])
    
    await m.answer(
        f"🎩 <b>Игорёчек открывает стол!</b>\n\n"
        f"👤 {m.from_user.first_name}\n"
        f"👥 1/5\n"
        f"⏳ 60 сек\n\n"
        f"Нажмите кнопку!\n"
        f"Создатель может отменить игру.",
        reply_markup=kb,
        parse_mode="HTML"
    )
    
    await state.set_state(BlackjackStates.waiting)
    await asyncio.sleep(60)
    
    if cid not in bj_tables:
        return
    
    t = bj_tables[cid]
    
    if len(t["players"]) < 2:
        await m.answer("😔 Мало игроков. Стол закрыт.")
        del bj_tables[cid]
        await state.clear()
        return
    
    t["stage"] = "betting"
    pl = ", ".join(p["name"] for p in t["players"].values())
    
    for uid in t["order"]:
        if uid == t["creator"]:
            bk = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="100", callback_data=f"bet_100_{cid}"),
                 InlineKeyboardButton(text="200", callback_data=f"bet_200_{cid}")],
                [InlineKeyboardButton(text="500", callback_data=f"bet_500_{cid}"),
                 InlineKeyboardButton(text="1000", callback_data=f"bet_1000_{cid}")],
                [InlineKeyboardButton(text="❌ Отменить игру", callback_data=f"bj_cancel_{cid}")]
            ])
        else:
            bk = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="100", callback_data=f"bet_100_{cid}"),
                 InlineKeyboardButton(text="200", callback_data=f"bet_200_{cid}")],
                [InlineKeyboardButton(text="500", callback_data=f"bet_500_{cid}"),
                 InlineKeyboardButton(text="1000", callback_data=f"bet_1000_{cid}")]
            ])
        
        try:
            await bot.send_message(
                uid,
                f"🎩 <b>Ваша ставка?</b>",
                reply_markup=bk,
                parse_mode="HTML"
            )
        except:
            await m.answer(f"️ {t['players'][uid]['name']}, напишите боту в ЛС!")
    
    await m.answer(f"🎩 <b>Игроки:</b> {pl}\n\n💰 Проверьте личку!", parse_mode="HTML")


@dp.callback_query(lambda c: c.data.startswith("bj_join_"))
async def blackjack_join(cb: types.CallbackQuery, state: FSMContext):
    """
    Обработка кнопки присоединения к столу
    
    Проверяет баланс и добавляет игрока в стол
    """
    cid = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    
    if cid not in bj_tables:
        return await cb.answer("Стол закрыт!", show_alert=True)
    
    t = bj_tables[cid]
    
    if t["stage"] != "waiting":
        return await cb.answer("Началась!", show_alert=True)
    
    if uid in t["players"]:
        return await cb.answer("Вы уже тут!", show_alert=True)
    
    if len(t["players"]) >= 5:
        return await cb.answer("Мест нет!", show_alert=True)
    
    u = await get_user(cid, uid)
    if u['balance'] < 100:
        return await cb.answer(f"Нужно 100+ ({fmt_money(u['balance'])})", show_alert=True)
    
    t["players"][uid] = {
        "name": cb.from_user.first_name,
        "bet": 0,
        "cards": [],
        "stand": False,
        "busted": False
    }
    t["order"].append(uid)
    
    await cb.answer("✅ Присоединились!")
    
    pl = "\n".join([f"• {p['name']}" for p in t["players"].values()])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"bj_join_{cid}")],
        [InlineKeyboardButton(text="❌ Отменить игру", callback_data=f"bj_cancel_{cid}")]
    ])
    
    try:
        await cb.message.edit_text(
            f" <b>Игроки ({len(t['players'])}/5):\n{pl}\n\n⏳ Ждём...</b>",
            reply_markup=kb,
            parse_mode="HTML"
        )
    except:
        pass


@dp.callback_query(lambda c: c.data.startswith("bj_cancel_"))
async def blackjack_cancel(cb: types.CallbackQuery, state: FSMContext):
    """
    Обработка кнопки отмены игры
    
    Только создатель стола может отменить игру.
    Возвращает ставки всем игрокам.
    """
    cid = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    
    if cid not in bj_tables:
        return await cb.answer("Игра уже завершена!", show_alert=True)
    
    t = bj_tables[cid]
    
    if uid != t["creator"]:
        return await cb.answer("❌ Отменить может только создатель!", show_alert=True)
    
    if t["stage"] == "playing":
        return await cb.answer("❌ Игра уже началась!", show_alert=True)
    
    refunded = []
    for pid, pd in t["players"].items():
        if pd["bet"] > 0:
            await update_balance(cid, pid, pd["bet"])
            refunded.append(f"• {pd['name']}: +{fmt_money(pd['bet'])}")
    
    del bj_tables[cid]
    await state.clear()
    
    rt = "\n".join(refunded) if refunded else "Никто не успел поставить"
    
    try:
        await cb.message.edit_text(
            f"❌ <b>Игра отменена!</b>\n\n"
            f"👤 {cb.from_user.first_name}\n\n"
            f"💰 Возврат:\n{rt}",
            parse_mode="HTML"
        )
    except:
        pass
    
    await cb.answer("✅ Игра отменена!")


@dp.callback_query(lambda c: c.data.startswith("bet_"))
async def blackjack_bet(cb: types.CallbackQuery, state: FSMContext):
    """
    Обработка кнопки ставки
    
    Проверяет баланс и записывает ставку
    """
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
        await cb.message.edit_text(
            f"✅ Ставка: <b>{bet}</b>. Ждём...",
            parse_mode="HTML"
        )
    except:
        pass
    
    await cb.answer(f"Ставка {bet} принята!")
    
    if all(p["bet"] > 0 for p in t["players"].values()):
        await blackjack_deal(cid, state)


async def blackjack_deal(cid, state):
    """
    Раздача карт
    
    Раздает по 2 карты каждому игроку и 2 карты дилеру
    """
    t = bj_tables[cid]
    t["deck"] = create_deck()
    
    for uid in t["order"]:
        t["players"][uid]["cards"] = [t["deck"].pop(), t["deck"].pop()]
    
    t["dealer"] = [t["deck"].pop(), t["deck"].pop()]
    t["stage"] = "playing"
    
    pi = "\n".join([f" {p['name']}: {p['bet']}" for p in t["players"].values()])
    
    await bot.send_message(
        cid,
        f"🎩 <b>Карты розданы!</b>\n\n"
        f"🤖 Мои: {show_cards(t['dealer'], True)}\n\n"
        f"{pi}\n\n"
        f" Ходит: <b>{t['players'][t['order'][0]]['name']}</b>",
        parse_mode="HTML"
    )
    
    await state.set_state(BlackjackStates.playing)
    await blackjack_player_turn(cid, t["order"][0], state)


async def blackjack_player_turn(cid, uid, state):
    """
    Ход игрока
    
    Отправляет игроку его карты и кнопки действий
    """
    t = bj_tables[cid]
    p = t["players"][uid]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Ещё", callback_data=f"hit_{uid}_{cid}"),
         InlineKeyboardButton(text="✋ Хватит", callback_data=f"stand_{uid}_{cid}")]
    ])
    
    await bot.send_message(
        uid,
        f"🎩 <b>Ваш ход!</b>\n\n"
        f"🃏 Ваши: {show_cards(p['cards'])}\n"
        f" Сумма: <b>{calc_score(p['cards'])}</b>\n"
        f"💰 Ставка: {p['bet']}\n\n"
        f"🎴 Карта Игорёчка: {t['dealer'][0][0]}{t['dealer'][0][1]}",
        reply_markup=kb,
        parse_mode="HTML"
    )


@dp.callback_query(lambda c: c.data.startswith("hit_") or c.data.startswith("stand_"))
async def blackjack_hit_stand(cb: types.CallbackQuery, state: FSMContext):
    """
    Обработка кнопок 'Ещё карту' и 'Хватит'
    """
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
        
        await cb.message.edit_text(
            f"🎩 Взял карту!\n\n"
            f"🃏 +{c[0]}{c[1]}\n"
            f"📊 {show_cards(p['cards'])}\n"
            f"🔢 Сумма: <b>{sc}</b>",
            parse_mode="HTML"
        )
        
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
                [InlineKeyboardButton(text="🃏 Ещё", callback_data=f"hit_{uid}_{cid}"),
                 InlineKeyboardButton(text="✋ Хватит", callback_data=f"stand_{uid}_{cid}")]
            ])
            await cb.message.answer(f"💰 Сумма: {sc}. Ещё?", reply_markup=kb)
    
    elif act == "stand":
        p["stand"] = True
        await cb.message.edit_text(
            f"✋ Остановился на <b>{calc_score(p['cards'])}</b>",
            parse_mode="HTML"
        )
        await blackjack_next_turn(cid, state)


async def blackjack_next_turn(cid, state):
    """
    Переход к следующему игроку
    """
    t = bj_tables[cid]
    nxt = next((u for u in t["order"] if not t["players"][u]["stand"]), None)
    
    if nxt:
        await bot.send_message(
            cid,
            f" Ходит: <b>{t['players'][nxt]['name']}</b>",
            parse_mode="HTML"
        )
        await blackjack_player_turn(cid, nxt, state)
    else:
        await blackjack_dealer_play(cid, state)


async def blackjack_dealer_play(cid, state):
    """
    Ход Игорёчка (дилера)
    
    Дилер берет карты пока сумма < 17
    """
    t = bj_tables[cid]
    
    await bot.send_message(
        cid,
        f" <b>Ход Игорёчка!</b>\n\n"
        f"🤖 Мои: {show_cards(t['dealer'])}",
        parse_mode="HTML"
    )
    
    while calc_score(t["dealer"]) < 17:
        await asyncio.sleep(1)
        c = t["deck"].pop()
        t["dealer"].append(c)
        await bot.send_message(
            cid,
            f"🎩 Берёт: <b>{c[0]}{c[1]}</b> → <b>{calc_score(t['dealer'])}</b>",
            parse_mode="HTML"
        )
    
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
    
    fn = "😱 Перебрал!" if ds > 21 else "🎉 Поздравляем!" if any("победа" in r for r in res) else "🎩 Забирает ставки!" if any("проигрыш" in r for r in res) else "🤝 Ничья!"
    
    await bot.send_message(
        cid,
        f"🎩 <b>{fn}</b>\n\n"
        f"🤖 Карты: {show_cards(t['dealer'])} ({ds})\n\n"
        f" Результаты:\n" + "\n".join(res),
        parse_mode="HTML"
    )
    
    del bj_tables[cid]
    await state.clear()


# ============================================================================
# АВТО-РЕГИСТРАЦИЯ И ПРИВЕТСТВИЕ
# ============================================================================

@dp.message()
async def auto_register(m: Message):
    """
    Автоматическая регистрация пользователей в группе
    
    Срабатывает на каждое сообщение в группе
    """
    if m.chat.type not in ['group', 'supergroup']:
        return
    await get_user(m.chat.id, m.from_user.id)


@dp.message(F.new_chat_members)
async def on_user_join(m: Message):
    """
    Приветствие новых участников
    
    Автоматически регистрирует новых пользователей
    """
    cid = m.chat.id
    
    for user in m.new_chat_members:
        if user.is_bot:
            if user.id == int(API_TOKEN.split(':')[0]):
                await m.answer(" Привет! Я экономический бот. /start")
            continue
        await get_user(cid, user.id)
        await save_username(cid, user.id, user.full_name)


# ============================================================================
# ЗАПУСК БОТА
# ============================================================================

async def main():
    """
    Главная функция запуска бота
    
    Инициализирует базу данных, запускает веб-сервер и фоновые задачи
    """
    await init_db()
    print("🤖 Бот запущен!")
    
    await start_web_server()
    asyncio.create_task(polling_health_check())
    asyncio.create_task(auto_lottery_loop())
    asyncio.create_task(loan_interest_loop())
    
    await dp.start_polling(
        bot,
        timeout=30,
        allowed_updates=["message", "callback_query", "my_chat_member"]
    )


if __name__ == "__main__":
    asyncio.run(main())
