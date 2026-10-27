import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path("paper_state.json")
STARTING_BALANCE = 1000.0
FEE_RATE = 0.001
INTERVAL = 60
BUY_DROP = 0.005
SELL_RISE = 0.005

COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
}


def get_prices():
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,ethereum&vs_currencies=usd"
    )
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PaperTradingBot/1.0"},
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))

    return {
        symbol: float(data[coin]["usd"])
        for symbol, coin in COINS.items()
    }


def load_state():
    if STATE_FILE.exists():
        state = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )
        if all(
            key in state
            for key in ("cash", "coins", "last_prices", "trades")
        ):
            return state

    return {
        "cash": STARTING_BALANCE,
        "coins": {"BTC": 0.0, "ETH": 0.0},
        "last_prices": {},
        "trades": [],
    }


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )


def record_trade(state, symbol, side, price, amount, fee):
    state["trades"].append({
        "time": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "side": side,
        "price": round(price, 2),
        "amount": round(amount, 10),
        "fee": round(fee, 4),
    })


def process_prices(state, prices):
    for symbol, price in prices.items():
        previous = state["last_prices"].get(symbol)

        if previous is not None and previous > 0:
            change = (price - previous) / previous

            # Buy only in the simulation after a price drop.
            if change <= -BUY_DROP and state["cash"] > 10:
                budget = min(state["cash"] * 0.10, 50.0)
                amount = budget / (price * (1 + FEE_RATE))
                cost = amount * price
                fee = cost * FEE_RATE

                if cost + fee <= state["cash"]:
                    state["cash"] -= cost + fee
                    state["coins"][symbol] += amount
                    record_trade(
                        state, symbol, "BUY", price, amount, fee
                    )

            # Sell a small part after a price rise.
            elif (
                change >= SELL_RISE
                and state["coins"][symbol] > 0
            ):
                amount = state["coins"][symbol] * 0.10
                proceeds = amount * price
                fee = proceeds * FEE_RATE

                state["cash"] += proceeds - fee
                state["coins"][symbol] -= amount
                record_trade(
                    state, symbol, "SELL", price, amount, fee
                )

        state["last_prices"][symbol] = price

    save_state(state)


def report(state, prices):
    holdings = sum(
        state["coins"][symbol] * prices[symbol]
        for symbol in COINS
    )
    total = state["cash"] + holdings
    profit = total - STARTING_BALANCE

    print("\n--- PAPER TRADING REPORT ---")
    print("Time:", datetime.now(timezone.utc).isoformat())
    print("Prices (USD):")

    for symbol in COINS:
        print(f"  {symbol}: ${prices[symbol]:,.2f}")

    print(f"Virtual cash: ${state['cash']:,.2f}")
    print(f"Virtual holdings: ${holdings:,.2f}")
    print(f"Total value: ${total:,.2f}")
    print(f"Unrealized + realized P/L: ${profit:,.2f}")
    print(f"Recorded trades: {len(state['trades'])}")
    print("REAL ORDERS: DISABLED")


def main():
    state = load_state()
    print("Paper trading only. No real orders will be placed.")

    while True:
        try:
            prices = get_prices()
            process_prices(state, prices)
            report(state, prices)

        except Exception as error:
            print("Could not update prices:", error)
            print("Check internet access or API availability.")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
