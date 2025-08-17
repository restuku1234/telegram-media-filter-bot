import os
import logging
from typing import Dict, Set
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# =============== CONFIG DARI ENV ===============
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))  # ID grup/room Eksib (negatif untuk supergroup)
TOPIC_PAP_LACUR = int(os.getenv("TOPIC_PAP_LACUR"))   # thread_id Pap Lacur
TOPIC_PAP_PISANG = int(os.getenv("TOPIC_PAP_PISANG")) # thread_id Pap Pisang
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# Emoji ekspresi
EMOJI_LIST = ["🔥", "💦", "😍"]

# =============== LOGGING ===============
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger("anon-bot")

# =============== STATE ===============
# Simpan topik yang dipilih user di chat private
user_topic: Dict[int, str] = {}  # user_id -> "pap_lacur" | "pap_pisang"

# Simpan reaction: message_id -> {emoji: set(user_ids)}
reaction_data: Dict[int, Dict[str, Set[int]]] = {}

# =============== HELPER UI ===============
def topic_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Pap Lacur 👩‍🦰", callback_data="topic|pap_lacur")],
        [InlineKeyboardButton("Pap Pisang 👦",  callback_data="topic|pap_pisang")],
    ])

def reaction_keyboard(msg_id: int) -> InlineKeyboardMarkup:
    # Bangun label tombol sesuai jumlah klik
    counts = reaction_data.get(msg_id, {e: set() for e in EMOJI_LIST})
    row = [
        InlineKeyboardButton(f"{e} {len(counts.get(e, set()))}", callback_data=f"react|{e}")
        for e in EMOJI_LIST
    ]
    return InlineKeyboardMarkup([row])

def format_anon(topic: str, text: str) -> str:
    if topic == "pap_lacur":
        header = "🕵 Pesan anonim dari: 👩‍🦰\nCewek"
    elif topic == "pap_pisang":
        header = "🕵 Pesan anonim dari: 👦\nCowok"
    else:
        header = "🕵 Pesan anonim"
    return f"{header}\n\nisi pesan : {text}"

def thread_id_for(topic: str) -> int:
    return TOPIC_PAP_LACUR if topic == "pap_lacur" else TOPIC_PAP_PISANG

# =============== HANDLERS ===============
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "Pilih topik untuk mengirim pesan anonim ke room Eksib:",
        reply_markup=topic_keyboard()
    )

