import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Strategy Backtesting Dashboard", layout="wide")

# --- Custom CSS for larger sidebar fonts ---
st.markdown("""
    <style>
    section[data-testid="stSidebar"] * {
        font-size: 20px !important;
    }
    section[data-testid="stSidebar"] .stSlider > div {
        height: auto !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Strategy Backtesting Dashboard")

# --- Tabs ---
tab1, tab2 = st.tabs(["📈 Chart", "📋 Summary"])

# --- Sidebar Controls ---
st.sidebar.header("Strategy Settings")
symbol = st.sidebar.selectbox("Stock Symbol", ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"])
period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=1)
interval = st.sidebar.selectbox("Interval", ["15m", "1h", "1d"], index=1)

fast_ma = st.sidebar.slider("Fast MA", 3, 20, 5)
slow_ma = st.sidebar.slider("Slow MA", 10, 50, 20)
rsi_period = st.sidebar.slider("RSI Period", 7, 21, 14)
rsi_buy = st.sidebar.slider("RSI Buy Threshold", 10, 50, 30)
rsi_sell = st.sidebar.slider("RSI Sell Threshold", 50, 90, 70)

# --- Download Data ---
st.write(f"Pulling historical data for {symbol}...")
data = yf.download(symbol, period=period, interval=interval)
data.dropna(inplace=True)

# --- Calculate Indicators ---
data["Fast_MA"] = data["Close"].rolling(window=fast_ma).mean()
data["Slow_MA"] = data["Close"].rolling(window=slow_ma).mean()

# RSI calculation
delta = data["Close"].diff()
gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
loss = -delta.where(delta < 0, 0).rolling(rsi_period).mean()
rs = gain / loss
data["RSI"] = 100 - (100 / (1 + rs))

# --- Generate Buy/Sell Signals ---
buy_signals = []
sell_signals = []
trades = []

for i in range(1, len(data)):
    prev = data.iloc[i - 1]
    row = data.iloc[i]

    prev_fast = float(prev["Fast_MA"])
    prev_slow = float(prev["Slow_MA"])
    curr_rsi = float(row["RSI"])
    curr_price = float(row["Close"])
    date = row.name

    if prev_fast > prev_slow and curr_rsi < rsi_buy:
        buy_signals.append((date, curr_price))
        trades.append({"Type": "Buy", "Date": date, "Price": curr_price})
    elif prev_fast < prev_slow and curr_rsi > rsi_sell:
        sell_signals.append((date, curr_price))
        trades.append({"Type": "Sell", "Date": date, "Price": curr_price})

# --- Tab 1: Chart ---
with tab1:
    fig, ax = plt.subplots(figsize=(24, 12))
    ax.plot(data.index, data["Close"], label="Price", color="orange", linewidth=2)
    ax.plot(data.index, data["Fast_MA"], label=f"MA{fast_ma}", linestyle="--")
    ax.plot(data.index, data["Slow_MA"], label=f"MA{slow_ma}", linestyle=":")

    for date, price in buy_signals:
        ax.scatter(date, price, marker="^", color="green", s=120, label="Buy")
    for date, price in sell_signals:
        ax.scatter(date, price, marker="v", color="red", s=120, label="Sell")

    ax.set_title(f"{symbol} Price with MA/RSI Strategy", fontsize=24)
    ax.set_ylabel("Price ($)", fontsize=18)
    ax.grid(True)
    ax.legend(fontsize=14)
    st.pyplot(fig)

# --- Tab 2: Summary ---
with tab2:
    st.subheader("📋 Strategy Summary")
    st.write(f"Total Buy Signals: {len(buy_signals)}")
    st.write(f"Total Sell Signals: {len(sell_signals)}")

    # Calculate performance metrics
    buy_prices = [t["Price"] for t in trades if t["Type"] == "Buy"]
    sell_prices = [t["Price"] for t in trades if t["Type"] == "Sell"]
    trade_pairs = list(zip(buy_prices, sell_prices))

    profits = [round(sell - buy, 2) for buy, sell in trade_pairs if sell > buy]
    losses = [round(sell - buy, 2) for buy, sell in trade_pairs if sell < buy]
    total_trades = len(trade_pairs)
    profitable_trades = len(profits)
    losing_trades = len(losses)

    if total_trades > 0:
        win_rate = round((profitable_trades / total_trades) * 100, 2)
        avg_profit = round(sum(profits) / len(profits), 2) if profits else 0
        avg_loss = round(sum(losses) / len(losses), 2) if losses else 0
        total_return = round(sum(profits + losses), 2)

        st.markdown("### 🧮 Performance Metrics")
        st.write(f"Total Trades: {total_trades}")
        st.write(f"Winning Trades: {profitable_trades}")
        st.write(f"Losing Trades: {losing_trades}")
        st.write(f"Win Rate: {win_rate}%")
        st.write(f"Average Profit per Winning Trade: ${avg_profit}")
        st.write(f"Average Loss per Losing Trade: ${avg_loss}")
        st.write(f"Net Return from All Trades: ${total_return}")
    else:
        st.info("No complete trade pairs (Buy → Sell) found for performance analysis.")
