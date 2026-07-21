
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


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 6376605934

BINGO_URL = "https://afro-bingo-6.onrender.com"

CARD_10_PRICE = 10
CARD_20_PRICE = 20

PRIZE_PERCENT = 70

CARD_BUYING_SECONDS = 40

DATA_FILE = "data.json"


# =========================================================
# FLASK
# =========================================================

web_app = Flask(__name__)


# =========================================================
# GAME STATE
# =========================================================

bingo_game = {
    "game_id": 0,
    "started": False,
    "card_buying": False,
    "card_buying_end_time": 0,

    "called_numbers": [],
    "current_number": None,

    "players": {},

    "winner": None,
    "winner_user_id": None,
    "winner_card_number": None,

    "prize": 0,
    "total_sales": 0,
}


bingo_lock = threading.Lock()


# =========================================================
# BOT DATA
# =========================================================

users = {}

balances = {}

transactions = []

cards_10 = {}

cards_20 = {}

pending_deposits = {}

pending_withdrawals = {}

winners = []


# =========================================================
# SAVE / LOAD
# =========================================================

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

            int(k): v

            for k, v in data.get(
                "cards_10",
                {}
            ).items()

        }


        cards_20 = {

            int(k): v

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


# =========================================================
# USER FUNCTIONS
# =========================================================

def is_registered(
    user_id
):

    return user_id in users


def get_balance(
    user_id
):

    return balances.get(
        user_id,
        0
    )


def add_balance(
    user_id,
    amount
):

    balances[user_id] = (

        get_balance(
            user_id
        )

        + amount

    )

    save_data()


def remove_balance(
    user_id,
    amount
):

    if get_balance(
        user_id
    ) < amount:

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

        "user_id":
        user_id,

        "type":
        transaction_type,

        "amount":
        amount,

        "status":
        status,

        "note":
        note,

        "time":
        time.time(),

    })

    save_data()


# =========================================================
# CARD DATA HELPERS
# =========================================================

def normalize_card_data():

    """
    Data.json keessatti card duraanii yoo akkana ta'e:

        25: 123456

    gara:

        25: {
            "owner": 123456,
            "used_games": []
        }

    jijjiira.
    """

    global cards_10
    global cards_20


    for cards in [
        cards_10,
        cards_20
    ]:

        for card_number in list(
            cards.keys()
        ):

            value = cards[card_number]


            if isinstance(
                value,
                int
            ):

                cards[card_number] = {

                    "owner":
                    value,

                    "used_games":
                    [],

                    "paid_games":
                    [],

                }


            elif isinstance(
                value,
                str
            ):

                try:

                    cards[card_number] = {

                        "owner":
                        int(value),

                        "used_games":
                        [],

                        "paid_games":
                        [],

                    }

                except Exception:

                    pass


def get_card_owner(
    card_type,
    card_number
):

    cards = (

        cards_10

        if card_type == "10"

        else cards_20

    )


    card = cards.get(
        int(card_number)
    )


    if not card:

        return None


    if isinstance(
        card,
        int
    ):

        return card


    return card.get(
        "owner"
    )


def get_card_data(
    card_type,
    card_number
):

    cards = (

        cards_10

        if card_type == "10"

        else cards_20

    )


    card_number = int(
        card_number
    )


    if card_number not in cards:

        return None


    card = cards[
        card_number
    ]


    if isinstance(
        card,
        int
    ):

        card = {

            "owner":
            card,

            "used_games":
            [],

            "paid_games":
            [],

        }

        cards[
            card_number
        ] = card


    return card


def card_was_used_in_game(
    card_type,
    card_number,
    game_id
):

    card = get_card_data(
        card_type,
        card_number
    )


    if not card:

        return False


    return game_id in card.get(
        "used_games",
        []
    )


def card_was_paid_for_game(
    card_type,
    card_number,
    game_id
):

    card = get_card_data(
        card_type,
        card_number
    )


    if not card:

        return False


    return game_id in card.get(
        "paid_games",
        []
    )


def mark_card_paid_for_game(
    card_type,
    card_number,
    game_id
):

    card = get_card_data(
        card_type,
        card_number
    )


    if not card:

        return False


    paid_games = card.setdefault(
        "paid_games",
        []
    )


    if game_id not in paid_games:

        paid_games.append(
            game_id
        )


    save_data()

    return True


def mark_card_used_in_game(
    card_type,
    card_number,
    game_id
):

    card = get_card_data(
        card_type,
        card_number
    )


    if not card:

        return False


    used_games = card.setdefault(
        "used_games",
        []
    )


    if game_id not in used_games:

        used_games.append(
            game_id
        )


    save_data()

    return True


