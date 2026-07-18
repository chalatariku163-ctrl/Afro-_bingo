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

# Card 1-500
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


def back_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🏠 Main Menu",
                callback_data="back"
            )
        ]
    ])


def card_keyboard(group):
    keyboard = []

    for start in range(1, 501, 10):
        row = []

        for card_number in range(start, min(start + 10, 501)):

            if group == "10":
                taken = card_number in cards_10
            else:
                taken = card_number in cards_20

            text = f"❌ {card_number}" if taken else str(card_number)

            row.append(
                InlineKeyboardButton(
                    text,
                    callback_data=f"card_{group}_{card_number}"
                )
            )

        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            "🔙 Back",
            callback_data="back"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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


    # BUY CARD
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


    # 10 BIRR GROUP
    elif data == "group_10":

        await query.edit_message_text(
            "💵 10 Birr Group\n\n"
            "🎫 Kaardii 1 hanga 500 keessaa filadhu:",
            reply_markup=card_keyboard("10")
        )


    # 20 BIRR GROUP
    elif data == "group_20":

        await query.edit_message_text(
            "💵 20 Birr Group\n\n"
            "🎫 Kaardii 1 hanga 500 keessaa filadhu:",
            reply_markup=card_keyboard("20")
        )


    # CARD SELECTION
    elif data.startswith("card_"):

        parts = data.split("_")

        if len(parts) != 3:
            return

        group = parts[1]
        card_number = int(parts[2])


        if group == "10":

            if card_number in cards_10:

                await query.answer(
                    "❌ Kaardiin kun duraan fudhatameera!",
                    show_alert=True
                )

                return

            cards_10.add(card_number)

            await query.edit_message_text(
                f"🎉 Kaardii kee filatte!\n\n"
                f"💵 Garee: 10 Birr\n"
                f"🎫 Card ID: {card_number}\n\n"
                f"💰 Amma kaffaltii raawwadhu.\n\n"
                f"📱 Telebirr 1\n"
                f"📞 0902640434",
                reply_markup=back_menu()
            )


        elif group == "20":

            if card_number in cards_20:

                await query.answer(
                    "❌ Kaardiin kun duraan fudhatameera!",
                    show_alert=True
                )

                return

            cards_20.add(card_number)

            await query.edit_message_text(
                f"🎉 Kaardii kee filatte!\n\n"
                f"💵 Garee: 20 Birr\n"
                f"🎫 Card ID: {card_number}\n\n"
                f"💰 Amma kaffaltii raawwadhu.\n\n"
                f"📱 Telebirr 2\n"
                f"📞 0950740256",
                reply_markup=back_menu()
            )


    # DEPOSIT
    elif data == "deposit":

        keyboard = [
            [
                InlineKeyboardButton(
                    "💵 10 Birr",
                    callback_data="amount_10"
                ),
                InlineKeyboardButton(
                    "💵 20 Birr",
                    callback_data="amount_20"
                )
            ],
            [
                InlineKeyboardButton(
                    "💵 50 Birr",
                    callback_data="amount_50"
                ),
                InlineKeyboardButton(
                    "💵 100 Birr",
                    callback_data="amount_100"
                )
            ],
            [
                InlineKeyboardButton(
                    "💵 200 Birr",
                    callback_data="amount_200"
                ),
                InlineKeyboardButton(
                    "💵 500 Birr",
                    callback_data="amount_500"
                )
            ],
            [
                InlineKeyboardButton(
                    "💵 1000 Birr",
                    callback_data="amount_1000"
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
            "💰 Deposit\n\n"
            "Qarshii galchuu barbaaddu filadhu:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # DEPOSIT AMOUNT
    elif data.startswith("amount_"):

        amount = data.split("_")[1]

        keyboard = [
            [
                InlineKeyboardButton(
                    "📱 Telebirr 1",
                    callback_data=f"pay1_{amount}"
                )
            ],
            [
                InlineKeyboardButton(
                    "📱 Telebirr 2",
                    callback_data=f"pay2_{amount}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Back",
                    callback_data="deposit"
                )
            ]
        ]

        await query.edit_message_text(
            f"💰 Amount: {amount} Birr\n\n"
            "Telebirr ittiin kaffaltu filadhu:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # TELEBIRR 1
    elif data.startswith("pay1_"):

        amount = data.split("_")[1]

        await query.edit_message_text(
            f"📱 Telebirr 1\n\n"
            f"💰 Amount: {amount} Birr\n\n"
            f"📞 0902640434\n\n"
            f"Erga {amount} Birr kaffaltee booda, "
            f"ragaa kaffaltii adminitti ergi.",
            reply_markup=back_menu()
        )


    # TELEBIRR 2
    elif data.startswith("pay2_"):

        amount = data.split("_")[1]

        await query.edit_message_text(
            f"📱 Telebirr 2\n\n"
            f"💰 Amount: {amount} Birr\n\n"
            f"📞 0950740256\n\n"
            f"Erga {amount} Birr kaffaltee booda, "
            f"ragaa kaffaltii adminitti ergi.",
            reply_markup=back_menu()
        )


    # BALANCE
    elif data == "balance":

        await query.answer(
            "💳 Balance yeroo itti aanu keessatti ni hojjenna.",
            show_alert=True
        )


    # PLAY BINGO
    elif data == "play_bingo":

        await query.answer(
            "🎲 Play Bingo yeroo itti aanu keessatti ni hojjenna.",
            show_alert=True
        )


    # BACK TO MAIN MENU
    elif data == "back":

        await query.edit_message_text(
            "🎱 Welcome to Gadaa Bingo!\n\n"
            "👇 Choose an option:",
            reply_markup=main_menu()
        )


def main():

    token = os.environ.get("BOT_TOKEN")

    if not token:

        print("ERROR: BOT_TOKEN is missing!")

        return


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


if __name__ == "__main__":

    main()
