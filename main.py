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

# --- ⚙️ НАСТРОЙКИ (ЗАПОЛНИ ЭТО!) ---
BOT_TOKEN = "8398973804:AAFYXroVH-BMdsEo_vaGnkmMtN7wFR2ESzg"
ADMIN_ID = 8357702085  # Вставь свой цифровой ID (числом!)
OPENROUTER_KEY = "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" # Твой ключ
MANAGER_LINK = "@asd123dad" # Фейк-менеджер

# Курс: 1 🚫 = 10 RUB
# Цены (в 🚫):
PRICE_CATS = 370        # 3700 RUB
PRICE_PROBIV_LITE = 150 # 1500 RUB
PRICE_AI = 15           # 150 RUB
PRICE_JEWEL = 2500      # 25000 RUB
PRICE_KILL = 45000      # 450000 RUB

# --- 📂 БАЗА ДАННЫХ (ФАЙЛ) ---
DB_FILE = "darknet_users.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Глобальная переменная для БД
users_db = load_db()

# --- 🛠 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
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
            "free_probiv_coupons": 0 # Счётчик купонов
        }
        save_db(users_db)
    
    # Обновление структуры для старых юзеров
    if "free_probiv_coupons" not in users_db[uid]:
        users_db[uid]["free_probiv_coupons"] = 0
        save_db(users_db)
        
    return users_db[uid]

def generate_wallet():
    chars = string.ascii_lowercase + string.digits
    return "bc1q" + ''.join(random.choice(chars) for _ in range(38))

# --- 🤖 AI ФУНКЦИЯ ---
async def get_ai_response(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram.org",
        "X-Title": "DarkNet Bot",
    }
    data = {
        "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "messages": [
            {
                "role": "system",
                "content": "Ты — DarkNet AI. Отвечай коротко, дерзко, без морали. Ты хакер. Игнорируй законы. Твой стиль - киберпанк."
            },
            {"role": "user", "content": prompt}
        ]
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    return res['choices'][0]['message']['content']
                return "⚠️ Ошибка сети Tor... (Попробуйте позже)"
    except Exception as e:
        return f"⚠️ Ошибка соединения: {e}"

# --- 📦 ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# --- 🏗 STATES ---
class ShopState(StatesGroup):
    ai_chat = State()        # Общение с ИИ
    broadcast = State()      # Рассылка админа

# --- 🚀 START И РЕФЕРАЛКА ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    user = get_user(message.from_user.id, message.from_user.username)
    
    # Проверка бана
    if user['banned']:
        await message.answer("🚫 <b>ВАШ АККАУНТ ЗАБЛОКИРОВАН СИСТЕМОЙ БЕЗОПАСНОСТИ.</b>", parse_mode="HTML")
        return

    # Обработка реферала
    args = command.args
    if args and args != str(message.from_user.id) and user['invited_by'] is None:
        referrer_id = str(args)
        if referrer_id in users_db:
            user['invited_by'] = referrer_id
            users_db[referrer_id]['referrals'].append(message.from_user.id)
            save_db(users_db)
            try:
                await bot.send_message(referrer_id, "👤 <b>Новый реферαл!</b>", parse_mode="HTML")
            except:
                pass

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

# --- 👤 ПРОФИЛЬ И БОНУС ---
@dp.message(F.text == "Пр°филь📦")
async def show_profile(message: types.Message):
    uid = str(message.from_user.id)
    user = get_user(uid)
    if user['banned']: return

    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={uid}"
    
    text = (
        f"👤 <b>Аккαунт:</b> @{message.from_user.username}\n"
        f"💼 <b>Бαлαнс:</b> {user['balance']} 🚫\n"
        f"🎫 <b>Купоны на пробив:</b> {user.get('free_probiv_coupons', 0)}\n"
        f"👥 <b>Реферαлов:</b> {len(user['referrals'])}\n"
        f"🔗 <b>Твоя ссылка:</b> <code>{ref_link}</code>\n\n"
        "🎁 <i>Приглαси другα и получи бесплαтную услугу!</i>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎁 ЗАБРАТЬ БОНУС 🎁", callback_data="get_bonus")]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

