import os
import random
import threading
import time

from flask import Flask, render_template_string, request, jsonify

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)


# ==================================================
# SETTINGS
# ==================================================

ADMIN_ID = 6376605934

BINGO_URL = "https://afro-bingo-6.onrender.com"

CARD_10_PRICE = 10
CARD_20_PRICE = 20


# ==================================================
# FLASK
# ==================================================

web_app = Flask(__name__)


# ==================================================
# GAME DATA
# ==================================================

bingo_game = {

    "started": False,

    "called_numbers": [],

    "current_number": None,

    "players": {},

    "winner": None

}

bingo_lock = threading.Lock()


# ==================================================
# BOT DATA
# ==================================================

balances = {}

transactions = []

cards_10 = {}

cards_20 = {}

pending_deposits = {}

pending_withdrawals = {}

winners = []

game_open = False


# ==================================================
# FLASK HOME
# ==================================================

@web_app.route("/")
def home():

    try:

        with open(
            "index.html",
            encoding="utf-8"
        ) as file:

            return render_template_string(
                file.read()
            )

    except Exception as error:

        return f"index.html error: {error}", 500


# ==================================================
# GAME STATE
# ==================================================

@web_app.route(
    "/api/game-state",
    methods=["GET"]
)
def game_state():

    with bingo_lock:

        return jsonify({

            "started":
                bingo_game["started"],

            "called_numbers":
                bingo_game["called_numbers"],

            "current_number":
                bingo_game["current_number"],

            "winner":
                bingo_game["winner"],

            "players":
                len(
                    bingo_game["players"]
                )

        })


# ==================================================
# JOIN GAME
# ==================================================

@web_app.route(
    "/api/join-game",
    methods=["POST"]
)
def join_game():

    data = request.get_json(
        silent=True
    ) or {}

    user_id = str(
        data.get(
            "user_id",
            ""
        )
    ).strip()


    if not user_id:

        return jsonify({

            "success": False,

            "message":
                "User ID hin jiru."

        }), 400


    try:

        user_id_int = int(
            user_id
        )

    except ValueError:

        return jsonify({

            "success": False,

            "message":
                "Telegram User ID sirrii miti."

        }), 400


    user_card = None


    # 10 BIRR CARD

    for (

        card_number,

        owner

    ) in cards_10.items():

        if owner == user_id_int:

            user_card = card_number

            break


    # 20 BIRR CARD

    if user_card is None:

        for (

            card_number,

            owner

        ) in cards_20.items():

            if owner == user_id_int:

                user_card = card_number

                break


    if user_card is None:

        return jsonify({

            "success": False,

            "message":
                "Ati card hin qabdu."

        }), 403


    with bingo_lock:

        bingo_game[
            "players"
        ][user_id] = {

            "joined": True,

            "card_number":
                user_card,

            "joined_at":
                time.time()

        }


    return jsonify({

        "success": True,

        "card_number":
            user_card,

        "message":
            "Game keessa seente."

    })


# ==================================================
# ADMIN CALL NUMBER
# ==================================================

@web_app.route(
    "/api/admin/call-number",
    methods=["POST"]
)
def admin_call_number():

    data = request.get_json(
        silent=True
    ) or {}


    admin_id = str(
        data.get(
            "admin_id",
            ""
        )
    )


    if admin_id != str(
        ADMIN_ID
    ):

        return jsonify({

            "success": False,

            "message":
                "Admin qofa."

        }), 403


    with bingo_lock:

        if not bingo_game[
            "started"
        ]:

            return jsonify({

                "success": False,

                "message":
                    "Game hin jalqabne."

            }), 400


        if len(

            bingo_game[
                "called_numbers"
            ]

        ) >= 75:

            return jsonify({

                "success": False,

                "message":
                    "Lakkoofsi hundi waamameera."

            }), 400


        available = [

            number

            for number in range(
                1,
                76
            )

            if number not in
            bingo_game[
                "called_numbers"
            ]

        ]


        number = random.choice(
            available
        )


        bingo_game[
            "called_numbers"
        ].append(
            number
        )


        bingo_game[
            "current_number"
        ] = number


        called_numbers = list(

            bingo_game[
                "called_numbers"
            ]

        )


    return jsonify({

        "success": True,

        "number":
            number,

        "called_numbers":
            called_numbers

    })


