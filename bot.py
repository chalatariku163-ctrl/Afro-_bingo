import os
import threading
from flask import Flask, render_template_string

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


# =========================
# SETTINGS
# =========================

ADMIN_ID = 6376605934

CARD_10_PRICE = 10
CARD_20_PRICE = 20

PRIZE_PERCENT = 70


# =========================
# FLASK WEB SERVER
# =========================

web_app = Flask(__name__)





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


@web_app.route("/")
def home():
    return render_template_string(open("index.html", encoding="utf-8").read())# =========================
# DATA
# =========================

balances = {}

transactions = []

pending_deposits = {}

pending_withdrawals = {}

cards_10 = {}

cards_20 = {}

game_open = True

game_cards_10 = {}

game_cards_20 = {}

winners = []


# =========================
# BALANCE FUNCTIONS
# =========================

def get_balance(user_id):

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

        get_balance(user_id)
        + amount

    )

    transactions.append(

        {

            "user_id": user_id,

            "type": transaction_type,

            "amount": amount

        }

    )


def remove_balance(
    user_id,
    amount,
    transaction_type="CARD BUY"
):

    if get_balance(user_id) < amount:

        return False


    balances[user_id] = (

        get_balance(user_id)
        - amount

    )

    transactions.append(

        {

            "user_id": user_id,

            "type": transaction_type,

            "amount": -amount

        }

    )

    return True


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

            ),

            InlineKeyboardButton(

                "💳 Balance",

                callback_data="balance"

            )

        ],

        [

            InlineKeyboardButton(

                "🎮 Play Game",

                callback_data="play_bingo"

            )

        ],

        [

            InlineKeyboardButton(

                "💸 Withdrawal",

                callback_data="withdrawal"

            )

        ],

        [

            InlineKeyboardButton(

                "🧾 My Cards",

                callback_data="my_cards"

            )

        ],

        [

            InlineKeyboardButton(

                "📜 History",

                callback_data="history"

            )

        ],

        [

            InlineKeyboardButton(

                "🏆 Winners",

                callback_data="winners"

            )

        ],

        [

            InlineKeyboardButton(

                "ℹ️ How to Play",

                callback_data="how_to_play"

            )

        ]

    ]

    return InlineKeyboardMarkup(keyboard)


def back_button():

    return InlineKeyboardMarkup(

        [

            [

                InlineKeyboardButton(

                    "🏠 Main Menu",

                    callback_data="back"

                )

            ]

        ]

    )


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    if user_id not in balances:

        balances[user_id] = 0


    await update.message.reply_text(

        "🎱 Welcome to Gadaa Bingo!\n\n"

        "👇 Filannoo kee filadhu:",

        reply_markup=main_menu()

    )