def get_user_cards(
    user_id
):

    cards = []


    for card_number, card in cards_10.items():

        owner = get_card_owner(
            "10",
            card_number
        )


        if owner == user_id:

            cards.append({

                "card_number":
                int(card_number),

                "card_type":
                "10",

            })


    for card_number, card in cards_20.items():

        owner = get_card_owner(
            "20",
            card_number
        )


        if owner == user_id:

            cards.append({

                "card_number":
                int(card_number),

                "card_type":
                "20",

            })


    return cards


def get_user_game_cards(
    user_id,
    game_id
):

    result = []


    for card in get_user_cards(
        user_id
    ):

        card_type = card[
            "card_type"
        ]

        card_number = card[
            "card_number"
        ]


        if card_was_paid_for_game(

            card_type,

            card_number,

            game_id

        ):

            result.append(
                card
            )


    return result


def get_user_card(
    user_id
):

    cards = get_user_cards(
        user_id
    )


    if not cards:

        return None


    return cards[
        -1
    ][
        "card_number"
    ]


# =========================================================
# CARD GENERATOR
# =========================================================

def generate_card(
    card_number
):

    seed = int(
        card_number
    )


    def seeded_random(
        minimum,
        maximum
    ):

        nonlocal seed


        seed = (

            seed * 9301

            + 49297

        ) % 233280


        rnd = seed / 233280


        return int(

            minimum

            + rnd * (

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


        while len(
            numbers
        ) < 5:

            number = seeded_random(

                minimum,

                maximum

            )


            if number not in numbers:

                numbers.append(
                    number
                )


        return numbers


    columns = [

        generate_column(
            1,
            15
        ),

        generate_column(
            16,
            30
        ),

        generate_column(
            31,
            45
        ),

        generate_column(
            46,
            60
        ),

        generate_column(
            61,
            75
        ),

    ]


    card = []


    for row in range(
        5
    ):

        row_data = []


        for col in range(
            5
        ):

            if (

                row == 2

                and col == 2

            ):

                row_data.append(
                    "FREE"
                )

            else:

                row_data.append(

                    columns[
                        col
                    ][
                        row
                    ]

                )


        card.append(
            row_data
        )


    return card


# =========================================================
# BINGO VALIDATION
# =========================================================

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

                    value in
                    called_numbers

                )


        marked.append(
            marked_row
        )


    for row in range(
        5
    ):

        if all(
            marked[row]
        ):

            return True


    for col in range(
        5
    ):

        if all(

            marked[row][col]

            for row in range(
                5
            )

        ):

            return True


    if all(

        marked[i][i]

        for i in range(
            5
        )

    ):

        return True


    if all(

        marked[i][4 - i]

        for i in range(
            5
        )

    ):

        return True


    return False


# =========================================================
# MAIN MENU
# =========================================================

def main_menu(
    user_id=None
):

    keyboard = [

        [

            InlineKeyboardButton(

                "🎮 Play Game",

                callback_data=
                "play_game"

            ),

            InlineKeyboardButton(

                "🎫 Buy Card",

                callback_data=
                "buy_card"

            ),

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

            ),

        ],

        [

            InlineKeyboardButton(

                "🧾 My Cards",

                callback_data=
                "my_cards"

            ),

            InlineKeyboardButton(

                "💸 Withdrawal",

                callback_data=
                "withdrawal"

            ),

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

            ),

        ],

        [

            InlineKeyboardButton(

                "ℹ️ How to Play",

                callback_data=
                "how_to_play"

            ),

        ],

    ]


    if user_id == ADMIN_ID:

        keyboard.append([

            InlineKeyboardButton(

                "🔓 OPEN GAME",

                callback_data=
                "admin_open_game"

            ),

            InlineKeyboardButton(

                "🔒 CLOSE GAME",

                callback_data=
                "admin_close_game"

            ),

        ])


    return InlineKeyboardMarkup(
        keyboard
    )


# =========================================================
# REGISTER
# =========================================================

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


    if is_registered(
        user_id
    ):

        await update.message.reply_text(

            "🏠 <b>GADAA BINGO</b>\n\n"

            "Welcome back! 👋\n\n"

            "👇 Choose an option:",

            parse_mode="HTML",

            reply_markup=
            main_menu(
                user_id
            )

        )

        return


    await update.message.reply_text(

        "🎉 <b>WELCOME TO GADAA BINGO!</b> 🎉\n\n"

        "📱 Please register first.",

        parse_mode="HTML",

        reply_markup=
        register_keyboard()

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

        "id":
        user_id,

        "name":
        user.full_name,

        "username":
        user.username,

        "phone":
        contact.phone_number,

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

        reply_markup=
        ReplyKeyboardRemove()

    )


    await update.message.reply_text(

        "🏠 <b>MAIN MENU</b>",

        parse_mode="HTML",

        reply_markup=
        main_menu(
            user_id
        )

    )


# =========================================================
# BUY CARD MENU
# =========================================================