# ==================================================
# WEB SERVER
# ==================================================

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


# ==================================================
# BALANCE
# ==================================================

def get_balance(
    user_id
):

    return balances.get(

        user_id,

        0

    )


def add_balance(

    user_id,

    amount,

    transaction_type="DEPOSIT"

):

    balances[user_id] = (

        get_balance(
            user_id
        )

        + amount

    )


    transactions.append({

        "user_id":
            user_id,

        "type":
            transaction_type,

        "amount":
            amount

    })


def remove_balance(

    user_id,

    amount,

    transaction_type="CARD BUY"

):

    if get_balance(
        user_id
    ) < amount:

        return False


    balances[user_id] = (

        get_balance(
            user_id
        )

        - amount

    )


    transactions.append({

        "user_id":
            user_id,

        "type":
            transaction_type,

        "amount":
            -amount

    })


    return True


# ==================================================
# MAIN MENU
# ==================================================

def main_menu():

    return InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "🎫 Buy Card",

                callback_data=
                "buy_card"

            )

        ],

        [

            InlineKeyboardButton(

                "💰 Deposit",

                callback_data=
                "deposit"

            ),

            InlineKeyboardButton(

                "💳 Balance",

                callback_data=
                "balance"

            )

        ],

        [

            InlineKeyboardButton(

                "🎮 Play Game",

                callback_data=
                "play_bingo"

            )

        ],

        [

            InlineKeyboardButton(

                "💸 Withdrawal",

                callback_data=
                "withdrawal"

            )

        ],

        [

            InlineKeyboardButton(

                "🧾 My Cards",

                callback_data=
                "my_cards"

            )

        ],

        [

            InlineKeyboardButton(

                "📜 History",

                callback_data=
                "history"

            ),

            InlineKeyboardButton(

                "🏆 Winners",

                callback_data=
                "winners"

            )

        ],

        [

            InlineKeyboardButton(

                "ℹ️ How to Play",

                callback_data=
                "how_to_play"

            )

        ]

    ])


def back_button():

    return InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "🏠 Main Menu",

                callback_data=
                "back"

            )

        ]

    ])


# ==================================================
# ADMIN MENU
# ==================================================

def admin_menu():

    return InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "🎮 OPEN GAME",

                callback_data=
                "admin_open_game"

            )

        ],

        [

            InlineKeyboardButton(

                "🔒 CLOSE GAME",

                callback_data=
                "admin_close_game"

            )

        ],

        [

            InlineKeyboardButton(

                "🏠 Main Menu",

                callback_data=
                "back"

            )

        ]

    ])


# ==================================================
# START
# ==================================================

async def start(

    update: Update,

    context:
    ContextTypes.DEFAULT_TYPE

):

    user_id = (

        update
        .effective_user
        .id

    )


    if user_id not in balances:

        balances[user_id] = 0


    await update.message.reply_text(

        "🎱 Welcome to Gadaa Bingo!\n\n"

        "👇 Filannoo kee filadhu:",

        reply_markup=
        main_menu()

    )


# ==================================================
# ADMIN
# ==================================================

async def admin(

    update: Update,

    context:
    ContextTypes.DEFAULT_TYPE

):

    if (

        update
        .effective_user
        .id

        != ADMIN_ID

    ):

        await update.message.reply_text(

            "❌ Admin qofaaf."

        )

        return


    await update.message.reply_text(

        "👨‍💼 ADMIN MENU",

        reply_markup=
        admin_menu()

    )


# ==================================================
# BUTTON HANDLER
# ==================================================

