import asyncio
import logging
import random
import time
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

API_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",") if x.strip().isdigit()]

if not API_TOKEN:
    raise ValueError("BOT_TOKEN не установлен!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==================== ХРАНИЛИЩЕ ====================
players = {}       # uid -> state
countries_state = {}  # country_name -> state
wars = {}          # war_id -> state
game_events = {}   # uid -> list of events
tick_count = 0

# ==================== СТРАНЫ ====================
COUNTRIES = {
    "Германия":   {"emoji":"🇩🇪","color":"gray","manpower":68,"industry":90,"stability":80,"ideology":"fascism","bonus":"army_power","bonus_val":0.15},
    "СССР":       {"emoji":"🇷🇺","color":"red","manpower":196,"industry":85,"stability":75,"ideology":"communism","bonus":"manpower","bonus_val":0.20},
    "США":        {"emoji":"🇺🇸","color":"blue","manpower":132,"industry":100,"stability":90,"ideology":"democracy","bonus":"industry","bonus_val":0.20},
    "Великобритания":{"emoji":"🇬🇧","color":"blue","manpower":45,"industry":70,"stability":85,"ideology":"democracy","bonus":"navy","bonus_val":0.20},
    "Франция":    {"emoji":"🇫🇷","color":"blue","manpower":40,"industry":60,"stability":70,"ideology":"democracy","bonus":"defense","bonus_val":0.15},
    "Япония":     {"emoji":"🇯🇵","color":"red","manpower":72,"industry":65,"stability":75,"ideology":"fascism","bonus":"navy","bonus_val":0.20},
    "Италия":     {"emoji":"🇮🇹","color":"green","manpower":43,"industry":50,"stability":65,"ideology":"fascism","bonus":"morale","bonus_val":0.10},
    "Китай":      {"emoji":"🇨🇳","color":"red","manpower":470,"industry":40,"stability":60,"ideology":"communism","bonus":"manpower","bonus_val":0.30},
    "Польша":     {"emoji":"🇵🇱","color":"white","manpower":35,"industry":45,"stability":70,"ideology":"democracy","bonus":"defense","bonus_val":0.10},
    "Канада":     {"emoji":"🇨🇦","color":"red","manpower":11,"industry":55,"stability":90,"ideology":"democracy","bonus":"industry","bonus_val":0.10},
}

IDEOLOGIES = {
    "democracy":{"name":"🗳️ Демократия","stability":1.1,"war_support":0.7},
    "fascism":{"name":"⚫ Фашизм","stability":0.9,"war_support":1.3},
    "communism":{"name":"☭ Коммунизм","stability":1.0,"war_support":1.0},
}

TECHS = {
    "infantry":{"name":"🪖 Пехота","max":5,"cost":5000},
    "armor":{"name":"🛡️ Танки","max":5,"cost":12000},
    "air":{"name":"✈️ Авиация","max":5,"cost":15000},
    "navy":{"name":"⚓ Флот","max":5,"cost":18000},
    "industry_t":{"name":"🏭 Промышленность","max":5,"cost":8000},
    "research":{"name":"🔬 Наука","max":5,"cost":6000},
}

UNITS = {
    "infantry":{"name":"🪖 Пехота","cost":100,"power":1,"mp":1},
    "armor":{"name":"🛡️ Танк","cost":500,"power":5,"mp":0.5},
    "artillery":{"name":"💥 Артиллерия","cost":300,"power":3,"mp":0.8},
    "plane":{"name":"✈️ Самолёт","cost":800,"power":6,"mp":0.2},
    "ship":{"name":"⚓ Корабль","cost":1200,"power":8,"mp":1.5},
}

BUILDINGS = {
    "factory":{"name":"🏭 Фабрика","cost":10000,"effect":"+500 CIV/день"},
    "dockyard":{"name":"🚢 Верфь","cost":15000,"effect":"+300 CIV/день, +флот"},
    "airbase":{"name":"✈️ Аэродром","cost":12000,"effect":"+200 CIV/день, +авиа"},
    "bunker":{"name":"🏰 Бункер","cost":20000,"effect":"+20% оборона"},
    "radar":{"name":"📡 Радар","cost":8000,"effect":"+10% разведка"},
    "infrastructure":{"name":"🛤️ Инфраструктура","cost":5000,"effect":"+5% логистика"},
}

# ==================== УТИЛИТЫ ====================
def fmt(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(int(n))

def get_player(uid):
    if uid not in players:
        players[uid] = {
            "country": None,
            "civilian": 100000,
            "manpower": 500000,
            "stability": 80,
            "war_support": 50,
            "army": {"infantry":50,"armor":5,"artillery":10,"plane":3,"ship":1},
            "techs": {k:0 for k in TECHS},
            "buildings": {k:0 for k in BUILDINGS},
            "researching": None,
            "research_days": 0,
            "last_country_change": 0,
            "wars": [],
            "allies": [],
            "enemies": [],
            "events": [],
            "last_tick": time.time(),
            "days": 0,
            "name": "Игрок",
        }
    return players[uid]

def get_country(name):
    if name not in countries_state:
        c = COUNTRIES[name]
        countries_state[name] = {
            "owner": None,
            "civ": 500000,
            "mp": c["manpower"]*1000000,
            "industry": c["industry"],
            "stability": c["stability"],
            "ideology": c["ideology"],
            "army": {"infantry":100,"armor":10,"artillery":20,"plane":5,"ship":2},
            "techs": {k:1 for k in TECHS},
            "buildings": {k:2 for k in BUILDINGS},
            "wars": [],
            "allies": [],
        }
    return countries_state[name]

def army_power(p):
    power = 0
    for u, cnt in p["army"].items():
        power += cnt * UNITS[u]["power"]
    tech_mult = 1.0
    for t, lvl in p["techs"].items():
        if t in ("infantry","armor","air","navy"):
            tech_mult += lvl * 0.10
    c = COUNTRIES.get(p["country"]) if p["country"] else None
    if c and c["bonus"] == "army_power":
        tech_mult += c["bonus_val"]
    return int(power * tech_mult)

def daily_income(p):
    base = 1000 + p["buildings"]["factory"]*500 + p["buildings"]["dockyard"]*300 + p["buildings"]["airbase"]*200
    tech_mult = 1 + p["techs"]["industry_t"]*0.10
    c = COUNTRIES.get(p["country"]) if p["country"] else None
    if c and c["bonus"] == "industry":
        tech_mult += c["bonus_val"]
    stab = p["stability"]/100
    return int(base * tech_mult * stab)

# ==================== КОМАНДЫ ====================
@dp.message(Command("start"))
async def cmd_start(m: Message):
    p = get_player(m.from_user.id)
    p["name"] = m.from_user.full_name
    if p["country"] is None:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{c['emoji']} {name}", callback_data=f"pick_{name}")]
            for name, c in list(COUNTRIES.items())[:5]
        ] + [
            [InlineKeyboardButton(text=f"{c['emoji']} {name}", callback_data=f"pick_{name}")]
            for name, c in list(COUNTRIES.items())[5:10]
        ])
        await m.answer(
            "🌍 <b>HEARTS OF IRON: CHAT EDITION</b>\n\n"
            "Выбери страну. Смена — раз в 30 дней.\n"
            "⚠️ После выбора — /help",
            reply_markup=kb, parse_mode="HTML")
    else:
        await cmd_country(m)

