import os
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL")

try:
    api = REST(API_KEY, API_SECRET, BASE_URL)
    account = api.get_account()
    print("✅ Connected to Alpaca!")
    print("Account status:", account.status)
    print("Equity:", account.equity)
    print("Buying Power:", account.buying_power)
except Exception as e:
    print("❌ Error connecting to Alpaca:", e)