async def buy_card_menu(
    query
):

    keyboard = [

        [

            InlineKeyboardButton(

                "🎫 10 Birr Card",

                callback_data=
                "cards_10"

            )

        ],

        [

            InlineKeyboardButton(

                "🎫 20 Birr Card",

                callback_data=
                "cards_20"

            )

        ],

        [

            InlineKeyboardButton(

                "🔙 Back",

                callback_data=
                "back_menu"

            )

        ],

    ]


    await query.edit_message_text(

        "🎫 <b>BUY BINGO CARD</b>\n\n"

        "Choose card price:",

        parse_mode="HTML",

        reply_markup=
        InlineKeyboardMarkup(
            keyboard
        )

    )


# =========================================================
# CARD NUMBER MENU
# =========================================================

async def card_number_menu(
    query,
    card_type
):

    user_id = query.from_user.id


    with bingo_lock:

        game_open = bingo_game[
            "card_buying"
        ]

        game_id = bingo_game[
            "game_id"
        ]


    if not game_open:

        await query.edit_message_text(

            "⏳ <b>CARD BUYING IS CLOSED</b>\n\n"

            "Wait for the next game.",

            parse_mode="HTML",

            reply_markup=
            main_menu(
                user_id
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


    for number in range(
        1,
        501
    ):

        card = get_card_data(

            card_type,

            number

        )


        if number not in owned_cards:

            text = f"🔴 {number}"


        else:

            owner = get_card_owner(

                card_type,

                number

            )


            if owner != user_id:

                text = f"⚫ {number}"


            elif card_was_paid_for_game(

                card_type,

                number,

                game_id

            ):

                text = f"🟢 {number}"


            else:

                text = f"🔵 {number}"


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

            callback_data=
            "buy_card"

        )

    ])


    await query.edit_message_text(

        f"🎫 <b>{card_type} BIRR CARD</b>\n\n"

        f"🎮 Game: <b>{game_id}</b>\n\n"

        "🔴 Available\n"

        "⚫ Other user owns\n"

        "🔵 Your old card - pay again\n"

        "🟢 Already paid for this game\n\n"

        "Choose card number:",

        parse_mode="HTML",

        reply_markup=
        InlineKeyboardMarkup(
            keyboard
        )

    )


# =========================================================
# SELECT CARD
# =========================================================

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


    with bingo_lock:

        card_buying = bingo_game[
            "card_buying"
        ]

        game_id = bingo_game[
            "game_id"
        ]


    if not card_buying:

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


    owner = get_card_owner(

        card_type,

        card_number

    )


    if owner is not None and owner != user_id:

        await query.answer(

            "⚠️ Card already owned by another user.",

            show_alert=True

        )

        return


    if owner == user_id and card_was_paid_for_game(

        card_type,

        card_number,

        game_id

    ):

        await query.answer(

            "✅ You already paid for this card in this game.",

            show_alert=True

        )

        return


    if get_balance(
        user_id
    ) < price:

        await query.answer(

            f"⚠️ You need {price} Birr.",

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


    if owner is None:

        owned_cards[
            card_number
        ] = {

            "owner":
            user_id,

            "used_games":
            [],

            "paid_games":
            [],

        }


    mark_card_paid_for_game(

        card_type,

        card_number,

        game_id

    )


    add_transaction(

        user_id,

        f"buy_card_{card_type}",

        price,

        "completed",

        f"Card {card_number} - Game {game_id}"

    )


    await query.answer(

        "✅ Card paid for this game!",

        show_alert=True

    )


    await query.edit_message_text(

        f"✅ <b>Card {card_number} READY!</b>\n\n"

        f"🎮 Game: <b>{game_id}</b>\n"

        f"💰 Paid: {price} Birr\n"

        f"💳 Balance: {get_balance(user_id)} Birr\n\n"

        "🎮 You can buy another card too.",

        parse_mode="HTML",

        reply_markup=
        main_menu(
            user_id
        )

    )


# =========================================================
# PLAY GAME
# =========================================================

async def play_game(
    query
):

    user_id = query.from_user.id


    with bingo_lock:

        game_id = bingo_game[
            "game_id"
        ]

        started = bingo_game[
            "started"
        ]

        card_buying = bingo_game[
            "card_buying"
        ]


    cards = get_user_game_cards(

        user_id,

        game_id

    )


    if not cards:

        await query.edit_message_text(

            "⚠️ <b>You have no card for this game.</b>\n\n"

            "You must pay for a card for the current game.",

            parse_mode="HTML",

            reply_markup=
            main_menu(
                user_id
            )

        )

        return


    card_numbers = ", ".join(

        str(
            card["card_number"]
        )

        for card in cards

    )


    status_text = (

        "🎮 Game is running."

        if started

        else

        "⏳ Waiting for game to start."

    )


    if card_buying:

        status_text = (

            "🎫 Card buying is open."

        )


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

                "🎫 BUY ANOTHER CARD",

                callback_data=
                "buy_card"

            )

        ],

        [

            InlineKeyboardButton(

                "🔙 Back",

                callback_data=
                "back_menu"

            )

        ]

    ])


    await query.edit_message_text(

        "🎮 <b>BINGO GAME</b>\n\n"

        f"🎯 Game ID: <b>{game_id}</b>\n"

        f"🎫 Your cards: <b>{card_numbers}</b>\n\n"

        f"{status_text}\n\n"

        "Click below to open Bingo:",

        parse_mode="HTML",

        reply_markup=keyboard

    )


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_menu(
    query
):

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

            callback_data=
            "back_menu"

        )

    ])


    await query.edit_message_text(

        "💰 <b>DEPOSIT</b>\n\n"

        "Choose amount:",

        parse_mode="HTML",

        reply_markup=
        InlineKeyboardMarkup(
            keyboard
        )

    )


