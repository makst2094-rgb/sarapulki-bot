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
players_db = {}  # {uid: {"country": str, "balance": int, "army": int, "industry": int, "last_country_change": float}}
countries_db = {}  # {country_name: {"leader": uid, "treasury": int, "army": int, "industry": int, "population": int}}
wars_db = []  # [{"attacker": uid, "defender": uid, "start": float, "status": str}]
alliances_db = {}  # {country: [allies]}
diplomacy_db = {}  # {(country1, country2): "relation"}

# --- СТРАНЫ ---
COUNTRIES_LIST = [
    {"name": "Россия", "emoji": "🇷🇺", "bonus": "Нефть: +20% доход", "bonus_type": "income", "bonus_value": 0.20},
    {"name": "США", "emoji": "🇺🇸", "bonus": "Технологии: -15% стоимость", "bonus_type": "cost", "bonus_value": 0.15},
    {"name": "Китай", "emoji": "🇨🇳", "bonus": "Производство: +25% армия", "bonus_type": "army", "bonus_value": 0.25},
    {"name": "Германия", "emoji": "🇩🇪", "bonus": "Промышленность: +30% доход", "bonus_type": "income", "bonus_value": 0.30},
    {"name": "Япония", "emoji": "🇯🇵", "bonus": "Флот: +20% армия", "bonus_type": "army", "bonus_value": 0.20},
    {"name": "Франция", "emoji": "🇫🇷", "bonus": "Дипломатия: +10% ко всем", "bonus_type": "all", "bonus_value": 0.10},
    {"name": "Великобритания", "emoji": "🇬🇧", "bonus": "Торговля: +15% доход", "bonus_type": "income", "bonus_value": 0.15},
    {"name": "Индия", "emoji": "🇮🇳", "bonus": "Население: +50% рекрутов", "bonus_type": "army", "bonus_value": 0.50},
]

COUNTRY_CHANGE_COOLDOWN = 30 * 86400  # 30 дней

# --- УТИЛИТЫ ---
def fmt_money(amount):
    if amount >= 1000000:
        return f"{amount/1000000:.1f}M$"
    elif amount >= 1000:
        return f"{amount/1000:.1f}K$"
    return f"{amount}$"

def get_player(uid):
    if uid not in players_db:
        players_db[uid] = {"country": None, "balance": 10000, "army": 100, "industry": 50, "last_country_change": 0}
    return players_db[uid]

def get_country(name):
    if name not in countries_db:
        countries_db[name] = {"leader": None, "treasury": 100000, "army": 500, "industry": 200, "population": 10000}
    return countries_db[name]

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
        await m.answer("🌍 <b>Добро пожаловать в геополитическую стратегию!</b>\n\nВыберите страну:\n\n⚠️ Смена страны возможна раз в 30 дней", reply_markup=keyboard, parse_mode="HTML")
    else:
        country = next((c for c in COUNTRIES_LIST if c["name"] == player["country"]), None)
        await m.answer(f"🌍 <b>Вы играете за {country['emoji']} {country['name']}</b>\n\n💰 Баланс: {fmt_money(player['balance'])}\n⚔️ Армия: {player['army']}\n🏭 Промышленность: {player['industry']}\n\n/commands - список команд", parse_mode="HTML")

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
    
    country = get_country(country_name)
    if country["leader"] is None:
        country["leader"] = uid
    
    await callback.message.edit_text(f"✅ <b>Вы выбрали {country_data['emoji']} {country_name}!</b>\n\n📊 {country_data['bonus']}\n\n💰 Начальный баланс: {fmt_money(player['balance'])}\n⚔️ Армия: {player['army']}\n🏭 Промышленность: {player['industry']}\n\n/commands - список команд", parse_mode="HTML")
    await callback.answer()

