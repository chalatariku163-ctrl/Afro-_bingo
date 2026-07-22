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
NUMBER_CALL_SECONDS = 5

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

    global cards_10

    global cards_20


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


def get_user_game_cards(
    user_id,
    game_id
):

    result = []


    for card in get_user_cards(
        user_id
    ):

        data = get_card_data(

            card[
                "card_type"
            ],

            card[
                "card_number"
            ]

        )


        if data and game_id in data.get(
            "paid_games",
            []
        ):

            result.append(
                card
            )


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
# GAME START
# =========================================================

def create_new_game():

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


        game_id = bingo_game[
            "game_id"
        ]


    print(
        f"🎮 GAME {game_id} CREATED"
    )


    threading.Thread(

        target=card_buying_timer,

        args=(game_id,),

        daemon=True

    ).start()


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


    print(
        f"🎮 GAME {game_id} STARTED"
    )


    threading.Thread(

        target=automatic_number_caller,

        args=(game_id,),

        daemon=True

    ).start()


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
# BINGO WINNER
# =========================================================

def register_winner(

    user_id,

    card_type,

    card_number

):

    with bingo_lock:

        if not bingo_game[
            "started"
        ]:

            return False, "Game is not running."


        if bingo_game[
            "winner"
        ]:

            return False, "Winner already found."


        game_id = bingo_game[
            "game_id"
        ]

        called_numbers = bingo_game[
            "called_numbers"
        ]


    card = generate_card(
        card_number
    )


    if not check_bingo(

        card,

        called_numbers

    ):

        return False, "Bingo is not complete."


    with bingo_lock:

        if bingo_game[
            "winner"
        ]:

            return False, "Winner already found."


        total_sales = bingo_game[
            "total_sales"
        ]


        prize = (

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

            "prize":
            prize,

            "time":
            time.time(),

        })


        save_data()


    return True, prize


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

            "⏳ <b>CARD BUYING IS CLOSED</b>\n\n"

            "Wait for the next game.",

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

        "🟢 Paid for this game\n\n"

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

            "✅ Already paid for this game.",

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

        "✅ Card paid for this game!",

        show_alert=True

    )


    await query.edit_message_text(

        f"✅ <b>Card {card_number} READY!</b>\n\n"

        f"🎮 Game: <b>{game_id}</b>\n"

        f"💰 Paid: {price} Birr\n"

        f"💳 Balance: {get_balance(user_id)} Birr\n\n"

        "🎮 Game will start automatically after card buying time.",

        parse_mode="HTML",

        reply_markup=

        main_menu(
            user_id
        )# =========================================================
# BALANCE
# =========================================================

async def show_balance(query, user_id):

    balance = get_balance(user_id)

    await query.edit_message_text(

        "💳 <b>YOUR BALANCE</b>\n\n"
        f"💰 Balance: <b>{balance} Birr</b>",

        parse_mode="HTML",

        reply_markup=main_menu(user_id)

    )


# =========================================================
# MY CARDS
# =========================================================

async def show_my_cards(query, user_id):

    cards = get_user_cards(user_id)

    if not cards:

        await query.edit_message_text(

            "🎫 <b>MY CARDS</b>\n\n"
            "You do not own any card yet.",

            parse_mode="HTML",

            reply_markup=main_menu(user_id)

        )

        return


    text = "🎫 <b>MY CARDS</b>\n\n"

    for card in cards:

        card_type = card["card_type"]

        card_number = card["card_number"]

        text += (

            f"🎫 Card: <b>{card_number}</b>\n"
            f"💰 Type: {card_type} Birr\n\n"

        )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu(user_id)

    )


# =========================================================
# HISTORY
# =========================================================

async def show_history(query, user_id):

    user_transactions = [

        transaction

        for transaction in transactions

        if transaction["user_id"] == user_id

    ]


    if not user_transactions:

        await query.edit_message_text(

            "📜 <b>HISTORY</b>\n\n"
            "No transaction history.",

            parse_mode="HTML",

            reply_markup=main_menu(user_id)

        )

        return


    text = "📜 <b>TRANSACTION HISTORY</b>\n\n"


    for transaction in user_transactions[-15:]:

        transaction_type = transaction["type"]

        amount = transaction["amount"]

        status = transaction["status"]


        text += (

            f"🔹 {transaction_type}\n"
            f"💰 {amount} Birr\n"
            f"📌 {status}\n\n"

        )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu(user_id)

    )


