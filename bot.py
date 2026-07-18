
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

web_app = Flask(name)

# Card 1-500:

10 Birr group fi 20 Birr group addaan addaan

cards_10 = set()
cards_20 = set()

@web_app.route("/")
def home():
return "Gadaa Bingo Bot is running!"

def run_web():
port = int(os.environ.get("PORT", 10000))
web_app.run(host="0.0.0.0", port=port)

def main_menu():
keyboard = [
[InlineKeyboardButton("🎫 Buy Card", callback_data="buy_card")],
[InlineKeyboardButton("💰 Deposit", callback_data="deposit")],
[InlineKeyboardButton("💳 My Balance", callback_data="balance")],
[InlineKeyboardButton("🎲 Play Bingo", callback_data="play_bingo")]
]

return InlineKeyboardMarkup(keyboard)

def card_keyboard(group):
keyboard = []

for start in range(1, 501, 10):
    row = []

    for card_number in range(start, min(start + 10, 501)):
        if group == "10":
            taken = card_number in cards_10
        else:
            taken = card_number in cards_20

        if taken:
            text = f"❌ {card_number}"
        else:
            text = str(card_number)

        row.append(
            InlineKeyboardButton(
                text,
                callback_data=f"card_{group}_{card_number}"
            )
        )

    keyboard.append(row)

keyboard.append(
    [InlineKeyboardButton("🔙 Back", callback_data="back")]
)

return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"🎱 Welcome to Gadaa Bingo!\n\n"
"👇 Choose an option:",
reply_markup=main_menu()
)

async def button_handler(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):
query = update.callback_query
await query.answer()

data = query.data

if data == "buy_card":
    keyboard = [
        [
            InlineKeyboardButton(
                "💵 10 Birr Group",
                callback_data="group_10"
            )
        ],
        [
            InlineKeyboardButton(
                "💵 20 Birr Group",
                callback_data="group_20"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back"
            )
        ]
    ]

    await query.edit_message_text(
        "🎫 Buy Card\n\n"
        "💰 Garee taphaa kee filadhu:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

elif data == "group_10":
    await query.edit_message_text(
        "💵 10 Birr Group\n\n"
        "🎫 Kaardii 1 hanga 500 keessaa filadhu:",
        reply_markup=card_keyboard("10")
    )

elif data == "group_20":
    await query.edit_message_text(
        "💵 20 Birr Group\n\n"
        "🎫 Kaardii 1 hanga 500 keessaa filadhu:",
        reply_markup=card_keyboard("20")
    )

elif data.startswith("card_"):
    parts = data.split("_")

    group = parts[1]
    card_number = int(parts[2])

    if group == "10":
        if card_number in cards_10:
            await query.answer(
                "❌ Kaardiin kun duraan fudhatameera!",
                show_alert=True
            )
        else:
            cards_10.add(card_number)

            await query.edit_message_text(
                f"🎉 Kaardii kee milkaa'inaan filatte!\n\n"
                f"💵 Garee: 10 Birr\n"
                f"🎫 Card ID: {card_number}\n\n"
                f"⏳ Kaffaltii booda kaardiin kee ni mirkanaa'a."
            )

    elif group == "20":
        if card_number in cards_20:
            await query.answer(
                "❌ Kaardiin kun duraan fudhatameera!",
                show_alert=True
            )
        else:
            cards_20.add(card_number)

            await query.edit_message_text(
                f"🎉 Kaardii kee milkaa'inaan filatte!\n\n"
                f"💵 Garee: 20 Birr\n"
                f"🎫 Card ID: {card_number}\n\n"
                f"⏳ Kaffaltii booda kaardiin kee ni mirkanaa'a."
            )

elif data == "back":
    await query.edit_message_text(
        "🎱 Welcome to Gadaa Bingo!\n\n"
        "👇 Choose an option:",
        reply_markup=main_menu()
    )

elif data == "deposit":
    await query.answer(
        "💰 Deposit yeroo itti aanu keessatti ni hojjenna.",
        show_alert=True
    )

elif data == "balance":
    await query.answer(
        "💳 Balance yeroo itti aanu keessatti ni hojjenna.",
        show_alert=True
    )

elif data == "play_bingo":
    await query.answer(
        "🎲 Play Bingo yeroo itti aanu keessatti ni hojjenna.",
        show_alert=True
    )

def main():
token = os.environ.get("BOT_TOKEN")

threading.Thread(
    target=run_web,
    daemon=True
).start()

app = Application.builder().token(token).build()

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    CallbackQueryHandler(button_handler)
)

print("Gadaa Bingo Bot is running...")

app.run_polling()

if name == "main":
main()
