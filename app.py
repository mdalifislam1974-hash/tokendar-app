from flask import Flask, send_from_directory, request
import sqlite3
import time
import os
import asyncio
import json
from urllib.request import Request, urlopen

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    Update
)


app = Flask(__name__)


# ==========================================
# SETTINGS
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://tokendar-app.onrender.com"
)

WEBHOOK_URL = os.getenv(
    "WEBHOOK_URL",
    "https://tokendar-app.onrender.com/telegram/webhook"
)

DB = "mining.db"

# Demo reward-points system
RATE_PER_HOUR = 0.0985
MINING_HOURS = 4
MINING_SECONDS = MINING_HOURS * 3600


dp = Dispatcher()


# ==========================================
# DATABASE
# ==========================================

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():

    con = db()

    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL NOT NULL DEFAULT 0,
            mining_started INTEGER NOT NULL DEFAULT 0,
            referral_id INTEGER
        )
    """)

    con.commit()
    con.close()


# ==========================================
# USER
# ==========================================

def get_user(tg_user, referral_id=None):

    con = db()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (tg_user.id,)
    ).fetchone()

    if not row:

        con.execute(
            """
            INSERT INTO users (
                id,
                username,
                referral_id
            )
            VALUES (?, ?, ?)
            """,
            (
                tg_user.id,
                tg_user.username or "",
                referral_id
            )
        )

        con.commit()

        row = con.execute(
            "SELECT * FROM users WHERE id=?",
            (tg_user.id,)
        ).fetchone()

    con.close()

    return row


# ==========================================
# TELEGRAM /START
# ==========================================

@dp.message(CommandStart())
async def start(message: types.Message):

    referral_id = None

    parts = message.text.split(maxsplit=1)

    if (
        len(parts) == 2
        and parts[1].isdigit()
        and int(parts[1]) != message.from_user.id
    ):
        referral_id = int(parts[1])

    get_user(
        message.from_user,
        referral_id
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⛏️ Open Mining",
                    web_app=WebAppInfo(
                        url=WEBAPP_URL
                    )
                )
            ]
        ]
    )

    await message.answer(
        "🚀 Welcome to TokenDar Mining!\n\n"
        "This demo uses reward points, "
        "not real cryptocurrency mining.\n\n"
        "Open the Mini App to start mining "
        "and claim points.",
        reply_markup=keyboard
    )


# ==========================================
# TELEGRAM /BALANCE
# ==========================================

@dp.message(Command("balance"))
async def balance(message: types.Message):

    row = get_user(message.from_user)

    await message.answer(
        f"💰 Balance: "
        f"{row['balance']:.4f} TokenDar"
    )


# ==========================================
# WEBSITE
# ==========================================

@app.get("/")
def index():

    return send_from_directory(
        ".",
        "index.html"
    )


@app.get("/style.css")
def style():

    return send_from_directory(
        ".",
        "style.css"
    )


# ==========================================
# USER API
# ==========================================

@app.get("/api/user/<int:user_id>")
def user(user_id):

    con = db()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    con.close()

    if not row:

        return {
            "error": "user_not_found"
        }, 404

    now = int(time.time())

    mining_started = row["mining_started"]

    earned = 0.0
    remaining = 0

    if mining_started:

        elapsed = max(
            0,
            now - mining_started
        )

        elapsed = min(
            elapsed,
            MINING_SECONDS
        )

        earned = (
            elapsed / 3600
        ) * RATE_PER_HOUR

        remaining = max(
            0,
            MINING_SECONDS - elapsed
        )

    return {
        "id": row["id"],
        "username": row["username"],
        "balance": row["balance"],
        "mining_started": mining_started,
        "earned": earned,
        "remaining": remaining
    }


# ==========================================
# START MINING
# ==========================================

@app.post("/api/start/<int:user_id>")
def start_mining(user_id):

    con = db()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not row:

        con.close()

        return {
            "error": "user_not_found"
        }, 404

    # If mining is already active,
    # DO NOT restart the timer.
    if row["mining_started"]:

        mining_started = row["mining_started"]

    else:

        mining_started = int(time.time())

        con.execute(
            """
            UPDATE users
            SET mining_started=?
            WHERE id=?
            """,
            (
                mining_started,
                user_id
            )
        )

        con.commit()

    con.close()

    return {
        "ok": True,
        "mining_started": mining_started
    }


# ==========================================
# CLAIM
# ==========================================

@app.post("/api/claim/<int:user_id>")
def claim(user_id):

    con = db()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not row:

        con.close()

        return {
            "error": "user_not_found"
        }, 404

    mining_started = row["mining_started"]

    if not mining_started:

        con.close()

        return {
            "error": "mining_not_started"
        }, 400

    now = int(time.time())

    elapsed = max(
        0,
        now - mining_started
    )

    # Maximum mining time = 4 hours
    elapsed = min(
        elapsed,
        MINING_SECONDS
    )

    earned = (
        elapsed / 3600
    ) * RATE_PER_HOUR

    new_balance = (
        row["balance"] + earned
    )

    # Claim once, then stop this mining session.
    con.execute(
        """
        UPDATE users
        SET balance=?,
            mining_started=0
        WHERE id=?
        """,
        (
            new_balance,
            user_id
        )
    )

    con.commit()

    con.close()

    return {
        "ok": True,
        "earned": earned,
        "balance": new_balance
    }


# ==========================================
# TELEGRAM WEBHOOK
# ==========================================

@app.post("/telegram/webhook")
def telegram_webhook():

    if not BOT_TOKEN:

        return {
            "error": "BOT_TOKEN is not configured"
        }, 500

    data = request.get_json(
        silent=True
    )

    if not data:

        return {
            "error": "invalid update"
        }, 400

    async def process_update():

        bot = Bot(BOT_TOKEN)

        try:

            update = Update.model_validate(
                data
            )

            await dp.feed_update(
                bot,
                update
            )

        finally:

            await bot.session.close()

    asyncio.run(
        process_update()
    )

    return {
        "ok": True
    }


# ==========================================
# SET TELEGRAM WEBHOOK
# ==========================================

def set_webhook():

    if not BOT_TOKEN:
        return

    url = (
        "https://api.telegram.org/"
        f"bot{BOT_TOKEN}/setWebhook"
    )

    payload = json.dumps({
        "url": WEBHOOK_URL
    }).encode()

    req = Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json"
        }
    )

    try:

        with urlopen(
            req,
            timeout=10
        ) as response:

            print(
                "Webhook:",
                response.read().decode()
            )

    except Exception as e:

        print(
            "Webhook setup failed:",
            e
        )


# ==========================================
# INITIALIZE
# ==========================================

init_db()
set_webhook()


# ==========================================
# LOCAL RUN
# ==========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "8080"
            )
        )
    )