# =========================
# BUTTON HANDLER
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    global game_open

    query = update.callback_query

    await query.answer()

    data = query.data

    user_id = query.from_user.id


    # =========================
    # BUY CARD
    # =========================

    if data == "buy_card":

        keyboard = [

            [

                InlineKeyboardButton(

                    "💵 10 Birr Card",

                    callback_data="group_10"

                )

            ],

            [

                InlineKeyboardButton(

                    "💵 20 Birr Card",

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

            "🎫 Buy Bingo Card\n\n"

            "Garee card filadhu:",

            reply_markup=InlineKeyboardMarkup(

                keyboard

            )

        )


    # =========================
    # GROUP 10
    # =========================

    elif data == "group_10":

        keyboard = []

        row = []


        for number in range(1, 501):

            if number not in cards_10:

                row.append(

                    InlineKeyboardButton(

                        str(number),

                        callback_data=f"buy10_{number}"

                    )

                )


            if len(row) == 5:

                keyboard.append(row)

                row = []


        if row:

            keyboard.append(row)


        keyboard.append(

            [

                InlineKeyboardButton(

                    "🔙 Back",

                    callback_data="buy_card"

                )

            ]

        )


        await query.edit_message_text(

            "💵 10 Birr Card\n\n"

            "🎫 Card kee filadhu:",

            reply_markup=InlineKeyboardMarkup(

                keyboard

            )

        )


    # =========================
    # GROUP 20
    # =========================

    elif data == "group_20":

        keyboard = []

        row = []


        for number in range(1, 501):

            if number not in cards_20:

                row.append(

                    InlineKeyboardButton(

                        str(number),

                        callback_data=f"buy20_{number}"

                    )

                )


            if len(row) == 5:

                keyboard.append(row)

                row = []


        if row:

            keyboard.append(row)


        keyboard.append(

            [

                InlineKeyboardButton(

                    "🔙 Back",

                    callback_data="buy_card"

                )

            ]

        )


        await query.edit_message_text(

            "💵 20 Birr Card\n\n"

            "🎫 Card kee filadhu:",

            reply_markup=InlineKeyboardMarkup(

                keyboard

            )

        )


    # =========================
    # BUY 10 CARD
    # =========================

    elif data.startswith("buy10_"):

        card_number = int(

            data.split("_")[1]

        )


        if card_number in cards_10:

            await query.answer(

                "❌ Card kun duraan gurgurameera!",

                show_alert=True

            )

            return


        if get_balance(user_id) < CARD_10_PRICE:

            await query.answer(

                "❌ Balance kee 10 Birr hin gahu!",

                show_alert=True

            )

            return


        remove_balance(

            user_id,

            CARD_10_PRICE,

            "CARD 10 BUY"

        )


        cards_10[card_number] = user_id


        await query.edit_message_text(

            f"🎉 Card kee bitameera!\n\n"

            f"🎫 Card ID: {card_number}\n"

            f"💵 Gatii: 10 Birr\n\n"

            f"💰 Balance hafe: "

            f"{get_balance(user_id)} Birr",

            reply_markup=back_button()

        )


    # =========================
    # BUY 20 CARD
    # =========================

    elif data.startswith("buy20_"):

        card_number = int(

            data.split("_")[1]

        )


        if card_number in cards_20:

            await query.answer(

                "❌ Card kun duraan gurgurameera!",

                show_alert=True

            )

            return


        if get_balance(user_id) < CARD_20_PRICE:

            await query.answer(

                "❌ Balance kee 20 Birr hin gahu!",

                show_alert=True

            )

            return


        remove_balance(

            user_id,

            CARD_20_PRICE,

            "CARD 20 BUY"

        )


        cards_20[card_number] = user_id


        await query.edit_message_text(

            f"🎉 Card kee bitameera!\n\n"

            f"🎫 Card ID: {card_number}\n"

            f"💵 Gatii: 20 Birr\n\n"

            f"💰 Balance hafe: "

            f"{get_balance(user_id)} Birr",

            reply_markup=back_button()

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

            reply_markup=InlineKeyboardMarkup(

                keyboard

            )

        )


    # =========================
    # AMOUNT
    # =========================

    elif data.startswith("amount_"):

        amount = int(

            data.split("_")[1]

        )


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

            "Telebirr filadhu:",

            reply_markup=InlineKeyboardMarkup(

                keyboard

            )

        )


    # =========================
    # TELEBIRR 1
    # =========================

    elif data.startswith("pay1_"):

        amount = int(

            data.split("_")[1]

        )


        context.user_data["proof_amount"] = amount


        await query.edit_message_text(

            f"📱 Telebirr 1\n\n"

            f"💰 Amount: {amount} Birr\n\n"

            f"📞 0902640434\n\n"

            f"Erga {amount} Birr kaffaltee booda,\n"

            f"📸 Payment proof ergi.",

            reply_markup=back_button()

        )


    # =========================
    # TELEBIRR 2
    # =========================

    elif data.startswith("pay2_"):

        amount = int(

            data.split("_")[1]

        )


        context.user_data["proof_amount"] = amount


        await query.edit_message_text(

            f"📱 Telebirr 2\n\n"

            f"💰 Amount: {amount} Birr\n\n"

            f"📞 0950740256\n\n"

            f"Erga {amount} Birr kaffaltee booda,\n"

            f"📸 Payment proof ergi.",

            reply_markup=back_button()

        )


    # =========================
    # BALANCE
    # =========================

    elif data == "balance":

        await query.edit_message_text(

            f"💳 Balance Kee\n\n"

            f"💰 {get_balance(user_id)} Birr",

            reply_markup=back_button()

        )


    # =========================
    # MY CARDS
    # =========================

    elif data == "my_cards":

        my_10 = [

            str(card)

            for card, owner

            in cards_10.items()

            if owner == user_id

        ]


        my_20 = [

            str(card)

            for card, owner

            in cards_20.items()

            if owner == user_id

        ]


        await query.edit_message_text(

            "🧾 My Cards\n\n"

            f"💵 10 Birr:\n"

            f"{', '.join(my_10) if my_10 else 'Hin jiru'}\n\n"

            f"💵 20 Birr:\n"

            f"{', '.join(my_20) if my_20 else 'Hin jiru'}",

            reply_markup=back_button()

        )


    # =========================
    # HISTORY
    # =========================

    elif data == "history":

        my_history = [

            item

            for item in transactions

            if item["user_id"] == user_id

        ]


        if not my_history:

            text = "📜 History kee duwwaa dha."

        else:

            text = "📜 Transaction History\n\n"

            for item in my_history[-20:]:

                text += (

                    f"• {item['type']}: "

                    f"{item['amount']} Birr\n"

                )


        await query.edit_message_text(

            text,

            reply_markup=back_button()

        )


    # =========================
    # PLAY BINGO
    # =========================

    elif data == "play_bingo":

        if not game_open:

            await query.edit_message_text(

                "⏳ Bingo game amma cufaa dha.\n\n"

                "Admin yeroo game banu ni taphatta.",

                reply_markup=back_button()

            )

            return


        bingo_url = "https://afro-bingo-6.onrender.com"


        keyboard = [

            [

                InlineKeyboardButton(

                    "🎮 PLAY BINGO NOW",

                    web_app=WebAppInfo(

                        url=bingo_url

                    )

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

            "🎮 AFRO BINGO\n\n"

            "Bingo game taphachuuf "

            "button armaan gadii cuqaasi.",

            reply_markup=InlineKeyboardMarkup(

                keyboard

            )

        )


    # =========================
    # WITHDRAWAL
    # =========================

    elif data == "withdrawal":

        if get_balance(user_id) <= 0:

            await query.edit_message_text(

                "❌ Balance kee 0 Birr dha.",

                reply_markup=back_button()

            )

            return


        context.user_data["withdrawal_mode"] = True


        await query.edit_message_text(

            "💸 Withdrawal\n\n"

            "Mee amount ati baasuu barbaaddu "

            "barreessi.\n\n"

            "Fakkeenya: 100",

            reply_markup=back_button()

        )


    # =========================
    # WINNERS
    # =========================

    elif data == "winners":

        if not winners:

            text = "🏆 Amma winner hin jiru."

        else:

            text = "🏆 Winners\n\n"

            for winner in winners[-20:]:

                text += (

                    f"👤 User ID: {winner['user_id']}\n"

                    f"💰 Prize: {winner['prize']} Birr\n\n"

                )


        await query.edit_message_text(

            text,

            reply_markup=back_button()

        )


    # =========================
    # HOW TO PLAY
    # =========================

    elif data == "how_to_play":

        await query.edit_message_text(

            "ℹ️ How to Play\n\n"

            "1️⃣ Deposit godhi\n"

            "2️⃣ Admin approve eega\n"

            "3️⃣ Card bitadhu\n"

            "4️⃣ Play Game cuqaasi\n"

            "5️⃣ Bingo yeroo cufamu winner ni murtaa'a\n\n"

            "🏆 Prize = 70% total card sales",

            reply_markup=back_button()

        )


    # =========================
    # ADMIN OPEN GAME
    # =========================

    elif data == "admin_open_game":

        if user_id != ADMIN_ID:

            await query.answer(

                "❌ Admin qofaaf!",

                show_alert=True

            )

            return


        game_open = True


        await query.edit_message_text(

            "🎮 Bingo Game banameera.",

            reply_markup=admin_menu()

        )


    # =========================
    # ADMIN CLOSE GAME
    # =========================

    elif data == "admin_close_game":

        if user_id != ADMIN_ID:

            await query.answer(

                "❌ Admin qofaaf!",

                show_alert=True

            )

            return


        game_open = False


        await close_game(

            context

        )


        await query.edit_message_text(

            "🔒 Bingo Game cufameera.\n\n"

            "🏆 Winner process xumurameera.",

            reply_markup=admin_menu()

        )


    # =========================
    # ADMIN MENU
    # =========================

    elif data == "admin_menu":

        if user_id != ADMIN_ID:

            await query.answer(

                "❌ Admin qofaaf!",

                show_alert=True

            )

            return


        await query.edit_message_text(

            "👨‍💼 Admin Menu",

            reply_markup=admin_menu()

        )


    # =========================
    # APPROVE DEPOSIT
    # =========================

    elif data.startswith("approve_"):

        if user_id != ADMIN_ID:

            await query.answer(

                "❌ Admin qofaaf!",

                show_alert=True

            )

            return


        parts = data.split("_")

        deposit_user_id = int(parts[1])

        amount = int(parts[2])


        add_balance(

            deposit_user_id,

            amount,

            "DEPOSIT APPROVED"

        )


        await context.bot.send_message(

            chat_id=deposit_user_id,

            text=(

                "✅ Payment kee mirkanaa'eera!\n\n"

                f"💰 {amount} Birr balance kee irratti "

                "dabalameera.\n\n"

                f"💳 Balance kee: "

                f"{get_balance(deposit_user_id)} Birr"

            )

        )


        await query.edit_message_caption(

            caption=(

                "✅ APPROVED\n\n"

                f"💰 Amount: {amount} Birr\n"

                f"🆔 User ID: {deposit_user_id}"

            )

        )


    # =========================
    # REJECT DEPOSIT
    # =========================

    elif data.startswith("reject_"):

        if user_id != ADMIN_ID:

            await query.answer(

                "❌ Admin qofaaf!",

                show_alert=True

            )

            return


        deposit_user_id = int(

            data.split("_")[1]

        )


        await context.bot.send_message(

            chat_id=deposit_user_id,

            text=(

                "❌ Payment proof kee "

                "hin mirkanoofne.\n\n"

                "Maaloo irra deebi'ii ilaali."

            )

        )


        await query.edit_message_caption(

            caption=(

                "❌ REJECTED\n\n"

                f"🆔 User ID: {deposit_user_id}"

            )

        )


    # =========================
    # APPROVE WITHDRAWAL
    # =========================

    elif data.startswith("approve_withdraw_"):

        if user_id != ADMIN_ID:

            await query.answer(

                "❌ Admin qofaaf!",

                show_alert=True

            )

            return


        parts = data.split("_")

        withdraw_user_id = int(parts[2])

        amount = int(parts[3])


        if amount > get_balance(withdraw_user_id):

            await query.answer(

                "❌ Balance user sanaa gahaa miti.",

                show_alert=True

            )

            return


        remove_balance(

            withdraw_user_id,

            amount,

            "WITHDRAWAL"

        )


        await context.bot.send_message(

            chat_id=withdraw_user_id,

            text=(

                "✅ Withdrawal kee mirkanaa'eera!\n\n"

                f"💸 Amount: {amount} Birr\n\n"

                "📞 Admin irraa kaffaltii eegi."

            )

        )


        await query.edit_message_caption(

            caption=(

                "✅ WITHDRAWAL APPROVED\n\n"

                f"💰 Amount: {amount} Birr\n"

                f"🆔 User ID: {withdraw_user_id}"

            )

        )


    # =========================
    # REJECT WITHDRAWAL
    # =========================

    elif data.startswith("reject_withdraw_"):

        if user_id != ADMIN_ID:

            await query.answer(

                "❌ Admin qofaaf!",

                show_alert=True

            )

            return


        withdraw_user_id = int(

            data.split("_")[2]

        )


        await context.bot.send_message(

            chat_id=withdraw_user_id,

            text=(

                "❌ Withdrawal kee "

                "hin mirkanoofne."

            )

        )


        await query.edit_message_caption(

            caption=(

                "❌ WITHDRAWAL REJECTED\n\n"

                f"🆔 User ID: {withdraw_user_id}"

            )

        )


    # =========================
    # BACK
    # =========================

    elif data == "back":

        await query.edit_message_text(

            "🎱 Welcome to Gadaa Bingo!\n\n"

            "👇 Filannoo kee filadhu:",

            reply_markup=main_menu()

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

            "❌ Dura amount fi payment method filadhu."

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

                callback_data=f"approve_{user_id}_{amount}"

            ),

            InlineKeyboardButton(

                "❌ Reject",

                callback_data=f"reject_{user_id}"

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
# TEXT HANDLER
# =========================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    text = update.message.text.strip()


    # =========================
    # WITHDRAWAL AMOUNT
    # =========================

    if context.user_data.get(

        "withdrawal_mode"

    ):

        try:

            amount = int(text)

        except ValueError:

            await update.message.reply_text(

                "❌ Lakkoofsa sirrii barreessi."

            )

            return


        if amount <= 0:

            await update.message.reply_text(

                "❌ Amount sirrii galchi."

            )

            return


        if amount > get_balance(user_id):

            await update.message.reply_text(

                "❌ Balance kee gahaa miti."

            )

            return


        context.user_data["withdraw_amount"] = amount

        context.user_data["withdrawal_mode"] = False

        context.user_data["withdraw_account_mode"] = True


        await update.message.reply_text(

            f"💸 Withdrawal: {amount} Birr\n\n"

            "📱 Lakkoofsa Telebirr ykn account "

            "kaffaltii itti fudhattu ergi."

        )

        return


    # =========================
    # WITHDRAWAL ACCOUNT
    # =========================

    if context.user_data.get(

        "withdraw_account_mode"

    ):

        amount = context.user_data.get(

            "withdraw_amount"

        )


        pending_withdrawals[user_id] = {

            "amount": amount,

            "account": text

        }


        keyboard = [

            [

                InlineKeyboardButton(

                    "✅ Approve",

                    callback_data=(

                        f"approve_withdraw_"

                        f"{user_id}_{amount}"

                    )

                ),

                InlineKeyboardButton(

                    "❌ Reject",

                    callback_data=(

                        f"reject_withdraw_"

                        f"{user_id}"

                    )

                )

            ]

        ]


        await context.bot.send_message(

            chat_id=ADMIN_ID,

            text=(

                "💸 WITHDRAWAL REQUEST\n\n"

                f"🆔 User ID: {user_id}\n"

                f"💰 Amount: {amount} Birr\n"

                f"📱 Account: {text}"

            ),

            reply_markup=InlineKeyboardMarkup(

                keyboard

            )

        )


        await update.message.reply_text(

            "✅ Withdrawal request kee adminitti "

            "ergameera.\n\n"

            "⏳ Admin mirkaneessuu eegi."

        )


        context.user_data.pop(

            "withdraw_account_mode",

            None

        )

        context.user_data.pop(

            "withdraw_amount",

            None

        )

        return


# =========================
# ADMIN MENU
# =========================

def admin_menu():

    keyboard = [

        [

            InlineKeyboardButton(

                "🎮 Open Game",

                callback_data="admin_open_game"

            ),

            InlineKeyboardButton(

                "🔒 Close Game",

                callback_data="admin_close_game"

            )

        ],

        [

            InlineKeyboardButton(

                "🏠 Main Menu",

                callback_data="back"

            )

        ]

    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# CLOSE GAME
# =========================

async def close_game(context):

    total_sales = 0

    card_count = 0


    for card in cards_10:

        total_sales += 10

        card_count += 1


    for card in cards_20:

        total_sales += 20

        card_count += 1


    if card_count == 0:

        return


    prize = int(

        total_sales * PRIZE_PERCENT / 100

    )


    all_cards = []


    for card, owner in cards_10.items():

        all_cards.append(

            (

                card,

                owner,

                10

            )

        )


    for card, owner in cards_20.items():

        all_cards.append(

            (

                card,

                owner,

                20

            )

        )


    if not all_cards:

        return


    winner_card, winner_id, price = all_cards[0]


    add_balance(

        winner_id,

        prize,

        "BINGO PRIZE"

    )


    winners.append(

        {

            "user_id": winner_id,

            "prize": prize

        }

    )


    await context.bot.send_message(

        chat_id=winner_id,

        text=(

            "🎉 CONGRATULATIONS!\n\n"

            "🏆 Ati winner taateetta!\n"

            f"💰 Prize: {prize} Birr\n\n"

            f"💳 Balance kee: "

            f"{get_balance(winner_id)} Birr"

        )

    )


# =========================
# ADMIN COMMAND
# =========================

async def admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(

            "❌ Admin qofaaf."

        )

        return


    await update.message.reply_text(

        "👨‍💼 Admin Menu",

        reply_markup=admin_menu()

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

        "Gadaa Bingo Bot is running..."

    )


    app.run_polling()


if __name__ == "__main__":

    main()
