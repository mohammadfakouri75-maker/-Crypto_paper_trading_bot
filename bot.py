import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path("paper_state.json")
STARTING_BALANCE = 1000.0
FEE_RATE = 0.001
SYMBOLS = ["BTC", "ETH"]


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "cash": STARTING_BALANCE,
        "coins": {"BTC": 0.0, "ETH": 0.0},
        "last_price": {"BTC": 60000.0, "ETH": 3000.0},
        "trades": [],
    }


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def tick(state):
    for symbol in SYMBOLS:
        old = state["last_price"][symbol]
        price = old * (1 + random.uniform(-0.01, 0.01))
        state["last_price"][symbol] = price

        # نمونه آموزشی ساده: خرید پس از افت و فروش پس از رشد
        change = (price - old) / old

        if change < -0.005 and state["cash"] > 10:
            amount = min(state["cash"] * 0.10, 50) / price
            cost = amount * price
            fee = cost * FEE_RATE
            state["cash"] -= cost + fee
            state["coins"][symbol] += amount
            state["trades"].append({
                "time": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "side": "BUY",
                "price": round(price, 2),
                "amount": amount,
                "fee": fee,
            })

        elif change > 0.005 and state["coins"][symbol] > 0:
            amount = state["coins"][symbol] * 0.10
            proceeds = amount * price
            fee = proceeds * FEE_RATE
            state["cash"] += proceeds - fee
            state["coins"][symbol] -= amount
            state["trades"].append({
                "time": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "side": "SELL",
                "price": round(price, 2),
                "amount": amount,
                "fee": fee,
            })

    save_state(state)


def report(state):
    holdings = sum(
        state["coins"][s] * state["last_price"][s] for s in SYMBOLS
    )
    total = state["cash"] + holdings
    print("\n--- PAPER TRADING REPORT ---")
    print("Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("Cash:", round(state["cash"], 2), "USD (virtual)")
    print("Holdings:", round(holdings, 2), "USD (virtual)")
    print("Total:", round(total, 2), "USD (virtual)")
    print("Profit/loss:", round(total - STARTING_BALANCE, 2), "USD")
    print("Trades recorded:", len(state["trades"]))
    print("Prices:", {
        s: round(state["last_price"][s], 2) for s in SYMBOLS
    })


if __name__ == "__main__":
    state = load_state()
    print("Educational simulation only. No real orders are placed.")
    while True:
        try:
            tick(state)
            report(state)
            time.sleep(60)
        except KeyboardInterrupt:
            print("Stopped.")
            break
        except Exception as exc:
            print("Error:", exc)
            time.sleep(60)
