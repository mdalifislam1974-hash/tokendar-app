from flask import Flask, send_from_directory
import sqlite3, time, os

app = Flask(__name__, static_folder="web")

def db():
    con = sqlite3.connect("mining.db")
    con.row_factory = sqlite3.Row
    return con

@app.get("/")
def index():
    return send_from_directory(".", "index.html")
@app.get("/style.css")
def style():
    return send_from_directory(".", "style.css")
@app.get("/api/user/<int:user_id>")
def user(user_id):
    con = db()
    row = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
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
def start(user_id):
    now = int(time.time())
    con = db()
    con.execute("UPDATE users SET mining_started=? WHERE id=? AND mining_started=0",
                (now, user_id))
    con.commit()
    con.close()
    return {"ok": True}

@app.post("/api/claim/<int:user_id>")
def claim(user_id):
    # Demo claim endpoint. In production, validate Telegram WebApp initData
    # server-side before accepting user_id.
    con = db()
    row = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        con.close()
        return {"error": "user_not_found"}, 404

    now = int(time.time())
    if not row["mining_started"]:
        con.close()
        return {"error": "mining_not_started"}, 400

    elapsed = min(max(0, now - row["mining_started"]), 4 * 3600)
    earned = elapsed / 3600 * 0.0985
    con.execute("UPDATE users SET balance=balance+?, mining_started=0 WHERE id=?",
                (earned, user_id))
    con.commit()
    new_balance = con.execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()[0]
    con.close()
    return {"ok": True, "earned": earned, "balance": new_balance}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
