import os
import random
import threading
import time
import json
from threading import Lock

from flask import Flask, jsonify, request

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
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

PORT = int(os.getenv("PORT", 10000))

CARD_10_PRICE = 10
CARD_20_PRICE = 20

PRIZE_PERCENT = 70

CARD_BUYING_SECONDS = 40
NUMBER_CALL_SECONDS = 5

DATA_FILE = "data.json"


# =========================================================
# FLASK
# =========================================================

web_app = Flask(__name__)


# =========================================================
# LOCK
# =========================================================

bingo_lock = Lock()


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

    "winner": False,

    "winner_user_id": None,

    "winner_card_number": None,

    "winner_card_type": None,

    "prize": 0,

    "total_sales": 0,

}


# =========================================================
# DATA
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
# SAVE DATA
# =========================================================

def save_data():

    data = {

        "users": users,

        "balances": balances,

        "transactions": transactions,

        "cards_10": cards_10,

        "cards_20": cards_20,

        "pending_deposits": pending_deposits,

        "pending_withdrawals": pending_withdrawals,

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


# =========================================================
# LOAD DATA
# =========================================================

def load_data():

    global users
    global balances
    global transactions
    global cards_10
    global cards_20
    global pending_deposits
    global pending_withdrawals
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


        pending_deposits = {

            int(k): v

            for k, v in data.get(
                "pending_deposits",
                {}
            ).items()

        }


        pending_withdrawals = {

            int(k): v

            for k, v in data.get(
                "pending_withdrawals",
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
# CARD FUNCTIONS
# =========================================================

def normalize_card_data():

    for cards in [

        cards_10,

        cards_20

    ]:

        for card_number in list(
            cards.keys()
        ):

            value = cards[
                card_number
            ]


            if isinstance(
                value,
                int
            ):

                cards[
                    card_number
                ] = {

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

                    cards[
                        card_number
                    ] = {

                        "owner":
                        int(value),

                        "used_games":
                        [],

                        "paid_games":
                        [],

                    }

                except Exception:

                    pass


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


def get_card_owner(

    card_type,

    card_number

):

    card = get_card_data(

        card_type,

        card_number

    )


    if not card:

        return None


    return card.get(
        "owner"
    )


def get_user_cards(
    user_id
):

    result = []


    for card_number in cards_10:

        if get_card_owner(
            "10",
            card_number
        ) == user_id:

            result.append({

                "card_number":
                int(card_number),

                "card_type":
                "10",

            })


    for card_number in cards_20:

        if get_card_owner(
            "20",
            card_number
        ) == user_id:

            result.append({

                "card_number":
                int(card_number),

                "card_type":
                "20",

            })


    return result


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


# =========================================================
# BINGO CARD GENERATOR
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

            if row == 2 and col == 2:

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


# =========================================================
# CHECK BINGO
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

                    value in called_numbers

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


# =========================================================
# REGISTER CONTACT
# =========================================================

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

        "🏠 <b>MAIN MENU</b>\n\n"

        "👇 Wanta barbaadde filadhu:",

        parse_mode="HTML",

        reply_markup=

        main_menu(
            user_id
        )

    )


# =========================================================
# DEPOSIT MENU
# =========================================================

async def deposit_menu(

    query,

    user_id

):

    amounts = [

        10,

        20,

        50,

        100,

        200,

        500,

        1000,

    ]


    keyboard = []


    for amount in amounts:

        keyboard.append([

            InlineKeyboardButton(

                f"💰 {amount} Birr",

                callback_data=

                f"deposit_amount_{amount}"

            )

        ])


    keyboard.append([

        InlineKeyboardButton(

            "🔙 Back",

            callback_data=
            "back_menu"

        )

    ])


    await query.edit_message_text(

        "💰 <b>DEPOSIT</b>\n\n"

        "Amount filadhu:",

        parse_mode="HTML",

        reply_markup=

        InlineKeyboardMarkup(
            keyboard
        )

    )


# =========================================================
# DEPOSIT AMOUNT
# =========================================================

async def deposit_amount(

    query,

    user_id,

    amount

):

    pending_deposits[user_id] = {

        "amount":
        amount,

        "status":
        "waiting_screenshot",

    }


    save_data()


    await query.edit_message_text(

        "💰 <b>DEPOSIT</b>\n\n"

        f"Amount: <b>{amount} Birr</b>\n\n"

        "1️⃣ Telebirr irratti kaffali.\n\n"

        "2️⃣ Screenshot ragaa kaffaltii asitti ergi.\n\n"

        "⏳ Admin approve godha.",

        parse_mode="HTML",

        reply_markup=

        main_menu(
            user_id
        )

    )


# =========================================================
# RECEIVE SCREENSHOT
# =========================================================

async def receive_deposit_photo(

    update,

    context

):

    user_id = update.effective_user.id


    if user_id not in pending_deposits:

        return


    deposit = pending_deposits[user_id]


    if deposit.get(
        "status"
    ) != "waiting_screenshot":

        return


    amount = deposit[
        "amount"
    ]


    photo = update.message.photo[-1]


    file = await context.bot.get_file(

        photo.file_id

    )


    pending_deposits[user_id] = {

        "amount":
        amount,

        "status":
        "pending_admin",

        "photo_id":
        photo.file_id,

    }


    save_data()


    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ APPROVE",

                callback_data=

                f"approve_deposit_{user_id}"

            ),

            InlineKeyboardButton(

                "❌ REJECT",

                callback_data=

                f"reject_deposit_{user_id}"

            ),

        ]

    ])


    await context.bot.send_photo(

        chat_id=ADMIN_ID,

        photo=photo.file_id,

        caption=(

            "💰 <b>NEW TELEBIRR DEPOSIT</b>\n\n"

            f"👤 User ID: {user_id}\n"

            f"💵 Amount: {amount} Birr\n\n"

            "Screenshot payment proof."

        ),

        parse_mode="HTML",

        reply_markup=keyboard

    )


    await update.message.reply_text(

        "✅ <b>Payment proof received!</b>\n\n"

        f"💰 Amount: {amount} Birr\n\n"

        "⏳ Admin approval eeggataa jira.",

        parse_mode="HTML",

        reply_markup=

        main_menu(
            user_id
        )

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


    if deposit.get(
        "status"
    ) != "pending_admin":

        await query.answer(

            "Already processed.",

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

        "approved",

        "Telebirr"

    )


    del pending_deposits[
        user_id
    ]


    save_data()


    await query.edit_message_caption(

        caption=(

            "✅ <b>DEPOSIT APPROVED</b>\n\n"

            f"👤 User ID: {user_id}\n"

            f"💰 Amount: {amount} Birr"

        ),

        parse_mode="HTML"

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "✅ <b>DEPOSIT APPROVED!</b>\n\n"

            f"💰 Added: {amount} Birr\n"

            f"💳 Balance: {get_balance(user_id)} Birr"

        ),

        parse_mode="HTML",

        reply_markup=

        main_menu(
            user_id
        )

    )


