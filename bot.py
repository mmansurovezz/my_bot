import json
import os
import random
import re
from collections import Counter
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import ADMINS, BOT_TOKEN

# ── Bot & Dispatcher ──────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())

# ── Persistent data ───────────────────────────────────────────────────────────
DATA_FILE = "data.json"


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"users": {}, "groups": {}}


def save_data(d: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


data = load_data()


def get_group(gid: int) -> dict:
    key = str(gid)
    if key not in data["groups"]:
        data["groups"][key] = {
            "welcome_msg": "👋 {name} guruhga xush keldi!",
            "welcome_enabled": True,
            "rules": "Guruh qoidalari hali belgilanmagan.",
            "notes": {},
            "filters": [],
            "antiflood": False,
            "word_stats": {},
            "user_msg_count": {},
            "warns": {},
        }
    return data["groups"][key]


def get_user(uid: int, name: str = "", username: str = "") -> dict:
    key = str(uid)
    if key not in data["users"]:
        data["users"][key] = {"name": name, "username": username, "total_msgs": 0}
    else:
        if name:
            data["users"][key]["name"] = name
    return data["users"][key]


# ── Helpers ───────────────────────────────────────────────────────────────────
async def is_admin(chat_id: int, user_id: int) -> bool:
    if user_id in ADMINS:
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def parse_time(text: str):
    match = re.fullmatch(r"(\d+)([mhd])", text.lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    if unit == "m":
        return timedelta(minutes=value)
    if unit == "h":
        return timedelta(hours=value)
    if unit == "d":
        return timedelta(days=value)
    return None


async def get_target_user(msg: types.Message):
    if msg.reply_to_message:
        return msg.reply_to_message.from_user
    args = msg.get_args().split()
    if args and args[0].startswith("@"):
        try:
            member = await bot.get_chat_member(msg.chat.id, args[0])
            return member.user
        except Exception:
            pass
    return None


# ── Anti-flood tracker ────────────────────────────────────────────────────────
flood_tracker: dict = {}
FLOOD_LIMIT = 5
FLOOD_WINDOW = 5


def is_flooding(chat_id: int, user_id: int) -> bool:
    now = datetime.now().timestamp()
    flood_tracker.setdefault(chat_id, {}).setdefault(user_id, [])
    ts = flood_tracker[chat_id][user_id]
    ts[:] = [t for t in ts if now - t < FLOOD_WINDOW]
    ts.append(now)
    return len(ts) >= FLOOD_LIMIT


# ── Pending state ─────────────────────────────────────────────────────────────
pending: dict = {}
WARN_LIMIT = 3


# ── /start ────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["start"])
async def cmd_start(msg: types.Message):
    get_user(msg.from_user.id, msg.from_user.full_name, msg.from_user.username or "")
    save_data(data)
    await msg.answer(
        "🤖 <b>Admin Yordamchi Bot</b>\n\n"
        "Men guruhlar uchun kuchli admin yordamchisiman!\n\n"
        "📋 <b>Asosiy buyruqlar:</b>\n"
        "/help — Barcha buyruqlar\n"
        "/admin — Bot admin paneli\n\n"
        "Guruhga qo'shib <b>/help</b> yozing! 🚀"
    )


# ── /help ─────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["help"])
async def cmd_help(msg: types.Message):
    await msg.answer(
        "📖 <b>Barcha buyruqlar:</b>\n\n"
        "⚙️ <b>Admin buyruqlari (guruhda):</b>\n"
        "/ban @user [sabab] — Foydalanuvchini ban\n"
        "/unban @user — Banni ochish\n"
        "/kick @user [sabab] — Guruhdan chiqarish\n"
        "/mute @user [10m/2h/1d] — Ovozini o'chirish\n"
        "/unmute @user — Ovozini ochish\n"
        "/warn @user [sabab] — Ogohlantirish (3 ta = ban)\n"
        "/warns @user — Ogohlantirishlar soni\n"
        "/resetwarn @user — Ogohlantirishlarni tozalash\n"
        "/pin — Xabarni pin (reply)\n"
        "/unpin — Pinni ochish\n\n"
        "🔧 <b>Guruh sozlamalari (admin):</b>\n"
        "/setwelcome <matn> — Xush kelibsiz xabar ({name}, {group})\n"
        "/welcome on|off — Yoqish/o'chirish\n"
        "/setrules <matn> — Qoidalarni belgilash\n"
        "/rules — Qoidalarni ko'rish\n"
        "/setnote <nom> <matn> — Eslatma saqlash\n"
        "/note <nom> — Eslatmani olish\n"
        "/notes — Barcha eslatmalar\n"
        "/filter add <so'z> — Taqiqlangan so'z qo'shish\n"
        "/filter remove <so'z> — O'chirish\n"
        "/filter list — Ko'rish\n"
        "/antiflood on|off — Flood himoyasi\n\n"
        "📊 <b>Statistika:</b>\n"
        "/stats — Guruh/bot statistikasi\n"
        "/topwords — Ko'p ishlatilgan so'zlar TOP-10\n"
        "/topusers — Eng faol a'zolar TOP-10\n"
        "/mystats — Sizning statistikangiz\n\n"
        "🎮 <b>Ko'ngil ochar:</b>\n"
        "/dice — Zar tashlash 🎲\n"
        "/coin — Tanga tashlash 🪙\n"
        "/choose v1 | v2 | ... — Tasodifiy tanlash\n"
        "/calc <ifoda> — Hisoblash\n"
        "/quote — Tasodifiy iqtibos\n\n"
        "🔍 <b>Ma'lumot:</b>\n"
        "/id — Chat/foydalanuvchi ID\n"
        "/info — Foydalanuvchi haqida\n\n"
        "📢 <b>Bot admin (faqat superadmin):</b>\n"
        "/broadcast — Hammaga xabar\n"
        "/usercount — Foydalanuvchilar soni\n"
        "/admin — Admin paneli\n"
    )


# ── /id ───────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["id"])
async def cmd_id(msg: types.Message):
    if msg.reply_to_message:
        u = msg.reply_to_message.from_user
        await msg.reply(
            f"👤 <b>Foydalanuvchi ID:</b> <code>{u.id}</code>\n"
            f"💬 <b>Chat ID:</b> <code>{msg.chat.id}</code>"
        )
    else:
        await msg.reply(
            f"👤 <b>Sizning ID:</b> <code>{msg.from_user.id}</code>\n"
            f"💬 <b>Chat ID:</b> <code>{msg.chat.id}</code>"
        )


# ── /info ─────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["info"])
async def cmd_info(msg: types.Message):
    target = msg.reply_to_message.from_user if msg.reply_to_message else msg.from_user
    username = f"@{target.username}" if target.username else "—"
    status = "—"
    try:
        member = await bot.get_chat_member(msg.chat.id, target.id)
        status_map = {
            "creator": "👑 Guruh egasi",
            "administrator": "🛡 Admin",
            "member": "👤 A'zo",
            "restricted": "🔇 Cheklangan",
            "left": "🚪 Chiqib ketgan",
            "kicked": "🚫 Ban",
        }
        status = status_map.get(member.status, member.status)
    except Exception:
        pass
    await msg.reply(
        f"ℹ️ <b>Foydalanuvchi ma'lumoti:</b>\n"
        f"👤 Ism: {target.full_name}\n"
        f"🆔 ID: <code>{target.id}</code>\n"
        f"📛 Username: {username}\n"
        f"📌 Holat: {status}"
    )


# ── /ban ──────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["ban"])
async def cmd_ban(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return await msg.reply("❌ Bu buyruq faqat guruhlarda ishlaydi.")
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    target = await get_target_user(msg)
    if not target:
        return await msg.reply("❌ Foydalanuvchini ko'rsating (reply yoki @username).")
    if await is_admin(msg.chat.id, target.id):
        return await msg.reply("⛔ Adminni ban qilib bo'lmaydi.")
    args = msg.get_args().split()
    reason = " ".join(args[1:]) if (args and args[0].startswith("@")) else " ".join(args)
    try:
        await bot.kick_chat_member(msg.chat.id, target.id)
        text = f"🚫 {target.mention} ban qilindi."
        if reason:
            text += f"\n📌 Sabab: {reason}"
        await msg.answer(text)
    except Exception as e:
        await msg.reply(f"❌ Xato: {e}")


# ── /unban ────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["unban"])
async def cmd_unban(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return await msg.reply("❌ Bu buyruq faqat guruhlarda ishlaydi.")
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    target = await get_target_user(msg)
    if not target:
        return await msg.reply("❌ Foydalanuvchini ko'rsating.")
    try:
        await bot.unban_chat_member(msg.chat.id, target.id)
        await msg.answer(f"✅ {target.mention} bani ochildi.")
    except Exception as e:
        await msg.reply(f"❌ Xato: {e}")


# ── /kick ─────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["kick"])
async def cmd_kick(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return await msg.reply("❌ Bu buyruq faqat guruhlarda ishlaydi.")
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    target = await get_target_user(msg)
    if not target:
        return await msg.reply("❌ Foydalanuvchini ko'rsating.")
    if await is_admin(msg.chat.id, target.id):
        return await msg.reply("⛔ Adminni chiqarib bo'lmaydi.")
    args = msg.get_args().split()
    reason = " ".join(args[1:]) if (args and args[0].startswith("@")) else " ".join(args)
    try:
        await bot.kick_chat_member(msg.chat.id, target.id)
        await bot.unban_chat_member(msg.chat.id, target.id)
        text = f"👢 {target.mention} guruhdan chiqarildi."
        if reason:
            text += f"\n📌 Sabab: {reason}"
        await msg.answer(text)
    except Exception as e:
        await msg.reply(f"❌ Xato: {e}")


# ── /mute ─────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["mute"])
async def cmd_mute(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return await msg.reply("❌ Bu buyruq faqat guruhlarda ishlaydi.")
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    target = await get_target_user(msg)
    if not target:
        return await msg.reply("❌ Foydalanuvchini ko'rsating.")
    if await is_admin(msg.chat.id, target.id):
        return await msg.reply("⛔ Adminni mute qilib bo'lmaydi.")
    args = msg.get_args().split()
    duration = None
    time_label = None
    for arg in args:
        delta = parse_time(arg)
        if delta:
            duration = delta
            time_label = arg
            break
    until_date = (datetime.now() + duration) if duration else None
    try:
        await bot.restrict_chat_member(
            msg.chat.id,
            target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date,
        )
        suffix = f"{time_label} davomida" if time_label else "doimiy"
        await msg.answer(f"🔇 {target.mention} {suffix} mute qilindi.")
    except Exception as e:
        await msg.reply(f"❌ Xato: {e}")


# ── /unmute ───────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["unmute"])
async def cmd_unmute(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return await msg.reply("❌ Bu buyruq faqat guruhlarda ishlaydi.")
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    target = await get_target_user(msg)
    if not target:
        return await msg.reply("❌ Foydalanuvchini ko'rsating.")
    try:
        await bot.restrict_chat_member(
            msg.chat.id,
            target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await msg.answer(f"🔊 {target.mention} mute ochildi.")
    except Exception as e:
        await msg.reply(f"❌ Xato: {e}")


# ── /warn ─────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["warn"])
async def cmd_warn(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return await msg.reply("❌ Bu buyruq faqat guruhlarda ishlaydi.")
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    target = await get_target_user(msg)
    if not target:
        return await msg.reply("❌ Foydalanuvchini ko'rsating.")
    if await is_admin(msg.chat.id, target.id):
        return await msg.reply("⛔ Adminni ogohlantirish mumkin emas.")
    group = get_group(msg.chat.id)
    warns = group.setdefault("warns", {})
    uid_str = str(target.id)
    warns[uid_str] = warns.get(uid_str, 0) + 1
    count = warns[uid_str]
    args = msg.get_args().split()
    reason = " ".join(args[1:]) if (args and args[0].startswith("@")) else " ".join(args)
    text = f"⚠️ {target.mention} ogohlantirish oldi! ({count}/{WARN_LIMIT})"
    if reason:
        text += f"\n📌 Sabab: {reason}"
    if count >= WARN_LIMIT:
        try:
            await bot.kick_chat_member(msg.chat.id, target.id)
            text += f"\n🚫 {WARN_LIMIT} ta ogohlantirish to'ldi — ban qilindi!"
            warns[uid_str] = 0
        except Exception:
            pass
    save_data(data)
    await msg.answer(text)


# ── /warns ────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["warns"])
async def cmd_warns(msg: types.Message):
    target = await get_target_user(msg) or msg.from_user
    group = get_group(msg.chat.id)
    count = group.get("warns", {}).get(str(target.id), 0)
    await msg.reply(f"⚠️ {target.mention}: {count}/{WARN_LIMIT} ogohlantirish")


# ── /resetwarn ────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["resetwarn"])
async def cmd_resetwarn(msg: types.Message):
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    target = await get_target_user(msg)
    if not target:
        return await msg.reply("❌ Foydalanuvchini ko'rsating.")
    group = get_group(msg.chat.id)
    group.setdefault("warns", {})[str(target.id)] = 0
    save_data(data)
    await msg.answer(f"✅ {target.mention} ogohlantirishlari tozalandi.")


# ── /pin ──────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["pin"])
async def cmd_pin(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    if not msg.reply_to_message:
        return await msg.reply("❌ Xabarni reply qilib /pin yuboring.")
    try:
        await bot.pin_chat_message(msg.chat.id, msg.reply_to_message.message_id)
        await msg.answer("📌 Xabar pin qilindi.")
    except Exception as e:
        await msg.reply(f"❌ Xato: {e}")


# ── /unpin ────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["unpin"])
async def cmd_unpin(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    try:
        await bot.unpin_chat_message(msg.chat.id)
        await msg.answer("📌 Pin ochildi.")
    except Exception as e:
        await msg.reply(f"❌ Xato: {e}")


# ── /setwelcome ───────────────────────────────────────────────────────────────
@dp.message_handler(commands=["setwelcome"])
async def cmd_setwelcome(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    text = msg.get_args()
    if not text:
        return await msg.reply("❌ Matn kiriting.\nMasalan: /setwelcome {name} xush keldi!")
    get_group(msg.chat.id)["welcome_msg"] = text
    save_data(data)
    await msg.answer(f"✅ Xush kelibsiz xabari saqlandi:\n{text}")


# ── /welcome ──────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["welcome"])
async def cmd_welcome_toggle(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    arg = msg.get_args().strip().lower()
    if arg not in ("on", "off"):
        return await msg.reply("❌ Foydalanish: /welcome on yoki /welcome off")
    get_group(msg.chat.id)["welcome_enabled"] = arg == "on"
    save_data(data)
    status = "yoqildi ✅" if arg == "on" else "o'chirildi ❌"
    await msg.answer(f"👋 Xush kelibsiz {status}")


# ── /setrules ─────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["setrules"])
async def cmd_setrules(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    text = msg.get_args()
    if not text:
        return await msg.reply("❌ Qoidalarni kiriting.")
    get_group(msg.chat.id)["rules"] = text
    save_data(data)
    await msg.answer("✅ Guruh qoidalari saqlandi.")


# ── /rules ────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["rules"])
async def cmd_rules(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return await msg.reply("❌ Bu buyruq faqat guruhlarda ishlaydi.")
    group = get_group(msg.chat.id)
    await msg.answer(f"📋 <b>Guruh qoidalari:</b>\n\n{group['rules']}")


# ── /setnote ──────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["setnote"])
async def cmd_setnote(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    args = msg.get_args().split(None, 1)
    if len(args) < 2:
        return await msg.reply("❌ Foydalanish: /setnote <nom> <matn>")
    name, text = args[0].lower(), args[1]
    get_group(msg.chat.id)["notes"][name] = text
    save_data(data)
    await msg.answer(f"✅ <b>{name}</b> eslatmasi saqlandi.")


# ── /note ─────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["note"])
async def cmd_note(msg: types.Message):
    name = msg.get_args().strip().lower()
    if not name:
        return await msg.reply("❌ Eslatma nomini kiriting: /note <nom>")
    note = get_group(msg.chat.id)["notes"].get(name)
    if note:
        await msg.answer(f"📝 <b>{name}:</b>\n{note}")
    else:
        await msg.answer(f"❌ <b>{name}</b> nomli eslatma topilmadi.")


# ── /notes ────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["notes"])
async def cmd_notes(msg: types.Message):
    notes = get_group(msg.chat.id)["notes"]
    if not notes:
        return await msg.answer("📝 Hech qanday eslatma yo'q.")
    await msg.answer("📝 <b>Eslatmalar:</b>\n" + "\n".join(f"• {n}" for n in notes))


# ── /filter ───────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["filter"])
async def cmd_filter(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    args = msg.get_args().split(None, 1)
    if not args:
        return await msg.reply("❌ Foydalanish: /filter add|remove|list <so'z>")
    group = get_group(msg.chat.id)
    filters: list = group.setdefault("filters", [])
    action = args[0].lower()
    if action == "list":
        if not filters:
            return await msg.answer("🚫 Filter yo'q.")
        return await msg.answer(
            "🚫 <b>Taqiqlangan so'zlar:</b>\n" + "\n".join(f"• {w}" for w in filters)
        )
    if len(args) < 2:
        return await msg.reply("❌ So'zni kiriting.")
    word = args[1].lower()
    if action == "add":
        if word not in filters:
            filters.append(word)
            save_data(data)
            await msg.answer(f"✅ <b>{word}</b> filterlarga qo'shildi.")
        else:
            await msg.answer("⚠️ Bu so'z allaqachon filterlarda.")
    elif action == "remove":
        if word in filters:
            filters.remove(word)
            save_data(data)
            await msg.answer(f"✅ <b>{word}</b> filterlardan o'chirildi.")
        else:
            await msg.answer("⚠️ Bu so'z filterlarda yo'q.")
    else:
        await msg.reply("❌ Foydalanish: /filter add|remove|list <so'z>")


# ── /antiflood ────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["antiflood"])
async def cmd_antiflood(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return
    if not await is_admin(msg.chat.id, msg.from_user.id):
        return await msg.reply("⛔ Siz admin emassiz.")
    arg = msg.get_args().strip().lower()
    if arg not in ("on", "off"):
        return await msg.reply("❌ Foydalanish: /antiflood on yoki /antiflood off")
    get_group(msg.chat.id)["antiflood"] = arg == "on"
    save_data(data)
    status = "yoqildi ✅" if arg == "on" else "o'chirildi ❌"
    await msg.answer(f"🛡 Antiflood {status}")


# ── /stats ────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["stats"])
async def cmd_stats(msg: types.Message):
    if msg.chat.type in ("group", "supergroup"):
        group = get_group(msg.chat.id)
        umc = group.get("user_msg_count", {})
        ws = group.get("word_stats", {})
        await msg.answer(
            f"📊 <b>Guruh statistikasi:</b>\n"
            f"👥 Faol a'zolar: {len(umc)}\n"
            f"💬 Jami xabarlar: {sum(umc.values())}\n"
            f"🔤 Jami so'zlar: {sum(ws.values())}"
        )
    else:
        await msg.answer(
            f"📊 <b>Bot statistikasi:</b>\n"
            f"👥 Foydalanuvchilar: {len(data['users'])}\n"
            f"💬 Guruhlar: {len(data['groups'])}"
        )


# ── /topwords ─────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["topwords"])
async def cmd_topwords(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return await msg.reply("❌ Bu buyruq faqat guruhlarda ishlaydi.")
    ws = get_group(msg.chat.id).get("word_stats", {})
    if not ws:
        return await msg.answer("📊 Hali statistika yo'q.")
    top = Counter(ws).most_common(10)
    lines = "\n".join(f"{i}. <code>{w}</code> — {c} marta" for i, (w, c) in enumerate(top, 1))
    await msg.answer(f"🔤 <b>Ko'p ishlatilgan so'zlar TOP-10:</b>\n\n{lines}")


# ── /topusers ─────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["topusers"])
async def cmd_topusers(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return await msg.reply("❌ Bu buyruq faqat guruhlarda ishlaydi.")
    umc = get_group(msg.chat.id).get("user_msg_count", {})
    if not umc:
        return await msg.answer("📊 Hali statistika yo'q.")
    top = sorted(umc.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = []
    for i, (uid_str, count) in enumerate(top, 1):
        name = data["users"].get(uid_str, {}).get("name", uid_str)
        lines.append(f"{i}. {name} — {count} xabar")
    await msg.answer("👥 <b>Eng faol foydalanuvchilar TOP-10:</b>\n\n" + "\n".join(lines))


# ── /mystats ──────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["mystats"])
async def cmd_mystats(msg: types.Message):
    uid = msg.from_user.id
    user = get_user(uid, msg.from_user.full_name, msg.from_user.username or "")
    total = user.get("total_msgs", 0)
    if msg.chat.type in ("group", "supergroup"):
        group = get_group(msg.chat.id)
        group_msgs = group.get("user_msg_count", {}).get(str(uid), 0)
        warns_count = group.get("warns", {}).get(str(uid), 0)
        await msg.answer(
            f"📊 <b>Sizning statistikangiz:</b>\n"
            f"💬 Bu guruhdagi xabarlar: {group_msgs}\n"
            f"📨 Jami xabarlar: {total}\n"
            f"⚠️ Ogohlantirishlar: {warns_count}/{WARN_LIMIT}"
        )
    else:
        await msg.answer(
            f"📊 <b>Sizning statistikangiz:</b>\n"
            f"📨 Jami xabarlar: {total}"
        )


# ── /dice ─────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["dice"])
async def cmd_dice(msg: types.Message):
    result = random.randint(1, 6)
    faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    await msg.answer(f"🎲 Zar natijasi: {faces[result - 1]} ({result})")


# ── /coin ─────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["coin"])
async def cmd_coin(msg: types.Message):
    result = random.choice(["🟡 Oltin (Heads)", "⚪ Kumush (Tails)"])
    await msg.answer(f"🪙 Tanga: {result}")


# ── /choose ───────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["choose"])
async def cmd_choose(msg: types.Message):
    args = msg.get_args()
    if not args:
        return await msg.reply("❌ Foydalanish: /choose variant1 | variant2 | ...")
    choices = [c.strip() for c in args.split("|") if c.strip()]
    if len(choices) < 2:
        return await msg.reply("❌ Kamida 2 ta variant kiriting (| bilan ajrating).")
    await msg.answer(f"🎯 Tanlandi: <b>{random.choice(choices)}</b>")


# ── /calc ─────────────────────────────────────────────────────────────────────
_SAFE_CALC = re.compile(r"^[\d\s\+\-\*\/\.\(\)\^%]+$")


@dp.message_handler(commands=["calc"])
async def cmd_calc(msg: types.Message):
    expr = msg.get_args().strip()
    if not expr:
        return await msg.reply("❌ Foydalanish: /calc 2+2*3")
    if not _SAFE_CALC.match(expr):
        return await msg.reply("❌ Faqat raqamlar va amallar (+, -, *, /, %, ()) qabul qilinadi.")
    try:
        result = eval(expr.replace("^", "**"), {"__builtins__": {}}, {})  # noqa: S307
        await msg.answer(f"🔢 {expr} = <b>{result}</b>")
    except Exception:
        await msg.reply("❌ Hisoblashda xato.")


# ── /quote ────────────────────────────────────────────────────────────────────
_QUOTES = [
    "Muvaffaqiyat — bu tasodif emas, mehnat natijasidir. 💪",
    "Har bir yangi kun — yangi imkoniyat. 🌅",
    "Qiyinchiliklar seni kuchliroq qiladi. 🏋️",
    "Orzularing katta bo'lsin, harakating undan ham katta. 🚀",
    "Bugun qilmagan ishingni ertaga qilma. ⏰",
    "Bilim — eng katta boylik. 📚",
    "Sabr — muvaffaqiyatning kaliti. 🗝️",
    "Kichik qadamlar ham oldinga harakatdir. 👣",
    "Har bir xato — yangi saboq. 📝",
    "Qo'rqma — boshlash eng qiyin qism. 🎯",
]


@dp.message_handler(commands=["quote"])
async def cmd_quote(msg: types.Message):
    await msg.answer(f"💬 {random.choice(_QUOTES)}")


# ── /broadcast ────────────────────────────────────────────────────────────────
async def do_broadcast(origin: types.Message, text: str) -> None:
    sent = failed = 0
    for uid_str in data["users"]:
        try:
            await bot.send_message(int(uid_str), text)
            sent += 1
        except Exception:
            failed += 1
    await origin.answer(f"✅ Broadcast tugadi!\n📤 Yuborildi: {sent}\n❌ Xato: {failed}")


@dp.message_handler(commands=["broadcast"])
async def cmd_broadcast(msg: types.Message):
    if msg.from_user.id not in ADMINS:
        return await msg.reply("⛔ Siz bot admin emassiz.")
    text = msg.get_args()
    if text:
        await do_broadcast(msg, text)
    else:
        pending[msg.from_user.id] = "broadcast"
        await msg.reply("✍️ Hammaga yuboriladigan xabarni yozing:")


# ── /usercount ────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["usercount"])
async def cmd_usercount(msg: types.Message):
    if msg.from_user.id not in ADMINS:
        return await msg.reply("⛔ Siz bot admin emassiz.")
    await msg.answer(f"👥 Jami foydalanuvchilar: {len(data['users'])}")


# ── /admin ────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["admin"])
async def cmd_admin_panel(msg: types.Message):
    if msg.from_user.id not in ADMINS:
        return await msg.reply("⛔ Siz bot admin emassiz.")
    panel = InlineKeyboardMarkup(row_width=2)
    panel.add(
        InlineKeyboardButton("📊 Statistika", callback_data="adm_stats"),
        InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="adm_users"),
        InlineKeyboardButton("�� Broadcast", callback_data="adm_broadcast"),
    )
    await msg.answer("🛠 <b>Bot Admin Panel</b>", reply_markup=panel)


@dp.callback_query_handler(lambda c: c.data == "adm_stats")
async def cb_adm_stats(c: types.CallbackQuery):
    if c.from_user.id not in ADMINS:
        return await c.answer("⛔ Ruxsat yo'q", show_alert=True)
    await c.message.edit_text(
        f"📊 <b>Bot statistikasi:</b>\n"
        f"👥 Foydalanuvchilar: {len(data['users'])}\n"
        f"💬 Guruhlar: {len(data['groups'])}"
    )


@dp.callback_query_handler(lambda c: c.data == "adm_users")
async def cb_adm_users(c: types.CallbackQuery):
    if c.from_user.id not in ADMINS:
        return await c.answer("⛔ Ruxsat yo'q", show_alert=True)
    await c.message.edit_text(f"👥 Jami foydalanuvchilar: {len(data['users'])}")


@dp.callback_query_handler(lambda c: c.data == "adm_broadcast")
async def cb_adm_broadcast(c: types.CallbackQuery):
    if c.from_user.id not in ADMINS:
        return await c.answer("⛔ Ruxsat yo'q", show_alert=True)
    pending[c.from_user.id] = "broadcast"
    await c.message.answer("✍️ Hammaga yuboriladigan xabarni yozing:")
    await c.answer()


# ── New member welcome ────────────────────────────────────────────────────────
@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def welcome_new_member(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return
    group = get_group(msg.chat.id)
    if not group.get("welcome_enabled", True):
        return
    for member in msg.new_chat_members:
        if member.is_bot:
            continue
        welcome = group.get("welcome_msg", "👋 {name} guruhga xush keldi!")
        welcome = welcome.replace("{name}", member.mention).replace(
            "{group}", msg.chat.title or "guruh"
        )
        await msg.answer(welcome)


# ── Member left ───────────────────────────────────────────────────────────────
@dp.message_handler(content_types=types.ContentType.LEFT_CHAT_MEMBER)
async def member_left(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return
    member = msg.left_chat_member
    if not member.is_bot:
        await msg.answer(f"👋 {member.mention} guruhdan chiqdi.")


# ── General text handler (pending, word stats, flood, filters) ────────────────
@dp.message_handler(content_types=types.ContentType.TEXT)
async def message_tracker(msg: types.Message):
    uid = msg.from_user.id

    # Handle pending broadcast input
    if uid in pending and pending[uid] == "broadcast":
        del pending[uid]
        await do_broadcast(msg, msg.text)
        return

    # Register/update user
    user = get_user(uid, msg.from_user.full_name, msg.from_user.username or "")
    user["total_msgs"] = user.get("total_msgs", 0) + 1

    if msg.chat.type not in ("group", "supergroup"):
        save_data(data)
        return

    group = get_group(msg.chat.id)

    # Anti-flood
    if group.get("antiflood") and not await is_admin(msg.chat.id, uid):
        if is_flooding(msg.chat.id, uid):
            try:
                await bot.restrict_chat_member(
                    msg.chat.id,
                    uid,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=datetime.now() + timedelta(minutes=1),
                )
                await msg.reply("⚠️ Flood aniqlandi! 1 daqiqaga mute qilindi.")
            except Exception:
                pass
            return

    # Word filter
    text_lower = msg.text.lower()
    for banned in group.get("filters", []):
        if banned in text_lower:
            try:
                await msg.delete()
                await msg.answer(
                    f"🚫 {msg.from_user.mention} taqiqlangan so'z ishlatdi — xabar o'chirildi."
                )
            except Exception:
                pass
            break

    # Word statistics (only 3+ letter words)
    words = re.findall(r"[a-zA-Z\u0400-\u04FF\u0600-\u06FF]{3,}", msg.text.lower())
    ws = group.setdefault("word_stats", {})
    for word in words:
        ws[word] = ws.get(word, 0) + 1

    # User message count per group
    umc = group.setdefault("user_msg_count", {})
    umc[str(uid)] = umc.get(str(uid), 0) + 1

    save_data(data)


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
