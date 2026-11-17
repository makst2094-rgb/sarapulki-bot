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

# --- ХРАНИЛИЩЕ ---
players_db = {}
countries_db = {}
wars_db = []
alliances_db = {}
technologies_db = {}
events_db = {}
game_time_db = {}

# --- СТРАНЫ ---
COUNTRIES_LIST = [
    {"name": "Россия", "emoji": "🇷🇺", "bonus": "Нефть: +25% доход", "bonus_type": "income", "bonus_value": 0.25, "manpower": 144000000, "factories": 80},
    {"name": "США", "emoji": "🇺🇸", "bonus": "Технологии: -20% стоимость", "bonus_type": "tech", "bonus_value": 0.20, "manpower": 331000000, "factories": 120},
    {"name": "Китай", "emoji": "🇨🇳", "bonus": "Производство: +30% армия", "bonus_type": "army", "bonus_value": 0.30, "manpower": 1400000000, "factories": 100},
    {"name": "Германия", "emoji": "🇩🇪", "bonus": "Промышленность: +35% доход", "bonus_type": "income", "bonus_value": 0.35, "manpower": 83000000, "factories": 90},
    {"name": "Япония", "emoji": "🇯🇵", "bonus": "Флот: +25% сила", "bonus_type": "navy", "bonus_value": 0.25, "manpower": 126000000, "factories": 70},
    {"name": "Франция", "emoji": "🇫🇷", "bonus": "Дипломатия: +15% ко всем", "bonus_type": "all", "bonus_value": 0.15, "manpower": 67000000, "factories": 65},
    {"name": "Великобритания", "emoji": "🇬🇧", "bonus": "Торговля: +20% доход", "bonus_type": "income", "bonus_value": 0.20, "manpower": 67000000, "factories": 75},
    {"name": "Индия", "emoji": "🇮🇳", "bonus": "Население: +50% рекрутов", "bonus_type": "manpower", "bonus_value": 0.50, "manpower": 1380000000, "factories": 60},
]

COUNTRY_CHANGE_COOLDOWN = 30 * 86400

# --- ИДЕОЛОГИИ ---
IDEOLOGIES = {
    "democracy": {"name": "🗳️ Демократия", "stability": 1.0, "war_support": 0.5, "bonus": "Стабильность +20%"},
    "fascism": {"name": "⚫ Фашизм", "stability": 0.8, "war_support": 1.2, "bonus": "Поддержка войны +40%"},
    "communism": {"name": "☭ Коммунизм", "stability": 0.9, "war_support": 0.9, "bonus": "Производство +15%"},
    "neutral": {"name": "⚪ Нейтралитет", "stability": 1.1, "war_support": 0.3, "bonus": "Торговля +25%"},
}

# --- ТЕХНОЛОГИИ ---
TECHNOLOGIES = {
    "industry": {"name": "🏭 Промышленность", "levels": 10, "cost": 5000, "effect": "+10% доход за уровень"},
    "army": {"name": "⚔️ Армия", "levels": 10, "cost": 6000, "effect": "+10% сила армии за уровень"},
    "navy": {"name": "⚓ Флот", "levels": 10, "cost": 7000, "effect": "+10% сила флота за уровень"},
    "air": {"name": "✈️ Авиация", "levels": 10, "cost": 6500, "effect": "+10% сила авиации за уровень"},
    "infantry": {"name": "🪖 Пехота", "levels": 10, "cost": 4000, "effect": "+15% пехота за уровень"},
    "armor": {"name": "🛡️ Танки", "levels": 10, "cost": 8000, "effect": "+20% танки за уровень"},
}

# --- ТИПЫ ВОЙСК ---
UNIT_TYPES = {
    "infantry": {"name": "🪖 Пехота", "cost": 100, "power": 10, "manpower": 1000},
    "tank": {"name": "🛡️ Танки", "cost": 500, "power": 50, "manpower": 500},
    "artillery": {"name": "💥 Артиллерия", "cost": 300, "power": 35, "manpower": 800},
    "plane": {"name": "✈️ Авиация", "cost": 800, "power": 60, "manpower": 200},
    "ship": {"name": "⚓ Флот", "cost": 1200, "power": 80, "manpower": 1500},
    "missile": {"name": "🚀 Ракеты", "cost": 2000, "power": 150, "manpower": 100},
}

# --- ЗДАНИЯ ---
BUILDINGS = {
    "factory": {"name": "🏭 Фабрика", "cost": 5000, "income": 500, "effect": "+500$/день"},
    "dockyard": {"name": "🚢 Верфь", "cost": 7000, "income": 300, "effect": "+300$/день, +флот"},
    "airbase": {"name": "✈️ Аэродром", "cost": 6000, "income": 200, "effect": "+200$/день, +авиация"},
    "bunker": {"name": "🏰 Бункер", "cost": 10000, "income": 0, "effect": "+20% оборона"},
    "radar": {"name": "📡 Радар", "cost": 8000, "income": 100, "effect": "+10% разведка"},
}