# =========================================================
# REJECT DEPOSIT
# =========================================================

async def reject_deposit(

    query,

    user_id

):

    if query.from_user.id != ADMIN_ID:

        return


    deposit = pending_deposits.get(
        user_id
    )


    if not deposit:

        return


    amount = deposit[
        "amount"
    ]


    del pending_deposits[
        user_id
    ]


    save_data()


    await query.edit_message_caption(

        caption=(

            "❌ <b>DEPOSIT REJECTED</b>\n\n"

            f"👤 User ID: {user_id}\n"

            f"💰 Amount: {amount} Birr"

        ),

        parse_mode="HTML"

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "❌ <b>DEPOSIT REJECTED</b>\n\n"

            "Payment proof admin irraa hin mirkanoofne."

        ),

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

        card_buying = bingo_game[
            "card_buying"
        ]

        game_id = bingo_game[
            "game_id"
        ]


    if not card_buying:

        await query.edit_message_text(

            "⏳ <b>CARD BUYING CLOSED</b>\n\n"

            "Wait for next game.",

            parse_mode="HTML",

            reply_markup=

            main_menu(
                user_id
            )

        )

        return


    keyboard = []

    row = []


    for number in range(

        1,

        501

    ):

        owner = get_card_owner(

            card_type,

            number

        )


        if owner is None:

            text = f"🔴 {number}"

        elif owner != user_id:

            text = f"⚫ {number}"

        else:

            card = get_card_data(

                card_type,

                number

            )


            if game_id in card.get(

                "paid_games",

                []

            ):

                text = f"🟢 {number}"

            else:

                text = f"🔵 {number}"


        row.append(

            InlineKeyboardButton(

                text,

                callback_data=

                f"select_{card_type}_{number}"

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

        "🔵 Your old card\n"

        "🟢 Paid this game\n\n"

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

        if not bingo_game[
            "card_buying"
        ]:

            await query.answer(

                "⏳ Card buying ended.",

                show_alert=True

            )

            return


        game_id = bingo_game[
            "game_id"
        ]


    owner = get_card_owner(

        card_type,

        card_number

    )


    if owner is not None and owner != user_id:

        await query.answer(

            "⚠️ Card owned by another user.",

            show_alert=True

        )

        return


    card = get_card_data(

        card_type,

        card_number

    )


    if card and game_id in card.get(

        "paid_games",

        []

    ):

        await query.answer(

            "✅ Already paid.",

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

            "⚠️ Balance insufficient.",

            show_alert=True

        )

        return


    owned_cards = (

        cards_10

        if card_type == "10"

        else cards_20

    )


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


    with bingo_lock:

        bingo_game[
            "total_sales"
        ] += price


    add_transaction(

        user_id,

        f"buy_card_{card_type}",

        price,

        "completed",

        f"Card {card_number} - Game {game_id}"

    )


    await query.answer(

        "✅ Card paid!",

        show_alert=True

    )


    await query.edit_message_text(

        f"✅ <b>CARD {card_number} READY!</b>\n\n"

        f"🎮 Game: <b>{game_id}</b>\n"

        f"💰 Paid: {price} Birr\n"

        f"💳 Balance: {get_balance(user_id)} Birr\n\n"

        "🎮 Game starts automatically.",

        parse_mode="HTML",

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

        f"💰 Balance: <b>{get_balance(user_id)} Birr</b>",

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

    cards = get_user_cards(
        user_id
    )


    if not cards:

        await query.edit_message_text(

            "🎫 <b>MY CARDS</b>\n\n"

            "You do not own any card.",

            parse_mode="HTML",

            reply_markup=

            main_menu(
                user_id
            )

        )

        return


    text = "🎫 <b>MY CARDS</b>\n\n"


    for card in cards:

        text += (

            f"🎫 Card: <b>{card['card_number']}</b>\n"

            f"💰 Type: {card['card_type']} Birr\n\n"

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
# HISTORY
# =========================================================

async def show_history(

    query,

    user_id

):

    user_transactions = [

        transaction

        for transaction in transactions

        if transaction.get(
            "user_id"
        ) == user_id

    ]


    if not user_transactions:

        await query.edit_message_text(

            "📜 <b>HISTORY</b>\n\n"

            "No transaction history.",

            parse_mode="HTML",

            reply_markup=

            main_menu(
                user_id
            )

        )

        return


    text = "📜 <b>HISTORY</b>\n\n"


    for transaction in user_transactions[-15:]:

        text += (

            f"🔹 {transaction['type']}\n"

            f"💰 {transaction['amount']} Birr\n"

            f"📌 {transaction['status']}\n\n"

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

        await query.edit_message_text(

            "🏆 <b>WINNERS</b>\n\n"

            "No winners yet.",

            parse_mode="HTML",

            reply_markup=

            main_menu(
                user_id
            )

        )

        return


    text = "🏆 <b>RECENT WINNERS</b>\n\n"


    for winner in reversed(
        winners[-20:]
    ):

        text += (

            f"🏆 Game: {winner['game_id']}\n"

            f"👤 User: {winner['user_id']}\n"

            f"🎫 Card: {winner['card_number']}\n"

            f"💰 Prize: {winner['prize']} Birr\n\n"

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

    text = (

        "ℹ️ <b>HOW TO PLAY GADAA BINGO</b>\n\n"

        "1️⃣ Deposit money.\n\n"

        "2️⃣ Buy Bingo card.\n\n"

        "3️⃣ Wait until game starts.\n\n"

        "4️⃣ Numbers are called automatically every 5 seconds.\n\n"

        "5️⃣ Mark called numbers.\n\n"

        "6️⃣ Complete one Bingo pattern.\n\n"

        "➖ Horizontal\n"

        "│ Vertical\n"

        "↘ Diagonal\n"

        "↙ Diagonal\n\n"

        "7️⃣ Press Bingo in the web app.\n\n"

        "🏆 First valid Bingo wins.\n\n"

        "💰 Prize = 70% of total card sales."

    )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=

        main_menu()

    )


# =========================================================
# WITHDRAWAL
# =========================================================

async def withdrawal_start(

    query,

    user_id

):

    balance = get_balance(
        user_id
    )


    if balance <= 0:

        await query.edit_message_text(

            "💸 <b>WITHDRAWAL</b>\n\n"

            "⚠️ Balance is empty.",

            parse_mode="HTML",

            reply_markup=

            main_menu(
                user_id
            )

        )

        return


    pending_withdrawals[user_id] = {

        "status":
        "waiting_info"

    }


    save_data()


    await query.edit_message_text(

        "💸 <b>WITHDRAWAL</b>\n\n"

        f"💰 Balance: {balance} Birr\n\n"

        "📱 Send Telebirr number and amount.\n\n"

        "Example:\n"

        "<code>0912345678 100</code>",

        parse_mode="HTML",

        reply_markup=

        main_menu(
            user_id
        )

    )


# =========================================================
# PROCESS WITHDRAWAL
# =========================================================

async def process_withdrawal(

    update,

    context

):

    user_id = update.effective_user.id


    if user_id not in pending_withdrawals:

        return False


    withdrawal = pending_withdrawals[
        user_id
    ]


    if withdrawal.get(
        "status"
    ) != "waiting_info":

        return False


    parts = update.message.text.strip().split()


    if len(parts) != 2:

        await update.message.reply_text(

            "⚠️ Sirrii miti.\n\n"

            "Fakkeenya:\n"

            "<code>0912345678 100</code>",

            parse_mode="HTML"

        )

        return True


    phone = parts[0]


    try:

        amount = float(
            parts[1]
        )

    except ValueError:

        await update.message.reply_text(

            "⚠️ Amount sirrii galchi."

        )

        return True


    if amount <= 0:

        return True


    if get_balance(
        user_id
    ) < amount:

        await update.message.reply_text(

            "⚠️ Balance gahaa miti."

        )

        del pending_withdrawals[
            user_id
        ]

        return True


    pending_withdrawals[user_id] = {

        "status":
        "pending_admin",

        "phone":
        phone,

        "amount":
        amount,

    }


    save_data()


    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ APPROVE",

                callback_data=

                f"approve_withdrawal_{user_id}"

            ),

            InlineKeyboardButton(

                "❌ REJECT",

                callback_data=

                f"reject_withdrawal_{user_id}"

            ),

        ]

    ])


    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(

            "💸 <b>NEW WITHDRAWAL</b>\n\n"

            f"👤 User ID: {user_id}\n"

            f"📱 Phone: {phone}\n"

            f"💰 Amount: {amount} Birr"

        ),

        parse_mode="HTML",

        reply_markup=keyboard

    )


    await update.message.reply_text(

        "✅ Withdrawal request received.\n\n"

        "⏳ Admin approval eeggataa jira.",

        reply_markup=

        main_menu(
            user_id
        )

    )


    return True