async def create_deposit(
    query,
    user_id,
    amount
):

    pending_deposits[
        user_id
    ] = {

        "amount":
        amount,

        "status":
        "waiting_screenshot",

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

            reply_markup=
            main_menu(
                user_id
            )

        )

        return


    deposit = pending_deposits[
        user_id
    ]


    photo_id = update.message.photo[
        -1
    ].file_id


    pending_deposits[
        user_id
    ] = {

        "amount":
        deposit["amount"],

        "status":
        "pending_admin",

        "photo_id":
        photo_id,

    }


    await update.message.reply_text(

        "✅ Payment proof received!\n\n"

        "⏳ Waiting for admin approval.",

        reply_markup=
        main_menu(
            user_id
        )

    )


    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ Approve",

                callback_data=(

                    f"approve_deposit_"
                    f"{user_id}"

                )

            ),

            InlineKeyboardButton(

                "❌ Reject",

                callback_data=(

                    f"reject_deposit_"
                    f"{user_id}"

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


# =========================================================
# APPROVE DEPOSIT
# =========================================================

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


    amount = deposit[
        "amount"
    ]


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


    del pending_deposits[
        user_id
    ]


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

        reply_markup=
        main_menu(
            user_id
        )

    )


async def reject_deposit(
    query,
    user_id
):

    if query.from_user.id != ADMIN_ID:

        return


    if user_id not in pending_deposits:

        return


    del pending_deposits[
        user_id
    ]


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

        reply_markup=
        main_menu(
            user_id
        )

    )


# =========================================================
# BALANCE
# =========================================================

async def show_balance(
    query,
    user_id
):

    await query.edit_message_text(

        "💳 <b>YOUR BALANCE</b>\n\n"

        f"💰 Balance: "

        f"<b>{get_balance(user_id)} Birr</b>",

        parse_mode="HTML",

        reply_markup=
        main_menu(
            user_id
        )

    )


# =========================================================
# MY CARDS
# =========================================================

async def show_my_cards(
    query,
    user_id
):

    cards10 = []


    for number in cards_10:

        if get_card_owner(

            "10",

            number

        ) == user_id:

            card = get_card_data(

                "10",

                number

            )


            cards10.append(

                f"{number}"

            )


    cards20 = []


    for number in cards_20:

        if get_card_owner(

            "20",

            number

        ) == user_id:

            cards20.append(

                f"{number}"

            )


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

        + "\n\n"

        "ℹ️ Card duraan bitame hin haqamu.\n"

        "🎮 Game haaraa keessatti itti fayyadamuuf "

        "irra deebiin kaffaluu qabda."

    )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=
        main_menu(
            user_id
        )

    )


# =========================================================
# WITHDRAWAL
# =========================================================

async def withdrawal_start(
    query,
    user_id
):

    if get_balance(
        user_id
    ) <= 0:

        await query.edit_message_text(

            "💸 <b>WITHDRAWAL</b>\n\n"

            "⚠️ Your balance is empty.\n\n"

            "Send amount like:\n"

            "<code>withdraw 100</code>",

            parse_mode="HTML",

            reply_markup=
            main_menu(
                user_id
            )

        )

        return


    await query.edit_message_text(

        "💸 <b>WITHDRAWAL</b>\n\n"

        f"💳 Balance: "

        f"{get_balance(user_id)} Birr\n\n"

        "Send your withdrawal request:\n\n"

        "<code>withdraw 100\n"

        "telebirr: 09xxxxxxxx</code>",

        parse_mode="HTML",

        reply_markup=
        main_menu(
            user_id
        )

    )