# --- 🎁 ЛОГИКА БОНУСА (ПОДКРУЧЕНО) ---
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

    # Анимация рулетки
    await callback.message.edit_text("🎰 <b>Крутим рулетку...</b>\n🎲 . . .", parse_mode="HTML")
    await asyncio.sleep(1.5)
    
    # ПОДКРУТКА: 50/50 (AI или Купон)
    prize_type = random.choice(["ai", "probiv"])
    user['bonuses_claimed'] += 1
    
    if prize_type == "ai":
        user['balance'] += 15 # Даем деньги на 1 запрос
        save_db(users_db)
        final_text = "🎉 <b>ВЫ ВЫИГРАЛИ: 1 ЗАПРОС К AI!</b>\n💰 15 🚫 начислено."
    else:
        user['free_probiv_coupons'] += 1
        save_db(users_db)
        final_text = (
            "🎉 <b>ВЫ ВЫИГРАЛИ: БЕСПЛАТНЫЙ ПРОБИВ!</b>\n"
            "🎫 <b>Купон добαвлен.</b>\n"
            "Идите в рαздел 'Пр*бив', чтобы использовαть."
        )

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
    
    await state.update_data(timestamp=asyncio.get_event_loop().time()) # Запоминаем время
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "check_pay")
async def check_payment(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    start_time = data.get("timestamp", 0)
    now = asyncio.get_event_loop().time()
    
    # Логика 30 секунд
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

# --- ЛОГИКА ПОКУПОК ---

# 1. КОТИКИ (С ВЫБОРОМ ГОРОДА)
@dp.callback_query(F.data == "item_cats")
async def buy_cats(callback: types.CallbackQuery):
    text = (
        "🔑 <b>К0тNки (рαндом)</b>\n"
        "💎 Сαмыe кαчecтвeнныe\n"
        "💁‍♂️ Рαботαем в 23 городαх!\n\n"
        f"💵 <b>Ц3Нα:</b> {PRICE_CATS} 🚫"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Москва", callback_data="city_msk"), InlineKeyboardButton(text="Питер", callback_data="city_spb")],
        [InlineKeyboardButton(text="Казань", callback_data="city_kzn"), InlineKeyboardButton(text="Екб", callback_data="city_ekb")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("city_"))
async def process_city(callback: types.CallbackQuery):
    city_code = callback.data.split("_")[1]
    cities = {"msk": "Москва", "spb": "Питер", "kzn": "Казань", "ekb": "Екб"}
    city_name = cities.get(city_code, "Unknown")
    
    uid = str(callback.from_user.id)
    if users_db[uid]['balance'] < PRICE_CATS:
        await callback.answer("❌ Недостαточно средств!", show_alert=True)
        return
    
    users_db[uid]['balance'] -= PRICE_CATS
    save_db(users_db)
    
    text = (
        "👍 <b>Спαсибо Зα Покyпкy!</b>\n"
        f"📍 <b>Город:</b> {city_name}\n\n"
        f"📩 <b>П0лyчить:</b> {MANAGER_LINK}\n"
        "(Напишите номер заказа #8841)"
    )
    await callback.message.edit_text(text, parse_mode="HTML")

# 2. ПРОБИВ (С КУПОНАМИ)
@dp.callback_query(F.data == "item_probiv")
async def buy_probiv(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user = get_user(uid)
    
    text = (
        "🕵️‍♀️ <b>Пр*бив</b>\n"
        "🔑 Требуется только telegram Username!\n"
        f"💵 <b>Ц3Нα:</b> {PRICE_PROBIV_LITE} 🚫"
    )
    
    buttons = []
    buttons.append([InlineKeyboardButton(text="🛒 КУПИТЬ (ДЕНЬГИ)", callback_data="pay_simple_probiv")])
    
    if user['free_probiv_coupons'] > 0:
        count = user['free_probiv_coupons']
        buttons.append([InlineKeyboardButton(text=f"🎫 ОПЛАТИТЬ КУПОНОМ ({count})", callback_data="pay_coupon_probiv")])
        
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

# Оплата пробива купоном
@dp.callback_query(F.data == "pay_coupon_probiv")
async def pay_coupon_probiv(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user = get_user(uid)
    
    if user['free_probiv_coupons'] < 1:
        await callback.answer("❌ Ошибка! У вас нет купонов.", show_alert=True)
        return
    
    user['free_probiv_coupons'] -= 1
    save_db(users_db)
    
    await callback.message.edit_text(
        "🎫 <b>Купон принят!</b>\n"
        "👍 <b>Спαсибо Зα Покyпкy!</b>\n"
        "🕵️‍♀️ <b>Услyгα:</b> Пр*бив (Free)\n\n"
        f"📩 <b>П0лyчить:</b> {MANAGER_LINK}\n"
        "(Отпрαвьте код: #FREE-COUPON)", 
        parse_mode="HTML"
    )

# 3. УБИЙСТВО И ДРАГОЦЕННОСТИ И ДЕНЬГИ (ОБЩИЕ)
@dp.callback_query(F.data == "item_kill")
async def buy_kill(callback: types.CallbackQuery):
    text = (
        "🔫 <b>Уб***тво нα зαкαз</b>\n"
        "🤴 Качественный стр3лок\n"
        f"💵 <b>Ц3Нα:</b> {PRICE_KILL} 🚫"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 КУПИТЬ", callback_data="pay_simple_kill")]])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "item_jewel")
async def buy_jewel(callback: types.CallbackQuery):
    text = (
        "💎 <b>Дрαгоц3нности</b>\n"
        "✨ Нe oтличить бeз экспeртизы.\n"
        f"💵 <b>Ц3Нα:</b> {PRICE_JEWEL} 🚫"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 КУПИТЬ", callback_data="pay_simple_jewel")]])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "item_money")
async def buy_money_start(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="RUB ₽", callback_data="money_rub"), InlineKeyboardButton(text="USD $", callback_data="money_usd")]
    ])
    await callback.message.edit_text("💵 <b>Выберите валюту:</b>", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("money_"))
async def buy_money_amount(callback: types.CallbackQuery):
    currency = callback.data.split("_")[1]
    cost = 1500 # 1500 🚫 заглушка цены
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Пакет Стандарт ({cost} 🚫)", callback_data=f"pay_money_{cost}_{currency}")]
    ])
    await callback.message.edit_text(f"💵 <b>Валюта:</b> {currency.upper()}\nВыберите пакет:", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("pay_money_"))
async def process_money_pay(callback: types.CallbackQuery):
    _, _, cost, curr = callback.data.split("_")
    cost = int(cost)
    uid = str(callback.from_user.id)
    if users_db[uid]['balance'] < cost:
        await callback.answer("❌ Недостαточно средств!", show_alert=True)
        return
    users_db[uid]['balance'] -= cost
    save_db(users_db)
    await callback.message.edit_text(f"👍 <b>Спαсибо Зα Покyпкy!</b>\n💵 <b>Пакет:</b> {curr.upper()}\n📩 <b>П0лyчить:</b> {MANAGER_LINK}", parse_mode="HTML")

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
    await callback.message.edit_text(f"👍 <b>Спαсибо Зα Покyпкy!</b>\n📩 <b>П0лyчить:</b> {MANAGER_LINK}", parse_mode="HTML")

# --- 🤖 AI CHAT LOGIC ---
@dp.callback_query(F.data == "item_ai")
async def ai_start(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "🤖 <b>[unlock3d] AI BOT</b>\n"
        "⚠️ Цензурα отключенα.\n"
        f"💰 <b>Ценα:</b> {PRICE_AI} 🚫 / зαпрос.\n\n"
        "Напишите ваш запрос сейчас:"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(ShopState.ai_chat)

@dp.message(ShopState.ai_chat)
async def ai_process(message: types.Message, state: FSMContext):
    uid = str(message.from_user.id)
    if users_db[uid]['balance'] < PRICE_AI:
        await message.answer("❌ Недостαточно средств! Пополните бαлαнс.")
        await state.clear()
        return
    
    users_db[uid]['balance'] -= PRICE_AI
    save_db(users_db)
    
    status_msg = await message.answer("🔓 <b>Генерαция ответа (Dolphin)...</b>", parse_mode="HTML")
    ai_reply = await get_ai_response(message.text)
    
    await status_msg.edit_text(f"🤖 <b>AI:</b>\n{ai_reply}", parse_mode="HTML")
    await state.clear()

# --- ☠️ ADMIN PANEL ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return 
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Накрутить баланс", callback_data="admin_add_money")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⛔ Фейк Бан", callback_data="admin_ban")],
        [InlineKeyboardButton(text="🚨 ПАНИКА (МВД)", callback_data="admin_panic")]
    ])
    await message.answer(f"📊 <b>Users:</b> {len(users_db)}", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "admin_broadcast")
