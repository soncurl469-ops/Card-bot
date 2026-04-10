import re
import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ===================== কনফিগারেশন =====================
CHANNEL_USERNAME = "@Vanila_cards"
ADMIN_ID = 8508012498
BOT_TOKEN = "এখানে বট টুকেন বসান"   # আপনার টোকেন দিন

USER_FILE = "users.txt"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ফ্লাস্ক অ্যাপ
app = Flask(__name__)

# বট ও ডিসপ্যাচার
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

awaiting_broadcast = False  # ব্রডকাস্ট স্টেট (ইন-মেমরি)

# ===================== ইউজার ম্যানেজমেন্ট =====================
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

# ===================== মেম্বারশিপ চেক =====================
async def is_user_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return chat_member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.error(f"মেম্বারশিপ চেক ব্যর্থ {user_id}: {e}")
        return False

# ===================== হ্যান্ডলার =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    save_user(user_id)
    welcome_text = (
        "💠 Dear users!\n\n"
        "🚀 JOIN OUR OFFICIAL BOT FIRST!\n"
        "🤖 Buy Cards Instantly:\n"
        "👉 @vanilla_cards_bot— Type /start\n"
        "🔔 Get Instant Support:\n"
        "👉 https://t.me/Vanila_cards\n"
        "⚡ Early Join = Early Access\n"
        "🔥 Don't Miss The Best Cards!"
    )
    keyboard = [
        [
            InlineKeyboardButton("💳 Buy Card", url="https://t.me/vanilla_cards_bot"),
            InlineKeyboardButton("🔍 Card Chake", callback_data="card_check")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def card_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def send_card_formats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    save_user(user_id)
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

CARD_PATTERN = re.compile(r'^\d{16}([:/\s])\d{2}([:/\s])\d{2}([:/\s])\d{3}$')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global awaiting_broadcast
    user_input = update.message.text.strip()
    user_id = update.effective_user.id
    save_user(user_id)

    if user_id == ADMIN_ID and awaiting_broadcast:
        all_users = get_all_users()
        success_count = 0
        fail_count = 0
        for uid in all_users:
            try:
                await context.bot.copy_message(
                    chat_id=uid,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                success_count += 1
            except Exception as e:
                logger.error(f"ব্যর্থ {uid}: {e}")
                fail_count += 1
        awaiting_broadcast = False
        await update.message.reply_text(f"✅ ব্রডকাস্ট শেষ!\nসফল: {success_count}\nব্যর্থ: {fail_count}")
        return

    if CARD_PATTERN.match(user_input):
        member = await is_user_member(user_id, context)
        if not member:
            await update.message.reply_text("You can't check the card because you're not a member of @vanilla_cards_bot")
        else:
            await update.message.reply_text("✅ You are a member! Card details received (demo).\nAdd your own card validation here.")
    else:
        await update.message.reply_text("❌ Invalid format")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ আপনি এই কমান্ড ব্যবহার করার অনুমতি রাখেন না।")
        return
    global awaiting_broadcast
    awaiting_broadcast = True
    await update.message.reply_text(
        "📢 **ব্রডকাস্ট মোড অন**\n\nএখন আপনি যে কোনো মেসেজ পাঠাবেন তা **সব ইউজারের কাছে** পৌঁছে যাবে।",
        parse_mode="Markdown"
    )

# রেজিস্ট্রেশন
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("card_chake", send_card_formats))
dispatcher.add_handler(CommandHandler("admin", admin_command))
dispatcher.add_handler(CallbackQueryHandler(card_check_callback, pattern="^card_check$"))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ===================== ওয়েবহুক এন্ডপয়েন্ট =====================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(), bot)
        dispatcher.process_update(update)
        return "ok", 200
    except Exception as e:
        logger.error(f"ওয়েবহুক ত্রুটি: {e}")
        return "error", 500

@app.route("/", methods=["GET"])
def index():
    return "Bot is running", 200

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

# ===================== ওয়েবহুক সেটআপ =====================
async def set_webhook():
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        # লোকাল ডেভেলপমেন্ট বা Render-এ URL সেট না থাকলে
        render_url = "https://card-bot-2.onrender.com"  # আপনার Render URL দিন
    webhook_url = f"{render_url}/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    logger.info(f"ওয়েবহুক সেট করা হলো: {webhook_url}")

# ===================== মেইন =====================
if __name__ == "__main__":
    if BOT_TOKEN == "এখানে বট টুকেন বসান":
        raise RuntimeError("দয়া করে বট টোকেন দিন।")

    # ইভেন্ট লুপ ম্যানুয়ালি চালিয়ে ওয়েবহুক সেট করি
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(set_webhook())

    # ফ্লাস্ক চালু (Render-এর জন্য)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
