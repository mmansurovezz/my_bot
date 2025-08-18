import asyncio
import sqlite3
import random
from datetime import datetime
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

# ==============================
# 1. Token va adminlar
# ==============================
TOKEN = os.getenv("8461331939:AAFTnBncGUUJA34WUa2NKu-iAAulbymiL1w") or "8461331939:AAFTnBncGUUJA34WUa2NKu-iAAulbymiL1w"
ADMINS = [5708983199]

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# ==============================
# 2. Bazani yaratish va ulash
# ==============================
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

# ==============================
# 3. Foydalanuvchi qo'shish va referal
# ==============================
def add_user(user_id, ref_id=None):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users(user_id, ref_id) VALUES (?, ?)", (user_id, ref_id))
        if ref_id:
            cursor.execute("UPDATE users SET balance = balance + 1 WHERE user_id=?", (ref_id,))
        conn.commit()

# ==============================
# 4. Kanalga obuna tekshirish
# ==============================
async def check_subscription(user_id):
    cursor.execute("SELECT channel_id FROM channels")
    channels = cursor.fetchall()
    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch[0], user_id)
            if member.status in ["left", "kicked"]:
                not_subscribed.append(ch[0])
                cursor.execute(
                    "INSERT INTO unsubscribed(user_id, channel_id, left_time) VALUES (?, ?, ?)",
                    (user_id, ch[0], datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
        except:
            pass
    return not_subscribed

# ==============================
# 5. Obuna uchun klaviatura
# ==============================
def sub_keyboard(channels):
    kb = InlineKeyboardMarkup()
    for ch in channels:
        kb.add(InlineKeyboardButton(text="✅ Kanalga obuna bo‘lish", url=f"https://t.me/{ch.replace('@','')}"))
    kb.add(InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_subs"))
    return kb

# ==============================
# 6. /start buyrug'i
# ==============================
@dp.message(lambda m: m.text and m.text.startswith("/start"))
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
        await message.answer(
            "❗️Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:",
            reply_markup=sub_keyboard(not_subs)
        )
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Referal", callback_data="referal")],
        [InlineKeyboardButton(text="🏆 Reyting", callback_data="reyting")],
        [InlineKeyboardButton(text="🎲 Random foydalanuvchi", callback_data="random")],
        [InlineKeyboardButton(text="✉️ Adminga murojaat", callback_data="murojaat")]
    ])
    await message.answer("Assalomu alaykum! Botga xush kelibsiz!", reply_markup=kb)

# ==============================
# 7. Obuna tekshirish tugmasi
# ==============================
@dp.callback_query(lambda c: c.data == "check_subs")
async def check_subs(call: CallbackQuery):
    not_subs = await check_subscription(call.from_user.id)
    if not_subs:
        await call.message.edit_text(
            "❗️Hali ham barcha kanallarga obuna bo‘lmadingiz!",
            reply_markup=sub_keyboard(not_subs)
        )
    else:
        await call.message.edit_text("✅ Obuna tasdiqlandi! Endi botdan foydalanishingiz mumkin.")

# ==============================
# 8. Referal
# ==============================
@dp.callback_query(lambda c: c.data == "referal")
async def referal(call: CallbackQuery):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
    balance = cursor.fetchone()[0]
    link = f"https://t.me/{(await bot.get_me()).username}?start={call.from_user.id}"
    await call.message.answer(f"👤 Sizning referal linkingiz:\n{link}\n\n💰 Balansingiz: {balance}")

# ==============================
# 9. Reyting
# ==============================
@dp.callback_query(lambda c: c.data == "reyting")
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

# ==============================
# 10. Random foydalanuvchi
# ==============================
@dp.callback_query(lambda c: c.data == "random")
async def random_user(call: CallbackQuery):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    if users:
        winner = random.choice(users)[0]
        await call.message.answer(f"🎉 Random tanlov natijasi: <a href='tg://user?id={winner}'>G‘olib</a>")
    else:
        await call.message.answer("❌ Foydalanuvchilar yo‘q")

# ==============================
# 11. Adminga murojaat
# ==============================
@dp.callback_query(lambda c: c.data == "murojaat")
async def murojaat(call: CallbackQuery):
    await call.message.answer("✍️ Adminga murojaat qilmoqchi bo‘lsangiz, xabaringizni yozing:")
    dp.message.register(forward_to_admin, lambda m: m.chat.id == call.from_user.id)

async def forward_to_admin(message: Message):
    for admin in ADMINS:
        await bot.send_message(admin, f"📩 Yangi murojaat:\n\n{message.from_user.id} ({message.from_user.full_name})\n\n{message.text}")
    await message.answer("✅ Murojaatingiz adminga yuborildi.")

# ==============================
# 12. Admin panel va funksiyalar
# ==============================
@dp.message(lambda m: m.text and m.text.startswith("/admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMINS:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Hammaga xabar", callback_data="broadcast")],
        [InlineKeyboardButton(text="➕ Kanal qo‘shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="➖ Kanal o‘chirish", callback_data="del_channel")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar soni", callback_data="users_count")],
        [InlineKeyboardButton(text="👤 Adminlar boshqaruvi", callback_data="manage_admins")],
        [InlineKeyboardButton(text="🚪 Chiqqanlar ro‘yxati", callback_data="left_users")]
    ])
    await message.answer("⚙️ Admin panel", reply_markup=kb)