async def process_withdrawal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    text = update.message.text.strip()


    if not text.lower().startswith(
        "withdraw"
    ):

        return False


    lines = text.splitlines()


    if len(lines) < 2:

        await update.message.reply_text(

            "❌ Format sirrii miti.\n\n"

            "Fakkeenya:\n"

            "<code>withdraw 100\n"

            "telebirr: 09xxxxxxxx</code>",

            parse_mode="HTML"

        )

        return True


    try:

        amount = int(

            lines[0].split()[1]

        )

    except Exception:

        await update.message.reply_text(

            "❌ Amount sirrii miti."

        )

        return True


    account = lines[1].strip()


    if amount <= 0:

        await update.message.reply_text(

            "❌ Amount sirrii miti."

        )

        return True


    if get_balance(
        user_id
    ) < amount:

        await update.message.reply_text(

            "⚠️ Balance gahaa miti."

        )

        return True


    if user_id in pending_withdrawals:

        await update.message.reply_text(

            "⏳ Withdrawal request duraan jira."

        )

        return True


    remove_balance(

        user_id,

        amount

    )


    pending_withdrawals[
        user_id
    ] = {

        "user_id":
        user_id,

        "amount":
        amount,

        "account":
        account,

        "status":
        "pending",

        "time":
        time.time(),

    }


    add_transaction(

        user_id,

        "withdrawal",

        amount,

        "pending",

        account

    )


    await update.message.reply_text(

        "✅ <b>WITHDRAWAL REQUEST SENT</b>\n\n"

        f"💰 Amount: {amount} Birr\n"

        f"📱 Account: {account}\n\n"

        "⏳ Waiting for admin approval.",

        parse_mode="HTML",

        reply_markup=
        main_menu(
            user_id
        )

    )


    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ Approve",

                callback_data=(

                    f"approve_withdrawal_"
                    f"{user_id}"

                )

            ),

            InlineKeyboardButton(

                "❌ Reject",

                callback_data=(

                    f"reject_withdrawal_"
                    f"{user_id}"

                )

            ),

        ]

    ])


    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(

            "💸 <b>NEW WITHDRAWAL</b>\n\n"

            f"👤 User ID: {user_id}\n"

            f"💰 Amount: {amount} Birr\n"

            f"📱 Account: {account}"

        ),

        parse_mode="HTML",

        reply_markup=keyboard

    )


    return True


async def approve_withdrawal(
    query,
    user_id
):

    if query.from_user.id != ADMIN_ID:

        return


    request_data = pending_withdrawals.get(

        user_id

    )


    if not request_data:

        return


    amount = request_data[
        "amount"
    ]


    add_transaction(

        user_id,

        "withdrawal",

        amount,

        "approved",

        request_data[
            "account"
        ]

    )


    del pending_withdrawals[
        user_id
    ]


    await query.edit_message_text(

        "✅ <b>WITHDRAWAL APPROVED</b>\n\n"

        f"User: {user_id}\n"

        f"Amount: {amount} Birr",

        parse_mode="HTML"

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "✅ <b>WITHDRAWAL APPROVED</b>\n\n"

            f"💰 Amount: {amount} Birr\n"

            f"📱 Account: "

            f"{request_data['account']}"

        ),

        parse_mode="HTML",

        reply_markup=
        main_menu(
            user_id
        )

    )


async def reject_withdrawal(
    query,
    user_id
):

    if query.from_user.id != ADMIN_ID:

        return


    request_data = pending_withdrawals.get(

        user_id

    )


    if not request_data:

        return


    amount = request_data[
        "amount"
    ]


    add_balance(

        user_id,

        amount

    )


    add_transaction(

        user_id,

        "withdrawal",

        amount,

        "rejected",

        request_data[
            "account"
        ]

    )


    del pending_withdrawals[
        user_id
    ]


    await query.edit_message_text(

        "❌ <b>WITHDRAWAL REJECTED</b>\n\n"

        f"User: {user_id}\n"

        f"Amount returned: {amount} Birr",

        parse_mode="HTML"

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "❌ <b>WITHDRAWAL REJECTED</b>\n\n"

            f"💰 {amount} Birr balance kee irratti "

            "deebi'e."

        ),

        parse_mode="HTML",

        reply_markup=
        main_menu(
            user_id
        )

    )


# =========================================================
# HISTORY
# =========================================================

async def show_history(
    query,
    user_id
):

    user_transactions = [

        item

        for item in transactions

        if item[
            "user_id"
        ] == user_id

    ]


    if not user_transactions:

        text = (

            "📜 <b>HISTORY</b>\n\n"

            "No transactions yet."

        )


    else:

        lines = [

            "📜 <b>HISTORY</b>\n"

        ]


        for item in reversed(

            user_transactions[
                -15:
            ]

        ):

            lines.append(

                f"• {item['type']}\n"

                f"  💰 {item['amount']} Birr\n"

                f"  📌 {item['status']}\n"

            )


        text = "\n".join(
            lines
        )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=
        main_menu(
            user_id
        )

    )


# =========================================================
# WINNERS
# =========================================================

