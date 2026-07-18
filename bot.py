import os
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
Application,
CommandHandler,
MessageHandler,
ContextTypes,
filters
)

Web server for Render

web_app = Flask(name)

@web_app.route("/")
def home():
return "Gadaa Bingo Bot is running!", 200

def run_web_server():
port = int(os.environ.get("PORT", "10000"))
web_app.run(
host="0.0.0.0",
port=port,
debug=False,
use_reloader=False
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
keyboard = [
["🎫 Buy Card", "💰 Deposit"],
["💳 My Balance", "🎲 Play Bingo"]
]

await update.message.reply_text(
    "🎱 Welcome to Gadaa Bingo!\n\n"
    "Filannoo tokko tuqi:",
    reply_markup=ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )
)

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text

if text == "💰 Deposit":
    await update.message.reply_text(
        "💰 Deposit\n\n"
        "Mee maallaqa galchuu barbaaddu barreessi.\n"
        "Fakkeenya: 100"
    )

elif text == "💳 My Balance":
    await update.message.reply_text(
        "💳 My Balance\n\n"
        "Balance kee amma: 0 Birr"
    )

elif text == "🎫 Buy Card":
    await update.message.reply_text(
        "🎫 Buy Card\n\n"
        "Kaardii Bingo bitachuuf qophiidhaa."
    )

elif text == "🎲 Play Bingo":
    await update.message.reply_text(
        "🎲 Play Bingo\n\n"
        "Taphni Bingo qophaa'aa jira."
    )

else:
    await update.message.reply_text(
        "Filannoo sirrii tokko tuqi."
    )

def main():
token = os.environ.get("BOT_TOKEN")

if not token:
    print("ERROR: BOT_TOKEN is missing!")
    return

# Start Render web server
threading.Thread(
    target=run_web_server,
    daemon=True
).start()

# Start Telegram bot
app = Application.builder().token(token).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        buttons
    )
)

print("Gadaa Bingo Bot is running...")
app.run_polling()

if name == "main":
main()