@dp.callback_query(lambda c: c.data.startswith("pick_"))
async def cb_pick(cb: CallbackQuery):
    uid = cb.from_user.id
    name = cb.data.replace("pick_","")
    p = get_player(uid)
    now = time.time()
    if p["country"] and now - p["last_country_change"] < 30*86400:
        d = int((30*86400 - (now - p["last_country_change"]))/86400)
        return await cb.answer(f"Смена через {d} дн.", show_alert=True)
    p["country"] = name
    p["last_country_change"] = now
    p["manpower"] = COUNTRIES[name]["manpower"]*100000
    p["stability"] = COUNTRIES[name]["stability"]
    c = get_country(name)
    c["owner"] = uid
    await cb.message.edit_text(
        f"✅ {COUNTRIES[name]['emoji']} <b>{name}</b>\n"
        f"📊 {COUNTRIES[name]['bonus']}: +{int(COUNTRIES[name]['bonus_val']*100)}%\n\n"
        f"👥 Население: {fmt(p['manpower'])}\n"
        f"💰 Гражданские: {fmt(p['civilian'])}\n\n"
        f"Используй /help", parse_mode="HTML")
    await cb.answer()

@dp.message(Command("help"))
async def cmd_help(m: Message):
    await m.answer(
        "📋 <b>КОМАНДЫ HOI</b>\n\n"
        "🌍 <b>Страна:</b>\n"
        "/country — статус\n/change — сменить страну\n/ideology [democracy|fascism|communism]\n\n"
        "💰 <b>Экономика:</b>\n"
        "/build [factory|dockyard|airbase|bunker|radar|infrastructure]\n/buildings — мои здания\n\n"
        "⚔️ <b>Армия:</b>\n"
        "/recruit [тип] [кол-во]\n/army — мои войска\n/attack @user — атака\n/defend — оборона\n\n"
        "🔬 <b>Наука:</b>\n"
        "/research [tech]\n/techs — технологии\n\n"
        "🤝 <b>Дипломатия:</b>\n"
        "/war @user — объявить войну\n/peace @user — мир\n/alliance @user — союз\n/diplomacy\n\n"
        "📅 <b>Время:</b>\n/next_day — следующий день\n/events — события\n\n"
        "🏆 <b>Рейтинг:</b>\n/rating — топ игроков\n/countries — все страны",
        parse_mode="HTML")

