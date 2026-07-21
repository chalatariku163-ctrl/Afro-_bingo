import os
import random
import threading
import time
import json

from flask import Flask, jsonify, request, render_template

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# ==================================================
# SETTINGS
# ==================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 6376605934

BINGO_URL = "https://afro-bingo-6.onrender.com"

CARD_10_PRICE = 10
CARD_20_PRICE = 20

PRIZE_PERCENT = 70

CARD_BUYING_SECONDS = 40

NEXT_GAME_DELAY = 40

DATA_FILE = "data.json"


# ==================================================
# FLASK
# ==================================================

web_app = Flask(__name__)


# ==================================================
# GAME STATE
# ==================================================

bingo_game = {

    "game_id": 0,

    "started": False,

    "called_numbers": [],

    "current_number": None,

    "players": {},

    "winner": None,

    "winner_user_id": None,

    "prize": 0,

    "total_sales": 0,

}


bingo_lock = threading.Lock()


# ==================================================
# BOT DATA
# ==================================================

users = {}

balances = {}

transactions = []

cards_10 = {}

cards_20 = {}

pending_deposits = {}

pending_withdrawals = {}

winners = []


game_open = False

card_buying_open = False

card_buying_end_time = 0


# ==================================================
# SAVE / LOAD
# ==================================================

def save_data():

    data = {

        "users": users,

        "balances": balances,

        "transactions": transactions,

        "cards_10": cards_10,

        "cards_20": cards_20,

        "winners": winners,

    }

    try:

        with open(

            DATA_FILE,

            "w",

            encoding="utf-8"

        ) as file:

            json.dump(

                data,

                file,

                ensure_ascii=False,

                indent=2

            )

    except Exception as error:

        print(

            "SAVE ERROR:",

            error

        )


def load_data():

    global users

    global balances

    global transactions

    global cards_10

    global cards_20

    global winners


    if not os.path.exists(DATA_FILE):

        return


    try:

        with open(

            DATA_FILE,

            "r",

            encoding="utf-8"

        ) as file:

            data = json.load(file)


        users = {

            int(k): v

            for k, v in data.get(

                "users",

                {}

            ).items()

        }


        balances = {

            int(k): v

            for k, v in data.get(

                "balances",

                {}

            ).items()

        }


        transactions = data.get(

            "transactions",

            []

        )


        cards_10 = {

            int(k): int(v)

            for k, v in data.get(

                "cards_10",

                {}

            ).items()

        }


        cards_20 = {

            int(k): int(v)

            for k, v in data.get(

                "cards_20",

                {}

            ).items()

        }


        winners = data.get(

            "winners",

            []

        )


        print(

            "✅ DATA LOADED"

        )


    except Exception as error:

        print(

            "LOAD ERROR:",

            error

        )


# ==================================================
# USER FUNCTIONS
# ==================================================

def is_registered(user_id):

    return user_id in users


def get_balance(user_id):

    return balances.get(

        user_id,

        0

    )


def add_balance(

    user_id,

    amount

):

    balances[user_id] = (

        get_balance(user_id)

        + amount

    )

    save_data()


def remove_balance(

    user_id,

    amount

):

    if get_balance(user_id) < amount:

        return False


    balances[user_id] -= amount

    save_data()

    return True


def add_transaction(

    user_id,

    transaction_type,

    amount,

    status="completed",

    note=""

):

    transactions.append({

        "user_id": user_id,

        "type": transaction_type,

        "amount": amount,

        "status": status,

        "note": note,

        "time": time.time(),

    })

    save_data()


# ==================================================
# CARD FUNCTIONS
# ==================================================

def get_user_cards(user_id):

    cards = []


    for card_number, owner in cards_10.items():

        if owner == user_id:

            cards.append({

                "card_number": card_number,

                "card_type": "10",

            })


    for card_number, owner in cards_20.items():

        if owner == user_id:

            cards.append({

                "card_number": card_number,

                "card_type": "20",

            })


    return cards


