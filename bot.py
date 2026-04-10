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

# ========== Configuration ==========
CHANNEL_USERNAME = "@Vanila_cards"
ADMIN_ID = 8508012498
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8713347006:AAE8Eu_bYiJITlfhfUAVFHaJQ933tI4NILk")

USER_FILE = "users.txt"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

awaiting_broadcast = False

# ========== User File ==========
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

# ========== Membership Check ==========
async def is_user_member(user_id: int, bot: Bot) -> bool:
    try:
        chat_member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME, user_id=user_id
        )
        return chat_member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.error(f"Membership check failed {user_id}: {e}")
        return False

# ========== Card Format Text ==========
FORMATS_TEXT = (
    "Welcome\\! Please provide your card details in a standard format:\n\n"
    "`2222222222222222:22:22:222`\n"
    "`3333333333333333:33/33:333`\n"
    "`4444444444444444/44/44/444`\n"
    "`5555555555555555 55/55 555`\n"
    "`6666666666666666 66 66 666`\n\n"
    "👆 Tap any format to copy"
)

# ========== Handlers ==========
async def start(update: Update, context):
    user_id = update.effective_user.id
    save_user(user_id)
    welcome_text = (
        "💠 Dear users\\!\n\n"
        "🚀 JOIN OUR OFFICIAL BOT FIRST\\!\n"
        "🤖 Buy Cards Instantly:\n"
        "👉 @vanilla\\_cards\\_bot — Type /start\n"
        "🔔 Get Instant Support: https://t\\.me/Vanilagcm\n"
        "⚡ Early Join \\= Early Access\n"
        "🔥 Don't Miss The Best Cards \\!"
    )
    keyboard = [[
        InlineKeyboardButton("💳 Buy Card", url="https://t.me/vanilla_cards_bot"),
        InlineKeyboardButton("🔍 Card Check", callback_data="card_check"),
    ]]
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2",
    )

async def card_check_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(FORMATS_TEXT, parse_mode="MarkdownV2")

async def send_card_formats(update: Update, context):
    save_user(update.effective_user.id)
    await update.message.reply_text(FORMATS_TEXT, parse_mode="MarkdownV2")

async def unknown_command(update: Update, context):
    save_user(update.effective_user.id)
    cmd = update.message.text.strip().split()[0]
    await update.message.reply_text(
        f"⚠️ `{cmd}` — This command does not exist\\!\n\n"
        "✅ Available commands:\n"
        "/start — Start the bot\n"
        "/card\\_chake — Show card formats",
        parse_mode="MarkdownV2",
    )

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
            f"✅ Broadcast done!\nSuccess: {ok}\nFailed: {fail}"
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
                "❌ You can't check the card because you're not a member of @vanilla_cards_bot"
            )
    else:
        await update.message.reply_text(
            "❌ Invalid format\\!\n\nPlease use one of these formats:\n"
            "`1234567890123456:12:34:567`\n"
            "`1234567890123456/12/34/567`\n"
            "`1234567890123456 12/34 567`",
            parse_mode="MarkdownV2",
        )

async def admin_command(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ You are not authorized to use this command."
        )
        return
    global awaiting_broadcast
    awaiting_broadcast = True
    await update.message.reply_text(
        "📢 *Broadcast mode ON*\n\n"
        "Any message you send now will be delivered to *all users*.",
        parse_mode="Markdown",
    )

# ========== Build Application ==========
def build_application():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("card_chake", send_card_formats))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(
        CallbackQueryHandler(card_check_callback, pattern="^card_check$")
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    # Unknown commands — must be last
    application.add_handler(
        MessageHandler(filters.COMMAND, unknown_command)
    )
    return application

# ========== Webhook Mode (Render/gunicorn) ==========
# This runs at import time so gunicorn picks it up correctly
flask_app = Flask(__name__)
main_loop = asyncio.new_event_loop()
asyncio.set_event_loop(main_loop)
ptb_app = build_application()
main_loop.run_until_complete(ptb_app.initialize())

# Set webhook automatically when RENDER_EXTERNAL_URL is available
_render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
if _render_url and BOT_TOKEN:
    _webhook_url = f"{_render_url}/webhook/{BOT_TOKEN}"
    main_loop.run_until_complete(ptb_app.bot.set_webhook(_webhook_url))
    logger.info(f"✅ Webhook set: {_webhook_url}")

@flask_app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, ptb_app.bot)
        main_loop.run_until_complete(ptb_app.process_update(update))
        return "ok", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "error", 500

@flask_app.route("/")
def index():
    return "Bot is running", 200

@flask_app.route("/health")
def health():
    return "OK", 200

# ========== Polling Mode (local/dev) ==========
if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN is not set!")
        exit(1)

    if _render_url:
        # Render: run Flask with gunicorn instead
        port = int(os.environ.get("PORT", 5000))
        flask_app.run(host="0.0.0.0", port=port, threaded=False)
    else:
        # Local/Replit: polling mode
        logger.info("🤖 Starting polling mode...")
        polling_app = build_application()
        polling_app.run_polling(drop_pending_updates=True)