# --- СОБЫТИЯ ---
EVENTS = [
    {"name": "📈 Экономический бум", "effect": "income", "value": 1.5, "duration": 3},
    {"name": "⚠️ Военная угроза", "effect": "war_support", "value": 1.3, "duration": 5},
    {"name": "🦠 Пандемия", "effect": "income", "value": 0.7, "duration": 7},
    {"name": "🎉 Национальный праздник", "effect": "stability", "value": 1.2, "duration": 2},
    {"name": "💰 Торговое соглашение", "effect": "income", "value": 1.3, "duration": 4},
    {"name": "⚔️ Пограничный конфликт", "effect": "war_support", "value": 1.4, "duration": 3},
]

# --- УТИЛИТЫ ---
def fmt_money(amount):
    if amount >= 1000000:
        return f"{amount/1000000:.1f}M$"
    elif amount >= 1000:
        return f"{amount/1000:.1f}K$"
    return f"{amount}$"

def fmt_number(amount):
    if amount >= 1000000:
        return f"{amount/1000000:.1f}M"
    elif amount >= 1000:
        return f"{amount/1000:.1f}K"
    return str(amount)

def get_player(uid):
    if uid not in players_db:
        players_db[uid] = {
            "country": None,
            "money": 100000,
            "manpower": 1000000,
            "stability": 100,
            "war_support": 50,
            "ideology": "democracy",
            "factories": 10,
            "dockyards": 5,
            "airbases": 3,
            "bunkers": 0,
            "radars": 0,
            "army": {"infantry": 100, "tank": 10, "artillery": 20, "plane": 5, "ship": 2, "missile": 0},
            "technologies": {"industry": 1, "army": 1, "navy": 1, "air": 1, "infantry": 1, "armor": 1},
            "researching": None,
            "research_progress": 0,
            "last_country_change": 0,
            "wars": [],
            "allies": [],
            "enemies": [],
            "events": [],
            "last_day": time.time(),
            "days_played": 0,
        }
    return players_db[uid]

def get_country_power(player):
    power = 0
    for unit_type, count in player["army"].items():
        unit_data = UNIT_TYPES[unit_type]
        power += count * unit_data["power"]
    
    tech_bonus = 1.0
    for tech, level in player["technologies"].items():
        if tech == "army":
            tech_bonus += (level - 1) * 0.10
        elif tech == "infantry":
            tech_bonus += (level - 1) * 0.15
        elif tech == "armor":
            tech_bonus += (level - 1) * 0.20
    
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == player["country"]), None)
    if country_data and country_data["bonus_type"] in ["army", "navy", "all"]:
        tech_bonus += country_data["bonus_value"]
    
    return int(power * tech_bonus)

def get_country_income(player):
    base_income = 1000 * player["factories"] + 500 * player["dockyards"] + 300 * player["airbases"]
    
    tech_bonus = 1.0 + (player["technologies"]["industry"] - 1) * 0.10
    
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == player["country"]), None)
    if country_data and country_data["bonus_type"] == "income":
        tech_bonus += country_data["bonus_value"]
    elif country_data and country_data["bonus_type"] == "all":
        tech_bonus += country_data["bonus_value"]
    
    stability_bonus = player["stability"] / 100
    
    return int(base_income * tech_bonus * stability_bonus)

def get_manpower(player):
    base = player["manpower"]
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == player["country"]), None)
    if country_data and country_data["bonus_type"] == "manpower":
        base *= (1 + country_data["bonus_value"])
    return int(base)

# --- КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{c['emoji']} {c['name']}", callback_data=f"select_{c['name']}")] 
            for c in COUNTRIES_LIST
        ])
        await m.answer("🌍 <b>Добро пожаловать в Hearts of Iron: Chat Edition!</b>\n\n"
                      "Выберите страну для игры:\n\n"
                      "⚠️ Смена страны возможна раз в 30 дней\n"
                      "📊 У каждой страны уникальные бонусы", 
                      reply_markup=keyboard, parse_mode="HTML")
    else:
        country = next((c for c in COUNTRIES_LIST if c["name"] == player["country"]), None)
        power = get_country_power(player)
        income = get_country_income(player)
        await m.answer(f"{country['emoji']} <b>{country['name']}</b>\n\n"
                      f"💰 Деньги: {fmt_money(player['money'])}\n"
                      f"👥 Население: {fmt_number(player['manpower'])}\n"
                      f"📊 Стабильность: {player['stability']}%\n"
                      f"⚔️ Поддержка войны: {player['war_support']}%\n"
                      f"🏭 Фабрики: {player['factories']}\n"
                      f"⚔️ Сила армии: {fmt_number(power)}\n"
                      f"💵 Доход/день: {fmt_money(income)}\n\n"
                      f"📅 Дней в игре: {player['days_played']}\n\n"
                      f"/help - список команд", parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith("select_"))
