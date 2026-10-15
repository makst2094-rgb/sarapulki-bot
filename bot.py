# ============================================================================
# 🤖 ЭКОНОМИЧЕСКИЙ БОТ ДЛЯ TELEGRAM ГРУПП - ПОЛНАЯ ВЕРСИЯ 5.0
# ============================================================================
# Автор: Создан для группы "Сарапулки"
# Версия: 5.0 Ultimate Edition
# Описание: Полноценная экономическая система с изоляцией групп
# Функции: Работа, Банк, Блэкджек, Образование, Крафт, Трейд, Лотерея
# ============================================================================


# ==================== ИМПОРТ БИБЛИОТЕК ====================
# Основные библиотеки для работы бота
import asyncio
import logging
import random
import time
import os

# Aiogram - фреймворк для Telegram ботов
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# База данных PostgreSQL
import asyncpg

# Веб-сервер для UptimeRobot
from aiohttp import web


# ==================== НАСТРОЙКИ БОТА ====================
# Токен бота берется из переменных окружения Render
API_TOKEN = os.environ.get("BOT_TOKEN", "")

# ID администраторов (через запятую)
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]

# URL базы данных PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL", "")


# ==================== ИНИЦИАЛИЗАЦИЯ ЛОГГЕРА ====================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
pool = None


# ==================== СОСТОЯНИЯ FSM ====================
class BlackjackStates(StatesGroup):
    """Состояния для игры в Блэкджек"""
    waiting = State()    # Ожидание игроков
    betting = State()    # Ставки
    playing = State()    # Игра


# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
bj_tables = {}      # Активные столы Блэкджека
exam_sessions = {}  # Активные сессии экзаменов


# ==================== РЕЦЕПТЫ КРАФТА ====================
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
LOTTERY_PRICE = 50              # Цена билета
LOTTERY_INTERVAL = 12 * 3600    # Интервал розыгрыша (12 часов)


# ==================== НАСТРОЙКИ БАНКА ====================
BANK_INTEREST_RATE = 0.01  # 1% в сутки


# ==================== КУРСЫ ОБРАЗОВАНИЯ ====================
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
        "name": "💻 Курс программирования",
        "price": 1000,
        "required_for": "coder",
        "questions": [
            {"q": "Язык для веб-разработки?", "a": ["Python", "HTML", "C++"], "correct": 1},
            {"q": "Что такое баг?", "a": ["ошибка", "функция", "переменная"], "correct": 0},
            {"q": "Сколько бит в байте?", "a": ["4", "8", "16"], "correct": 1}
        ]
    },
    "trader": {
        "name": " Курс трейдинга",
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
    Пример: pluralize(5, ['яблоко', 'яблока', 'яблок']) -> 'яблок'
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
    Пример: fmt_money(5) -> '5 сарапулок'
    """
    word = pluralize(amount, ['сарапулка', 'сарапулки', 'сарапулок'])
    return f"{amount} {word}"


# ==================== КОНФИГУРАЦИЯ РАБОТЫ ====================
JOBS = {
    "novice": {
        "name": "👶 Новичок",
        "base_pay": 10,
        "cooldown": 3600
    },
    "miner": {
        "name": "⛏️ Шахтёр",
        "base_pay": 25,
        "cooldown": 3600
    },
    "coder": {
        "name": "💻 Программист",
        "base_pay": 50,
        "cooldown": 7200
    },
    "trader": {
        "name": "📈 Трейдер",
        "base_pay": 80,
        "cooldown": 10800
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
MARKET = {
    "case_basic": {
        "name": "📦 Обычный кейс",
        "price": 200,
        "type": "case"
    },
    "biz_shawarma": {
        "name": "🌯 Ларёк с шаурмой",
        "price": 2000,
        "type": "business",
        "income": 150
    },
    "biz_crypto": {
        "name": " Крипто-ферма",
        "price": 15000,
        "type": "business",
        "income": 1200
    }
}


# ==================== АВТОСАЛОН ====================
CARS = {
    "ok": {
        "name": " Ока",
        "price": 3000,
        "desc": "Едет и едет."
    },
    "priora": {
        "name": "🚘 Приора",
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


# ==================== НАСТРОЙКИ СЛОТОВ ====================
SLOTS_SYMBOLS = ['🍒', '🍋', '🍊', '🍇', '', '7️⃣']
SLOTS_PAYOUTS = {
    '7️7️⃣7️⃣': 10,
    '💎💎': 5,
    '🍇🍇': 3,
    '🍊🍊🍊': 2,
    '🍋🍋': 2,
    '🍒🍒': 2
}


# ============================================================================
# БАЗА ДАННЫХ
# ============================================================================

async def init_db():
    """
    Инициализация базы данных PostgreSQL
    Создает все необходимые таблицы если их нет
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
        # Таблица пользователей
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id BIGINT,
                user_id BIGINT,
                balance INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Таблица профилей
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
        
        # Таблица инвентаря
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
        
        # Таблица гаража
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
        
        # Таблица ограблений
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
        
        # Таблица банка
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bank (
                chat_id BIGINT,
                user_id BIGINT,
                deposit INTEGER DEFAULT 0,
                last_interest_time REAL DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Таблица образования
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS education (
                chat_id BIGINT,
                user_id BIGINT,
                completed_courses TEXT[] DEFAULT '{}',
                has_mba BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
    print("✅ База данных готова")


async def save_username(chat_id, user_id, username):
    """Сохранение имени пользователя в базу данных"""
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO usernames (chat_id, user_id, username) VALUES ($1, $2, $3) ON CONFLICT (chat_id, user_id) DO UPDATE SET username = $3",
            chat_id, user_id, username
        )


async def get_user(chat_id, user_id):
    """Получение данных пользователя"""
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
    """Обновление баланса пользователя"""
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET balance = balance + $1 WHERE chat_id = $2 AND user_id = $3",
            amount, chat_id, user_id
        )


async def get_profile(chat_id, user_id):
    """Получение профиля пользователя"""
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
    """Установка машины пользователю"""
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO garage (chat_id, user_id, car_key, car_name) VALUES ($1, $2, $3, $4) ON CONFLICT (chat_id, user_id) DO UPDATE SET car_key = $3, car_name = $4",
            chat_id, user_id, car_key, car_name
        )


async def get_car(chat_id, user_id):
    """Получение машины пользователя"""
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT car_name FROM garage WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )


async def get_bank(chat_id, user_id):
    """Получение данных банка пользователя"""
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
    """Обновление депозита в банке"""
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE bank SET deposit = deposit + $1 WHERE chat_id = $2 AND user_id = $3",
            amount, chat_id, user_id
        )


async def calc_interest(deposit, last_time):
    """Расчет накопленных процентов"""
    now = time.time()
    days_passed = (now - last_time) / 86400
    interest = int(deposit * BANK_INTEREST_RATE * days_passed)
    return interest, now


async def get_education(chat_id, user_id):
    """Получение данных об образовании пользователя"""
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
    """Завершение курса образования"""
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


# ============================================================================
# ВЕБ-СЕРВЕР И ЗДОРОВЬЕ БОТА
# ============================================================================

async def handle_ping(request):
    """Обработчик ping-запросов от UptimeRobot"""
    return web.Response(text="🤖 Bot is alive!")


