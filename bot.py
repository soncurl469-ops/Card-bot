import re
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# ===================== কনফিগারেশন =====================
CHANNEL_USERNAME = "@Vanila_cards"
ADMIN_ID = 8508012498
BOT_TOKEN = "এখানে বট টুকেন দিন"  # আপনার টোকেন দিন
USER_FILE = "users.txt"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

awaiting_broadcast = False

# ইউজার ম্যানেজমেন্ট
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

# মেম্বারশিপ চেক
async def is_user_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return chat_member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.error(f"মেম্বারশিপ চেক ব্যর্থ {user_id}: {e}")
        return False

# /start হ্যান্ডলার (দুটি বাটন সহ)
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

# Card Chake বাটনে ক্লিক করলে (প্লেইন টেক্সট আকারে ফরম্যাট দেখাবে)
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

# /card_chake কমান্ড (একই প্লেইন টেক্সট)
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

# কার্ড প্যাটার্ন চেক
CARD_PATTERN = re.compile(r'^\d{16}([:/\s])\d{2}([:/\s])\d{2}([:/\s])\d{3}$')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global awaiting_broadcast
    user_input = update.message.text.strip()
    user_id = update.effective_user.id
    save_user(user_id)

    # অ্যাডমিন ব্রডকাস্ট
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

    # কার্ড ফরম্যাট চেক
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

def main():
    if BOT_TOKEN == "এখানে বট টুকেন দিন":
        raise RuntimeError("দয়া করে আপনার বট টোকেন দিন।")
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
    app = Application.builder().token(BOT_TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("card_chake", send_card_formats))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(card_check_callback, pattern="^card_check$"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    logger.info("বট চালু হয়েছে...")
    app.run_polling()

if __name__ == "__main__":
    main()
