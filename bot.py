import os
import random
import threading
import time

from flask import Flask, jsonify, request

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

CARD_BUYING_SECONDS = 60


# ==================================================
# FLASK
# ==================================================

web_app = Flask(__name__)


# ==================================================
# DATA
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
# BINGO GAME
# ==================================================

bingo_game = {

    "started": False,

    "called_numbers": [],

    "current_number": None,

    "players": {},

    "winner": None,

}

bingo_lock = threading.Lock()


# ==================================================
# CARD GENERATOR
# ==================================================

def generate_card(card_number):

    seed = int(card_number)

    def seeded_random(minimum, maximum):

        nonlocal seed

        seed = (

            seed * 9301 + 49297

        ) % 233280

        rnd = seed / 233280

        return int(

            minimum

            + rnd *

            (

                maximum

                - minimum

                + 1

            )

        )

    def generate_column(minimum, maximum):

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

            if row == 2 and col == 2:

                row_data.append("FREE")

            else:

                row_data.append(

                    columns[col][row]

                )

        card.append(row_data)

    return card


# ==================================================
# BINGO CHECK
# ==================================================

def check_bingo(card, called_numbers):

    marked = []

    for row in card:

        marked_row = []

        for value in row:

            if value == "FREE":

                marked_row.append(True)

            else:

                marked_row.append(

                    value in called_numbers

                )

        marked.append(marked_row)

    for row in range(5):

        if all(marked[row]):

            return True

    for col in range(5):

        if all(

            marked[row][col]

            for row in range(5)

        ):

            return True

    if all(

        marked[i][i]

        for i in range(5)

    ):

        return True

    if all(

        marked[i][4 - i]

        for i in range(5)

    ):

        return True

    return False


# ==================================================
# BALANCE
# ==================================================

def get_balance(user_id):

    return balances.get(user_id, 0)


def add_balance(user_id, amount):

    balances[user_id] = (

        get_balance(user_id)

        + amount

    )


def remove_balance(user_id, amount):

    if get_balance(user_id) < amount:

        return False

    balances[user_id] -= amount

    return True


def add_transaction(

    user_id,

    transaction_type,

    amount,

    status="completed"

):

    transactions.append({

        "user_id": user_id,

        "type": transaction_type,

        "amount": amount,

        "status": status,

        "time": time.time(),

    })


# ==================================================
# MAIN MENU
# ==================================================

def main_menu():

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

    return InlineKeyboardMarkup(keyboard)


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

    if user_id in users:

        await update.message.reply_text(

            "🏠 <b>GADAA BINGO</b>\n\n"

            "Welcome back! 👋",

            parse_mode="HTML",

            reply_markup=main_menu()

        )

        return

    await update.message.reply_text(

        "🎉 <b>WELCOME TO GADAA BINGO!</b>\n\n"

        "📱 Register by sending your phone number.",

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

    balances.setdefault(user_id, 0)

    await update.message.reply_text(

        "✅ <b>REGISTRATION SUCCESSFUL!</b>\n\n"

        "Welcome to Gadaa Bingo 🎉",

        parse_mode="HTML",

        reply_markup=ReplyKeyboardRemove()

    )

    await update.message.reply_text(

        "🏠 <b>MAIN MENU</b>",

        parse_mode="HTML",

        reply_markup=main_menu()

    )


# ==================================================
# BUY CARD
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

        reply_markup=InlineKeyboardMarkup(keyboard)

    )


async def card_number_menu(

    query,

    card_type

):

    if not card_buying_open:

        await query.edit_message_text(

            "🔒 <b>CARD BUYING CLOSED</b>\n\n"

            "⏳ Please wait for the next game.",

            parse_mode="HTML",

            reply_markup=main_menu()

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

            label = f"⚫ {number}"

        else:

            label = f"🔴 {number}"

        row.append(

            InlineKeyboardButton(

                label,

                callback_data=(

                    f"select_{card_type}_{number}"

                )

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

            callback_data="buy_card"

        )

    ])

    await query.edit_message_text(

        f"🎫 <b>{card_type} BIRR CARD</b>\n\n"

        "🔴 Available\n"

        "⚫ Already sold\n\n"

        "Choose your card:",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(keyboard)

    )


