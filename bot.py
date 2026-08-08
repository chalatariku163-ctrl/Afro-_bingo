import os
import json
import time
import random
import threading

from threading import Lock

from flask import Flask, jsonify, request, send_from_directory

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

PORT = int(
    os.getenv(
        "PORT",
        "10000"
    )
)

WEB_APP_URL = (
    "https://afro-bingo-1.onrender.com"
)

TELEBIRR_NUMBER = "0902640434"


# =========================================================
# CARD PRICE
# =========================================================

CARD_10_PRICE = 10
CARD_20_PRICE = 20

STAKE_START = 10


# =========================================================
# PRIZE
# =========================================================

PRIZE_PERCENT = 80


# =========================================================
# TIME
# =========================================================

CARD_BUYING_SECONDS = 40

NUMBER_CALL_SECONDS = 5

WINNER_SHARE_SECONDS = 3


# =========================================================
# CARDS
# =========================================================

TOTAL_CARD_COUNT = 500


# =========================================================
# PLAYER / DERASH
# =========================================================

STARTING_PLAYER_COUNT = 0

DERASH_START = 0

PLAYER_PER_CARD = 1

DERASH_PER_CARD = 8


# =========================================================
# DATA FILE
# =========================================================

DATA_FILE = "data.json"


# =========================================================
# FLASK
# =========================================================

web_app = Flask(__name__)

bingo_lock = Lock()


# =========================================================
# GAME STATE
# =========================================================