async def callback_select_country(callback: CallbackQuery):
    uid = callback.from_user.id
    country_name = callback.data.replace("select_", "")
    player = get_player(uid)
    
    now = time.time()
    if player["country"] is not None and now - player["last_country_change"] < COUNTRY_CHANGE_COOLDOWN:
        days_left = int((COUNTRY_CHANGE_COOLDOWN - (now - player["last_country_change"])) / 86400)
        return await callback.answer(f"❌ Смена страны через {days_left} дн.", show_alert=True)
    
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == country_name), None)
    if not country_data:
        return await callback.answer("❌ Страна не найдена", show_alert=True)
    
    player["country"] = country_name
    player["last_country_change"] = now
    player["manpower"] = country_data["manpower"]
    player["factories"] = country_data["factories"]
    
    await callback.message.edit_text(f"✅ <b>Вы выбрали {country_data['emoji']} {country_name}!</b>\n\n"
                                    f"📊 {country_data['bonus']}\n"
                                    f"👥 Население: {fmt_number(country_data['manpower'])}\n"
                                    f"🏭 Фабрики: {country_data['factories']}\n\n"
                                    f"💰 Начальный баланс: {fmt_money(player['money'])}\n\n"
                                    f"/help - список команд", parse_mode="HTML")
    await callback.answer()

@dp.message(Command("help"))
async def cmd_help(m: Message):
    text = """📋 <b>КОМАНДЫ HEARTS OF IRON</b>

🌍 <b>Страна:</b>
/country - статус страны
/change_country - сменить страну (30 дней)
/ideology [идеология] - сменить идеологию

💰 <b>Экономика:</b>
/build [здание] - построить
/buildings - список зданий
/trade @user сумма - торговля

⚔️ <b>Армия:</b>
/recruit [тип] [кол-во] - нанять
/army - статус армии
/attack @user - атаковать
/defend - оборонительная позиция

🔬 <b>Исследования:</b>
/research [технология] - исследовать
/technologies - список технологий

🤝 <b>Дипломатия:</b>
/alliance @user - предложить союз
/war @user - объявить войну
/peace @user - заключить мир
/diplomacy - статус дипломатии

📅 <b>Время:</b>
/next_day - следующий день
/events - текущие события

🏆 <b>Рейтинг:</b>
/rating - топ игроков
/countries - все страны"""
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("country"))
async def cmd_country(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    country_name = player["country"]
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == country_name), None)
    ideology = IDEOLOGIES[player["ideology"]]
    power = get_country_power(player)
    income = get_country_income(player)
    
    days_since_change = int((time.time() - player["last_country_change"]) / 86400)
    days_until_change = 30 - days_since_change
    
    text = f"{country_data['emoji']} <b>{country_name}</b>\n\n"
    text += f"📊 {country_data['bonus']}\n"
    text += f"🏛️ Идеология: {ideology['name']}\n"
    text += f"   {ideology['bonus']}\n\n"
    text += f"💰 Деньги: {fmt_money(player['money'])}\n"
    text += f"👥 Население: {fmt_number(player['manpower'])}\n"
    text += f"📊 Стабильность: {player['stability']}%\n"
    text += f"⚔️ Поддержка войны: {player['war_support']}%\n\n"
    text += f"🏭 Фабрики: {player['factories']}\n"
    text += f"🚢 Верфи: {player['dockyards']}\n"
    text += f"✈️ Аэродромы: {player['airbases']}\n"
    text += f"🏰 Бункеры: {player['bunkers']}\n"
    text += f"📡 Радары: {player['radars']}\n\n"
    text += f"⚔️ Сила армии: {fmt_number(power)}\n"
    text += f"💵 Доход/день: {fmt_money(income)}\n\n"
    text += f"🔬 Исследования:\n"
    for tech, level in player["technologies"].items():
        tech_data = TECHNOLOGIES[tech]
        text += f"   {tech_data['name']}: Ур.{level}\n"
    
    if player["researching"]:
        text += f"\n🔬 Исследуется: {TECHNOLOGIES[player['researching']]['name']}\n"
        text += f"   Прогресс: {player['research_progress']}%\n"
    
    text += f"\n📅 Дней в игре: {player['days_played']}\n"
    text += f"⏰ Смена страны через: {days_until_change} дн."
    
    if player["wars"]:
        text += f"\n\n⚔️ Войны: {len(player['wars'])}"
    if player["allies"]:
        text += f"\n🤝 Союзы: {len(player['allies'])}"
    
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("change_country"))
async def cmd_change_country(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    now = time.time()
    if player["country"] is not None and now - player["last_country_change"] < COUNTRY_CHANGE_COOLDOWN:
        days_left = int((COUNTRY_CHANGE_COOLDOWN - (now - player["last_country_change"])) / 86400)
        return await m.answer(f"❌ Смена страны возможна через {days_left} дн.")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{c['emoji']} {c['name']}", callback_data=f"change_{c['name']}")] 
        for c in COUNTRIES_LIST if c["name"] != player["country"]
    ])
    await m.answer("🌍 Выберите новую страну:", reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith("change_"))
