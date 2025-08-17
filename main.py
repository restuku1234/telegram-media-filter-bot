import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# === KONFIGURASI BOT ===
TOKEN = "8069081808:AAG6T8ytFHqK_Kx9qLpLGEHz9ugSW0higj0"
CHAT_ID = -1002754430828  # ID grup utama
ADMIN_IDS = [6046272730]   # List admin
TOPICS = {
    "Menfess": 5071,
    "Moan Cwo": 5013,
    "Moan Cwe": 5046,
    "Pap Cwo": 5052,
    "Pap Lacur": 5048,
    "Pap Pisang": 4423,
    "Eksib": 5529,
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

    if topic_name == "Menfess":
        keyboard_gender = [
            [InlineKeyboardButton("👩 Cewek", callback_data="gender_cwe")],
            [InlineKeyboardButton("👦 Cowok", callback_data="gender_cwo")]
        ]
        await query.message.reply_text("✅ Pilih gender pengirim:", reply_markup=InlineKeyboardMarkup(keyboard_gender))
    else:
        keyboard_delete = [
            [
                InlineKeyboardButton("Tidak", callback_data="delete_none"),
                InlineKeyboardButton("30 menit", callback_data="delete_30"),
                InlineKeyboardButton("1 jam", callback_data="delete_60"),
                InlineKeyboardButton("2 jam", callback_data="delete_120")
            ]
        ]
        await query.message.reply_text(f"✅ Kamu pilih topik: {topic_name}\n🕒 Pilih opsi hapus otomatis:", reply_markup=InlineKeyboardMarkup(keyboard_delete))

# ===== PILIH GENDER =====
async def gender_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data
    user_state[user_id]["gender"] = "👩 Cewek" if choice == "gender_cwe" else "👦 Cowok"

    keyboard_delete = [
        [
            InlineKeyboardButton("Tidak", callback_data="delete_none"),
            InlineKeyboardButton("30 menit", callback_data="delete_30"),
            InlineKeyboardButton("1 jam", callback_data="delete_60"),
            InlineKeyboardButton("2 jam", callback_data="delete_120")
        ]
    ]
    await query.message.reply_text("✅ Gender tersimpan. Pilih opsi hapus otomatis:", reply_markup=InlineKeyboardMarkup(keyboard_delete))

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

    keyboard_reset = [[InlineKeyboardButton("Reset / Pilih Topik Baru", callback_data="reset")]]
    await query.message.reply_text("✅ Pilihan tersimpan. Sekarang kirim konten sesuai topik.", reply_markup=InlineKeyboardMarkup(keyboard_reset))

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
    gender = user_state[uid].get("gender", "")

    # Emoji reaksi otomatis
    emoji_reaction = "🔥 💦 😍"

    # MENFESS
    if topic_name == "Menfess" and update.message.text:
        text = update.message.text
        sent_msg = await context.bot.send_message(
            chat_id=CHAT_ID,
            message_thread_id=message_thread_id,
            text=f"🕵 Pesan anonim dari: {gender}\nisi pesan: {text}\n{emoji_reaction}"
        )

    # MOAN (voice)
    elif topic_name.startswith("Moan") and update.message.voice:
        file_id = update.message.voice.file_id
        sent_msg = await context.bot.send_voice(
            chat_id=CHAT_ID,
            message_thread_id=message_thread_id,
            voice=file_id,
            caption=f"🕵 Voice dari: {gender}\n{emoji_reaction}"
        )

    # PAP (foto/video)
    elif topic_name.startswith("Pap") or topic_name == "Eksib":
        caption = update.message.caption or ""
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            sent_msg = await context.bot.send_photo(
                chat_id=CHAT_ID,
                message_thread_id=message_thread_id,
                photo=file_id,
                caption=f"🕵 Pesan anonim dari: {gender}\n{caption}\n{emoji_reaction}"
            )
        elif update.message.video:
            file_id = update.message.video.file_id
            sent_msg = await context.bot.send_video(
                chat_id=CHAT_ID,
                message_thread_id=message_thread_id,
                video=file_id,
                caption=f"🕵 Pesan anonim dari: {gender}\n{caption}\n{emoji_reaction}"
            )
        else:
            await update.message.reply_text("⚠️ Kirim foto atau video saja untuk topik ini.")
            return
    else:
        await update.message.reply_text("⚠️ Konten tidak sesuai topik.")
        return

    # Kirim notifikasi ke admin
    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"[{topic_name}] Kiriman baru dari {gender}"
        )

    await update.message.reply_text(f"✅ Konten berhasil dikirim ke '{topic_name}' dan admin diberi notifikasi.")

    # Auto-delete
    if user_state[uid].get("auto_delete"):
        minutes = user_state[uid]["delete_minutes"]
        asyncio.create_task(auto_delete_message(context, CHAT_ID, sent_msg.message_id, minutes))

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
app.add_handler(CallbackQueryHandler(gender_choice, pattern="^gender_"))
app.add_handler(CallbackQueryHandler(auto_delete_choice, pattern="^delete_"))
app.add_handler(CallbackQueryHandler(reset_choice, pattern="^reset$"))
app.add_handler(MessageHandler(filters.ALL, handle_media))

if __name__ == "__main__":
    print("Bot berjalan...")
    app.run_polling()