@dp.message(Command("commands"))
async def cmd_commands(m: Message):
    text = """📋 <b>КОМАНДЫ:</b>

🌍 <b>Страна:</b>
/country - инфо о стране
/change_country - сменить страну (раз в 30 дней)

💰 <b>Экономика:</b>
/balance - баланс
/work - работать (+доход)
/industry - развить промышленность (5000$)
/trade @user сумма - торговля

⚔️ <b>Армия:</b>
/army - инфо об армии
/recruit [кол-во] - нанять солдат (100$/солдат)
/war @user - объявить войну
/peace @user - заключить мир

🤝 <b>Дипломатия:</b>
/alliance @user - предложить союз
/break_alliance @user - разорвать союз
/diplomacy - список отношений

🏆 <b>Рейтинг:</b>
/rating - топ игроков
/countries - топ стран"""
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("country"))
async def cmd_country(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    country_name = player["country"]
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == country_name), None)
    country = get_country(country_name)
    
    days_since_change = int((time.time() - player["last_country_change"]) / 86400)
    days_until_change = 30 - days_since_change
    
    text = f"{country_data['emoji']} <b>{country_name}</b>\n\n"
    text += f"📊 {country_data['bonus']}\n\n"
    text += f"💰 Казна: {fmt_money(country['treasury'])}\n"
    text += f"⚔️ Армия: {country['army']}\n"
    text += f"🏭 Промышленность: {country['industry']}\n"
    text += f"👥 Население: {country['population']}\n\n"
    text += f"👤 Лидер: {'ID:' + str(country['leader']) if country['leader'] else 'ВАКАНТНО'}\n"
    text += f"⏰ Смена страны через: {days_until_change} дн."
    
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
    
    country = get_country(country_name)
    if country["leader"] is None:
        country["leader"] = uid
    
    await callback.message.edit_text(f"✅ <b>Вы сменили страну на {country_data['emoji']} {country_name}!</b>\n\n📊 {country_data['bonus']}", parse_mode="HTML")
    await callback.answer()

@dp.message(Command("balance"))
async def cmd_balance(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    country = next((c for c in COUNTRIES_LIST if c["name"] == player["country"]), None)
    await m.answer(f"💰 <b>Баланс:</b> {fmt_money(player['balance'])}\n\n{country['emoji']} {country['name']}", parse_mode="HTML")

@dp.message(Command("work"))
async def cmd_work(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    country_name = player["country"]
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == country_name), None)
    
    base_income = 1000
    bonus = 1.0
    
    if country_data["bonus_type"] == "income":
        bonus += country_data["bonus_value"]
    elif country_data["bonus_type"] == "all":
        bonus += country_data["bonus_value"]
    
    income = int(base_income * bonus * (1 + player["industry"] / 100))
    player["balance"] += income
    
    await m.answer(f"💼 <b>Вы заработали {fmt_money(income)}</b>\n\n💰 Баланс: {fmt_money(player['balance'])}", parse_mode="HTML")

@dp.message(Command("industry"))
async def cmd_industry(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    country_name = player["country"]
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == country_name), None)
    
    cost = 5000
    if country_data["bonus_type"] == "cost":
        cost = int(cost * (1 - country_data["bonus_value"]))
    
    if player["balance"] < cost:
        return await m.answer(f"❌ Нужно {fmt_money(cost)}")
    
    player["balance"] -= cost
    player["industry"] += 10
    
    country = get_country(country_name)
    country["industry"] += 10
    
    await m.answer(f"🏭 <b>Промышленность развита!</b>\n\n📊 Уровень: {player['industry']}\n💰 Потрачено: {fmt_money(cost)}", parse_mode="HTML")

