import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# === KONFIGURASI BOT ===
TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS").split(",")]

TOPICS = {
    "Pap Lacur": 5048,
    "Pap Cwo": 5052,
    "Pap Pisang": 5053,
    "Moan Cwo": 5013,
    "Moan Cwe": 5046,
    "Menfess": 5071,
    "Eksib": 5529
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
    await query.message.reply_text("✅ Pilihan tersimpan. Sekarang kirim konten yang ingin dikirim ke grup.", reply_markup=reply_markup)

# ===== RESET =====
async def reset_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in user_state:
        del user_state[user_id]
    await show_topics(query, context)

# ===== HANDLE MEDIA / MENFESS =====
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    uid = update.message.from_user.id
    if uid not in user_state or "topic" not in user_state[uid]:
        await update.message.reply_text("⚠️ Silakan ketik /start untuk mulai.")
        return

    topic_name = user_state[uid]["topic"]
    thread_id = TOPICS[topic_name]

    # Gender untuk Menfess
    gender_icon = "👩‍🦰 Cewek" if "Cwe" in topic_name or "Menfess" in topic_name else "👦 Cowok"

    # ===== MENFESS =====
    if topic_name == "Menfess":
        text = update.message.text or ""
        if not text:
            await update.message.reply_text("⚠️ Masukkan isi pesan menfess.")
            return
        msg = f"🕵 Pesan anonim dari: {gender_icon}\n\nisi pesan: {text}\n\nemoji: 🔥 💦 😍"
        await context.bot.send_message(chat_id=GROUP_ID, message_thread_id=thread_id, text=msg)

        # Notifikasi admin
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(chat_id=admin_id, text=f"[Menfess] {text}")

        await update.message.reply_text("✅ Pesan menfess berhasil dikirim!")

    # ===== MOAN (hanya audio) =====
    elif topic_name in ["Moan Cwo", "Moan Cwe"]:
        if update.message.voice or update.message.audio:
            file_id = update.message.voice.file_id if update.message.voice else update.message.audio.file_id
            caption = f"🕵 Pesan anonim dari: {gender_icon}\n\nemoji: 🔥 💦 😍"
            sent = await context.bot.send_audio(chat_id=GROUP_ID, message_thread_id=thread_id, audio=file_id, caption=caption)

            # Notifikasi admin
            for admin_id in ADMIN_IDS:
                await context.bot.send_audio(chat_id=admin_id, audio=file_id, caption=f"[{topic_name}] {caption}")

            if user_state[uid].get("auto_delete"):
                minutes = user_state[uid]["delete_minutes"]
                asyncio.create_task(auto_delete_message(context, GROUP_ID, sent.message_id, minutes))
            await update.message.reply_text("✅ Audio berhasil dikirim ke grup!")
        else:
            await update.message.reply_text("⚠️ MOAN hanya menerima voice atau audio file.")

    # ===== PAP (foto/video) =====
    else:
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            caption_text = update.message.caption or ""
            sent = await context.bot.send_photo(chat_id=GROUP_ID, message_thread_id=thread_id, photo=file_id,
                                               caption=f"🕵 Pesan anonim dari: {gender_icon}\nFoto + Caption: {caption_text}\nemoji: 🔥 💦 😍")
        elif update.message.video:
            file_id = update.message.video.file_id
            caption_text = update.message.caption or ""
            sent = await context.bot.send_video(chat_id=GROUP_ID, message_thread_id=thread_id, video=file_id,
                                               caption=f"🕵 Pesan anonim dari: {gender_icon}\nVideo + Caption: {caption_text}\nemoji: 🔥 💦 😍")
        else:
            await update.message.reply_text("⚠️ Kirim foto/video untuk topik PAP.")
            return

        # Notifikasi admin
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(chat_id=admin_id, text=f"[{topic_name}] {caption_text}")

        if user_state[uid].get("auto_delete"):
            minutes = user_state[uid]["delete_minutes"]
            asyncio.create_task(auto_delete_message(context, GROUP_ID, sent.message_id, minutes))
        await update.message.reply_text("✅ Konten berhasil dikirim ke grup!")

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