async def choose_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        _, chosen = q.data.split("|", 1)
    except Exception:
        await q.edit_message_text("Pilihan tidak dikenal. Ketik /start.")
        return
    user_topic[q.from_user.id] = chosen
    await q.edit_message_text(
        f"Topik dipilih: {('Pap Lacur 👩‍🦰' if chosen=='pap_lacur' else 'Pap Pisang 👦')}\n"
        "Sekarang kirim teks / foto / video (pakai caption)."
    )

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Terima pesan dari chat private, kirim ke room Eksib sesuai topik + tombol emoji."""
    if not update.message or update.message.chat.type != "private":
        return

    uid = update.effective_user.id
    topic = user_topic.get(uid)
    if topic not in ("pap_lacur", "pap_pisang"):
        await update.message.reply_text("Ketik /start lalu pilih topik dulu, ya.")
        return

    # Ambil isi/jenis pesan
    caption = (update.message.caption or "").strip()
    text = (update.message.text or "").strip()

    # Tentukan payload & kirim ke grup pada thread yang sesuai
    sent = None
    try:
        if update.message.photo:
            # pakai resolusi terbesar
            file_id = update.message.photo[-1].file_id
            sent = await context.bot.send_photo(
                chat_id=CHAT_ID,
                photo=file_id,
                caption=format_anon(topic, caption or "(tidak ada pesan)"),
                message_thread_id=thread_id_for(topic),
                reply_markup=reaction_keyboard(0)  # placeholder; akan diganti setelah terkirim
            )
        elif update.message.video:
            file_id = update.message.video.file_id
            sent = await context.bot.send_video(
                chat_id=CHAT_ID,
                video=file_id,
                caption=format_anon(topic, caption or "(tidak ada pesan)"),
                message_thread_id=thread_id_for(topic),
                reply_markup=reaction_keyboard(0)
            )
        else:
            # kirim sebagai text
            content = text or caption or "(tidak ada pesan)"
            sent = await context.bot.send_message(
                chat_id=CHAT_ID,
                text=format_anon(topic, content),
                message_thread_id=thread_id_for(topic),
                reply_markup=reaction_keyboard(0)
            )
    except Exception as e:
        log.exception("Gagal mengirim ke grup: %s", e)
        await update.message.reply_text("❌ Gagal mengirim ke grup. Coba lagi sebentar ya.")
        return

    # Inisialisasi reaction_data untuk msg ini & update tombol dengan message_id sebenarnya
    if sent:
        reaction_data[sent.message_id] = {e: set() for e in EMOJI_LIST}
        try:
            # Ganti keyboard placeholder -> keyboard dengan counter 0
            if sent.caption:
                await context.bot.edit_message_reply_markup(
                    chat_id=sent.chat_id,
                    message_id=sent.message_id,
                    reply_markup=reaction_keyboard(sent.message_id)
                )
            else:
                await context.bot.edit_message_reply_markup(
                    chat_id=sent.chat_id,
                    message_id=sent.message_id,
                    reply_markup=reaction_keyboard(sent.message_id)
                )
        except Exception:
            pass

    # Notif admin (opsional)
    for aid in ADMIN_IDS:
        try:
            preview = (caption or text or "(media)")[:200]
            await context.bot.send_message(
                chat_id=aid,
                text=f"[{topic}] pesan baru dari user {uid}:\n\n{preview}"
            )
        except Exception:
            pass

    await update.message.reply_text("✅ Pesan anonim sudah terkirim ke room Eksib.")

async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle reaction per user per emoji dan update label tombol."""
    q = update.callback_query
    await q.answer()

    if not q.message:
        return

    # Data callback: react|🔥  (message_id diambil dari q.message)
    try:
        _, emoji = q.data.split("|", 1)
    except Exception:
        return

    msg_id = q.message.message_id
    user_id = q.from_user.id

    # Pastikan struktur ada
    if msg_id not in reaction_data:
        reaction_data[msg_id] = {e: set() for e in EMOJI_LIST}
    if emoji not in reaction_data[msg_id]:
        reaction_data[msg_id][emoji] = set()

    # Toggle
    if user_id in reaction_data[msg_id][emoji]:
        reaction_data[msg_id][emoji].remove(user_id)
        feedback = f"{emoji} dibatalkan"
    else:
        reaction_data[msg_id][emoji].add(user_id)
        feedback = f"{emoji} ditambahkan"

    await q.answer(feedback, show_alert=False)

    # Update tombol dengan angka terbaru
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=q.message.chat_id,
            message_id=msg_id,
            reply_markup=reaction_keyboard(msg_id)
        )
    except Exception:
        pass

# =============== MAIN ===============
def main():
    if not BOT_TOKEN or not CHAT_ID or not TOPIC_PAP_LACUR or not TOPIC_PAP_PISANG:
        raise RuntimeError("ENV belum lengkap: BOT_TOKEN, CHAT_ID, TOPIC_PAP_LACUR, TOPIC_PAP_PISANG wajib diisi.")

    app = Application.builder().token(BOT_TOKEN).build()

    # Private flow: pilih topik -> kirim pesan/media
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(choose_topic, pattern=r"^topic\|"))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & (filters.TEXT | filters.PHOTO | filters.VIDEO),
                                   handle_private_message))

    # Reaction di pesan grup
    app.add_handler(CallbackQueryHandler(handle_reaction, pattern=r"^react\|"))

    log.info("Bot berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
