import os
import json
from dotenv import load_dotenv
import pandas as pd
import yfinance as yf
from datetime import datetime
from alpaca_trade_api.rest import REST
import requests
import pytz
import numpy as np

# --- Market Hours Check ---
def is_market_open():
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    return now.weekday() < 5 and datetime.strptime("09:30", "%H:%M").time() <= now.time() <= datetime.strptime("16:00", "%H:%M").time()

if not is_market_open():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Market is closed. Bot will not run.")
    exit()

# --- Load Environment Variables ---
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Load Strategy Settings from JSON ---
settings_path = "settings.json"
if os.path.exists(settings_path):
    with open(settings_path, "r") as f:
        settings = json.load(f)
else:
    settings = {}

strategy = settings.get("strategy", "ma_rsi_combo")

# --- Initialize Alpaca API ---
api = REST(API_KEY, API_SECRET, BASE_URL)

# --- Notification Functions ---
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print("Telegram error:", response.text)
    except Exception as e:
        print(f"Telegram send failed: {e}")

def sound_alert(message="Trade executed"):
    os.system(f'say "{message}"')

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open("bot_log.txt", "a") as f:
        f.write(full_message + "\n")

# --- STRATEGY: MA + RSI COMBO ---
def ma_rsi_combo(symbol):
    df = yf.download(symbol, period="5d", interval="15m", auto_adjust=True)
    if df.empty: return None

    fast_ma = settings.get("fast_ma", 5)
    slow_ma = settings.get("slow_ma", 20)
    rsi_period = settings.get("rsi_period", 14)
    rsi_buy = settings.get("rsi_buy", 30)
    rsi_sell = settings.get("rsi_sell", 70)

    df["Fast_MA"] = df["Close"].rolling(window=fast_ma).mean()
    df["Slow_MA"] = df["Close"].rolling(window=slow_ma).mean()
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
    loss = -delta.where(delta < 0, 0).rolling(rsi_period).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    fast_prev = df["Fast_MA"].iloc[-2]
    slow_prev = df["Slow_MA"].iloc[-2]
    rsi_now = df["RSI"].iloc[-1]

    if fast_prev > slow_prev and rsi_now < rsi_buy:
        return "buy"
    elif fast_prev < slow_prev and rsi_now > rsi_sell:
        return "sell"
    return None

# --- STRATEGY: Bollinger Band + RSI ---
def bollinger_rsi(symbol):
    df = yf.download(symbol, period="5d", interval="15m", auto_adjust=True)
    if df.empty: return None

    window = settings.get("bollinger_window", 20)
    std_dev = settings.get("bollinger_std_dev", 2)
    rsi_thresh = settings.get("bollinger_rsi_thresh", 35)
    rsi_period = settings.get("rsi_period", 14)

    df["MA"] = df["Close"].rolling(window=window).mean()
    df["STD"] = df["Close"].rolling(window=window).std()
    df["Upper"] = df["MA"] + std_dev * df["STD"]
    df["Lower"] = df["MA"] - std_dev * df["STD"]

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
    loss = -delta.where(delta < 0, 0).rolling(rsi_period).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    price = df["Close"].iloc[-1]
    rsi_now = df["RSI"].iloc[-1]

    if price < df["Lower"].iloc[-1] and rsi_now < rsi_thresh:
        return "buy"
    elif price > df["Upper"].iloc[-1] and rsi_now > 100 - rsi_thresh:
        return "sell"
    return None

# --- STRATEGY: Pairs Trading Z-Score ---
def pairs_zscore():
    pair = settings.get("pairs", {}).get("symbols", ["AAPL", "MSFT"])
    lookback = settings.get("pairs", {}).get("lookback_days", 15)
    entry_z = settings.get("pairs", {}).get("entry_zscore", 2.0)
    exit_z = settings.get("pairs", {}).get("exit_zscore", 0.5)

    df1 = yf.download(pair[0], period=f"{lookback + 5}d", interval="1h")["Close"]
    df2 = yf.download(pair[1], period=f"{lookback + 5}d", interval="1h")["Close"]
    df = pd.DataFrame({"x": df1, "y": df2}).dropna()

    spread = df["x"] - df["y"]
    mean = spread.rolling(window=lookback).mean()
    std = spread.rolling(window=lookback).std()
    zscore = (spread - mean) / std

    z_now = zscore.iloc[-1]
    if z_now > entry_z:
        return pair[0], "sell", pair[1], "buy"
    elif z_now < -entry_z:
        return pair[0], "buy", pair[1], "sell"
    elif abs(z_now) < exit_z:
        return "exit"
    return None

# --- MAIN BOT EXECUTION ---
def execute_trade(symbol, action):
    try:
        api.submit_order(symbol=symbol, qty=1, side=action, type="market", time_in_force="gtc")
        msg = f"📈 {symbol.upper()} {action.upper()} executed."
        send_telegram(msg)
        sound_alert(f"{symbol} {action} executed")
        log(msg)
    except Exception as e:
        log(f"Trade error for {symbol}: {e}")

if strategy == "ma_rsi_combo":
    for symbol in ["AAPL", "MSFT", "GOOGL"]:
        signal = ma_rsi_combo(symbol)
        log(f"{symbol} signal: {signal}")
        if signal:
            execute_trade(symbol, signal)

elif strategy == "bollinger_rsi":
    for symbol in ["AAPL", "MSFT", "GOOGL"]:
        signal = bollinger_rsi(symbol)
        log(f"{symbol} signal: {signal}")
        if signal:
            execute_trade(symbol, signal)

elif strategy == "pairs_zscore":
    result = pairs_zscore()
    if result == "exit":
        log("Z-score exited. No action.")
    elif result:
        sym1, act1, sym2, act2 = result
        log(f"Pairs signal: {sym1}-{act1}, {sym2}-{act2}")
        execute_trade(sym1, act1)
        execute_trade(sym2, act2)

log("🤖 Bot run complete.")