async def callback_change_country(callback: CallbackQuery):
    uid = callback.from_user.id
    country_name = callback.data.replace("change_", "")
    player = get_player(uid)
    
    now = time.time()
    if now - player["last_country_change"] < COUNTRY_CHANGE_COOLDOWN:
        days_left = int((COUNTRY_CHANGE_COOLDOWN - (now - player["last_country_change"])) / 86400)
        return await callback.answer(f"❌ Ещё {days_left} дн.", show_alert=True)
    
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == country_name), None)
    if not country_data:
        return await callback.answer("❌ Страна не найдена", show_alert=True)
    
    player["country"] = country_name
    player["last_country_change"] = now
    player["manpower"] = country_data["manpower"]
    player["factories"] = country_data["factories"]
    
    await callback.message.edit_text(f"✅ <b>Вы сменили страну на {country_data['emoji']} {country_name}!</b>\n\n"
                                    f"📊 {country_data['bonus']}\n"
                                    f"👥 Население: {fmt_number(country_data['manpower'])}\n"
                                    f"🏭 Фабрики: {country_data['factories']}", parse_mode="HTML")
    await callback.answer()

@dp.message(Command("ideology"))
async def cmd_ideology(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    args = m.text.split()
    if len(args) < 2:
        text = "🏛️ <b>ИДЕОЛОГИИ:</b>\n\n"
        for key, val in IDEOLOGIES.items():
            current = "✅" if key == player["ideology"] else "⬜"
            text += f"{current} {val['name']}\n   {val['bonus']}\n   Стабильность: {int(val['stability']*100)}%\n"
            text += f"   Поддержка войны: {int(val['war_support']*100)}%\n\n"
        text += "\n/ideology [название]\nПример: /ideology fascism"
        return await m.answer(text, parse_mode="HTML")
    
    ideology_key = args[1].lower()
    if ideology_key not in IDEOLOGIES:
        return await m.answer("❌ Неизвестная идеология! /ideology")
    
    if ideology_key == player["ideology"]:
        return await m.answer("❌ Уже выбрана эта идеология!")
    
    cost = 50000
    if player["money"] < cost:
        return await m.answer(f"❌ Нужно {fmt_money(cost)} для смены идеологии")
    
    player["money"] -= cost
    player["ideology"] = ideology_key
    
    ideology = IDEOLOGIES[ideology_key]
    player["stability"] = int(100 * ideology["stability"])
    player["war_support"] = int(50 * ideology["war_support"])
    
    await m.answer(f"🏛️ <b>Идеология изменена!</b>\n\n"
                  f"{ideology['name']}\n{ideology['bonus']}\n\n"
                  f"💰 Потрачено: {fmt_money(cost)}\n"
                  f"📊 Стабильность: {player['stability']}%\n"
                  f"⚔️ Поддержка войны: {player['war_support']}%", parse_mode="HTML")

@dp.message(Command("build"))
async def cmd_build(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    args = m.text.split()
    if len(args) < 2:
        text = "🏗️ <b>ЗДАНИЯ:</b>\n\n"
        for key, val in BUILDINGS.items():
            text += f"🔹 {val['name']} — {fmt_money(val['cost'])}\n"
            text += f"   {val['effect']}\n\n"
        text += "/build [название]\nПример: /build factory"
        return await m.answer(text, parse_mode="HTML")
    
    building_key = args[1].lower()
    if building_key not in BUILDINGS:
        return await m.answer("❌ Неизвестное здание! /build")
    
    building = BUILDINGS[building_key]
    cost = building["cost"]
    
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == player["country"]), None)
    if country_data and country_data["bonus_type"] == "tech":
        cost = int(cost * (1 - country_data["bonus_value"]))
    
    if player["money"] < cost:
        return await m.answer(f"❌ Нужно {fmt_money(cost)}")
    
    player["money"] -= cost
    
    if building_key == "factory":
        player["factories"] += 1
    elif building_key == "dockyard":
        player["dockyards"] += 1
    elif building_key == "airbase":
        player["airbases"] += 1
    elif building_key == "bunker":
        player["bunkers"] += 1
    elif building_key == "radar":
        player["radars"] += 1
    
    await m.answer(f"🏗️ <b>Построено: {building['name']}</b>\n\n"
                  f"💰 Потрачено: {fmt_money(cost)}\n"
                  f"{building['effect']}", parse_mode="HTML")