bingo_game = {

    "game_id": 0,

    "status": "waiting",

    "started": False,

    "card_buying": False,

    "card_buying_end_time": 0,

    "called_numbers": [],

    "current_number": None,

    "winner": False,

    "winner_window_open": False,

    "winner_window_end_time": 0,

    "winners": [],

    "prize": 0,

    "winner_prize": 0,

    "winner_cards": [],

    "total_sales": 0,

    "player_count": 0,

    "derash": 0,

    "cards_sold": [],

    "game_time": 0,
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

data_lock = Lock()


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

        with data_lock:

            with open(
                DATA_FILE,
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

    except Exception as error:

        print(
            "SAVE ERROR:",
            error,
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

        print(
            "NO DATA FILE FOUND"
        )

        return

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        users = {
            int(k): v
            for k, v in data.get(
                "users",
                {},
            ).items()
        }

        balances = {
            int(k): float(v)
            for k, v in data.get(
                "balances",
                {},
            ).items()
        }

        transactions = data.get(
            "transactions",
            [],
        )

        cards_10 = {
            int(k): v
            for k, v in data.get(
                "cards_10",
                {},
            ).items()
        }

        cards_20 = {
            int(k): v
            for k, v in data.get(
                "cards_20",
                {},
            ).items()
        }

        pending_deposits = {
            int(k): v
            for k, v in data.get(
                "pending_deposits",
                {},
            ).items()
        }

        pending_withdrawals = {
            int(k): v
            for k, v in data.get(
                "pending_withdrawals",
                {},
            ).items()
        }

        winners = data.get(
            "winners",
            [],
        )

        print(
            "DATA LOADED"
        )

    except Exception as error:

        print(
            "LOAD ERROR:",
            error,
        )


# =========================================================
# BALANCE
# =========================================================

def get_balance(user_id):

    try:

        user_id = int(user_id)

    except Exception:

        return 0.0

    try:

        return float(
            balances.get(
                user_id,
                0.0,
            )
        )

    except Exception:

        return 0.0


def add_balance(
    user_id,
    amount,
):

    try:

        user_id = int(user_id)

        amount = float(amount)

    except Exception:

        return False

    if amount <= 0:

        return False

    balances[user_id] = round(
        get_balance(user_id)
        + amount,
        2,
    )

    save_data()

    return True


def remove_balance(
    user_id,
    amount,
):

    try:

        user_id = int(user_id)

        amount = float(amount)

    except Exception:

        return False

    if amount <= 0:

        return False

    current_balance = get_balance(
        user_id
    )

    if current_balance < amount:

        return False

    balances[user_id] = round(
        current_balance - amount,
        2,
    )

    save_data()

    return True


# =========================================================
# TRANSACTION
# =========================================================

def add_transaction(
    user_id,
    transaction_type,
    amount,
    status="completed",
    note="",
):

    try:

        user_id = int(user_id)

        amount = float(amount)

    except Exception:

        return

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
# CARD NORMALIZATION
# =========================================================

def normalize_card_data():

    for cards in (
        cards_10,
        cards_20,
    ):

        for card_number in list(
            cards.keys()
        ):

            value = cards[
                card_number
            ]

            if isinstance(
                value,
                int,
            ):

                cards[
                    card_number
                ] = {

                    "owner":
                        value,

                    "card_type":
                        "10"
                        if cards is cards_10
                        else "20",

                    "price":
                        CARD_10_PRICE
                        if cards is cards_10
                        else CARD_20_PRICE,

                    "game_id":
                        0,

                    "card_data":
                        None,

                }

            elif isinstance(
                value,
                str,
            ):

                try:

                    cards[
                        card_number
                    ] = {

                        "owner":
                            int(value),

                        "card_type":
                            "10"
                            if cards is cards_10
                            else "20",

                        "price":
                            CARD_10_PRICE
                            if cards is cards_10
                            else CARD_20_PRICE,

                        "game_id":
                            0,

                        "card_data":
                            None,

                    }

                except Exception:

                    pass

            elif isinstance(
                value,
                dict,
            ):

                value.setdefault(
                    "owner",
                    None,
                )

                value.setdefault(
                    "card_type",
                    "10"
                    if cards is cards_10
                    else "20",
                )

                value.setdefault(
                    "price",
                    CARD_10_PRICE
                    if cards is cards_10
                    else CARD_20_PRICE,
                )

                value.setdefault(
                    "game_id",
                    0,
                )

                value.setdefault(
                    "card_data",
                    None,
                )


# =========================================================
# GET CARD DATA
# =========================================================

def get_card_data(
    card_type,
    card_number,
):

    card_type = str(
        card_type
    ).strip()

    if card_type == "10":

        cards = cards_10

    elif card_type == "20":

        cards = cards_20

    else:

        return None

    try:

        card_number = int(
            card_number
        )

    except Exception:

        return None

    card = cards.get(
        card_number
    )

    if card is None:

        return None

    if isinstance(
        card,
        int,
    ):

        card = {

            "owner":
                card,

            "card_type":
                card_type,

            "price":
                CARD_10_PRICE
                if card_type == "10"
                else CARD_20_PRICE,

            "game_id":
                0,

            "card_data":
                None,

        }

        cards[
            card_number
        ] = card

    return card


# =========================================================
# CARD OWNER
# =========================================================

def get_card_owner(
    card_type,
    card_number,
):

    card = get_card_data(
        card_type,
        card_number,
    )

    if not card:

        return None

    try:

        return int(
            card.get(
                "owner"
            )
        )

    except Exception:

        return None


# =========================================================
# CARD PAID FOR GAME
# =========================================================

def card_was_paid_for_game(
    card_type,
    card_number,
    game_id,
):

    card = get_card_data(
        card_type,
        card_number,
    )

    if not card:

        return False

    try:

        return int(
            card.get(
                "game_id",
                0,
            )
        ) == int(game_id)

    except Exception:

        return False


# =========================================================
# MARK CARD PAID
# =========================================================

def mark_card_paid_for_game(
    card_type,
    card_number,
    game_id,
):

    card = get_card_data(
        card_type,
        card_number,
    )

    if not card:

        return False

    card["game_id"] = int(
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
        maximum,
    ):

        nonlocal seed

        seed = (
            seed * 9301
            + 49297
        ) % 233280

        rnd = (
            seed / 233280
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
        maximum,
    ):

        numbers = []

        while len(numbers) < 5:

            number = seeded_random(
                minimum,
                maximum,
            )

            if number not in numbers:

                numbers.append(
                    number
                )

        return numbers

    columns = [

        generate_column(
            1,
            15,
        ),

        generate_column(
            16,
            30,
        ),

        generate_column(
            31,
            45,
        ),

        generate_column(
            46,
            60,
        ),

        generate_column(
            61,
            75,
        ),

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


# =========================================================
# CHECK BINGO
# =========================================================

def check_bingo(
    card,
    called_numbers,
):

    called_numbers = {
        int(x)
        for x in called_numbers
    }

    marked = []

    for row in card:

        marked_row = []

        for value in row:

            if value == "FREE":

                marked_row.append(
                    True
                )

            else:

                try:

                    marked_row.append(
                        int(value)
                        in called_numbers
                    )

                except Exception:

                    marked_row.append(
                        False
                    )

        marked.append(
            marked_row
        )

    # ROW
    for row in range(5):

        if all(
            marked[row]
        ):

            return True

    # COLUMN
    for col in range(5):

        if all(
            marked[row][col]
            for row in range(5)
        ):

            return True

    # DIAGONAL
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

    # FOUR CORNERS
    if (
        marked[0][0]
        and marked[0][4]
        and marked[4][0]
        and marked[4][4]
    ):

        return True

    return False


# =========================================================
# DERASH
# =========================================================

def update_player_and_derash_locked():

    player_count = (
        len(cards_10)
        + len(cards_20)
    )

    bingo_game[
        "player_count"
    ] = player_count

    derash = (

        DERASH_START

        +

        (
            player_count
            - STARTING_PLAYER_COUNT
        )

        *

        DERASH_PER_CARD

    )

    if derash < DERASH_START:

        derash = DERASH_START

    bingo_game[
        "derash"
    ] = round(
        derash,
        2,
    )


# =========================================================
# WINNER WINDOW
# =========================================================

def start_winner_window_locked():

    if bingo_game[
        "winner_window_open"
    ]:

        return

    game_id = bingo_game[
        "game_id"
    ]

    bingo_game[
        "winner_window_open"
    ] = True

    bingo_game[
        "winner_window_end_time"
    ] = (
        time.time()
        + WINNER_SHARE_SECONDS
    )

    bingo_game[
        "winner"
    ] = True

    bingo_game[
        "started"
    ] = False

    bingo_game[
        "card_buying"
    ] = False

    bingo_game[
        "status"
    ] = "winner"

    threading.Thread(
        target=finish_game_and_share_prize,
        args=(game_id,),
        daemon=True,
    ).start()


# =========================================================
# HOME
# =========================================================

@web_app.route(
    "/",
    methods=["GET"],
)
def home():

    base_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    return send_from_directory(
        base_dir,
        "index.html",
    )


# =========================================================
# HEALTH
# =========================================================

@web_app.route(
    "/health",
    methods=["GET"],
)
def health():

    return jsonify({

        "success":
            True,

        "message":
            "GADAA BINGO SERVER IS RUNNING",

    })


# =========================================================
# GAME STATE API
# =========================================================

@web_app.route(
    "/api/game-state",
    methods=["GET"],
)
def game_state():

    user_id = request.args.get(
        "user_id",
        type=int,
    )

    with bingo_lock:

        if user_id:

            balance = get_balance(
                user_id
            )

        else:

            balance = 0.0


        # =================================================
        # MY CARDS
        # =================================================

        my_cards = []

        if user_id:

            for card_number, card_data in cards_10.items():

                if not isinstance(
                    card_data,
                    dict,
                ):

                    continue

                try:

                    owner = int(
                        card_data.get(
                            "owner"
                        )
                    )

                except Exception:

                    continue

                if owner != user_id:

                    continue

                my_cards.append({

                    "card_number":
                        int(card_number),

                    "card_type":
                        "10",

                    "price":
                        CARD_10_PRICE,

                    "game_id":
                        card_data.get(
                            "game_id",
                            0,
                        ),

                    "card":
                        card_data.get(
                            "card_data"
                        )
                        or generate_card(
                            int(card_number)
                        ),

                    "paid_for_current_game":
                        card_was_paid_for_game(
                            "10",
                            int(card_number),
                            bingo_game[
                                "game_id"
                            ],
                        ),

                })


            for card_number, card_data in cards_20.items():

                if not isinstance(
                    card_data,
                    dict,
                ):

                    continue

                try:

                    owner = int(
                        card_data.get(
                            "owner"
                        )
                    )

                except Exception:

                    continue

                if owner != user_id:

                    continue

                my_cards.append({

                    "card_number":
                        int(card_number),

                    "card_type":
                        "20",

                    "price":
                        CARD_20_PRICE,

                    "game_id":
                        card_data.get(
                            "game_id",
                            0,
                        ),

                    "card":
                        card_data.get(
                            "card_data"
                        )
                        or generate_card(
                            int(card_number)
                        ),

                    "paid_for_current_game":
                        card_was_paid_for_game(
                            "20",
                            int(card_number),
                            bingo_game[
                                "game_id"
                            ],
                        ),

                })


        # =================================================
        # WINNERS
        # =================================================

        visible_winners = []

        for winner in bingo_game.get(
            "winners",
            [],
        ):

            visible_winners.append({

                "game_id":
                    winner.get(
                        "game_id",
                        0,
                    ),

                "card_number":
                    winner.get(
                        "card_number",
                        "",
                    ),

                "card_type":
                    winner.get(
                        "card_type",
                        "",
                    ),

                "owner_type":
                    winner.get(
                        "owner_type",
                        "CUSTOMER",
                    ),

                "user_id":
                    winner.get(
                        "user_id"
                    ),

                "username":
                    winner.get(
                        "username",
                        "",
                    ),

                "prize":
                    winner.get(
                        "prize",
                        0,
                    ),

                "time":
                    winner.get(
                        "time",
                        0,
                    ),

            })


        # =================================================
        # DERASH
        # =================================================

        update_player_and_derash_locked()

        player_count = bingo_game[
            "player_count"
        ]

        derash = bingo_game[
            "derash"
        ]


        # =================================================
        # PRIZE POOL
        # =================================================

        total_sales = bingo_game[
            "total_sales"
        ]

        prize_pool = round(
            total_sales
            * PRIZE_PERCENT
            / 100,
            2,
        )


        # =================================================
        # GAME TIME
        # =================================================

        if bingo_game[
            "card_buying"
        ]:

            game_time = max(
                0,
                int(
                    bingo_game[
                        "card_buying_end_time"
                    ]
                    - time.time()
                )
            )

        else:

            game_time = 0


        # =================================================
        # STATE
        # =================================================

        state = {

            "success":
                True,

            "game_id":
                bingo_game[
                    "game_id"
                ],

            "status":
                bingo_game[
                    "status"
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
                list(
                    bingo_game[
                        "called_numbers"
                    ]
                ),

            "current_number":
                bingo_game[
                    "current_number"
                ],

            "cards_sold":
                list(
                    bingo_game[
                        "cards_sold"
                    ]
                ),

            "player":
                player_count,

            "player_count":
                player_count,

            "total_sales":
                total_sales,

            "prize_pool":
                prize_pool,

            "derash":
                derash,

            "winner":
                bingo_game[
                    "winner"
                ],

            "winner_window_open":
                bingo_game[
                    "winner_window_open"
                ],

            "winner_window_end_time":
                bingo_game[
                    "winner_window_end_time"
                ],

            "winners":
                visible_winners,

            "winner_count":
                len(
                    visible_winners
                ),

            "prize":
                bingo_game[
                    "prize"
                ],

            "balance":
                balance,

            "my_cards":
                my_cards,

            "my_card_count":
                len(
                    my_cards
                ),

            "game_time":
                game_time,

        }

    return jsonify(
        state
    )


# =========================================================
# USER CARDS API
# =========================================================

@web_app.route(
    "/api/my-cards",
    methods=["GET"],
)
def my_cards_api():

    user_id = request.args.get(
        "user_id",
        type=int,
    )

    if not user_id:

        return jsonify({

            "success":
                False,

            "message":
                "User ID hin jiru.",

        }), 400


    result = []

    with bingo_lock:

        # 10 BIRR
        for card_number, card_data in cards_10.items():

            if not isinstance(
                card_data,
                dict,
            ):

                continue

            try:

                owner = int(
                    card_data.get(
                        "owner"
                    )
                )

            except Exception:

                continue

            if owner != user_id:

                continue

            result.append({

                "card_number":
                    int(card_number),

                "card_type":
                    "10",

                "price":
                    CARD_10_PRICE,

                "game_id":
                    card_data.get(
                        "game_id",
                        0,
                    ),

                "card":
                    card_data.get(
                        "card_data"
                    )
                    or generate_card(
                        int(card_number)
                    ),

            })


        # 20 BIRR
        for card_number, card_data in cards_20.items():

            if not isinstance(
                card_data,
                dict,
            ):

                continue

            try:

                owner = int(
                    card_data.get(
                        "owner"
                    )
                )

            except Exception:

                continue

            if owner != user_id:

                continue

            result.append({

                "card_number":
                    int(card_number),

                "card_type":
                    "20",

                "price":
                    CARD_20_PRICE,

                "game_id":
                    card_data.get(
                        "game_id",
                        0,
                    ),

                "card":
                    card_data.get(
                        "card_data"
                    )
                    or generate_card(
                        int(card_number)
                    ),

            })


    return jsonify({

        "success":
            True,

        "count":
            len(result),

        "cards":
            result,

    })


# =========================================================
# CHECK BINGO API
# =========================================================

@web_app.route(
    "/api/check-bingo",
    methods=["POST"],
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

    card_type = str(
        data.get(
            "card_type",
            "",
        )
    ).strip()


    if user_id is None:

        return jsonify({

            "success":
                False,

            "message":
                "User ID hin argamne.",

        }), 400


    if card_number is None:

        return jsonify({

            "success":
                False,

            "message":
                "Card number hin argamne.",

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
                "Data sirrii miti.",

        }), 400


    if card_type not in (
        "10",
        "20",
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Card type sirrii miti.",

        }), 400


    with bingo_lock:

        game_id = bingo_game[
            "game_id"
        ]

        started = bingo_game[
            "started"
        ]

        winner_window_open = bingo_game[
            "winner_window_open"
        ]

        winner_window_end_time = bingo_game[
            "winner_window_end_time"
        ]

        called_numbers = list(
            bingo_game[
                "called_numbers"
            ]
        )


        # Game must be running
        if (
            not started
            and
            not winner_window_open
        ):

            return jsonify({

                "success":
                    False,

                "message":
                    "Game amma hin jalqabne.",

            }), 400


        # Winner window
        if winner_window_open:

            if (
                time.time()
                > winner_window_end_time
            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        "Winner sharing time xumurame.",

                }), 400


        # Owner
        owner = get_card_owner(
            card_type,
            card_number,
        )

        if owner != user_id:

            return jsonify({

                "success":
                    False,

                "message":
                    "Card kun kan kee miti.",

            }), 403


        # Must belong to current game
        if not card_was_paid_for_game(
            card_type,
            card_number,
            game_id,
        ):

            return jsonify({

                "success":
                    False,

                "message":
                    "Card kun game kanaaf hin kaffalamne.",

            }), 403


        card = generate_card(
            card_number
        )


        # Check pattern
        if not check_bingo(
            card,
            called_numbers,
        ):

            return jsonify({

                "success":
                    False,

                "message":
                    "Bingo pattern hin guunne.",

            }), 400


        # Prevent duplicate
        for winner in bingo_game[
            "winners"
        ]:

            if (

                winner.get(
                    "owner_type"
                )
                == "CUSTOMER"

                and

                int(
                    winner.get(
                        "user_id",
                        -1,
                    )
                )
                == user_id

                and

                int(
                    winner.get(
                        "card_number",
                        -1,
                    )
                )
                == card_number

                and

                str(
                    winner.get(
                        "card_type",
                        "",
                    )
                )
                == card_type

            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        "Card kun duraan winner ta'eera.",

                }), 400


        # =================================================
        # WINNER
        # =================================================

        winner_data = {

            "game_id":
                game_id,

            "user_id":
                user_id,

            "username":
                users.get(
                    user_id,
                    {},
                ).get(
                    "username",
                    "",
                ),

            "card_number":
                card_number,

            "card_type":
                card_type,

            "owner_type":
                "CUSTOMER",

            "prize":
                0,

            "time":
                time.time(),

        }


        bingo_game[
            "winners"
        ].append(
            winner_data
        )


        bingo_game[
            "winner_cards"
        ].append(
            card_number
        )


        start_winner_window_locked()


        visible_winners = list(
            bingo_game[
                "winners"
            ]
        )


    return jsonify({

        "success":
            True,

        "message":
            "BINGO! Ati winner taate.",

        "game_id":
            game_id,

        "card_number":
            card_number,

        "card_type":
            card_type,

        "winner_count":
            len(
                visible_winners
            ),

        "winners":
            visible_winners,

        "message2":
            "Winneroota biroo waliin prize share ni ta'a.",

    })


# =========================================================
# FINISH GAME
# =========================================================

def finish_game_and_share_prize(
    game_id
):

    time.sleep(
        WINNER_SHARE_SECONDS
    )


    with bingo_lock:

        if bingo_game[
            "game_id"
        ] != game_id:

            return


        if not bingo_game[
            "winner_window_open"
        ]:

            return


        winner_list = list(
            bingo_game[
                "winners"
            ]
        )


        if not winner_list:

            bingo_game[
                "winner_window_open"
            ] = False

            return


        total_sales = float(
            bingo_game[
                "total_sales"
            ]
        )


        prize_pool = round(
            total_sales
            * PRIZE_PERCENT
            / 100,
            2,
        )


        winner_count = len(
            winner_list
        )


        share = round(
            prize_pool
            / winner_count,
            2,
        )


        bingo_game[
            "prize"
        ] = prize_pool

        bingo_game[
            "winner_prize"
        ] = share

        bingo_game[
            "winner_window_open"
        ] = False

        bingo_game[
            "started"
        ] = False

        bingo_game[
            "status"
        ] = "finished"


        # Save winner prizes
        for winner in winner_list:

            winner[
                "prize"
            ] = share


    # =====================================================
    # PAY WINNERS
    # =====================================================

    for winner in winner_list:

        if winner.get(
            "owner_type"
        ) != "CUSTOMER":

            continue


        try:

            user_id = int(
                winner[
                    "user_id"
                ]
            )

        except Exception:

            continue


        amount = round(
            share,
            2,
        )


        add_balance(
            user_id,
            amount,
        )


        winner_record = {

            "game_id":
                game_id,

            "user_id":
                user_id,

            "card_number":
                winner[
                    "card_number"
                ],

            "card_type":
                winner[
                    "card_type"
                ],

            "prize":
                amount,

            "winner_count":
                winner_count,

            "time":
                time.time(),

        }


        winners.append(
            winner_record
        )


        add_transaction(
            user_id,
            "bingo_prize",
            amount,
            "completed",
            f"Game {game_id} shared prize",
        )


    save_data()


    print(
        f"GAME {game_id} FINISHED"
    )

    print(
        f"TOTAL WINNERS: {winner_count}"
    )

    print(
        f"PRIZE POOL: {prize_pool}"
    )

    print(
        f"SHARE EACH: {share}"
    )


    threading.Thread(
        target=auto_next_game_after_finish,
        args=(game_id,),
        daemon=True,
    ).start()


# =========================================================
# BUY CARD API
# =========================================================

@web_app.route(
    "/api/buy-card",
    methods=["POST"],
)
def buy_card_api():

    data = request.get_json(
        silent=True
    ) or {}


    user_id = data.get(
        "user_id"
    )

    card_number = data.get(
        "card_number"
    )

    card_type = str(
        data.get(
            "card_type",
            "",
        )
    ).strip()


    # =====================================================
    # USER
    # =====================================================

    if user_id is None:

        return jsonify({

            "success":
                False,

            "message":
                "User ID hin jiru.",

        }), 400


    try:

        user_id = int(
            user_id
        )

        card_number = int(
            card_number
        )

    except (
        TypeError,
        ValueError,
    ):

        return jsonify({

            "success":
                False,

            "message":
                "User ID ykn Card Number sirrii miti.",

        }), 400


    # =====================================================
    # CARD TYPE
    # =====================================================

    if card_type in (
        "10",
        "10 Birr",
        "CARD_10",
    ):

        card_type = "10"

        price = CARD_10_PRICE

        cards = cards_10


    elif card_type in (
        "20",
        "20 Birr",
        "CARD_20",
    ):

        card_type = "20"

        price = CARD_20_PRICE

        cards = cards_20


    else:

        return jsonify({

            "success":
                False,

            "message":
                "Card type sirrii miti.",

        }), 400


    # =====================================================
    # CARD NUMBER
    # =====================================================

    if (
        card_number < 1
        or
        card_number > TOTAL_CARD_COUNT
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Card number 1 hanga 500 ta'uu qaba.",

        }), 400


    # =====================================================
    # LOCK
    # =====================================================

    with bingo_lock:

        game_id = bingo_game[
            "game_id"
        ]


        # =================================================
        # BUYING OPEN?
        # =================================================

        if not bingo_game[
            "card_buying"
        ]:

            return jsonify({

                "success":
                    False,

                "message":
                    "Yeroon card bituu cufameera.",

            }), 400


        # =================================================
        # CARD ALREADY SOLD
        # =================================================

        if card_number in cards:

            existing = cards[
                card_number
            ]

            existing_owner = None

            if isinstance(
                existing,
                dict,
            ):

                existing_owner = existing.get(
                    "owner"
                )

            else:

                existing_owner = existing


            if str(
                existing_owner
            ) == str(
                user_id
            ):

                return jsonify({

                    "success":
                        False,

                    "message":
                        "Card kun ati duraan bitatteetta.",

                }), 400


            return jsonify({

                "success":
                    False,

                "message":
                    "Card kun duraan fudhatameera.",

            }), 400


        # =================================================
        # BALANCE
        # =================================================

        balance = get_balance(
            user_id
        )


        if balance < price:

            return jsonify({

                "success":
                    False,

                "message":
                    "Balance kee gahaa miti.",

                "balance":
                    balance,

                "required":
                    price,

            }), 400


        # =================================================
        # CARD GENERATE
        # =================================================

        card_data = generate_card(
            card_number
        )


        # =================================================
        # REMOVE MONEY
        # =================================================

        if not remove_balance(
            user_id,
            price,
        ):

            return jsonify({

                "success":
                    False,

                "message":
                    "Balance irraa maallaqa hir'isuun hin danda'amne.",

            }), 400


        # =================================================
        # SAVE CARD
        # =================================================

        cards[
            card_number
        ] = {

            "owner":
                user_id,

            "card_type":
                card_type,

            "price":
                price,

            "game_id":
                game_id,

            "card_data":
                card_data,

            "created_at":
                time.time(),

        }


        # =================================================
        # CARDS SOLD
        # =================================================

        bingo_game[
            "cards_sold"
        ].append({

            "card_number":
                card_number,

            "card_type":
                card_type,

            "user_id":
                user_id,

            "price":
                price,

        })


        # =================================================
        # SALES
        # =================================================

        bingo_game[
            "total_sales"
        ] = round(

            bingo_game.get(
                "total_sales",
                0,
            )
            + price,

            2,
        )


        # =================================================
        # PLAYER / DERASH
        # =================================================

        update_player_and_derash_locked()


        # =================================================
        # TRANSACTION
        # =================================================

        transactions.append({

            "user_id":
                user_id,

            "type":
                "card_purchase",

            "amount":
                price,

            "status":
                "completed",

            "note":
                (
                    f"Game {game_id} "
                    f"Card {card_number} "
                    f"Type {card_type}"
                ),

            "time":
                time.time(),

        })


        save_data()


        new_balance = get_balance(
            user_id
        )


        player_count = bingo_game[
            "player_count"
        ]

        total_sales = bingo_game[
            "total_sales"
        ]

        derash = bingo_game[
            "derash"
        ]


    return jsonify({

    "success":
        True,

    "message":
        "Card bitameera.",

    "user_id":
        user_id,

    "card_number":
        card_number,

    "card_type":
        card_type,

    "price":
        price,

    "game_id":
        game_id,

    # IMPORTANT:
    # index.html kee "data.card" eega
    "card":
        card_data,

    # Kunis compatibility'f haa jiraatu
    "card_data":
        card_data,

    "balance":
        new_balance,

    "player_count":
        player_count,

    "total_sales":
        total_sales,

    "prize_pool":
        round(
            total_sales
            * PRIZE_PERCENT
            / 100,
            2,
        ),

    "derash":
        derash,

})


# =========================================================
# RESET GAME STATE
# =========================================================

def reset_game_state():

    bingo_game[
        "status"
    ] = "waiting"

    bingo_game[
        "started"
    ] = False

    bingo_game[
        "card_buying"
    ] = False

    bingo_game[
        "card_buying_end_time"
    ] = 0

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
        "winner_window_open"
    ] = False

    bingo_game[
        "winner_window_end_time"
    ] = 0

    bingo_game[
        "winners"
    ] = []

    bingo_game[
        "winner_cards"
    ] = []

    bingo_game[
        "prize"
    ] = 0

    bingo_game[
        "winner_prize"
    ] = 0

    bingo_game[
        "total_sales"
    ] = 0

    bingo_game[
        "cards_sold"
    ] = []

    bingo_game[
        "player_count"
    ] = 0

    bingo_game[
        "derash"
    ] = DERASH_START

    bingo_game[
        "game_time"
    ] = 0

    print(
        "GAME STATE RESET"
    )


# =========================================================
# CLEAR CURRENT GAME CARDS
# =========================================================

def clear_cards_for_new_game():

    global cards_10
    global cards_20

    # Current game cards only.
    # User card ownership is not permanent.
    # New game starts with fresh card numbers.

    cards_10 = {}

    cards_20 = {}

    save_data()

    print(
        "CURRENT GAME CARDS CLEARED"
    )


# =========================================================
# START NEW GAME
# =========================================================

def start_new_game():

    with bingo_lock:

        # Clear cards from previous game
        clear_cards_for_new_game()

        # New game ID
        bingo_game[
            "game_id"
        ] += 1

        game_id = bingo_game[
            "game_id"
        ]

        reset_game_state()

        bingo_game[
            "status"
        ] = "buying"

        bingo_game[
            "card_buying"
        ] = True

        bingo_game[
            "card_buying_end_time"
        ] = (
            time.time()
            + CARD_BUYING_SECONDS
        )


    print(
        f"GAME {game_id} STARTED"
    )

    print(
        f"CARD BUYING OPEN FOR "
        f"{CARD_BUYING_SECONDS} SECONDS"
    )


    threading.Thread(
        target=card_buying_timer,
        args=(game_id,),
        daemon=True,
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

        bingo_game[
            "status"
        ] = "running"

        bingo_game[
            "game_time"
        ] = time.time()


        # No cards
        if (
            len(cards_10)
            +
            len(cards_20)
        ) == 0:

            bingo_game[
                "started"
            ] = False

            bingo_game[
                "status"
            ] = "no_players"


            threading.Thread(
                target=auto_next_game_after_finish,
                args=(game_id,),
                daemon=True,
            ).start()

            print(
                f"GAME {game_id}: "
                "NO CARDS SOLD"
            )

            return


    print(
        f"GAME {game_id} "
        "CARD BUYING CLOSED"
    )

    print(
        f"GAME {game_id} RUNNING"
    )


    threading.Thread(
        target=automatic_number_caller,
        args=(game_id,),
        daemon=True,
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


            available = [

                number

                for number in range(
                    1,
                    76,
                )

                if number not in bingo_game[
                    "called_numbers"
                ]

            ]


            if not available:

                bingo_game[
                    "started"
                ] = False

                bingo_game[
                    "status"
                ] = "finished"


                print(
                    "ALL 75 NUMBERS CALLED"
                )


                threading.Thread(
                    target=auto_next_game_after_finish,
                    args=(game_id,),
                    daemon=True,
                ).start()


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
            f"GAME {game_id} "
            f"NUMBER CALLED: "
            f"{number}"
        )


# =========================================================
# NEXT GAME
# =========================================================

def auto_next_game_after_finish(
    old_game_id
):

    time.sleep(
        5
    )


    with bingo_lock:

        if bingo_game[
            "game_id"
        ] != old_game_id:

            return


        if bingo_game[
            "started"
        ]:

            return


        if bingo_game[
            "card_buying"
        ]:

            return


        if bingo_game[
            "winner_window_open"
        ]:

            return


    print(
        "STARTING NEXT GAME"
    )


    start_new_game()


# =========================================================
# MAIN MENU
# =========================================================

def main_menu(
    user_id=None
):

    keyboard = [

        [

            InlineKeyboardButton(
                "🎮 PLAY GAME",
                web_app=WebAppInfo(
                    url=WEB_APP_URL
                ),
            )

        ],

        [

            InlineKeyboardButton(
                "💰 DEPOSIT",
                callback_data="deposit",
            ),

            InlineKeyboardButton(
                "💳 BALANCE",
                callback_data="balance",
            ),

        ],

        [

            InlineKeyboardButton(
                "💸 WITHDRAWAL",
                callback_data="withdrawal",
            ),

            InlineKeyboardButton(
                "📜 HISTORY",
                callback_data="history",
            ),

        ],

        [

            InlineKeyboardButton(
                "🏆 WINNERS",
                callback_data="winners",
            )

        ],

        [

            InlineKeyboardButton(
                "ℹ️ HOW TO PLAY",
                callback_data="how_to_play",
            )

        ],

    ]

    return InlineKeyboardMarkup(
        keyboard
    )


# =========================================================
# REGISTER KEYBOARD
# =========================================================

def register_keyboard():

    return ReplyKeyboardMarkup(

        [

            [

                KeyboardButton(
                    "📱 Register",
                    request_contact=True,
                )

            ]

        ],

        resize_keyboard=True,

        one_time_keyboard=True,

    )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    user_id = user.id


    if user_id in users:

        await update.message.reply_text(

            "🏠 <b>GADAA BINGO</b>\n\n"

            "👋 Welcome back!\n\n"

            "👇 Wanta barbaadde filadhu:",

            parse_mode="HTML",

            reply_markup=main_menu(
                user_id
            ),

        )

        return


    await update.message.reply_text(

        "🎉 <b>WELCOME TO GADAA BINGO!</b> 🎉\n\n"

        "📱 Mee Register godhi.",

        parse_mode="HTML",

        reply_markup=register_keyboard(),

    )


# =========================================================
# CONTACT REGISTRATION
# =========================================================

async def receive_contact(
    update,
    context,
):

    contact = update.message.contact

    user = update.effective_user

    user_id = user.id


    if user_id in users:

        await update.message.reply_text(

            "👋 Ati duraan register gooteetta.",

            reply_markup=main_menu(
                user_id
            ),

        )

        return


    if contact.user_id != user_id:

        await update.message.reply_text(

            "⚠️ Mee button Register fayyadami."

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


    REGISTER_BONUS = 50


    balances[user_id] = round(

        get_balance(user_id)
        + REGISTER_BONUS,

        2,

    )


    add_transaction(

        user_id,

        "register_bonus",

        REGISTER_BONUS,

        "completed",

        "Welcome bonus",

    )


    save_data()


    await update.message.reply_text(

        "✅ <b>REGISTRATION SUCCESSFUL!</b>\n\n"

        f"🎉 Welcome {user.first_name}!\n"

        f"🎁 Welcome Bonus: {REGISTER_BONUS} Birr\n\n"

        "💰 Bonus gara balance keetti dabalameera.",

        parse_mode="HTML",

        reply_markup=ReplyKeyboardRemove(),

    )


    await update.message.reply_text(

        "🏠 <b>MAIN MENU</b>\n\n"

        "👇 Wanta barbaadde filadhu:",

        parse_mode="HTML",

        reply_markup=main_menu(
            user_id
        ),

    )


# =========================================================
# DEPOSIT MENU
# =========================================================

async def deposit_menu(
    query,
    user_id,
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
                    f"deposit_amount_{amount}",

            )

        ])


    keyboard.append([

        InlineKeyboardButton(

            "🔙 Back",

            callback_data="back_menu",

        )

    ])


    await query.edit_message_text(

        "💰 <b>DEPOSIT</b>\n\n"

        "Amount filadhu:",

        parse_mode="HTML",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),

    )


