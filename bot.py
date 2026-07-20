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
# GAME DATA
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
            minimum +
            rnd *
            (
                maximum -
                minimum +
                1
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
# BINGO VALIDATION
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
# USER FUNCTIONS
# ==================================================

def is_registered(user_id):

    return user_id in users


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
# REGISTER BUTTON
# ==================================================

def register_keyboard():

    keyboard = [

        [

            KeyboardButton(
                "📱 Register",
                request_contact=True
            )

        ]

    ]

    return ReplyKeyboardMarkup(

        keyboard,

        resize_keyboard=True,

        one_time_keyboard=True

    )


# ==================================================
# /START
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    user_id = user.id

    if is_registered(user_id):

        await update.message.reply_text(

            "🏠 <b>GADAA BINGO</b>\n\n"
            "Welcome back! 👋\n\n"
            "👇 Choose an option:",

            parse_mode="HTML",

            reply_markup=main_menu()

        )

        return

    await update.message.reply_text(

        "🎉 <b>WELCOME TO GADAA BINGO!</b> 🎉\n\n"
        "👋 Welcome!\n\n"
        "📱 To use Gadaa Bingo, please register "
        "by sending your phone number.",

        parse_mode="HTML",

        reply_markup=register_keyboard()

    )


# ==================================================
# CONTACT / REGISTRATION
# ==================================================

async def receive_contact(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    contact = update.message.contact

    user = update.effective_user

    user_id = user.id

    if contact.user_id != user_id:

        await update.message.reply_text(

            "⚠️ Please use the Register button "
            "to send your own phone number."

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

        "✅ <b>REGISTRATION SUCCESSFUL!</b> 🎉\n\n"
        "Welcome to Gadaa Bingo, "
        f"{user.first_name}!\n\n"
        "👇 Choose an option below:",

        parse_mode="HTML",

        reply_markup=ReplyKeyboardRemove()

    )

    await update.message.reply_text(

        "🏠 <b>MAIN MENU</b>",

        parse_mode="HTML",

        reply_markup=main_menu()

    )


# ==================================================
# BUY CARD MENU
# ==================================================

async def buy_card_menu(
    query
):

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


# ==================================================
# CARD NUMBER MENU
# ==================================================

async def card_number_menu(

    query,

    card_type

):

    if not card_buying_open:

        await query.edit_message_text(

            "🔒 <b>CARD BUYING IS CLOSED</b>\n\n"
            "🎮 The Bingo game is starting.",

            parse_mode="HTML",

            reply_markup=main_menu()

        )

        return

    keyboard = []

    row = []

    owned_cards = (

        cards_10
        if card_type == "10"
        else cards_20

    )

    for number in range(1, 501):

        if number in owned_cards:

            button_text = f"⚫ {number}"

        else:

            button_text = f"🔴 {number}"

        row.append(

            InlineKeyboardButton(

                button_text,

                callback_data=f"select_{card_type}_{number}"

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
        "⚫ Already owned\n\n"
        "Choose card number:",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(keyboard)

    )


# ==================================================
# CARD PURCHASE
# ==================================================

async def select_card(

    query,

    user_id,

    card_type,

    card_number

):

    global cards_10

    global cards_20

    global card_buying_open

    global game_open

    price = (

        CARD_10_PRICE
        if card_type == "10"
        else CARD_20_PRICE

    )

    card_number = int(card_number)

    owned_cards = (

        cards_10
        if card_type == "10"
        else cards_20

    )

    if not card_buying_open:

        await query.answer(

            "🔒 Card buying time has ended.",

            show_alert=True

        )

        return

    if card_number in owned_cards:

        await query.answer(

            "⚠️ This card is already owned.",

            show_alert=True

        )

        return

    if get_balance(user_id) < price:

        await query.answer(

            "⚠️ Insufficient balance. Please Deposit first.",

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

        f"✅ Card {card_number} purchased!",

        show_alert=True

    )

    await query.edit_message_text(

        f"✅ <b>Card {card_number} purchased!</b>\n\n"
        f"💳 Price: {price} Birr\n"
        f"💰 Balance: {get_balance(user_id)} Birr\n\n"
        "🎫 You can continue buying more cards.",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup([

            [

                InlineKeyboardButton(

                    "🎫 Buy Another Card",

                    callback_data=f"cards_{card_type}"

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
# BALANCE
# ==================================================

async def show_balance(query, user_id):

    await query.edit_message_text(

        "💳 <b>YOUR BALANCE</b>\n\n"
        f"💰 Balance: <b>{get_balance(user_id)} Birr</b>",

        parse_mode="HTML",

        reply_markup=main_menu()

    )


# ==================================================
# MY CARDS
# ==================================================

async def show_my_cards(query, user_id):

    user_cards_10 = [

        number

        for number, owner in cards_10.items()

        if owner == user_id

    ]

    user_cards_20 = [

        number

        for number, owner in cards_20.items()

        if owner == user_id

    ]

    text = (

        "🧾 <b>MY CARDS</b>\n\n"

        "🎫 <b>10 Birr Cards:</b>\n"

        + (

            ", ".join(

                str(number)

                for number in user_cards_10

            )

            if user_cards_10

            else "None"

        )

        + "\n\n🎫 <b>20 Birr Cards:</b>\n"

        + (

            ", ".join(

                str(number)

                for number in user_cards_20

            )

            if user_cards_20

            else "None"

        )

    )

    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu()

    )


# ==================================================
# DEPOSIT MENU
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

                callback_data=f"deposit_{amount}"

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
        "Choose deposit amount:",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(keyboard)

    )


# ==================================================
# DEPOSIT REQUEST
# ==================================================

async def create_deposit(

    query,

    user_id,

    amount,

    context

):

    pending_deposits[user_id] = {

        "amount": amount,

        "status": "waiting_screenshot",

    }

    await query.edit_message_text(

        f"💰 <b>Deposit: {amount} Birr</b>\n\n"

        "📱 Please pay using Telebirr.\n\n"

        "📸 After payment, send your payment screenshot here.\n\n"

        "⏳ Waiting for screenshot...",

        parse_mode="HTML"

    )


# ==================================================
# PHOTO / DEPOSIT SCREENSHOT
# ==================================================

async def receive_photo(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):

    user_id = update.effective_user.id

    if user_id not in pending_deposits:

        await update.message.reply_text(

            "⚠️ No pending deposit found.",

            reply_markup=main_menu()

        )

        return

    deposit = pending_deposits[user_id]

    if deposit["status"] != "waiting_screenshot":

        return

    pending_deposits[user_id] = {

        "amount": deposit["amount"],

        "status": "pending_admin",

        "photo_id": update.message.photo[-1].file_id,

    }

    await update.message.reply_text(

        "✅ <b>Payment proof received!</b>\n\n"
        "⏳ Waiting for admin approval.",

        parse_mode="HTML"

    )

    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ Approve",

                callback_data=f"approve_deposit_{user_id}"

            ),

            InlineKeyboardButton(

                "❌ Reject",

                callback_data=f"reject_deposit_{user_id}"

            ),

        ]

    ])

    await context.bot.send_photo(

        chat_id=ADMIN_ID,

        photo=update.message.photo[-1].file_id,

        caption=(

            "💰 <b>NEW DEPOSIT REQUEST</b>\n\n"

            f"👤 User ID: {user_id}\n"

            f"💵 Amount: {deposit['amount']} Birr"

        ),

        parse_mode="HTML",

        reply_markup=keyboard

    )


# ==================================================
# ADMIN DEPOSIT APPROVAL
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

    deposit = pending_deposits.get(user_id)

    if not deposit:

        await query.answer(

            "⚠️ Deposit not found.",

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

            f"👤 User ID: {user_id}\n"

            f"💰 Amount: {amount} Birr"

        ),

        parse_mode="HTML"

    )

    await query.answer("Approved")

    try:

        await query.get_bot().send_message(

            chat_id=user_id,

            text=(

                "✅ <b>Deposit Approved!</b>\n\n"

                f"💰 Added: {amount} Birr\n"

                f"💳 New Balance: {get_balance(user_id)} Birr"

            ),

            parse_mode="HTML",

            reply_markup=main_menu()

        )

    except Exception:

        pass


async def reject_deposit(

    query,

    user_id

):

    if query.from_user.id != ADMIN_ID:

        await query.answer(

            "⛔ Admin only.",

            show_alert=True

        )

        return

    if user_id not in pending_deposits:

        await query.answer(

            "⚠️ Deposit not found.",

            show_alert=True

        )

        return

    del pending_deposits[user_id]

    await query.edit_message_caption(

        caption=(

            "❌ <b>DEPOSIT REJECTED</b>\n\n"

            f"👤 User ID: {user_id}"

        ),

        parse_mode="HTML"

    )

    await query.answer("Rejected")

    try:

        await query.get_bot().send_message(

            chat_id=user_id,

            text=(

                "❌ <b>Deposit rejected.</b>\n\n"

                "Please contact support if you believe this is a mistake."

            ),

            parse_mode="HTML",

            reply_markup=main_menu()

        )

    except Exception:

        pass


# ==================================================
# WITHDRAWAL
# ==================================================

async def withdrawal_menu(

    query,

    user_id

):

    balance = get_balance(user_id)

    if balance <= 0:

        await query.edit_message_text(

            "💸 <b>WITHDRAWAL</b>\n\n"

            "⚠️ Your balance is not enough.",

            parse_mode="HTML",

            reply_markup=main_menu()

        )

        return

    context_user = query.from_user

    await query.edit_message_text(

        "💸 <b>WITHDRAWAL</b>\n\n"

        f"💰 Available Balance: {balance} Birr\n\n"

        "Please send the amount you want to withdraw.",

        parse_mode="HTML"

    )


# ==================================================
# HISTORY
# ==================================================

async def show_history(query, user_id):

    user_transactions = [

        transaction

        for transaction in transactions

        if transaction["user_id"] == user_id

    ]

    if not user_transactions:

        text = (

            "📜 <b>HISTORY</b>\n\n"

            "No transactions yet."

        )

    else:

        text = "📜 <b>HISTORY</b>\n\n"

        for transaction in user_transactions[-20:]:

            text += (

                f"• {transaction['type']} — "

                f"{transaction['amount']} Birr — "

                f"{transaction['status']}\n"

            )

    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu()

    )


