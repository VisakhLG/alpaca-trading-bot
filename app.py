import os
import json
import streamlit as st
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST
from datetime import datetime
import pandas as pd

# Load environment variables
load_dotenv()
API_KEY = os.getenv("PKTLY0I42V66RGJO36WM")
API_SECRET = os.getenv("x8dMaTGxYRwCN3TzQaNX5YH1WryRG8mE0JAjQ7Nl")
BASE_URL = os.getenv("https://paper-api.alpaca.markets")

# Initialize API
api = REST(API_KEY, API_SECRET, BASE_URL)

# Set Streamlit UI layout
st.set_page_config(page_title="Alpaca Trading Bot", layout="wide")
st.markdown("""
    <style>
        html, body, [class*="css"]  {
            font-size: 20px !important;
        }
        .block-container {
            padding-top: 3rem;
            padding-bottom: 3rem;
            max-width: 100%;
        }
        .log-box {
            white-space: pre-wrap;
            font-size: 16px;
            padding: 15px;
            border: 2px solid #ccc;
            background: #f4f4f4;
            overflow-y: auto;
            height: 300px;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar layout
st.sidebar.title("📋 Menu")
tabs = st.sidebar.radio("Navigation", ["📊 Trading Panel", "📉 Performance", "⚙️ Strategy Settings"])

# --- Account Info ---
st.sidebar.subheader("Account Info")
try:
    account = api.get_account()
    st.sidebar.success("✅ API Connected")
    st.sidebar.write("**Status:**", account.status)
    st.sidebar.write("**Equity:** ${:,.2f}".format(float(account.equity)))
    st.sidebar.write("**Buying Power:** ${:,.2f}".format(float(account.buying_power)))
except Exception as e:
    st.sidebar.error(f"API Error: {e}")
    st.stop()

# --- Symbol Selector ---
symbol = st.sidebar.selectbox("Select Symbol", ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"])

# --- Main Panel ---
if tabs == "📊 Trading Panel":
    st.header(f"📈 {symbol} Live Chart (via TradingView)")

    # TradingView widget
    tv_height = st.slider("Chart Height", 300, 800, 500)
    st.components.v1.html(f"""
        <iframe src="https://s.tradingview.com/widgetembed/?symbol=NASDAQ:{symbol}&interval=15&theme=light"
                width="100%" height="{tv_height}" frameborder="0" allowtransparency="true" scrolling="no"></iframe>
    """, height=tv_height + 20)

    # Live price
    try:
        latest_quote = api.get_latest_trade(symbol)
        current_price = float(latest_quote.price)
        st.markdown(f"### 💵 Current Price: **${current_price:.2f}**")
    except Exception as e:
        st.warning(f"Price fetch error: {e}")

    # Trade Controls
    st.subheader("💼 Trade Controls")
    col1, col2 = st.columns(2)

    with col1:
        if st.button(f"Buy 1 {symbol} @ Market"):
            try:
                api.submit_order(symbol=symbol, qty=1, side="buy", type="market", time_in_force="gtc")
                st.success("✅ Buy market order sent.")
            except Exception as e:
                st.error(f"Buy error: {e}")

    with col2:
        if st.button(f"Sell 1 {symbol} @ Market"):
            try:
                api.submit_order(symbol=symbol, qty=1, side="sell", type="market", time_in_force="gtc")
                st.success("✅ Sell market order sent.")
            except Exception as e:
                st.error(f"Sell error: {e}")

    # Limit Order
    with st.expander("➕ Place Limit Order"):
        side = st.selectbox("Order Type", ["buy", "sell"])
        limit_price = st.number_input("Limit Price ($)", min_value=0.0, step=0.1)
        qty = st.number_input("Quantity", min_value=1, step=1)
        if st.button("Submit Limit Order"):
            try:
                api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type="limit",
                    time_in_force="gtc",
                    limit_price=limit_price
                )
                st.success(f"{side.title()} limit order for {qty} {symbol} at ${limit_price} placed.")
            except Exception as e:
                st.error(f"Limit order error: {e}")

    # Open Positions
    st.subheader("📂 Open Positions")
    try:
        positions = api.list_positions()
        if positions:
            data = []
            for p in positions:
                data.append({
                    "Symbol": p.symbol,
                    "Qty": p.qty,
                    "Market Value": float(p.market_value),
                    "Unrealized P/L": float(p.unrealized_pl)
                })
            df = pd.DataFrame(data)
            st.dataframe(df)
        else:
            st.info("No open positions.")
    except Exception as e:
        st.warning(f"Position load error: {e}")

elif tabs == "📉 Performance":
    st.header("📊 Performance Tracker")
    try:
        activities = api.get_activities()
        trade_data = [a for a in activities if a.activity_type == 'FILL' and hasattr(a, 'price')]
        if trade_data:
            df_perf = pd.DataFrame([{
                "Symbol": getattr(t, 'symbol', 'N/A'),
                "Side": t.side,
                "Qty": float(t.qty),
                "Price": float(t.price),
                "Time": t.transaction_time
            } for t in trade_data])
            df_perf = df_perf.sort_values("Time")
            trades_grouped = df_perf.groupby("Symbol")
            results = []
            for symbol, group in trades_grouped:
                buys = group[group["Side"] == "buy"]
                sells = group[group["Side"] == "sell"]
                profit = sells["Price"].sum() - buys["Price"].sum()
                results.append({"Symbol": symbol, "Total P/L": round(profit, 2)})
            st.dataframe(pd.DataFrame(results))
        else:
            st.info("No trade history available.")
    except Exception as e:
        st.warning(f"Performance error: {e}")

elif tabs == "⚙️ Strategy Settings":
    st.header("⚙️ Strategy Settings")
    settings_path = "settings.json"

    if os.path.exists(settings_path):
        with open(settings_path, "r") as f:
            settings = json.load(f)
    else:
        settings = {}

    strategy = st.selectbox("Select Strategy", ["ma_rsi_combo", "bollinger_rsi", "pairs_zscore"], index=0)

    if strategy == "ma_rsi_combo":
        st.subheader("MA + RSI Settings")
        fast_ma = st.number_input("Fast MA", 3, 20, settings.get("fast_ma", 5))
        slow_ma = st.number_input("Slow MA", 10, 100, settings.get("slow_ma", 20))
        rsi_period = st.number_input("RSI Period", 7, 30, settings.get("rsi_period", 14))
        rsi_buy = st.number_input("RSI Buy Threshold", 10, 50, settings.get("rsi_buy", 30))
        rsi_sell = st.number_input("RSI Sell Threshold", 50, 90, settings.get("rsi_sell", 70))

        settings.update({
            "fast_ma": fast_ma,
            "slow_ma": slow_ma,
            "rsi_period": rsi_period,
            "rsi_buy": rsi_buy,
            "rsi_sell": rsi_sell
        })

    elif strategy == "bollinger_rsi":
        st.subheader("Bollinger + RSI Settings")
        window = st.number_input("Bollinger Window", 10, 50, settings.get("bollinger_window", 20))
        std = st.number_input("Std Dev", 1, 4, settings.get("bollinger_std_dev", 2))
        rsi_thresh = st.number_input("RSI Filter Threshold", 10, 50, settings.get("bollinger_rsi_thresh", 35))

        settings.update({
            "bollinger_window": window,
            "bollinger_std_dev": std,
            "bollinger_rsi_thresh": rsi_thresh
        })

    elif strategy == "pairs_zscore":
        st.subheader("Pairs Trading Settings")
        symbol1 = st.text_input("Symbol 1", settings.get("pairs", {}).get("symbols", ["AAPL", "MSFT"])[0])
        symbol2 = st.text_input("Symbol 2", settings.get("pairs", {}).get("symbols", ["AAPL", "MSFT"])[1])
        lookback = st.number_input("Lookback Days", 5, 30, settings.get("pairs", {}).get("lookback_days", 15))
        entry_z = st.number_input("Entry Z-score", 1.0, 3.0, settings.get("pairs", {}).get("entry_zscore", 2.0))
        exit_z = st.number_input("Exit Z-score", 0.1, 2.0, settings.get("pairs", {}).get("exit_zscore", 0.5))

        settings["pairs"] = {
            "symbols": [symbol1.upper(), symbol2.upper()],
            "lookback_days": lookback,
            "entry_zscore": entry_z,
            "exit_zscore": exit_z
        }

    settings["strategy"] = strategy

    if st.button("💾 Save Strategy Settings"):
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=4)
        st.success("Settings saved.")

# --- Bot Log Viewer ---
st.subheader("🪵 Bot Logs")
log_path = os.path.join(os.getcwd(), "bot_log.txt")
if os.path.exists(log_path):
    with open(log_path, "r") as f:
        logs = f.read()
    st.markdown(f'<div class="log-box">{logs}</div>', unsafe_allow_html=True)
else:
    st.info("No bot log file found yet.")