async def start_web_server():
    """Запуск веб-сервера для UptimeRobot"""
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("🌐 Web server started")


async def polling_health_check():
    """Проверка здоровья бота каждые 5 минут"""
    while True:
        try:
            await asyncio.sleep(300)
            await bot.get_me()
            print("✅ Health check OK")
        except Exception as e:
            print(f" Health check failed: {e}")


async def auto_lottery_loop():
    """Автоматический розыгрыш лотереи каждые 12 часов"""
    print("🎰 Авто-лотерея запущена")
    while True:
        await asyncio.sleep(3600)
        now = time.time()
        async with pool.acquire() as conn:
            chats = await conn.fetch("SELECT DISTINCT chat_id FROM lottery_tickets")
            for row in chats:
                chat_id = row['chat_id']
                tickets = await conn.fetch(
                    "SELECT id, user_id FROM lottery_tickets WHERE chat_id = $1 AND buy_time <= $2",
                    chat_id, now - LOTTERY_INTERVAL
                )
                if len(tickets) >= 2:
                    winner = random.choice(tickets)
                    bank = len(tickets) * LOTTERY_PRICE
                    await update_balance(chat_id, winner['user_id'], bank)
                    winner_name = await conn.fetchval(
                        "SELECT username FROM usernames WHERE chat_id = $1 AND user_id = $2",
                        chat_id, winner['user_id']
                    ) or f"User{winner['user_id']}"
                    await conn.execute("DELETE FROM lottery_tickets WHERE chat_id = $1", chat_id)
                    try:
                        await bot.send_message(
                            chat_id,
                            f"🎊 <b>АВТО-РОЗЫГРЫШ ЛОТЕРЕИ!</b>\n\n"
                            f"🏆 Победитель: <b>{winner_name}</b>\n"
                            f"💰 Банк: <b>{fmt_money(bank)}</b>\n"
                            f"️ Билетов: {len(tickets)}",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"❌ Ошибка лотереи: {e}")


# ============================================================================
# ОСНОВНЫЕ КОМАНДЫ
# ============================================================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start - главное меню"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    await message.answer(
        " <b>Добро пожаловать в Экономику группы!</b>\n\n"
        "💰 <b>/balance</b> — мой баланс\n"
        "💼 <b>/work</b> — работать\n"
        "💸 <b>/pay</b> — перевести (ответь на сообщение)\n"
        "🔫 <b>/rob</b> — ограбить (ответь на сообщение)\n"
        "🎁 <b>/daily</b> — ежедневный бонус\n"
        "🎰 <b>/slots</b> ставка — казино\n"
        "️ <b>/buy_ticket</b> — лотерейный билет\n"
        " <b>/shop</b> — улучшения\n"
        "🏪 <b>/market</b> — бизнесы и кейсы\n"
        "🚗 <b>/cars</b> — автосалон\n"
        "️ <b>/mycar</b> — моя тачка\n"
        "💼 <b>/collect</b> — прибыль с бизнеса\n"
        "🎒 <b>/inv</b> — инвентарь\n"
        " <b>/info</b> — моя карточка\n"
        "🏆 <b>/rating</b> — рейтинг богачей\n"
        "🃏 <b>/blackjack</b> — Блэкджек с Игорёчком\n"
        "🔨 <b>/craft</b> — крафт предметов\n"
        "🔄 <b>/trade</b> — обмен с игроком\n"
        "🏦 <b>/bank</b> — банковский счёт\n"
        "📥 <b>/deposit</b> — положить в банк\n"
        "📤 <b>/withdraw</b> — снять из банка\n"
        "🎓 <b>/education</b> — образование\n"
        "📘 <b>/buy_course</b> — купить курс",
        parse_mode="HTML"
    )


@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    """Команда /balance - проверка баланса"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    user = await get_user(chat_id, user_id)
    car = await get_car(chat_id, user_id)
    car_text = f"\n🚗 Тачка: <b>{car}</b>" if car else "\n🚗 Тачка: <i>нет</i> (/cars)"
    await message.answer(
        f"💰 <b>Твой баланс:</b>\n{fmt_money(user['balance'])}{car_text}",
        parse_mode="HTML"
    )


@dp.message(Command("work"))
async def cmd_work(message: Message):
    """Команда /work - работа"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    
    # Проверяем профиль
    profile = await get_profile(chat_id, user_id)
    job_key = profile['job_key']
    
    # Проверяем, есть ли у пользователя курс для текущей профессии
    if job_key != 'novice':
        edu = await get_education(chat_id, user_id)
        if job_key not in edu['completed_courses']:
            # Если профессии нет в пройденных курсах - сбрасываем на novice
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE profiles SET job_key = 'novice' WHERE chat_id = $1 AND user_id = $2",
                    chat_id, user_id
                )
            job_key = 'novice'
            profile['job_key'] = 'novice'
    
    job = JOBS[job_key]
    current_time = time.time()
    cooldown = job['cooldown'] * (0.9 if profile['has_coffee'] else 1.0)
    time_passed = current_time - profile['last_work_time']
    
    if time_passed < cooldown:
        remaining = int(cooldown - time_passed)
        minutes = remaining // 60
        return await message.answer(f"⏳ Отдыхайте ещё <b>{minutes}</b> мин.", parse_mode="HTML")
    
    salary = job['base_pay'] * profile['level'] + random.randint(0, 5)
    edu = await get_education(chat_id, user_id)
    if edu['has_mba']:
        salary = int(salary * 1.5)
    
    await update_balance(chat_id, user_id, salary)
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE profiles SET last_work_time = $1 WHERE chat_id = $2 AND user_id = $3",
            current_time, chat_id, user_id
        )
    
    await message.answer(
        f" <b>{job['name']}</b> (Ур. {profile['level']})\nЗаработано: <b>{fmt_money(salary)}</b>",
        parse_mode="HTML"
    )


@dp.message(Command("jobs"))
async def cmd_jobs(message: Message):
    """Команда /jobs - список вакансий"""
    text = "📋 <b>Доступные вакансии:</b>\n\n"
    for key, info in JOBS.items():
        text += f"🔹 <b>{info['name']}</b>\n"
        text += f"   💰 {info['base_pay']} сарапулок/час\n"
        text += f"   ⏱️ Кулдаун: {info['cooldown'] // 3600} ч\n"
        text += f"   → /job {key}\n\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("job"))