# ==================================================
# WINNERS
# ==================================================

async def show_winners(query):

    if not winners:

        text = (

            "🏆 <b>WINNERS</b>\n\n"

            "No winners yet."

        )

    else:

        text = "🏆 <b>WINNERS</b>\n\n"

        for winner in winners[-20:]:

            text += (

                f"🏆 User: {winner['user_id']}\n"

                f"💰 Prize: {winner['prize']} Birr\n\n"

            )

    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu()

    )


# ==================================================
# HOW TO PLAY
# ==================================================

async def how_to_play(query):

    await query.edit_message_text(

        "ℹ️ <b>HOW TO PLAY</b>\n\n"

        "1️⃣ Deposit money.\n"

        "2️⃣ Buy a Bingo card.\n"

        "3️⃣ Wait until card buying ends.\n"

        "4️⃣ Bingo game starts.\n"

        "5️⃣ Match called numbers on your card.\n"

        "6️⃣ Complete a line and win! 🏆",

        parse_mode="HTML",

        reply_markup=main_menu()

    )


# ==================================================
# PLAY GAME
# ==================================================

async def play_game(query):

    if not game_open:

        await query.edit_message_text(

            "🔒 <b>GAME IS CLOSED</b>\n\n"

            "Please wait until the admin opens the game.",

            parse_mode="HTML",

            reply_markup=main_menu()

        )

        return

    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "🎮 OPEN BINGO GAME",

                web_app=WebAppInfo(url=BINGO_URL)

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

        "Click below to open the game:",

        parse_mode="HTML",

        reply_markup=keyboard

    )