# =========================================================
# APPROVE WITHDRAWAL
# =========================================================

async def approve_withdrawal(

    query,

    user_id

):

    if query.from_user.id != ADMIN_ID:

        return


    withdrawal = pending_withdrawals.get(
        user_id
    )


    if not withdrawal:

        return


    amount = withdrawal[
        "amount"
    ]

    phone = withdrawal[
        "phone"
    ]


    if not remove_balance(

        user_id,

        amount

    ):

        return


    add_transaction(

        user_id,

        "withdrawal",

        amount,

        "approved",

        phone

    )


    del pending_withdrawals[
        user_id
    ]


    save_data()


    await query.edit_message_text(

        "✅ <b>WITHDRAWAL APPROVED</b>\n\n"

        f"👤 User: {user_id}\n"

        f"📱 Phone: {phone}\n"

        f"💰 Amount: {amount} Birr",

        parse_mode="HTML"

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "✅ <b>Withdrawal Approved!</b>\n\n"

            f"💰 Amount: {amount} Birr\n"

            f"📱 Telebirr: {phone}\n\n"

            f"💳 Remaining: {get_balance(user_id)} Birr"

        ),

        parse_mode="HTML",

        reply_markup=

        main_menu(
            user_id
        )

    )


# =========================================================
# REJECT WITHDRAWAL
# =========================================================

