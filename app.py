import os
import json
from flask import Flask, request, render_template, redirect, url_for, jsonify
from bot import ScalpingBot

USERNAME = "MDB93"
PASSWORD = "scalping2025"

# ENV VARS (set on Render): TESTNET_API_KEY, TESTNET_API_SECRET
TESTNET_API_KEY = os.getenv("TESTNET_API_KEY", "")
TESTNET_API_SECRET = os.getenv("TESTNET_API_SECRET", "")

REAL_API_KEY = os.getenv("REAL_API_KEY", "")
REAL_API_SECRET = os.getenv("REAL_API_SECRET", "")

DEFAULT_MODE = os.getenv("DEFAULT_MODE", "DEMO").upper()  # DEMO or REALE
STAKE_DEFAULT = float(os.getenv("STAKE", "500"))

app = Flask(__name__)
bot = ScalpingBot(
    api_key=TESTNET_API_KEY if DEFAULT_MODE == "DEMO" else REAL_API_KEY,
    api_secret=TESTNET_API_SECRET if DEFAULT_MODE == "DEMO" else REAL_API_SECRET,
    testnet=(DEFAULT_MODE == "DEMO"),
    stake_usdt=STAKE_DEFAULT,
    profit_pct=0.003,
    stop_pct=-0.003
)

# ---------- auth (super light) ----------
def check_auth(u, p):
    return u == USERNAME and p == PASSWORD

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        if check_auth(u, p):
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", username=USERNAME)

# ---------- API endpoints ----------
@app.route("/api/snapshot")
def api_snapshot():
    return jsonify(bot.snapshot())

@app.route("/api/start", methods=["POST"])
def api_start():
    bot.set_running(True)
    return jsonify({"ok": True})

@app.route("/api/stop", methods=["POST"])
def api_stop():
    bot.set_running(False)
    return jsonify({"ok": True})

@app.route("/api/set_symbol", methods=["POST"])
def api_set_symbol():
    symbol = request.json.get("symbol", "BTCUSDT").upper()
    ok = bot.set_symbol(symbol)
    return jsonify({"ok": ok, "symbol": symbol})

@app.route("/api/set_stake", methods=["POST"])
def api_set_stake():
    stake = float(request.json.get("stake", 500))
    bot.set_stake(stake)
    return jsonify({"ok": True, "stake": stake})

@app.route("/api/set_tp_sl", methods=["POST"])
def api_set_tp_sl():
    tp = float(request.json.get("tp", 0.003))
    sl = float(request.json.get("sl", -0.003))
    bot.set_tp_sl(tp, sl)
    return jsonify({"ok": True, "tp": tp, "sl": sl})

@app.route("/api/mode", methods=["POST"])
def api_mode():
    mode = request.json.get("mode", "DEMO").upper()
    if mode == "DEMO":
        bot.set_mode(True, api_key=os.getenv("TESTNET_API_KEY",""), api_secret=os.getenv("TESTNET_API_SECRET",""))
    else:
        ak = request.json.get("api_key") or os.getenv("REAL_API_KEY","")
        sk = request.json.get("api_secret") or os.getenv("REAL_API_SECRET","")
        bot.set_mode(False, api_key=ak, api_secret=sk)
    return jsonify({"ok": True, "mode": mode})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