# =========================================================
# DEPOSIT AMOUNT
# =========================================================

async def deposit_amount(
    query,
    user_id,
    amount,
):

    pending_deposits[
        user_id
    ] = {

        "amount":
            amount,

        "status":
            "waiting_screenshot",

    }


    save_data()


    await query.edit_message_text(

        "💰 <b>DEPOSIT</b>\n\n"

        f"💵 Amount: <b>{amount} Birr</b>\n\n"

        "📱 <b>Telebirr:</b>\n"

        f"<code>{TELEBIRR_NUMBER}</code>\n\n"

        "1️⃣ Lakkoofsa kana irratti kaffali.\n\n"

        "2️⃣ Screenshot ragaa kaffaltii ergi.\n\n"

        "✅ Admin ni mirkaneessa.",

        parse_mode="HTML",

    )


# =========================================================
# RECEIVE DEPOSIT PHOTO
# =========================================================

async def receive_deposit_photo(
    update,
    context,
):

    user_id = update.effective_user.id


    if user_id not in pending_deposits:

        await update.message.reply_text(

            "⚠️ Deposit jalqabiitii amount filadhu."

        )

        return


    deposit = pending_deposits[
        user_id
    ]


    if deposit.get(
        "status"
    ) != "waiting_screenshot":

        await update.message.reply_text(

            "⏳ Deposit request kee duraan ergameera."

        )

        return


    amount = deposit[
        "amount"
    ]


    photo = update.message.photo[-1]


    pending_deposits[
        user_id
    ] = {

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
                    f"approve_deposit_{user_id}",

            ),

            InlineKeyboardButton(

                "❌ REJECT",

                callback_data=
                    f"reject_deposit_{user_id}",

            ),

        ]

    ])


    await context.bot.send_photo(

        chat_id=ADMIN_ID,

        photo=photo.file_id,

        caption=(

            "💰 <b>NEW TELEBIRR DEPOSIT</b>\n\n"

            f"👤 User ID: {user_id}\n"

            f"💵 Amount: {amount} Birr\n"

            f"📱 Paid to: {TELEBIRR_NUMBER}"

        ),

        parse_mode="HTML",

        reply_markup=keyboard,

    )


    await update.message.reply_text(

        "✅ Screenshot kee fudhatame.\n\n"

        "⏳ Admin mirkaneessaa jira.",

        reply_markup=main_menu(
            user_id
        ),

    )


