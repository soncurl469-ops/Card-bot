import re
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

CHANNEL_USERNAME = "@Vanila_cards"
ADMIN_ID = 8508012498
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7839522620:AAFz4rHDYyKfOA7kK0MfkE9G4nuyU8B_5N4")
USER_FILE = "users.txt"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

awaiting_broadcast = False


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


async def is_user_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return chat_member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.error(f"Membership check failed for {user_id}: {e}")
        return False


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
            InlineKeyboardButton("🔍 Card Check", callback_data="card_check")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def card_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
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
    await query.edit_message_text(
        "Welcome! Please provide your card details in a standard format:\n(Click any format to copy)",
        reply_markup=reply_markup,
    )


async def send_card_formats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
                logger.error(f"Failed to send to {uid}: {e}")
                fail_count += 1
        awaiting_broadcast = False
        await update.message.reply_text(f"✅ Broadcast done!\nSuccess: {success_count}\nFailed: {fail_count}")
        return

    if CARD_PATTERN.match(user_input):
        member = await is_user_member(user_id, context)
        if not member:
            await update.message.reply_text(
                "❌ You can't check the card because you're not a member of @Vanila_cards"
            )
        else:
            await update.message.reply_text(
                "✅ You are a member! Card details received.\nAdd your own card validation logic here."
            )
    else:
        await update.message.reply_text("❌ Invalid format. Please use a valid card format.")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return
    global awaiting_broadcast
    awaiting_broadcast = True
    await update.message.reply_text(
        "📢 *Broadcast Mode ON*\n\nThe next message you send will be forwarded to all users.",
        parse_mode="Markdown"
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
    app = Application.builder().token(BOT_TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("card_check", send_card_formats))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(card_check_callback, pattern="^card_check$"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    logger.info("Bot started...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