def get_user_card(user_id):

    """

    Card tokko game tokko qofaaf.

    Game haaraan jalqabuun dura

    cards duraanii expire ta'u.

    """

    cards = get_user_cards(

        user_id

    )


    if not cards:

        return None


    return cards[-1][

        "card_number"

    ]


def clear_expired_cards():

    """

    Game tokko erga xumuramee booda

    cardwwan game sanaa hundi expire ta'u.

    """

    cards_10.clear()

    cards_20.clear()

    save_data()


# ==================================================
# CARD GENERATOR
# ==================================================

def generate_card(card_number):

    seed = int(card_number)


    def seeded_random(

        minimum,

        maximum

    ):

        nonlocal seed


        seed = (

            seed * 9301

            + 49297

        ) % 233280


        rnd = (

            seed

            / 233280

        )


        return int(

            minimum

            + rnd

            * (

                maximum

                - minimum

                + 1

            )

        )


    def generate_column(

        minimum,

        maximum

    ):

        numbers = []


        while len(numbers) < 5:

            number = seeded_random(

                minimum,

                maximum

            )


            if number not in numbers:

                numbers.append(number)


        return numbers


    columns = [

        generate_column(1, 15),

        generate_column(16, 30),

        generate_column(31, 45),

        generate_column(46, 60),

        generate_column(61, 75),

    ]


    card = []


    for row in range(5):

        row_data = []


        for col in range(5):

            if (

                row == 2

                and col == 2

            ):

                row_data.append(

                    "FREE"

                )

            else:

                row_data.append(

                    columns[col][row]

                )


        card.append(

            row_data

        )


    return card


# ==================================================
# BINGO VALIDATION
# ==================================================

def check_bingo(

    card,

    called_numbers

):

    marked = []


    for row in card:

        marked_row = []


        for value in row:

            if value == "FREE":

                marked_row.append(

                    True

                )

            else:

                marked_row.append(

                    value in called_numbers

                )


        marked.append(

            marked_row

        )


    # HORIZONTAL

    for row in range(5):

        if all(

            marked[row]

        ):

            return True


    # VERTICAL

    for col in range(5):

        if all(

            marked[row][col]

            for row in range(5)

        ):

            return True


    # DIAGONAL 1

    if all(

        marked[i][i]

        for i in range(5)

    ):

        return True


    # DIAGONAL 2

    if all(

        marked[i][4 - i]

        for i in range(5)

    ):

        return True


    return False


# ==================================================
# MAIN MENU
# ==================================================

def main_menu(user_id=None):

    keyboard = [

        [

            InlineKeyboardButton(

                "🎮 Play Game",

                callback_data="play_game"

            ),

            InlineKeyboardButton(

                "🎫 Buy Card",

                callback_data="buy_card"

            ),

        ],

        [

            InlineKeyboardButton(

                "💰 Deposit",

                callback_data="deposit"

            ),

            InlineKeyboardButton(

                "💳 Balance",

                callback_data="balance"

            ),

        ],

        [

            InlineKeyboardButton(

                "🧾 My Cards",

                callback_data="my_cards"

            ),

            InlineKeyboardButton(

                "💸 Withdrawal",

                callback_data="withdrawal"

            ),

        ],

        [

            InlineKeyboardButton(

                "📜 History",

                callback_data="history"

            ),

            InlineKeyboardButton(

                "🏆 Winners",

                callback_data="winners"

            ),

        ],

        [

            InlineKeyboardButton(

                "ℹ️ How to Play",

                callback_data="how_to_play"

            ),

        ],

    ]


    if user_id == ADMIN_ID:

        keyboard.append([

            InlineKeyboardButton(

                "🔓 OPEN GAME",

                callback_data="admin_open_game"

            ),

            InlineKeyboardButton(

                "🔒 CLOSE GAME",

                callback_data="admin_close_game"

            ),

        ])


    return InlineKeyboardMarkup(

        keyboard

    )


# ==================================================
# REGISTER
# ==================================================

def register_keyboard():

    return ReplyKeyboardMarkup(

        [[

            KeyboardButton(

                "📱 Register",

                request_contact=True

            )

        ]],

        resize_keyboard=True,

        one_time_keyboard=True

    )


