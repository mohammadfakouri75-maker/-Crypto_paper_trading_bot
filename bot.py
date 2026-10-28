import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path("paper_state.json")
TRADES_FILE = Path("trades.csv")

STARTING_BALANCE = 1000.0
FEE_RATE = 0.001
BUY_DROP = 0.005
SELL_RISE = 0.005

COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
}

CSV_FIELDS = [
    "timestamp",
    "symbol",
    "action",
    "price",
    "quantity",
    "cash_balance",
    "portfolio_value",
    "profit_loss",
]

def update_dashboard_data(state, prices):
    holdings = {
        symbol: state["coins"][symbol]
        for symbol in COINS
    }

    holdings_value = sum(
        holdings[symbol] * prices[symbol]
        for symbol in COINS
    )

    total = state["cash"] + holdings_value

    data = {
        "starting_balance": STARTING_BALANCE,
        "cash": round(state["cash"], 2),
        "holdings": holdings,
        "prices": prices,
        "holdings_value": round(holdings_value, 2),
        "portfolio_value": round(total, 2),
        "profit_loss": round(total - STARTING_BALANCE, 2),
        "trades": state["trades"][-50:],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    Path("dashboard-data.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )
def get_prices():
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,ethereum&vs_currencies=usd"
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PaperTradingBot/1.0"},
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))

    return {
        symbol: float(data[coin]["usd"])
        for symbol, coin in COINS.items()
    }


def load_state():
    if STATE_FILE.exists():
        try:
            state = json.loads(
                STATE_FILE.read_text(encoding="utf-8")
            )

            if all(
                key in state
                for key in ("cash", "coins", "last_prices")
            ):
                state.setdefault("trades", [])
                return state

        except (json.JSONDecodeError, OSError):
            print("Could not read saved state; starting fresh.")

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


def ensure_csv():
    if not TRADES_FILE.exists() or TRADES_FILE.stat().st_size == 0:
        with TRADES_FILE.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
            writer.writeheader()


def portfolio_value(state, prices):
    holdings = sum(
        state["coins"][symbol] * prices[symbol]
        for symbol in COINS
    )
    return state["cash"] + holdings


def record_trade(state, symbol, action, price, amount, fee, prices):
    total = portfolio_value(state, prices)

    trade = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "action": action,
        "price": round(price, 2),
        "quantity": round(amount, 10),
        "cash_balance": round(state["cash"], 2),
        "portfolio_value": round(total, 2),
        "profit_loss": round(total - STARTING_BALANCE, 2),
    }

    state["trades"].append(trade)

    with TRADES_FILE.open(
        "a", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writerow(trade)


def process_prices(state, prices):
    ensure_csv()

    for symbol, price in prices.items():
        previous = state["last_prices"].get(symbol)

        if previous is not None and previous > 0:
            change = (price - previous) / previous

            if change <= -BUY_DROP and state["cash"] > 10:
                budget = min(state["cash"] * 0.10, 50.0)
                amount = budget / (price * (1 + FEE_RATE))
                cost = amount * price
                fee = cost * FEE_RATE

                if cost + fee <= state["cash"]:
                    state["cash"] -= cost + fee
                    state["coins"][symbol] += amount

                    record_trade(
                        state, symbol, "BUY",
                        price, amount, fee, prices
                    )

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
                    state, symbol, "SELL",
                    price, amount, fee, prices
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

    for symbol in COINS:
        print(f"{symbol} price: ${prices[symbol]:,.2f}")

    print(f"Virtual cash: ${state['cash']:,.2f}")
    print(f"Holdings value: ${holdings:,.2f}")
    print(f"Total portfolio: ${total:,.2f}")
    print(f"Profit/Loss: ${profit:,.2f}")
    print(f"Recorded trades: {len(state['trades'])}")
    print("REAL ORDERS: DISABLED")


def main():
    print("Paper trading only. No real orders will be placed.")

    state = load_state()

    try:
        prices = get_prices()
        process_prices(state, prices)
update_dashboard_data(state, prices)
report(state, prices)

    except Exception as error:
        print("Could not update prices:", error)
        raise


if __name__ == "__main__":
    main()
