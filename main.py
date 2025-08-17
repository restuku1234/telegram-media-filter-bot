import os
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# ENV Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))

# Topik Konstanta
TOPIK_PAP_LACUR = "pap_lacur"
TOPIK_PAP_PISANG = "pap_pisang"
TOPIK_MENFESS = "menfess"
TOPIK_MOAN_CWE = "moan_cwe"
TOPIK_MOAN_CWO = "moan_cwo"

TOPIKS = [TOPIK_PAP_LACUR, TOPIK_PAP_PISANG, TOPIK_MENFESS, TOPIK_MOAN_CWE, TOPIK_MOAN_CWO]

# Simpan state user
user_topics = {}       # user_id: topik
user_autodelete = {}   # user_id: bool

# ----- Helper -----
def get_gender_emoji(gender: str):
    if gender.lower() in ["cowo", "cowok", "male"]:
        return "👦"
    return "👩"

def get_topic_emoji(topic: str):
    if topic in [TOPIK_PAP_LACUR, TOPIK_PAP_PISANG, TOPIK_MENFESS]:
        return "🔥 💦 😍"
    elif topic in [TOPIK_MOAN_CWE, TOPIK_MOAN_CWO]:
        return "🎤 🔊 😈"
    return ""

async def notify_admins(message: str, context: ContextTypes.DEFAULT_TYPE):
    for admin_id in ADMIN_IDS:
        await context.bot.send_message(chat_id=admin_id, text=message)

# ----- Command Handlers -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot aktif!\nGunakan /topik untuk memilih topik kirim pesan."
    )

async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"Pilih topik: {', '.join(TOPIKS)}")
        return
    topic = context.args[0].lower()
    if topic not in TOPIKS:
        await update.message.reply_text(f"Topik tidak valid. Pilih: {', '.join(TOPIKS)}")
        return
    user_topics[update.effective_user.id] = topic
    await update.message.reply_text(f"Topik kamu diatur ke: {topic}")

async def reset_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_topics.pop(update.effective_user.id, None)
    await update.message.reply_text("Topik kamu telah di-reset.")

async def toggle_autodelete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = user_autodelete.get(update.effective_user.id, False)
    user_autodelete[update.effective_user.id] = not current
    await update.message.reply_text(f"Auto-delete diubah menjadi {not current}")

# ----- Message Handler -----
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    topic = user_topics.get(user_id)
    if not topic:
        await update.message.reply_text("Pilih topik dulu pakai /topik <nama_topik>")
        return

    gender = update.effective_user.full_name
    gender_emoji = get_gender_emoji(update.effective_user.username or "cowo")
    topic_emoji = get_topic_emoji(topic)

    # Moan hanya menerima audio
    if topic in [TOPIK_MOAN_CWE, TOPIK_MOAN_CWO]:
        if not update.message.voice and not update.message.audio:
            await update.message.reply_text("Moan hanya menerima voice note / file audio.")
            return

    # Kirim preview ke group
    msg_preview = f"🕵 Pesan anonim dari: {gender_emoji} {topic.replace('_', ' ').title()}\n"
    if update.message.text:
        msg_preview += f"Caption: {update.message.text}\n"
    if update.message.photo:
        msg_preview += "Foto/Video: ✅\n"
    if update.message.audio or update.message.voice:
        msg_preview += "Audio: ✅\n"
    msg_preview += f"emoji: {topic_emoji}"

    await context.bot.send_message(chat_id=GROUP_ID, text=msg_preview)

    # Notifikasi admin
    await notify_admins(f"User {gender_emoji} mengirim pesan topik {topic}", context)

    # Auto delete
    if user_autodelete.get(user_id):
        await update.message.delete()

# ----- Main -----
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("topik", set_topic))
    app.add_handler(CommandHandler("reset", reset_topic))
    app.add_handler(CommandHandler("autodelete", toggle_autodelete))

    app.add_handler(MessageHandler(filters.ALL, handle_message))

    app.run_polling()
