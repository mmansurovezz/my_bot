from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN, ADMINS, CHANNELS, REFERAL_BALL, USERS
import random

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Menyular
user_menu = ReplyKeyboardMarkup(resize_keyboard=True)
user_menu.add(
    KeyboardButton("🏆 Reyting"),
    KeyboardButton("✅ Referal"),
    KeyboardButton("📩 Admin bilan bog‘lanish")
)

admin_panel = InlineKeyboardMarkup(row_width=2)
admin_panel.add(
    InlineKeyboardButton("📊 Statistikalar", callback_data="stats"),
    InlineKeyboardButton("🎲 Random tanlash", callback_data="random"),
    InlineKeyboardButton("📢 Hammaga xabar", callback_data="broadcast"),
    InlineKeyboardButton("➕ Admin qo‘shish", callback_data="add_admin"),
    InlineKeyboardButton("➖ Admin chiqarish", callback_data="remove_admin"),
    InlineKeyboardButton("➕ Kanal qo‘shish", callback_data="add_channel"),
    InlineKeyboardButton("➖ Kanal chiqarish", callback_data="remove_channel")
)

pending_admin_action = {}
pending_channel_action = {}
pending_broadcast = {}

# /start
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    ref_id = None
    if message.get_args():
        try:
            ref_id = int(message.get_args())
        except:
            pass

    if user_id not in USERS:
        USERS[user_id] = {"ref": ref_id, "score": 0, "joined": False}
        if ref_id and ref_id in USERS:
            USERS[ref_id]["score"] += REFERAL_BALL

    await message.answer("🎉 Xush kelibsiz! Siz konkursda ishtirok etyapsiz.", reply_markup=user_menu)

# Reyting
@dp.message_handler(lambda msg: msg.text == "🏆 Reyting")
async def show_rating(msg: types.Message):
    sorted_users = sorted(USERS.items(), key=lambda x: x[1]["score"], reverse=True)
    text = "🏆 Reyting:\n"
    for i, (uid, data) in enumerate(sorted_users[:10], 1):
        text += f"{i}. {uid} — {data['score']} ball\n"
    await msg.answer(text)

# Referal
@dp.message_handler(lambda msg: msg.text == "✅ Referal")
async def referal_link(msg: types.Message):
    link = f"https://t.me/{(await bot.get_me()).username}?start={msg.from_user.id}"
    await msg.answer(f"🔗 Sizning referal linkingiz:\n{link}")

# Admin bilan bog‘lanish
@dp.message_handler(lambda msg: msg.text == "📩 Admin bilan bog‘lanish")
async def contact_admin(msg: types.Message):
    await msg.answer("✍️ Savolingizni yozing:")
    pending_admin_action[msg.from_user.id] = "contact"

@dp.message_handler(lambda msg: msg.from_user.id in pending_admin_action and pending_admin_action[msg.from_user.id] == "contact")
async def handle_contact(msg: types.Message):
    for admin_id in ADMINS:
        await bot.send_message(admin_id, f"📩 Yangi xabar:\n{msg.text}\n👤 From: {msg.from_user.full_name}")
    await msg.answer("✅ Xabaringiz adminga yuborildi.")
    pending_admin_action.pop(msg.from_user.id)

# /admin
@dp.message_handler(commands=["admin"])
async def admin_handler(msg: types.Message):
    if msg.from_user.id in ADMINS:
        await msg.answer("🛠 Admin Panel:", reply_markup=admin_panel)
    else:
        await msg.answer("⛔ Siz admin emassiz.")

# Kanal monitoringi
@dp.chat_member_handler()
async def channel_monitor(event: ChatMemberUpdated):
    user = event.from_user
    chat = event.chat
    status = event.new_chat_member.status
    if chat.id in CHANNELS:
        if status == "member":
            USERS[user.id]["joined"] = True
        elif status == "left":
            USERS[user.id]["joined"] = False

