import re
import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# ========== কনফিগারেশন ==========
CHANNEL_USERNAME = "@Vanila_cards"
ADMIN_ID = 8508012498
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7839522620:AAFZPWXQ3Hpb_40Ie_w5yjiHNphUAo0J0mU")

USER_FILE = "users.txt"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

awaiting_broadcast = False

# ========== ইউজার ফাইল ম্যানেজ ==========
def load_users():
    if not os.path.exists(USER_FILE):
        return set()
    with open(USER_FILE, "r") as f:
        return {int(line.strip()) for line in f if line.strip()}

def save_user(user_id: int):
    users = load_users()
    if user_id not in users:
        users.add(user_id)
        with open(USER_FILE, "w") as f:
            for uid in users:
                f.write(f"{uid}\n")

def get_all_users():
    return load_users()

# ========== মেম্বারশিপ চেক ==========
async def is_user_member(user_id: int, bot: Bot) -> bool:
    try:
        chat_member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME, user_id=user_id
        )
        return chat_member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.error(f"মেম্বারশিপ চেক ব্যর্থ {user_id}: {e}")
        return False

# ========== হ্যান্ডলার ==========
async def start(update: Update, context):
    user_id = update.effective_user.id
    save_user(user_id)
    welcome_text = (
        "💠 Dear users!\n\n🚀 JOIN OUR OFFICIAL BOT FIRST!\n🤖 Buy Cards Instantly:\n"
        "👉 @vanilla_cards_bot— Type /start\n🔔 Get Instant Support:\n👉 https://t.me/Vanila_cards\n"
        "⚡ Early Join = Early Access\n🔥 Don't Miss The Best Cards!"
    )
    keyboard = [[
        InlineKeyboardButton("💳 Buy Card", url="https://t.me/vanilla_cards_bot"),
        InlineKeyboardButton("🔍 Card Chake", callback_data="card_check"),
    ]]
    await update.message.reply_text(
        welcome_text, reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def card_check_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    formats_text = (
        "Welcome! Please provide your card details in a standard format:\n\n"
        "2222222222222222:22:22:222\n"
        "3333333333333333:33/33:333\n"
        "4444444444444444/44/44/444\n"
        "5555555555555555 55/55 555\n"
        "6666666666666666 66 66 666\n\n"
        "(Tap and hold any line to copy)"
    )
    await query.edit_message_text(formats_text)

async def send_card_formats(update: Update, context):
    save_user(update.effective_user.id)
    formats_text = (
        "Welcome! Please provide your card details in a standard format:\n\n"
        "2222222222222222:22:22:222\n"
        "3333333333333333:33/33:333\n"
        "4444444444444444/44/44/444\n"
        "5555555555555555 55/55 555\n"
        "6666666666666666 66 66 666\n\n"
        "(Tap and hold any line to copy)"
    )
    await update.message.reply_text(formats_text)

CARD_PATTERN = re.compile(r"^\d{16}[:/\s]\d{2}[:/\s]\d{2}[:/\s]\d{3,4}$")

async def handle_message(update: Update, context):
    global awaiting_broadcast
    user_input = update.message.text.strip()
    user_id = update.effective_user.id
    save_user(user_id)

    if user_id == ADMIN_ID and awaiting_broadcast:
        users = get_all_users()
        ok = fail = 0
        for uid in users:
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                ok += 1
            except Exception:
                fail += 1
        awaiting_broadcast = False
        await update.message.reply_text(
            f"✅ ব্রডকাস্ট শেষ!\nসফল: {ok}\nব্যর্থ: {fail}"
        )
        return

    if CARD_PATTERN.match(user_input):
        member = await is_user_member(user_id, context.bot)
        if member:
            await update.message.reply_text(
                "✅ You are a member! Card details received (demo).\n"
                "Add your own card validation here."
            )
        else:
            await update.message.reply_text(
                "You can't check the card because you're not a member of @Vanila_cards"
            )
    else:
        await update.message.reply_text("❌ Invalid format")

async def admin_command(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ আপনি এই কমান্ড ব্যবহার করার অনুমতি রাখেন না।"
        )
        return
    global awaiting_broadcast
    awaiting_broadcast = True
    await update.message.reply_text(
        "📢 *ব্রডকাস্ট মোড অন*\n\n"
        "এখন আপনি যে কোনো মেসেজ পাঠাবেন তা *সব ইউজারের কাছে* পৌঁছে যাবে।",
        parse_mode="Markdown",
    )

# ========== Application তৈরি ==========
application = Application.builder().token(BOT_TOKEN).updater(None).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("card_chake", send_card_formats))
application.add_handler(CommandHandler("admin", admin_command))
application.add_handler(
    CallbackQueryHandler(card_check_callback, pattern="^card_check$")
)
application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
)

# ========== ফ্লাস্ক রাউট ==========
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.process_update(update))
        loop.close()
        return "ok", 200
    except Exception as e:
        logger.error(f"ওয়েবহুক ত্রুটি: {e}")
        return "error", 500

@app.route("/")
def index():
    return "Bot is running", 200

@app.route("/health")
def health():
    return "OK", 200

# ========== ওয়েবহুক সেটআপ ==========
def set_webhook():
    render_url = os.environ.get(
        "RENDER_EXTERNAL_URL", "https://card-bot-2.onrender.com"
    )
    webhook_url = f"{render_url}/webhook/{BOT_TOKEN}"

    async def _set():
        await application.initialize()
        await application.bot.set_webhook(webhook_url)
        logger.info(f"✅ ওয়েবহুক সেট: {webhook_url}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_set())
    loop.close()

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN environment variable সেট করা নেই!")
        exit(1)

    set_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
