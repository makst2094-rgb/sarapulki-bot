import random
import time
from aiogram.types import Message

BANKS = {
    "local": {"name": "🏦 Местный банк", "reward": 5000, "chance": 70, "min": 2, "max": 3, "jail": 4, "fee": 5000},
    "city": {"name": "🏛️ Городской банк", "reward": 20000, "chance": 50, "min": 3, "max": 4, "jail": 6, "fee": 10000},
    "central": {"name": "🏢 Центральный банк", "reward": 100000, "chance": 30, "min": 4, "max": 5, "jail": 8, "fee": 25000},
    "swiss": {"name": "🇨🇭 Швейцарский банк", "reward": 500000, "chance": 15, "min": 5, "max": 5, "jail": 12, "fee": 50000}
}

UPGRADES = {
    "weapon": {"name": "🔫 Оружие", "price": 5000, "bonus": 20},
    "car": {"name": "🚗 Машина", "price": 3000, "cooldown": 3600},
    "explosives": {"name": "💣 Взрывчатка", "price": 7000, "reward_bonus": 30},
    "masks": {"name": "🎭 Маски", "price": 2000, "jail_reduce": 2}
}

def register_heists(dp, pool, update_balance, fmt_money):
    
    @dp.message(lambda m: m.text and m.text.startswith("/bank_heist"))
    async def cmd_bank_heist(m: Message):
        t = "🏦 <b>ОГРАБЛЕНИЯ БАНКОВ</b>\n\n"
        for key, bank in BANKS.items():
            t += f"{bank['name']}\n"
            t += f"    Награда: {fmt_money(bank['reward'])}\n"
            t += f"    Шанс: {bank['chance']}%\n"
            t += f"   👥 Игроков: {bank['min']}-{bank['max']}\n"
            t += f"    Тюрьма: {bank['jail']}ч\n"
            t += f"   💵 Взнос: {fmt_money(bank['fee'])}\n"
            t += f"   🛒 Создать: /create_heist {key}\n\n"
        t += "━━━━━━━━━━━━━━━━━━━━\n"
        t += "🎒 <b>Улучшения:</b>\n"
        for key, upg in UPGRADES.items():
            t += f"   {upg['name']} — {fmt_money(upg['price'])}\n\n"
        t += "💡 <b>Как играть:</b>\n1. Ответь на сообщение игрока\n2. Напиши /create_heist local\n3. Купи улучшения: /buy_upgrade weapon\n4. Начни: /start_heist"
        await m.answer(t, parse_mode="HTML")

    @dp.message(lambda m: m.text and m.text.startswith("/create_heist"))
    async def cmd_create_heist(m: Message):
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2: return await m.answer("🏦 <b>Использование:</b>\n\n1. Ответь на сообщение игрока\n2. Напиши: /create_heist local\n\nТипы: local, city, central, swiss", parse_mode="HTML")
        bank_type = args[1]
        if bank_type not in BANKS: return await m.answer("❌ Неверный тип банка! Используй: local, city, central, swiss")
        if not m.reply_to_message: return await m.answer("❌ Ответь на сообщение игрока, чтобы пригласить его!")
        partner_id = m.reply_to_message.from_user.id
        if partner_id == uid: return await m.answer("❌ Нельзя пригласить самого себя!")
        bank = BANKS[bank_type]
        team = [uid, partner_id]
        if len(team) < bank['min']: return await m.answer(f"❌ Нужно минимум {bank['min']} игроков! Сейчас: {len(team)}")
        if len(team) > bank['max']: return await m.answer(f"❌ Максимум {bank['max']} игроков! Сейчас: {len(team)}")
        
        async with pool.acquire() as conn:
            for mid in team:
                bal = await conn.fetchval("SELECT balance FROM users WHERE chat_id=$1 AND user_id=$2", cid, mid)
                if bal is None or bal < bank['fee']:
                    name = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, mid) or f"User{mid}"
                    return await m.answer(f"❌ У {name} недостаточно средств! Нужно: {fmt_money(bank['fee'])}")
                last = await conn.fetchval("SELECT last_heist FROM heist_cooldowns WHERE chat_id=$1 AND user_id=$2", cid, mid)
                if last and time.time() - last < 86400:
                    name = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, mid) or f"User{mid}"
                    rem = int(86400 - (time.time() - last))
                    h, m_rem = rem // 3600, (rem % 3600) // 60
                    return await m.answer(f"❌ {name} в кулдауне! Осталось: {h}ч {m_rem}мин")
        
        for mid in team: await update_balance(cid, mid, -bank['fee'])
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO bank_heists (chat_id, leader_id, bank_type, team_members, status, created_at, start_time) VALUES ($1,$2,$3,$4,'preparing',$5,$6)", cid, uid, bank_type, team, time.time(), time.time() + 300)
        
        l_name = m.from_user.first_name
        p_name = m.reply_to_message.from_user.first_name
        await m.answer(f" <b>ОГРАБЛЕНИЕ СОЗДАНО!</b>\n\n🏛️ Банк: {bank['name']}\n👥 Команда: {l_name} + {p_name}\n💰 Взнос с каждого: {fmt_money(bank['fee'])}\n⏰ Начало через: 5 минут\n\n🎒 Купите улучшения: /buy_upgrade weapon\n🚀 Начать: /start_heist", parse_mode="HTML")

    @dp.message(lambda m: m.text and m.text.startswith("/buy_upgrade"))
    async def cmd_buy_upgrade(m: Message):
        cid, uid = m.chat.id, m.from_user.id
        args = m.text.split()
        if len(args) < 2: return await m.answer("🎒 <b>Использование:</b> /buy_upgrade weapon\n\nДоступны: weapon, car, explosives, masks", parse_mode="HTML")
        key = args[1]
        if key not in UPGRADES: return await m.answer("❌ Неверное улучшение! Доступны: weapon, car, explosives, masks")
        upg = UPGRADES[key]
        async with pool.acquire() as conn:
            bal = await conn.fetchval("SELECT balance FROM users WHERE chat_id=$1 AND user_id=$2", cid, uid)
            if bal is None or bal < upg['price']: return await m.answer(f"❌ Недостаточно средств! Нужно: {fmt_money(upg['price'])}")
            heist = await conn.fetchrow("SELECT * FROM bank_heists WHERE chat_id=$1 AND $2 = ANY(team_members) AND status='preparing'", cid, uid)
            if not heist: return await m.answer("❌ У вас нет активного ограбления!")
            ups = heist['upgrades'] or []
            if key in ups: return await m.answer("❌ Это улучшение уже куплено!")
            ups.append(key)
            await conn.execute("UPDATE bank_heists SET upgrades=$1 WHERE id=$2", ups, heist['id'])
        await update_balance(cid, uid, -upg['price'])
        await m.answer(f"✅ <b>Улучшение куплено!</b>\n\n🎒 {upg['name']}\n💰 Списано: {fmt_money(upg['price'])}", parse_mode="HTML")

    @dp.message(lambda m: m.text and m.text.startswith("/start_heist"))
    async def cmd_start_heist(m: Message):
        cid, uid = m.chat.id, m.from_user.id
        async with pool.acquire() as conn:
            heist = await conn.fetchrow("SELECT * FROM bank_heists WHERE chat_id=$1 AND leader_id=$2 AND status='preparing'", cid, uid)
            if not heist: return await m.answer("❌ У вас нет активного ограбления!")
            if time.time() < heist['start_time']:
                rem = int(heist['start_time'] - time.time())
                return await m.answer(f"⏰ Ограбление начнется через {rem} секунд!")
            bank = BANKS[heist['bank_type']]
            chance = bank['chance']
            ups = heist['upgrades'] or []
            if 'weapon' in ups: chance += UPGRADES['weapon']['bonus']
            chance += random.randint(-20, 20)
            chance = max(5, min(95, chance))
            roll = random.randint(1, 100)
            if roll <= chance:
                reward = bank['reward']
                if 'explosives' in ups: reward = int(reward * (1 + UPGRADES['explosives']['reward_bonus'] / 100))
                per_player = reward // len(heist['team_members'])
                for mid in heist['team_members']:
                    await update_balance(cid, mid, per_player)
                    cd = 86400
                    if 'car' in ups: cd -= UPGRADES['car']['cooldown']
                    await conn.execute("INSERT INTO heist_cooldowns (chat_id, user_id, last_heist) VALUES ($1,$2,$3) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_heist=$3", cid, mid, time.time())
                await conn.execute("UPDATE bank_heists SET status='success', result='success', reward=$1 WHERE id=$2", reward, heist['id'])
                names = []
                for mid in heist['team_members']:
                    n = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, mid) or f"User{mid}"
                    names.append(n)
                msg = f"✅ <b>ОГРАБЛЕНИЕ УСПЕШНО!</b>\n\n🏦 Банк: {bank['name']}\n👥 Команда: {', '.join(names)}\n💰 Общая награда: {fmt_money(reward)}\n💵 На каждого: {fmt_money(per_player)}\n\n Поздравляем!"
                await m.answer(msg, parse_mode="HTML")
            else:
                jail_time = bank['jail']
                if 'masks' in ups: jail_time -= UPGRADES['masks']['jail_reduce']
                jail_time = max(2, jail_time)
                for mid in heist['team_members']:
                    release = time.time() + (jail_time * 3600)
                    await conn.execute("INSERT INTO jail (chat_id, user_id, release_time, reason) VALUES ($1,$2,$3,$4) ON CONFLICT (chat_id, user_id) DO UPDATE SET release_time=$3, reason=$4", cid, mid, release, "Провал ограбления")
                    await conn.execute("INSERT INTO heist_cooldowns (chat_id, user_id, last_heist) VALUES ($1,$2,$3) ON CONFLICT (chat_id, user_id) DO UPDATE SET last_heist=$3", cid, mid, time.time() - 86400)
                await conn.execute("UPDATE bank_heists SET status='failed', result='failed' WHERE id=$1", heist['id'])
                names = []
                for mid in heist['team_members']:
                    n = await conn.fetchval("SELECT username FROM usernames WHERE chat_id=$1 AND user_id=$2", cid, mid) or f"User{mid}"
                    names.append(n)
                msg = f"❌ <b>ОГРАБЛЕНИЕ ПРОВАЛИЛОСЬ!</b>\n\n Банк: {bank['name']}\n Команда: {', '.join(names)}\n🔒 Все в тюрьме на {jail_time} часов!\n⏰ Кулдаун: 48 часов\n\n😔 В следующий раз повезет..."
                await m.answer(msg, parse_mode="HTML")