async def show_winners(
    query,
    user_id
):

    if not winners:

        text = (

            "🏆 <b>WINNERS</b>\n\n"

            "No winners yet."

        )


    else:

        lines = [

            "🏆 <b>WINNERS</b>\n"

        ]


        for winner in reversed(

            winners[
                -20:
            ]

        ):

            winner_id = winner[
                "user_id"
            ]


            user_data = users.get(

                winner_id,

                {}

            )


            name = user_data.get(

                "name",

                str(
                    winner_id
                )

            )


            lines.append(

                f"🏆 {name}\n"

                f"🎮 Game: "

                f"{winner['game_id']}\n"

                f"🎫 Card: "

                f"{winner.get('card_number', '-')}\n"

                f"💰 Prize: "

                f"{winner['prize']} Birr\n"

            )


        text = "\n".join(
            lines
        )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=
        main_menu(
            user_id
        )

    )


# =========================================================
# HOW TO PLAY
# =========================================================

async def how_to_play(
    query
):

    await query.edit_message_text(

        "ℹ️ <b>HOW TO PLAY GADAA BINGO</b>\n\n"

        "1️⃣ Deposit money\n"

        "2️⃣ Buy/pay for Bingo card\n"

        "3️⃣ One card is valid for one game only\n"

        "4️⃣ You can use multiple cards in one game\n"

        "5️⃣ After the game ends, pay again for the next game\n"

        "6️⃣ Wait until game starts\n"

        "7️⃣ Numbers 1–75 are called\n"

        "8️⃣ Complete row, column or diagonal\n"

        "9️⃣ Press BINGO\n"

        "🔟 Server checks your card\n\n"

        "🏆 Winner gets the prize.",

        parse_mode="HTML",

        reply_markup=
        main_menu(

            query.from_user.id

        )

    )


# =========================================================
# START NEW GAME
# =========================================================

def start_new_game():

    with bingo_lock:

        bingo_game[
            "game_id"
        ] += 1

        bingo_game[
            "started"
        ] = False

        bingo_game[
            "card_buying"
        ] = True

        bingo_game[
            "card_buying_end_time"
        ] = (

            time.time()

            + CARD_BUYING_SECONDS

        )

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
            "winner_card_number"
        ] = None

        bingo_game[
            "prize"
        ] = 0

        bingo_game[
            "total_sales"
        ] = 0


    print(

        f"🎫 GAME {bingo_game['game_id']} "

        "CARD BUYING OPENED"

    )


    threading.Thread(

        target=card_timer_thread,

        daemon=True

    ).start()


# =========================================================
# CARD TIMER
# =========================================================

def card_timer_thread():

    time.sleep(

        CARD_BUYING_SECONDS

    )


    with bingo_lock:

        if not bingo_game[
            "card_buying"
        ]:

            return


        bingo_game[
            "card_buying"
        ] = False

        bingo_game[
            "started"
        ] = True


    print(

        f"🎮 GAME "

        f"{bingo_game['game_id']} "

        "STARTED"

    )


# =========================================================
# ADMIN OPEN GAME
# =========================================================

async def admin_open_game(
    query
):

    if query.from_user.id != ADMIN_ID:

        await query.answer(

            "⛔ Admin only.",

            show_alert=True

        )

        return


    with bingo_lock:

        if bingo_game[
            "started"
        ] or bingo_game[
            "card_buying"
        ]:

            await query.answer(

                "⚠️ Game already open.",

                show_alert=True

            )

            return


    start_new_game()


    with bingo_lock:

        game_id = bingo_game[
            "game_id"
        ]


    await query.edit_message_text(

        "🔓 <b>GAME OPENED</b>\n\n"

        f"🎮 Game ID: <b>{game_id}</b>\n"

        f"🎫 Card buying: "

        f"<b>{CARD_BUYING_SECONDS} seconds</b>\n\n"

        "⏳ After 40 seconds game starts automatically.",

        parse_mode="HTML",

        reply_markup=
        main_menu(
            ADMIN_ID
        )

    )


# =========================================================
# ADMIN CLOSE GAME
# =========================================================

