import logging
import os
import re
from telegram import Update, ChatMember
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Ambil token dari environment variable
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Konstanta target
TARGET_CHAT_ID = -1002575081823  # Grup Explore Fetish
TARGET_TOPIC_ID = 63            # Topik "Fantasy Lecehin"

# Fungsi deteksi link
def contains_link(text: str) -> bool:
    return bool(re.search(r'https?://|t\.me/|www\.', text, re.IGNORECASE))

# Fungsi handler pesan
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text or ""
    caption = message.caption or ""

    user = update.effective_user.username or f"user_{user_id}"
    logging.info(f"Dari @{user}: {text or caption}")

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        is_admin = False

    # Blokir link jika bukan admin
    if contains_link(text) or contains_link(caption):
        if not is_admin:
            try:
                await message.delete()
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.unban_chat_member(chat_id, user_id)
                logging.info(f"🚫 Link oleh {user_id} dihapus dan user diblokir sementara.")
            except Exception as e:
                logging.error(f"⚠️ Error saat blokir: {e}")
        return

    # Kirim ulang media dengan caption ke topik
    if (message.photo or message.video) and message.caption:
        try:
            if message.photo:
                await context.bot.send_photo(
                    chat_id=TARGET_CHAT_ID,
                    message_thread_id=TARGET_TOPIC_ID,
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    parse_mode='HTML'
                )
                logging.info(f"📸 Foto dari {user_id} dikirim ulang ke topik.")
            elif message.video:
                await context.bot.send_video(
                    chat_id=TARGET_CHAT_ID,
                    message_thread_id=TARGET_TOPIC_ID,
                    video=message.video.file_id,
                    caption=message.caption,
                    parse_mode='HTML'
                )
                logging.info(f"🎥 Video dari {user_id} dikirim ulang ke topik.")
        except Exception as e:
            logging.error(f"⚠️ Gagal kirim media: {e}")

# Fungsi utama
def main():
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN tidak ditemukan. Pastikan sudah di-set di environment variable.")
        return

    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(MessageHandler(filters.ALL, handle_message))

    print("✅ Bot sedang berjalan...")
    try:
        app_telegram.run_polling(drop_pending_updates=True)
    except Exception as e:
        logging.error(f"Bot error: {e}")
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()