async def cmd_change_job(message: Message):
    """Команда /job - смена работы"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2 or args[1] not in JOBS:
        return await message.answer("❌ Выберите работу: /jobs")
    
    # Проверяем наличие курса (кроме novice)
    if args[1] != 'novice':
        edu = await get_education(chat_id, user_id)
        if args[1] not in edu['completed_courses']:
            course = COURSES.get(args[1])
            if course:
                return await message.answer(
                    f"❌ Нужен курс: <b>{course['name']}</b>\nКупите: /buy_course {args[1]}",
                    parse_mode="HTML"
                )
    
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE profiles SET job_key = $1 WHERE chat_id = $2 AND user_id = $3",
            args[1], chat_id, user_id
        )
    await message.answer(f"✅ Вы теперь: <b>{JOBS[args[1]]['name']}</b>", parse_mode="HTML")


@dp.message(Command("pay"))
async def cmd_pay(message: Message):
    """Команда /pay - перевод денег"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        return await message.answer(" Использование: <b>/pay сумма</b> (ответь на сообщение)", parse_mode="HTML")
    if not message.reply_to_message:
        return await message.answer("❌ Ответьте на сообщение получателя!")
    try:
        amount = int(args[1])
    except:
        return await message.answer(" Сумма должна быть числом!")
    if amount <= 0:
        return await message.answer("❌ Сумма должна быть положительной!")
    sender_id = user_id
    receiver_id = message.reply_to_message.from_user.id
    if sender_id == receiver_id:
        return await message.answer("❌ Нельзя перевести самому себе!")
    sender_bal = await get_user(chat_id, sender_id)
    if sender_bal['balance'] < amount:
        return await message.answer(f"❌ Недостаточно средств ({fmt_money(sender_bal['balance'])})")
    await update_balance(chat_id, sender_id, -amount)
    await update_balance(chat_id, receiver_id, amount)
    await save_username(chat_id, receiver_id, message.reply_to_message.from_user.full_name)
    await message.answer(
        f"✅ <b>{message.from_user.full_name}</b> перевёл <b>{fmt_money(amount)}</b> пользователю <b>{message.reply_to_message.from_user.full_name}</b>",
        parse_mode="HTML"
    )


@dp.message(Command("rob"))
async def cmd_rob(message: Message):
    """Команда /rob - ограбление"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not message.reply_to_message:
        return await message.answer("🔫 Ответьте на сообщение жертвы!")
    robber_id = user_id
    victim_id = message.reply_to_message.from_user.id
    if robber_id == victim_id:
        return await message.answer("❌ Нельзя ограбить самого себя!")
    async with pool.acquire() as conn:
        last_rob = await conn.fetchval(
            "SELECT last_robbery FROM robbery WHERE chat_id = $1 AND user_id = $2",
            chat_id, robber_id
        )
        last_rob = last_rob or 0
        current_time = time.time()
        if current_time - last_rob < 10800:
            remaining = int(10800 - (current_time - last_rob))
            hours = remaining // 3600
            return await message.answer(f"⏳ Отдыхайте ещё <b>{hours}</b> ч.", parse_mode="HTML")
        await conn.execute(
            "INSERT INTO robbery (chat_id, user_id, last_robbery) VALUES ($1, $2, $3) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_robbery = $3",
            chat_id, robber_id, current_time
        )
    victim_bal = await get_user(chat_id, victim_id)
    available_balance = victim_bal['balance']
    if available_balance < 50:
        return await message.answer(" У жертвы слишком мало денег!")
    success = random.random() < 0.4
    if success:
        stolen = int(available_balance * random.uniform(0.1, 0.5))
        await update_balance(chat_id, victim_id, -stolen)
        await update_balance(chat_id, robber_id, stolen)
        await message.answer(
            f"🔫 <b>ОГРАБЛЕНИЕ УСПЕШНО!</b>\n\n{message.from_user.full_name} украл <b>{fmt_money(stolen)}</b> у {message.reply_to_message.from_user.full_name}!",
            parse_mode="HTML"
        )
    else:
        robber_bal = await get_user(chat_id, robber_id)
        penalty = int(robber_bal['balance'] * 0.2)
        await update_balance(chat_id, robber_id, -penalty)
        await update_balance(chat_id, victim_id, penalty)
        await message.answer(
            f"🚔 <b>ПОПАЛСЯ!</b>\n\n{message.from_user.full_name} заплатил штраф <b>{fmt_money(penalty)}</b> пользователю {message.reply_to_message.from_user.full_name}!",
            parse_mode="HTML"
        )


@dp.message(Command("daily"))
async def cmd_daily(message: Message):
    """Команда /daily - ежедневный бонус"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    current_time = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT last_claim, streak FROM daily_bonus WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )
        last_claim, streak = (row['last_claim'], row['streak']) if row else (0, 0)
        if current_time - last_claim < 86400:
            remaining = int(86400 - (current_time - last_claim))
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            return await message.answer(f"⏰ Приходи через <b>{hours}</b> ч. <b>{minutes}</b> мин.", parse_mode="HTML")
        if current_time - last_claim < 172800:
            streak += 1
        else:
            streak = 1
        base_bonus = random.randint(100, 300)
        multiplier = min(streak, 7)
        bonus = base_bonus * multiplier
        await update_balance(chat_id, user_id, bonus)
        await conn.execute(
            "INSERT INTO daily_bonus (chat_id, user_id, last_claim, streak) VALUES ($1, $2, $3, $4) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_claim = $3, streak = $4",
            chat_id, user_id, current_time, streak
        )
    await message.answer(
        f"🎁 <b>Ежедневный бонус!</b>\n\n🔥 Ты зашёл <b>{streak}</b> {pluralize(streak, ['день', 'дня', 'дней'])} подряд!\n💰 Получено: <b>{fmt_money(bonus)}</b>",
        parse_mode="HTML"
    )


@dp.message(Command("slots"))
async def cmd_slots(message: Message):
    """Команда /slots - игровые автоматы"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("🎰 Укажите ставку: <b>/slots 100</b>", parse_mode="HTML")
    try:
        bet = int(args[1])
    except:
        return await message.answer("❌ Ставка должна быть числом!")
    if bet < 10:
        return await message.answer("❌ Минимальная ставка: 10 сарапулок")
    user_bal = await get_user(chat_id, user_id)
    if user_bal['balance'] < bet:
        return await message.answer(f"❌ Недостаточно ({fmt_money(user_bal['balance'])})")
    await update_balance(chat_id, user_id, -bet)
    result = [random.choice(SLOTS_SYMBOLS) for _ in range(3)]
    result_str = ''.join(result)
    win_amount = 0
    if result_str in SLOTS_PAYOUTS:
        multiplier = SLOTS_PAYOUTS[result_str]
        win_amount = bet * multiplier
        await update_balance(chat_id, user_id, win_amount)
    text = f"🎰 <b>СЛОТЫ</b>\n\n💰 Ставка: {fmt_money(bet)}\n🎲 Результат: {' | '.join(result)}\n\n"
    if win_amount > 0:
        text += f"🎉 <b>ВЫИГРЫШ: {fmt_money(win_amount)}</b> (x{SLOTS_PAYOUTS[result_str]})"
    else:
        text += "💀 Проигрыш. Попробуй ещё раз!"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("buy_ticket"))
async def cmd_buy_ticket(message: Message):
    """Команда /buy_ticket - покупка лотерейного билета"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    user_bal = await get_user(chat_id, user_id)
    if user_bal['balance'] < LOTTERY_PRICE:
        return await message.answer(f"❌ Билет стоит {fmt_money(LOTTERY_PRICE)}")
    await update_balance(chat_id, user_id, -LOTTERY_PRICE)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO lottery_tickets (chat_id, user_id, buy_time) VALUES ($1, $2, $3)",
            chat_id, user_id, time.time()
        )
    await message.answer(
        f"🎟️ Вы купили лотерейный билет за {fmt_money(LOTTERY_PRICE)}!\n\n⏰ Розыгрыш произойдёт автоматически через 12 часов.",
        parse_mode="HTML"
    )


