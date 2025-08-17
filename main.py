from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import asyncio
import os

# ===== KONFIGURASI BOT =====
TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
ADMIN_IDS = [int(x) for x in (os.getenv("ADMIN_IDS") or "6046272730").split(",")]
TOPICS = {
    "Menfess": -1005071,
    "Pap Pisang": -1005052,
    "Pap Cwo": -1005052,
    "Pap Lacur": -1005048,
    "Eksib": -1005529,
    "Moan Cwo": -1005013,
    "Moan Cwe": -1005046,
}

# Simpan state sementara user
user_state = {}

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    await show_topics(update, context)

async def show_topics(update, context):
    keyboard = [[InlineKeyboardButton(name, callback_data=f"topic_{name}")] for name in TOPICS.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 Pilih tujuan pengiriman:", reply_markup=reply_markup)

# ===== PILIH TOPIK =====
async def topic_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    topic_name = query.data.replace("topic_", "")
    user_state[user_id] = {"topic": topic_name}

    # Pilihan auto-delete
    keyboard = [
        [
            InlineKeyboardButton("Tidak", callback_data="delete_none"),
            InlineKeyboardButton("30 menit", callback_data="delete_30"),
            InlineKeyboardButton("1 jam", callback_data="delete_60"),
            InlineKeyboardButton("2 jam", callback_data="delete_120")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(f"✅ Kamu pilih topik: {topic_name}\n🕒 Pilih opsi hapus otomatis:", reply_markup=reply_markup)

# ===== PILIH AUTO-DELETE =====
async def auto_delete_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data

    if choice == "delete_none":
        user_state[user_id]["auto_delete"] = False
        user_state[user_id]["delete_minutes"] = 0
    else:
        user_state[user_id]["auto_delete"] = True
        minutes = int(choice.split("_")[1])
        user_state[user_id]["delete_minutes"] = minutes

    keyboard = [[InlineKeyboardButton("Reset / Pilih Topik Baru", callback_data="reset")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("✅ Pilihan tersimpan. Sekarang kirim media atau pesanmu.", reply_markup=reply_markup)

# ===== RESET =====
async def reset_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in user_state:
        del user_state[user_id]
    await show_topics(query, context)

# ===== HANDLE MEDIA / PESAN =====
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    uid = update.message.from_user.id
    if uid not in user_state or "topic" not in user_state[uid]:
        await update.message.reply_text("⚠️ Silakan ketik /start untuk mulai.")
        return

    topic_name = user_state[uid]["topic"]
    chat_id = TOPICS[topic_name]

    # Gender otomatis
    gender_icon = "👩‍🦰 Cewek" if hasattr(update.message.from_user, 'first_name') and update.message.from_user.first_name.lower().startswith("cwe") else "👦 Cowok"
    prefix = f"🕵 Pesan anonim dari: {gender_icon}"

    sent_msg = None
    caption_text = update.message.caption or "Tidak ada caption"

    # ===== Menfess / Teks =====
    if topic_name == "Menfess" and update.message.text:
        sent_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"{prefix}\n\n💬 Pesan: {update.message.text}\n\nemoji: 🔥 💦 😍"
        )

    # ===== Pap / Eksib =====
    elif topic_name in ["Pap Pisang","Pap Cwo","Pap Lacur","Eksib"] and (update.message.photo or update.message.video):
        media = update.message.photo[-1].file_id if update.message.photo else update.message.video.file_id
        if update.message.photo:
            sent_msg = await context.bot.send_photo(chat_id, media, caption=f"{prefix}\nFoto/Video + Caption: {caption_text}\nemoji: 🔥 💦 😍")
        else:
            sent_msg = await context.bot.send_video(chat_id, media, caption=f"{prefix}\nFoto/Video + Caption: {caption_text}\nemoji: 🔥 💦 😍")

    # ===== Moan (voice only) =====
    elif topic_name in ["Moan Cwo","Moan Cwe"] and (update.message.voice or update.message.audio):
        media = update.message.voice.file_id if update.message.voice else update.message.audio.file_id
        sent_msg = await context.bot.send_voice(chat_id, media, caption=f"{prefix}\nVoice Note + Caption: {caption_text}\nemoji: 🔥 💦 😍")

    else:
        await update.message.reply_text("⚠️ Media tidak sesuai dengan topik.")
        return

    # ===== Notifikasi admin =====
    for admin_id in ADMIN_IDS:
        try:
            if update.message.photo:
                await context.bot.send_photo(admin_id, media, caption=f"[{topic_name}] {prefix}\n{caption_text}")
            elif update.message.video:
                await context.bot.send_video(admin_id, media, caption=f"[{topic_name}] {prefix}\n{caption_text}")
            elif update.message.voice or update.message.audio:
                await context.bot.send_voice(admin_id, media, caption=f"[{topic_name}] {prefix}\n{caption_text}")
            else:
                await context.bot.send_message(admin_id, f"[{topic_name}] {prefix}\n{caption_text}")
        except:
            continue

    # ===== Auto-delete =====
    if sent_msg and user_state[uid].get("auto_delete"):
        minutes = user_state[uid]["delete_minutes"]
        asyncio.create_task(auto_delete_message(context, sent_msg.chat_id, sent_msg.message_id, minutes))

# ===== AUTO DELETE =====
async def auto_delete_message(context, chat_id, message_id, minutes):
    await asyncio.sleep(minutes * 60)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# ===== MAIN =====
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(topic_choice, pattern="^topic_"))
app.add_handler(CallbackQueryHandler(auto_delete_choice, pattern="^delete_"))
app.add_handler(CallbackQueryHandler(reset_choice, pattern="^reset$"))
app.add_handler(MessageHandler(filters.ALL, handle_media))

if __name__ == "__main__":
    print("Bot berjalan...")
    app.run_polling()