@dp.message(Command("army"))
async def cmd_army(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    await m.answer(f"⚔️ <b>Армия:</b> {player['army']} солдат\n\n💰 Стоимость рекрута: 100$/солдат\n/recruit [кол-во]", parse_mode="HTML")

@dp.message(Command("recruit"))
async def cmd_recruit(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    args = m.text.split()
    if len(args) < 2:
        return await m.answer("⚠️ /recruit [кол-во]")
    
    try:
        count = int(args[1])
    except ValueError:
        return await m.answer("❌ Число!")
    
    if count <= 0:
        return await m.answer("❌ >0!")
    
    cost = count * 100
    country_name = player["country"]
    country_data = next((c for c in COUNTRIES_LIST if c["name"] == country_name), None)
    
    if country_data["bonus_type"] == "army":
        count = int(count * (1 + country_data["bonus_value"]))
    
    if player["balance"] < cost:
        return await m.answer(f"❌ Нужно {fmt_money(cost)}")
    
    player["balance"] -= cost
    player["army"] += count
    
    country = get_country(country_name)
    country["army"] += count
    
    await m.answer(f"⚔️ <b>Нанято {count} солдат!</b>\n\n💰 Потрачено: {fmt_money(cost)}\n🪖 Всего: {player['army']}", parse_mode="HTML")

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
    
    if player["army"] < 50:
        return await m.answer("❌ Нужно минимум 50 солдат")
    
    war_cost = 10000
    if player["balance"] < war_cost:
        return await m.answer(f"❌ Нужно {fmt_money(war_cost)} на войну")
    
    player["balance"] -= war_cost
    wars_db.append({"attacker": uid, "defender": target_uid, "start": time.time(), "status": "active"})
    
    await m.answer(f"⚔️ <b>ВОЙНА ОБЪЯВЛЕНА!</b>\n\n🎯 Цель: {target['country']}\n💰 Потрачено: {fmt_money(war_cost)}\n\nИтог через 24 часа", parse_mode="HTML")

@dp.message(Command("peace"))
async def cmd_peace(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if not m.reply_to_message:
        return await m.answer("⚠️ Ответьте на игрока")
    
    target_uid = m.reply_to_message.from_user.id
    
    war = next((w for w in wars_db if (w["attacker"] == uid and w["defender"] == target_uid) or (w["attacker"] == target_uid and w["defender"] == uid) and w["status"] == "active"), None)
    
    if not war:
        return await m.answer("❌ Нет активной войны")
    
    war["status"] = "peace"
    await m.answer("🕊️ <b>МИР ЗАКЛЮЧЁН!</b>", parse_mode="HTML")

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
    
    key = (player["country"], target["country"])
    diplomacy_db[key] = "alliance"
    
    await m.answer(f"🤝 <b>СОЮЗ ЗАКЛЮЧЁН!</b>\n\n{player['country']} 🤝 {target['country']}", parse_mode="HTML")

@dp.message(Command("break_alliance"))
async def cmd_break_alliance(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if not m.reply_to_message:
        return await m.answer("⚠️ Ответьте на игрока")
    
    target_uid = m.reply_to_message.from_user.id
    target = get_player(target_uid)
    
    key = (player["country"], target["country"])
    if key in diplomacy_db:
        del diplomacy_db[key]
        await m.answer("💔 <b>СОЮЗ РАЗОРВАН!</b>", parse_mode="HTML")
    else:
        await m.answer("❌ Нет союза")

@dp.message(Command("diplomacy"))
async def cmd_diplomacy(m: Message):
    uid = m.from_user.id
    player = get_player(uid)
    
    if player["country"] is None:
        return await m.answer("❌ Сначала выберите страну: /start")
    
    text = f"🤝 <b>Дипломатия {player['country']}</b>\n\n"
    
    alliances = []
    for (c1, c2), relation in diplomacy_db.items():
        if c1 == player["country"] and relation == "alliance":
            alliances.append(c2)
        elif c2 == player["country"] and relation == "alliance":
            alliances.append(c1)
    
    if alliances:
        text += "Союзы:\n" + "\n".join([f"• {a}" for a in alliances])
    else:
        text += "Нет союзов"
    
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("rating"))
async def cmd_rating(m: Message):
    sorted_players = sorted(players_db.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
    
    text = "🏆 <b>Топ игроков:</b>\n\n"
    for i, (uid, player) in enumerate(sorted_players, 1):
        if player["country"]:
            country = next((c for c in COUNTRIES_LIST if c["name"] == player["country"]), None)
            text += f"{i}. {country['emoji']} {player['country']} — {fmt_money(player['balance'])}\n"
    
    await m.answer(text, parse_mode="HTML")

@dp.message(Command("countries"))
async def cmd_countries(m: Message):
    text = "🌍 <b>Страны:</b>\n\n"
    for country_name, country in countries_db.items():
        country_data = next((c for c in COUNTRIES_LIST if c["name"] == country_name), None)
        if country_data:
            leader_name = f"ID:{country['leader']}" if country['leader'] else "ВАКАНТНО"
            text += f"{country_data['emoji']} <b>{country_name}</b>\n   Казна: {fmt_money(country['treasury'])}\n   Армия: {country['army']}\n   Лидер: {leader_name}\n\n"
    
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
    player["balance"] += amt
    
    await m.answer(f"✅ Выдано {fmt_money(amt)}")

# --- АВТО-РЕГИСТРАЦИЯ ---
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

# --- ГЛАВНАЯ ФУНКЦИЯ ---
async def main():
    print("🤖 Бот запускается...")
    print(f"✅ Токен: {API_TOKEN[:10]}...")
    print(f"✅ ADMIN_IDS: {ADMIN_IDS}")
    print("🚀 Бот готов к работе!")
    await dp.start_polling(bot, timeout=30, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