async def button_handler(

    update: Update,

    context:
    ContextTypes.DEFAULT_TYPE

):

    global game_open


    query =
        update.callback_query


    await query.answer()


    data =
        query.data


    user_id =
        query.from_user.id


    # ==================================================
    # BUY CARD
    # ==================================================

    if data == "buy_card":

        await query.edit_message_text(

            "🎫 Buy Bingo Card\n\n"

            "Garee card filadhu:",

            reply_markup=
            InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(

                        "💵 10 Birr Card",

                        callback_data=
                        "group_10"

                    )

                ],

                [

                    InlineKeyboardButton(

                        "💵 20 Birr Card",

                        callback_data=
                        "group_20"

                    )

                ],

                [

                    InlineKeyboardButton(

                        "🔙 Back",

                        callback_data=
                        "back"

                    )

                ]

            ])

        )


    # ==================================================
    # CARD GROUP
    # ==================================================

    elif data in [

        "group_10",

        "group_20"

    ]:

        price = (

            10

            if data == "group_10"

            else 20

        )


        cards = (

            cards_10

            if price == 10

            else cards_20

        )


        keyboard = []

        row = []


        for number in range(

            1,

            501

        ):


            if number not in cards:

                row.append(

                    InlineKeyboardButton(

                        str(number),

                        callback_data=

                        f"buy{price}_{number}"

                    )

                )


            if len(row) == 5:

                keyboard.append(row)

                row = []


        if row:

            keyboard.append(row)


        keyboard.append([

            InlineKeyboardButton(

                "🔙 Back",

                callback_data=
                "buy_card"

            )

        ])


        await query.edit_message_text(

            f"💵 {price} Birr Card\n\n"

            "🎫 Card kee filadhu:",

            reply_markup=

            InlineKeyboardMarkup(

                keyboard

            )

        )


    # ==================================================
    # BUY CARD
    # ==================================================

    elif (

        data.startswith("buy10_")

        or

        data.startswith("buy20_")

    ):


        parts =
            data.split("_")


        price = int(

            parts[0].replace(

                "buy",

                ""

            )

        )


        card_number = int(

            parts[1]

        )


        cards = (

            cards_10

            if price == 10

            else cards_20

        )


        if card_number in cards:

            await query.answer(

                "❌ Card kun duraan bitameera.",

                show_alert=True

            )

            return


        if get_balance(
            user_id
        ) < price:

            await query.answer(

                f"❌ Balance kee {price} Birr hin gahu.",

                show_alert=True

            )

            return


        remove_balance(

            user_id,

            price,

            f"CARD {price} BUY"

        )


        cards[
            card_number
        ] = user_id


        await query.edit_message_text(

            "🎉 CARD BITAMEERA!\n\n"

            f"🎫 Card Number: {card_number}\n"

            f"💵 Price: {price} Birr\n\n"

            f"💳 Balance: "

            f"{get_balance(user_id)} Birr",

            reply_markup=
            back_button()

        )


    # ==================================================
    # DEPOSIT
    # ==================================================

    elif data == "deposit":

        await query.edit_message_text(

            "💰 Deposit\n\n"

            "Amount filadhu:",

            reply_markup=
            InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(

                        "10",

                        callback_data=
                        "amount_10"

                    ),

                    InlineKeyboardButton(

                        "20",

                        callback_data=
                        "amount_20"

                    )

                ],

                [

                    InlineKeyboardButton(

                        "50",

                        callback_data=
                        "amount_50"

                    ),

                    InlineKeyboardButton(

                        "100",

                        callback_data=
                        "amount_100"

                    )

                ],

                [

                    InlineKeyboardButton(

                        "200",

                        callback_data=
                        "amount_200"

                    ),

                    InlineKeyboardButton(

                        "500",

                        callback_data=
                        "amount_500"

                    )

                ],

                [

                    InlineKeyboardButton(

                        "1000",

                        callback_data=
                        "amount_1000"

                    )

                ],

                [

                    InlineKeyboardButton(

                        "🔙 Back",

                        callback_data=
                        "back"

                    )

                ]

            ])

        )


    # ==================================================
    # AMOUNT
    # ==================================================

    elif data.startswith(

        "amount_"

    ):


        amount = int(

            data.split("_")[1]

        )


        await query.edit_message_text(

            f"💰 Amount: {amount} Birr\n\n"

            "Telebirr filadhu:",

            reply_markup=
            InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(

                        "📱 Telebirr 1",

                        callback_data=
                        f"pay1_{amount}"

                    )

                ],

                [

                    InlineKeyboardButton(

                        "📱 Telebirr 2",

                        callback_data=
                        f"pay2_{amount}"

                    )

                ],

                [

                    InlineKeyboardButton(

                        "🔙 Back",

                        callback_data=
                        "deposit"

                    )

                ]

            ])

        )


    # ==================================================
    # PAYMENT
    # ==================================================

    elif data.startswith(

        "pay1_"

    ):

        amount = int(

            data.split("_")[1]

        )


        context.user_data[

            "proof_amount"

        ] = amount


        await query.edit_message_text(

            f"📱 Telebirr 1\n\n"

            f"💰 Amount: {amount} Birr\n"

            "📞 0902640434\n\n"

            "Erga kaffaltee booda screenshot ergi.",

            reply_markup=
            back_button()

        )


    elif data.startswith(

        "pay2_"

    ):


        amount = int(

            data.split("_")[1]

        )


        context.user_data[

            "proof_amount"

        ] = amount


        await query.edit_message_text(

            f"📱 Telebirr 2\n\n"

            f"💰 Amount: {amount} Birr\n"

            "📞 0950740256\n\n"

            "Erga kaffaltee booda screenshot ergi.",

            reply_markup=
            back_button()

        )


    # ==================================================
    # BALANCE
    # ==================================================

    elif data == "balance":

        await query.edit_message_text(

            f"💳 Balance Kee\n\n"

            f"💰 {get_balance(user_id)} Birr",

            reply_markup=
            back_button()

        )


    # ==================================================
    # PLAY GAME
    # ==================================================

    elif data == "play_bingo":

        if not game_open:

            await query.edit_message_text(

                "⏳ Game amma cufaa dha.\n\n"

                "Admin game akka banu eegi.",

                reply_markup=
                back_button()

            )

            return


        await query.edit_message_text(

            "🎮 GADAA BINGO\n\n"

            "Card kee qabda yoo ta'e "

            "button armaan gadii cuqaasi.",

            reply_markup=
            InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(

                        "🎮 PLAY BINGO NOW",

                        web_app=

                        WebAppInfo(

                            url=BINGO_URL

                        )

                    )

                ],

                [

                    InlineKeyboardButton(

                        "🔙 Back",

                        callback_data=
                        "back"

                    )

                ]

            ])

        )


    # ==================================================
    # MY CARDS
    # ==================================================

    elif data == "my_cards":

        my10 = [

            str(card)

            for card, owner

            in cards_10.items()

            if owner == user_id

        ]


        my20 = [

            str(card)

            for card, owner

            in cards_20.items()

            if owner == user_id

        ]


        await query.edit_message_text(

            "🧾 MY CARDS\n\n"

            f"💵 10 Birr:\n"

            f"{', '.join(my10) or 'Hin jiru'}\n\n"

            f"💵 20 Birr:\n"

            f"{', '.join(my20) or 'Hin jiru'}",

            reply_markup=
            back_button()

        )


    # ==================================================
    # ADMIN OPEN
    # ==================================================

    elif data == "admin_open_game":

        if user_id != ADMIN_ID:

            await query.answer(

                "❌ Admin qofaaf.",

                show_alert=True

            )

            return


        game_open = True


        with bingo_lock:

            bingo_game[
                "started"
            ] = True


            bingo_game[
                "called_numbers"
            ] = []


            bingo_game[
                "current_number"
            ] = None


            bingo_game[
                "winner"
            ] = None


            bingo_game[
                "players"
            ] = {}


        await query.edit_message_text(

            "🎮 GAME BANAMEERA!\n\n"

            "⚠️ CALL NUMBER Admin qofa.",

            reply_markup=
            admin_menu()

        )


    # ==================================================
    # ADMIN CLOSE
    # ==================================================

    elif data == "admin_close_game":

        if user_id != ADMIN_ID:

            return


        game_open = False


        with bingo_lock:

            bingo_game[
                "started"
            ] = False


        await query.edit_message_text(

            "🔒 GAME CUFAMEERA.",

            reply_markup=
            admin_menu()

        )


    # ==================================================
    # BACK
    # ==================================================

    elif data == "back":

        await query.edit_message_text(

            "🎱 Welcome to Gadaa Bingo!\n\n"

            "👇 Filannoo kee filadhu:",

            reply_markup=
            main_menu()

        )