# =========================================================
# APPROVE DEPOSIT
# =========================================================

async def approve_deposit(
    query,
    user_id,
):

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Admin only.",
            show_alert=True,
        )

        return


    deposit = pending_deposits.get(
        user_id
    )


    if not deposit:

        await query.answer(
            "⚠️ Deposit request hin jiru.",
            show_alert=True,
        )

        return


    if deposit.get(
        "status"
    ) != "pending_admin":

        await query.answer(
            "⚠️ Deposit request kun duraan processed ta'eera.",
            show_alert=True,
        )

        return


    amount = float(
        deposit[
            "amount"
        ]
    )


    add_balance(
        user_id,
        amount,
    )


    add_transaction(
        user_id,
        "deposit",
        amount,
        "approved",
        "Telebirr",
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

        parse_mode="HTML",

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "✅ <b>DEPOSIT COMPLETED!</b>\n\n"

            f"💰 {amount} Birr balance kee irratti dabaleera.\n\n"

            f"💳 Balance: "

            f"{get_balance(user_id):.2f} Birr"

        ),

        parse_mode="HTML",

        reply_markup=main_menu(
            user_id
        ),

    )


# =========================================================
# REJECT DEPOSIT
# =========================================================

async def reject_deposit(
    query,
    user_id,
):

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Admin only.",
            show_alert=True,
        )

        return


    deposit = pending_deposits.get(
        user_id
    )


    if not deposit:

        await query.answer(
            "⚠️ Deposit request hin jiru.",
            show_alert=True,
        )

        return


    amount = deposit[
        "amount"
    ]


    del pending_deposits[
        user_id
    ]


    add_transaction(
        user_id,
        "deposit",
        amount,
        "rejected",
        "Telebirr",
    )


    save_data()


    await query.edit_message_caption(

        caption=(

            "❌ <b>DEPOSIT REJECTED</b>\n\n"

            f"👤 User ID: {user_id}\n"

            f"💰 Amount: {amount} Birr"

        ),

        parse_mode="HTML",

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "❌ <b>PAYMENT NOT ACCEPTED</b>\n\n"

            "Ragaan kaffaltii kee hin mirkanoofne."

        ),

        parse_mode="HTML",

        reply_markup=main_menu(
            user_id
        ),

    )


