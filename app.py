
from flask import Flask, send_from_directory, request
import sqlite3
import time
import os
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, Update

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://tokendar-app.onrender.com"
)

DB = "mining.db"
RATE_PER_HOUR = 0.0985
MINING_HOURS = 4

dp = Dispatcher()


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL NOT NULL DEFAULT 0,
            mining_started INTEGER NOT NULL DEFAULT 0,
            referral_id INTEGER
        )
    """)
    con.commit()
    con.close()


def get_user(tg_user, referral_id=None):
    con = db()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (tg_user.id,)
    ).fetchone()

    if not row:
        con.execute(
            "INSERT INTO users(id,username,referral_id) VALUES(?,?,?)",
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


def update_mining(user_id):
    con = db()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not row:
        con.close()
        return

    now = int(time.time())

    if row["mining_started"]:
        elapsed = max(0, now - row["mining_started"])

        earned = min(
            elapsed / 3600,
            MINING_HOURS
        ) * RATE_PER_HOUR

        con.execute(
            """
            UPDATE users
            SET balance=balance+?,
                mining_started=?
            WHERE id=?
            """,
            (
                earned,
                now if elapsed >= MINING_HOURS * 3600
                else row["mining_started"],
                user_id
            )
        )

        con.commit()

    con.close()


@dp.message(CommandStart())
async def start(message: types.Message):

    ref = None

    parts = message.text.split(maxsplit=1)

    if (
        len(parts) == 2
        and parts[1].isdigit()
        and int(parts[1]) != message.from_user.id
    ):
        ref = int(parts[1])

    get_user(message.from_user, ref)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⛏️ Open Mining",
                    web_app=WebAppInfo(url=WEBAPP_URL)
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
        reply_markup=kb
    )


@dp.message(Command("balance"))
async def balance(message: types.Message):

    get_user(message.from_user)

    update_mining(message.from_user.id)

    row = get_user(message.from_user)

    await message.answer(
        f"💰 Balance: {row['balance']:.4f} TokenDar"
    )


@app.get("/")
def index():
    return send_from_directory(".", "index.html")


@app.get("/style.css")
def style():
    return send_from_directory(".", "style.css")


@app.get("/api/user/<int:user_id>")
def user(user_id):

    con = db()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    con.close()

    if not row:
        return {"error": "user_not_found"}, 404

    return {
        "id": row["id"],
        "username": row["username"],
        "balance": row["balance"],
        "mining_started": row["mining_started"]
    }


@app.post("/api/start/<int:user_id>")
def start_mining(user_id):

    now = int(time.time())

    con = db()

    con.execute(
        """
        UPDATE users
        SET mining_started=?
        WHERE id=? AND mining_started=0
        """,
        (now, user_id)
    )

    con.commit()
    con.close()

    return {"ok": True}


@app.post("/api/claim/<int:user_id>")
def claim(user_id):

    con = db()

    row = con.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not row:
        con.close()
        return {"error": "user_not_found"}, 404

    now = int(time.time())

    if not row["mining_started"]:
        con.close()
        return {"error": "mining_not_started"}, 400

    elapsed = min(
        max(0, now - row["mining_started"]),
        4 * 3600
    )

    earned = elapsed / 3600 * RATE_PER_HOUR

    con.execute(
        """
        UPDATE users
        SET balance=balance+?,
            mining_started=0
        WHERE id=?
        """,
        (earned, user_id)
    )

    con.commit()

    new_balance = con.execute(
        "SELECT balance FROM users WHERE id=?",
        (user_id,)
    ).fetchone()[0]

    con.close()

    return {
        "ok": True,
        "earned": earned,
        "balance": new_balance
    }


@app.post("/telegram/webhook")
def telegram_webhook():

    if not BOT_TOKEN:
        return {"error": "BOT_TOKEN is not configured"}, 500

    data = request.get_json(silent=True)

    if not data:
        return {"error": "invalid update"}, 400

    async def process_update():

        bot = Bot(BOT_TOKEN)

        try:
            update = Update.model_validate(data)
            await dp.feed_update(bot, update)
        finally:
            await bot.session.close()

    asyncio.run(process_update())

    return {"ok": True}


init_db()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080"))
    )
