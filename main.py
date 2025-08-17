from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import asyncio

# === KONFIGURASI BOT ===
TOKEN = "8069081808:AAG6T8ytFHqK_Kx9qLpLGEHz9ugSW0higj0"
CHAT_ID = -1002754430828  # ID grup utama
ADMIN_IDS = [6046272730]   # List admin
TOPICS = {
    "Moan Cwo": 5013,       # hanya voice
    "Moan Cwe": 5046,       # hanya voice
    "Menfess": 5071,        # hanya teks
    "Pap Cwo": 5052,        # foto/video + caption + emoji
    "Pap Lacur": 5048,      # foto/video + caption + emoji
    "Eksib": 5529,          # foto/video + caption + emoji
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
    await query.message.reply_text(
        f"✅ Kamu pilih topik: {topic_name}\n🕒 Pilih opsi hapus otomatis:", reply_markup=reply_markup
    )

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
    await query.message.reply_text(
        "✅ Pilihan tersimpan. Sekarang kirim file/teks sesuai topik.", reply_markup=reply_markup
    )

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
    message_thread_id = TOPICS[topic_name]

    # ===== MENFESS =====
    if topic_name == "Menfess" and update.message.text:
        sent_msg = await context.bot.send_message(
            chat_id=CHAT_ID,
            message_thread_id=message_thread_id,
            text=f"🕵 Pesan anonim: {update.message.text}"
        )
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(chat_id=admin_id, text=f"[Menfess] {update.message.text}")
        await update.message.reply_text("✅ Pesan berhasil dikirim ke Menfess.")
        return

    # ===== MOAN CWO / CWE =====
    if topic_name in ["Moan Cwo", "Moan Cwe"] and update.message.voice:
        sent_msg = await context.bot.send_voice(
            chat_id=CHAT_ID,
            message_thread_id=message_thread_id,
            voice=update.message.voice.file_id,
            caption=update.message.caption or ""
        )
        for admin_id in ADMIN_IDS:
            await context.bot.send_voice(chat_id=admin_id, voice=update.message.voice.file_id,
                                         caption=f"[{topic_name}] {update.message.caption or ''}")
        await update.message.reply_text(f"✅ Voice berhasil dikirim ke {topic_name}.")
        return

    # ===== PAP CWO / PAP LACUR / EKSIB =====
    if topic_name in ["Pap Cwo", "Pap Lacur", "Eksib"] and (update.message.photo or update.message.video):
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            sent_msg = await context.bot.send_photo(
                chat_id=CHAT_ID,
                message_thread_id=message_thread_id,
                photo=file_id,
                caption=update.message.caption or "🕵 Pesan anonim\nEmoji: 🔥 💦 😍"
            )
            for admin_id in ADMIN_IDS:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=file_id,
                    caption=f"[{topic_name}] {update.message.caption or ''}"
                )
        elif update.message.video:
            file_id = update.message.video.file_id
            sent_msg = await context.bot.send_video(
                chat_id=CHAT_ID,
                message_thread_id=message_thread_id,
                video=file_id,
                caption=update.message.caption or "🕵 Pesan anonim\nEmoji: 🔥 💦 😍"
            )
            for admin_id in ADMIN_IDS:
                await context.bot.send_video(
                    chat_id=admin_id,
                    video=file_id,
                    caption=f"[{topic_name}] {update.message.caption or ''}"
                )
        await update.message.reply_text(f"✅ File berhasil dikirim ke {topic_name} dengan emoji default.")
        
        # Auto-delete
        if user_state[uid].get("auto_delete"):
            minutes = user_state[uid]["delete_minutes"]
            asyncio.create_task(auto_delete_message(context, CHAT_ID, sent_msg.message_id, minutes))
        return

    # ===== TEKS TIDAK DIKIRIM KE GRUP =====
    await update.message.reply_text(f"⚠️ Format file tidak sesuai topik atau teks tidak dikirim ke grup.")

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