# =========================================================
# WITHDRAWAL START
# =========================================================

async def withdrawal_start(
    query,
    user_id,
):

    balance = get_balance(
        user_id
    )


    if balance <= 0:

        await query.edit_message_text(

            "💸 <b>WITHDRAWAL</b>\n\n"

            "⚠️ Balance kee duwwaa dha.",

            parse_mode="HTML",

            reply_markup=main_menu(
                user_id
            ),

        )

        return


    if user_id in pending_withdrawals:

        current = pending_withdrawals[
            user_id
        ]


        await query.edit_message_text(

            "⏳ <b>WITHDRAWAL PENDING</b>\n\n"

            f"💰 Amount: "
            f"{current.get('amount', 'N/A')} Birr\n"

            f"📱 Telebirr: "
            f"{current.get('phone', 'N/A')}\n\n"

            "⏳ Admin approval eeggachaa jira.",

            parse_mode="HTML",

            reply_markup=main_menu(
                user_id
            ),

        )

        return


    pending_withdrawals[
        user_id
    ] = {

        "status":
            "waiting_info",

    }


    save_data()


    await query.edit_message_text(

        "💸 <b>WITHDRAWAL</b>\n\n"

        f"💰 Balance: "
        f"<b>{balance:.2f} Birr</b>\n\n"

        "📱 Lakkoofsa Telebirr fi amount ergi.\n\n"

        "Fakkeenya:\n"

        "<code>0902640434 100</code>\n\n"

        "📌 Lakkoofsa fi amount gidduu space godhi.",

        parse_mode="HTML",

    )


