import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, ChatMember
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import re

# Ambil token dari environment variable Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID grup dan topik target
TARGET_CHAT_ID = -1002575081823
TARGET_TOPIC_ID = 63  # ID topik "Fantasy Lecehin"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Web server (agar Railway tetap hidup)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# Deteksi link
def contains_link(text: str) -> bool:
    return bool(re.search(r'https?://|t\.me/|www\.', text, re.IGNORECASE))

# Handle semua pesan
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text or ""
    caption = message.caption or ""

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        is_admin = False

    # Hapus link dari non-admin
    if contains_link(text) or co_
