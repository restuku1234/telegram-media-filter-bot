import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===== KONFIGURASI BOT DARI ENV =====
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

TOPICS = {
    "Menfess": 5071,
    "Pap Pisang": 5052,
    "Pap Cwo": 5052,
    "Pap Lacur": 5048,
    "Eksib": 5529,
    "Moan Cwo": 5013,
    "Moan Cwe": 5046,
}

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

    keyboard = [
        [
            InlineKeyboardButton("Tidak", callback_data="delete_none"),
            InlineKeyboardButton("30 menit", callback_data="delete_30"),
            InlineKeyboardButton("1 jam", callback_data="delete_60"),
            InlineKeyboardButton("2 jam", callback_data="delete_120")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(f"✅ Topik: {topic_name}\n🕒 Pilih auto-delete:", reply_markup=reply_markup)

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
    message_thread_id = TOPICS[topic_name]
    gender_icon = "👩‍🦰 Cewek" if update.message.from_user.username and update.message.from_user.username.lower().startswith("cwe") else "👦 Cowok"
    prefix = f"🕵 Pesan anonim dari: {gender_icon}"

    # ===== Menfess / teks =====
    if topic_name in ["Menfess"] and update.message.text:
        content = update.message.text
        sent_msg = await context.bot.send_message(
            chat_id=CHAT_ID,
            message_thread_id=message_thread_id,
            text=f"{prefix}\n\n💬 Pesan: {content}\n\nemoji: 🔥 💦 😍"
        )
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(chat_id=admin_id, text=f"[{topic_name}] {prefix}\n{content}")

    # ===== Pap / Eksib =====
    elif topic_name in ["Pap Pisang","Pap Cwo","Pap Lacur","Eksib"] and (update.message.photo or update.message.video):
        media = update.message.photo[-1].file_id if update.message.photo else update.message.video.file_id
        caption = update.message.caption or "Tidak ada caption"
        if update.message.photo:
            sent_msg = await context.bot.send_photo(chat_id=CHAT_ID, message_thread_id=message_thread_id, photo=media, caption=f"{prefix}\nFoto/Video + Caption: {caption}\nemoji: 🔥 💦 😍")
        else:
            sent_msg = await context.bot.send_video(chat_id=CHAT_ID, message_thread_id=message_thread_id, video=media, caption=f"{prefix}\nFoto/Video + Caption: {caption}\nemoji: 🔥 💦 😍")
        for admin_id in ADMIN_IDS:
            if update.message.photo:
                await context.bot.send_photo(admin_id, media, caption=f"[{topic_name}] {prefix}\n{caption}")
            else:
                await context.bot.send_video(admin_id, media, caption=f"[{topic_name}] {prefix}\n{caption}")

    # ===== Moan (voice only) =====
    elif topic_name in ["Moan Cwo","Moan Cwe"] and (update.message.voice or update.message.audio):
        media = update.message.voice.file_id if update.message.voice else update.message.audio.file_id
        sent_msg = await context.bot.send_voice(chat_id=CHAT_ID, message_thread_id=message_thread_id, voice=media, caption=f"{prefix}\nVoice Note + Caption: {update.message.caption or 'Tidak ada caption'}\nemoji: 🔥 💦 😍")
        for admin_id in ADMIN_IDS:
            await context.bot.send_voice(admin_id, media, caption=f"[{topic_name}] {prefix}\n{update.message.caption or 'Tidak ada caption'}")
    else:
        await update.message.reply_text("⚠️ Media tidak sesuai dengan topik.")

    # ===== Auto-delete =====
    if user_state[uid].get("auto_delete"):
        minutes = user_state[uid]["delete_minutes"]
        asyncio.create_task(auto_delete_message(context, CHAT_ID, sent_msg.message_id, minutes))

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