# =========================================================
# PROCESS WITHDRAWAL
# =========================================================

async def process_withdrawal(
    update,
    context,
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


    text = (
        update.message.text
        or ""
    ).strip()


    parts = text.split()


    if len(parts) != 2:

        await update.message.reply_text(

            "⚠️ Format sirrii miti.\n\n"

            "Fakkeenya:\n"

            "<code>0902640434 100</code>",

            parse_mode="HTML",

        )

        return True


    phone = parts[0]


    if (
        not phone.isdigit()
        or len(phone) != 10
    ):

        await update.message.reply_text(

            "⚠️ Lakkoofsa Telebirr sirrii galchi.",

            parse_mode="HTML",

        )

        return True


    try:

        amount = float(
            parts[1]
        )

    except ValueError:

        await update.message.reply_text(

            "⚠️ Amount sirrii galchi.",

            reply_markup=main_menu(
                user_id
            ),

        )

        return True


    if amount <= 0:

        await update.message.reply_text(

            "⚠️ Amount 0 caalaa ta'uu qaba.",

            reply_markup=main_menu(
                user_id
            ),

        )

        return True


    if amount > get_balance(
        user_id
    ):

        await update.message.reply_text(

            "⚠️ Balance kee withdrawal kanaaf gahaa miti.",

            reply_markup=main_menu(
                user_id
            ),

        )

        del pending_withdrawals[
            user_id
        ]

        save_data()

        return True


    if not remove_balance(
        user_id,
        amount,
    ):

        await update.message.reply_text(

            "⚠️ Balance kee jijjiirameera. Irra deebi'i.",

            reply_markup=main_menu(
                user_id
            ),

        )

        del pending_withdrawals[
            user_id
        ]

        save_data()

        return True


    pending_withdrawals[
        user_id
    ] = {

        "status":
            "pending_admin",

        "phone":
            phone,

        "amount":
            amount,

        "user_id":
            user_id,

        "created_at":
            time.time(),

    }


    add_transaction(

        user_id,

        "withdrawal",

        amount,

        "pending",

        f"Telebirr: {phone}",

    )


    save_data()


    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ APPROVE",

                callback_data=
                    f"approve_withdrawal_{user_id}",

            ),

            InlineKeyboardButton(

                "❌ REJECT",

                callback_data=
                    f"reject_withdrawal_{user_id}",

            ),

        ]

    ])


    await context.bot.send_message(

        chat_id=ADMIN_ID,

        text=(

            "💸 <b>NEW WITHDRAWAL REQUEST</b>\n\n"

            f"👤 User ID: "
            f"<code>{user_id}</code>\n"

            f"📱 Telebirr: "
            f"<code>{phone}</code>\n"

            f"💰 Amount: "
            f"<b>{amount} Birr</b>\n\n"

            "⚠️ Maallaqni balance user irraa qabameera."

        ),

        parse_mode="HTML",

        reply_markup=keyboard,

    )


    await update.message.reply_text(

        "✅ <b>WITHDRAWAL REQUEST SENT</b>\n\n"

        f"💰 Amount: {amount} Birr\n"

        f"📱 Telebirr: {phone}\n\n"

        "⏳ Admin maallaqa ergee booda approve godha.",

        parse_mode="HTML",

        reply_markup=main_menu(
            user_id
        ),

    )


    return True


