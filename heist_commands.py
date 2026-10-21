import random
import time
from aiogram import types
from aiogram.types import Message

# Словари (дублируем здесь, чтобы файл был независимым)
BANK_TYPES = {
    "local": {"name": " Местный банк", "reward": 5000, "chance": 70, "min_players": 2, "max_players": 3, "jail_hours": 4, "fee": 5000},
    "city": {"name": "🏛️ Городской банк", "reward": 20000, "chance": 50, "min_players": 3, "max_players": 4, "jail_hours": 6, "fee": 10000},
    "central": {"name": " Центральный банк", "reward": 100000, "chance": 30, "min_players": 4, "max_players": 5, "jail_hours": 8, "fee": 25000},
    "swiss": {"name": "🇨 Швейцарский банк", "reward": 500000, "chance": 15, "min_players": 5, "max_players": 5, "jail_hours": 12, "fee": 50000}
}

UPGRADES = {
    "weapon": {"name": "🔫 Оружие", "price": 5000, "bonus": 20},
    "car": {"name": "🚗 Машина", "price": 3000, "cooldown": 3600},
    "explosives": {"name": "💣 Взрывчатка", "price": 7000, "reward_bonus": 30},
    "masks": {"name": " Маски", "price": 2000, "jail_reduce": 2}
}

def register_heist_commands(dp, pool, update_balance, fmt_money):
    """Регистрирует все команды ограблений"""
    
    @dp.message(lambda m: m.text and m.text.startswith("/bank_heist"))
    async def cmd_bank_heist(m: Message):
        try:
            print("🔥 КОМАНДА /bank_heist ВЫЗВАНА 🔥")
            t = "🏦 <b>ОГРАБЛЕНИЯ БАНКОВ</b>\n\n"
            t += "📋 <b>Доступные банки:</b>\n\n"
            for key, bank in BANK_TYPES.items():
                t += f"{bank['name']}\n"
                t += f"   💰 Награда: {fmt_money(bank['reward'])}\n"
                t += f"   🎯 Шанс успеха: {bank['chance']}%\n"
                t += f"   👥 Игроков: {bank['min_players']}-{bank['max_players']}\n"
                t += f"   🔒 Тюрьма при провале: {bank['jail_hours']}ч\n"
                t += f"   💵 Взнос: {fmt_money(bank['fee'])}\n"
                t += f"   🛒 Создать: /create_heist {key}\n\n"
            t += "━━━━━━━━━━━━━━━━━━━━\n"
            t += "🎒 <b>Улучшения:</b>\n"
            for key, upg in UPGRADES.items():
                t += f"   {upg['name']} — {fmt_money(upg['price'])}\n\n"
            t += "💡 <b>Как играть:</b>\n"
            t += "1. Ответь на сообщение игрока\n"
            t += "2. Напиши /create_heist local\n"
            t += "3. Купи улучшения: /buy_upgrade weapon\n"
            t += "4. Начни ограбление: /start_heist"
            await m.answer(t, parse_mode="HTML")
        except Exception as e:
            print(f"❌ Ошибка в /bank_heist: {e}")
            await m.answer(f"❌ Ошибка: {str(e)}")
    
    print("✅ Команды ограблений зарегистрированы")
