import re
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# ===================== কনফিগারেশন =====================
CHANNEL_USERNAME = "@Vanila_cards"
ADMIN_ID = 8508012498  # এডমিনের টেলিগ্রাম আইডি

# বট টোকেন - এখানে আপনার টোকেন দিন
BOT_TOKEN = "7839522620:AAGdHNFa1AuU2yQcvToTvG9_cAP4IdTGL-M"  # <-- আপনার টোকেন এখানে বসান

# ইউজার আইডি সংরক্ষণের ফাইল
USER_FILE = "users.txt"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ব্রডকাস্টের জন্য অ্যাডমিন স্টেট
awaiting_broadcast = False

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
        logger.info(f"নতুন ইউজার যোগ হলো: {user_id}")

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
    # দুটি বাটন তৈরি
    keyboard = [
        [
            InlineKeyboardButton("💳 Buy Card", url="https://t.me/vanilla_cards_bot"),
            InlineKeyboardButton("🔍 Card Chake", callback_data="card_check")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def card_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Card Chake বাটনে ক্লিক করলে কার্ড ফরম্যাট দেখাবে"""
    query = update.callback_query
    await query.answer()  # লোডিং ইফেক্ট দূর করতে
    
    formats = [
        "2222222222222222:22:22:222",
        "3333333333333333:33/33:333",
        "4444444444444444/44/44/444",
        "5555555555555555 55/55 555",
        "6666666666666666 66 66 666",
    ]
    keyboard = []
    for fmt in formats:
        button = InlineKeyboardButton(text=f"📋 {fmt}", copy_text=CopyTextButton(text=fmt))
        keyboard.append([button])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(  # বাটনের জায়গায় মেসেজ রিপ্লেস করে
        "Welcome! Please provide your card details in a standard format:",
        reply_markup=reply_markup,
    )
    # অথবা নতুন মেসেজ পাঠাতে চাইলে:
    # await query.message.reply_text(...)

async def send_card_formats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """পুরনো /card_chake কমান্ড - একই কাজ করে"""
    user_id = update.effective_user.id
    save_user(user_id)

    formats = [
        "2222222222222222:22:22:222",
        "3333333333333333:33/33:333",
        "4444444444444444/44/44/444",
        "5555555555555555 55/55 555",
        "6666666666666666 66 66 666",
    ]
    keyboard = []
    for fmt in formats:
        button = InlineKeyboardButton(text=f"📋 {fmt}", copy_text=CopyTextButton(text=fmt))
        keyboard.append([button])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome! Please provide your card details in a standard format:",
        reply_markup=reply_markup,
    )

CARD_PATTERN = re.compile(r'^\d{16}([:/\s])\d{2}([:/\s])\d{2}([:/\s])\d{3}$')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global awaiting_broadcast
    user_input = update.message.text.strip()
    user_id = update.effective_user.id
    save_user(user_id)

    # ========== অ্যাডমিন ব্রডকাস্ট হ্যান্ডলিং ==========
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
        await update.message.reply_text(
            f"✅ ব্রডকাস্ট শেষ!\nসফল: {success_count}\nব্যর্থ: {fail_count}"
        )
        return

    # ========== স্বাভাবিক মেসেজ হ্যান্ডলিং (কার্ড ফরম্যাট চেক) ==========
    if CARD_PATTERN.match(user_input):
        member = await is_user_member(user_id, context)
        if not member:
            await update.message.reply_text(
                "You can't check the card because you're not a member of @vanilla_cards_bot"
            )
        else:
            await update.message.reply_text(
                "✅ You are a member! Card details received (demo).\n"
                "Add your own card validation here."
            )
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
        "📢 **ব্রডকাস্ট মোড অন**\n\n"
        "এখন আপনি যে কোনো মেসেজ (টেক্সট, ফটো, ভিডিও, ডকুমেন্ট) পাঠাবেন, "
        "তা **সব ইউজারের কাছে** পৌঁছে যাবে।\n\n"
        "মেসেজ পাঠান শেষ হলে আমি জানিয়ে দেব।",
        parse_mode="Markdown"
    )

# ===================== মেইন ফাংশন =====================
def main() -> None:
    if BOT_TOKEN == "এখানে বট টুকেন দিন":
        raise RuntimeError("দয়া করে আপনার বট টোকেন 'BOT_TOKEN' ভেরিয়েবলে দিন।")
    
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("card_chake", send_card_formats))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(card_check_callback, pattern="^card_check$"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    logger.info("বট চালু হয়েছে, আপডেটের জন্য অপেক্ষা করছে...")
    app.run_polling()

if __name__ == "__main__":
    main()