async def reject_withdrawal(

    query,

    user_id

):

    if query.from_user.id != ADMIN_ID:

        return


    if user_id not in pending_withdrawals:

        return


    del pending_withdrawals[
        user_id
    ]


    save_data()


    await query.edit_message_text(

        "❌ <b>WITHDRAWAL REJECTED</b>",

        parse_mode="HTML"

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "❌ Withdrawal rejected.\n\n"

            "Your balance has not been removed."

        ),

        reply_markup=

        main_menu(
            user_id
        )

    )


# =========================================================
# GAME START
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
            "winner"
        ] = False

        bingo_game[
            "winner_user_id"
        ] = None

        bingo_game[
            "winner_card_number"
        ] = None

        bingo_game[
            "winner_card_type"
        ] = None

        bingo_game[
            "prize"
        ] = 0

        bingo_game[
            "total_sales"
        ] = 0

        game_id = bingo_game[
            "game_id"
        ]


    threading.Thread(

        target=card_buying_timer,

        args=(game_id,),

        daemon=True

    ).start()


# =========================================================
# CARD BUYING TIMER
# =========================================================

def card_buying_timer(

    game_id

):

    time.sleep(
        CARD_BUYING_SECONDS
    )


    with bingo_lock:

        if bingo_game[
            "game_id"
        ] != game_id:

            return


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


    threading.Thread(

        target=automatic_number_caller,

        args=(game_id,),

        daemon=True

    ).start()


