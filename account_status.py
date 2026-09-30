"""Read-only account assessment for trend-bot. Never places/cancels anything."""
import os

from binance.client import Client
from dotenv import load_dotenv

load_dotenv()
SYMBOLS = [s.strip() for s in os.getenv("SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT").split(",") if s.strip()]


def main():
    api_key = os.getenv("BINANCE_US_API_KEY")
    api_secret = os.getenv("BINANCE_US_API_SECRET")
    client = Client(api_key, api_secret, tld="us")

    print("=== Account balances (nonzero only) ===")
    account = client.get_account()
    for bal in account["balances"]:
        free, locked = float(bal["free"]), float(bal["locked"])
        if free > 0 or locked > 0:
            print(f"  {bal['asset']:>6}: free={free:.8f}  locked={locked:.8f}")

    for symbol in SYMBOLS:
        print(f"\n=== {symbol} ===")
        price = float(client.get_symbol_ticker(symbol=symbol)["price"])
        print(f"  price: {price}")
        orders = client.get_open_orders(symbol=symbol)
        print(f"  open orders: {len(orders)}")
        for o in orders:
            print(f"    {o['side']} {o['origQty']} @ {o['price']} status={o['status']}")


if __name__ == "__main__":
    main()