async def start(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):

    user = update.effective_user

    user_id = user.id


    if is_registered(user_id):

        await update.message.reply_text(

            "🏠 <b>GADAA BINGO</b>\n\n"

            "Welcome back! 👋\n\n"

            "👇 Choose an option:",

            parse_mode="HTML",

            reply_markup=main_menu(

                user_id

            )

        )

        return


    await update.message.reply_text(

        "🎉 <b>WELCOME TO GADAA BINGO!</b> 🎉\n\n"

        "📱 Please register first.",

        parse_mode="HTML",

        reply_markup=register_keyboard()

    )


async def receive_contact(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):

    contact = update.message.contact

    user = update.effective_user

    user_id = user.id


    if contact.user_id != user_id:

        await update.message.reply_text(

            "⚠️ Please use the Register button."

        )

        return


    users[user_id] = {

        "id": user_id,

        "name": user.full_name,

        "username": user.username,

        "phone": contact.phone_number,

    }


    balances.setdefault(

        user_id,

        0

    )


    save_data()


    await update.message.reply_text(

        "✅ <b>REGISTRATION SUCCESSFUL!</b>\n\n"

        f"Welcome {user.first_name}! 🎉",

        parse_mode="HTML",

        reply_markup=ReplyKeyboardRemove()

    )


    await update.message.reply_text(

        "🏠 <b>MAIN MENU</b>",

        parse_mode="HTML",

        reply_markup=main_menu(

            user_id

        )

    )


# ==================================================
# BUY CARD MENU
# ==================================================

async def buy_card_menu(query):

    keyboard = [

        [

            InlineKeyboardButton(

                "🎫 10 Birr Card",

                callback_data="cards_10"

            )

        ],

        [

            InlineKeyboardButton(

                "🎫 20 Birr Card",

                callback_data="cards_20"

            )

        ],

        [

            InlineKeyboardButton(

                "🔙 Back",

                callback_data="back_menu"

            )

        ],

    ]


    await query.edit_message_text(

        "🎫 <b>BUY BINGO CARD</b>\n\n"

        "Choose card price:",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(

            keyboard

        )

    )


# ==================================================
# CARD NUMBER MENU
# ==================================================

async def card_number_menu(

    query,

    card_type

):

    if not game_open:

        await query.edit_message_text(

            "🔒 <b>GAME IS CLOSED</b>",

            parse_mode="HTML",

            reply_markup=main_menu(

                query.from_user.id

            )

        )

        return


    if not card_buying_open:

        await query.edit_message_text(

            "⏳ <b>CARD BUYING IS CLOSED</b>\n\n"

            "Wait for the next game.",

            parse_mode="HTML",

            reply_markup=main_menu(

                query.from_user.id

            )

        )

        return


    owned_cards = (

        cards_10

        if card_type == "10"

        else cards_20

    )


    keyboard = []

    row = []


    for number in range(1, 501):

        if number in owned_cards:

            text = f"⚫ {number}"

        else:

            text = f"🔴 {number}"


        row.append(

            InlineKeyboardButton(

                text,

                callback_data=(

                    f"select_"

                    f"{card_type}_"

                    f"{number}"

                )

            )

        )


        if len(row) == 5:

            keyboard.append(

                row

            )

            row = []


    if row:

        keyboard.append(

            row

        )


    keyboard.append([

        InlineKeyboardButton(

            "🔙 Back",

            callback_data="buy_card"

        )

    ])


    await query.edit_message_text(

        f"🎫 <b>{card_type} BIRR CARD</b>\n\n"

        "🔴 Available\n"

        "⚫ Already owned\n\n"

        "Choose card number:",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(

            keyboard

        )

    )


# ==================================================
# SELECT CARD
# ==================================================

