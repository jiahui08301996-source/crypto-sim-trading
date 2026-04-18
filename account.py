# account.py - 模拟账户系统

import json
import time
import os
from config import INITIAL_BALANCE, DATA_DIR

class Account:
    def __init__(self, account_id="default"):
        self.account_id = account_id
        self.filepath = os.path.join(DATA_DIR, f"account_{account_id}.json")
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                data = json.load(f)
            self.balance = data["balance"]
            self.positions = data["positions"]
            self.orders = data["orders"]
            self.history = data["history"]
        else:
            self.balance = INITIAL_BALANCE
            self.positions = {}   # symbol -> {size, entry_price, side}
            self.orders = []      # 挂单列表
            self.history = []     # 成交历史
            self._save()

    def _save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump({
                "balance": self.balance,
                "positions": self.positions,
                "orders": self.orders,
                "history": self.history
            }, f, indent=2, ensure_ascii=False)

    def place_order(self, symbol, side, order_type, price, size, tp=None, sl=None):
        """
        下单
        side: 'buy' / 'sell'
        order_type: 'limit' / 'market'
        size: 数量 (BTC单位)
        """
        order = {
            "id": f"{int(time.time()*1000)}",
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "price": price,
            "size": size,
            "tp": tp,    # 止盈价
            "sl": sl,    # 止损价
            "status": "open",
            "created_at": time.time()
        }
        self.orders.append(order)
        self._save()
        return order

    def fill_order(self, order, fill_price, fee_rate):
        """成交一笔订单"""
        cost = fill_price * order["size"]
        fee = cost * fee_rate

        if order["side"] == "buy":
            if self.balance < cost + fee:
                return False, "余额不足"
            self.balance -= (cost + fee)
            # 更新仓位
            sym = order["symbol"]
            if sym not in self.positions:
                self.positions[sym] = {"size": 0, "entry_price": 0, "side": "long"}
            pos = self.positions[sym]
            total_size = pos["size"] + order["size"]
            pos["entry_price"] = (pos["size"] * pos["entry_price"] + order["size"] * fill_price) / total_size
            pos["size"] = total_size
            pos["side"] = "long"
        else:  # sell
            sym = order["symbol"]
            if sym in self.positions and self.positions[sym]["size"] > 0:
                # 平多仓
                pos = self.positions[sym]
                pnl = (fill_price - pos["entry_price"]) * order["size"]
                self.balance += fill_price * order["size"] - fee + pnl
                pos["size"] -= order["size"]
                if pos["size"] <= 0:
                    del self.positions[sym]
            else:
                # 开空仓
                self.balance -= fee
                if sym not in self.positions:
                    self.positions[sym] = {"size": 0, "entry_price": 0, "side": "short"}
                pos = self.positions[sym]
                total_size = pos["size"] + order["size"]
                pos["entry_price"] = (pos["size"] * pos["entry_price"] + order["size"] * fill_price) / total_size
                pos["size"] = total_size
                pos["side"] = "short"

        # 记录成交
        fill_record = {
            "order_id": order["id"],
            "symbol": order["symbol"],
            "side": order["side"],
            "fill_price": fill_price,
            "size": order["size"],
            "fee": fee,
            "time": time.time()
        }
        self.history.append(fill_record)

        # 移除已成交订单
        self.orders = [o for o in self.orders if o["id"] != order["id"]]
        self._save()
        return True, fill_record

    def get_pnl(self, current_prices):
        """计算当前浮动盈亏"""
        total_pnl = 0
        for sym, pos in self.positions.items():
            if sym in current_prices:
                price = current_prices[sym]
                if pos["side"] == "long":
                    pnl = (price - pos["entry_price"]) * pos["size"]
                else:
                    pnl = (pos["entry_price"] - price) * pos["size"]
                total_pnl += pnl
        return total_pnl

    def show_status(self, current_prices=None):
        print(f"\n{'='*50}")
        print(f"📊 账户: {self.account_id}")
        print(f"💰 余额: ${self.balance:,.2f} USDT")
        if current_prices:
            pnl = self.get_pnl(current_prices)
            print(f"📈 浮动盈亏: ${pnl:+,.2f} USDT")
        print(f"\n📦 持仓:")
        if self.positions:
            for sym, pos in self.positions.items():
                price = current_prices.get(sym, 0) if current_prices else 0
                print(f"  {sym}: {pos['side'].upper()} {pos['size']} @ ${pos['entry_price']:,.2f} | 现价: ${price:,.2f}")
        else:
            print("  暂无持仓")
        print(f"\n📋 挂单: {len(self.orders)} 笔")
        for o in self.orders:
            print(f"  [{o['id'][-6:]}] {o['symbol']} {o['side'].upper()} {o['size']} @ ${o['price']:,.2f} | TP:{o.get('tp','无')} SL:{o.get('sl','无')}")
        print('='*50)