@dp.message(Command("country"))
async def cmd_country(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]:
        return await m.answer("❌ /start сначала")
    c = COUNTRIES[p["country"]]
    idg = IDEOLOGIES[c["ideology"]]
    pw = army_power(p)
    inc = daily_income(p)
    res = ""
    if p["researching"]:
        res = f"\n🔬 Идёт: {TECHS[p['researching']]['name']} ({p['research_days']}/5 дн)"
    txt = (f"{c['emoji']} <b>{p['country']}</b>\n"
           f"🏛️ {idg['name']}\n\n"
           f"💰 CIV: {fmt(p['civilian'])}\n"
           f"👥 MP: {fmt(p['manpower'])}\n"
           f"📊 Стабильность: {p['stability']}%\n"
           f"⚔️ Поддержка войны: {p['war_support']}%\n"
           f"🏭 Фабрик: {p['buildings']['factory']}\n\n"
           f"⚔️ Сила армии: {fmt(pw)}\n"
           f"💵 Доход/день: {fmt(inc)}\n"
           f"📅 Дней: {p['days']}{res}\n\n"
           f"🤝 Союзы: {len(p['allies'])} | ⚔️ Войны: {len(p['wars'])}")
    await m.answer(txt, parse_mode="HTML")

@dp.message(Command("recruit"))
async def cmd_recruit(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    args = m.text.split()
    if len(args) < 3:
        txt = "⚔️ <b>Юниты:</b>\n"
        for k,v in UNITS.items():
            txt += f"• {v['name']} — {v['cost']}$ (сила {v['power']})\n"
        txt += "\n/recruit [тип] [кол-во]"
        return await m.answer(txt, parse_mode="HTML")
    ut = args[1]
    if ut not in UNITS: return await m.answer("❌ Тип не найден")
    try: cnt = int(args[2])
    except: return await m.answer("❌ Число")
    u = UNITS[ut]
    cost = u["cost"]*cnt
    mp = u["mp"]*cnt
    if p["civilian"] < cost: return await m.answer(f"❌ Нужно {fmt(cost)} CIV")
    if p["manpower"] < mp*1000: return await m.answer(f"❌ Нужно {fmt(mp*1000)} MP")
    p["civilian"] -= cost
    p["manpower"] -= mp*1000
    p["army"][ut] += cnt
    await m.answer(f"⚔️ Нанято {cnt} {u['name']}\n💸 -{fmt(cost)} | 👥 -{fmt(mp*1000)}")

@dp.message(Command("army"))
async def cmd_army(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    txt = "⚔️ <b>Армия:</b>\n\n"
    for u, cnt in p["army"].items():
        txt += f"{UNITS[u]['name']}: {cnt} (сила {cnt*UNITS[u]['power']})\n"
    txt += f"\n💪 Общая сила: {fmt(army_power(p))}"
    await m.answer(txt, parse_mode="HTML")

@dp.message(Command("build"))
async def cmd_build(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    args = m.text.split()
    if len(args) < 2:
        txt = "🏗️ <b>Здания:</b>\n"
        for k,v in BUILDINGS.items():
            txt += f"• {v['name']} — {fmt(v['cost'])} ({v['effect']})\n"
        txt += "\n/build [ключ]"
        return await m.answer(txt, parse_mode="HTML")
    b = args[1]
    if b not in BUILDINGS: return await m.answer("❌ Не найдено")
    cost = BUILDINGS[b]["cost"]
    if p["civilian"] < cost: return await m.answer(f"❌ Нужно {fmt(cost)}")
    p["civilian"] -= cost
    p["buildings"][b] += 1
    await m.answer(f"🏗️ Построено {BUILDINGS[b]['name']} (всего {p['buildings'][b]})\n{BUILDINGS[b]['effect']}")

@dp.message(Command("buildings"))
async def cmd_buildings(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    txt = "🏗️ <b>Здания:</b>\n\n"
    for k,v in p["buildings"].items():
        txt += f"{BUILDINGS[k]['name']}: {v}\n"
    txt += f"\n💵 Доход/день: {fmt(daily_income(p))}"
    await m.answer(txt, parse_mode="HTML")

@dp.message(Command("research"))
async def cmd_research(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    if p["researching"]: return await m.answer(f"⏳ Идёт: {TECHS[p['researching']]['name']}")
    args = m.text.split()
    if len(args) < 2:
        txt = "🔬 <b>Технологии:</b>\n"
        for k,v in TECHS.items():
            cur = p["techs"][k]
            txt += f"• {v['name']} — Ур.{cur}/{v['max']} ({fmt(v['cost'])})\n"
        txt += "\n/research [ключ]"
        return await m.answer(txt, parse_mode="HTML")
    t = args[1]
    if t not in TECHS: return await m.answer("❌ Не найдено")
    if p["techs"][t] >= TECHS[t]["max"]: return await m.answer("✅ Максимум")
    cost = TECHS[t]["cost"] * (p["techs"][t]+1)
    if p["civilian"] < cost: return await m.answer(f"❌ Нужно {fmt(cost)}")
    p["civilian"] -= cost
    p["researching"] = t
    p["research_days"] = 0
    await m.answer(f"🔬 Начато: {TECHS[t]['name']}\n⏳ 5 дней")

@dp.message(Command("techs"))
async def cmd_techs(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    txt = "🔬 <b>Технологии:</b>\n\n"
    for k,v in TECHS.items():
        txt += f"{v['name']}: Ур.{p['techs'][k]}/{v['max']}\n"
    if p["researching"]:
        txt += f"\n⏳ Идёт: {TECHS[p['researching']]['name']} ({p['research_days']}/5)"
    await m.answer(txt, parse_mode="HTML")

@dp.message(Command("war"))
async def cmd_war(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    if not m.reply_to_message: return await m.answer("⚠️ Ответь на врага")
    tid = m.reply_to_message.from_user.id
    t = get_player(tid)
    if not t["country"]: return await m.answer("❌ У цели нет страны")
    if t["country"] == p["country"]: return await m.answer("❌ Соотечественники")
    if tid in p["allies"]: return await m.answer("❌ Союзник!")
    if p["war_support"] < 30: return await m.answer("❌ Низкая поддержка войны")
    cost = 50000
    if p["civilian"] < cost: return await m.answer(f"❌ Нужно {fmt(cost)}")
    p["civilian"] -= cost
    wid = f"{min(m.from_user.id,tid)}_{max(m.from_user.id,tid)}"
    wars[wid] = {"a":m.from_user.id,"b":tid,"day":0,"status":"active"}
    p["wars"].append(tid); t["wars"].append(m.from_user.id)
    await m.answer(f"⚔️ <b>ВОЙНА ОБЪЯВЛЕНА!</b>\n{p['country']} vs {t['country']}\n💸 -{fmt(cost)}\n\n/attack @user")

@dp.message(Command("attack"))
async def cmd_attack(m: Message):
    p = get_player(m.from_user.id)
    if not m.reply_to_message: return await m.answer("⚠️ Ответь на врага")
    tid = m.reply_to_message.from_user.id
    if tid not in p["wars"]: return await m.answer("❌ Нет войны")
    t = get_player(tid)
    ap = army_power(p); dp_ = army_power(t)
    bunk = 1 + t["buildings"]["bunker"]*0.20
    dp_ = int(dp_ * bunk)
    rad = 1 + p["buildings"]["radar"]*0.10
    ap = int(ap * rad)
    cost = 20000
    if p["civilian"] < cost: return await m.answer(f"❌ Нужно {fmt(cost)}")
    p["civilian"] -= cost
    roll_a = random.uniform(0.8,1.2); roll_d = random.uniform(0.8,1.2)
    fa = ap*roll_a; fd = dp_*roll_d
    if fa > fd:
        loot = int(t["civilian"]*0.15)
        p["civilian"] += loot; t["civilian"] -= loot
        t["stability"] = max(0, t["stability"]-5)
        p["war_support"] = min(100, p["war_support"]+3)
        await m.answer(f"🎯 <b>АТАКА УСПЕШНА!</b>\n{int(fa)} vs {int(fd)}\n💰 Захвачено: {fmt(loot)}\n📉 Враг стабильность -5")
    else:
        loss = int(p["civilian"]*0.05)
        p["civilian"] -= loss
        p["stability"] = max(0, p["stability"]-3)
        await m.answer(f"💥 <b>АТАКА ОТБИТА!</b>\n{int(fa)} vs {int(fd)}\n💸 Потери: {fmt(loss)}\n📉 Стабильность -3")

@dp.message(Command("peace"))
async def cmd_peace(m: Message):
    p = get_player(m.from_user.id)
    if not m.reply_to_message: return await m.answer("⚠️ Ответь на врага")
    tid = m.reply_to_message.from_user.id
    if tid not in p["wars"]: return await m.answer("❌ Нет войны")
    p["wars"].remove(tid)
    t = get_player(tid)
    if m.from_user.id in t["wars"]: t["wars"].remove(m.from_user.id)
    wid = f"{min(m.from_user.id,tid)}_{max(m.from_user.id,tid)}"
    if wid in wars: wars[wid]["status"] = "peace"
    p["stability"] = min(100, p["stability"]+5)
    await m.answer("🕊️ <b>МИР ЗАКЛЮЧЁН!</b>\n📊 Стабильность +5")

@dp.message(Command("alliance"))
async def cmd_alliance(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    if not m.reply_to_message: return await m.answer("⚠️ Ответь на игрока")
    tid = m.reply_to_message.from_user.id
    t = get_player(tid)
    if not t["country"]: return await m.answer("❌ У цели нет страны")
    if tid in p["wars"]: return await m.answer("❌ Враг!")
    if tid in p["allies"]: return await m.answer("❌ Уже союз")
    p["allies"].append(tid); t["allies"].append(m.from_user.id)
    p["stability"] = min(100, p["stability"]+3)
    t["stability"] = min(100, t["stability"]+3)
    await m.answer(f"🤝 <b>СОЮЗ!</b>\n{p['country']} + {t['country']}\n📊 +3% стабильности")

@dp.message(Command("diplomacy"))
async def cmd_diplomacy(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    txt = f"🤝 <b>Дипломатия {p['country']}</b>\n\n"
    txt += "🤝 Союзы:\n" if p["allies"] else "🤝 Союзов нет\n"
    for a in p["allies"]:
        ap = get_player(a)
        if ap["country"]: txt += f"• {ap['country']}\n"
    txt += "\n⚔️ Войны:\n" if p["wars"] else "⚔️ Войн нет"
    for w in p["wars"]:
        wp = get_player(w)
        if wp["country"]: txt += f"• {wp['country']}\n"
    await m.answer(txt, parse_mode="HTML")

@dp.message(Command("ideology"))
async def cmd_ideology(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    args = m.text.split()
    if len(args) < 2:
        txt = "🏛️ <b>Идеологии:</b>\n"
        for k,v in IDEOLOGIES.items():
            txt += f"• {v['name']} — стаб {int(v['stability']*100)}%, война {int(v['war_support']*100)}%\n"
        return await m.answer(txt, parse_mode="HTML")
    i = args[1]
    if i not in IDEOLOGIES: return await m.answer("❌ Не найдено")
    cost = 30000
    if p["civilian"] < cost: return await m.answer(f"❌ Нужно {fmt(cost)}")
    p["civilian"] -= cost
    p["stability"] = int(100 * IDEOLOGIES[i]["stability"])
    p["war_support"] = int(50 * IDEOLOGIES[i]["war_support"])
    await m.answer(f"🏛️ Идеология: {IDEOLOGIES[i]['name']}\n📊 Стаб: {p['stability']}% | Война: {p['war_support']}%")

@dp.message(Command("next_day"))
async def cmd_next_day(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    now = time.time()
    if now - p["last_tick"] < 300:
        return await m.answer(f"⏳ Ещё {int(300-(now-p['last_tick']))} сек")
    p["last_tick"] = now
    p["days"] += 1
    inc = daily_income(p)
    p["civilian"] += inc
    regen = int(p["manpower"]*0.01)
    p["manpower"] += regen
    res_txt = ""
    if p["researching"]:
        p["research_days"] += 1
        if p["research_days"] >= 5:
            p["techs"][p["researching"]] += 1
            res_txt = f"\n🔬 <b>Изучено: {TECHS[p['researching']]['name']}</b>"
            p["researching"] = None
            p["research_days"] = 0
    evt_txt = ""
    if random.random() < 0.12:
        ev = random.choice([
            ("📈 Экономический бум", 5000),
            ("🎉 Национальный праздник", 0),
            ("⚠️ Забастовка", -3000),
            ("🌾 Хороший урожай", 2000),
            ("🔥 Пожар на фабрике", -5000),
        ])
        p["civilian"] += ev[1]
        evt_txt = f"\n📰 <b>{ev[0]}</b> ({'+' if ev[1]>=0 else ''}{fmt(ev[1])})"
    await m.answer(
        f"📅 <b>День {p['days']}</b>\n"
        f"💵 +{fmt(inc)} CIV\n"
        f"👥 +{fmt(regen)} MP\n"
        f"💰 Баланс: {fmt(p['civilian'])}\n"
        f"📊 Стаб: {p['stability']}%{res_txt}{evt_txt}", parse_mode="HTML")

@dp.message(Command("events"))
async def cmd_events(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    txt = f"📰 <b>События {p['country']}</b>\n\n"
    if p["wars"]:
        txt += f"⚔️ Войны: {len(p['wars'])}\n"
    if p["allies"]:
        txt += f"🤝 Союзы: {len(p['allies'])}\n"
    txt += f"📅 День: {p['days']}\n"
    txt += f"🔬 Исследование: {TECHS[p['researching']]['name'] if p['researching'] else 'нет'}"
    await m.answer(txt, parse_mode="HTML")

@dp.message(Command("rating"))
async def cmd_rating(m: Message):
    top = sorted([p for p in players.values() if p["country"]], key=lambda x: x["civilian"], reverse=True)[:10]
    txt = "🏆 <b>ТОП ИГРОКОВ:</b>\n\n"
    for i, p in enumerate(top, 1):
        medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
        c = COUNTRIES[p["country"]]
        txt += f"{medal} {c['emoji']} {p['country']} — {fmt(p['civilian'])} CIV (сила {fmt(army_power(p))})\n"
    await m.answer(txt, parse_mode="HTML")

@dp.message(Command("countries"))
async def cmd_countries(m: Message):
    txt = "🌍 <b>СТРАНЫ:</b>\n\n"
    for name, c in COUNTRIES.items():
        cs = get_country(name)
        owner = cs["owner"]
        owner_str = f"👤 {players[owner]['name']}" if owner and owner in players else "🏜️ Свободна"
        txt += f"{c['emoji']} <b>{name}</b> — {owner_str}\n"
    await m.answer(txt, parse_mode="HTML")

@dp.message(Command("change"))
async def cmd_change(m: Message):
    p = get_player(m.from_user.id)
    if not p["country"]: return await m.answer("❌ /start")
    now = time.time()
    if now - p["last_country_change"] < 30*86400:
        d = int((30*86400 - (now - p["last_country_change"]))/86400)
        return await m.answer(f"⏳ Смена через {d} дн.")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{c['emoji']} {name}", callback_data=f"pick_{name}")]
        for name, c in list(COUNTRIES.items())[:5]
    ] + [
        [InlineKeyboardButton(text=f"{c['emoji']} {name}", callback_data=f"pick_{name}")]
        for name, c in list(COUNTRIES.items())[5:10]
    ])
    await m.answer("🌍 Новая страна:", reply_markup=kb, parse_mode="HTML")

@dp.message(Command("give"))
async def cmd_give(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    args = m.text.split()
    if len(args) < 2 or not m.reply_to_message: return await m.answer("/give сумма")
    try: amt = int(args[1])
    except: return
    p = get_player(m.reply_to_message.from_user.id)
    p["civilian"] += amt
    await m.answer(f"✅ +{fmt(amt)} CIV")

@dp.message(Command("reset"))
async def cmd_reset(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    players.clear(); countries_state.clear(); wars.clear()
    await m.answer("✅ Игра сброшена")

@dp.message(F.new_chat_members)
async def on_join(m: Message):
    for u in m.new_chat_members:
        if u.is_bot:
            if u.id == await bot.get_me() and False: pass
            continue
        get_player(u.id)
    await m.answer("🌍 <b>HOI CHAT</b> — напиши /start", parse_mode="HTML")

# ==================== WEB SERVER (для Render) ====================
async def handle_ping(req):
    return web.Response(text="🤖 HOI Bot alive")

async def start_web():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"🌐 Web on port {port}")

# ==================== MAIN ====================
async def main():
    # ⚠️ ВАЖНО: удаляем webhook, чтобы polling работал
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.get_me()
    print(f"✅ Бот: @{me.username} (id={me.id})")
    print(f"✅ ADMIN_IDS: {ADMIN_IDS}")
    await start_web()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