async def select_card(

    query,

    user_id,

    card_type,

    card_number

):

    card_number = int(

        card_number

    )


    price = (

        CARD_10_PRICE

        if card_type == "10"

        else CARD_20_PRICE

    )


    if not game_open:

        await query.answer(

            "🔒 Game is closed.",

            show_alert=True

        )

        return


    if not card_buying_open:

        await query.answer(

            "⏳ Card buying ended.",

            show_alert=True

        )

        return


    owned_cards = (

        cards_10

        if card_type == "10"

        else cards_20

    )


    if card_number in owned_cards:

        await query.answer(

            "⚠️ Card already owned.",

            show_alert=True

        )

        return


    if get_balance(user_id) < price:

        await query.answer(

            "⚠️ Insufficient balance.",

            show_alert=True

        )

        return


    if not remove_balance(

        user_id,

        price

    ):

        await query.answer(

            "⚠️ Insufficient balance.",

            show_alert=True

        )

        return


    owned_cards[

        card_number

    ] = user_id


    add_transaction(

        user_id,

        f"buy_card_{card_type}",

        price,

        "completed",

        f"Card {card_number}"

    )


    await query.answer(

        "✅ Card purchased!",

        show_alert=True

    )


    await query.edit_message_text(

        f"✅ <b>Card {card_number} Purchased!</b>\n\n"

        f"💰 Price: {price} Birr\n"

        f"💳 Balance: "

        f"{get_balance(user_id)} Birr\n\n"

        "🎮 Now press Play Game.",

        parse_mode="HTML",

        reply_markup=main_menu(

            user_id

        )

    )


# ==================================================
# PLAY GAME
# ==================================================

async def play_game(query):

    user_id = query.from_user.id


    if not game_open:

        await query.edit_message_text(

            "🔒 <b>GAME IS CLOSED</b>",

            parse_mode="HTML",

            reply_markup=main_menu(

                user_id

            )

        )

        return


    card_number = get_user_card(

        user_id

    )


    if card_number is None:

        await query.edit_message_text(

            "⚠️ <b>You do not own a Bingo card.</b>\n\n"

            "🎫 Buy a card for this game first.",

            parse_mode="HTML",

            reply_markup=main_menu(

                user_id

            )

        )

        return


    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "🎮 OPEN BINGO GAME",

                web_app=WebAppInfo(

                    url=BINGO_URL

                )

            )

        ],

        [

            InlineKeyboardButton(

                "🔙 Back",

                callback_data="back_menu"

            )

        ]

    ])


    await query.edit_message_text(

        "🎮 <b>BINGO GAME</b>\n\n"

        f"🎫 Your card: "

        f"<b>{card_number}</b>\n\n"

        "Click below to open Bingo:",

        parse_mode="HTML",

        reply_markup=keyboard

    )


# ==================================================
# DEPOSIT
# ==================================================

async def deposit_menu(query):

    amounts = [

        10,

        20,

        50,

        100,

        200,

        500,

        1000

    ]


    keyboard = []

    row = []


    for amount in amounts:

        row.append(

            InlineKeyboardButton(

                f"💰 {amount} Birr",

                callback_data=(

                    f"deposit_{amount}"

                )

            )

        )


        if len(row) == 2:

            keyboard.append(

                row

            )

            row = []


    if row:

        keyboard.append(

            row

        )


    keyboard.append([

        InlineKeyboardButton(

            "🔙 Back",

            callback_data="back_menu"

        )

    ])


    await query.edit_message_text(

        "💰 <b>DEPOSIT</b>\n\n"

        "Choose amount:",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(

            keyboard

        )

    )


async def create_deposit(

    query,

    user_id,

    amount

):

    pending_deposits[user_id] = {

        "amount": amount,

        "status": "waiting_screenshot",

    }


    await query.edit_message_text(

        f"💰 <b>Deposit {amount} Birr</b>\n\n"

        "📱 Pay using Telebirr.\n\n"

        "📸 Send payment screenshot here.",

        parse_mode="HTML"

    )


