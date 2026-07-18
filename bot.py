import os
import threading

from flask import Flask

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)


# =========================
# SETTINGS
# =========================

ADMIN_ID = 6376605934


# =========================
# FLASK WEB SERVER
# =========================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Gadaa Bingo Bot is running!"


def run_web():

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    web_app.run(
        host="0.0.0.0",
        port=port
    )


# =========================
# CARDS
# =========================

cards_10 = set()
cards_20 = set()


# =========================
# MAIN MENU
# =========================

def main_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "🎫 Buy Card",
                callback_data="buy_card"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 Deposit",
                callback_data="deposit"
            )
        ],

        [
            InlineKeyboardButton(
                "💳 My Balance",
                callback_data="balance"
            )
        ],

        [
            InlineKeyboardButton(
                "🎲 Play Bingo",
                callback_data="play_bingo"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# MAIN MENU BUTTON
# =========================

def main_menu_button():

    keyboard = [

        [
            InlineKeyboardButton(
                "🏠 Main Menu",
                callback_data="back"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# CARD KEYBOARD
# =========================

def card_keyboard(group):

    keyboard = []


    for start in range(
        1,
        501,
        10
    ):

        row = []


        for card_number in range(
            start,
            min(
                start + 10,
                501
            )
        ):


            if group == "10":

                taken = (
                    card_number
                    in cards_10
                )

            else:

                taken = (
                    card_number
                    in cards_20
                )


            text = (

                f"❌ {card_number}"

                if taken

                else str(card_number)

            )


            row.append(

                InlineKeyboardButton(

                    text,

                    callback_data=(

                        f"card_"
                        f"{group}_"
                        f"{card_number}"

                    )

                )

            )


        keyboard.append(row)


    keyboard.append(

        [

            InlineKeyboardButton(

                "🔙 Back",

                callback_data="back"

            )

        ]

    )


    return InlineKeyboardMarkup(
        keyboard
    )


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    await update.message.reply_text(

        "🎱 Welcome to Gadaa Bingo!\n\n"

        "👇 Choose an option:",

        reply_markup=main_menu()

    )


# =========================
# BUTTON HANDLER
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    query = update.callback_query


    await query.answer()


    data = query.data


    # =========================
    # BUY CARD
    # =========================

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

            reply_markup=(

                InlineKeyboardMarkup(
                    keyboard
                )

            )

        )


    # =========================
    # GROUP 10
    # =========================

    elif data == "group_10":


        await query.edit_message_text(

            "💵 10 Birr Group\n\n"

            "🎫 Kaardii 1 hanga 500 keessaa filadhu:",

            reply_markup=card_keyboard(
                "10"
            )

        )


    # =========================
    # GROUP 20
    # =========================

    elif data == "group_20":


        await query.edit_message_text(

            "💵 20 Birr Group\n\n"

            "🎫 Kaardii 1 hanga 500 keessaa filadhu:",

            reply_markup=card_keyboard(
                "20"
            )

        )


    # =========================
    # CARD SELECTION
    # =========================

    elif data.startswith("card_"):


        parts = data.split("_")


        if len(parts) != 3:

            return


        group = parts[1]


        card_number = int(
            parts[2]
        )


        if group == "10":


            if card_number in cards_10:


                await query.answer(

                    "❌ Kaardiin kun duraan fudhatameera!",

                    show_alert=True

                )


                return


            cards_10.add(
                card_number
            )


            await query.edit_message_text(

                f"🎉 Kaardii kee filatte!\n\n"

                f"💵 Garee: 10 Birr\n"

                f"🎫 Card ID: {card_number}\n\n"

                f"💰 Amma kaffaltii raawwadhu.\n\n"

                f"📱 Telebirr 1\n"

                f"📞 0902640434",

                reply_markup=main_menu_button()

            )


        elif group == "20":


            if card_number in cards_20:


                await query.answer(

                    "❌ Kaardiin kun duraan fudhatameera!",

                    show_alert=True

                )


                return


            cards_20.add(
                card_number
            )


            await query.edit_message_text(

                f"🎉 Kaardii kee filatte!\n\n"

                f"💵 Garee: 20 Birr\n"

                f"🎫 Card ID: {card_number}\n\n"

                f"💰 Amma kaffaltii raawwadhu.\n\n"

                f"📱 Telebirr 2\n"

                f"📞 0950740256",

                reply_markup=main_menu_button()

            )


    # =========================
    # DEPOSIT
    # =========================

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

            reply_markup=(

                InlineKeyboardMarkup(
                    keyboard
                )

            )

        )


    # =========================
    # AMOUNT
    # =========================

    elif data.startswith("amount_"):


        amount = data.split("_")[1]


        keyboard = [

            [

                InlineKeyboardButton(

                    "📱 Telebirr 1",

                    callback_data=(

                        f"pay1_{amount}"

                    )

                )

            ],

            [

                InlineKeyboardButton(

                    "📱 Telebirr 2",

                    callback_data=(

                        f"pay2_{amount}"

                    )

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

            reply_markup=(

                InlineKeyboardMarkup(
                    keyboard
                )

            )

        )


    # =========================
    # TELEBIRR 1
    # =========================

    elif data.startswith("pay1_"):


        amount = data.split("_")[1]


        keyboard = [

            [

                InlineKeyboardButton(

                    "📤 Payment Proof Ergi",

                    callback_data=(

                        f"proof_{amount}"

                    )

                )

            ],

            [

                InlineKeyboardButton(

                    "🏠 Main Menu",

                    callback_data="back"

                )

            ]

        ]


        await query.edit_message_text(

            f"📱 Telebirr 1\n\n"

            f"💰 Amount: {amount} Birr\n\n"

            f"📞 0902640434\n\n"

            f"Erga {amount} Birr kaffaltee booda,\n"

            f"📸 Payment proof ergi.",

            reply_markup=(

                InlineKeyboardMarkup(
                    keyboard
                )

            )

        )


    # =========================
    # TELEBIRR 2
    # =========================

    elif data.startswith("pay2_"):


        amount = data.split("_")[1]


        keyboard = [

            [

                InlineKeyboardButton(

                    "📤 Payment Proof Ergi",

                    callback_data=(

                        f"proof_{amount}"

                    )

                )

            ],

            [

                InlineKeyboardButton(

                    "🏠 Main Menu",

                    callback_data="back"

                )

            ]

        ]


        await query.edit_message_text(

            f"📱 Telebirr 2\n\n"

            f"💰 Amount: {amount} Birr\n\n"

            f"📞 0950740256\n\n"

            f"Erga {amount} Birr kaffaltee booda,\n"

            f"📸 Payment proof ergi.",

            reply_markup=(

                InlineKeyboardMarkup(
                    keyboard
                )

            )

        )


    # =========================
    # PAYMENT PROOF
    # =========================

    elif data.startswith("proof_"):


        amount = data.split("_")[1]


        context.user_data["proof_amount"] = amount


        await query.edit_message_text(

            f"📸 Amma screenshot kaffaltii kee ergi.\n\n"

            f"💰 Amount: {amount} Birr\n\n"

            f"Screenshot payment proof kee asitti ergi.",

            reply_markup=main_menu_button()

        )


    # =========================
    # BALANCE
    # =========================

    elif data == "balance":


        await query.answer(

            "💳 Balance yeroo itti aanu keessatti ni hojjenna.",

            show_alert=True

        )


    # =========================
    # PLAY BINGO
    # =========================

    elif data == "play_bingo":


        await query.answer(

            "🎲 Play Bingo yeroo itti aanu keessatti ni hojjenna.",

            show_alert=True

        )


    # =========================
    # BACK
    # =========================

    elif data == "back":


        await query.edit_message_text(

            "🎱 Welcome to Gadaa Bingo!\n\n"

            "👇 Choose an option:",

            reply_markup=main_menu()

        )


    # =========================
    # ADMIN APPROVE
    # =========================

    elif data.startswith("approve_"):


        if query.from_user.id != ADMIN_ID:

            await query.answer(

                "❌ Admin qofaaf!",

                show_alert=True

            )

            return


        user_id = int(
            data.split("_")[1]
        )


        await context.bot.send_message(

            chat_id=user_id,

            text=(

                "✅ Payment kee mirkanaa'eera!\n\n"

                "🎉 Galatoomi."

            )

        )


        await query.edit_message_reply_markup(
            reply_markup=None
        )


        await query.answer(

            "✅ Approved",

            show_alert=True

        )


    # =========================
    # ADMIN REJECT
    # =========================

    elif data.startswith("reject_"):


        if query.from_user.id != ADMIN_ID:

            await query.answer(

                "❌ Admin qofaaf!",

                show_alert=True

            )

            return


        user_id = int(
            data.split("_")[1]
        )


        await context.bot.send_message(

            chat_id=user_id,

            text=(

                "❌ Payment proof kee "

                "hin mirkanoofne.\n\n"

                "Maaloo irra deebi'ii ilaali."

            )

        )


        await query.edit_message_reply_markup(
            reply_markup=None
        )


        await query.answer(

            "❌ Rejected",

            show_alert=True

        )


# =========================
# PHOTO HANDLER
# =========================

async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    user = update.effective_user


    amount = context.user_data.get(
        "proof_amount"
    )


    if not amount:


        await update.message.reply_text(

            "❌ Dura Payment Proof Ergi jedhu cuqaasi."

        )


        return


    user_id = user.id


    username = (

        f"@{user.username}"

        if user.username

        else "No username"

    )


    keyboard = [

        [

            InlineKeyboardButton(

                "✅ Approve",

                callback_data=(

                    f"approve_{user_id}"

                )

            ),

            InlineKeyboardButton(

                "❌ Reject",

                callback_data=(

                    f"reject_{user_id}"

                )

            )

        ]

    ]


    await context.bot.send_photo(

        chat_id=ADMIN_ID,

        photo=update.message.photo[-1].file_id,

        caption=(

            "📥 PAYMENT PROOF\n\n"

            f"👤 Name: {user.full_name}\n"

            f"🆔 User ID: {user_id}\n"

            f"🔗 Username: {username}\n"

            f"💰 Amount: {amount} Birr\n\n"

            "👇 Murtii kenni:"

        ),

        reply_markup=InlineKeyboardMarkup(

            keyboard

        )

    )


    await update.message.reply_text(

        "✅ Payment proof kee adminitti ergameera.\n\n"

        "⏳ Admin mirkaneessuu eega."

    )


    context.user_data.pop(
        "proof_amount",
        None
    )


# =========================
# MAIN
# =========================

def main():


    token = os.environ.get(
        "BOT_TOKEN"
    )


    if not token:


        print(

            "ERROR: BOT_TOKEN is missing!"

        )


        return


    threading.Thread(

        target=run_web,

        daemon=True

    ).start()


    app = (

        Application

        .builder()

        .token(token)

        .build()

    )


    app.add_handler(

        CommandHandler(

            "start",

            start

        )

    )


    app.add_handler(

        CallbackQueryHandler(

            button_handler

        )

    )


    app.add_handler(

        MessageHandler(

            filters.PHOTO,

            photo_handler

        )

    )


    print(

        "Gadaa Bingo Bot is running..."

    )


    app.run_polling()


if __name__ == "__main__":


    main()
