import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Gadaa Bingo Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎫 Buy Card", callback_data="buy_card")],
        [InlineKeyboardButton("💰 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("💳 My Balance", callback_data="balance")],
        [InlineKeyboardButton("🎲 Play Bingo", callback_data="play_bingo")]
    ]

    await update.message.reply_text(
        "🎱 Welcome to Gadaa Bingo!\n\n"
        "👇 Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "buy_card":
        keyboard = [
            [InlineKeyboardButton("💵 10 Birr", callback_data="card_10")],
            [InlineKeyboardButton("💵 20 Birr", callback_data="card_20")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]

        await query.edit_message_text(
            "🎫 Buy Card\n\n"
            "💰 Gatii kaardii filadhu:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "card_10":
        await query.edit_message_text(
            "💵 Kaardii 10 Birr filatte.\n\n"
            "⏳ Kaffaltii booda kaardiin kee siif kennama."
        )

    elif query.data == "card_20":
        await query.edit_message_text(
            "💵 Kaardii 20 Birr filatte.\n\n"
            "⏳ Kaffaltii booda kaardiin kee siif kennama."
        )

    elif query.data == "back":
        await start(update, context)


def main():
    token = os.environ.get("BOT_TOKEN")

    threading.Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Gadaa Bingo Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
