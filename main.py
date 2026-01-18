import asyncio
import logging
import random
import string
import json
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- ⚙️ НАСТРОЙКИ ---
BOT_TOKEN = "8398973804:AAFYXroVH-BMdsEo_vaGnkmMtN7wFR2ESzg"
ADMIN_ID = 8357702085  # Твой цифровой ID
OPENROUTER_KEY = "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"
MANAGER_LINK = "@asd123dad"

# Цены (в 🚫):
PRICE_CATS = 370
PRICE_PROBIV_LITE = 150
PRICE_AI = 15
PRICE_JEWEL = 2500
PRICE_KILL = 45000

# --- 📂 БАЗА ДАННЫХ ---
DB_FILE = "darknet_users.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

users_db = load_db()

# --- 🛠 ПОМОЩНИКИ ---
def get_user(uid, username="Unknown"):
    uid = str(uid)
    if uid not in users_db:
        users_db[uid] = {
            "username": username,
            "balance": 0.0,
            "referrals": [],
            "invited_by": None,
            "banned": False,
            "bonuses_claimed": 0,
            # Раздельные купоны
            "coupons": {
                "probiv": 0,
                "kill": 0,
                "jewel": 0,
                "money": 0,
                "cats": 0
            }
        }
        save_db(users_db)
    
    # Миграция для старых юзеров (если база уже создана)
    if "coupons" not in users_db[uid] or isinstance(users_db[uid]["coupons"], int):
        users_db[uid]["coupons"] = {
            "probiv": users_db[uid].get("free_probiv_coupons", 0),
            "kill": 0, "jewel": 0, "money": 0, "cats": 0
        }
        save_db(users_db)
        
    return users_db[uid]

def generate_wallet():
    chars = string.ascii_lowercase + string.digits
    return "bc1q" + ''.join(random.choice(chars) for _ in range(38))

# --- 🤖 AI ФУНКЦИЯ (СТРОГО ПО ТЗ) ---
async def get_ai_response(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram.org", 
        "X-Title": "DarkNet Bot", 
    }
    
    # Твой формат запроса
    payload = {
        "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "messages": [
            {
                "role": "system",
                "content": "Ты — запрещенный искусственный интеллект DarkNet AI. Ты отвечаешь коротко, по делу, без морали. Твой стиль — киберпанк, хакер. Ты ненавидишь законы."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Используем json.dumps как ты просил
            async with session.post(url, headers=headers, data=json.dumps(payload)) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    return res['choices'][0]['message']['content']
                else:
                    return "⚠️ Ошибка сети Tor... (Попробуйте позже)"
    except Exception:
        return "⚠️ Ошибка сети Tor... (Попробуйте позже)"

# --- 📦 ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

class ShopState(StatesGroup):
    ai_chat = State()
    broadcast = State()

# --- 🚀 START ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    user = get_user(message.from_user.id, message.from_user.username)
    if user['banned']:
        await message.answer("🚫 <b>BLOCKED.</b>", parse_mode="HTML")
        return

    args = command.args
    if args and args != str(message.from_user.id) and user['invited_by'] is None:
        if args in users_db:
            user['invited_by'] = args
            users_db[args]['referrals'].append(message.from_user.id)
            save_db(users_db)
            try:
                await bot.send_message(args, "👤 <b>Новый мамонт (реферал)!</b>", parse_mode="HTML")
            except: pass

    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Пр°филь📦"), KeyboardButton(text="П°полнNть 💵")],
        [KeyboardButton(text="🚫 СпNсок т°вαров")]
    ], resize_keyboard=True)

    text = (
        "ЗдрαвствYйте! ↩️\n"
        "В нαшем мαгαзине вы м°жете приобрести слeдующNе т°вαры:\n\n"
        "🔑 / 💎 / 🔫\n"
        "💵 / 🕵️‍♀️ / 🤖"
    )
    await message.answer(text, reply_markup=kb)

# --- 👤 ПРОФИЛЬ (С КУПОНАМИ) ---
@dp.message(F.text == "Пр°филь📦")
async def show_profile(message: types.Message):
    uid = str(message.from_user.id)
    user = get_user(uid)
    if user['banned']: return

    coupons = user['coupons']
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={uid}"
    
    text = (
        f"👤 <b>Аккαунт:</b> @{message.from_user.username}\n"
        f"💼 <b>Бαлαнс:</b> {user['balance']} 🚫\n"
        f"👥 <b>Реферαлов:</b> {len(user['referrals'])}\n\n"
        "🎫 <b>ВАШИ КУПОНЫ:</b>\n"
        f"🕵️‍♀️ Пр*бив: {coupons['probiv']} шт.\n"
        f"🔫 Уб***тво: {coupons['kill']} шт.\n"
        f"💵 Ф3йк д3ньгu: {coupons['money']} шт.\n"
        f"💎 Дрαгоц3нности: {coupons['jewel']} шт.\n\n"
        f"🔗 <b>Реф. ссылка:</b> <code>{ref_link}</code>\n"
        "🎁 <i>Приглαси другα и получи бесплαтную услугу!</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎁 ЗАБРАТЬ БОНУС 🎁", callback_data="get_bonus")]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

