# TARGET_FILE: risk_management.py
import json
import time
from typing import Dict, Optional

class MicroScalpingRiskManager:
    def __init__(self, settings: dict, state_file: str = "shared_state.json"):
        self.settings = settings
        self.state_file = state_file
        self.load_state()

    def load_state(self):
        try:
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        except Exception:
            self.state = {
                "portfolio_value_usdt": 1000.0,
                "active_position": None,
                "total_pnl_pct": 0.0,
                "daily_pnl_pct": 0.0
            }

    def save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f)

    def can_open_position(self, symbol: str) -> bool:
        if self.state["active_position"] is not None:
            return False
        if self.state["daily_pnl_pct"] <= -self.settings['risk']['daily_loss_limit_pct']:
            return False
        return True

    def calculate_position_size(self, current_price: float) -> float:
        portfolio = self.state["portfolio_value_usdt"]
        pct = self.settings['trading']['position_size_pct'] / 100.0
        usdt_amount = portfolio * pct
        qty = usdt_amount / current_price

        symbol = self.settings['trading']['symbols'][0]
        
        if 'BTC' in symbol:
            qty = max(qty, 0.00001)
            qty = round(qty, 5)
            if qty * current_price < 10.0:
                qty = 10.0 / current_price
                qty = round(qty, 5)
                qty = max(qty, 0.00001)
        elif 'ETH' in symbol:
            qty = max(qty, 0.0001)
            qty = round(qty, 4)
            if qty * current_price < 10.0:
                qty = 10.0 / current_price
                qty = round(qty, 4)
                qty = max(qty, 0.0001)
        else:
            qty = max(qty, 0.00001)
            qty = round(qty, 5)
            if qty * current_price < 10.0:
                qty = 10.0 / current_price
                qty = round(qty, 5)
                qty = max(qty, 0.00001)

        return qty

    def check_exit_conditions(self, current_price: float) -> Optional[str]:
        pos = self.state["active_position"]
        if not pos:
            return None

        entry = pos["entry_price"]
        side = pos["side"]
        sl_pct = self.settings['trading']['stop_loss_pct'] / 100.0
        tp_pct = self.settings['trading']['take_profit_pct'] / 100.0

        if side == "buy":
            if current_price <= entry * (1 - sl_pct):
                return "stop_loss"
            if current_price >= entry * (1 + tp_pct):
                return "take_profit"
        else:  # sell
            if current_price >= entry * (1 + sl_pct):
                return "stop_loss"
            if current_price <= entry * (1 - tp_pct):
                return "take_profit"

        if time.time() - pos["open_time"] > self.settings['trading']['max_order_age_seconds']:
            return "timeout"

        return None

    def update_portfolio_after_close(self, close_price: float, side: str, qty: float, entry_price: float):
        pnl_usdt = (close_price - entry_price) * qty if side == "buy" else (entry_price - close_price) * qty
        old_value = self.state["portfolio_value_usdt"]
        new_value = old_value + pnl_usdt
        self.state["portfolio_value_usdt"] = new_value
        self.state["total_pnl_pct"] = (new_value / 1000.0 - 1) * 100
        self.state["daily_pnl_pct"] += (pnl_usdt / old_value) * 100
        self.state["active_position"] = None