# =========================================================
# WINNERS
# =========================================================

async def show_winners(query, user_id):

    if not winners:

        await query.edit_message_text(

            "🏆 <b>WINNERS</b>\n\n"
            "No winners yet.",

            parse_mode="HTML",

            reply_markup=main_menu(user_id)

        )

        return


    text = "🏆 <b>RECENT WINNERS</b>\n\n"


    recent_winners = winners[-20:]


    for winner in reversed(recent_winners):

        text += (

            f"🏆 Game: {winner.get('game_id')}\n"
            f"👤 User: {winner.get('user_id')}\n"
            f"🎫 Card: {winner.get('card_number')}\n"
            f"💰 Prize: {winner.get('prize')} Birr\n\n"

        )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu(user_id)

    )


# =========================================================
# HOW TO PLAY
# =========================================================

async def how_to_play(query):

    text = (

        "ℹ️ <b>HOW TO PLAY GADAA BINGO</b>\n\n"

        "1️⃣ Deposit money.\n\n"

        "2️⃣ Buy a Bingo card.\n\n"

        "3️⃣ Wait until the game starts.\n\n"

        "4️⃣ The system calls numbers automatically every 5 seconds.\n\n"

        "5️⃣ Mark the called numbers on your card.\n\n"

        "6️⃣ Complete one of these patterns:\n\n"

        "➖ Horizontal line\n"
        "│ Vertical line\n"
        "↘ Diagonal\n"
        "↙ Diagonal\n"
        "⏺ Four corners\n\n"

        "7️⃣ Press Bingo when you complete the pattern.\n\n"

        "🏆 The first valid Bingo wins.\n\n"

        "💰 Prize = 70% of total card sales."

    )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu()

    )


# =========================================================
# WITHDRAWAL START
# =========================================================

async def withdrawal_start(query, user_id):

    balance = get_balance(user_id)


    if balance <= 0:

        await query.edit_message_text(

            "💸 <b>WITHDRAWAL</b>\n\n"
            "⚠️ Your balance is empty.",

            parse_mode="HTML",

            reply_markup=main_menu(user_id)

        )

        return


    context_data = {

        "waiting_withdrawal":

        True

    }


    pending_withdrawals[user_id] = {

        "status":
        "waiting_info"

    }


    await query.edit_message_text(

        "💸 <b>WITHDRAWAL</b>\n\n"

        f"💰 Available balance: {balance} Birr\n\n"

        "📱 Send your Telebirr number and amount.\n\n"

        "Example:\n"

        "<code>0912345678 100</code>",

        parse_mode="HTML",

        reply_markup=main_menu(user_id)

    )


# =========================================================
# PROCESS WITHDRAWAL
# =========================================================

async def process_withdrawal(update, context):

    user_id = update.effective_user.id


    if user_id not in pending_withdrawals:

        return False


    withdrawal = pending_withdrawals[user_id]


    if withdrawal.get("status") != "waiting_info":

        return False


    text = update.message.text.strip()

    parts = text.split()


    if len(parts) != 2:

        await update.message.reply_text(

            "⚠️ Sirri miti.\n\n"

            "Fakkeenya:\n"

            "<code>0912345678 100</code>",

            parse_mode="HTML"

        )

        return True


    phone = parts[0]


    try:

        amount = float(parts[1])

    except ValueError:

        await update.message.reply_text(

            "⚠️ Amount sirrii galchi."

        )

        return True


    if amount <= 0:

        await update.message.reply_text(

            "⚠️ Amount sirrii galchi."

        )

        return True


    if get_balance(user_id) < amount:

        await update.message.reply_text(

            "⚠️ Balance gahaa miti."

        )

        del pending_withdrawals[user_id]

        return True


    pending_withdrawals[user_id] = {

        "status":
        "pending_admin",

        "phone":
        phone,

        "amount":
        amount

    }


    await update.message.reply_text(

        "✅ <b>Withdrawal request received!</b>\n\n"

        f"📱 Number: {phone}\n"
        f"💰 Amount: {amount} Birr\n\n"

        "⏳ Admin approval eeggataa jira.",

        parse_mode="HTML",

        reply_markup=main_menu(user_id)

    )


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

            )

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


    return True


# =========================================================
# APPROVE WITHDRAWAL
# =========================================================