async def receive_photo(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):

    user_id = update.effective_user.id


    if user_id not in pending_deposits:

        await update.message.reply_text(

            "⚠️ No pending deposit.",

            reply_markup=main_menu(

                user_id

            )

        )

        return


    deposit = pending_deposits[user_id]

    photo_id = update.message.photo[-1].file_id


    pending_deposits[user_id] = {

        "amount": deposit["amount"],

        "status": "pending_admin",

        "photo_id": photo_id,

    }


    await update.message.reply_text(

        "✅ Payment proof received!\n\n"

        "⏳ Waiting for admin approval.",

        reply_markup=main_menu(

            user_id

        )

    )


    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ Approve",

                callback_data=(

                    f"approve_deposit_{user_id}"

                )

            ),

            InlineKeyboardButton(

                "❌ Reject",

                callback_data=(

                    f"reject_deposit_{user_id}"

                )

            ),

        ]

    ])


    await context.bot.send_photo(

        chat_id=ADMIN_ID,

        photo=photo_id,

        caption=(

            "💰 <b>NEW DEPOSIT</b>\n\n"

            f"👤 User ID: {user_id}\n"

            f"💵 Amount: "

            f"{deposit['amount']} Birr"

        ),

        parse_mode="HTML",

        reply_markup=keyboard

    )


# ==================================================
# APPROVE DEPOSIT
# ==================================================

async def approve_deposit(

    query,

    user_id

):

    if query.from_user.id != ADMIN_ID:

        await query.answer(

            "⛔ Admin only.",

            show_alert=True

        )

        return


    deposit = pending_deposits.get(

        user_id

    )


    if not deposit:

        await query.answer(

            "Deposit not found.",

            show_alert=True

        )

        return


    amount = deposit["amount"]


    add_balance(

        user_id,

        amount

    )


    add_transaction(

        user_id,

        "deposit",

        amount,

        "approved"

    )


    del pending_deposits[user_id]


    await query.edit_message_caption(

        caption=(

            "✅ <b>DEPOSIT APPROVED</b>\n\n"

            f"User: {user_id}\n"

            f"Amount: {amount} Birr"

        ),

        parse_mode="HTML"

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "✅ <b>Deposit Approved!</b>\n\n"

            f"💰 Added: {amount} Birr\n"

            f"💳 Balance: "

            f"{get_balance(user_id)} Birr"

        ),

        parse_mode="HTML",

        reply_markup=main_menu(

            user_id

        )

    )


# ==================================================
# REJECT DEPOSIT
# ==================================================

async def reject_deposit(

    query,

    user_id

):

    if query.from_user.id != ADMIN_ID:

        return


    if user_id not in pending_deposits:

        return


    del pending_deposits[user_id]


    await query.edit_message_caption(

        caption=(

            "❌ <b>DEPOSIT REJECTED</b>\n\n"

            f"User ID: {user_id}"

        ),

        parse_mode="HTML"

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text="❌ Deposit rejected.",

        reply_markup=main_menu(

            user_id

        )

    )


# ==================================================
# BALANCE
# ==================================================

async def show_balance(

    query,

    user_id

):

    await query.edit_message_text(

        "💳 <b>YOUR BALANCE</b>\n\n"

        f"💰 Balance: "

        f"<b>{get_balance(user_id)} Birr</b>",

        parse_mode="HTML",

        reply_markup=main_menu(

            user_id

        )

    )


# ==================================================
# MY CARDS
# ==================================================

async def show_my_cards(

    query,

    user_id

):

    cards10 = [

        str(number)

        for number, owner

        in cards_10.items()

        if owner == user_id

    ]


    cards20 = [

        str(number)

        for number, owner

        in cards_20.items()

        if owner == user_id

    ]


    text = (

        "🧾 <b>MY CARDS</b>\n\n"

        "🎫 <b>10 Birr Cards:</b>\n"

        + (

            ", ".join(cards10)

            if cards10

            else

            "None"

        )

        + "\n\n"

        "🎫 <b>20 Birr Cards:</b>\n"

        + (

            ", ".join(cards20)

            if cards20

            else

            "None"

        )

    )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu(

            user_id

        )

)# ==================================================
# GAME API
# ==================================================

