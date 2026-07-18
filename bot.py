import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))

    print("Gadaa Bingo Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    
