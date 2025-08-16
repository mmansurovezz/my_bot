import json
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from datetime import datetime

# ---------------- LOGLASH ----------------
logging.basicConfig(level=logging.INFO)

# ---------------- BOT TOKEN ----------------
API_TOKEN = "8461331939:AAFTnBncGUUJA34WUa2NKu-iAAulbymiL1w"
bot = Bot(token=API_TOKEN)
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
    if str(user_id) in data["admins"]:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("Admin panel")],
                [KeyboardButton("Reyting 🏆"), KeyboardButton("Referal ✅")],
                [KeyboardButton("Kontakt admin 📩")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("Reyting 🏆"), KeyboardButton("Referal ✅")],
                [KeyboardButton("Kontakt admin 📩")]
            ],
            resize_keyboard=True
        )

# ---------------- START VA REFERAL ----------------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    args = message.get_args()
    ref_id = args if args else None

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
        logging.info(f"Yangi foydalanuvchi qo'shildi: {user_id}")

    # Kanalni db.json dan olish va tekshirish
    channel_msg_list = []
    for channel_id in data["channels"]:
        try:
            member = await bot.get_chat_member(channel_id, message.from_user.id)
            if member.status in ["member", "administrator", "creator"]:
                channel_msg_list.append(f"Siz kanalga obuna bo‘lgansiz ✅ ({channel_id})")
            else:
                channel_msg_list.append(f"Iltimos kanalga obuna bo‘ling: {channel_id} ❌")
        except:
            channel_msg_list.append(f"Kanalni tekshirib bo‘lmadi: {channel_id}")

    await message.reply(
        f"Salom @{message.from_user.username}!\n"
        "Siz konkursga qo‘shildingiz 🎉\n"
        "Yutish imkoniyatingizni oshirish uchun ko‘proq odamlarni taklif qiling va kanalga obuna bo‘ling ✅\n\n"
        + "\n".join(channel_msg_list),
        reply_markup=get_menu(user_id)
    )

# ---------------- ADMIN PANEL ----------------
@dp.message_handler(lambda message: message.text == "Admin panel")
async def admin_panel(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in data["admins"]:
        await message.reply("Siz admin emassiz ❌")
        return

    admin_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Show admins"), KeyboardButton("Show channels")],
            [KeyboardButton("/addadmin"), KeyboardButton("/deladmin")],
            [KeyboardButton("/addchannel"), KeyboardButton("/delchannel")],
            [KeyboardButton("/randomuser"), KeyboardButton("/stats")],
            [KeyboardButton("/sendall"), KeyboardButton("/save")]
        ],
        resize_keyboard=True
    )
    await message.reply("Admin panel:", reply_markup=admin_keyboard)

# ---------------- SHOW ADMINS & CHANNELS ----------------
@dp.message_handler(lambda message: message.text == "Show admins")
async def show_admins_button(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in data["admins"]:
        await message.reply("Siz admin emassiz ❌")
        return
    admins = "\n".join(data["admins"]) if data["admins"] else "Hech qanday admin yo‘q"
    await message.reply(f"Adminlar ro‘yxati:\n{admins}")

@dp.message_handler(lambda message: message.text == "Show channels")
async def show_channels_button(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in data["admins"]:
        await message.reply("Siz admin emassiz ❌")
        return
    channels = "\n".join(data["channels"]) if data["channels"] else "Hech qanday kanal yo‘q"
    await message.reply(f"Kanallar ro‘yxati:\n{channels}")

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
    await message.reply(f"Sizning referal linkingiz:\n{link}")

# ---------------- KONTAKT ADMIN ----------------
@dp.message_handler(lambda message: message.text == "Kontakt admin 📩")
async def contact_admin(message: types.Message):
    await message.reply("Admin bilan bog‘lanish: @CREATOR_SHEYKX")

# ---------------- ADMIN BUYRUQLARI ----------------
@dp.message_handler(commands=["addadmin"])
async def add_admin(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in data["admins"]:
        await message.reply("Siz admin emassiz ❌")
        return
    args = message.get_args().split()
    for admin_id in args:
        if admin_id not in data["admins"]:
            data["admins"].append(admin_id)
    save_data(data)
    await message.reply("Adminlar qo‘shildi ✅")

@dp.message_handler(commands=["deladmin"])
async def del_admin(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in data["admins"]:
        await message.reply("Siz admin emassiz ❌")
        return
    args = message.get_args().split()
    removed = []
    for admin_id in args:
        if admin_id in data["admins"]:
            data["admins"].remove(admin_id)
            removed.append(admin_id)
    save_data(data)
    if removed:
        await message.reply(f"Quyidagi adminlar o‘chirildi: {', '.join(removed)} ✅")
    else:
        await message.reply("Hech kim o‘chirilmadi ❌")

@dp.message_handler(commands=["addchannel"])
async def add_channel(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in data["admins"]:
        await message.reply("Siz admin emassiz ❌")
        return
    args = message.get_args().split()
    for ch in args:
        if ch not in data["channels"]:
            data["channels"].append(ch)
    save_data(data)
    await message.reply("Kanallar qo‘shildi ✅")

@dp.message_handler(commands=["delchannel"])
async def del_channel(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in data["admins"]:
        await message.reply("Siz admin emassiz ❌")
        return
    args = message.get_args().split()
    removed = []
    for ch in args:
        if ch in data["channels"]:
            data["channels"].remove(ch)
            removed.append(ch)
    save_data(data)
    if removed:
        await message.reply(f"Quyidagi kanallar o‘chirildi: {', '.join(removed)} ✅")
    else:
        await message.reply("Hech qanday kanal o‘chirilmadi ❌")

@dp.message_handler(commands=["randomuser"])
async def random_user(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in data["admins"]:
        await message.reply("Siz admin emassiz ❌")
        return
    if not data["users"]:
        await message.reply("Hech qanday foydalanuvchi yo‘q ❌")
        return
    rand_id, info = random.choice(list(data["users"].items()))
    await message.reply(f"Random foydalanuvchi:\n@{info.get('username','')} ({rand_id})")

@dp.message_handler(commands=["stats"])
async def stats(message: types.Message):
    user_count = len(data["users"])
    admin_count = len(data["admins"])
    channel_count = len(data["channels"])
    await message.reply(f"Foydalanuvchilar: {user_count}\nAdminlar: {admin_count}\nKanallar: {channel_count}")

@dp.message_handler(commands=["sendall"])
async def send_all(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in data["admins"]:
        await message.reply("Siz admin emassiz ❌")
        return
    text = message.get_args()
    for uid in data["users"]:
        try:
            await bot.send_message(uid, text)
        except:
            pass
    await message.reply("Xabar barcha foydalanuvchilarga yuborildi ✅")

@dp.message_handler(commands=["save"])
async def save_info(message: types.Message):
    save_data(data)
    await message.reply("Ma’lumotlar saqlandi ✅")

# ---------------- BOT ISHGA TUSHISH ----------------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