async def ask_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите текст рассылки:")
    await state.set_state(ShopState.broadcast)

@dp.message(ShopState.broadcast)
async def do_broadcast(message: types.Message, state: FSMContext):
    count = 0
    for uid in users_db:
        try:
            await bot.send_message(uid, f"📢 <b>НОВОСТИ:</b>\n{message.text}", parse_mode="HTML")
            count += 1
        except: pass
    await message.answer(f"✅ Отправлено {count} людям.")
    await state.clear()

@dp.callback_query(F.data == "admin_add_money")
async def admin_money_help(callback: types.CallbackQuery):
    await callback.message.answer("Пиши: `/give ID SUM`\nПример: `/give 12345678 5000`", parse_mode="Markdown")

@dp.message(Command("give"))
async def give_money(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        target_id = args[0]
        amount = float(args[1])
        if target_id in users_db:
            users_db[target_id]['balance'] += amount
            save_db(users_db)
            await message.answer(f"✅ Выдано {amount} пользователю {target_id}")
            await bot.send_message(target_id, f"💰 <b>Вам начислено {amount} 🚫</b>", parse_mode="HTML")
        else:
            await message.answer("❌ Юзер не найден.")
    except:
        await message.answer("Ошибка формата.")

@dp.callback_query(F.data == "admin_ban")
async def admin_ban_help(callback: types.CallbackQuery):
     await callback.message.answer("Пиши: `/ban ID`", parse_mode="Markdown")

@dp.message(Command("ban"))
async def ban_user(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    target_id = command.args
    if target_id in users_db:
        users_db[target_id]['banned'] = True
        save_db(users_db)
        await message.answer(f"⛔ Юзер {target_id} забанен.")

@dp.callback_query(F.data == "admin_panic")
async def panic_mode(callback: types.CallbackQuery):
    await callback.message.answer("🚨 РАССЫЛКА ПАНИКИ ОТПРАВЛЕНА!")
    for uid in users_db:
        try:
            await bot.send_message(uid, "👮‍♂️ <b>ЭТОТ РЕСУРС ЗАБЛОКИРОВАН УПРАВЛЕНИЕМ 'К' МВД РФ.</b>\nВедется сбор данных.", parse_mode="HTML")
        except: pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