@dp.message(Command("buildings"))
async def cmd_buildings(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    text = "🏗️ <b>ВАШИ ЗДАНИЯ:</b>\n\n"
    text += f"🏭 Фабрики: {player['factories']}\n"
    text += f"🚢 Верфи: {player['dockyards']}\n"
    text += f"✈️ Аэродромы: {player['airbases']}\n"
    text += f"🏰 Бункеры: {player['bunkers']}\n"
    text += f"📡 Радары: {player['radars']}\n"
    
    income = get_country_income(player)
    text += f"\n💵 Общий доход: {fmt_money(income)}/день"
    
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("recruit"))
async def cmd_recruit(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    args = m.text.split()
    if len(args) < 3:
        text = "⚔️ <b>НАБОР АРМИИ:</b>\n\n"
        for key, val in UNIT_TYPES.items():
            text += f"🔹 {val['name']} — {fmt_money(val['cost'])}/шт\n"
            text += f"   Сила: {val['power']}, Население: {fmt_number(val['manpower'])}\n\n"
        text += "/recruit [тип] [кол-во]\nПример: /recruit infantry 100"
        return await m.answer(text, parse_mode="HTML")
    
    unit_key = args[1].lower()
    if unit_key not in UNIT_TYPES:
        return await m.answer("❌ Неизвестный тип войск! /recruit")
    
    try:
        count = int(args[2])
    except ValueError:
        return await m.answer("❌ Число!")
    
    if count <= 0:
        return await m.answer("❌ >0!")
    
    unit = UNIT_TYPES[unit_key]
    cost = unit["cost"] * count
    manpower_needed = unit["manpower"] * count
    
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == player["country"]), None)
    if country_data and country_data["bonus_type"] == "army":
        count = int(count * (1 + country_data["bonus_value"]))
    
    if player["money"] < cost:
        return await m.answer(f"❌ Нужно {fmt_money(cost)}")
    
    available_manpower = get_manpower(player)
    if manpower_needed > available_manpower:
        return await m.answer(f"❌ Нужно {fmt_number(manpower_needed)} населения, есть {fmt_number(available_manpower)}")
    
    player["money"] -= cost
    player["manpower"] -= manpower_needed
    player["army"][unit_key] += count
    
    await m.answer(f"⚔️ <b>Нанято: {count} {unit['name']}</b>\n\n"
                  f"💰 Потрачено: {fmt_money(cost)}\n"
                  f"👥 Использовано населения: {fmt_number(manpower_needed)}\n"
                  f"🪖 Всего: {player['army'][unit_key]}", parse_mode="HTML")

