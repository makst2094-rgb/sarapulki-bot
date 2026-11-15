import asyncio
import logging
import random
import time
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not API_TOKEN:
    raise ValueError("BOT_TOKEN не установлен!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- ХРАНИЛИЩЕ В ПАМЯТИ ---
users_db = {}
profiles_db = {}
bank_db = {}
businesses_db = {}
garage_db = {}
inventory_db = {}
education_db = {}
loans_db = {}
jail_db = {}
jail_fines_db = {}
daily_bonus_db = {}
robbery_db = {}
lottery_tickets_db = []
usernames_db = {}
achievements_db = {}
debts_db = []
state_debts_db = {}
player_cities_db = {}
city_treasury_db = {}
mayors_db = {}
mayor_candidates_db = []
mayor_votes_db = []
city_decrees_db = []
state_treasury_db = {}
federal_roles_db = {}
federal_candidates_db = []
federal_votes_db = []
federal_elections_start_db = {}
mayor_elections_start_db = {}
federal_decrees_db = []
mayor_reports_db = []
impeachment_votes_db = []
mayor_projects_db = []
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
    "yacht_car": {"name": "🛥️ Яхта", "price": 5000000}
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

# --- УТИЛИТЫ ---
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

# --- ФУНКЦИИ ХРАНИЛИЩА ---
def get_user(cid, uid):
    key = f"{cid}_{uid}"
    if key not in users_db:
        users_db[key] = {"balance": 0}
    return users_db[key]

def update_balance(cid, uid, amt):
    key = f"{cid}_{uid}"
    if key not in users_db:
        users_db[key] = {"balance": 0}
    users_db[key]["balance"] += amt

def get_profile(cid, uid):
    key = f"{cid}_{uid}"
    if key not in profiles_db:
        profiles_db[key] = {"job_key": "novice", "level": 1, "last_work_time": 0, "coffee_level": 0}
    return profiles_db[key]

def get_bank(cid, uid):
    key = f"{cid}_{uid}"
    if key not in bank_db:
        bank_db[key] = {"deposit": 0, "last_interest_time": time.time()}
    return bank_db[key]

def update_bank(cid, uid, amt):
    key = f"{cid}_{uid}"
    if key not in bank_db:
        bank_db[key] = {"deposit": 0, "last_interest_time": time.time()}
    bank_db[key]["deposit"] += amt

def get_car(cid, uid):
    key = f"{cid}_{uid}"
    return garage_db.get(key, [])

def set_car(cid, uid, car_key, car_name):
    key = f"{cid}_{uid}"
    if key not in garage_db:
        garage_db[key] = []
    garage_db[key].append({"car_key": car_key, "car_name": car_name})

def get_education(cid, uid):
    key = f"{cid}_{uid}"
    if key not in education_db:
        education_db[key] = {"completed_courses": [], "has_mba": False}
    return education_db[key]

def complete_course(cid, uid, course_key):
    key = f"{cid}_{uid}"
    if key not in education_db:
        education_db[key] = {"completed_courses": [], "has_mba": False}
    if course_key == "mba":
        education_db[key]["has_mba"] = True
    else:
        education_db[key]["completed_courses"].append(course_key)

def get_loan(cid, uid):
    key = f"{cid}_{uid}"
    if key not in loans_db:
        loans_db[key] = {"amount": 0, "interest": 0, "taken_at": 0, "due_date": 0}
    return loans_db[key]

def update_loan(cid, uid, amount, interest, taken_at, due_date):
    key = f"{cid}_{uid}"
    loans_db[key] = {"amount": amount, "interest": interest, "taken_at": taken_at, "due_date": due_date}

def clear_loan(cid, uid):
    key = f"{cid}_{uid}"
    if key in loans_db:
        del loans_db[key]

def is_in_jail(cid, uid):
    key = f"{cid}_{uid}"
    if key not in jail_db:
        return False
    if time.time() >= jail_db[key]["release_time"]:
        del jail_db[key]
        return False
    return True

def get_jail_info(cid, uid):
    key = f"{cid}_{uid}"
    return jail_db.get(key)

def send_to_jail(cid, uid, hours):
    key = f"{cid}_{uid}"
    jail_db[key] = {"release_time": time.time() + (hours * 3600), "fine_per_hour": JAIL_FINE_PER_HOUR}

def release_from_jail(cid, uid):
    key = f"{cid}_{uid}"
    if key in jail_db:
        del jail_db[key]

def get_player_city(cid, uid):
    key = f"{cid}_{uid}"
    city_id = player_cities_db.get(key)
    if not city_id:
        return None
    for city in CITIES_LIST:
        if city["id"] == city_id:
            return city.copy()
    return None

def set_player_city(cid, uid, city_id):
    key = f"{cid}_{uid}"
    player_cities_db[key] = city_id

def get_state_treasury(cid):
    return state_treasury_db.get(cid, 0)

def update_state_treasury(cid, amount):
    if cid not in state_treasury_db:
        state_treasury_db[cid] = 0
    state_treasury_db[cid] += amount

def get_city_treasury(cid, city_id):
    key = f"{cid}_{city_id}"
    return city_treasury_db.get(key, 0)

def update_city_treasury(cid, city_id, amount):
    key = f"{cid}_{city_id}"
    if key not in city_treasury_db:
        city_treasury_db[key] = 0
    city_treasury_db[key] += amount

def get_mayor(cid, city_id):
    key = f"{cid}_{city_id}"
    mayor = mayors_db.get(key)
    if mayor and mayor["expires_at"] > time.time():
        return mayor
    return None

def get_federal_role(cid, role):
    key = f"{cid}_{role}"
    official = federal_roles_db.get(key)
    if official and official["expires_at"] > time.time():
        return official
    return None

def is_mayor(cid, uid, city_id):
    mayor = get_mayor(cid, city_id)
    return mayor and mayor["user_id"] == uid

def is_federal_official(cid, uid, role):
    official = get_federal_role(cid, role)
    return official and official["user_id"] == uid

def save_username(cid, uid, name):
    key = f"{cid}_{uid}"
    usernames_db[key] = name

# --- МЕНЮ ---
@dp.message(Command("start"))
async def cmd_start(m: Message):
    save_username(m.chat.id, m.from_user.id, m.from_user.full_name)
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
        u = get_user(cid, uid)
        bd = get_bank(cid, uid)
        text = f"💰 <b>ФИНАНСЫ</b>\n\n💵 Баланс: <b>{fmt_money(u['balance'])}</b>\n🏦 Банк: <b>{fmt_money(bd['deposit'])}</b>\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/balance\n/bank\n/deposit сумма\n/withdraw сумма\n/pay сумма\n/credit сумма\n/debt\n/repay сумма\n/repay_all\n/debt_give\n/debt_return\n/debt_list"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "work":
        p = get_profile(cid, uid)
        j = JOBS[p['job_key']]
        text = f"💼 <b>РАБОТА</b>\n\n🔹 {j['name']} (Ур.{p['level']})\n💰 {fmt_money(j['base_pay'] * p['level'])}/ч\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/work\n/jobs\n/job ключ\n/shop\n/buy course\n/buy coffee"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "business":
        bc = len([b for b in businesses_db.values() if b['chat_id'] == cid and b['user_id'] == uid])
        text = f"🏪 <b>БИЗНЕС</b>\n\n🏢 У вас: <b>{bc}</b> бизнес(ов)\n⚠️ Лимит одного типа: <b>{MAX_BUSINESSES_PER_TYPE}</b>\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/market\n/buy_market ключ\n/collect\n/my_businesses\n/inv\n/craft\n/craft_item ключ\n/trade @user предмет кол-во"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "cars":
        c = get_car(cid, uid)
        cars_text = ", ".join([car['car_name'] for car in c]) if c else 'нет'
        text = f"🚗 <b>АВТОСАЛОН</b>\n\n🅿️ {cars_text}\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/cars\n/buycar ключ\n/mycar"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "edu":
        edu = get_education(cid, uid)
        cc = len(edu['completed_courses']) + (1 if edu['has_mba'] else 0)
        text = f"🎓 <b>ОБРАЗОВАНИЕ</b>\n\n📚 Пройдено: <b>{cc}</b>\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/education\n/buy_course ключ\nКурсы: miner, coder, trader, lawyer, mba"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "games":
        text = f"🎮 <b>ИГРЫ</b>\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n🎲 /dice сумма\n🎟️ /buy_ticket\n🎁 /daily"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "politics":
        president = get_federal_role(cid, 'president')
        president_text = "👤 ВАКАНТНО"
        if president:
            days_left = int((president['expires_at'] - time.time()) / 86400)
            president_text = f"👤 ID:{president['user_id']} ({days_left} дн.)"
        prime = get_federal_role(cid, 'prime_minister')
        prime_text = "👤 ВАКАНТНО"
        if prime:
            days_left = int((prime['expires_at'] - time.time()) / 86400)
            prime_text = f"👤 ID:{prime['user_id']} ({days_left} дн.)"
        state_treasury = get_state_treasury(cid)
        mayors_text = ""
        for city in CITIES_LIST:
            mayor = get_mayor(cid, city['id'])
            city_treasury = get_city_treasury(cid, city['id'])
            if mayor:
                days_left = int((mayor['expires_at'] - time.time()) / 86400)
                mayors_text += f"{city['emoji']} {city['name']}: ID:{mayor['user_id']} ({days_left} дн.) | Казна: {city_treasury}\n"
            else:
                mayors_text += f"{city['emoji']} {city['name']}: ВАКАНТНО | Казна: {city_treasury}\n"
        text = f"🏛️ <b>ПОЛИТИКА</b>\n\n🇷🇺 Президент: {president_text}\n💼 Премьер: {prime_text}\n🏛️ Фед. казна: {fmt_money(state_treasury)}\n\n🏙️ <b>Мэры:</b>\n{mayors_text}\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Города:</b>\n/city list\n/city choose [город]\n/city move [город]\n/city info\n/city residents\n\n🏛️ <b>Мэр:</b>\n/mayor_nominate (30к)\n/mayor_vote (500)\n/mayor_decree\n/mayor_finalize\n/city_decrees\n/mayor_project\n/project_done\n/project_check [город] approve/reject\n/project_status\n\n🇷🇺 <b>Президент (90 дней):</b>\n/president_nominate (50к)\n/president_vote (1000)\n/president_decree\n/president_decrees\n/president_finalize\n\n💼 <b>Премьер (90 дней):</b>\n/prime_nominate (40к)\n/prime_vote (800)\n/prime_decree\n/prime_decrees\n/prime_finalize\n\n⚖️ <b>Импичмент:</b>\n/impeach president\n/impeach prime\n\n💰 <b>Бюджет:</b>\n/budget"
        await callback.message.edit_text(text, parse_mode="HTML")
    elif action == "info":
        u = get_user(cid, uid)
        p = get_profile(cid, uid)
        in_jail = is_in_jail(cid, uid)
        jail_text = "\n🔒 <b>В ТЮРЬМЕ!</b>" if in_jail else ""
        debt_text = f"\n⛔ ДОЛГ: {fmt_money(abs(u['balance']))}" if u['balance'] < 0 else ""
        text = f"📊 <b>КАРТОЧКА ИГРОКА</b>\n\n👤 {callback.from_user.full_name}\n💰 Баланс: {fmt_money(u['balance'])}\n💼 Профессия: {JOBS[p['job_key']]['name']} (Ур.{p['level']}){jail_text}{debt_text}\n\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Команды:</b>\n/info\n/rating\n/achievements\n/budget"
        await callback.message.edit_text(text, parse_mode="HTML")
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
    await m.answer("🏪 <b>МАГАЗИН БИЗНЕСА</b>\n\n━━━━━━━━━━━━━━━━━━━━\n📊 <b>Категории:</b>\n\n📦 <b>Кейсы</b> — случайные предметы\n🏢 <b>Малый бизнес</b> — от 500 до 15к\n🏭 <b>Средний бизнес</b> — от 30к до 150к\n🏗️ <b>Крупный бизнес</b> — от 500к до 15М\n👑 <b>Элитный бизнес</b> — от 50М до 1МЛРД\n\n━━━━━━━━━━━━━━━━━━━━\n⚠️ Лимит: <b>10 бизнесов</b> одного типа\n💡 Купи бизнес → /collect раз в 24ч → прибыль!", reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith("market_"))
async def callback_market(callback: CallbackQuery):
    action = callback.data.replace("market_", "")
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
                text += f"🔸 {v['name']}\n   💰 Цена: {fmt_money(v['price'])}\n   📈 Доход: {fmt_money(v['income'])}/сутки\n   ⏱️ Окупаемость: ~{roi} дн.\n   🛒 /buy_market {k}\n\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n💡 {desc}"
        await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

# --- COLLECT ---
@dp.message(Command("collect"))
async def cmd_collect(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if is_in_jail(cid, uid):
        return await m.answer("🔒 В тюрьме нельзя собирать прибыль!")
    now = time.time()
    tot = 0
    collected = []
    waiting = []
    user_businesses = [b for b in businesses_db.values() if b['chat_id'] == cid and b['user_id'] == uid]
    if not user_businesses:
        return await m.answer("❌ У вас нет бизнесов.\n🏪 Купите в /market", parse_mode="HTML")
    for b in user_businesses:
        time_since = now - b['last_collect_time']
        if time_since >= 86400:
            income = b['income']
            tot += income
            collected.append(f"✅ {b['business_name']}: +{fmt_money(income)}")
            b['last_collect_time'] = now
        else:
            remaining = 86400 - time_since
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            waiting.append(f"⏳ {b['business_name']} — через {hours}ч {minutes}мин")
    if tot > 0:
        tax_rate = 12
        tax_amount = int(tot * tax_rate / 100)
        net_profit = tot - tax_amount
        update_balance(cid, uid, net_profit)
        msg = f"💼 <b>ПРИБЫЛЬ СОБРАНА!</b>\n\n" + "\n".join(collected)
        msg += f"\n\n━━━━━━━━━━━━━━━━━━━━\n💰 Доход: <b>{fmt_money(tot)}</b>\n🏛️ Налог ({tax_rate}%): <b>-{fmt_money(tax_amount)}</b>\n\n✅ <b>На руки: +{fmt_money(net_profit)}</b>"
        if waiting:
            msg += f"\n\n⏳ <b>Не готовы (ждите 24ч):</b>\n" + "\n".join(waiting[:5])
        await m.answer(msg, parse_mode="HTML")
    else:
        msg = "⏳ <b>Рано собирать!</b>\n\n"
        if waiting:
            msg += "\n".join(waiting[:10])
        else:
            msg += "Все бизнесы на кулдауне."
        await m.answer(msg, parse_mode="HTML")

# --- БЮДЖЕТ ---
@dp.message(Command("budget"))
async def cmd_budget(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    federal_treasury = get_state_treasury(cid)
    federal_daily = FEDERAL_SALARY_PRESIDENT + FEDERAL_SALARY_PRIME + FEDERAL_INFRASTRUCTURE
    player_city = get_player_city(cid, uid)
    city_treasury = 0
    city_daily = 0
    city_name = "Нет города"
    if player_city:
        city_treasury = get_city_treasury(cid, player_city['id'])
        mayor = get_mayor(cid, player_city['id'])
        city_daily = CITY_UTILITIES
        if mayor: city_daily += CITY_SALARY_MAYOR
        city_name = f"{player_city['emoji']} {player_city['name']}"
    text = (f"💰 <b>БЮДЖЕТ</b>\n\n🏛️ <b>Федеральная казна:</b>\n   Баланс: {fmt_money(federal_treasury)}\n   Расходы/день: {fmt_money(federal_daily)}\n   Хватит на: {int(federal_treasury / federal_daily) if federal_daily > 0 else '∞'} дн.\n\n🏙️ <b>Городская казна ({city_name}):</b>\n   Баланс: {fmt_money(city_treasury)}\n   Расходы/день: {fmt_money(city_daily)}\n   Хватит на: {int(city_treasury / city_daily) if city_daily > 0 else '∞'} дн.\n\n━━━━━━━━━━━━━━━━━━━━\n📊 <b>Статьи расходов:</b>\n👤 Президент: {fmt_money(FEDERAL_SALARY_PRESIDENT)}/день\n💼 Премьер: {fmt_money(FEDERAL_SALARY_PRIME)}/день\n🏛️ Мэр: {fmt_money(CITY_SALARY_MAYOR)}/день\n🏗️ Инфраструктура: {fmt_money(FEDERAL_INFRASTRUCTURE)}/день\n🔧 Коммуналка: {fmt_money(CITY_UTILITIES)}/день\n🎁 Соц. помощь: {fmt_money(FEDERAL_SOCIAL_AID)}/чел/день")
    await m.answer(text, parse_mode="HTML")

# --- БАЛАНС ---
@dp.message(Command("balance"))
async def cmd_balance(m: Message):
    save_username(m.chat.id, m.from_user.id, m.from_user.full_name)
    u = get_user(m.chat.id, m.from_user.id)
    c = get_car(m.chat.id, m.from_user.id)
    bd = get_bank(m.chat.id, m.from_user.id)
    in_jail = is_in_jail(m.chat.id, m.from_user.id)
    jail_text = "\n🔒 <b>В ТЮРЬМЕ!</b>" if in_jail else ""
    debt_text = f"\n⛔ <b>ДОЛГ: {fmt_money(abs(u['balance']))}</b>" if u['balance'] < 0 else ""
    cars_text = ", ".join([car['car_name'] for car in c]) if c else 'нет'
    await m.answer(f"💰 <b>Баланс:</b> {fmt_money(u['balance'])}\n🏦 <b>Банк:</b> {fmt_money(bd['deposit'])}\n🚗 <b>Машины:</b> {cars_text}{jail_text}{debt_text}", parse_mode="HTML")

# --- РАБОТА ---
@dp.message(Command("work"))
async def cmd_work(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if is_in_jail(cid, uid):
        info = get_jail_info(cid, uid)
        return await m.answer(f"🔒 Вы в тюрьме! Осталось: {format_time(int(info['release_time'] - time.time()))}")
    user = get_user(cid, uid)
    loan = get_loan(cid, uid)
    if loan['amount'] > 0 and time.time() > loan['due_date']:
        total_debt = loan['amount'] + loan['interest']
        if user['balance'] < total_debt:
            await m.answer(f"🚔 <b>АРЕСТ ИМУЩЕСТВА!</b>\n\n💰 Долг: <b>{fmt_money(total_debt)}</b>\n⛔ Имущество конфисковано!", parse_mode="HTML")
            clear_loan(cid, uid)
            return
        else:
            update_balance(cid, uid, -total_debt)
            clear_loan(cid, uid)
            return await m.answer(f"✅ Кредит погашен автоматически. Списано: {fmt_money(total_debt)}", parse_mode="HTML")
    save_username(cid, uid, m.from_user.full_name)
    p = get_profile(cid, uid)
    jk = p['job_key']
    if jk != 'novice':
        edu = get_education(cid, uid)
        if jk not in edu['completed_courses']:
            p['job_key'] = 'novice'
            jk = 'novice'
    j = JOBS[jk]
    ct = time.time()
    work_bonus_multiplier = 1.0
    player_city = get_player_city(cid, uid)
    if player_city:
        city = next((c for c in CITIES_LIST if c['id'] == player_city['id']), None)
        if city and city.get('work_bonus'): work_bonus_multiplier += city['work_bonus']
    coffee_level = p.get('coffee_level', 0)
    coffee_bonus = 1.0 - (coffee_level * 0.1)
    cd = j['cooldown'] * coffee_bonus
    if ct - p['last_work_time'] < cd:
        rest_seconds = cd - (ct - p['last_work_time'])
        return await m.answer(f"⏳ Отдых {int(rest_seconds // 60)} мин. {int(rest_seconds % 60)} сек.")
    gross_sal = j['base_pay'] * p['level'] + random.randint(0, 5)
    gross_sal = int(gross_sal * work_bonus_multiplier)
    edu = get_education(cid, uid)
    if edu['has_mba']: gross_sal = int(gross_sal * 1.5)
    tax_rate = 10
    tax_paid = int(gross_sal * tax_rate / 100)
    net_sal = gross_sal - tax_paid
    debt_deduction = 0
    deduction_msg = ""
    if user['balance'] < 0:
        debt_deduction = int(net_sal * 0.5)
        debt_deduction = min(debt_deduction, abs(user['balance']))
        if debt_deduction > 0:
            net_sal -= debt_deduction
            deduction_msg = f"\n💸 Погашено долга: <b>{fmt_money(debt_deduction)}</b>"
    update_balance(cid, uid, net_sal)
    p['last_work_time'] = ct
    response = f"💼 <b>{j['name']}</b> (Ур.{p['level']}):\n💰 Начислено: <b>{fmt_money(gross_sal)}</b>\n🏛️ Налог ({tax_rate}%): <b>-{fmt_money(tax_paid)}</b>\n✅ <b>На руки: +{fmt_money(net_sal)}</b>"
    if deduction_msg: response += deduction_msg
    await m.answer(response, parse_mode="HTML")

# --- ВАКАНСИИ ---
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
        edu = get_education(cid, uid)
        if args[1] not in edu['completed_courses']: return await m.answer(f"❌ Нужен курс: /buy_course {args[1]}")
    p = get_profile(cid, uid)
    p['job_key'] = args[1]
    await m.answer(f"✅ Теперь: <b>{JOBS[args[1]]['name']}</b>", parse_mode="HTML")

# --- ПЕРЕВОД ---
@dp.message(Command("pay"))
async def cmd_pay(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя переводить!")
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message: return await m.answer("/pay сумма (ответ)")
    try: amt = int(args[1])
    except: return await m.answer("❌ Число!")
    if amt <= 0: return await m.answer("❌ >0!")
    s, r = uid, m.reply_to_message.from_user.id
    if s == r: return await m.answer("❌ Себе нельзя!")
    sb = get_user(cid, s)
    if sb['balance'] < amt: return await m.answer(f"❌ Мало ({fmt_money(sb['balance'])})")
    update_balance(cid, s, -amt)
    update_balance(cid, r, amt)
    save_username(cid, r, m.reply_to_message.from_user.full_name)
    await m.answer(f"✅ Перевод <b>{fmt_money(amt)}</b>", parse_mode="HTML")

# --- ОГРАБЛЕНИЕ ---
@dp.message(Command("rob"))
async def cmd_rob(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if is_in_jail(cid, uid):
        info = get_jail_info(cid, uid)
        return await m.answer(f"🔒 Вы в тюрьме! Осталось: {format_time(int(info['release_time'] - time.time()))}")
    user = get_user(cid, uid)
    if user['balance'] < 0: return await m.answer(f"⛔ У вас долг!")
    if not m.reply_to_message: return await m.answer("🔫 Ответьте на жертву!")
    rid, vid = uid, m.reply_to_message.from_user.id
    if rid == vid: return await m.answer("❌ Себя нельзя!")
    if is_in_jail(cid, vid): return await m.answer("❌ Жертва в тюрьме!")
    key = f"{cid}_{rid}"
    ct = time.time()
    last_rob = robbery_db.get(key, 0)
    if ct - last_rob < ROB_COOLDOWN: return await m.answer(f"⏳ Кулдаун {format_time(ROB_COOLDOWN - (ct - last_rob))}")
    robbery_db[key] = ct
    vb = get_user(cid, vid)
    if vb['balance'] < 50: return await m.answer("❌ У жертвы мало денег!")
    rob_success_rate = ROB_SUCCESS_RATE
    player_city = get_player_city(cid, uid)
    if player_city:
        city = next((c for c in CITIES_LIST if c['id'] == player_city['id']), None)
        if city and city.get('rob_bonus'): rob_success_rate += city['rob_bonus']
    if random.random() < rob_success_rate:
        st = int(vb['balance'] * random.uniform(ROB_MIN_PERCENT, ROB_MAX_PERCENT))
        update_balance(cid, vid, -st)
        update_balance(cid, rid, st)
        await m.answer(f"🔫 <b>ОГРАБЛЕНИЕ УСПЕШНО!</b>\n\n{m.from_user.full_name} украл <b>{fmt_money(st)}</b>\nу {m.reply_to_message.from_user.full_name}!", parse_mode="HTML")
    else:
        rb = get_user(cid, rid)
        bank_data = get_bank(cid, rid)
        total_wealth = rb['balance'] + bank_data['deposit']
        fine_amount = int(total_wealth * JAIL_FINE_RATE)
        jail_fines_db[f"{cid}_{rid}"] = {"fine_amount": fine_amount, "debt_time": ct, "paid": False}
        send_to_jail(cid, rid, JAIL_TIME_HOURS)
        await m.answer(f"🚔 <b>ПОПАЛСЯ!</b>\n\n🔒 Тюрьма: <b>{JAIL_TIME_HOURS} часа</b>\n\n⚠️ После выхода штраф <b>25%</b> от капитала:\n💰 Ожидаемый штраф: <b>{fmt_money(fine_amount)}</b>", parse_mode="HTML")

# --- ТЮРЬМА ---
@dp.message(Command("jail"))
async def cmd_jail(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    info = get_jail_info(cid, uid)
    if not info or time.time() >= info['release_time']:
        if info: release_from_jail(cid, uid)
        return await m.answer("✅ Вы не в тюрьме!")
    remaining = int(info['release_time'] - time.time())
    remaining_hours = int(remaining / 3600) + 1
    total_fine = remaining_hours * info['fine_per_hour']
    jail_fine = jail_fines_db.get(f"{cid}_{uid}")
    fine_text = ""
    if jail_fine: fine_text = f"\n⚠️ Штраф после выхода: <b>{fmt_money(jail_fine['fine_amount'])}</b>"
    await m.answer(f"🔒 <b>Вы в тюрьме!</b>\n\n⏰ Осталось: <b>{format_time(remaining)}</b>\n💰 Штраф/час: {fmt_money(info['fine_per_hour'])}\n💸 Досрочный выход: <b>{fmt_money(total_fine)}</b>{fine_text}\n\n/jail_pay", parse_mode="HTML")

@dp.message(Command("jail_pay"))
async def cmd_jail_pay(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    info = get_jail_info(cid, uid)
    if not info or time.time() >= info['release_time']:
        if info: release_from_jail(cid, uid)
        return await m.answer("✅ Вы не в тюрьме!")
    remaining_seconds = info['release_time'] - time.time()
    remaining_hours = int(remaining_seconds / 3600) + 1
    total_fine = remaining_hours * info['fine_per_hour']
    user_bal = get_user(cid, uid)['balance']
    bank_dep = get_bank(cid, uid)['deposit']
    total_available = user_bal + bank_dep
    jail_fine = jail_fines_db.get(f"{cid}_{uid}")
    jail_fine_amount = jail_fine['fine_amount'] if jail_fine else 0
    total_needed = total_fine + jail_fine_amount
    if total_available < total_needed:
        return await m.answer(f"❌ Недостаточно средств!\nНужно: {fmt_money(total_needed)}\nНа руках: {fmt_money(max(0, user_bal))}\nВ банке: {fmt_money(bank_dep)}", parse_mode="HTML")
    pay_from_main = min(total_fine, max(0, user_bal))
    remaining_to_pay = total_fine - pay_from_main
    if pay_from_main > 0: update_balance(cid, uid, -pay_from_main)
    if remaining_to_pay > 0: update_bank(cid, uid, -remaining_to_pay)
    if jail_fine:
        jail_fines_db[f"{cid}_{uid}"]["paid"] = True
    release_from_jail(cid, uid)
    await m.answer(f"✅ Досрочный выход!\n\n💰 Оплачено: {fmt_money(total_fine + jail_fine_amount)}", parse_mode="HTML")

# --- ЕЖЕДНЕВНЫЙ БОНУС ---
@dp.message(Command("daily"))
async def cmd_daily(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    user = get_user(cid, uid)
    if user['balance'] < 0: return await m.answer(f"⛔ У вас долг!")
    save_username(cid, uid, m.from_user.full_name)
    ct = time.time()
    key = f"{cid}_{uid}"
    if key not in daily_bonus_db:
        daily_bonus_db[key] = {"last_claim": 0, "streak": 0}
    db = daily_bonus_db[key]
    lc, sk = db['last_claim'], db['streak']
    if ct - lc < 86400: return await m.answer(f"⏰ Через {format_time(86400 - (ct - lc))}")
    sk = sk + 1 if ct - lc < 172800 else 1
    bn = random.randint(100, 300) * min(sk, 7)
    update_balance(cid, uid, bn)
    db['last_claim'] = ct
    db['streak'] = sk
    await m.answer(f"🎁 Бонус за {sk} дн.: <b>{fmt_money(bn)}</b>", parse_mode="HTML")

# --- МАГАЗИН ---
@dp.message(Command("buy_market"))
async def cmd_buy_market(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2 or args[1] not in MARKET:
        return await m.answer("🛒 <b>МАГАЗИН</b>\n\n/buy_market [название]\n\n" + "\n".join([f"• {k} — {fmt_money(v['price'])}" for k, v in MARKET.items()]))
    item_type = args[1]
    it = MARKET[item_type]
    if it['type'] == 'business':
        user_biz_count = len([b for b in businesses_db.values() if b['chat_id'] == cid and b['user_id'] == uid and b['business_name'] == it['name']])
        if user_biz_count >= MAX_BUSINESSES_PER_TYPE:
            return await m.answer(f"❌ <b>ЛИМИТ ДОСТИГНУТ!</b>\n\nВы можете владеть максимум <b>{MAX_BUSINESSES_PER_TYPE}</b> бизнесами типа \"{it['name']}\".", parse_mode="HTML")
    price = it['price']
    price_multiplier = 1.0
    player_city = get_player_city(cid, uid)
    if player_city:
        city = next((c for c in CITIES_LIST if c['id'] == player_city['id']), None)
        if city and city.get('market_discount'): price_multiplier -= city['market_discount']
    final_price = int(price * price_multiplier)
    if is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    u = get_user(cid, uid)
    if u['balance'] < final_price: return await m.answer(f"❌ Нужно {fmt_money(final_price)}!")
    update_balance(cid, uid, -final_price)
    if it['type'] == 'case':
        r = random.randint(1, 100)
        if r <= 5: pr, rar = "🎸 Золотая Скрипка", "legendary"
        elif r <= 25: pr, rar = "💎 Алмаз", "rare"
        else: pr, rar = "📄 Бумага", "common"
        key = f"{cid}_{uid}"
        if key not in inventory_db:
            inventory_db[key] = []
        inventory_db[key].append({"item_name": pr, "item_type": 'card', "rarity": rar})
        await m.answer(f"✅ <b>Выпало: {pr}</b> ({rar})", parse_mode="HTML")
    elif it['type'] == 'business':
        biz_id = len(businesses_db) + 1
        businesses_db[biz_id] = {"chat_id": cid, "user_id": uid, "business_name": it['name'], "income": it['income'], "last_collect_time": time.time()}
        count = len([b for b in businesses_db.values() if b['chat_id'] == cid and b['user_id'] == uid and b['business_name'] == it['name']])
        await m.answer(f"✅ <b>Куплен бизнес: {it['name']}</b>\n💰 {fmt_money(it['income'])}/сбор\n📊 У вас таких: <b>{count}/{MAX_BUSINESSES_PER_TYPE}</b>", parse_mode="HTML")
    else:
        key = f"{cid}_{uid}"
        if key not in inventory_db:
            inventory_db[key] = []
        inventory_db[key].append({"item_name": it['name'], "item_type": item_type, "rarity": 'common'})
        await m.answer(f"✅ <b>Куплено: {it['name']}</b>", parse_mode="HTML")

@dp.message(Command("my_businesses"))
async def cmd_my_businesses(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    user_biz = [b for b in businesses_db.values() if b['chat_id'] == cid and b['user_id'] == uid]
    if not user_biz: return await m.answer("🏪 <b>У вас нет бизнесов</b>\n\nКупите в /market", parse_mode="HTML")
    biz_counts = {}
    for b in user_biz:
        name = b['business_name']
        biz_counts[name] = biz_counts.get(name, 0) + 1
    t = "🏪 <b>ВАШИ БИЗНЕСЫ</b>\n\n"
    total = 0
    for name, count in biz_counts.items():
        t += f"• {name}: <b>{count}</b> шт.\n"
        total += count
    t += f"\n📊 <b>Всего: {total} бизнес(ов)</b>"
    t += f"\n⚠️ Лимит одного типа: <b>{MAX_BUSINESSES_PER_TYPE}</b>"
    await m.answer(t, parse_mode="HTML")

# --- МАШИНЫ ---
@dp.message(Command("cars"))
async def cmd_cars(m: Message):
    t = "🚗 <b>Автосалон:</b>\n\n"
    for k, v in CARS.items():
        t += f"🔸 {v['name']} — {fmt_money(v['price'])} → /buycar {k}\n"
    await m.answer(t, parse_mode="HTML")

@dp.message(Command("buycar"))
async def cmd_buycar(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2 or args[1] not in CARS: return await m.answer("/cars")
    c = CARS[args[1]]
    u = get_user(cid, uid)
    if u['balance'] < c['price']: return await m.answer(f"❌ Нужно {fmt_money(c['price'])}")
    update_balance(cid, uid, -c['price'])
    set_car(cid, uid, args[1], c['name'])
    await m.answer(f"🎉 Куплена <b>{c['name']}</b>!", parse_mode="HTML")

@dp.message(Command("mycar"))
async def cmd_mycar(m: Message):
    c = get_car(m.chat.id, m.from_user.id)
    cars_text = ", ".join([car['car_name'] for car in c]) if c else None
    await m.answer(f"🅿️ <b>Твои машины:</b>\n{cars_text}" if cars_text else "🅿️ Пусто. /cars", parse_mode="HTML")

# --- ИНВЕНТАРЬ ---
@dp.message(Command("inv"))
async def cmd_inv(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    key = f"{cid}_{uid}"
    items = inventory_db.get(key, [])
    if not items: return await m.answer("🎒 Пусто.")
    t = "🎒 <b>Инвентарь:</b>\n\n"
    for i in items:
        em = "🟡" if i['rarity'] == "legendary" else "🔵" if i['rarity'] == "rare" else "🟢"
        t += f"{em} {i['item_name']}\n"
    await m.answer(t, parse_mode="HTML")

# --- РЕЙТИНГ ---
@dp.message(Command("rating"))
async def cmd_rating(m: Message):
    cid = m.chat.id
    sorted_users = sorted([(k, v['balance']) for k, v in users_db.items() if k.startswith(f"{cid}_")], key=lambda x: x[1], reverse=True)[:10]
    t = "🏆 <b>Рейтинг богачей:</b>\n\n"
    for i, (key, balance) in enumerate(sorted_users, 1):
        uid = int(key.split("_")[1])
        uname = usernames_db.get(key, f"User{uid}")
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        t += f"{medal} <b>{uname}</b> — {fmt_money(balance)}\n"
    await m.answer(t, parse_mode="HTML")

# --- АДМИН ---
@dp.message(Command("give"))
async def cmd_give(m: Message):
    cid = m.chat.id
    if m.from_user.id not in ADMIN_IDS: return
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message: return await m.answer("/give сумма (ответ)")
    try: amt = int(args[1])
    except: return await m.answer("❌ Число!")
    update_balance(cid, m.reply_to_message.from_user.id, amt)
    await m.answer(f"✅ Выдано {fmt_money(amt)}.")

# --- БАНК ---
@dp.message(Command("bank"))
async def cmd_bank(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    bd = get_bank(cid, uid)
    interest = int(bd['deposit'] * BANK_INTEREST_RATE * ((time.time() - bd['last_interest_time']) / 86400))
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
    u = get_user(cid, uid)
    if u['balance'] < amt: return await m.answer(f"❌ Мало ({fmt_money(u['balance'])})")
    update_balance(cid, uid, -amt)
    update_bank(cid, uid, amt)
    bd = get_bank(cid, uid)
    await m.answer(f"📥 Вклад: <b>{fmt_money(amt)}</b>\nНа счету: <b>{fmt_money(bd['deposit'])}</b>", parse_mode="HTML")

@dp.message(Command("withdraw"))
async def cmd_withdraw(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2: return await m.answer("/withdraw сумма")
    try: amt = int(args[1])
    except: return await m.answer("❌ Число!")
    bd = get_bank(cid, uid)
    interest = int(bd['deposit'] * BANK_INTEREST_RATE * ((time.time() - bd['last_interest_time']) / 86400))
    if bd['deposit'] < amt: return await m.answer(f"❌ На счету {fmt_money(bd['deposit'])}")
    bd['deposit'] -= amt
    bd['last_interest_time'] = time.time()
    if interest > 0 and bd['deposit'] > 0:
        bd['deposit'] += interest
        update_balance(cid, uid, interest)
    update_balance(cid, uid, amt)
    t = f"📤 Снято: <b>{fmt_money(amt)}</b>"
    if interest > 0: t += f"\n📈 Проценты: +{fmt_money(interest)}"
    t += f"\nОстаток: <b>{fmt_money(bd['deposit'])}</b>"
    await m.answer(t, parse_mode="HTML")

# --- КРЕДИТ ---
@dp.message(Command("credit"))
async def cmd_credit(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2: return await m.answer("💳 <b>Взять кредит</b>\n\n/credit сумма\n\n• Макс: 10x баланса\n• 2% в день\n• Срок: 7 дней\n• Просрочка = арест", parse_mode="HTML")
    try: amount = int(args[1])
    except: return await m.answer("❌ Число!")
    if amount < 100: return await m.answer("❌ Мин: 100")
    loan = get_loan(cid, uid)
    if loan['amount'] > 0: return await m.answer(f"❌ Уже есть кредит! Долг: {fmt_money(loan['amount'])}")
    user = get_user(cid, uid)
    max_loan = user['balance'] * CREDIT_MULTIPLIER
    if amount > max_loan: return await m.answer(f"❌ Макс: {fmt_money(max_loan)}")
    taken_at = time.time()
    due_date = taken_at + (CREDIT_TERM_DAYS * 86400)
    update_loan(cid, uid, amount, 0, taken_at, due_date)
    update_balance(cid, uid, amount)
    await m.answer(f"💳 <b>Кредит оформлен!</b>\n\n💰 Получено: {fmt_money(amount)}\n📉 Процент: 2% в день\n⏰ Вернуть до: {format_date(due_date)}\n\n⚠️ Просрочка = АРЕСТ!", parse_mode="HTML")

@dp.message(Command("debt"))
async def cmd_debt(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    loan = get_loan(cid, uid)
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
    loan = get_loan(cid, uid)
    if loan['amount'] == 0: return await m.answer("✅ Нет кредитов!")
    user = get_user(cid, uid)
    if user['balance'] < amount: return await m.answer(f"❌ Мало ({fmt_money(user['balance'])})")
    total_debt = loan['amount'] + loan['interest']
    if amount > total_debt: amount = total_debt
    remaining = amount
    interest_paid = min(remaining, loan['interest'])
    remaining -= interest_paid
    principal_paid = min(remaining, loan['amount'])
    new_interest = loan['interest'] - interest_paid
    new_amount = loan['amount'] - principal_paid
    update_balance(cid, uid, -amount)
    if new_amount <= 0:
        clear_loan(cid, uid)
        await m.answer(f"✅ Кредит погашен!\nСписано: {fmt_money(amount)}\nПроценты: {fmt_money(interest_paid)}", parse_mode="HTML")
    else:
        update_loan(cid, uid, new_amount, new_interest, loan['taken_at'], loan['due_date'])
        await m.answer(f"✅ Частично погашено!\nСписано: {fmt_money(amount)}\nОстаток: <b>{fmt_money(new_amount + new_interest)}</b>", parse_mode="HTML")

@dp.message(Command("repay_all"))
async def cmd_repay_all(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    loan = get_loan(cid, uid)
    if loan['amount'] == 0: return await m.answer("✅ Нет кредитов!")
    total_debt = loan['amount'] + loan['interest']
    user = get_user(cid, uid)
    if user['balance'] < total_debt: return await m.answer(f"❌ Нужно: {fmt_money(total_debt)}\nУ вас: {fmt_money(user['balance'])}")
    update_balance(cid, uid, -total_debt)
    clear_loan(cid, uid)
    await m.answer(f"✅ Кредит погашен!\nСписано: <b>{fmt_money(total_debt)}</b>", parse_mode="HTML")

# --- КРАФТ ---
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
    key = f"{cid}_{uid}"
    items = inventory_db.get(key, [])
    inv = {}
    for i in items: inv[i['item_name']] = inv.get(i['item_name'], 0) + 1
    for rn, rc in rec["requires"].items():
        if inv.get(rn, 0) < rc: return await m.answer(f"❌ Нужно {rc}× {rn} (есть {inv.get(rn, 0)})")
    for rn, rc in rec["requires"].items():
        removed = 0
        new_items = []
        for item in items:
            if item['item_name'] == rn and removed < rc:
                removed += 1
            else:
                new_items.append(item)
        items = new_items
    items.append({"item_name": rec["name"], "item_type": 'crafted', "rarity": rec["rarity"]})
    inventory_db[key] = items
    await m.answer(f"✅ Скрафчено: <b>{rec['name']}</b>", parse_mode="HTML")

# --- ОБРАЗОВАНИЕ ---
@dp.message(Command("education"))
async def cmd_education(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    edu = get_education(cid, uid)
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
    edu = get_education(cid, uid)
    if ck in edu['completed_courses'] or (ck == 'mba' and edu['has_mba']): return await m.answer("✅ Уже пройдено")
    u = get_user(cid, uid)
    if u['balance'] < c['price']: return await m.answer(f"❌ Нужно {fmt_money(c['price'])}")
    update_balance(cid, uid, -c['price'])
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
            complete_course(cid, uid, ex['course'])
            await m.answer(f"🎉 <b>Сдано!</b> Курс <b>{c['name']}</b> завершён!", parse_mode="HTML")
        else:
            await m.answer(f"😔 <b>Провал.</b> {ex['correct']}/3\n/buy_course {ex['course']}", parse_mode="HTML")
        del exam_sessions[ek]

# --- КОСТИ ---
@dp.message(Command("dice"))
async def cmd_dice(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2: return await m.answer(f"🎲 <b>/dice сумма</b>\n\n🎯 Шанс: <b>50%</b>\n💰 Выигрыш: x{DICE_WIN_MULTIPLIER}\n📉 Мин: {DICE_MIN_BET}", parse_mode="HTML")
    try: bet = int(args[1])
    except: return await m.answer("❌ Число!")
    if bet < DICE_MIN_BET: return await m.answer(f"❌ Мин: {DICE_MIN_BET}")
    ub = get_user(cid, uid)
    if ub['balance'] < bet: return await m.answer(f"❌ Мало ({fmt_money(ub['balance'])})")
    update_balance(cid, uid, -bet)
    chance_roll = random.randint(1, 100)
    is_win = chance_roll <= DICE_WIN_PERCENT
    visual_dice = random.randint(4, 6) if is_win else random.randint(1, 3)
    await m.answer(f"🎲 <b>Бросаем...</b>\nСтавка: {fmt_money(bet)}", parse_mode="HTML")
    await asyncio.sleep(1)
    if is_win:
        win = bet * DICE_WIN_MULTIPLIER
        update_balance(cid, uid, win)
        await m.answer(f"🎲 Выпало: <b>{visual_dice}</b>\n\n🎉 <b>ПОБЕДА!</b>\n💰 +{fmt_money(win)} (x{DICE_WIN_MULTIPLIER})", parse_mode="HTML")
    else:
        await m.answer(f"🎲 Выпало: <b>{visual_dice}</b>\n\n💀 <b>Проигрыш</b>", parse_mode="HTML")

@dp.message(Command("buy_ticket"))
async def cmd_buy_ticket(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    ub = get_user(cid, uid)
    if ub['balance'] < LOTTERY_PRICE: return await m.answer(f"❌ Нужно {fmt_money(LOTTERY_PRICE)}")
    update_balance(cid, uid, -LOTTERY_PRICE)
    lottery_tickets_db.append({"chat_id": cid, "user_id": uid, "buy_time": time.time()})
    await m.answer("🎟️ Билет куплен! Розыгрыш через 12ч.")

# --- ИНФО ---
@dp.message(Command("info"))
async def cmd_info(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    save_username(cid, uid, m.from_user.full_name)
    u = get_user(cid, uid)
    p = get_profile(cid, uid)
    c = get_car(cid, uid)
    bd = get_bank(cid, uid)
    edu = get_education(cid, uid)
    loan = get_loan(cid, uid)
    in_jail = is_in_jail(cid, uid)
    key = f"{cid}_{uid}"
    bc = len([b for b in businesses_db.values() if b['chat_id'] == cid and b['user_id'] == uid])
    ic = len(inventory_db.get(key, []))
    jail_fine = jail_fines_db.get(key)
    j = JOBS[p['job_key']]
    cc = len(edu['completed_courses']) + (1 if edu['has_mba'] else 0)
    cars_text = ", ".join([car['car_name'] for car in c]) if c else 'нет'
    t = f"📊 <b>Карточка</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>{m.from_user.full_name}</b>\n💰 {fmt_money(u['balance'])}\n🏦 {fmt_money(bd['deposit'])}\n💼 {j['name']} (Ур.{p['level']})\n🚗 {cars_text}\n🏢 {bc}\n🎒 {ic}\n🎓 {cc}"
    if in_jail: t += "\n🔒 <b>В ТЮРЬМЕ!</b>"
    if u['balance'] < 0: t += f"\n⛔ ДОЛГ: {fmt_money(abs(u['balance']))}"
    if jail_fine: t += f"\n⚠️ Штраф: {fmt_money(jail_fine['fine_amount'])}"
    coffee_level = p.get('coffee_level', 0)
    if coffee_level > 0: t += f"\n☕ Кофе Ур.{coffee_level} (-{coffee_level*10}% кулдаун)"
    if edu['has_mba']: t += "\n🎯 MBA (+50% к зарплате)"
    if loan['amount'] > 0: t += f"\n💳 Кредит: {fmt_money(loan['amount'] + loan['interest'])}"
    t += "\n━━━━━━━━━━━━━━━━━━━━"
    await m.answer(t, parse_mode="HTML")

# --- ДОСТИЖЕНИЯ ---
@dp.message(Command("achievements"))
async def cmd_achievements(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    key = f"{cid}_{uid}"
    user_achs = achievements_db.get(key, [])
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
                if ach_id in user_achs:
                    t += f"✅ {ach['icon']} <b>{ach['name']}</b>\n   {ach['desc']}\n\n"
                else:
                    t += f"🔒 {ach['icon']} <b>{ach['name']}</b>\n   {ach['desc']}\n\n"
    t += f"━━━━━━━━━━━━━━━━━━━━\n📊 Прогресс: <b>{total_unlocked}/{total_available}</b> ({int(total_unlocked/total_available*100)}%)"
    await m.answer(t, parse_mode="HTML")

# --- МАГАЗИН УЛУЧШЕНИЙ ---
@dp.message(Command("shop"))
async def cmd_shop(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    p = get_profile(cid, uid)
    u = get_user(cid, uid)
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
    if is_in_jail(cid, uid): return await m.answer("🔒 В тюрьме нельзя!")
    args = m.text.split()
    if len(args) < 2 or args[1] not in SHOP_ITEMS: return await m.answer("/shop")
    it = SHOP_ITEMS[args[1]]
    u = get_user(cid, uid)
    p = get_profile(cid, uid)
    if it['type'] == 'level_up':
        price = 3000 * p['level']
        if u['balance'] < price: return await m.answer(f"❌ Нужно {fmt_money(price)}")
        update_balance(cid, uid, -price)
        p['level'] += 1
        await m.answer(f"✅ <b>Уровень повышен!</b>\n\n📊 Ур.{p['level']-1} → <b>Ур.{p['level']}</b>\n💰 {fmt_money(price)}\n\n💡 Следующий: <b>{fmt_money(3000 * p['level'])}</b>", parse_mode="HTML")
    elif it['type'] == 'cooldown_reduce':
        coffee_level = p.get('coffee_level', 0)
        if coffee_level >= 5: return await m.answer("☕ Максимальный уровень!")
        price = 6000 * (coffee_level + 1)
        if u['balance'] < price: return await m.answer(f"❌ Нужно {fmt_money(price)}")
        update_balance(cid, uid, -price)
        p['coffee_level'] = coffee_level + 1
        bonus = p['coffee_level'] * 10
        next_price = 6000 * (p['coffee_level'] + 1) if p['coffee_level'] < 5 else "МАКС"
        await m.answer(f"☕ <b>Кофе улучшена!</b>\n\n📊 Ур.{coffee_level} → <b>{p['coffee_level']}</b>\n⚡ -{bonus}% кулдаун\n💰 {fmt_money(price)}\n\n💡 Следующий: <b>{next_price}</b>" if p['coffee_level'] < 5 else "Максимум!", parse_mode="HTML")

# --- ГОРОДА ---
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
        player_city = get_player_city(cid, uid)
        if not player_city: return await m.answer("❌ Нет города!\n/city choose [город]")
        mayor = get_mayor(cid, player_city['id'])
        treasury = get_city_treasury(cid, player_city['id'])
        t = f"{player_city['emoji']} <b>{player_city['name']}</b>\n\n📊 {player_city['desc']}\n💰 Казна: {treasury}\n\n"
        if mayor:
            days_left = int((mayor['expires_at'] - time.time()) / 86400)
            t += f"🏛️ Мэр: ID:{mayor['user_id']}\n📊 Рейтинг: {mayor['approval_rating']}%\n⏰ {days_left} дн."
        else: t += "🏛️ Мэр: ВАКАНТНО"
        return await m.answer(t, parse_mode="HTML")
    if subcmd == "choose":
        if len(args) < 3: return await m.answer("⚠️ /city choose Москва")
        city_name = " ".join(args[2:])
        existing = get_player_city(cid, uid)
        if existing: return await m.answer(f"❌ Уже в <b>{existing['name']}</b>!\n/city move", parse_mode="HTML")
        city = next((c for c in CITIES_LIST if c['name'].lower() == city_name.lower()), None)
        if not city: return await m.answer(f"❌ Не найден! /city list")
        set_player_city(cid, uid, city['id'])
        return await m.answer(f"🎉 <b>Добро пожаловать в {city['emoji']} {city['name']}!</b>\n\n📊 {city['desc']}", parse_mode="HTML")
    if subcmd == "move":
        if len(args) < 3: return await m.answer("⚠️ /city move Москва")
        city_name = " ".join(args[2:])
        existing = get_player_city(cid, uid)
        if not existing: return await m.answer("❌ Сначала /city choose")
        city = next((c for c in CITIES_LIST if c['name'].lower() == city_name.lower()), None)
        if not city: return await m.answer(f"❌ Не найден! /city list")
        if city['id'] == existing['id']: return await m.answer("❌ Уже здесь!")
        user = get_user(cid, uid)
        if user['balance'] < CITY_MOVE_COST: return await m.answer(f"❌ Нужно {CITY_MOVE_COST}")
        update_balance(cid, uid, -CITY_MOVE_COST)
        set_player_city(cid, uid, city['id'])
        return await m.answer(f"🚚 <b>ПЕРЕЕЗД!</b>\n\n{city['emoji']} {city['name']}\n📊 {city['desc']}", parse_mode="HTML")
    if subcmd == "residents":
        player_city = get_player_city(cid, uid)
        if not player_city: return await m.answer("❌ Нет города!")
        residents = [k for k, v in player_cities_db.items() if k.startswith(f"{cid}_") and v == player_city['id']][:20]
        if not residents: return await m.answer("🏙️ Никого нет!")
        t = f"{player_city['emoji']} <b>Жители {player_city['name']}:</b>\n\n"
        for i, key in enumerate(residents, 1):
            uid_res = int(key.split("_")[1])
            name = usernames_db.get(key, f"User{uid_res}")
            t += f"{i}. {name}\n"
        t += f"\n📊 Всего: {len(residents)}"
        return await m.answer(t, parse_mode="HTML")
    await m.answer("❓ /city")

# --- МЭР ---
@dp.message(Command("mayor_nominate"))
async def cmd_mayor_nominate(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города! /city choose")
    user = get_user(cid, uid)
    if user['balance'] < MAYOR_ELECTION_FEE:
        return await m.answer(f"❌ Нужно {fmt_money(MAYOR_ELECTION_FEE)}")
    current_mayor = get_mayor(cid, player_city['id'])
    if current_mayor:
        days_left = int((current_mayor['expires_at'] - time.time()) / 86400)
        return await m.answer(f"❌ В {player_city['name']} уже есть мэр! Срок: {days_left} дн.")
    update_balance(cid, uid, -MAYOR_ELECTION_FEE)
    week_num = int(time.time() // 604800)
    election_id = f"elec_{cid}_{player_city['id']}_w{week_num}"
    mayor_candidates_db.append({"chat_id": cid, "city_id": player_city['id'], "user_id": uid, "votes": 0, "election_id": election_id})
    await m.answer(f"✅ Выдвинут!\n💸 {fmt_money(MAYOR_ELECTION_FEE)}", parse_mode="HTML")

@dp.message(Command("mayor_vote"))
async def cmd_mayor_vote(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    player_city = get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    week_num = int(time.time() // 604800)
    election_id = f"elec_{cid}_{player_city['id']}_w{week_num}"
    candidates = [c for c in mayor_candidates_db if c['chat_id'] == cid and c['city_id'] == player_city['id'] and c['election_id'] == election_id]
    if len(args) < 2:
        if not candidates: return await m.answer(f"🏛️ <b>Выборы в {player_city['emoji']} {player_city['name']}</b>\n\n❌ Нет кандидатов.\n/mayor_nominate", parse_mode="HTML")
        t = f"🏛️ <b>Кандидаты {player_city['emoji']} {player_city['name']}:</b>\n\n"
        for i, c in enumerate(candidates, 1):
            t += f"{i}. ID:{c['user_id']} ({c['votes']})\n"
        t += f"\n💰 {MAYOR_VOTE_COST}\n/mayor_vote [номер]"
        return await m.answer(t, parse_mode="HTML")
    try: candidate_num = int(args[1])
    except ValueError: return await m.answer("❌ Число!")
    user = get_user(cid, uid)
    if user['balance'] < MAYOR_VOTE_COST:
        return await m.answer(f"❌ Голос стоит {MAYOR_VOTE_COST}")
    if not candidates: return await m.answer("❌ Нет кандидатов!")
    if candidate_num < 1 or candidate_num > len(candidates): return await m.answer(f"❌ 1-{len(candidates)}")
    target_candidate = candidates[candidate_num - 1]
    if target_candidate['user_id'] == uid: return await m.answer("❌ Нельзя за себя!")
    update_balance(cid, uid, -MAYOR_VOTE_COST)
    update_city_treasury(cid, player_city['id'], MAYOR_VOTE_COST)
    target_candidate['votes'] += 1
    await m.answer(f"✅ Голос принят!\n💸 {MAYOR_VOTE_COST}", parse_mode="HTML")

@dp.message(Command("mayor_finalize"))
async def cmd_mayor_finalize(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    week_num = int(time.time() // 604800)
    election_id = f"elec_{cid}_{player_city['id']}_w{week_num}"
    candidates = [c for c in mayor_candidates_db if c['chat_id'] == cid and c['city_id'] == player_city['id'] and c['election_id'] == election_id]
    if not candidates:
        return await m.answer(f"🏛️ <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
    winner = max(candidates, key=lambda x: x['votes'])
    expires_at = time.time() + MAYOR_TERM_DAYS * 86400
    mayors_db[f"{cid}_{player_city['id']}"] = {"user_id": winner['user_id'], "elected_at": time.time(), "expires_at": expires_at, "approval_rating": 50}
    update_balance(cid, winner['user_id'], MAYOR_ELECTION_FEE + MAYOR_WIN_BONUS)
    mayor_candidates_db[:] = [c for c in mayor_candidates_db if not (c['chat_id'] == cid and c['city_id'] == player_city['id'] and c['election_id'] == election_id)]
    return await m.answer(f"🎉 <b>НОВЫЙ МЭР!</b>\n\n🏛️ {player_city['emoji']} {player_city['name']}\n👤 ID: {winner['user_id']}\n🗳️ {winner['votes']}\n💰 +{MAYOR_WIN_BONUS}\n⏰ {MAYOR_TERM_DAYS} дн.\n\n/city info", parse_mode="HTML")

@dp.message(Command("mayor_decree"))
async def cmd_mayor_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    if not is_mayor(cid, uid, player_city['id']): return await m.answer("❌ Только мэр!")
    args = m.text.split()
    if len(args) < 2:
        return await m.answer(f"🏛️ <b>УКАЗЫ МЭРА</b>\n\n/mayor_decree work (+20% работа, 5к)\n/mayor_decree tools (-30% инструменты, 3к)\n/mayor_decree business (+15% бизнес, 8к)\n/mayor_decree cars (-25% авто, 4к)\n/mayor_decree event (праздник, 10к)\n\n💰 Казна: {get_city_treasury(cid, player_city['id'])}", parse_mode="HTML")
    decree = args[1].lower()
    decree_map = {'work': 'work_bonus', 'tools': 'tool_discount', 'business': 'business_bonus', 'cars': 'car_discount', 'event': 'city_event'}
    decree_type = decree_map.get(decree)
    if not decree_type: return await m.answer("❌ Неизвестный указ!")
    costs = {'work_bonus': 5000, 'tool_discount': 3000, 'business_bonus': 8000, 'car_discount': 4000, 'city_event': 10000}
    cost = costs.get(decree_type, 5000)
    treasury = get_city_treasury(cid, player_city['id'])
    if treasury < cost:
        return await m.answer(f"❌ В казне нужно {cost}, есть: {treasury}")
    update_city_treasury(cid, player_city['id'], -cost)
    city_decrees_db.append({"chat_id": cid, "city_id": player_city['id'], "mayor_id": uid, "decree_type": decree_type, "active_until": time.time() + 86400})
    await m.answer(f"✅ Указ издан! 24 часов.\n💸 Списано: {cost}", parse_mode="HTML")

@dp.message(Command("city_decrees"))
async def cmd_city_decrees(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    decrees = [d for d in city_decrees_db if d['chat_id'] == cid and d['city_id'] == player_city['id'] and d['active_until'] > time.time()]
    if not decrees: return await m.answer(f"🏛️ <b>{player_city['emoji']} {player_city['name']}</b>\n\n❌ Нет указов")
    names = {'work_bonus': '🏭 Рабочая смена (+20% к работе)', 'tool_discount': '🔧 Заводской бонус (-30% на инструменты)', 'business_bonus': '📈 Бизнес-стимул (+15% к бизнесам)', 'car_discount': '🚗 Авто-скидка (-25% на машины)', 'city_event': '🎉 День города (бонус всем жителям)'}
    t = f"🏛️ <b>Указы {player_city['emoji']} {player_city['name']}:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {names.get(d['decree_type'], 'Неизвестный указ')}\n  ⏰ {hours_left} ч.\n\n"
    return await m.answer(t, parse_mode="HTML")

# --- ПРЕЗИДЕНТ ---
@dp.message(Command("president_nominate"))
async def cmd_president_nominate(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    user = get_user(cid, uid)
    if user['balance'] < PRESIDENT_ELECTION_FEE:
        return await m.answer(f"❌ Нужно {fmt_money(PRESIDENT_ELECTION_FEE)}")
    current_official = get_federal_role(cid, 'president')
    if current_official:
        days_left = int((current_official['expires_at'] - time.time()) / 86400)
        return await m.answer(f"❌ Президент у власти! {days_left} дн.")
    update_balance(cid, uid, -PRESIDENT_ELECTION_FEE)
    week_num = int(time.time() // 604800)
    election_id = f"federal_{cid}_president_w{week_num}"
    federal_candidates_db.append({"chat_id": cid, "role": 'president', "user_id": uid, "votes": 0, "election_id": election_id})
    await m.answer(f"✅ Выдвинут в Президент!\n💸 {fmt_money(PRESIDENT_ELECTION_FEE)}", parse_mode="HTML")

@dp.message(Command("president_vote"))
async def cmd_president_vote(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    week_num = int(time.time() // 604800)
    election_id = f"federal_{cid}_president_w{week_num}"
    candidates = [c for c in federal_candidates_db if c['chat_id'] == cid and c['role'] == 'president' and c['election_id'] == election_id]
    if len(args) < 2:
        if not candidates: return await m.answer("🏛️ <b>Выборы Президента</b>\n\n❌ Нет кандидатов.\n/president_nominate", parse_mode="HTML")
        t = "🏛️ <b>Кандидаты:</b>\n\n"
        for i, c in enumerate(candidates, 1):
            t += f"{i}. ID:{c['user_id']} ({c['votes']})\n"
        t += f"\n💰 {PRESIDENT_VOTE_COST}\n/president_vote [номер]"
        return await m.answer(t, parse_mode="HTML")
    try: candidate_num = int(args[1])
    except ValueError: return await m.answer("❌ Число!")
    user = get_user(cid, uid)
    if user['balance'] < PRESIDENT_VOTE_COST:
        return await m.answer(f"❌ Голос стоит {fmt_money(PRESIDENT_VOTE_COST)}")
    if not candidates: return await m.answer("❌ Нет кандидатов!")
    if candidate_num < 1 or candidate_num > len(candidates): return await m.answer(f"❌ 1-{len(candidates)}")
    target_candidate = candidates[candidate_num - 1]
    if target_candidate['user_id'] == uid: return await m.answer("❌ Нельзя за себя!")
    update_balance(cid, uid, -PRESIDENT_VOTE_COST)
    update_state_treasury(cid, PRESIDENT_VOTE_COST)
    target_candidate['votes'] += 1
    await m.answer(f"✅ Голос принят!\n💸 {fmt_money(PRESIDENT_VOTE_COST)}", parse_mode="HTML")

@dp.message(Command("president_finalize"))
async def cmd_president_finalize(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    week_num = int(time.time() // 604800)
    election_id = f"federal_{cid}_president_w{week_num}"
    candidates = [c for c in federal_candidates_db if c['chat_id'] == cid and c['role'] == 'president' and c['election_id'] == election_id]
    if not candidates:
        return await m.answer("🏛️ <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
    winner = max(candidates, key=lambda x: x['votes'])
    expires_at = time.time() + PRESIDENT_TERM_DAYS * 86400
    federal_roles_db[f"{cid}_president"] = {"user_id": winner['user_id'], "elected_at": time.time(), "expires_at": expires_at, "approval_rating": 50}
    update_balance(cid, winner['user_id'], PRESIDENT_ELECTION_FEE + PRESIDENT_WIN_BONUS)
    federal_candidates_db[:] = [c for c in federal_candidates_db if not (c['chat_id'] == cid and c['role'] == 'president' and c['election_id'] == election_id)]
    return await m.answer(f"🎉 <b>НОВЫЙ ПРЕЗИДЕНТ!</b>\n\n👤 ID: {winner['user_id']}\n🗳️ {winner['votes']}\n💰 +{PRESIDENT_WIN_BONUS}\n⏰ {PRESIDENT_TERM_DAYS} дн.", parse_mode="HTML")

@dp.message(Command("president_decree"))
async def cmd_president_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if not is_federal_official(cid, uid, 'president'): return await m.answer("❌ Только Президент!")
    args = m.text.split()
    if len(args) < 2: return await m.answer("🏛️ <b>УКАЗЫ</b>\n\n/president_decree amnesty\n/president_decree tax_cut\n/president_decree tax_boost\n/president_decree emergency", parse_mode="HTML")
    decree = args[1].lower()
    decree_map = {'amnesty': 'amnesty', 'tax_cut': 'tax_cut', 'tax_boost': 'tax_boost', 'emergency': 'emergency'}
    decree_type = decree_map.get(decree)
    if not decree_type: return await m.answer("❌ Неизвестный указ!")
    if decree_type == 'amnesty':
        jailed_users = [k for k, v in jail_db.items() if v['release_time'] > time.time()]
        count = len(jailed_users)
        if count > 0:
            for k in jailed_users:
                del jail_db[k]
        return await m.answer(f"🕊️ <b>АМНИСТИЯ!</b>\n\nОсвобождено: <b>{count}</b>", parse_mode="HTML")
    duration = 168
    federal_decrees_db.append({"chat_id": cid, "role": 'president', "decree_type": decree_type, "active_until": time.time() + (duration * 3600)})
    await m.answer(f"✅ Указ Президент издан!\n⏰ {duration} часов.", parse_mode="HTML")

@dp.message(Command("president_decrees"))
async def cmd_president_decrees(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    decrees = [d for d in federal_decrees_db if d['chat_id'] == cid and d['role'] == 'president' and d['active_until'] > time.time()]
    if not decrees: return await m.answer("🏛️ <b>Указы Президента</b>\n\n❌ Нет активных")
    names = {'amnesty': '🕊️ Амнистия', 'tax_cut': '📉 Снижение налога до 5%', 'tax_boost': '📈 Повышение до 15%', 'emergency': '🚨 ЧП'}
    t = "🏛️ <b>Активные указы:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {names.get(d['decree_type'], 'Неизвестный указ')}\n  ⏰ {hours_left} ч.\n\n"
    return await m.answer(t, parse_mode="HTML")

# --- ПРЕМЬЕР ---
@dp.message(Command("prime_nominate"))
async def cmd_prime_nominate(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    user = get_user(cid, uid)
    if user['balance'] < PRIME_MINISTER_ELECTION_FEE:
        return await m.answer(f"❌ Нужно {fmt_money(PRIME_MINISTER_ELECTION_FEE)}")
    current_official = get_federal_role(cid, 'prime_minister')
    if current_official:
        days_left = int((current_official['expires_at'] - time.time()) / 86400)
        return await m.answer(f"❌ Премьер у власти! {days_left} дн.")
    update_balance(cid, uid, -PRIME_MINISTER_ELECTION_FEE)
    week_num = int(time.time() // 604800)
    election_id = f"federal_{cid}_prime_minister_w{week_num}"
    federal_candidates_db.append({"chat_id": cid, "role": 'prime_minister', "user_id": uid, "votes": 0, "election_id": election_id})
    await m.answer(f"✅ Выдвинут в Премьер!\n💸 {fmt_money(PRIME_MINISTER_ELECTION_FEE)}", parse_mode="HTML")

@dp.message(Command("prime_vote"))
async def cmd_prime_vote(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    week_num = int(time.time() // 604800)
    election_id = f"federal_{cid}_prime_minister_w{week_num}"
    candidates = [c for c in federal_candidates_db if c['chat_id'] == cid and c['role'] == 'prime_minister' and c['election_id'] == election_id]
    if len(args) < 2:
        if not candidates: return await m.answer("💼 <b>Выборы Премьера</b>\n\n❌ Нет кандидатов.\n/prime_nominate", parse_mode="HTML")
        t = "💼 <b>Кандидаты:</b>\n\n"
        for i, c in enumerate(candidates, 1):
            t += f"{i}. ID:{c['user_id']} ({c['votes']})\n"
        t += f"\n💰 {PRIME_MINISTER_VOTE_COST}\n/prime_vote [номер]"
        return await m.answer(t, parse_mode="HTML")
    try: candidate_num = int(args[1])
    except ValueError: return await m.answer("❌ Число!")
    user = get_user(cid, uid)
    if user['balance'] < PRIME_MINISTER_VOTE_COST:
        return await m.answer(f"❌ Голос стоит {fmt_money(PRIME_MINISTER_VOTE_COST)}")
    if not candidates: return await m.answer("❌ Нет кандидатов!")
    if candidate_num < 1 or candidate_num > len(candidates): return await m.answer(f"❌ 1-{len(candidates)}")
    target_candidate = candidates[candidate_num - 1]
    if target_candidate['user_id'] == uid: return await m.answer("❌ Нельзя за себя!")
    update_balance(cid, uid, -PRIME_MINISTER_VOTE_COST)
    update_state_treasury(cid, PRIME_MINISTER_VOTE_COST)
    target_candidate['votes'] += 1
    await m.answer(f"✅ Голос принят!\n💸 {fmt_money(PRIME_MINISTER_VOTE_COST)}", parse_mode="HTML")

@dp.message(Command("prime_finalize"))
async def cmd_prime_finalize(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    week_num = int(time.time() // 604800)
    election_id = f"federal_{cid}_prime_minister_w{week_num}"
    candidates = [c for c in federal_candidates_db if c['chat_id'] == cid and c['role'] == 'prime_minister' and c['election_id'] == election_id]
    if not candidates:
        return await m.answer("💼 <b>Выборы завершены.</b>\n\n❌ Никто не баллотировался.", parse_mode="HTML")
    winner = max(candidates, key=lambda x: x['votes'])
    expires_at = time.time() + PRIME_MINISTER_TERM_DAYS * 86400
    federal_roles_db[f"{cid}_prime_minister"] = {"user_id": winner['user_id'], "elected_at": time.time(), "expires_at": expires_at, "approval_rating": 50}
    update_balance(cid, winner['user_id'], PRIME_MINISTER_ELECTION_FEE + PRIME_MINISTER_WIN_BONUS)
    federal_candidates_db[:] = [c for c in federal_candidates_db if not (c['chat_id'] == cid and c['role'] == 'prime_minister' and c['election_id'] == election_id)]
    return await m.answer(f"🎉 <b>НОВЫЙ ПРЕМЬЕР!</b>\n\n👤 ID: {winner['user_id']}\n🗳️ {winner['votes']}\n💰 +{PRIME_MINISTER_WIN_BONUS}\n⏰ {PRIME_MINISTER_TERM_DAYS} дн.", parse_mode="HTML")

@dp.message(Command("prime_decree"))
async def cmd_prime_decree(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    if not is_federal_official(cid, uid, 'prime_minister'): return await m.answer("❌ Только Премьер!")
    args = m.text.split()
    if len(args) < 2: return await m.answer("💼 <b>УКАЗЫ</b>\n\n/prime_decree subsidy\n/prime_decree investment\n/prime_decree tax_cut\n/prime_decree tax_boost", parse_mode="HTML")
    decree = args[1].lower()
    decree_map = {'subsidy': 'subsidy', 'investment': 'investment', 'tax_cut': 'tax_cut', 'tax_boost': 'tax_boost'}
    decree_type = decree_map.get(decree)
    if not decree_type: return await m.answer("❌ Неизвестный указ!")
    if decree_type == 'investment':
        cities_with_players = set(v for v in player_cities_db.values())
        for city_id in cities_with_players:
            update_city_treasury(cid, city_id, 5000)
        return await m.answer(f"🏗️ <b>ИНВЕСТИЦИИ!</b>\n\nКаждому городу + <b>5000</b>\nГородов: <b>{len(cities_with_players)}</b>", parse_mode="HTML")
    duration = 168
    federal_decrees_db.append({"chat_id": cid, "role": 'prime_minister', "decree_type": decree_type, "active_until": time.time() + (duration * 3600)})
    await m.answer(f"✅ Указ Премьер издан!\n⏰ {duration} часов.", parse_mode="HTML")

@dp.message(Command("prime_decrees"))
async def cmd_prime_decrees(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    decrees = [d for d in federal_decrees_db if d['chat_id'] == cid and d['role'] == 'prime_minister' and d['active_until'] > time.time()]
    if not decrees: return await m.answer("💼 <b>Указы Премьера</b>\n\n❌ Нет активных")
    names = {'subsidy': '💰 Субсидии (+10%)', 'investment': '🏗️ Инвестиции (+5000)', 'tax_cut': '📉 Снижение налога до 5%', 'tax_boost': '📈 Повышение до 15%'}
    t = "💼 <b>Активные указы:</b>\n\n"
    for d in decrees:
        hours_left = int((d['active_until'] - time.time()) / 3600)
        t += f"• {names.get(d['decree_type'], 'Неизвестный указ')}\n  ⏰ {hours_left} ч.\n\n"
    return await m.answer(t, parse_mode="HTML")

# --- ИМПИЧМЕНТ ---
@dp.message(Command("impeach"))
async def cmd_impeach(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2: return await m.answer("⚖️ <b>ИМПИЧМЕНТ</b>\n\n/impeach president — против Президента\n/impeach prime — против Премьера\n\nНужно 10 голосов за 7 дней", parse_mode="HTML")
    role = args[1].lower()
    if role not in ['president', 'prime']: return await m.answer("❌ Используй president или prime")
    db_role = 'president' if role == 'president' else 'prime_minister'
    official = get_federal_role(cid, db_role)
    if not official: return await m.answer("❌ Сейчас нет действующего чиновника!")
    if official['user_id'] == uid: return await m.answer("❌ Нельзя голосовать против себя!")
    key = f"{cid}_{db_role}_{uid}"
    if key in impeachment_votes_db:
        return await m.answer("❌ Ты уже голосовал за импичмент!")
    impeachment_votes_db[key] = {"voted_at": time.time()}
    votes = len([k for k in impeachment_votes_db.keys() if k.startswith(f"{cid}_{db_role}_")])
    role_name = "Президент" if role == 'president' else "Премьер"
    if votes >= 10:
        del federal_roles_db[f"{cid}_{db_role}"]
        impeachment_votes_db.clear()
        msg = f"⚖️ <b>ИМПИЧМЕНТ УСПЕШЕН!</b>\n\n👤 {role_name} ID:{official['user_id']} отстранён от должности!\n🗳️ Голосов: {votes}/10\n\n⏳ Новые выборы через 24 часа"
        await m.answer(msg, parse_mode="HTML")
    else:
        await m.answer(f"⚖️ Голос за импичмент {role_name} принят!\n📊 Голосов: {votes}/10", parse_mode="HTML")

# --- ДОЛГИ ---
@dp.message(Command("debt_give"))
async def cmd_debt_give(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 3: return await m.answer(f"📜 <b>ДАТЬ В ДОЛГ</b>\n\nОтветь на сообщение:\n/debt_give сумма дни\n\nПример: /debt_give 50000 3\nКомиссия: {DEBT_FEE_PERCENT}%", parse_mode="HTML")
    if not m.reply_to_message: return await m.answer("⚠️ Ответь на сообщение!")
    borrower_id = m.reply_to_message.from_user.id
    if borrower_id == uid: return await m.answer("❌ Нельзя себе!")
    if is_in_jail(cid, borrower_id): return await m.answer("🔒 В тюрьме!")
    try:
        amount = int(args[1])
        days = int(args[2])
    except (ValueError, IndexError): return await m.answer("❌ Числа!")
    if amount < DEBT_MIN_AMOUNT: return await m.answer(f"❌ Мин: {fmt_money(DEBT_MIN_AMOUNT)}")
    if days < DEBT_MIN_DAYS or days > DEBT_MAX_DAYS: return await m.answer(f"❌ {DEBT_MIN_DAYS}-{DEBT_MAX_DAYS} дн.")
    fee = int(amount * DEBT_FEE_PERCENT / 100)
    total = amount + fee
    lender = get_user(cid, uid)
    if lender['balance'] < total: return await m.answer(f"❌ Нужно {fmt_money(total)}\nУ вас: {fmt_money(lender['balance'])}", parse_mode="HTML")
    deadline = time.time() + days * 86400
    debt_id = len(debts_db) + 1
    debts_db.append({"id": debt_id, "chat_id": cid, "lender_id": uid, "borrower_id": borrower_id, "amount": amount, "fee": fee, "created_at": time.time(), "deadline": deadline, "status": "active"})
    update_balance(cid, uid, -total)
    update_balance(cid, borrower_id, amount)
    await m.answer(f"📜 <b>РАСПИСКА</b>\n\n👤 ID:{borrower_id}\n💰 {fmt_money(amount)}\n📅 {days} дн.\n🏦 Комиссия: {fmt_money(fee)}\n📤 Списано: {fmt_money(total)}\n\n⚠️ Коллекторы!", parse_mode="HTML")

@dp.message(Command("debt_return"))
async def cmd_debt_return(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    debt = next((d for d in debts_db if d['borrower_id'] == uid and d['status'] == 'active'), None)
    if not debt: return await m.answer("✅ Нет долгов!")
    user = get_user(cid, uid)
    if user['balance'] < debt['amount']: return await m.answer(f"❌ Нужно {fmt_money(debt['amount'])}")
    update_balance(cid, uid, -debt['amount'])
    update_balance(cid, debt['lender_id'], debt['amount'])
    debt['status'] = 'returned'
    await m.answer(f"✅ <b>ДОЛГ ПОГАШЕН!</b>\n\n💰 {fmt_money(debt['amount'])}\n📊 {fmt_money(get_user(cid, uid)['balance'])}", parse_mode="HTML")

@dp.message(Command("debt_list"))
async def cmd_debt_list(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    i_owe = [d for d in debts_db if d['borrower_id'] == uid and d['status'] == 'active']
    owed_me = [d for d in debts_db if d['lender_id'] == uid and d['status'] == 'active']
    t = "📋 <b>ДОЛГИ</b>\n\n"
    if i_owe:
        t += "📤 <b>Я должен:</b>\n"
        for d in i_owe:
            t += f"• ID:{d['lender_id']}: {fmt_money(d['amount'])}\n"
    else: t += "✅ Я никому не должен\n"
    if owed_me:
        t += "\n📥 <b>Мне должны:</b>\n"
        for d in owed_me:
            t += f"• ID:{d['borrower_id']}: {fmt_money(d['amount'])}\n"
    else: t += "\n✅ Мне никто не должен"
    await m.answer(t, parse_mode="HTML")

# --- ПРОЕКТЫ МЭРА ---
@dp.message(Command("mayor_project"))
async def cmd_mayor_project(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    mayor = get_mayor(cid, player_city['id'])
    if not mayor or mayor['user_id'] != uid: return await m.answer("❌ Только мэр!")
    args = m.text.split(maxsplit=1)
    if len(args) < 2:
        proj_list = "\n".join([f"• /mayor_project {k} — {v['name']} ({fmt_money(v['cost'])})" for k, v in PROJECT_TYPES.items()])
        return await m.answer(f"🏗️ <b>ПРОЕКТЫ МЭРА</b>\n\nВыбери проект:\n{proj_list}\n\n⏰ Срок: 24 часа\n⚠️ 1-й провал = штраф 50%\n⚠️ 2-й провал = тюрьма + снятие", parse_mode="HTML")
    project_key = args[1].lower().strip()
    if project_key not in PROJECT_TYPES: return await m.answer("❌ Неизвестный проект!")
    project = PROJECT_TYPES[project_key]
    cost = project['cost']
    treasury = get_city_treasury(cid, player_city['id'])
    if treasury < cost: return await m.answer(f"❌ В казне только {fmt_money(treasury)}! Нужно {fmt_money(cost)}")
    active = next((p for p in mayor_projects_db if p['chat_id'] == cid and p['city_id'] == player_city['id'] and p['mayor_id'] == uid and p['status'] == 'active'), None)
    if active: return await m.answer("⚠️ У тебя уже есть активный проект!")
    update_city_treasury(cid, player_city['id'], -cost)
    deadline = time.time() + 86400
    project_id = len(mayor_projects_db) + 1
    mayor_projects_db.append({"id": project_id, "chat_id": cid, "city_id": player_city['id'], "mayor_id": uid, "project_type": project_key, "budget": cost, "description": project['desc'], "status": 'active', "started_at": time.time(), "deadline": deadline, "completed_at": None, "fail_count": 0, "reviewed_by": None, "review_result": None})
    await m.answer(f"🏗️ <b>ПРОЕКТ ЗАПУЩЕН!</b>\n\n🏙️ {player_city['emoji']} {player_city['name']}\n📋 {project['name']} — {project['desc']}\n💰 Бюджет: {fmt_money(cost)}\n⏰ Срок: 24 часа\n\nИспользуй <b>/project_done</b> чтобы завершить", parse_mode="HTML")

@dp.message(Command("project_done"))
async def cmd_project_done(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    player_city = get_player_city(cid, uid)
    if not player_city: return await m.answer("❌ Нет города!")
    project = next((p for p in mayor_projects_db if p['chat_id'] == cid and p['city_id'] == player_city['id'] and p['mayor_id'] == uid and p['status'] == 'active'), None)
    if not project: return await m.answer("❌ Нет активного проекта!")
    if time.time() > project['deadline']: return await m.answer("⏰ Срок уже истёк! Жди проверки Президента.")
    project['status'] = 'completed'
    project['completed_at'] = time.time()
    await m.answer(f"✅ <b>ПРОЕКТ ЗАВЕРШЁН!</b>\n\n📋 {PROJECT_TYPES[project['project_type']]['name']}\n⏳ Ожидает проверки Президентом", parse_mode="HTML")

@dp.message(Command("project_check"))
async def cmd_project_check(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    president = get_federal_role(cid, 'president')
    if not president or president['user_id'] != uid: return await m.answer("❌ Только Президент!")
    args = m.text.split()
    if len(args) < 2: return await m.answer("⚖️ <b>ПРОВЕРКА ПРОЕКТА</b>\n\n/project_check [город_id] [approve/reject]", parse_mode="HTML")
    try: city_id = int(args[1])
    except ValueError: return await m.answer("❌ ID города должен быть числом!")
    action = args[2].lower() if len(args) > 2 else None
    if action not in ['approve', 'reject']: return await m.answer("❌ Используй approve или reject!")
    city = next((c for c in CITIES_LIST if c['id'] == city_id), None)
    if not city: return await m.answer("❌ Город не найден!")
    project = next((p for p in mayor_projects_db if p['chat_id'] == cid and p['city_id'] == city_id and p['status'] in ['active', 'completed']), None)
    if not project: return await m.answer(f"✅ В {city['emoji']} {city['name']} нет проектов!")
    if action == 'approve':
        bonus = int(project['budget'] * 0.30)
        update_city_treasury(cid, city_id, bonus)
        mayor_key = f"{cid}_{city_id}"
        if mayor_key in mayors_db:
            mayors_db[mayor_key]['approval_rating'] = min(100, mayors_db[mayor_key]['approval_rating'] + 15)
        project['status'] = 'approved'
        project['reviewed_by'] = uid
        project['review_result'] = 'Одобрено'
        msg = f"✅ <b>ПРОЕКТ ОДОБРЕН!</b>\n\n🏙️ {city['emoji']} {city['name']}\n📋 {PROJECT_TYPES[project['project_type']]['name']}\n👤 Мэр: ID:{project['mayor_id']}\n💰 Возврат в казну: {fmt_money(bonus)}\n📈 Рейтинг мэра: +15%"
        await m.answer(msg, parse_mode="HTML")
    elif action == 'reject':
        project['fail_count'] += 1
        fail_count = project['fail_count']
        if fail_count >= 2:
            send_to_jail(cid, project['mayor_id'], 6)
            mayor_key = f"{cid}_{city_id}"
            if mayor_key in mayors_db:
                del mayors_db[mayor_key]
            project['status'] = 'failed'
            project['reviewed_by'] = uid
            project['review_result'] = 'Снят'
            msg = f"🔒 <b>МЭР СНЯТ С ДОЛЖНОСТИ!</b>\n\n🏙️ {city['emoji']} {city['name']}\n📋 {PROJECT_TYPES[project['project_type']]['name']}\n👤 ID:{project['mayor_id']}\n⚠️ 2-й провал проекта!\n🔒 Тюрьма: 6 часов\n📉 Должность: ВАКАНТНО"
        else:
            fine = int(project['budget'] * 0.50)
            update_balance(cid, project['mayor_id'], -fine)
            mayor_key = f"{cid}_{city_id}"
            if mayor_key in mayors_db:
                mayors_db[mayor_key]['approval_rating'] = max(0, mayors_db[mayor_key]['approval_rating'] - 20)
            project['status'] = 'failed'
            project['reviewed_by'] = uid
            project['review_result'] = 'Штраф'
            msg = f"❌ <b>ПРОЕКТ ОТКЛОНЁН!</b>\n\n🏙️ {city['emoji']} {city['name']}\n📋 {PROJECT_TYPES[project['project_type']]['name']}\n👤 Мэр: ID:{project['mayor_id']}\n💸 Штраф: {fmt_money(fine)} (50% бюджета)\n📉 Рейтинг: -20%\n⚠️ Провалов: {fail_count}/2\n 🔜 Следующий провал = тюрьма + снятие!"
        await m.answer(msg, parse_mode="HTML")

@dp.message(Command("project_status"))
async def cmd_project_status(m: Message):
    cid, uid = m.chat.id, m.from_user.id
    args = m.text.split()
    if len(args) < 2:
        player_city = get_player_city(cid, uid)
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
    projects = [p for p in mayor_projects_db if p['chat_id'] == cid and p['city_id'] == city_id][:5]
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

# --- АВТО-РЕГИСТРАЦИЯ ---
@dp.message()
async def auto_register(m: Message):
    if m.chat.type not in ['group', 'supergroup']: return
    get_user(m.chat.id, m.from_user.id)

@dp.message(F.new_chat_members)
async def on_user_join(m: Message):
    cid = m.chat.id
    for user in m.new_chat_members:
        if user.is_bot:
            if user.id == int(API_TOKEN.split(':')[0]): await m.answer("👋 Привет! /start")
            continue
        get_user(cid, user.id)
        save_username(cid, user.id, user.full_name)

# --- ГЛАВНАЯ ФУНКЦИЯ ---
async def main():
    print("🤖 Бот запускается...")
    print(f"✅ Токен: {API_TOKEN[:10]}...")
    print(f"✅ ADMIN_IDS: {ADMIN_IDS}")
    print("✅ База данных: В ПАМЯТИ (без PostgreSQL)")
    print("🚀 Бот готов к работе!")
    await dp.start_polling(bot, timeout=30, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
