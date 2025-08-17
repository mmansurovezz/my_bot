import json
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from datetime import datetime

# ---------------- LOGLASH ----------------
logging.basicConfig(level=logging.INFO)

# ---------------- BOT TOKEN ----------------
API_TOKEN = "8461331939:AAFTnBncGUUJA34WUa2NKu-iAAulbymiL1w"
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

DB_FILE = "db.json"

# ---------------- MA'LUMOTLAR BAZASI ----------------
def load_data():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"users": {}, "admins": [], "channels": [], "messages": []}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

data = load_data()

# ---------------- MENYU TUGMALARI ----------------
def get_menu(user_id):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Reyting 🏆"), KeyboardButton("Referal ✅")],
            [KeyboardButton("Kontakt admin 📩")]
        ],
        resize_keyboard=True
    )

# ---------------- START VA REFERAL ----------------
async def check_subscription(user_id):
    """Foydalanuvchi barcha kanallarga obuna bo‘lganini tekshiradi"""
    for channel in data["channels"]:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    args = message.get_args()
    ref_id = args if args else None

    # Agar user bazada yo‘q bo‘lsa qo‘shish
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "username": message.from_user.username,
            "points": 0,
            "referrals": [],
            "joined": str(datetime.now())
        }

        if ref_id and ref_id in data["users"] and ref_id != user_id:
            data["users"][ref_id]["points"] += 5
            data["users"][ref_id]["referrals"].append(user_id)
            await bot.send_message(ref_id, f"Siz yangi foydalanuvchini taklif qildingiz! +5 ball 🎉")

        save_data(data)

    # Kanal obunasini tekshirish
    if not await check_subscription(message.from_user.id):
        buttons = InlineKeyboardMarkup(row_width=1)
        for channel in data["channels"]:
            buttons.add(InlineKeyboardButton(text=f"👉 {channel}", url=f"https://t.me/{channel.replace('@','')}"))
        buttons.add(InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub"))

        await message.answer(
            "📢 Konkursda qatnashish uchun quyidagi kanallarga obuna bo‘ling:\n\n"
            + "\n".join(data["channels"]),
            reply_markup=buttons
        )
        return

    # Agar obuna bo‘lsa
    await message.answer(
        f"Salom @{message.from_user.username}!\n\n"
        "✅ Siz konkursga qo‘shildingiz!\n"
        "🏆 Yutish imkoniyatini oshirish uchun do‘stlaringizni referal link orqali taklif qiling!",
        reply_markup=get_menu(user_id)
    )

# ---------------- CALLBACK HANDLER ----------------
@dp.callback_query_handler(lambda call: call.data == "check_sub")
async def check_sub_callback(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.message.edit_text(
            "✅ Tabriklaymiz! Siz konkursga qo‘shildingiz!\n\n"
            "🏆 Yutish imkoniyatini oshirish uchun referal tizimidan foydalaning.",
        )
    else:
        await call.answer("❌ Hali hamma kanallarga obuna bo‘lmadingiz!", show_alert=True)

# ---------------- REYTING ----------------
@dp.message_handler(lambda message: message.text == "Reyting 🏆")
async def show_reyting(message: types.Message):
    sorted_users = sorted(data["users"].items(), key=lambda x: x[1]["points"], reverse=True)
    text = "🏆 Reyting:\n\n"
    for i, (uid, info) in enumerate(sorted_users, 1):
        text += f"{i}. @{info.get('username','')} - {info.get('points',0)} ball (Ref: {len(info['referrals'])})\n"
    await message.reply(text)

# ---------------- REFERAL ----------------
@dp.message_handler(lambda message: message.text == "Referal ✅")
async def show_ref(message: types.Message):
    user_id = str(message.from_user.id)
    link = f"https://t.me/mansurovkonkursbot?start={user_id}"
    await message.reply(
        "🔗 Sizning referal linkingiz:\n"
        f"{link}\n\n"
        "Taklif qilgan har bir do‘stingiz uchun <b>+5 ball</b> qo‘shiladi!"
    )

# ---------------- KONTAKT ADMIN ----------------
@dp.message_handler(lambda message: message.text == "Kontakt admin 📩")
async def contact_admin(message: types.Message):
    await message.reply("Admin bilan bog‘lanish: @CREATOR_SHEYKX")

# ---------------- BOT ISHGA TUSHISH ----------------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