# ==================================================
# ADMIN GAME CONTROL
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

        f"🎫 Card buying time: {CARD_BUYING_SECONDS} seconds."

    )

    threading.Thread(

        target=card_timer_thread,

        daemon=True

    ).start()


def card_timer_thread():

    global card_buying_open

    global game_open

    global bingo_game

    time.sleep(CARD_BUYING_SECONDS)

    card_buying_open = False

    bingo_game["started"] = True

    print("BINGO GAME STARTED")


async def close_game(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):

    global game_open

    global card_buying_open

    global bingo_game

    if update.effective_user.id != ADMIN_ID:

        return

    game_open = False

    card_buying_open = False

    bingo_game["started"] = False

    await update.message.reply_text(

        "🔒 Game closed."

    )


# ==================================================
# CALLBACK HANDLER
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

        return

    if data == "buy_card":

        await buy_card_menu(query)

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

    if data.startswith("select_"):

        parts = data.split("_")

        card_type = parts[1]

        card_number = parts[2]

        await select_card(

            query,

            user_id,

            card_type,

            card_number

        )

        return

    if data == "deposit":

        await deposit_menu(query)

        return

    if data.startswith("deposit_"):

        amount = int(

            data.split("_")[1]

        )

        await create_deposit(

            query,

            user_id,

            amount,

            context

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

        await withdrawal_menu(

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

        await show_winners(query)

        return

    if data == "how_to_play":

        await how_to_play(query)

        return

    if data == "play_game":

        await play_game(query)

        return

    if data.startswith("approve_deposit_"):

        target_user_id = int(

            data.split("_")[2]

        )

        await approve_deposit(

            query,

            target_user_id

        )

        return

    if data.startswith("reject_deposit_"):

        target_user_id = int(

            data.split("_")[2]

        )

        await reject_deposit(

            query,

            target_user_id

        )

        return


# ==================================================
# WITHDRAWAL MESSAGE
# ==================================================

async def withdrawal_message(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):

    user_id = update.effective_user.id

    text = update.message.text.strip()

    try:

        amount = int(text)

    except ValueError:

        return

    if amount <= 0:

        return

    if get_balance(user_id) < amount:

        await update.message.reply_text(

            "⚠️ Insufficient balance.",

            reply_markup=main_menu()

        )

        return

    remove_balance(

        user_id,

        amount

    )

    pending_withdrawals[user_id] = {

        "amount": amount,

        "status": "pending",

    }

    add_transaction(

        user_id,

        "withdrawal",

        amount,

        "pending"

    )

    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ Approve",

                callback_data=f"approve_withdrawal_{user_id}"

            ),

            InlineKeyboardButton(

                "❌ Reject",

                callback_data=f"reject_withdrawal_{user_id}"

            ),

        ]

    ])

    await update.message.reply_text(

        "✅ Withdrawal request sent to admin.\n"

        "⏳ Waiting for approval.",

        reply_markup=main_menu()

    )

    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(

            "💸 NEW WITHDRAWAL REQUEST\n\n"

            f"👤 User ID: {user_id}\n"

            f"💰 Amount: {amount} Birr"

        ),

        reply_markup=keyboard

    )