@dp.message(Command("info"))
async def cmd_info(message: Message):
    """Команда /info - карточка игрока"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await save_username(chat_id, user_id, message.from_user.full_name)
    user = await get_user(chat_id, user_id)
    profile = await get_profile(chat_id, user_id)
    car = await get_car(chat_id, user_id)
    bank_data = await get_bank(chat_id, user_id)
    edu = await get_education(chat_id, user_id)
    async with pool.acquire() as conn:
        biz_count = await conn.fetchval(
            "SELECT COUNT(*) FROM businesses WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )
        inv_count = await conn.fetchval(
            "SELECT COUNT(*) FROM inventory WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )
    job = JOBS[profile['job_key']]
    courses_completed = len(edu['completed_courses']) + (1 if edu['has_mba'] else 0)
    text = f" <b>Карточка игрока</b>\n\n👤 <b>{message.from_user.full_name}</b>\n\n"
    text += f"💰 Баланс: <b>{fmt_money(user['balance'])}</b>\n"
    text += f"🏦 В банке: <b>{fmt_money(bank_data['deposit'])}</b>\n"
    text += f"💼 Профессия: <b>{job['name']}</b> (Ур. {profile['level']})\n"
    text += f"🚗 Машина: <b>{car if car else 'нет'}</b>\n"
    text += f" Бизнесов: <b>{biz_count}</b>\n"
    text += f"🎒 Предметов: <b>{inv_count}</b>\n"
    text += f"🎓 Курсов: <b>{courses_completed}</b>\n"
    if edu['has_mba']:
        text += f"🎯 MBA: <b>есть</b> (+50% зарплата)\n"
    if profile['has_coffee']:
        text += f"☕ Кофе-машина: <b>есть</b>\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    """Команда /shop - магазин улучшений"""
    text = "🛒 <b>Улучшения:</b>\n\n"
    for k, v in SHOP_ITEMS.items():
        text += f"🔹 <b>{v['name']}</b>\n"
        text += f"   💰 {fmt_money(v['price'])}\n"
        text += f"   📝 {v['desc']}\n"
        text += f"   → /buy {k}\n\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("buy"))
async def cmd_buy(message: Message):
    """Команда /buy - покупка улучшений"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2 or args[1] not in SHOP_ITEMS:
        return await message.answer("🛒 Используйте: /shop")
    item = SHOP_ITEMS[args[1]]
    user = await get_user(chat_id, user_id)
    if user['balance'] < item['price']:
        return await message.answer(f"❌ Нужно {fmt_money(item['price'])}")
    await update_balance(chat_id, user_id, -item['price'])
    if item['type'] == 'level_up':
        p = await get_profile(chat_id, user_id)
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE profiles SET level = $1 WHERE chat_id = $2 AND user_id = $3",
                p['level'] + 1, chat_id, user_id
            )
        await message.answer(f"✅ Уровень повышен до <b>{p['level'] + 1}</b>!", parse_mode="HTML")
    elif item['type'] == 'cooldown_reduce':
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE profiles SET has_coffee = TRUE WHERE chat_id = $1 AND user_id = $2",
                chat_id, user_id
            )
        await message.answer("✅ Кофе-машина куплена! Работа быстрее на 10%.")


@dp.message(Command("market"))
async def cmd_market(message: Message):
    """Команда /market - рынок"""
    text = "🏪 <b>Рынок:</b>\n\n"
    for k, v in MARKET.items():
        text += f" <b>{v['name']}</b>\n"
        text += f"   💰 {fmt_money(v['price'])}\n"
        text += f"   → /buy_market {k}\n\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("buy_market"))
async def cmd_buy_market(message: Message):
    """Команда /buy_market - покупка на рынке"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2 or args[1] not in MARKET:
        return await message.answer("🏪 Используйте: /market")
    item = MARKET[args[1]]
    user = await get_user(chat_id, user_id)
    if user['balance'] < item['price']:
        return await message.answer(f"❌ Нужно {fmt_money(item['price'])}")
    await update_balance(chat_id, user_id, -item['price'])
    if item['type'] == 'case':
        rand = random.randint(1, 100)
        if rand <= 5:
            prize, rar = " Золотая Скрипка", "legendary"
        elif rand <= 25:
            prize, rar = "💎 Алмаз", "rare"
        else:
            prize, rar = "📄 Бумага", "common"
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1, $2, $3, 'card', $4)",
                chat_id, user_id, prize, rar
            )
        await message.answer(f"📦 <b>Выпало:</b> {prize}\nРедкость: <b>{rar}</b>", parse_mode="HTML")
    elif item['type'] == 'business':
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO businesses (chat_id, user_id, business_name, income) VALUES ($1, $2, $3, $4)",
                chat_id, user_id, item['name'], item['income']
            )
        await message.answer(
            f"✅ Куплен <b>{item['name']}</b>!\n💰 Доход: {fmt_money(item['income'])}/сутки\nЖми /collect раз в сутки!",
            parse_mode="HTML"
        )


@dp.message(Command("collect"))
async def cmd_collect(message: Message):
    """Команда /collect - сбор прибыли с бизнеса"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    now = time.time()
    total = 0
    async with pool.acquire() as conn:
        bizs = await conn.fetch(
            "SELECT id, income, last_collect_time FROM businesses WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )
        if not bizs:
            return await message.answer("❌ Нет бизнеса.")
        for biz in bizs:
            if now - biz['last_collect_time'] > 86400:
                total += biz['income']
                await conn.execute(
                    "UPDATE businesses SET last_collect_time = $1 WHERE id = $2",
                    now, biz['id']
                )
    if total > 0:
        await update_balance(chat_id, user_id, total)
        await message.answer(f"💼 Прибыль: <b>+{fmt_money(total)}</b>", parse_mode="HTML")
    else:
        await message.answer("⏳ Рано. Приходи завтра.")


@dp.message(Command("cars"))
async def cmd_cars(message: Message):
    """Команда /cars - автосалон"""
    text = "🚗 <b>Автосалон:</b>\n\n"
    for k, v in CARS.items():
        text += f"🔸 <b>{v['name']}</b>\n"
        text += f"   💰 {fmt_money(v['price'])}\n"
        text += f"   <i>{v['desc']}</i>\n"
        text += f"   Купить: <code>/buycar {k}</code>\n\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("buycar"))
async def cmd_buycar(message: Message):
    """Команда /buycar - покупка машины"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2 or args[1] not in CARS:
        return await message.answer("🚗 Используйте: /cars")
    car_key = args[1]
    car = CARS[car_key]
    user = await get_user(chat_id, user_id)
    if user['balance'] < car['price']:
        return await message.answer(f"❌ Нужно {fmt_money(car['price'])}")
    await update_balance(chat_id, user_id, -car['price'])
    await set_car(chat_id, user_id, car_key, car['name'])
    await message.answer(
        f"🎉 <b>КУПЛЕНО!</b>\n\nТеперь ты ездишь на <b>{car['name']}</b>!\nПроверь через /mycar",
        parse_mode="HTML"
    )


@dp.message(Command("mycar"))
async def cmd_mycar(message: Message):
    """Команда /mycar - моя машина"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    car = await get_car(chat_id, user_id)
    if car:
        await message.answer(f"🅿️ Твой гараж:\n🚗 <b>{car}</b>", parse_mode="HTML")
    else:
        await message.answer("🅿️ Гараж пуст. Купи тачку в /cars!")


@dp.message(Command("inv"))
async def cmd_inv(message: Message):
    """Команда /inv - инвентарь"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    async with pool.acquire() as conn:
        items = await conn.fetch(
            "SELECT item_name, rarity FROM inventory WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )
    if not items:
        return await message.answer("🎒 Инвентарь пуст.")
    text = "🎒 <b>Инвентарь:</b>\n\n"
    for item in items:
        if item['rarity'] == 'legendary':
            emoji = ""
        elif item['rarity'] == 'rare':
            emoji = "🔵"
        else:
            emoji = "🟢"
        text += f"{emoji} {item['item_name']}\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("rating"))
async def cmd_rating(message: Message):
    """Команда /rating - рейтинг богачей"""
    chat_id = message.chat.id
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT u.user_id, u.balance, us.username FROM users u LEFT JOIN usernames us ON u.chat_id = us.chat_id AND u.user_id = us.user_id WHERE u.chat_id = $1 ORDER BY u.balance DESC LIMIT 10",
            chat_id
        )
    if not rows:
        return await message.answer("🏆 Рейтинг пуст.")
    text = "🏆 <b>Рейтинг богачей:</b>\n\n"
    for i, row in enumerate(rows, 1):
        display_name = row['username'] if row['username'] else f"User{row['user_id']}"
        text += f"{i}. <b>{display_name}</b> — {fmt_money(row['balance'])}\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("give"))
async def cmd_give(message: Message):
    """Команда /give - выдача денег (только для админов)"""
    chat_id = message.chat.id
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.split()
    if len(args) < 2 or not message.reply_to_message:
        return await message.answer(" Использование: <b>/give сумма</b> (ответ)", parse_mode="HTML")
    try:
        amount = int(args[1])
    except:
        return await message.answer("❌ Число!")
    await update_balance(chat_id, message.reply_to_message.from_user.id, amount)
    await message.answer(f"✅ Выдано {fmt_money(amount)}.")


# ============================================================================
# БАНК
# ============================================================================

@dp.message(Command("bank"))
async def cmd_bank(message: Message):
    """Команда /bank - информация о банковском счёте"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    bank_data = await get_bank(chat_id, user_id)
    interest, _ = await calc_interest(bank_data['deposit'], bank_data['last_interest_time'])
    text = " <b>Твой банковский счёт</b>\n\n"
    text += f"💰 На счету: <b>{fmt_money(bank_data['deposit'])}</b>\n"
    text += f"📈 Накоплено процентов: <b>+{fmt_money(interest)}</b>\n"
    text += f"💹 Ставка: <b>1% в сутки</b>\n\n"
    text += f"<b>Команды:</b>\n"
    text += f"📥 <code>/deposit сумма</code> — положить\n"
    text += f"📤 <code>/withdraw сумма</code> — снять\n\n"
    text += f"⚠️ Деньги в банке <b>нельзя украсть</b> через /rob!"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("deposit"))
