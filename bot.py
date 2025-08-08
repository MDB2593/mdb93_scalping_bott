import time
import threading
import math
import datetime as dt
from collections import defaultdict, deque
from binance.client import Client
from binance.enums import *
from indicators import ema

class TradeLogEntry(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__

class ScalpingBot:
    def __init__(self, api_key, api_secret, testnet=True, stake_usdt=500.0, profit_pct=0.003, stop_pct=-0.003):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.client = Client(api_key, api_secret, testnet=testnet)

        self.stake_usdt = float(stake_usdt)
        self.tp = float(profit_pct)     # +0.3% default
        self.sl = float(stop_pct)       # -0.3% default

        self.active_symbol = "BTCUSDT"
        self.allowed_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        self.running = False

        # One position per symbol (qty>0 means long open)
        self.entries = {}   # symbol -> entry_price
        self.qty = {}       # symbol -> base asset quantity
        self.trade_log = deque(maxlen=5000)  # last N trades

        # stats
        self.daily_pnl = defaultdict(float) # date->pnl in USDT
        self.daily_pnl_by_symbol = defaultdict(lambda: defaultdict(float)) # date->symbol->pnl
        self.avoided_trades_today = 0

        self._lock = threading.Lock()
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    # ---------- helpers ----------
    def _now_date(self):
        return dt.datetime.utcnow().date().isoformat()

    def get_price(self, symbol=None):
        symbol = symbol or self.active_symbol
        try:
            p = float(self.client.get_symbol_ticker(symbol=symbol)["price"])
            return p
        except Exception:
            return None

    def get_free_usdt(self):
        try:
            bal = self.client.get_asset_balance(asset="USDT")
            return float(bal["free"])
        except Exception:
            return 0.0

    def set_mode(self, testnet: bool, api_key=None, api_secret=None):
        # switch between demo and real
        with self._lock:
            if api_key and api_secret:
                self.api_key = api_key
                self.api_secret = api_secret
            self.testnet = testnet
            self.client = Client(self.api_key, self.api_secret, testnet=testnet)

    def set_symbol(self, symbol):
        if symbol in self.allowed_symbols:
            with self._lock:
                self.active_symbol = symbol
            return True
        return False

    def set_stake(self, stake):
        with self._lock:
            self.stake_usdt = float(stake)

    def set_tp_sl(self, tp, sl):
        with self._lock:
            self.tp = float(tp)
            self.sl = float(sl)

    def set_running(self, on: bool):
        with self._lock:
            self.running = on

    # ---------- trading logic ----------
    def _place_order_market(self, symbol, side, quote_amount=None, base_qty=None):
        # choose qty: either by base_qty or by quote_amount converted to qty at market
        price = self.get_price(symbol)
        if price is None:
            raise RuntimeError("Price unavailable")
        qty = base_qty
        if qty is None:
            # compute qty by quote amount
            q = (quote_amount or self.stake_usdt) / price
            # round to 6 decimals to be safe
            qty = round(q, 6)

        order = self.client.create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )
        return order, price, qty

    def _enter_long(self, symbol):
        o, price, qty = self._place_order_market(symbol, SIDE_BUY, quote_amount=self.stake_usdt)
        with self._lock:
            self.entries[symbol] = price
            self.qty[symbol] = qty
            self.trade_log.append(TradeLogEntry(time=dt.datetime.utcnow().isoformat(), symbol=symbol, side="BUY", price=price, qty=qty))
        return True

    def _exit_long(self, symbol):
        qty = self.qty.get(symbol, 0.0)
        if qty <= 0:
            return False
        o, price, q_used = self._place_order_market(symbol, SIDE_SELL, base_qty=qty)
        with self._lock:
            entry = self.entries.get(symbol, price)
            pnl = (price - entry) * q_used  # in USDT
            self.daily_pnl[self._now_date()] += pnl
            self.daily_pnl_by_symbol[self._now_date()][symbol] += pnl
            self.trade_log.append(TradeLogEntry(time=dt.datetime.utcnow().isoformat(), symbol=symbol, side="SELL", price=price, qty=q_used, pnl=round(pnl, 4)))
            self.entries[symbol] = 0.0
            self.qty[symbol] = 0.0
        return True

    def strategy_should_trade_long(self, symbol):
        # Simple EMA filter using last 50 closes
        try:
            kl = self.client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1MINUTE, limit=50)
            closes = [float(k[4]) for k in kl]
            if len(closes) < 22:
                return False, None, None
            ema9 = ema(closes, 9)[-1]
            ema21 = ema(closes, 21)[-1]
            price = closes[-1]
            # BUY filter: price above both, ema9 > ema21
            allow_long = price > ema9 and price > ema21 and ema9 > ema21
            return allow_long, ema9, ema21
        except Exception:
            return False, None, None

    def _loop(self):
        while True:
            try:
                time.sleep(3)
                with self._lock:
                    running = self.running
                    symbols = list(set(list(self.entries.keys()) + [self.active_symbol] + self.allowed_symbols))
                if not running:
                    continue

                for sym in symbols:
                    price = self.get_price(sym)
                    if price is None:
                        continue

                    entry = self.entries.get(sym, 0.0)
                    has_pos = self.qty.get(sym, 0.0) > 0

                    if not has_pos and sym == self.active_symbol:
                        allow_long, e9, e21 = self.strategy_should_trade_long(sym)
                        if allow_long:
                            self._enter_long(sym)
                        else:
                            # count trades avoided by EMA only for active symbol
                            self.avoided_trades_today += 1
                        continue

                    if has_pos:
                        change = (price - entry) / entry if entry else 0.0
                        if change >= self.tp or change <= self.sl:
                            self._exit_long(sym)
            except Exception:
                # swallow exceptions to keep thread alive
                continue

    # ---------- read-only for API ----------
    def snapshot(self):
        with self._lock:
            today = self._now_date()
            return {
                "mode": "DEMO" if self.testnet else "REALE",
                "running": self.running,
                "active_symbol": self.active_symbol,
                "stake_usdt": self.stake_usdt,
                "tp": self.tp,
                "sl": self.sl,
                "free_usdt": self.get_free_usdt(),
                "price": self.get_price(self.active_symbol),
                "today_pnl": round(self.daily_pnl[today], 4),
                "today_avoided": int(self.avoided_trades_today),
                "pnl_by_symbol": {
                    s: round(v, 4) for s, v in self.daily_pnl_by_symbol[today].items()
                },
                "trades": list(self.trade_log)[-20:],
            }