# ==================================================
# ADMIN WITHDRAWAL
# ==================================================

async def approve_withdrawal(

    query,

    user_id

):

    if query.from_user.id != ADMIN_ID:

        return

    withdrawal = pending_withdrawals.get(user_id)

    if not withdrawal:

        await query.answer(

            "Not found",

            show_alert=True

        )

        return

    del pending_withdrawals[user_id]

    await query.edit_message_text(

        f"✅ Withdrawal approved.\n\n"

        f"User ID: {user_id}\n"

        f"Amount: {withdrawal['amount']} Birr"

    )

    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "✅ Withdrawal approved!\n\n"

            f"💰 Amount: {withdrawal['amount']} Birr"

        ),

        reply_markup=main_menu()

    )


async def reject_withdrawal(

    query,

    user_id

):

    if query.from_user.id != ADMIN_ID:

        return

    withdrawal = pending_withdrawals.get(user_id)

    if not withdrawal:

        await query.answer(

            "Not found",

            show_alert=True

        )

        return

    add_balance(

        user_id,

        withdrawal["amount"]

    )

    del pending_withdrawals[user_id]

    await query.edit_message_text(

        f"❌ Withdrawal rejected.\n\n"

        f"User ID: {user_id}\n"

        f"Amount returned: {withdrawal['amount']} Birr"

    )

    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "❌ Withdrawal rejected.\n\n"

            f"💰 {withdrawal['amount']} Birr returned to your balance."

        ),

        reply_markup=main_menu()

    )


# ==================================================
# FLASK ROUTES
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


@web_app.route("/api/game")

def api_game():

    with bingo_lock:

        return jsonify({

            "started": bingo_game["started"],

            "called_numbers": bingo_game["called_numbers"],

            "current_number": bingo_game["current_number"],

            "winner": bingo_game["winner"],

        })


@web_app.route("/api/call", methods=["POST"])

def api_call():

    global bingo_game

    with bingo_lock:

        if not bingo_game["started"]:

            return jsonify({

                "error": "Game not started"

            }), 400

        available_numbers = [

            number

            for number in range(1, 76)

            if number not in bingo_game["called_numbers"]

        ]

        if not available_numbers:

            return jsonify({

                "error": "All numbers called"

            }), 400

        number = random.choice(

            available_numbers

        )

        bingo_game["called_numbers"].append(

            number

        )

        bingo_game["current_number"] = number

        return jsonify({

            "number": number,

            "called_numbers": bingo_game["called_numbers"],

        })


@web_app.route("/api/reset", methods=["POST"])

def api_reset():

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
# BOT ERROR HANDLER
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
# RUN FLASK
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

            filters.TEXT

            & ~filters.COMMAND,

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