# =========================================================
# APPROVE WITHDRAWAL
# =========================================================

async def approve_withdrawal(
    query,
    user_id,
):

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Admin qofa.",
            show_alert=True,
        )

        return


    withdrawal = pending_withdrawals.get(
        user_id
    )


    if not withdrawal:

        await query.answer(
            "⚠️ Withdrawal request hin jiru.",
            show_alert=True,
        )

        return


    if withdrawal.get(
        "status"
    ) != "pending_admin":

        return


    amount = float(
        withdrawal[
            "amount"
        ]
    )

    phone = withdrawal[
        "phone"
    ]


    add_transaction(

        user_id,

        "withdrawal",

        amount,

        "approved",

        f"Telebirr: {phone}",

    )


    del pending_withdrawals[
        user_id
    ]


    save_data()


    await query.edit_message_text(

        "✅ <b>WITHDRAWAL APPROVED</b>\n\n"

        f"👤 User ID: {user_id}\n"

        f"📱 Telebirr: {phone}\n"

        f"💰 Amount: {amount} Birr",

        parse_mode="HTML",

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "✅ <b>WITHDRAWAL COMPLETED!</b>\n\n"

            f"💰 Amount: {amount} Birr\n"

            f"📱 Telebirr: {phone}\n\n"

            f"💳 Remaining balance: "
            f"{get_balance(user_id):.2f} Birr"

        ),

        parse_mode="HTML",

        reply_markup=main_menu(
            user_id
        ),

    )


# =========================================================
# REJECT WITHDRAWAL
# =========================================================

async def reject_withdrawal(
    query,
    user_id,
):

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "⛔ Admin qofa.",
            show_alert=True,
        )

        return


    withdrawal = pending_withdrawals.get(
        user_id
    )


    if not withdrawal:

        return


    amount = float(
        withdrawal[
            "amount"
        ]
    )

    phone = withdrawal[
        "phone"
    ]


    add_balance(
        user_id,
        amount,
    )


    add_transaction(

        user_id,

        "withdrawal",

        amount,

        "rejected",

        f"Refund - Telebirr: {phone}",

    )


    del pending_withdrawals[
        user_id
    ]


    save_data()


    await query.edit_message_text(

        "❌ <b>WITHDRAWAL REJECTED</b>\n\n"

        f"👤 User ID: {user_id}\n"

        f"💰 Amount: {amount} Birr\n\n"

        "💰 Maallaqni user balance isaatti deebifameera.",

        parse_mode="HTML",

    )


    await query.get_bot().send_message(

        chat_id=user_id,

        text=(

            "❌ <b>WITHDRAWAL REJECTED</b>\n\n"

            f"💰 Amount: {amount} Birr\n\n"

            "Maallaqni kee balance kee irratti deebifameera."

        ),

        parse_mode="HTML",

        reply_markup=main_menu(
            user_id
        ),

    )


# =========================================================
# BALANCE
# =========================================================

async def show_balance(
    query,
    user_id,
):

    balance = get_balance(
        user_id
    )


    await query.edit_message_text(

        "💳 <b>YOUR BALANCE</b>\n\n"

        f"💰 Balance: "
        f"<b>{balance:.2f} Birr</b>",

        parse_mode="HTML",

        reply_markup=main_menu(
            user_id
        ),

    )


# =========================================================
# HISTORY
# =========================================================