async def approve_withdrawal(query, user_id):

    if query.from_user.id != ADMIN_ID:

        await query.answer(

            "⛔ Admin only.",

            show_alert=True

        )

        return


    withdrawal = pending_withdrawals.get(user_id)


    if not withdrawal:

        await query.answer(

            "Withdrawal not found.",

            show_alert=True

        )

        return


    amount = withdrawal["amount"]

    phone = withdrawal["phone"]


    if not remove_balance(user_id, amount):

        await query.answer(

            "Balance is not enough.",

            show_alert=True

        )

        return


    add_transaction(

        user_id,

        "withdrawal",

        amount,

        "approved",

        phone

    )


    del pending_withdrawals[user_id]


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

            f"💳 Remaining balance: "
            f"{get_balance(user_id)} Birr"

        ),

        parse_mode="HTML",

        reply_markup=main_menu(user_id)

    )


# =========================================================
# REJECT WITHDRAWAL
# =========================================================

async def reject_withdrawal(query, user_id):

    if query.from_user.id != ADMIN_ID:

        return


    withdrawal = pending_withdrawals.get(user_id)


    if not withdrawal:

        return


    del pending_withdrawals[user_id]


    await query.edit_message_text(

        "❌ <b>WITHDRAWAL REJECTED</b>\n\n"

        f"User ID: {user_id}",

        parse_mode="HTML"

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "❌ <b>Withdrawal rejected.</b>\n\n"

            "Your balance has not been removed."

        ),

        parse_mode="HTML",

        reply_markup=main_menu(user_id)

    )


# =========================================================
# ADMIN OPEN GAME
# =========================================================

async def admin_open_game(query):

    if query.from_user.id != ADMIN_ID:

        await query.answer(

            "⛔ Admin only.",

            show_alert=True

        )

        return


    with bingo_lock:

        if bingo_game["started"]:

            await query.answer(

                "Game already started.",

                show_alert=True

            )

            return


        bingo_game["game_id"] += 1

        bingo_game["started"] = False

        bingo_game["card_buying"] = True

        bingo_game["card_buying_end_time"] = (

            time.time()

            + CARD_BUYING_SECONDS

        )

        bingo_game["called_numbers"] = []

        bingo_game["current_number"] = None

        bingo_game["players"] = {}

        bingo_game["winner"] = None

        bingo_game["winner_user_id"] = None

        bingo_game["winner_card_number"] = None

        bingo_game["prize"] = 0

        bingo_game["total_sales"] = 0


    await query.edit_message_text(

        "🔓 <b>GAME OPENED</b>\n\n"

        f"🎮 Game ID: {bingo_game['game_id']}\n\n"

        "🎫 Card buying is open for 40 seconds.\n\n"

        "⏱️ Game will start automatically.",

        parse_mode="HTML",

        reply_markup=main_menu(ADMIN_ID)

    )


    threading.Thread(

        target=card_buying_timer,

        daemon=True

    ).start()


# =========================================================
# 40 SECOND CARD BUYING TIMER
# =========================================================

def card_buying_timer():

    time.sleep(CARD_BUYING_SECONDS)


    with bingo_lock:

        if not bingo_game["card_buying"]:

            return


        bingo_game["card_buying"] = False

        bingo_game["started"] = True


    print(

        f"🎮 GAME {bingo_game['game_id']} STARTED"

    )


    threading.Thread(

        target=automatic_number_caller,

        daemon=True

    ).start()


# =========================================================
# AUTOMATIC NUMBER CALLER
# EVERY 5 SECONDS
# =========================================================

def automatic_number_caller():

    while True:

        time.sleep(5)


        with bingo_lock:

            if not bingo_game["started"]:

                break


            if bingo_game["winner"]:

                break


            if len(

                bingo_game["called_numbers"]

            ) >= 75:

                bingo_game["started"] = False

                break


            available = [

                number

                for number in range(1, 76)

                if number not in

                bingo_game["called_numbers"]

            ]


            if not available:

                break


            number = random.choice(available)


            bingo_game["called_numbers"].append(number)

            bingo_game["current_number"] = number


        print(

            f"📢 CALLED: {number}"

        )


# =========================================================
# ADMIN CLOSE GAME
# =========================================================

async def admin_close_game(query):

    if query.from_user.id != ADMIN_ID:

        await query.answer(

            "⛔ Admin only.",

            show_alert=True

        )

        return


    with bingo_lock:

        bingo_game["card_buying"] = False

        bingo_game["started"] = False


    await query.edit_message_text(

        "🔒 <b>GAME CLOSED</b>\n\n"

        "The current game has been closed.",

        parse_mode="HTML",

        reply_markup=main_menu(ADMIN_ID)

    )


