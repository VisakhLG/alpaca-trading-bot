# backtest_engine.py

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# --- Strategy Config ---
FAST_MA = 5
SLOW_MA = 20
RSI_PERIOD = 14
RSI_BUY = 30
RSI_SELL = 70

SYMBOL = "AAPL"
PERIOD = "3mo"
INTERVAL = "1h"

# --- Load Historical Data ---
print(f"📥 Downloading data for {SYMBOL}...")
data = yf.download(SYMBOL, period=PERIOD, interval=INTERVAL)
data.dropna(inplace=True)

# --- Indicators ---
data["Fast_MA"] = data["Close"].rolling(FAST_MA).mean()
data["Slow_MA"] = data["Close"].rolling(SLOW_MA).mean()
delta = data["Close"].diff()
gain = delta.where(delta > 0, 0).rolling(RSI_PERIOD).mean()
loss = -delta.where(delta < 0, 0).rolling(RSI_PERIOD).mean()
rs = gain / loss
data["RSI"] = 100 - (100 / (1 + rs))

# --- Backtest Loop ---
position = None
entry_price = 0
trades = []

for i in range(1, len(data)):
    row = data.iloc[i]
    prev = data.iloc[i-1]

    # Buy Condition
    if position is None:
        if (
            prev["Fast_MA"] < prev["Slow_MA"] and row["Fast_MA"] > row["Slow_MA"]
            and row["RSI"] < RSI_BUY
        ):
            position = "long"
            entry_price = row["Close"]
            trades.append({"Date": row.name, "Action": "Buy", "Price": row["Close"]})

    # Sell Condition
    elif position == "long":
        if (
            prev["Fast_MA"] > prev["Slow_MA"] and row["Fast_MA"] < row["Slow_MA"]
            or row["RSI"] > RSI_SELL
        ):
            profit = row["Close"] - entry_price
            trades.append({"Date": row.name, "Action": "Sell", "Price": row["Close"], "Profit": profit})
            position = None

# --- Results ---
trades_df = pd.DataFrame(trades)
profits = trades_df[trades_df["Action"] == "Sell"]["Profit"]
total_profit = profits.sum()
win_rate = (profits > 0).sum() / len(profits) * 100 if len(profits) else 0

print("\n📊 Backtest Results")
print("------------------")
print(f"Total Trades: {len(profits)}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Total Profit: ${total_profit:.2f}")

# --- Plot ---
plt.figure(figsize=(15,6))
plt.plot(data["Close"], label="Close", color="black")
plt.plot(data["Fast_MA"], label=f"MA{FAST_MA}", linestyle="--")
plt.plot(data["Slow_MA"], label=f"MA{SLOW_MA}", linestyle=":")
for _, t in trades_df.iterrows():
    color = "green" if t["Action"] == "Buy" else "red"
    marker = "^" if t["Action"] == "Buy" else "v"
    plt.plot(t["Date"], t["Price"], marker=marker, color=color, markersize=10)
plt.title(f"Backtest - {SYMBOL} ({PERIOD})")
plt.legend()
plt.grid(True)
plt.show()