@web_app.route(
    "/api/game",
    methods=["GET"]
)
def game_state():

    with bingo_lock:

        return jsonify({

            "success": True,

            "game_id":
            bingo_game["game_id"],

            "started":
            bingo_game["started"],

            "called_numbers":
            bingo_game["called_numbers"],

            "current_number":
            bingo_game["current_number"],

            "winner":
            bingo_game["winner"],

            "winner_user_id":
            bingo_game["winner_user_id"],

            "game_open":
            game_open,

            "card_buying_open":
            card_buying_open,

            "card_buying_end_time":
            card_buying_end_time,

        })


# ==================================================
# MY CARD API
# ==================================================

@web_app.route(
    "/api/my-card",
    methods=["GET"]
)
def my_card():

    user_id = request.args.get(
        "user_id"
    )

    if not user_id:

        return jsonify({

            "success": False,

            "message":
            "User ID missing."

        }), 400

    try:

        user_id = int(
            user_id
        )

    except ValueError:

        return jsonify({

            "success": False,

            "message":
            "Invalid user ID."

        }), 400

    if not game_open:

        return jsonify({

            "success": False,

            "message":
            "Game is closed."

        }), 403

    card_number = get_user_card(
        user_id
    )

    if card_number is None:

        return jsonify({

            "success": False,

            "message":
            "No Bingo card."

        }), 403

    return jsonify({

        "success": True,

        "card_number":
        card_number,

        "card":
        generate_card(
            card_number
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

    user_id = data.get(
        "user_id"
    )

    if not user_id:

        return jsonify({

            "success": False,

            "message":
            "User ID missing."

        }), 400

    try:

        user_id = int(
            user_id
        )

    except ValueError:

        return jsonify({

            "success": False,

            "message":
            "Invalid user ID."

        }), 400

    if not game_open:

        return jsonify({

            "success": False,

            "message":
            "Game is closed."

        }), 403

    card_number = get_user_card(
        user_id
    )

    if card_number is None:

        return jsonify({

            "success": False,

            "message":
            "No card."

        }), 403

    with bingo_lock:

        bingo_game["players"][user_id] = {

            "card_number":
            card_number

        }

    return jsonify({

        "success": True,

        "card_number":
        card_number

    })


# ==================================================
# CALL NUMBER API
# ==================================================

@web_app.route(
    "/api/call",
    methods=["POST"]
)
def call_number():

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
            "Admin only."

        }), 403

    with bingo_lock:

        if not bingo_game[
            "started"
        ]:

            return jsonify({

                "success": False,

                "message":
                "Game has not started."

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

        if not available:

            return jsonify({

                "success": False,

                "message":
                "All numbers called."

            }), 400

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

        return jsonify({

            "success": True,

            "number":
            number,

            "called_numbers":
            bingo_game[
                "called_numbers"
            ]

        })


# ==================================================
# CHECK BINGO API
# ==================================================

@web_app.route(
    "/api/check-bingo",
    methods=["POST"]
)
def check_bingo_api():

    data = request.get_json(
        silent=True
    ) or {}

    user_id = data.get(
        "user_id"
    )

    if not user_id:

        return jsonify({

            "success": False,

            "message":
            "User ID missing."

        }), 400

    try:

        user_id = int(
            user_id
        )

    except ValueError:

        return jsonify({

            "success": False,

            "message":
            "Invalid User ID."

        }), 400

    with bingo_lock:

        if not bingo_game[
            "started"
        ]:

            return jsonify({

                "success": False,

                "message":
                "Game has not started."

            }), 400

        if bingo_game[
            "winner_user_id"
        ] is not None:

            return jsonify({

                "success": False,

                "message":
                "Winner already exists."

            }), 400

        card_number = get_user_card(
            user_id
        )

        if card_number is None:

            return jsonify({

                "success": False,

                "message":
                "Card not found."

            }), 403

        card = generate_card(
            card_number
        )

        if not check_bingo(

            card,

            bingo_game[
                "called_numbers"
            ]

        ):

            return jsonify({

                "success": False,

                "message":
                "Bingo is not complete."

            }), 400

        total_sales = (

            len(cards_10)
            * CARD_10_PRICE

            +

            len(cards_20)
            * CARD_20_PRICE

        )

        prize = int(

            total_sales
            * PRIZE_PERCENT
            / 100

        )

        bingo_game[
            "winner"
        ] = True

        bingo_game[
            "winner_user_id"
        ] = user_id

        bingo_game[
            "prize"
        ] = prize

        winners.append({

            "game_id":
            bingo_game[
                "game_id"
            ],

            "user_id":
            user_id,

            "prize":
            prize,

            "time":
            time.time(),

        })

        add_balance(

            user_id,

            prize

        )

        add_transaction(

            user_id,

            "bingo_prize",

            prize,

            "completed"

        )

        save_data()

        # WINNER BOODA
        # 40 SECONDS KEESSATTI GAME HAARAA

        threading.Thread(

            target=
            new_game_after_winner,

            daemon=True

        ).start()

        return jsonify({

            "success": True,

            "message":
            "🏆 BINGO! YOU ARE THE WINNER!",

            "prize":
            prize

        })


# ==================================================
# NEW GAME AFTER WINNER
# ==================================================

def new_game_after_winner():

    global game_open

    global card_buying_open

    global card_buying_end_time

    print(

        "🏆 WINNER FOUND"

    )

    print(

        "⏳ New game starts after 40 seconds..."

    )

    time.sleep(
        CARD_BUYING_SECONDS
    )

    with bingo_lock:

        # CARD DURAAAN BITAMEE
        # HIN HAQAMU

        bingo_game[
            "game_id"
        ] += 1

        bingo_game[
            "started"
        ] = False

        bingo_game[
            "called_numbers"
        ] = []

        bingo_game[
            "current_number"
        ] = None

        bingo_game[
            "players"
        ] = {}

        bingo_game[
            "winner"
        ] = None

        bingo_game[
            "winner_user_id"
        ] = None

        bingo_game[
            "prize"
        ] = 0

    game_open = True

    card_buying_open = True

    card_buying_end_time = (

        time.time()

        +

        CARD_BUYING_SECONDS

    )

    print(

        "🔓 NEW GAME OPENED"

    )

    print(

        "🎫 Card buying open for 40 seconds"

    )

    threading.Thread(

        target=
        card_timer_thread,

        daemon=True

    ).start()


# ==================================================
# RESET
# ==================================================

@web_app.route(

    "/api/reset",

    methods=["POST"]

)
def reset_game():

    global game_open

    global card_buying_open

    global card_buying_end_time

    game_open = False

    card_buying_open = False

    card_buying_end_time = 0

    with bingo_lock:

        bingo_game[
            "started"
        ] = False

        bingo_game[
            "called_numbers"
        ] = []

        bingo_game[
            "current_number"
        ] = None

        bingo_game[
            "players"
        ] = {}

        bingo_game[
            "winner"
        ] = None

        bingo_game[
            "winner_user_id"
        ] = None

        bingo_game[
            "prize"
        ] = 0

    return jsonify({

        "success":
        True

    })


# ==================================================
# FLASK SERVER
# ==================================================

def run_flask():

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
# ERROR HANDLER
# ==================================================

async def error_handler(

    update,

    context

):

    print(

        "ERROR:",

        context.error

    )


# ==================================================
# MAIN
# ==================================================

def main():

    if not BOT_TOKEN:

        raise ValueError(

            "BOT_TOKEN is missing."

        )

    load_data()

    threading.Thread(

        target=
        run_flask,

        daemon=True

    ).start()

    app = (

        Application

        .builder()

        .token(

            BOT_TOKEN

        )

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

            callback_handler

        )

    )

    app.add_handler(

        MessageHandler(

            filters.CONTACT,

            receive_contact

        )

    )

    app.add_handler(

        MessageHandler(

            filters.PHOTO,

            receive_photo

        )

    )

    app.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            text_handler

        )

    )

    app.add_error_handler(

        error_handler

    )

    print(

        "🎯 GADAA BINGO BOT RUNNING..."

    )

    app.run_polling()


if __name__ == "__main__":

    main()