async def cmd_deposit(message: Message):
    """Команда /deposit - положить деньги в банк"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("📥 Использование: <b>/deposit сумма</b>", parse_mode="HTML")
    try:
        amount = int(args[1])
    except:
        return await message.answer("❌ Сумма должна быть числом!")
    if amount <= 0:
        return await message.answer("❌ Сумма должна быть положительной!")
    if amount < 100:
        return await message.answer("❌ Минимум 100 сарапулок")
    user = await get_user(chat_id, user_id)
    if user['balance'] < amount:
        return await message.answer(f"❌ Недостаточно ({fmt_money(user['balance'])})")
    await update_balance(chat_id, user_id, -amount)
    await update_bank(chat_id, user_id, amount)
    bank_data = await get_bank(chat_id, user_id)
    await message.answer(
        f"📥 <b>Вклад оформлен!</b>\n\nПоложено: <b>{fmt_money(amount)}</b>\nНа счету: <b>{fmt_money(bank_data['deposit'])}</b>\n💹 Процент: 1% в сутки",
        parse_mode="HTML"
    )


@dp.message(Command("withdraw"))
async def cmd_withdraw(message: Message):
    """Команда /withdraw - снять деньги из банка"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("📤 Использование: <b>/withdraw сумма</b>", parse_mode="HTML")
    try:
        amount = int(args[1])
    except:
        return await message.answer("❌ Сумма должна быть числом!")
    if amount <= 0:
        return await message.answer("❌ Сумма должна быть положительной!")
    bank_data = await get_bank(chat_id, user_id)
    interest, new_time = await calc_interest(bank_data['deposit'], bank_data['last_interest_time'])
    if bank_data['deposit'] < amount:
        return await message.answer(f"❌ На счету только <b>{fmt_money(bank_data['deposit'])}</b>", parse_mode="HTML")
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE bank SET deposit = deposit - $1, last_interest_time = $2 WHERE chat_id = $3 AND user_id = $4",
            amount, new_time, chat_id, user_id
        )
    if interest > 0 and bank_data['deposit'] - amount > 0:
        await update_bank(chat_id, user_id, interest)
        await update_balance(chat_id, user_id, interest)
    await update_balance(chat_id, user_id, amount)
    new_bank = await get_bank(chat_id, user_id)
    text = f" <b>Снятие выполнено!</b>\n\nПолучено: <b>{fmt_money(amount)}</b>\n"
    if interest > 0:
        text += f"📈 Начислено процентов: <b>+{fmt_money(interest)}</b>\n"
    text += f"Остаток на счету: <b>{fmt_money(new_bank['deposit'])}</b>"
    await message.answer(text, parse_mode="HTML")


# ============================================================================
# КРАФТ
# ============================================================================

@dp.message(Command("craft"))
async def cmd_craft(message: Message):
    """Команда /craft - список рецептов крафта"""
    text = " <b>Крафт:</b>\n\nОбъединяй предметы для создания более ценных!\n\n"
    for key, recipe in CRAFT_RECIPES.items():
        requires_text = ", ".join([f"{count}× {name}" for name, count in recipe["requires"].items()])
        text += f"🔹 <b>{recipe['name']}</b>\n"
        text += f"   Нужно: {requires_text}\n"
        text += f"   Редкость: {recipe['rarity']}\n"
        text += f"   Команда: <code>/craft_item {key}</code>\n\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("craft_item"))
