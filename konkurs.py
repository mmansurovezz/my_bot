import asyncio
import sqlite3
import random
from datetime import datetime
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command, Text
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("8461331939:AAFTnBncGUUJA34WUa2NKu-iAAulbymiL1w")  # Environment variable orqali token olish
ADMINS = [5708983199]  # Asosiy adminlar

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    ref_id INTEGER,
    balance INTEGER DEFAULT 0
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS channels(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS admins(
    user_id INTEGER PRIMARY KEY
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS unsubscribed(
    user_id INTEGER,
    channel_id TEXT,
    left_time TEXT
)""")

conn.commit()

def add_user(user_id, ref_id=None):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users(user_id, ref_id) VALUES (?, ?)", (user_id, ref_id))
        if ref_id:
            cursor.execute("UPDATE users SET balance = balance + 1 WHERE user_id=?", (ref_id,))
        conn.commit()

async def check_subscription(user_id):
    cursor.execute("SELECT channel_id FROM channels")
    channels = cursor.fetchall()
    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch[0], user_id)
            if member.status in ["left", "kicked"]:
                not_subscribed.append(ch[0])
                cursor.execute("INSERT INTO unsubscribed(user_id, channel_id, left_time) VALUES (?, ?, ?)",
                               (user_id, ch[0], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
        except:
            pass
    return not_subscribed

def sub_keyboard(channels):
    kb = InlineKeyboardBuilder()
    for ch in channels:
        kb.row(InlineKeyboardButton(text="✅ Kanalga obuna bo‘lish", url=f"https://t.me/{ch.replace('@','')}"))
    kb.row(InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_subs"))
    return kb.as_markup()

# /start command
@dp.message(Command("start"))
async def start_cmd(message: Message):
    ref_id = None
    if len(message.text.split()) > 1:
        try:
            ref_id = int(message.text.split()[1])
        except:
            pass

    add_user(message.from_user.id, ref_id)

    not_subs = await check_subscription(message.from_user.id)
    if not_subs:
        await message.answer("❗️Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=sub_keyboard(not_subs))
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Referal", callback_data="referal")],
        [InlineKeyboardButton(text="🏆 Reyting", callback_data="reyting")],
        [InlineKeyboardButton(text="🎲 Random foydalanuvchi", callback_data="random")],
        [InlineKeyboardButton(text="✉️ Adminga murojaat", callback_data="murojaat")]
    ])
    await message.answer("Assalomu alaykum! Botga xush kelibsiz!", reply_markup=kb)

# Callbacklar
@dp.callback_query(Text("check_subs"))
async def check_subs(call: CallbackQuery):
    not_subs = await check_subscription(call.from_user.id)
    if not_subs:
        await call.message.edit_text("❗️Hali ham barcha kanallarga obuna bo‘lmadingiz!", reply_markup=sub_keyboard(not_subs))
    else:
        await call.message.edit_text("✅ Obuna tasdiqlandi! Endi botdan foydalanishingiz mumkin.")

@dp.callback_query(Text("referal"))
async def referal(call: CallbackQuery):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
    balance = cursor.fetchone()[0]
    link = f"https://t.me/{(await bot.get_me()).username}?start={call.from_user.id}"
    await call.message.answer(f"👤 Sizning referal linkingiz:\n{link}\n\n💰 Balansingiz: {balance}")

@dp.callback_query(Text("reyting"))
async def reyting(call: CallbackQuery):
    cursor.execute("SELECT user_id FROM admins")
    admin_ids = set([row[0] for row in cursor.fetchall()])

    cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 20")
    top = cursor.fetchall()

    text_admin = "🏆 <b>Adminlar reytingi:</b>\n"
    text_users = "\n👥 <b>Oddiy foydalanuvchilar reytingi:</b>\n"

    a_count, u_count = 1, 1
    for user_id, balance in top:
        tag = f"<a href='tg://user?id={user_id}'>Foydalanuvchi</a> — {balance} referal\n"
        if user_id in admin_ids:
            text_admin += f"{a_count}. {tag}"
            a_count += 1
        else:
            text_users += f"{u_count}. {tag}"
            u_count += 1

    await call.message.answer(text_admin + text_users)

@dp.callback_query(Text("random"))
async def random_user(call: CallbackQuery):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    if users:
        winner = random.choice(users)[0]
        await call.message.answer(f"🎉 Random tanlov natijasi: <a href='tg://user?id={winner}'>G‘olib</a>")
    else:
        await call.message.answer("❌ Foydalanuvchilar yo‘q")

@dp.callback_query(Text("murojaat"))
async def murojaat(call: CallbackQuery):
    await call.message.answer("✍️ Adminga murojaat qilmoqchi bo‘lsangiz, xabaringizni yozing:")

    # Keyingi xabar adminlarga yuborish
    @dp.message()
    async def forward_to_admin(message: Message):
        for admin in ADMINS:
            await bot.send_message(admin, f"📩 Yangi murojaat:\n\n{message.from_user.id} ({message.from_user.full_name})\n\n{message.text}")
        await message.answer("✅ Murojaatingiz adminga yuborildi.")

async def main():
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