async def select_card(

    query,

    user_id,

    card_type,

    card_number

):

    card_number = int(card_number)

    price = (

        CARD_10_PRICE

        if card_type == "10"

        else CARD_20_PRICE

    )

    owned_cards = (

        cards_10

        if card_type == "10"

        else cards_20

    )

    if not card_buying_open:

        await query.answer(

            "⏳ Card buying time ended.",

            show_alert=True

        )

        return

    if card_number in owned_cards:

        await query.answer(

            "⚠️ Card already sold.",

            show_alert=True

        )

        return

    if get_balance(user_id) < price:

        await query.answer(

            "⚠️ Balance is not enough.",

            show_alert=True

        )

        return

    remove_balance(

        user_id,

        price

    )

    owned_cards[card_number] = user_id

    add_transaction(

        user_id,

        f"buy_card_{card_type}",

        price

    )

    await query.answer(

        "✅ Card purchased!",

        show_alert=True

    )

    await query.edit_message_text(

        f"✅ <b>Card {card_number} purchased!</b>\n\n"

        f"💰 Price: {price} Birr\n"

        f"💳 Balance: {get_balance(user_id)} Birr\n\n"

        "🎫 You can buy another card.",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup([

            [

                InlineKeyboardButton(

                    "🎫 Buy Another Card",

                    callback_data=(

                        f"cards_{card_type}"

                    )

                )

            ],

            [

                InlineKeyboardButton(

                    "🎮 Play Game",

                    callback_data="play_game"

                )

            ],

        ])

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

        1000,

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

            keyboard.append(row)

            row = []

    if row:

        keyboard.append(row)

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

        reply_markup=InlineKeyboardMarkup(keyboard)

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

        f"💰 <b>{amount} Birr Deposit</b>\n\n"

        "📱 Pay using Telebirr.\n\n"

        "📸 Then send payment screenshot here.",

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

            reply_markup=main_menu()

        )

        return

    deposit = pending_deposits[user_id]

    if deposit["status"] != "waiting_screenshot":

        return

    photo_id = update.message.photo[-1].file_id

    pending_deposits[user_id] = {

        "amount": deposit["amount"],

        "status": "pending_admin",

        "photo_id": photo_id,

    }

    await update.message.reply_text(

        "✅ Payment proof received.\n\n"

        "⏳ Waiting for admin approval.",

        reply_markup=main_menu()

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

            "💰 NEW DEPOSIT\n\n"

            f"👤 User ID: {user_id}\n"

            f"💵 Amount: {deposit['amount']} Birr"

        ),

        reply_markup=keyboard

    )


async def approve_deposit(

    query,

    user_id

):

    if query.from_user.id != ADMIN_ID:

        return

    deposit = pending_deposits.get(user_id)

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

            "✅ DEPOSIT APPROVED\n\n"

            f"👤 User ID: {user_id}\n"

            f"💰 Amount: {amount} Birr"

        )

    )

    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "✅ <b>Deposit Approved!</b>\n\n"

            f"💰 Added: {amount} Birr\n"

            f"💳 Balance: {get_balance(user_id)} Birr"

        ),

        parse_mode="HTML",

        reply_markup=main_menu()

    )


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

            "❌ DEPOSIT REJECTED\n\n"

            f"👤 User ID: {user_id}"

        )

    )

    await query.get_bot().send_message(

        chat_id=user_id,

        text="❌ Deposit rejected.",

        reply_markup=main_menu()

    )


# ==================================================
# BALANCE / CARDS / HISTORY
# ==================================================

async def show_balance(query, user_id):

    await query.edit_message_text(

        "💳 <b>BALANCE</b>\n\n"

        f"💰 {get_balance(user_id)} Birr",

        parse_mode="HTML",

        reply_markup=main_menu()

    )


async def show_my_cards(query, user_id):

    cards10 = [

        number

        for number, owner in cards_10.items()

        if owner == user_id

    ]

    cards20 = [

        number

        for number, owner in cards_20.items()

        if owner == user_id

    ]

    await query.edit_message_text(

        "🧾 <b>MY CARDS</b>\n\n"

        f"🎫 10 Birr: {cards10 or 'None'}\n\n"

        f"🎫 20 Birr: {cards20 or 'None'}",

        parse_mode="HTML",

        reply_markup=main_menu()

    )