async def admin_close_game(
    query
):

    if query.from_user.id != ADMIN_ID:

        await query.answer(

            "⛔ Admin only.",

            show_alert=True

        )

        return


    with bingo_lock:

        bingo_game[
            "started"
        ] = False

        bingo_game[
            "card_buying"
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
            "winner_card_number"
        ] = None

        bingo_game[
            "prize"
        ] = 0


    await query.edit_message_text(

        "🔒 <b>GAME CLOSED</b>",

        parse_mode="HTML",

        reply_markup=
        main_menu(
            ADMIN_ID
        )

    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query


    await query.answer()


    user_id = query.from_user.id

    data = query.data


    if data == "back_menu":

        await query.edit_message_text(

            "🏠 <b>MAIN MENU</b>",

            parse_mode="HTML",

            reply_markup=
            main_menu(
                user_id
            )

        )

        return


    if data == "buy_card":

        await buy_card_menu(
            query
        )

        return


    if data == "cards_10":

        await card_number_menu(

            query,

            "10"

        )

        return


    if data == "cards_20":

        await card_number_menu(

            query,

            "20"

        )

        return


    if data.startswith(
        "select_"
    ):

        parts = data.split(
            "_"
        )


        await select_card(

            query,

            user_id,

            parts[1],

            parts[2]

        )

        return


    if data == "play_game":

        await play_game(
            query
        )

        return


    if data == "deposit":

        await deposit_menu(
            query
        )

        return


    if data.startswith(
        "deposit_"
    ):

        amount = int(

            data.split(
                "_"
            )[1]

        )


        await create_deposit(

            query,

            user_id,

            amount

        )

        return


    if data == "balance":

        await show_balance(

            query,

            user_id

        )

        return


    if data == "my_cards":

        await show_my_cards(

            query,

            user_id

        )

        return


    if data == "withdrawal":

        await withdrawal_start(

            query,

            user_id

        )

        return


    if data == "history":

        await show_history(

            query,

            user_id

        )

        return


    if data == "winners":

        await show_winners(

            query,

            user_id

        )

        return


    if data == "how_to_play":

        await how_to_play(
            query
        )

        return


    if data == "admin_open_game":

        await admin_open_game(
            query
        )

        return


    if data == "admin_close_game":

        await admin_close_game(
            query
        )

        return


    if data.startswith(

        "approve_deposit_"

    ):

        target_id = int(

            data.split(
                "_"
            )[2]

        )


        await approve_deposit(

            query,

            target_id

        )

        return


    if data.startswith(

        "reject_deposit_"

    ):

        target_id = int(

            data.split(
                "_"
            )[2]

        )


        await reject_deposit(

            query,

            target_id

        )

        return


    if data.startswith(

        "approve_withdrawal_"

    ):

        target_id = int(

            data.split(
                "_"
            )[2]

        )


        await approve_withdrawal(

            query,

            target_id

        )

        return


    if data.startswith(

        "reject_withdrawal_"

    ):

        target_id = int(

            data.split(
                "_"
            )[2]

        )


        await reject_withdrawal(

            query,

            target_id

        )

        return


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    handled = await process_withdrawal(

        update,

        context

    )


    if handled:

        return


    await update.message.reply_text(

        "⚠️ Please use the menu buttons.",

        reply_markup=
        main_menu(

            update.effective_user.id

        )

    )


# =========================================================
# WEB APP HOME
# =========================================================

@web_app.route(
    "/"
)
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# GAME API
# =========================================================

@web_app.route(
    "/api/game",
    methods=["GET"]
)
def game_state():

    with bingo_lock:

        return jsonify({

            "success":
            True,

            "game_id":
            bingo_game[
                "game_id"
            ],

            "started":
            bingo_game[
                "started"
            ],

            "card_buying":
            bingo_game[
                "card_buying"
            ],

            "card_buying_end_time":
            bingo_game[
                "card_buying_end_time"
            ],

            "called_numbers":
            bingo_game[
                "called_numbers"
            ],

            "current_number":
            bingo_game[
                "current_number"
            ],

            "winner":
            bingo_game[
                "winner"
            ],

            "winner_user_id":
            bingo_game[
                "winner_user_id"
            ],

            "winner_card_number":
            bingo_game[
                "winner_card_number"
            ],

        })


# =========================================================
# MY CARDS API
# =========================================================

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

            "success":
            False,

            "message":
            "User ID missing."

        }), 400


    try:

        user_id = int(
            user_id
        )

    except ValueError:

        return jsonify({

            "success":
            False,

            "message":
            "Invalid user ID."

        }), 400


    with bingo_lock:

        game_id = bingo_game[
            "game_id"
        ]

        game_open = (

            bingo_game[
                "started"
            ]

            or

            bingo_game[
                "card_buying"
            ]

        )


    if not game_open:

        return jsonify({

            "success":
            False,

            "message":
            "Game is closed."

        }), 403


    cards = get_user_game_cards(

        user_id,

        game_id

    )


    if not cards:

        return jsonify({

            "success":
            False,

            "message":
            "No card paid for this game."

        }), 403


    result = []


    for card in cards:

        card_number = card[
            "card_number"
        ]


        result.append({

            "card_number":
            card_number,

            "card_type":
            card[
                "card_type"
            ],

            "card":
            generate_card(
                card_number
            )

        })


    return jsonify({

        "success":
        True,

        "game_id":
        game_id,

        "cards":
        result

    })


