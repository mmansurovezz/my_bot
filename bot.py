import logging
import sqlite3
import random
import json
import asyncio
from aiogram import Bot, Dispatcher, executor, types

# === CONFIG ===
BOT_TOKEN = "8461331939:AAFTnBncGUUJA34WUa2NKu-iAAulbymiL1w"
BOT_USERNAME = "mansurovkonkursbot"
DEFAULT_CHANNEL = "@allgamessavdo"
ADMIN_IDS = [5708983199]
CHANNEL_FILE = "channels.json"

# === DATABASE ===
conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    invited_by INTEGER,
    joined_channel BOOLEAN DEFAULT 0
)
""")
conn.commit()

# === BOT SETUP ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# === UTILS ===
def load_channels():
    try:
        with open(CHANNEL_FILE, "r") as f:
            return json.load(f)
    except:
        return [DEFAULT_CHANNEL]

def save_channels(channels):
    with open(CHANNEL_FILE, "w") as f:
        json.dump(channels, f)

async def check_subscription(user_id):
    channels = load_channels()
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# === MONITOR UNSUBSCRIBED USERS ===
async def monitor_unsubscribed():
    while True:
        cursor.execute("SELECT user_id FROM users WHERE joined_channel=1")
        users = cursor.fetchall()
        for user in users:
            user_id = user[0]
            if not await check_subscription(user_id):
                cursor.execute("UPDATE users SET joined_channel=0 WHERE user_id=?", (user_id,))
                conn.commit()
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, f"⚠️ <a href='tg://user?id={user_id}'>Foydalanuvchi</a> kanalni tark etdi.")
                    except:
                        continue
        await asyncio.sleep(600)  # 10 daqiqada bir marta tekshiradi

# === HANDLERS ===
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()
    invited_by = int(args) if args.isdigit() else None

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, invited_by) VALUES (?, ?)", (user_id, invited_by))
        conn.commit()

    if not await check_subscription(user_id):
        await message.answer("Botdan foydalanish uchun quyidagi kanal(lar)ga obuna bo‘ling:\n" +
                             "\n".join(load_channels()))
        return

    cursor.execute("UPDATE users SET joined_channel=1 WHERE user_id=?", (user_id,))
    conn.commit()

    await message.answer("🎉 Xush kelibsiz! Siz konkursda ishtirok etyapsiz.")

@dp.message_handler(commands=["referal"])
async def referral_handler(message: types.Message):
    user_id = message.from_user.id
    link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    cursor.execute("SELECT COUNT(*) FROM users WHERE invited_by=?", (user_id,))
    count = cursor.fetchone()[0]
    await message.answer(f"🔗 Sizning referal havolangiz:\n{link}\n👥 Taklif qilganlar soni: {count}")

@dp.message_handler(commands=["rating"])
async def rating_handler(message: types.Message):
    cursor.execute("""
        SELECT invited_by, COUNT(*) as total FROM users 
        WHERE invited_by IS NOT NULL GROUP BY invited_by ORDER BY total DESC LIMIT 10
    """)
    rows = cursor.fetchall()
    text = "🏆 Top 10 Referal Reyting:\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. <a href='tg://user?id={row[0]}'>User</a> — {row[1]} ta taklif\n"
    await message.answer(text)

@dp.message_handler(commands=["winner"])
async def winner_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    cursor.execute("SELECT user_id FROM users WHERE joined_channel=1")
    users = cursor.fetchall()
    if not users:
        await message.answer("Faol ishtirokchilar topilmadi.")
        return
    winner = random.choice(users)[0]
    await message.answer(f"🎉 Random g‘olib: <a href='tg://user?id={winner}'>User</a>")

@dp.message_handler(commands=["broadcast"])
async def broadcast_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text.replace("/broadcast ", "")
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    count = 0
    for user in users:
        try:
            await bot.send_message(user[0], text)
            count += 1
        except:
            continue
    await message.answer(f"📢 Xabar {count} foydalanuvchiga yuborildi.")

@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE joined_channel=1")
    joined = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE joined_channel=0")
    left = cursor.fetchone()[0]
    await message.answer(f"🛠 Admin Panel:\n👥 Umumiy: {total}\n✅ Obuna bo‘lganlar: {joined}\n🚪 Chiqib ketganlar: {left}")

@dp.message_handler(commands=["addchannel"])
async def add_channel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    channel = message.get_args()
    channels = load_channels()
    if channel not in channels:
        channels.append(channel)
        save_channels(channels)
        await message.answer(f"✅ Kanal qo‘shildi: {channel}")
    else:
        await message.answer("⚠️ Bu kanal allaqachon ro‘yxatda.")

@dp.message_handler(commands=["removechannel"])
async def remove_channel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    channel = message.get_args()
    channels = load_channels()
    if channel in channels:
        channels.remove(channel)
        save_channels(channels)
        await message.answer(f"❌ Kanal o‘chirildi: {channel}")
    else:
        await message.answer("⚠️ Bu kanal ro‘yxatda yo‘q.")

# === RUN ===
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_unsubscribed())
    executor.start_polling(dp, loop=loop)