async def cmd_craft_item(message: Message):
    """Команда /craft_item - крафт предмета"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("🔨 Укажи что крафтить: <b>/craft_item diamond</b>", parse_mode="HTML")
    item_key = args[1]
    if item_key not in CRAFT_RECIPES:
        return await message.answer("❌ Неизвестный рецепт! Посмотри /craft")
    recipe = CRAFT_RECIPES[item_key]
    async with pool.acquire() as conn:
        items = await conn.fetch(
            "SELECT item_name FROM inventory WHERE chat_id = $1 AND user_id = $2",
            chat_id, user_id
        )
    inventory = {}
    for item in items:
        name = item['item_name']
        inventory[name] = inventory.get(name, 0) + 1
    for required_name, required_count in recipe["requires"].items():
        if inventory.get(required_name, 0) < required_count:
            return await message.answer(
                f"❌ Не хватает ресурсов!\n\nНужно: <b>{required_count}× {required_name}</b>\nЕсть: <b>{inventory.get(required_name, 0)}× {required_name}</b>",
                parse_mode="HTML"
            )
    async with pool.acquire() as conn:
        for required_name, required_count in recipe["requires"].items():
            await conn.execute(
                "DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE chat_id = $1 AND user_id = $2 AND item_name = $3 LIMIT $4)",
                chat_id, user_id, required_name, required_count
            )
        await conn.execute(
            "INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1, $2, $3, 'crafted', $4)",
            chat_id, user_id, recipe["name"], recipe["rarity"]
        )
    await message.answer(
        f"✅ <b>Скрафчено!</b>\n\nПолучено: {recipe['name']}\nРедкость: <b>{recipe['rarity']}</b>",
        parse_mode="HTML"
    )


# ============================================================================
# ТРЕЙД
# ============================================================================

@dp.message(Command("trade"))
async def cmd_trade(message: Message):
    """Команда /trade - обмен предметами между игроками"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 4 or not message.reply_to_message:
        return await message.answer("🔄 Использование: <b>/trade @user предмет кол-во</b> (ответь на сообщение)", parse_mode="HTML")
    target_id = message.reply_to_message.from_user.id
    item_name = args[2]
    try:
        count = int(args[3])
    except:
        return await message.answer("❌ Количество должно быть числом!")
    if count <= 0:
        return await message.answer("❌ Количество должно быть > 0")
    if target_id == user_id:
        return await message.answer("❌ Нельзя торговать с собой!")
    async with pool.acquire() as conn:
        have = await conn.fetchval(
            "SELECT COUNT(*) FROM inventory WHERE chat_id = $1 AND user_id = $2 AND item_name = $3",
            chat_id, user_id, item_name
        )
    if have < count:
        return await message.answer(f"❌ У вас нет <b>{count}× {item_name}</b>\nЕсть: <b>{have}× {item_name}</b>", parse_mode="HTML")
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT item_name, item_type, rarity FROM inventory WHERE chat_id = $1 AND user_id = $2 AND item_name = $3 LIMIT $4",
            chat_id, user_id, item_name, count
        )
        await conn.execute(
            "DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE chat_id = $1 AND user_id = $2 AND item_name = $3 LIMIT $4)",
            chat_id, user_id, item_name, count
        )
        for row in rows:
            await conn.execute(
                "INSERT INTO inventory (chat_id, user_id, item_name, item_type, rarity) VALUES ($1, $2, $3, $4, $5)",
                chat_id, target_id, row['item_name'], row['item_type'], row['rarity']
            )
    target_name = message.reply_to_message.from_user.full_name
    await message.answer(f"✅ Передано <b>{count}× {item_name}</b> пользователю <b>{target_name}</b>", parse_mode="HTML")


# ============================================================================
# ОБРАЗОВАНИЕ
# ============================================================================

@dp.message(Command("education"))
async def cmd_education(message: Message):
    """Команда /education - список курсов"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    edu = await get_education(chat_id, user_id)
    text = "🎓 <b>Образование и квалификация</b>\n\nПолучи диплом → открой профессию!\n\n"
    for key, course in COURSES.items():
        completed = key in edu['completed_courses'] or (key == 'mba' and edu['has_mba'])
        status = "✅" if completed else "🔒"
        text += f"{status} <b>{course['name']}</b>\n"
        text += f"   💰 Цена: {fmt_money(course['price'])}\n"
        if course['required_for']:
            text += f"   🎯 Открывает: {JOBS[course['required_for']]['name']}\n"
        else:
            text += f"    Бонус: +50% ко всем зарплатам\n"
        text += f"   → /buy_course {key}\n\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("buy_course"))
async def cmd_buy_course(message: Message):
    """Команда /buy_course - покупка курса и начало экзамена"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2 or args[1] not in COURSES:
        return await message.answer("🎓 Используйте: /education")
    course_key = args[1]
    course = COURSES[course_key]
    edu = await get_education(chat_id, user_id)
    if course_key in edu['completed_courses'] or (course_key == 'mba' and edu['has_mba']):
        return await message.answer("✅ Вы уже прошли этот курс!")
    user = await get_user(chat_id, user_id)
    if user['balance'] < course['price']:
        return await message.answer(f"❌ Нужно {fmt_money(course['price'])}")
    await update_balance(chat_id, user_id, -course['price'])
    exam_sessions[f"{chat_id}_{user_id}"] = {"course": course_key, "question": 0, "correct": 0}
    q = course['questions'][0]
    await message.answer(
        f"✅ Курс оплачен!\n\n📝 <b>Экзамен:</b> ответьте на 3 вопроса.\nНужно правильно ответить на 2 из 3.\n\nВопрос 1 из 3:\n<b>{q['q']}</b>\n\n{' | '.join([f'{i+1}. {a}' for i, a in enumerate(q['a'])])}\n\nНапишите номер ответа (1, 2 или 3)",
        parse_mode="HTML"
    )


@dp.message(F.text & ~F.text.startswith('/'))
async def handle_exam_answer(message: Message):

    # ВАЖНО: пропускаем команды (начинаются с /)
    if not message.text or message.text.startswith('/'):
        return
    # Пропускаем не группы
    if message.chat.type not in ['group', 'supergroup']:
        return
    
    chat_id = message.chat.id
    user_id = message.from_user.id
    exam_key = f"{chat_id}_{user_id}"
    
    # Если нет активного экзамена — выходим
    if exam_key not in exam_sessions:
        return
    
    exam = exam_sessions[exam_key]
    course = COURSES[exam['course']]
    
    try:
        answer = int(message.text) - 1
    except:
        return await message.answer("❌ Введите номер ответа (1, 2 или 3)")
    
    if answer < 0 or answer > 2:
        return await message.answer(" Введите номер ответа (1, 2 или 3)")
    
    question = course['questions'][exam['question']]
    if answer == question['correct']:
        exam['correct'] += 1
        await message.answer("✅ Правильно!")
    else:
        await message.answer(f"❌ Неправильно! Правильный ответ: {question['a'][question['correct']]}")
    
    exam['question'] += 1
    
    if exam['question'] < 3:
        q = course['questions'][exam['question']]
        await message.answer(
            f"Вопрос {exam['question'] + 1} из 3:\n<b>{q['q']}</b>\n\n"
            f"{' | '.join([f'{i+1}. {a}' for i, a in enumerate(q['a'])])}\n\n"
            f"Напишите номер ответа (1, 2 или 3)",
            parse_mode="HTML"
        )
    else:
        if exam['correct'] >= 2:
            await complete_course(chat_id, user_id, exam['course'])
            await message.answer(
                f"🎉 <b>Поздравляем!</b>\n\n"
                f"Вы сдали экзамен на {exam['correct']}/3!\n"
                f"Курс <b>{course['name']}</b> завершён!",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"😔 <b>Экзамен провален.</b>\n\n"
                f"Вы ответили правильно на {exam['correct']}/3.\n"
                f"Нужно минимум 2 правильных ответа.\n\n"
                f"Попробуйте ещё раз: /buy_course {exam['course']}",
                parse_mode="HTML"
            )
        del exam_sessions[exam_key]


# ============================================================================
# БЛЭКДЖЕК С ИГОРЁЧКОМ
# ============================================================================