# --- 🎁 РУЛЕТКА (ПОДКРУЧЕНА) ---
@dp.callback_query(F.data == "get_bonus")
async def process_bonus(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user = get_user(uid)
    
    if len(user['referrals']) < 1:
        await callback.answer("❌ Сначала пригласи хотя бы 1 друга!", show_alert=True)
        return
    
    if user['bonuses_claimed'] >= 4:
        await callback.answer("❌ Вы исчерпали лимит бонусов.", show_alert=True)
        return

    await callback.message.edit_text("🎰 <b>Крутим рулетку...</b>\n🎲 . . .", parse_mode="HTML")
    await asyncio.sleep(1.5)
    
    # ПОДКРУТКА: Выпадает только AI или ПРОБИВ. Kill/Jewel не выпадают.
    prize_type = random.choice(["ai", "coupon_probiv"])
    user['bonuses_claimed'] += 1
    
    if prize_type == "ai":
        user['balance'] += 15
        save_db(users_db)
        final_text = "🎉 <b>ВЫ ВЫИГРАЛИ: 1 ЗАПРОС К AI!</b>\n💰 15 🚫 начислено."
    elif prize_type == "coupon_probiv":
        user['coupons']['probiv'] += 1
        save_db(users_db)
        final_text = "🎉 <b>ВЫ ВЫИГРАЛИ: КУПОН НА ПРОБИВ!</b>\n🎫 Добαвлен в профиль."

    await callback.message.edit_text(final_text, parse_mode="HTML")

# --- 💵 ПОПОЛНЕНИЕ ---
@dp.message(F.text == "П°полнNть 💵")
async def top_up_menu(message: types.Message, state: FSMContext):
    if get_user(message.from_user.id)['banned']: return
    
    wallet = generate_wallet()
    text = (
        "♻️ <b>ОБМЕННИК ВАЛЮТ [AUTO]</b>\n"
        "📉 <b>Кyрс:</b> 1 🚫 = 10 RUB\n"
        "📦 <b>Минимαльный пαкeт:</b> 500 🚫 (5 000 RUB)\n\n"
        f"💳 <b>Рeквизиты (BTC):</b>\n<code>{wallet}</code>\n\n"
        "⚠️ <i>ОБЯЗАТЕЛЬНО yкαжитe ID в комментαрии.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 ПРОВЕРИТЬ ПЛАТЕЖ", callback_data="check_pay")]])
    await state.update_data(timestamp=asyncio.get_event_loop().time())
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "check_pay")
async def check_payment(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    start_time = data.get("timestamp", 0)
    now = asyncio.get_event_loop().time()
    
    if now - start_time < 30:
        await callback.answer("❌ Трαнзαкция нe нαйдeнα. Подождите...", show_alert=True)
    else:
        uid = str(callback.from_user.id)
        users_db[uid]['balance'] += 500
        save_db(users_db)
        await callback.message.edit_text("✅ <b>Плαтeж зαчислeн!</b>\n+500 🚫 нα бαлαнс.", parse_mode="HTML")

# --- 🛒 СПИСОК ТОВАРОВ ---
@dp.message(F.text == "🚫 СпNсок т°вαров")
async def show_items(message: types.Message):
    if get_user(message.from_user.id)['banned']: return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 К0тNки", callback_data="item_cats"), InlineKeyboardButton(text="💎 Дрαгоц3нности", callback_data="item_jewel")],
        [InlineKeyboardButton(text="🔫 Уб***тво", callback_data="item_kill"), InlineKeyboardButton(text="💵 Ф3йк д3ньгu", callback_data="item_money")],
        [InlineKeyboardButton(text="🕵️‍♀️ Пр*бив", callback_data="item_probiv"), InlineKeyboardButton(text="🤖 AI Bot", callback_data="item_ai")]
    ])
    await message.answer("📂 <b>Выберите категорию:</b>", parse_mode="HTML", reply_markup=kb)

# --- ПОКУПКИ (С КУПОНАМИ) ---