# Callbacklar
@dp.callback_query_handler(lambda c: c.data == "stats")
async def stats_handler(c: types.CallbackQuery):
    total = len(USERS)
    joined = sum(1 for u in USERS.values() if u["joined"])
    left = total - joined
    await c.message.answer(f"📊 Statistikalar:\nUmumiy: {total}\nObuna: {joined}\nChiqib ketgan: {left}")

@dp.callback_query_handler(lambda c: c.data == "random")
async def random_handler(c: types.CallbackQuery):
    if USERS:
        winner = random.choice(list(USERS.keys()))
        await c.message.answer(f"🎉 G‘olib: {winner}")
    else:
        await c.message.answer("❌ Ishtirokchilar yo‘q.")

@dp.callback_query_handler(lambda c: c.data == "broadcast")
async def broadcast_prompt(c: types.CallbackQuery):
    pending_broadcast[c.from_user.id] = True
    await c.message.answer("✍️ Hammaga yuboriladigan xabarni yozing:")

@dp.message_handler(lambda msg: msg.from_user.id in pending_broadcast)
async def handle_broadcast(msg: types.Message):
    for uid in USERS:
        try:
            await bot.send_message(uid, msg.text)
        except:
            continue
    await msg.answer("✅ Xabar yuborildi.")
    pending_broadcast.pop(msg.from_user.id)

@dp.callback_query_handler(lambda c: c.data == "add_admin")
async def add_admin_prompt(c: types.CallbackQuery):
    pending_admin_action[c.from_user.id] = "add"
    await c.message.answer("🆕 Admin qo‘shish uchun user_id yuboring:")

@dp.callback_query_handler(lambda c: c.data == "remove_admin")
async def remove_admin_prompt(c: types.CallbackQuery):
    pending_admin_action[c.from_user.id] = "remove"
    await c.message.answer("🗑 Admin o‘chirish uchun user_id yuboring:")

@dp.message_handler(lambda msg: msg.from_user.id in pending_admin_action and pending_admin_action[msg.from_user.id] in ["add", "remove"])
async def handle_admin_change(msg: types.Message):
    action = pending_admin_action.pop(msg.from_user.id)
    try:
        uid = int(msg.text.strip())
        if action == "add":
            if uid not in ADMINS:
                ADMINS.append(uid)
                await msg.answer(f"✅ Admin qo‘shildi: {uid}")
            else:
                await msg.answer("⚠️ Bu user allaqachon admin.")
        else:
            if uid in ADMINS:
                ADMINS.remove(uid)
                await msg.answer(f"❌ Admin o‘chirildi: {uid}")
            else:
                await msg.answer("⚠️ Bu user admin emas.")
    except:
        await msg.answer("❌ Noto‘g‘ri ID.")

@dp.callback_query_handler(lambda c: c.data == "add_channel")
async def add_channel_prompt(c: types.CallbackQuery):
    pending_channel_action[c.from_user.id] = "add"
    await c.message.answer("📥 Kanal ID ni yuboring:")

@dp.callback_query_handler(lambda c: c.data == "remove_channel")
async def remove_channel_prompt(c: types.CallbackQuery):
    pending_channel_action[c.from_user.id] = "remove"
    await c.message.answer("🗑 Kanal ID ni yuboring:")

@dp.message_handler(lambda msg: msg.from_user.id in pending_channel_action)
async def handle_channel_change(msg: types.Message):
    action = pending_channel_action.pop(msg.from_user.id)
    try:
        cid = int(msg.text.strip())
        if action == "add":
            if cid not in CHANNELS:
                CHANNELS.append(cid)
                await msg.answer(f"✅ Kanal qo‘shildi: {cid}")
            else:
                await msg.answer("⚠️ Kanal allaqachon ro‘yxatda.")
        else:
            if cid in CHANNELS:
                CHANNELS.remove(cid)
                await msg.answer(f"❌ Kanal o‘chirildi: {cid}")
            else:
                await msg.answer("⚠️ Kanal ro‘yxatda yo‘q.")
    except:
        await msg.answer("❌ Noto‘g‘ri ID.")

# Botni ishga tushirish
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