# =========================================================
# BINGO VALIDATION API
# =========================================================

@web_app.route(

    "/api/check-bingo",

    methods=["POST"]

)

def check_bingo_api():

    data = request.get_json(

        silent=True

    ) or {}


    user_id = data.get("user_id")

    card_number = data.get("card_number")

    card_type = data.get("card_type")


    if not user_id or not card_number or not card_type:

        return jsonify({

            "success": False,

            "message": "Missing data."

        }), 400


    try:

        user_id = int(user_id)

        card_number = int(card_number)

    except ValueError:

        return jsonify({

            "success": False,

            "message": "Invalid data."

        }), 400


    with bingo_lock:

        game_id = bingo_game["game_id"]

        called_numbers = list(

            bingo_game["called_numbers"]

        )

        started = bingo_game["started"]

        winner = bingo_game["winner"]


    if not started:

        return jsonify({

            "success": False,

            "message": "Game is not running."

        }), 400


    if winner:

        return jsonify({

            "success": False,

            "message": "Winner already found."

        }), 400


    owner = get_card_owner(

        card_type,

        card_number

    )


    if owner != user_id:

        return jsonify({

            "success": False,

            "message": "This card does not belong to you."

        }), 403


    if not card_was_paid_for_game(

        card_type,

        card_number,

        game_id

    ):

        return jsonify({

            "success": False,

            "message": "Card not paid for this game."

        }), 403


    card = generate_card(card_number)


    if not check_bingo(

        card,

        called_numbers

    ):

        return jsonify({

            "success": False,

            "message": "Bingo is not complete."

        }), 400


    with bingo_lock:

        if bingo_game["winner"]:

            return jsonify({

                "success": False,

                "message": "Another player won first."

            }), 400


        bingo_game["winner"] = True

        bingo_game["winner_user_id"] = user_id

        bingo_game["winner_card_number"] = card_number

        bingo_game["started"] = False


        total_sales = bingo_game["total_sales"]

        prize = int(

            total_sales

            * PRIZE_PERCENT

            / 100

        )


        bingo_game["prize"] = prize


    winners.append({

        "game_id": game_id,

        "user_id": user_id,

        "card_number": card_number,

        "prize": prize,

        "time": time.time()

    })


    if prize > 0:

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

        "success": True,

        "message": "BINGO! You won!",

        "game_id": game_id,

        "prize": prize

    })


# =========================================================
# FIX GAME API
# =========================================================

@web_app.route(

    "/api/game-state",

    methods=["GET"]

)

def game_state_compatibility():

    with bingo_lock:

        return jsonify({

            "success": True,

            "game_id":

            bingo_game["game_id"],

            "started":

            bingo_game["started"],

            "card_buying":

            bingo_game["card_buying"],

            "card_buying_end_time":

            bingo_game["card_buying_end_time"],

            "called_numbers":

            bingo_game["called_numbers"],

            "current_number":

            bingo_game["current_number"],

            "players":

            len(bingo_game["players"]),

            "stake":

            10,

            "derash":

            bingo_game["total_sales"],

            "winner":

            bingo_game["winner"],

            "winner_user_id":

            bingo_game["winner_user_id"],

            "winner_card_number":

            bingo_game["winner_card_number"],

            "prize":

            bingo_game["prize"]

        })


# =========================================================
# ADMIN CALL NUMBER MANUALLY
# =========================================================

@web_app.route(

    "/api/admin/call-number",

    methods=["POST"]

)

def admin_call_number():

    data = request.get_json(

        silent=True

    ) or {}


    admin_id = str(

        data.get("admin_id")

    )


    if admin_id != str(ADMIN_ID):

        return jsonify({

            "success": False,

            "message": "Admin only."

        }), 403


    with bingo_lock:

        if not bingo_game["started"]:

            return jsonify({

                "success": False,

                "message": "Game is not started."

            }), 400


        available = [

            number

            for number in range(1, 76)

            if number not in

            bingo_game["called_numbers"]

        ]


        if not available:

            return jsonify({

                "success": False,

                "message": "All numbers called."

            }), 400


        number = random.choice(available)


        bingo_game["called_numbers"].append(number)

        bingo_game["current_number"] = number


        return jsonify({

            "success": True,

            "number": number,

            "called_numbers":

            bingo_game["called_numbers"]

        })


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

)