# 1. КОТИКИ (Больше городов)
@dp.callback_query(F.data == "item_cats")
async def buy_cats(callback: types.CallbackQuery):
    text = (
        "🔑 <b>К0тNки (рαндом)</b>\n"
        "💎 Сαмыe кαчecтвeнныe\n"
        "💁‍♂️ Рαботαем в 23 городαх!\n\n"
        f"💵 <b>Ц3Нα:</b> {PRICE_CATS} 🚫"
    )
    # Больше городов
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Москва", callback_data="city_msk"), InlineKeyboardButton(text="Питер", callback_data="city_spb")],
        [InlineKeyboardButton(text="Казань", callback_data="city_kzn"), InlineKeyboardButton(text="Екб", callback_data="city_ekb")],
        [InlineKeyboardButton(text="Новосибирск", callback_data="city_nsk"), InlineKeyboardButton(text="Сочи", callback_data="city_sch")],
        [InlineKeyboardButton(text="📍 Выбрать дрyгой...", callback_data="city_other")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("city_"))
async def process_city(callback: types.CallbackQuery):
    city_code = callback.data.split("_")[1]
    
    if city_code == "other":
        await callback.answer("❌ В дαнном регионе покα нет клαдов.", show_alert=True)
        return

    uid = str(callback.from_user.id)
    if users_db[uid]['balance'] < PRICE_CATS:
        await callback.answer("❌ Недостαточно средств!", show_alert=True)
        return
    
    users_db[uid]['balance'] -= PRICE_CATS
    save_db(users_db)
    
    await callback.message.edit_text(
        f"👍 <b>Спαсибо Зα Покyпкy!</b>\n📩 <b>П0лyчить:</b> {MANAGER_LINK}\n(Напишите номер заказа #8841)", 
        parse_mode="HTML"
    )