async def show_history(query, user_id):

    history = [

        item

        for item in transactions

        if item["user_id"] == user_id

    ]

    text = "📜 <b>HISTORY</b>\n\n"

    if not history:

        text += "No transactions yet."

    else:

        for item in history[-20:]:

            text += (

                f"• {item['type']} — "

                f"{item['amount']} Birr — "

                f"{item['status']}\n"

            )

    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu()

    )


async def show_winners(query):

    text = "🏆 <b>WINNERS</b>\n\n"

    if not winners:

        text += "No winners yet."

    else:

        for winner in winners[-20:]:

            text += (

                f"🏆 {winner['user_id']} — "

                f"{winner['prize']} Birr\n"

            )

    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu()

    )


async def how_to_play(query):

    await query.edit_message_text(

        "ℹ️ <b>HOW TO PLAY</b>\n\n"

        "1️⃣ Register.\n"

        "2️⃣ Deposit.\n"

        "3️⃣ Buy Bingo Card.\n"

        "4️⃣ Wait until card buying ends.\n"

        "5️⃣ Open Play Game.\n"

        "6️⃣ Match the called numbers.\n"

        "7️⃣ Complete a line and press BINGO.",

        parse_mode="HTML",

        reply_markup=main_menu()

    )


# ==================================================
# PLAY GAME
# ==================================================

async def play_game(query):

    if not game_open:

        await query.edit_message_text(

            "🔒 <b>GAME CLOSED</b>",

            parse_mode="HTML",

            reply_markup=main_menu()

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

        "Click to open:",

        parse_mode="HTML",

        reply_markup=keyboard

    )


# ==================================================
# ADMIN GAME
# ==================================================

async def open_game(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):

    global game_open

    global card_buying_open

    global card_buying_end_time

    if update.effective_user.id != ADMIN_ID:

        return

    game_open = True

    card_buying_open = True

    card_buying_end_time = (

        time.time()

        + CARD_BUYING_SECONDS

    )

    await update.message.reply_text(

        "🎮 Game opened!\n\n"

        f"🎫 Card buying: "

        f"{CARD_BUYING_SECONDS} seconds."

    )

    threading.Thread(

        target=card_timer_thread,

        daemon=True

    ).start()


def card_timer_thread():

    global card_buying_open

    global bingo_game

    time.sleep(CARD_BUYING_SECONDS)

    card_buying_open = False

    with bingo_lock:

        bingo_game["started"] = True

    print("BINGO GAME STARTED")


async def close_game(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):

    global game_open

    global card_buying_open

    if update.effective_user.id != ADMIN_ID:

        return

    game_open = False

    card_buying_open = False

    with bingo_lock:

        bingo_game["started"] = False

    await update.message.reply_text(

        "🔒 Game closed."

    )


# ==================================================
# CALLBACKS
# ==================================================

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

            reply_markup=main_menu()

        )

    elif data == "buy_card":

        await buy_card_menu(query)

    elif data == "cards_10":

        await card_number_menu(query, "10")

    elif data == "cards_20":

        await card_number_menu(query, "20")

    elif data.startswith("select_"):

        parts = data.split("_")

        await select_card(

            query,

            user_id,

            parts[1],

            parts[2]

        )

    elif data == "deposit":

        await deposit_menu(query)

    elif data.startswith("deposit_"):

        amount = int(

            data.split("_")[1]

        )

        await create_deposit(

            query,

            user_id,

            amount

        )

    elif data == "balance":

        await show_balance(

            query,

            user_id

        )

    elif data == "my_cards":

        await show_my_cards(

            query,

            user_id

        )

    elif data == "history":

        await show_history(

            query,

            user_id

        )

    elif data == "winners":

        await show_winners(query)

    elif data == "how_to_play":

        await how_to_play(query)

    elif data == "play_game":

        await play_game(query)

    elif data.startswith("approve_deposit_"):

        target = int(

            data.split("_")[2]

        )

        await approve_deposit(

            query,

            target

        )

    elif data.startswith("reject_deposit_"):

        target = int(

            data.split("_")[2]

        )

        await reject_deposit(

            query,

            target

        )


# ==================================================
# WITHDRAWAL
# ==================================================

