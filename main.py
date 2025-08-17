import os
import asyncio
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))

# Topik dan thread_id
TOPICS = {
    "Moan Cwo": 5043,
    "Moan Cwe": 5046,
    "Menfess": 5071,
    "Pap Cwo": 5052,
    "Pap Lacur": 5048,
    "Eksib": 5529,
}

HASHTAGS = {
    "menfess": "#menfess",
    "curhat": "#curhat",
    "cerita18+": "#cerita18+",
    "keluhkesah": "#keluhkesah",
}

EMOJI_LIST = ["🔥", "💦", "😍"]

user_state = {}       # {user_id: {"topic":..., "hashtag":..., "gender":..., "last_message_id":...}}
reaction_data = {}    # {message_id: {emoji: set(user_ids)}}

# ======= Handler Gender =======
async def ask_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    keyboard = [
        [InlineKeyboardButton("Cewek 👩‍🦰", callback_data="gender_cwe")],
        [InlineKeyboardButton("Cowok 👦", callback_data="gender_cwo")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Pilih gender kamu untuk pesan anonim:", reply_markup=reply_markup
    )

async def gender_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    gender = query.data.replace("gender_", "")
    if user_id not in user_state:
        user_state[user_id] = {}
    user_state[user_id]["gender"] = gender
    await query.message.reply_text(
        "✅ Gender tersimpan. Sekarang ketik /start untuk pilih topik."
    )

# ======= Start dan pilih topik =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    if update.message.from_user.id not in user_state or "gender" not in user_state[update.message.from_user.id]:
        await ask_gender(update, context)
        return

    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"topic_{name}")]
        for name in TOPICS.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 Pilih topik yang ingin kamu kirim:", reply_markup=reply_markup)

async def topic_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    topic = query.data.replace("topic_", "")
    if user_id not in user_state:
        user_state[user_id] = {}
    user_state[user_id]["topic"] = topic

    if topic == "Menfess":
        keyboard = [
            [InlineKeyboardButton(f"{tag} {desc}", callback_data=f"hashtag_{tag}")]
            for tag, desc in {
                "menfess": "fess umum",
                "curhat": "isi hati / 18+",
                "cerita18+": "pengalaman 18+",
                "keluhkesah": "tempat mengeluh",
            }.items()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "Pilih hashtag untuk pesan Menfess-mu:", reply_markup=reply_markup
        )
    else:
        await query.message.reply_text(
            f"Topik '{topic}' dipilih. Sekarang kirim pesan / media sesuai topik."
        )

async def hashtag_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    tag = query.data.replace("hashtag_", "")
    if user_id in user_state:
        user_state[user_id]["hashtag"] = tag
    await query.message.reply_text(
        f"Hashtag {HASHTAGS.get(tag, '')} dipilih. Silakan kirim pesan Menfess-mu sekarang."
    )

# ======= Handle kirim pesan =======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    user_id = update.message.from_user.id
    if user_id not in user_state or "topic" not in user_state[user_id] or "gender" not in user_state[user_id]:
        await update.message.reply_text("Ketik /start untuk mulai dan pilih gender.")
        return

    topic = user_state[user_id]["topic"]
    thread_id = TOPICS.get(topic)
    gender = user_state[user_id]["gender"]

    # Format gender
    if gender == "cwe":
        gender_text = "🕵 Pesan anonim dari: 👩‍🦰\nCewek\n\n"
    elif gender == "cwo":
        gender_text = "🕵 Pesan anonim dari: 👦\nCowok\n\n"
    else:
        gender_text = "🕵 Pesan anonim\n\n"

    sent_msg = None

    if topic in ["Moan Cwo", "Moan Cwe"]:
        if not (update.message.voice or update.message.audio):
            await update.message.reply_text("Topik ini hanya menerima voice/audio.")
            return
        if update.message.voice:
            sent_msg = await context.bot.send_voice(
                chat_id=GROUP_ID,
                voice=update.message.voice.file_id,
                caption=gender_text + (update.message.caption or ""),
                message_thread_id=thread_id,
            )
        elif update.message.audio:
            sent_msg = await context.bot.send_audio(
                chat_id=GROUP_ID,
                audio=update.message.audio.file_id,
                caption=gender_text + (update.message.caption or ""),
                message_thread_id=thread_id,
            )

    elif topic in ["Pap Cwo", "Pap Lacur"]:
        if update.message.photo:
            photo_file_id = update.message.photo[-1].file_id
            sent_msg = await context.bot.send_photo(
                chat_id=GROUP_ID,
                photo=photo_file_id,
                caption=gender_text + (update.message.caption or ""),
                message_thread_id=thread_id,
            )
        elif update.message.video:
            video_file_id = update.message.video.file_id
            sent_msg = await context.bot.send_video(
                chat_id=GROUP_ID,
                video=video_file_id,
                caption=gender_text + (update.message.caption or ""),
                message_thread_id=thread_id,
            )
        else:
            await update.message.reply_text("Topik ini hanya menerima foto atau video.")
            return

    elif topic == "Menfess":
        text = update.message.text or ""
        if not text:
            await update.message.reply_text("Kirim pesan teks untuk Menfess.")
            return
        hashtag = HASHTAGS.get(user_state[user_id].get("hashtag"), "#menfess")
        full_text = f"{gender_text}{text}\n\n{hashtag}"
        sent_msg = await context.bot.send_message(
            chat_id=GROUP_ID, text=full_text, message_thread_id=thread_id
        )
    else:
        await update.message.reply_text("Topik tidak dikenal.")
        return

    # Notifikasi admin
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"[{topic}] Pesan baru diterima dari user {user_id}.",
            )
        except Exception:
            pass

    await update.message.reply_text(f"Pesan berhasil dikirim ke topik '{topic}'.")

    if sent_msg:
        user_state[user_id]["last_message_id"] = sent_msg.message_id
        await add_reaction_keyboard(sent_msg, context)

# ======= Reaction emoji =======
async def add_reaction_keyboard(message, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(f"{emoji} 0", callback_data=f"react_{emoji}_{message.message_id}")
            for emoji in EMOJI_LIST
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=message.chat_id,
            message_id=message.message_id,
            reply_markup=reply_markup,
        )
    except Exception:
        pass
    reaction_data[message.message_id] = {emoji: set() for emoji in EMOJI_LIST}

async def reaction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    if not data.startswith("react_"):
        return
    _, emoji, msg_id_str = data.split("_")
    msg_id = int(msg_id_str)
    if msg_id not in reaction_data:
        reaction_data[msg_id] = {e: set() for e in EMOJI_LIST}

    if user_id in reaction_data[msg_id][emoji]:
        reaction_data[msg_id][emoji].remove(user_id)
    else:
        reaction_data[msg_id][emoji].add(user_id)

    keyboard = [
        [
            InlineKeyboardButton(
                f"{e} {len(reaction_data[msg_id][e])}", callback_data=f"react_{e}_{msg_id}"
            )
            for e in EMOJI_LIST
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=GROUP_ID,
            message_id=msg_id,
            reply_markup=reply_markup,
        )
    except Exception:
        pass

# ======= Main Application =======
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(gender_choice, pattern="^gender_"))
    app.add_handler(CallbackQueryHandler(topic_choice, pattern="^topic_"))
    app.add_handler(CallbackQueryHandler(hashtag_choice, pattern="^hashtag_"))
    app.add_handler(CallbackQueryHandler(reaction_handler, pattern="^react_"))
    app.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, handle_message))

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