async def show_history(
    query,
    user_id,
):

    user_transactions = [

        t

        for t in transactions

        if int(
            t.get(
                "user_id",
                -1,
            )
        ) == user_id

    ]


    if not user_transactions:

        await query.edit_message_text(

            "📜 <b>HISTORY</b>\n\n"

            "No transaction history.",

            parse_mode="HTML",

            reply_markup=main_menu(
                user_id
            ),

        )

        return


    text = (
        "📜 <b>HISTORY</b>\n\n"
    )


    for transaction in user_transactions[-15:]:

        text += (

            f"🔹 "
            f"{transaction.get('type', '')}\n"

            f"💰 "
            f"{transaction.get('amount', 0)} Birr\n"

            f"📌 "
            f"{transaction.get('status', '')}\n\n"

        )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu(
            user_id
        ),

    )


# =========================================================
# WINNERS
# =========================================================

async def show_winners(
    query,
    user_id,
):

    if not winners:

        await query.edit_message_text(

            "🏆 <b>WINNERS</b>\n\n"

            "No winners yet.",

            parse_mode="HTML",

            reply_markup=main_menu(
                user_id
            ),

        )

        return


    text = (
        "🏆 <b>RECENT WINNERS</b>\n\n"
    )


    for winner in reversed(
        winners[-20:]
    ):

        text += (

            f"🏆 Game: "
            f"{winner.get('game_id', '')}\n"

            f"👤 User: "
            f"{winner.get('user_id', '')}\n"

            f"🎫 Card: "
            f"{winner.get('card_number', '')}\n"

            f"💰 Prize: "
            f"{winner.get('prize', 0)} Birr\n"

            f"👥 Winners: "
            f"{winner.get('winner_count', 1)}\n\n"

        )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu(
            user_id
        ),

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

        "2️⃣ PLAY GAME cuqi.\n\n"

        "3️⃣ Card 10 ykn 20 filadhu.\n\n"

        "4️⃣ Card ID 1 hanga 500 keessaa filadhu.\n\n"

        "5️⃣ Balance kee irraa kaffali.\n\n"

        "6️⃣ Number 1 hanga 75 waamama.\n\n"

        "7️⃣ Bingo pattern guuti.\n\n"

        "8️⃣ BINGO cuqi.\n\n"

        "🏆 Winneroota hedduu yoo qabaate prize walqixa share godha.\n\n"

        "💰 Prize = 80% customer card sales."

    )


    await query.edit_message_text(

        text,

        parse_mode="HTML",

        reply_markup=main_menu(),

    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()


    user_id = query.from_user.id

    data = query.data


    # =====================================================
    # BACK
    # =====================================================

    if data == "back_menu":

        await query.edit_message_text(

            "🏠 <b>MAIN MENU</b>\n\n"

            "👇 Wanta barbaadde filadhu:",

            parse_mode="HTML",

            reply_markup=main_menu(
                user_id
            ),

        )

        return


    # =====================================================
    # DEPOSIT
    # =====================================================

    if data == "deposit":

        await deposit_menu(
            query,
            user_id,
        )

        return


    # =====================================================
    # DEPOSIT AMOUNT
    # =====================================================

    if data.startswith(
        "deposit_amount_"
    ):

        try:

            amount = int(
                data.replace(
                    "deposit_amount_",
                    "",
                )
            )

        except Exception:

            await query.answer(
                "Amount sirrii miti.",
                show_alert=True,
            )

            return


        await deposit_amount(
            query,
            user_id,
            amount,
        )

        return


    # =====================================================
    # BALANCE
    # =====================================================

    if data == "balance":

        await show_balance(
            query,
            user_id,
        )

        return


    # =====================================================
    # HISTORY
    # =====================================================

    if data == "history":

        await show_history(
            query,
            user_id,
        )

        return


    # =====================================================
    # WINNERS
    # =====================================================

    if data == "winners":

        await show_winners(
            query,
            user_id,
        )

        return


    # =====================================================
    # HOW TO PLAY
    # =====================================================

    if data == "how_to_play":

        await how_to_play(
            query
        )

        return


    # =====================================================
    # WITHDRAWAL
    # =====================================================

    if data == "withdrawal":

        await withdrawal_start(
            query,
            user_id,
        )

        return


    # =====================================================
    # APPROVE DEPOSIT
    # =====================================================

    if data.startswith(
        "approve_deposit_"
    ):

        try:

            target_user = int(
                data.split(
                    "_"
                )[-1]
            )

        except Exception:

            return


        await approve_deposit(
            query,
            target_user,
        )

        return


    # =====================================================
    # REJECT DEPOSIT
    # =====================================================

    if data.startswith(
        "reject_deposit_"
    ):

        try:

            target_user = int(
                data.split(
                    "_"
                )[-1]
            )

        except Exception:

            return


        await reject_deposit(
            query,
            target_user,
        )

        return


    # =====================================================
    # APPROVE WITHDRAWAL
    # =====================================================

    if data.startswith(
        "approve_withdrawal_"
    ):

        try:

            target_user = int(
                data.split(
                    "_"
                )[-1]
            )

        except Exception:

            return


        await approve_withdrawal(
            query,
            target_user,
        )

        return


    # =====================================================
    # REJECT WITHDRAWAL
    # =====================================================

    if data.startswith(
        "reject_withdrawal_"
    ):

        try:

            target_user = int(
                data.split(
                    "_"
                )[-1]
            )

        except Exception:

            return


        await reject_withdrawal(
            query,
            target_user,
        )

        return


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(
    update,
    context,
):

    user_id = update.effective_user.id


    handled = await process_withdrawal(
        update,
        context,
    )


    if handled:

        return


    await update.message.reply_text(

        "🏠 <b>MAIN MENU</b>\n\n"

        "👇 Wanta barbaadde filadhu:",

        parse_mode="HTML",

        reply_markup=main_menu(
            user_id
        ),

    )


# =========================================================
# FLASK SERVER
# =========================================================

def run_flask():

    web_app.run(

        host="0.0.0.0",

        port=PORT,

        debug=False,

        use_reloader=False,

    )


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


    # =====================================================
    # FLASK
    # =====================================================

    flask_thread = threading.Thread(

        target=run_flask,

        daemon=True,

    )

    flask_thread.start()


    # =====================================================
    # TELEGRAM
    # =====================================================

    application = (

        Application

        .builder()

        .token(BOT_TOKEN)

        .build()

    )


    # =====================================================
    # START
    # =====================================================

    application.add_handler(

        CommandHandler(
            "start",
            start,
        )

    )


    # =====================================================
    # CONTACT
    # =====================================================

    application.add_handler(

        MessageHandler(

            filters.CONTACT,

            receive_contact,

        )

    )


    # =====================================================
    # PHOTO
    # =====================================================

    application.add_handler(

        MessageHandler(

            filters.PHOTO,

            receive_deposit_photo,

        )

    )


    # =====================================================
    # TEXT
    # =====================================================

    application.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            text_handler,

        )

    )


    # =====================================================
    # CALLBACK
    # =====================================================

    application.add_handler(

        CallbackQueryHandler(
            callback_handler,
        )

    )


    print(
        "================================="
    )

    print(
        "GADAA BINGO BOT STARTED"
    )

    print(
        "================================="
    )


    # =====================================================
    # START FIRST GAME
    # =====================================================

    start_new_game()


    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