@dp.message(Command("army"))
async def cmd_army(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    power = get_country_power(player)
    
    text = "⚔️ <b>ВАША АРМИЯ:</b>\n\n"
    for unit_key, count in player["army"].items():
        if count > 0:
            unit = UNIT_TYPES[unit_key]
            text += f"{unit['name']}: {count} шт. (сила: {count * unit['power']})\n"
    
    text += f"\n⚔️ <b>Общая сила: {fmt_number(power)}</b>"
    
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("research"))
async def cmd_research(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    args = m.text.split()
    if len(args) < 2:
        text = "🔬 <b>ТЕХНОЛОГИИ:</b>\n\n"
        for key, val in TECHNOLOGIES.items():
            current_level = player["technologies"][key]
            text += f"🔹 {val['name']} — Ур.{current_level}/{val['levels']}\n"
            text += f"   {val['effect']}\n\n"
        text += "/research [название]\nПример: /research army"
        return await m.answer(text, parse_mode="HTML")
    
    tech_key = args[1].lower()
    if tech_key not in TECHNOLOGIES:
        return await m.answer("❌ Неизвестная технология! /research")
    
    if player["researching"]:
        return await m.answer(f"❌ Уже исследуется: {TECHNOLOGIES[player['researching']]['name']}")
    
    tech = TECHNOLOGIES[tech_key]
    current_level = player["technologies"][tech_key]
    
    if current_level >= tech["levels"]:
        return await m.answer("❌ Максимальный уровень!")
    
    player["researching"] = tech_key
    player["research_progress"] = 0
    
    await m.answer(f"🔬 <b>Начато исследование: {tech['name']}</b>\n\n"
                  f"📊 Текущий уровень: {current_level}\n"
                  f"🎯 Цель: Ур.{current_level + 1}\n"
                  f"⏳ Прогресс будет расти каждый день", parse_mode="HTML")

@dp.message(Command("technologies"))
async def cmd_technologies(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    text = "🔬 <b>ВАШИ ТЕХНОЛОГИИ:</b>\n\n"
    for tech_key, level in player["technologies"].items():
        tech = TECHNOLOGIES[tech_key]
        text += f"{tech['name']}: Ур.{level}/{tech['levels']}\n"
        text += f"   {tech['effect']}\n\n"
    
    if player["researching"]:
        text += f"\n🔬 Исследуется: {TECHNOLOGIES[player['researching']]['name']}\n"
        text += f"   Прогресс: {player['research_progress']}%"
    
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("war"))
async def cmd_war(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    if not m.reply_to_message:
        return await m.answer("⚠️ Ответьте на игрока")
    
    target_uid = m.reply_to_message.from_user.id
    target = get_player(target_uid)
    
    if target["country"] is None:
        return await m.answer("❌ У цели нет страны")
    
    if target["country"] == player["country"]:
        return await m.answer("❌ Нельзя воевать с собой")
    
    if target_uid in player["allies"]:
        return await m.answer("❌ Нельзя воевать с союзником!")
    
    if player["war_support"] < 30:
        return await m.answer("❌ Поддержка войны слишком низкая! Нужно >30%")
    
    war_cost = 100000
    if player["money"] < war_cost:
        return await m.answer(f"❌ Нужно {fmt_money(war_cost)} на войну")
    
    player["money"] -= war_cost
    player["wars"].append(target_uid)
    target["wars"].append(uid)
    
    wars_db.append({
        "attacker": uid,
        "defender": target_uid,
        "start": time.time(),
        "status": "active",
        "battles": 0
    })
    
    await m.answer(f"⚔️ <b>ВОЙНА ОБЪЯВЛЕНА!</b>\n\n"
                  f"🎯 Цель: {target['country']}\n"
                  f"💰 Потрачено: {fmt_money(war_cost)}\n\n"
                  f"Используйте /attack для атаки", parse_mode="HTML")

@dp.message(Command("attack"))
async def cmd_attack(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    if not m.reply_to_message:
        return await m.answer("⚠️ Ответьте на врага")
    
    target_uid = m.reply_to_message.from_user.id
    target = get_player(target_uid)
    
    if target_uid not in player["wars"]:
        return await m.answer("❌ Нет войны с этим игроком!")
    
    attacker_power = get_country_power(player)
    defender_power = get_country_power(target)
    
    if target["bunkers"] > 0:
        defender_power = int(defender_power * (1 + target["bunkers"] * 0.20))
    
    if player["radars"] > 0:
        attacker_power = int(attacker_power * (1 + player["radars"] * 0.10))
    
    attack_cost = 50000
    if player["money"] < attack_cost:
        return await m.answer(f"❌ Нужно {fmt_money(attack_cost)} на атаку")
    
    player["money"] -= attack_cost
    
    attacker_roll = random.randint(80, 120)
    defender_roll = random.randint(80, 120)
    
    attacker_final = attacker_power * attacker_roll / 100
    defender_final = defender_power * defender_roll / 100
    
    if attacker_final > defender_final:
        loot = int(target["money"] * 0.10)
        player["money"] += loot
        target["money"] -= loot
        target["stability"] = max(0, target["stability"] - 5)
        player["war_support"] = min(100, player["war_support"] + 2)
        
        await m.answer(f"⚔️ <b>АТАКА УСПЕШНА!</b>\n\n"
                      f"🎲 Атака: {int(attacker_final)} vs {int(defender_final)}\n"
                      f"💰 Захвачено: {fmt_money(loot)}\n"
                      f"📊 Стабильность врага: -5%\n"
                      f"⚔️ Поддержка войны: +2%", parse_mode="HTML")
    else:
        losses = int(player["money"] * 0.05)
        player["money"] -= losses
        player["stability"] = max(0, player["stability"] - 3)
        
        await m.answer(f"💥 <b>АТАКА ОТБИТА!</b>\n\n"
                      f"🎲 Атака: {int(attacker_final)} vs {int(defender_final)}\n"
                      f"💰 Потери: {fmt_money(losses)}\n"
                      f"📊 Стабильность: -3%", parse_mode="HTML")

@dp.message(Command("defend"))
async def cmd_defend(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    if not player["wars"]:
        return await m.answer("❌ Нет активных войн!")
    
    defense_bonus = 1.0 + player["bunkers"] * 0.20
    player["stability"] = min(100, player["stability"] + 2)
    
    await m.answer(f"🛡️ <b>ОБОРОНИТЕЛЬНАЯ ПОЗИЦИЯ!</b>\n\n"
                  f"🏰 Бонус обороны: +{int((defense_bonus-1)*100)}%\n"
                  f"📊 Стабильность: +2%\n"
                  f"⚔️ Готов к контратаке", parse_mode="HTML")

@dp.message(Command("peace"))
async def cmd_peace(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if not m.reply_to_message:
        return await m.answer("⚠️ Ответьте на игрока")
    
    target_uid = m.reply_to_message.from_user.id
    
    if target_uid not in player["wars"]:
        return await m.answer("❌ Нет войны с этим игроком!")
    
    player["wars"].remove(target_uid)
    target = get_player(target_uid)
    target["wars"].remove(uid)
    
    wars_db[:] = [w for w in wars_db if not ((w["attacker"] == uid and w["defender"] == target_uid) or (w["attacker"] == target_uid and w["defender"] == uid))]
    
    await m.answer("🕊️ <b>МИР ЗАКЛЮЧЁН!</b>\n\n"
                  f"Война завершена\n"
                  f"📊 Стабильность: +5%", parse_mode="HTML")
    
    player["stability"] = min(100, player["stability"] + 5)

@dp.message(Command("alliance"))
async def cmd_alliance(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    if not m.reply_to_message:
        return await m.answer("⚠️ Ответьте на игрока")
    
    target_uid = m.reply_to_message.from_user.id
    target = get_player(target_uid)
    
    if target["country"] is None:
        return await m.answer("❌ У цели нет страны")
    
    if target["country"] == player["country"]:
        return await m.answer("❌ Нельзя в союзе с собой")
    
    if target_uid in player["wars"]:
        return await m.answer("❌ Нельзя в союзе с врагом!")
    
    if target_uid in player["allies"]:
        return await m.answer("❌ Уже в союзе!")
    
    player["allies"].append(target_uid)
    target["allies"].append(uid)
    
    player["stability"] = min(100, player["stability"] + 3)
    target["stability"] = min(100, target["stability"] + 3)
    
    await m.answer(f"🤝 <b>СОЮЗ ЗАКЛЮЧЁН!</b>\n\n"
                  f"{player['country']} 🤝 {target['country']}\n\n"
                  f"📊 Стабильность: +3% (обеим странам)", parse_mode="HTML")

@dp.message(Command("diplomacy"))
async def cmd_diplomacy(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    text = f"🤝 <b>ДИПЛОМАТИЯ {player['country']}</b>\n\n"
    
    if player["allies"]:
        text += "🤝 <b>Союзы:</b>\n"
        for ally_uid in player["allies"]:
            ally = get_player(ally_uid)
            text += f"   • {ally['country']}\n"
    else:
        text += "🤝 Союзов нет\n"
    
    text += "\n"
    
    if player["wars"]:
        text += "⚔️ <b>Войны:</b>\n"
        for enemy_uid in player["wars"]:
            enemy = get_player(enemy_uid)
            text += f"   • {enemy['country']}\n"
    else:
        text += "⚔️ Войн нет\n"
    
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("trade"))
async def cmd_trade(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    if not m.reply_to_message:
        return await m.answer("⚠️ Ответьте на игрока")
    
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("⚠️ /trade [сумма]")
    
    try:
        amount = int(args[1])
    except ValueError:
        return await m.answer("❌ Число!")
    
    if amount <= 0:
        return await m.answer("❌ >0!")
    
    target_uid = m.reply_to_message.from_user.id
    target = get_player(target_uid)
    
    if target_uid in player["wars"]:
        return await m.answer("❌ Нельзя торговать с врагом!")
    
    if player["money"] < amount:
        return await m.answer(f"❌ Нужно {fmt_money(amount)}")
    
    player["money"] -= amount
    target["money"] += amount
    
    ideology = IDEOLOGIES[player["ideology"]]
    if ideology["name"] == "⚪ Нейтралитет":
        bonus = int(amount * 0.25)
        player["money"] += bonus
    
    await m.answer(f"💰 <b>ТОРГОВЛЯ ЗАВЕРШЕНА!</b>\n\n"
                  f"Переведено: {fmt_money(amount)}\n"
                  f"📊 Баланс: {fmt_money(player['money'])}", parse_mode="HTML")

@dp.message(Command("next_day"))
async def cmd_next_day(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    now = time.time()
    if now - player["last_day"] < 3600:
        hours_left = int((3600 - (now - player["last_day"])) / 60)
        return await m.answer(f"⏳ Следующий день через {hours_left} мин.")
    
    player["last_day"] = now
    player["days_played"] += 1
    
    income = get_country_income(player)
    player["money"] += income
    
    if player["researching"]:
        tech = TECHNOLOGIES[player["researching"]]
        player["research_progress"] += 10
        
        if player["research_progress"] >= 100:
            player["technologies"][player["researching"]] += 1
            player["researching"] = None
            player["research_progress"] = 0
            await m.answer(f"🔬 <b>Технология изучена!</b>\n\n"
                          f"{tech['name']} → Ур.{player['technologies'][player['researching']]}\n"
                          f"{tech['effect']}", parse_mode="HTML")
    
    if random.random() < 0.15:
        event = random.choice(EVENTS)
        player["events"].append({"name": event["name"], "day": player["days_played"], "duration": event["duration"]})
        await m.answer(f"📰 <b>СОБЫТИЕ: {event['name']}</b>\n\n"
                      f"Длительность: {event['duration']} дн.", parse_mode="HTML")
    
    active_events = [e for e in player["events"] if player["days_played"] - e["day"] < e["duration"]]
    player["events"] = active_events
    
    for event in active_events:
        if event["name"] == "📈 Экономический бум":
            player["money"] += int(income * 0.5)
        elif event["name"] == "🎉 Национальный праздник":
            player["stability"] = min(100, player["stability"] + 1)
    
    manpower_regen = int(get_manpower(player) * 0.01)
    player["manpower"] += manpower_regen
    
    await m.answer(f"📅 <b>ДЕНЬ {player['days_played']}</b>\n\n"
                  f"💰 Доход: +{fmt_money(income)}\n"
                  f"👥 Население: +{fmt_number(manpower_regen)}\n"
                  f"💰 Баланс: {fmt_money(player['money'])}\n"
                  f"📊 Стабильность: {player['stability']}%", parse_mode="HTML")

@dp.message(Command("events"))
async def cmd_events(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    active_events = [e for e in player["events"] if player["days_played"] - e["day"] < e["duration"]]
    
    if not active_events:
        return await m.answer("📰 Нет активных событий")
    
    text = "📰 <b>АКТИВНЫЕ СОБЫТИЯ:</b>\n\n"
    for event in active_events:
        days_left = event["duration"] - (player["days_played"] - event["day"])
        text += f"• {event['name']} — {days_left} дн.\n"
    
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("rating"))
async def cmd_rating(m: Message):
    sorted_players = sorted(players_db.items(), key=lambda x: x[1]["money"], reverse=True)[:10]
    
    text = "🏆 <b>ТОП ИГРОКОВ:</b>\n\n"
    for i, (uid, player) in enumerate(sorted_players, 1):
        if player["country"]:
            country = next((c for c in COUNTRIES_LIST if c["name"] == player["country"]), None)
            power = get_country_power(player)
            text += f"{i}. {country['emoji']} {player['country']} — {fmt_money(player['money'])} (сила: {fmt_number(power)})\n"
    
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("countries"))
async def cmd_countries(m: Message):
    text = "🌍 <b>СТРАНЫ:</b>\n\n"
    for country in COUNTRIES_LIST:
        players_in_country = [p for p in players_db.values() if p["country"] == country["name"]]
        text += f"{country['emoji']} <b>{country['name']}</b>\n"
        text += f"   {country['bonus']}\n"
        text += f"   Игроков: {len(players_in_country)}\n\n"
    
    await m.answer(text, parse_mode="HTML")

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
    
    target_uid = m.reply_to_message.from_user.id
    player = get_player(target_uid)
    player["money"] += amt
    
    await m.answer(f"✅ Выдано {fmt_money(amt)}")

@dp.message(Command("reset"))
async def cmd_reset(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    
    players_db.clear()
    countries_db.clear()
    wars_db.clear()
    alliances_db.clear()
    technologies_db.clear()
    events_db.clear()
    game_time_db.clear()
    
    await m.answer("✅ Игра сброшена!")

@dp.message()
async def auto_register(m: Message):
    if m.chat.type not in ['group', 'supergroup']:
        return
    get_player(m.from_user.id)

@dp.message(F.new_chat_members)
async def on_user_join(m: Message):
    cid = m.chat.id
    for user in m.new_chat_members:
        if user.is_bot:
            if user.id == int(API_TOKEN.split(':')[0]):
                await m.answer("👋 Привет! /start")
            continue
        get_player(user.id)

async def main():
    print("🤖 Hearts of Iron: Chat Edition запускается...")
    print(f"✅ Токен: {API_TOKEN[:10]}...")
    print(f"✅ ADMIN_IDS: {ADMIN_IDS}")
    print("🚀 Бот готов к войне!")
    await dp.start_polling(bot, timeout=30, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