def create_deck():
    """Создание и перемешивание колоды карт"""
    suits = ['♠', '♥', '♦', '♣']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    deck = [(r, s) for s in suits for r in ranks]
    random.shuffle(deck)
    return deck


def card_value(card):
    """Подсчет стоимости карты"""
    r = card[0]
    if r in ['J', 'Q', 'K']:
        return 10
    if r == 'A':
        return 11
    return int(r)


def calc_score(cards):
    """Подсчет очков руки с учетом тузов"""
    score = sum(card_value(c) for c in cards)
    aces = sum(1 for c in cards if c[0] == 'A')
    while score > 21 and aces > 0:
        score -= 10
        aces -= 1
    return score


def show_cards(cards, hide_first=False):
    """Отображение карт"""
    if hide_first:
        return f"🂠 + {' '.join(f'{r}{s}' for r,s in cards[1:])}"
    return ' '.join(f'{r}{s}' for r,s in cards)


@dp.message(Command("blackjack"))
async def blackjack_start(message: Message, state: FSMContext):
    """Команда /blackjack - начало игры"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    if chat_id in bj_tables:
        return await message.answer(" Игра уже идёт! Дождитесь окончания.")
    user = await get_user(chat_id, user_id)
    if user['balance'] < 100:
        return await message.answer(f"❌ Нужно минимум 100 сарапулек! У тебя: {fmt_money(user['balance'])}")
    
    bj_tables[chat_id] = {
        "players": {
            user_id: {
                "name": message.from_user.first_name,
                "bet": 0,
                "cards": [],
                "stand": False,
                "busted": False
            }
        },
        "order": [user_id],
        "stage": "waiting"
    }
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"bj_join_{chat_id}")]
    ])
    await message.answer(
        f"🎩 <b>Игорёчек открывает стол!</b>\n\n"
        f"👤 Создатель: {message.from_user.first_name}\n"
        f" Игроков: 1/5\n"
        f"⏳ Сбор игроков — 60 секунд\n\n"
        f"Нажмите кнопку, чтобы сесть за стол!",
        reply_markup=kb,
        parse_mode="HTML"
    )
    
    await state.set_state(BlackjackStates.waiting)
    await asyncio.sleep(60)
    
    if chat_id not in bj_tables:
        return
    table = bj_tables[chat_id]
    if len(table["players"]) < 2:
        await message.answer("😔 Недостаточно игроков (нужно минимум 2). Стол закрыт.")
        del bj_tables[chat_id]
        await state.clear()
        return
    
    table["stage"] = "betting"
    players_list = ", ".join(p["name"] for p in table["players"].values())
    await message.answer(
        f"🎩 <b>Игорёчек:</b> Отлично! Игроки: {players_list}\n\n"
        f"💰 Каждый игрок, проверьте <b>личку</b> для ставки!",
        parse_mode="HTML"
    )
    
    for uid in table["order"]:
        bets_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="50", callback_data=f"bet_50_{chat_id}"),
                InlineKeyboardButton(text="100", callback_data=f"bet_100_{chat_id}"),
                InlineKeyboardButton(text="200", callback_data=f"bet_200_{chat_id}")
            ],
            [
                InlineKeyboardButton(text="500", callback_data=f"bet_500_{chat_id}"),
                InlineKeyboardButton(text="1000", callback_data=f"bet_1000_{chat_id}")
            ]
        ])
        try:
            await bot.send_message(
                uid,
                f"🎩 <b>Игорёчек:</b> Ваша ставка?",
                reply_markup=bets_kb,
                parse_mode="HTML"
            )
        except:
            await message.answer(f"️ {table['players'][uid]['name']}, напишите боту в личку!")


@dp.callback_query(lambda c: c.data.startswith("bj_join_"))
async def blackjack_join(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки присоединения к столу"""
    chat_id = int(callback.data.split("_")[2])
    uid = callback.from_user.id
    if chat_id not in bj_tables:
        return await callback.answer("Стол закрыт!", show_alert=True)
    table = bj_tables[chat_id]
    if table["stage"] != "waiting":
        return await callback.answer("Игра уже началась!", show_alert=True)
    if uid in table["players"]:
        return await callback.answer("Вы уже в игре!", show_alert=True)
    if len(table["players"]) >= 5:
        return await callback.answer("Мест нет (макс. 5)!", show_alert=True)
    user = await get_user(chat_id, uid)
    if user['balance'] < 100:
        return await callback.answer(f"Нужно 100 сарапулек! У вас: {fmt_money(user['balance'])}", show_alert=True)
    
    table["players"][uid] = {
        "name": callback.from_user.first_name,
        "bet": 0,
        "cards": [],
        "stand": False,
        "busted": False
    }
    table["order"].append(uid)
    await callback.answer(f"✅ Вы присоединились!")
    
    players_list = "\n".join([f"• {p['name']}" for p in table["players"].values()])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"bj_join_{chat_id}")]
    ])
    try:
        await callback.message.edit_text(
            f"🎩 <b>Игорёчек открывает стол!</b>\n\n"
            f"👥 Игроки ({len(table['players'])}/5):\n{players_list}\n\n"
            f"⏳ Ожидание...",
            reply_markup=kb,
            parse_mode="HTML"
        )
    except:
        pass


