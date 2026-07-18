import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Web server Render akka service online godhuuf
web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Gadaa Bingo Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎱 Welcome to Gadaa Bingo!\n\n"
        "🎫 Buy Card\n"
        "💰 Deposit\n"
        "💳 My Balance\n"
        "🎲 Play Bingo"
    )

def main():
    token = os.environ.get("BOT_TOKEN")

    # Web server jalqabi
    threading.Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))

    print("Gadaa Bingo Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