# =========================================================
# JOIN GAME
# =========================================================

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

            "success":
            False,

            "message":
            "User ID missing."

        }), 400


    try:

        user_id = int(
            user_id
        )

    except ValueError:

        return jsonify({

            "success":
            False,

            "message":
            "Invalid user ID."

        }), 400


    with bingo_lock:

        game_id = bingo_game[
            "game_id"
        ]

        game_open = (

            bingo_game[
                "started"
            ]

            or

            bingo_game[
                "card_buying"
            ]

        )


    if not game_open:

        return jsonify({

            "success":
            False,

            "message":
            "Game is closed."

        }), 403


    cards = get_user_game_cards(

        user_id,

        game_id

    )


    if not cards:

        return jsonify({

            "success":
            False,

            "message":
            "No paid card for this game."

        }), 403


    with bingo_lock:

        bingo_game[
            "players"
        ][
            user_id
        ] = {

            "cards":
            cards

        }


        for card in cards:

            mark_card_used_in_game(

                card[
                    "card_type"
                ],

                card[
                    "card_number"
                ],

                game_id

            )


    return jsonify({

        "success":
        True,

        "game_id":
        game_id,

        "cards":
        cards

    })


# =========================================================
# CALL NUMBER API
# =========================================================

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

            "success":
            False,

            "message":
            "Admin only."

        }), 403


    with bingo_lock:

        if not bingo_game[
            "started"
        ]:

            return jsonify({

                "success":
                False,

                "message":
                "Game has not started."

            }), 400


        available = [

            number

            for number in range(
                1,
                76
            )

            if number not in bingo_game[
                "called_numbers"
            ]

        ]


        if not available:

            return jsonify({

                "success":
                False,

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

            "success":
            True,

            "number":
            number,

            "called_numbers":
            bingo_game[
                "called_numbers"
            ]

        })


# =========================================================
# CHECK BINGO API
# =========================================================

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

            "success":
            False,

            "message":
            "User ID missing."

        }), 400


    try:

        user_id = int(
            user_id
        )

    except ValueError:

        return jsonify({

            "success":
            False,

            "message":
            "Invalid User ID."

        }), 400


    with bingo_lock:

        if not bingo_game[
            "started"
        ]:

            return jsonify({

                "success":
                False,

                "message":
                "Game has not started."

            }), 400


        if bingo_game[
            "winner_user_id"
        ] is not None:

            return jsonify({

                "success":
                False,

                "message":
                "Winner already exists."

            }), 400


        game_id = bingo_game[
            "game_id"
        ]


        cards = get_user_game_cards(

            user_id,

            game_id

        )


        if not cards:

            return jsonify({

                "success":
                False,

                "message":
                "No card for this game."

            }), 403


        winning_card = None


        for card_data in cards:

            card_number = card_data[
                "card_number"
            ]


            card = generate_card(

                card_number

            )


            if check_bingo(

                card,

                bingo_game[
                    "called_numbers"
                ]

            ):

                winning_card = card_number

                break


        if winning_card is None:

            return jsonify({

                "success":
                False,

                "message":
                "Bingo is not complete."

            }), 400


        total_sales = 0


        for card in cards_10.values():

            total_sales += CARD_10_PRICE


        for card in cards_20.values():

            total_sales += CARD_20_PRICE


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
            "winner_card_number"
        ] = winning_card


        bingo_game[
            "prize"
        ] = prize


        winners.append({

            "game_id":
            game_id,

            "user_id":
            user_id,

            "card_number":
            winning_card,

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

            "completed",

            f"Game {game_id}"

        )


        save_data()


        threading.Thread(

            target=automatic_next_game,

            daemon=True

        ).start()


        return jsonify({

            "success":
            True,

            "message":
            "🏆 BINGO! YOU ARE THE WINNER!",

            "prize":
            prize,

            "card_number":
            winning_card

        })


# =========================================================
# AUTOMATIC NEXT GAME
# =========================================================

def automatic_next_game():

    print(

        "⏳ Winner found."

    )


    time.sleep(
        CARD_BUYING_SECONDS
    )


    with bingo_lock:

        if bingo_game[
            "winner_user_id"
        ] is None:

            return


        print(

            "🔄 STARTING NEW GAME..."

        )


    start_new_game()


# =========================================================
# RESET
# =========================================================

@web_app.route(
    "/api/reset",
    methods=["POST"]
)
def reset_game():

    with bingo_lock:

        bingo_game[
            "started"
        ] = False

        bingo_game[
            "card_buying"
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
            "winner_card_number"
        ] = None

        bingo_game[
            "prize"
        ] = 0


    return jsonify({

        "success":
        True

    })


# =========================================================
# FLASK
# =========================================================

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


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    print(

        "ERROR:",

        context.error

    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        raise ValueError(

            "BOT_TOKEN is missing."

        )


    load_data()


    normalize_card_data()


    save_data()


    threading.Thread(

        target=run_flask,

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

            &

            ~filters.COMMAND,

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