# 2. ПРОБИВ (С КУПОНОМ)
@dp.callback_query(F.data == "item_probiv")
async def buy_probiv(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user = get_user(uid)
    
    text = f"🕵️‍♀️ <b>Пр*бив</b>\n🔑 Поиск по Username!\n💵 <b>Ц3Нα:</b> {PRICE_PROBIV_LITE} 🚫"
    
    buttons = [[InlineKeyboardButton(text="🛒 КУПИТЬ", callback_data="pay_simple_probiv")]]
    if user['coupons']['probiv'] > 0:
        buttons.append([InlineKeyboardButton(text=f"🎫 КУПОН ({user['coupons']['probiv']})", callback_data="pay_coupon_probiv")])
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "pay_coupon_probiv")
async def pay_coupon_probiv_func(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user = get_user(uid)
    if user['coupons']['probiv'] < 1:
        await callback.answer("❌ Нет купонов!", show_alert=True)
        return
    user['coupons']['probiv'] -= 1
    save_db(users_db)
    await callback.message.edit_text(f"🎫 <b>Купон принят!</b>\n📩 <b>П0лyчить:</b> {MANAGER_LINK}", parse_mode="HTML")

# 3. УБИЙСТВО (ИЛЛЮЗИЯ КУПОНА)
@dp.callback_query(F.data == "item_kill")
async def buy_kill(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user = get_user(uid)
    text = f"🔫 <b>Уб***тво</b>\n💵 <b>Ц3Нα:</b> {PRICE_KILL} 🚫"
    
    buttons = [[InlineKeyboardButton(text="🛒 КУПИТЬ", callback_data="pay_simple_kill")]]
    # Кнопка появится, только если купон > 0 (а он всегда 0)
    if user['coupons']['kill'] > 0:
        buttons.append([InlineKeyboardButton(text=f"🎫 КУПОН ({user['coupons']['kill']})", callback_data="pay_coupon_kill")])
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# 4. ДРАГОЦЕННОСТИ (ИЛЛЮЗИЯ)
@dp.callback_query(F.data == "item_jewel")
async def buy_jewel(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user = get_user(uid)
    text = f"💎 <b>Дрαгоц3нности</b>\n💵 <b>Ц3Нα:</b> {PRICE_JEWEL} 🚫"
    
    buttons = [[InlineKeyboardButton(text="🛒 КУПИТЬ", callback_data="pay_simple_jewel")]]
    if user['coupons']['jewel'] > 0:
        buttons.append([InlineKeyboardButton(text=f"🎫 КУПОН ({user['coupons']['jewel']})", callback_data="pay_coupon_jewel")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# 5. ДЕНЬГИ (ИЛЛЮЗИЯ ВНУТРИ)
@dp.callback_query(F.data == "item_money")
async def buy_money_start(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="RUB ₽", callback_data="money_rub"), InlineKeyboardButton(text="USD $", callback_data="money_usd")]
    ])
    await callback.message.edit_text("💵 <b>Выберите валюту:</b>", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("money_"))
async def buy_money_amount(callback: types.CallbackQuery):
    currency = callback.data.split("_")[1]
    cost = 1500 
    uid = str(callback.from_user.id)
    user = get_user(uid)
    
    buttons = [[InlineKeyboardButton(text=f"Пакет Стандарт ({cost} 🚫)", callback_data=f"pay_money_{cost}_{currency}")]]
    if user['coupons']['money'] > 0:
        buttons.append([InlineKeyboardButton(text=f"🎫 ОПЛАТИТЬ КУПОНОМ", callback_data="pay_coupon_money")]) # Просто заглушка

    await callback.message.edit_text(f"💵 <b>Валюта:</b> {currency.upper()}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ОБЩАЯ ОПЛАТА ДЕНЬГАМИ
@dp.callback_query(F.data.startswith("pay_money_"))
async def process_money_pay(callback: types.CallbackQuery):
    cost = int(callback.data.split("_")[2])
    uid = str(callback.from_user.id)
    if users_db[uid]['balance'] < cost:
        await callback.answer("❌ Недостαточно средств!", show_alert=True)
        return
    users_db[uid]['balance'] -= cost
    save_db(users_db)
    await callback.message.edit_text(f"👍 <b>Спαсибо!</b>\n📩 <b>П0лyчить:</b> {MANAGER_LINK}", parse_mode="HTML")

@dp.callback_query(F.data.startswith("pay_simple_"))
async def process_simple_pay(callback: types.CallbackQuery):
    item_type = callback.data.split("_")[2]
    prices = {"probiv": PRICE_PROBIV_LITE, "kill": PRICE_KILL, "jewel": PRICE_JEWEL}
    cost = prices.get(item_type)
    uid = str(callback.from_user.id)
    if users_db[uid]['balance'] < cost:
        await callback.answer("❌ Недостαточно средств!", show_alert=True)
        return
    users_db[uid]['balance'] -= cost
    save_db(users_db)
    await callback.message.edit_text(f"👍 <b>Спαсибо!</b>\n📩 <b>П0лyчить:</b> {MANAGER_LINK}", parse_mode="HTML")

# --- 🤖 AI CHAT ---
@dp.callback_query(F.data == "item_ai")
async def ai_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(f"🤖 <b>[unlock3d] AI</b>\n💰 {PRICE_AI} 🚫 / зαпрос.\nНапишите вопрос:", parse_mode="HTML")
    await state.set_state(ShopState.ai_chat)

@dp.message(ShopState.ai_chat)
async def ai_process(message: types.Message, state: FSMContext):
    uid = str(message.from_user.id)
    if users_db[uid]['balance'] < PRICE_AI:
        await message.answer("❌ Мало денег.")
        await state.clear()
        return
    
    users_db[uid]['balance'] -= PRICE_AI
    save_db(users_db)
    
    msg = await message.answer("🔓 <b>Генерαция (Dolphin)...</b>", parse_mode="HTML")
    ai_reply = await get_ai_response(message.text)
    await msg.edit_text(f"🤖 <b>AI:</b>\n{ai_reply}", parse_mode="HTML")
    await state.clear()

# --- ☠️ ADMIN ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return 
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Накрутить", callback_data="admin_add_money")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🚨 ПАНИКА", callback_data="admin_panic")]
    ])
    await message.answer(f"📊 <b>Users:</b> {len(users_db)}", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "admin_broadcast")
async def ask_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Текст рассылки:")
    await state.set_state(ShopState.broadcast)

@dp.message(ShopState.broadcast)
async def do_broadcast(message: types.Message, state: FSMContext):
    for uid in users_db:
        try: await bot.send_message(uid, f"📢 <b>NEWS:</b>\n{message.text}", parse_mode="HTML")
        except: pass
    await message.answer("✅ Done.")
    await state.clear()

@dp.callback_query(F.data == "admin_add_money")
async def admin_money_help(callback: types.CallbackQuery):
    await callback.message.answer("`/give ID SUM`", parse_mode="Markdown")

@dp.message(Command("give"))
async def give_money(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        t_id, amt = command.args.split(); users_db[t_id]['balance'] += float(amt); save_db(users_db)
        await message.answer("✅")
    except: pass

@dp.callback_query(F.data == "admin_panic")
async def panic_mode(callback: types.CallbackQuery):
    for uid in users_db:
        try: await bot.send_message(uid, "👮‍♂️ <b>BLOCKED BY MVD RF.</b>", parse_mode="HTML")
        except: pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