# ==================================================
# PHOTO PAYMENT PROOF
# ==================================================

async def photo_handler(

    update: Update,

    context:
    ContextTypes.DEFAULT_TYPE

):

    amount = context.user_data.get(

        "proof_amount"

    )


    if not amount:

        await update.message.reply_text(

            "❌ Dura amount filadhu."

        )

        return


    user =
        update.effective_user


    user_id =
        user.id


    keyboard =
        InlineKeyboardMarkup([

            [

                InlineKeyboardButton(

                    "✅ Approve",

                    callback_data=

                    f"approve_{user_id}_{amount}"

                ),

                InlineKeyboardButton(

                    "❌ Reject",

                    callback_data=

                    f"reject_{user_id}"

                )

            ]

        ])


    await context.bot.send_photo(

        chat_id=ADMIN_ID,

        photo=

        update.message.photo[-1].file_id,

        caption=(

            "📥 PAYMENT PROOF\n\n"

            f"👤 {user.full_name}\n"

            f"🆔 {user_id}\n"

            f"💰 {amount} Birr"

        ),

        reply_markup=
        keyboard

    )


    await update.message.reply_text(

        "✅ Payment proof adminitti ergameera."

    )


    context.user_data.pop(

        "proof_amount",

        None

    )


# ==================================================
# TEXT HANDLER
# ==================================================