# ==============================
# 13. Broadcast
# ==============================
@dp.callback_query(lambda c: c.data == "broadcast")
async def broadcast_start(call: CallbackQuery):
    await call.message.answer("📨 Hammaga yuboriladigan xabarni yozing:")
    dp.message.register(broadcast_message)

async def broadcast_message(message: Message):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent = 0
    for user in users:
        try:
            await bot.send_message(user[0], message.text)
            sent += 1
        except:
            pass
    await message.answer(f"✅ {sent} ta foydalanuvchiga yuborildi.")

# ==============================
# 14. Kanal qo‘shish/o‘chirish
# ==============================
@dp.callback_query(lambda c: c.data == "add_channel")
async def add_channel_start(call: CallbackQuery):
    await call.message.answer("📌 Qo‘shmoqchi bo‘lgan kanal username (@kanal) ni yuboring:")
    dp.message.register(add_channel_db)

async def add_channel_db(message: Message):
    cursor.execute("INSERT INTO channels(channel_id) VALUES (?)", (message.text,))
    conn.commit()
    await message.answer("✅ Kanal qo‘shildi.")

@dp.callback_query(lambda c: c.data == "del_channel")
async def del_channel_start(call: CallbackQuery):
    await call.message.answer("❌ O‘chirish uchun kanal username (@kanal) ni yuboring:")
    dp.message.register(del_channel_db)

async def del_channel_db(message: Message):
    cursor.execute("DELETE FROM channels WHERE channel_id=?", (message.text,))
    conn.commit()
    await message.answer("✅ Kanal o‘chirildi.")

# ==============================
# 15. Foydalanuvchilar soni
# ==============================
@dp.callback_query(lambda c: c.data == "users_count")
async def users_count(call: CallbackQuery):
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    await call.message.answer(f"👥 Bot foydalanuvchilari soni: {count}")

# ==============================
# 16. Admin boshqaruvi
# ==============================
@dp.callback_query(lambda c: c.data == "manage_admins")
async def manage_admins(call: CallbackQuery):
    await call.message.answer("➕Admin qo‘shish uchun: `/addadmin user_id`\n➖Admin o‘chirish uchun: `/deladmin user_id`")

@dp.message(lambda m: m.text and m.text.startswith("/addadmin"))
async def add_admin(message: Message):
    if message.from_user.id not in ADMINS:
        return
    try:
        new_admin = int(message.text.split()[1])
        cursor.execute("INSERT OR IGNORE INTO admins(user_id) VALUES (?)", (new_admin,))
        conn.commit()
        await message.answer("✅ Admin qo‘shildi.")
    except:
        await message.answer("❌ Noto‘g‘ri format. Misol: /addadmin 123456789")

@dp.message(lambda m: m.text and m.text.startswith("/deladmin"))
async def del_admin(message: Message):
    if message.from_user.id not in ADMINS:
        return
    try:
        old_admin = int(message.text.split()[1])
        cursor.execute("DELETE FROM admins WHERE user_id=?", (old_admin,))
        conn.commit()
        await message.answer("✅ Admin o‘chirildi.")
    except:
        await message.answer("❌ Noto‘g‘ri format. Misol: /deladmin 123456789")

# ==============================
# 17. Chiqqanlar ro‘yxati
# ==============================
@dp.callback_query(lambda c: c.data == "left_users")
async def show_left_users(call: CallbackQuery):
    cursor.execute("SELECT user_id, channel_id, left_time FROM unsubscribed ORDER BY left_time DESC LIMIT 10")
    rows = cursor.fetchall()
    if not rows:
        await call.message.answer("✅ Hozircha hech kim chiqmagan.")
        return

    text = "🚪 <b>Kanaldan chiqqanlar:</b>\n\n"
    for user_id, channel_id, time in rows:
        text += f"👤 <a href='tg://user?id={user_id}'>User</a>\n📤 Kanal: {channel_id}\n🕒 Vaqt: {time}\n\n"

    await call.message.answer(text)

# ==============================
# 18. Botni ishga tushirish
# ==============================
async def main():
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