@dp.callback_query(lambda c: c.data.startswith("bet_"))
async def blackjack_bet(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки ставки"""
    parts = callback.data.split("_")
    bet = int(parts[1])
    chat_id = int(parts[2])
    uid = callback.from_user.id
    if chat_id not in bj_tables:
        return await callback.answer("Игра не найдена!", show_alert=True)
    table = bj_tables[chat_id]
    if uid not in table["players"]:
        return await callback.answer("Вы не в игре!", show_alert=True)
    if table["players"][uid]["bet"] > 0:
        return await callback.answer("Вы уже сделали ставку!", show_alert=True)
    user = await get_user(chat_id, uid)
    if user['balance'] < bet:
        return await callback.answer(f"Мало сарапулек! Баланс: {fmt_money(user['balance'])}", show_alert=True)
    
    await update_balance(chat_id, uid, -bet)
    table["players"][uid]["bet"] = bet
    try:
        await callback.message.edit_text(
            f"✅ Ваша ставка: <b>{bet}</b> сарапулек. Ждём остальных...",
            parse_mode="HTML"
        )
    except:
        pass
    await callback.answer(f"Ставка {bet} принята!")
    
    if all(p["bet"] > 0 for p in table["players"].values()):
        await blackjack_deal(chat_id, state)


async def blackjack_deal(chat_id, state):
    """Раздача карт"""
    table = bj_tables[chat_id]
    table["deck"] = create_deck()
    for uid in table["order"]:
        p = table["players"][uid]
        p["cards"] = [table["deck"].pop(), table["deck"].pop()]
    table["dealer"] = [table["deck"].pop(), table["deck"].pop()]
    table["stage"] = "playing"
    
    players_info = "\n".join([f"👤 {p['name']}: ставка {p['bet']}" for p in table["players"].values()])
    await bot.send_message(
        chat_id,
        f"🎩 <b>Игорёчек:</b> Карты розданы!\n\n"
        f"🤖 Мои карты: {show_cards(table['dealer'], hide_first=True)}\n\n"
        f"{players_info}\n\n"
        f"🎮 Ходит: <b>{table['players'][table['order'][0]]['name']}</b>",
        parse_mode="HTML"
    )
    
    await state.set_state(BlackjackStates.playing)
    await blackjack_player_turn(chat_id, table["order"][0], state)


async def blackjack_player_turn(chat_id, uid, state):
    """Ход игрока"""
    table = bj_tables[chat_id]
    p = table["players"][uid]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🃏 Ещё карту", callback_data=f"hit_{uid}_{chat_id}"),
            InlineKeyboardButton(text="✋ Хватит", callback_data=f"stand_{uid}_{chat_id}")
        ]
    ])
    await bot.send_message(
        uid,
        f"🎩 <b>Игорёчек:</b> Ваш ход!\n\n"
        f"🃏 Ваши карты: {show_cards(p['cards'])}\n"
        f"🔢 Сумма: <b>{calc_score(p['cards'])}</b>\n"
        f"💰 Ставка: {p['bet']}\n\n"
        f"🎴 Карта Игорёчка: {table['dealer'][0][0]}{table['dealer'][0][1]}",
        reply_markup=kb,
        parse_mode="HTML"
    )


@dp.callback_query(lambda c: c.data.startswith("hit_") or c.data.startswith("stand_"))
async def blackjack_hit_stand(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопок 'Ещё карту' и 'Хватит'"""
    parts = callback.data.split("_")
    action = parts[0]
    uid = int(parts[1])
    chat_id = int(parts[2])
    if chat_id not in bj_tables:
        return await callback.answer("Игра не найдена!", show_alert=True)
    table = bj_tables[chat_id]
    p = table["players"][uid]
    
    if action == "hit":
        card = table["deck"].pop()
        p["cards"].append(card)
        score = calc_score(p["cards"])
        await callback.message.edit_text(
            f"🎩 {callback.from_user.first_name} взял карту!\n\n"
            f"🃏 Вы взяли: {card[0]}{card[1]}\n"
            f"📊 Карты: {show_cards(p['cards'])}\n"
            f" Сумма: <b>{score}</b>",
            parse_mode="HTML"
        )
        
        if score > 21:
            p["stand"] = True
            p["busted"] = True
            await callback.message.answer(
                f"💥 <b>Перебор ({score})!</b> Вы проиграли ставку.",
                parse_mode="HTML"
            )
            await blackjack_next_turn(chat_id, state)
        elif score == 21:
            p["stand"] = True
            await callback.message.answer(f"🎉 <b>21!</b> Отлично!")
            await blackjack_next_turn(chat_id, state)
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🃏 Ещё карту", callback_data=f"hit_{uid}_{chat_id}"),
                    InlineKeyboardButton(text="✋ Хватит", callback_data=f"stand_{uid}_{chat_id}")
                ]
            ])
            await callback.message.answer(f"💰 Сумма: {score}. Ещё?", reply_markup=kb)
            
    elif action == "stand":
        p["stand"] = True
        await callback.message.edit_text(
            f"✋ Вы остановились на <b>{calc_score(p['cards'])}</b>",
            parse_mode="HTML"
        )
        await blackjack_next_turn(chat_id, state)


async def blackjack_next_turn(chat_id, state):
    """Переход к следующему игроку"""
    table = bj_tables[chat_id]
    next_uid = None
    for uid in table["order"]:
        if not table["players"][uid]["stand"]:
            next_uid = uid
            break
    if next_uid:
        p = table["players"][next_uid]
        await bot.send_message(chat_id, f"🎮 Ходит: <b>{p['name']}</b>", parse_mode="HTML")
        await blackjack_player_turn(chat_id, next_uid, state)
    else:
        await blackjack_dealer_play(chat_id, state)


async def blackjack_dealer_play(chat_id, state):
    """Ход Игорёчка (дилера)"""
    table = bj_tables[chat_id]
    await bot.send_message(
        chat_id,
        f"🎩 <b>Игорёчек:</b> Теперь мой ход!\n\n"
        f"🤖 Мои карты: {show_cards(table['dealer'])}",
        parse_mode="HTML"
    )
    
    while calc_score(table["dealer"]) < 17:
        await asyncio.sleep(1)
        card = table["deck"].pop()
        table["dealer"].append(card)
        await bot.send_message(
            chat_id,
            f"🎩 Игорёчек берёт: <b>{card[0]}{card[1]}</b> → сумма: <b>{calc_score(table['dealer'])}</b>",
            parse_mode="HTML"
        )
    
    dealer_score = calc_score(table["dealer"])
    results = []
    for uid in table["order"]:
        p = table["players"][uid]
        ps = calc_score(p["cards"])
        bet = p["bet"]
        if p["busted"]:
            results.append(f"❌ {p['name']}: перебор ({ps}) — проигрыш")
        elif dealer_score > 21:
            await update_balance(chat_id, uid, bet * 2)
            results.append(f"🎉 {p['name']}: Игорёчек перебрал! +{bet}")
        elif ps > dealer_score:
            await update_balance(chat_id, uid, bet * 2)
            results.append(f"🏆 {p['name']}: победа! +{bet}")
        elif ps == dealer_score:
            await update_balance(chat_id, uid, bet)
            results.append(f"🤝 {p['name']}: ничья")
        else:
            results.append(f"😢 {p['name']}: проигрыш")
    
    if dealer_score > 21:
        final = " Игорёчек перебрал!"
    elif any("победа" in r for r in results):
        final = "🎉 Игорёчек поздравляет победителей!"
    elif any("проигрыш" in r for r in results):
        final = "🎩 Игорёчек забирает ставки!"
    else:
        final = " Ничья!"
    
    await bot.send_message(
        chat_id,
        f" <b>Игорёчек:</b> {final}\n\n"
        f" Карты Игорёчка: {show_cards(table['dealer'])} ({dealer_score})\n\n"
        f"📊 Результаты:\n" + "\n".join(results),
        parse_mode="HTML"
    )
    del bj_tables[chat_id]
    await state.clear()


# ============================================================================
# АВТО-РЕГИСТРАЦИЯ И ПРИВЕТСТВИЕ
# ============================================================================

@dp.message()
async def auto_register(message: Message):
    """Автоматическая регистрация пользователей в группе"""
    if message.chat.type not in ['group', 'supergroup']:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id
    await get_user(chat_id, user_id)


@dp.message(F.new_chat_members)
async def on_user_join(message: Message):
    """Приветствие новых участников"""
    chat_id = message.chat.id
    for user in message.new_chat_members:
        if user.is_bot:
            if user.id == int(API_TOKEN.split(':')[0]):
                await message.answer("👋 Привет! Я экономический бот. Напиши /start чтобы начать!")
            continue
        await get_user(chat_id, user.id)
        await save_username(chat_id, user.id, user.full_name)


# ============================================================================
# ЗАПУСК БОТА
# ============================================================================

async def main():
    """Главная функция запуска бота"""
    await init_db()
    print("🤖 Бот запущен!")
    asyncio.create_task(start_web_server())
    asyncio.create_task(polling_health_check())
    asyncio.create_task(auto_lottery_loop())
    await dp.start_polling(bot, timeout=30, allowed_updates=["message", "callback_query", "my_chat_member"])


if __name__ == "__main__":
    asyncio.run(main())
