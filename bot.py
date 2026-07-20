
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

PRIZE_PERCENT = 70


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
# BINGO CARD GENERATOR
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

        generate_column(61, 75)

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


    # H
