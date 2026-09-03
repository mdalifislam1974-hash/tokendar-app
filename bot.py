import os
import sqlite3
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://YOUR-DOMAIN.example/app")

DB = "mining.db"
RATE_PER_HOUR = 0.0985
MINING_HOURS = 4

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT,
        balance REAL NOT NULL DEFAULT 0,
        mining_started INTEGER NOT NULL DEFAULT 0,
        referral_id INTEGER
    )""")
    con.commit()
    con.close()

def get_user(tg_user, referral_id=None):
    con = db()
    row = con.execute("SELECT * FROM users WHERE id=?", (tg_user.id,)).fetchone()
    if not row:
        con.execute(
            "INSERT INTO users(id,username,referral_id) VALUES(?,?,?)",
            (tg_user.id, tg_user.username or "", referral_id)
        )
        con.commit()
        row = con.execute("SELECT * FROM users WHERE id=?", (tg_user.id,)).fetchone()
    con.close()
    return row

def update_mining(user_id):
    con = db()
    row = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        con.close()
        return
    now = int(time.time())
    if row["mining_started"]:
        elapsed = max(0, now - row["mining_started"])
        earned = min(elapsed / 3600, MINING_HOURS) * RATE_PER_HOUR
        # Keep the balance live while mining.
        con.execute("UPDATE users SET balance=balance+?, mining_started=? WHERE id=?",
                    (earned, now if elapsed >= MINING_HOURS*3600 else row["mining_started"], user_id))
        con.commit()
    con.close()

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: types.Message):
    ref = None
    parts = message.text.split(maxsplit=1)
    if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) != message.from_user.id:
        ref = int(parts[1])
    get_user(message.from_user, ref)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛏️ Open Mining", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    await message.answer(
        "🚀 Welcome to TokenDar Mining!\n\n"
        "This demo uses reward points, not real cryptocurrency mining.\n"
        "Open the Mini App to start mining and claim points.",
        reply_markup=kb
    )

@dp.message(Command("balance"))
async def balance(message: types.Message):
    get_user(message.from_user)
    update_mining(message.from_user.id)
    row = get_user(message.from_user)
    await message.answer(f"💰 Balance: {row['balance']:.4f} TokenDar")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