async def text_handler(

    update: Update,

    context:
    ContextTypes.DEFAULT_TYPE

):

    text =
        update.message.text.strip()


    user_id =
        update.effective_user.id


    # WITHDRAWAL AMOUNT

    if context.user_data.get(

        "withdrawal_mode"

    ):


        try:

            amount = int(text)

        except ValueError:

            await update.message.reply_text(

                "❌ Lakkoofsa sirrii galchi."

            )

            return


        if amount <= 0:

            return


        if amount > get_balance(

            user_id

        ):

            await update.message.reply_text(

                "❌ Balance kee gahaa miti."

            )

            return


        context.user_data[

            "withdraw_amount"

        ] = amount


        context.user_data[

            "withdrawal_mode"

        ] = False


        context.user_data[

            "withdraw_account_mode"

        ] = True


        await update.message.reply_text(

            f"💸 {amount} Birr\n\n"

            "Telebirr/account number ergi."

        )

        return


    # WITHDRAW ACCOUNT

    if context.user_data.get(

        "withdraw_account_mode"

    ):


        amount = context.user_data.get(

            "withdraw_amount"

        )


        pending_withdrawals[

            user_id

        ] = {

            "amount":
                amount,

            "account":
                text

        }


        keyboard =
            InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(

                        "✅ Approve",

                        callback_data=

                        f"approve_withdraw_{user_id}_{amount}"

                    ),

                    InlineKeyboardButton(

                        "❌ Reject",

                        callback_data=

                        f"reject_withdraw_{user_id}"

                    )

                ]

            ])


        await context.bot.send_message(

            chat_id=ADMIN_ID,

            text=(

                "💸 WITHDRAWAL REQUEST\n\n"

                f"🆔 User: {user_id}\n"

                f"💰 Amount: {amount} Birr\n"

                f"📱 Account: {text}"

            ),

            reply_markup=
            keyboard

        )


        await update.message.reply_text(

            "✅ Withdrawal request adminitti ergameera."

        )


        context.user_data.pop(

            "withdraw_account_mode",

            None

        )


        context.user_data.pop(

            "withdraw_amount",

            None

        )


# ==================================================
# MAIN
# ==================================================

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

        CommandHandler(

            "admin",

            admin

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


    app.add_handler(

        MessageHandler(

            filters.TEXT

            & ~filters.COMMAND,

            text_handler

        )

    )


    print(

        "🎱 Gadaa Bingo Bot is running..."

    )


    app.run_polling()


# ==================================================
# START
# ==================================================

if __name__ == "__main__":

    main()