async def withdrawal_menu(

    query,

    user_id

):

    if get_balance(user_id) <= 0:

        await query.edit_message_text(

            "💸 Balance hin jiru.",

            reply_markup=main_menu()

        )

        return

    await query.edit_message_text(

        "💸 Withdrawal amount (Birr) barreessi.",

        reply_markup=main_menu()

    )


async def withdrawal_message(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):

    user_id = update.effective_user.id

    try:

        amount = int(

            update.message.text.strip()

        )

    except ValueError:

        return

    if get_balance(user_id) < amount:

        await update.message.reply_text(

            "⚠️ Balance gahaa miti.",

            reply_markup=main_menu()

        )

        return

    remove_balance(

        user_id,

        amount

    )

    pending_withdrawals[user_id] = {

        "amount": amount

    }

    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ Approve",

                callback_data=(

                    f"approve_withdrawal_{user_id}"

                )

            ),

            InlineKeyboardButton(

                "❌ Reject",

                callback_data=(

                    f"reject_withdrawal_{user_id}"

                )

            )

        ]

    ])

    await update.message.reply_text(

        "✅ Withdrawal request sent.",

        reply_markup=main_menu()

    )

    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(

            "💸 NEW WITHDRAWAL\n\n"

            f"User: {user_id}\n"

            f"Amount: {amount} Birr"

        ),

        reply_markup=keyboard

    )


# ==================================================
# FLASK API FOR INDEX.HTML
# ==================================================

@web_app.route("/")

def home():

    return jsonify({

        "status": "online",

        "service": "Gadaa Bingo",

        "game_open": game_open,

        "card_buying_open": card_buying_open,

        "bingo_started": bingo_game["started"],

    })


@web_app.route(

    "/api/join-game",

    methods=["POST"]

)

def join_game():

    data = request.get_json(

        silent=True

    ) or {}

    user_id = data.get("user_id")

    if not user_id:

        return jsonify({

            "success": False,

            "message": "User ID missing."

        }), 400

    try:

        user_id = int(user_id)

    except ValueError:

        return jsonify({

            "success": False,

            "message": "Invalid user ID."

        }), 400

    user_cards = [

        number

        for number, owner in cards_10.items()

        if owner == user_id

    ]

    user_cards += [

        number

        for number, owner in cards_20.items()

        if owner == user_id

    ]

    if not user_cards:

        return jsonify({

            "success": False,

            "message": "You have not bought a card."

        }), 403

    if not game_open:

        return jsonify({

            "success": False,

            "message": "Game is closed."

        }), 403

    card_number = user_cards[0]

    with bingo_lock:

        bingo_game["players"][str(user_id)] = {

            "card_number": card_number

        }

    return jsonify({

        "success": True,

        "card_number": card_number

    })


@web_app.route(

    "/api/game-state",

    methods=["GET"]

)

def game_state():

    with bingo_lock:

        return jsonify({

            "started": bingo_game["started"],

            "called_numbers": bingo_game["called_numbers"],

            "current_number": bingo_game["current_number"],

            "winner": bingo_game["winner"],

        })


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

                "message": "Game has not started."

            }), 400

        available = [

            number

            for number in range(1, 76)

            if number not in bingo_game["called_numbers"]

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

            "called_numbers": bingo_game["called_numbers"]

        })


@web_app.route(

    "/api/reset",

    methods=["POST"]

)

def reset_game():

    global bingo_game

    with bingo_lock:

        bingo_game = {

            "started": False,

            "called_numbers": [],

            "current_number": None,

            "players": {},

            "winner": None,

        }

    return jsonify({

        "success": True

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

            "BOT_TOKEN environment variable is missing."

        )

    threading.Thread(

        target=run_flask,

        daemon=True

    ).start()

    app = (

        Application

        .builder()

        .token(BOT_TOKEN)

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

            "open",

            open_game

        )

    )

    app.add_handler(

        CommandHandler(

            "close",

            close_game

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

            filters.TEXT & ~filters.COMMAND,

            withdrawal_message

        )

    )

    app.add_error_handler(

        error_handler

    )

    print(

        "GADAA BINGO BOT RUNNING..."

    )

    app.run_polling()


if __name__ == "__main__":

    main()