# =========================================================
# AUTOMATIC NUMBER CALLER
# =========================================================

def automatic_number_caller(

    game_id

):

    while True:

        time.sleep(
            NUMBER_CALL_SECONDS
        )


        with bingo_lock:

            if bingo_game[
                "game_id"
            ] != game_id:

                return


            if not bingo_game[
                "started"
            ]:

                return


            if bingo_game[
                "winner"
            ]:

                return


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

                bingo_game[
                    "started"
                ] = False

                return


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


        print(
            f"📢 CALLED: {number}"
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
            "card_buying"
        ] or bingo_game[
            "started"
        ]:

            await query.answer(

                "Game already running.",

                show_alert=True

            )

            return


    start_new_game()


    await query.edit_message_text(

        "🔓 <b>GAME OPENED</b>\n\n"

        f"🎮 Game ID: <b>{bingo_game['game_id']}</b>\n\n"

        "🎫 Card buying: 40 seconds\n"

        "🎮 Game starts automatically.",

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

        return


    with bingo_lock:

        bingo_game[
            "card_buying"
        ] = False

        bingo_game[
            "started"
        ] = False


    await query.edit_message_text(

        "🔒 <b>GAME CLOSED</b>",

        parse_mode="HTML",

        reply_markup=

        main_menu(
            ADMIN_ID
        )

    )


# =========================================================
# BINGO API
# =========================================================

@web_app.route(

    "/api/game-state",

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

            "total_sales":
            bingo_game[
                "total_sales"
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

            "prize":
            bingo_game[
                "prize"
            ],

        })


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

    card_number = data.get(
        "card_number"
    )

    card_type = data.get(
        "card_type"
    )


    if not user_id or not card_number or not card_type:

        return jsonify({

            "success":
            False,

            "message":
            "Missing data."

        }), 400


    try:

        user_id = int(
            user_id
        )

        card_number = int(
            card_number
        )

    except Exception:

        return jsonify({

            "success":
            False,

            "message":
            "Invalid data."

        }), 400


    with bingo_lock:

        game_id = bingo_game[
            "game_id"
        ]

        called_numbers = list(

            bingo_game[
                "called_numbers"
            ]

        )

        started = bingo_game[
            "started"
        ]

        winner = bingo_game[
            "winner"
        ]


    if not started:

        return jsonify({

            "success":
            False,

            "message":
            "Game is not running."

        }), 400


    if winner:

        return jsonify({

            "success":
            False,

            "message":
            "Winner already found."

        }), 400


    owner = get_card_owner(

        card_type,

        card_number

    )


    if owner != user_id:

        return jsonify({

            "success":
            False,

            "message":
            "Card does not belong to you."

        }), 403


    if not card_was_paid_for_game(

        card_type,

        card_number,

        game_id

    ):

        return jsonify({

            "success":
            False,

            "message":
            "Card not paid for this game."

        }), 403


    card = generate_card(
        card_number
    )


    if not check_bingo(

        card,

        called_numbers

    ):

        return jsonify({

            "success":
            False,

            "message":
            "Bingo is not complete."

        }), 400


    with bingo_lock:

        if bingo_game[
            "winner"
        ]:

            return jsonify({

                "success":
                False,

                "message":
                "Another player won first."

            }), 400


        total_sales = bingo_game[
            "total_sales"
        ]


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
        ] = card_number

        bingo_game[
            "winner_card_type"
        ] = card_type

        bingo_game[
            "prize"
        ] = prize

        bingo_game[
            "started"
        ] = False


    winners.append({

        "game_id":
        game_id,

        "user_id":
        user_id,

        "card_number":
        card_number,

        "card_type":
        card_type,

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


    return jsonify({

        "success":
        True,

        "message":
        "BINGO! You won!",

        "game_id":
        game_id,

        "prize":
        prize

    })


# =========================================================
# FLASK RUN
# =========================================================

def run_flask():

    web_app.run(

        host="0.0.0.0",

        port=PORT,

        debug=False,

        use_reloader=False

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


    if data == "deposit":

        await deposit_menu(

            query,

            user_id

        )

        return


    if data.startswith(
        "deposit_amount_"
    ):

        amount = int(

            data.replace(

                "deposit_amount_",

                ""

            )

        )


        await deposit_amount(

            query,

            user_id,

            amount

        )

        return


    if data == "withdrawal":

        await withdrawal_start(

            query,

            user_id

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

        target_user = int(

            data.split(
                "_"
            )[-1]

        )


        await approve_deposit(

            query,

            target_user

        )

        return


    if data.startswith(
        "reject_deposit_"
    ):

        target_user = int(

            data.split(
                "_"
            )[-1]

        )


        await reject_deposit(

            query,

            target_user

        )

        return


    if data.startswith(
        "approve_withdrawal_"
    ):

        target_user = int(

            data.split(
                "_"
            )[-1]

        )


        await approve_withdrawal(

            query,

            target_user

        )

        return


    if data.startswith(
        "reject_withdrawal_"
    ):

        target_user = int(

            data.split(
                "_"
            )[-1]

        )


        await reject_withdrawal(

            query,

            target_user

        )

        return


    if data == "play_game":

        await query.edit_message_text(

            "🎮 <b>PLAY GAME</b>\n\n"

            "Game web app irraa banuuf card kee filadhu.\n\n"

            "Game yeroo banamu, index.html irraa game state argatta.",

            parse_mode="HTML",

            reply_markup=

            main_menu(
                user_id
            )

        )

        return


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(

    update,

    context

):

    if await process_withdrawal(

        update,

        context

    ):

        return


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(

            "BOT_TOKEN environment variable is missing."

        )


    load_data()

    normalize_card_data()

    save_data()


    flask_thread = threading.Thread(

        target=run_flask,

        daemon=True

    )


    flask_thread.start()


    application = (

        Application

        .builder()

        .token(
            BOT_TOKEN
        )

        .build()

    )


    application.add_handler(

        CommandHandler(

            "start",

            start

        )

    )


    application.add_handler(

        MessageHandler(

            filters.CONTACT,

            receive_contact

        )

    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_deposit_photo
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    print("Bot started")

    port = int(
        os.getenv(
            "PORT",
            10000
        )
    )

    web_app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )


# =========================================================
# RUN BOT
# =========================================================

def run_bot():

    application = (

        Application.builder()

        .token(BOT_TOKEN)

        .build()

    )


    application.add_handler(

        CommandHandler(

            "start",

            start

        )

    )


    application.add_handler(

        MessageHandler(

            filters.CONTACT,

            receive_contact

        )

    )


    application.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            process_withdrawal

        )

    )


    application.add_handler(

        CallbackQueryHandler)
    

 "🤖 GADAA BINGO BOT STARTED"

    )


    application.run_polling()


# =========================================================
# MAIN
# =========================================================

def main():

    load_data()

    normalize_card_data()

    save_data()


    flask_thread = threading.Thread(

        target=run_flask,

        daemon=True

    )


    flask_thread.start()


    run_bot()


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
