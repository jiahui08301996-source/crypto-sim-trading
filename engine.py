# engine.py - 撮合引擎（穿针+滑点模拟）

import time
from config import TAKER_FEE, MAKER_FEE, SLIPPAGE_RATE


class MatchingEngine:
    def __init__(self, account):
        self.account = account
        self.current_prices = {}    # symbol -> last_price
        self.tick_highs = {}        # 当前秒内最高价（用于穿针检测）
        self.tick_lows = {}         # 当前秒内最低价
        self.callbacks = []         # 成交回调

    def on_tick(self, symbol, price, high=None, low=None):
        """
        每次收到行情tick
        price: 最新成交价
        high/low: 当前K线高低点（用于穿针）
        """
        self.current_prices[symbol] = price

        # 用逐笔价格模拟高低点（如果没有K线数据）
        if symbol not in self.tick_highs:
            self.tick_highs[symbol] = price
            self.tick_lows[symbol] = price
        else:
            self.tick_highs[symbol] = max(self.tick_highs[symbol], high or price)
            self.tick_lows[symbol] = min(self.tick_lows[symbol], low or price)

        # 检查所有挂单是否触发
        self._check_orders(symbol, price, self.tick_highs[symbol], self.tick_lows[symbol])

    def _check_orders(self, symbol, last_price, high, low):
        """
        核心撮合逻辑：穿针检测
        - 买单：价格低点 <= 挂单价 → 成交（影线穿针）
        - 卖单：价格高点 >= 挂单价 → 成交
        - 止盈止损：同样用高低点检测
        """
        orders_to_fill = []

        for order in self.account.orders:
            if order["symbol"] != symbol or order["status"] != "open":
                continue

            triggered = False
            fill_price = order["price"]

            if order["type"] == "limit":
                if order["side"] == "buy" and low <= order["price"]:
                    # 买单穿针成交
                    triggered = True
                    fill_price = self._apply_slippage(order["price"], "buy", order["size"])
                elif order["side"] == "sell" and high >= order["price"]:
                    # 卖单穿针成交
                    triggered = True
                    fill_price = self._apply_slippage(order["price"], "sell", order["size"])

            elif order["type"] == "market":
                triggered = True
                fill_price = self._apply_slippage(last_price, order["side"], order["size"])

            if triggered:
                orders_to_fill.append((order, fill_price, MAKER_FEE))

        # 检查止盈止损
        for order in list(self.account.orders):
            if order["symbol"] != symbol:
                continue
            # 止盈
            if order.get("tp"):
                tp = order["tp"]
                if (order["side"] == "buy" and high >= tp) or \
                   (order["side"] == "sell" and low <= tp):
                    # 创建反向平仓单
                    close_side = "sell" if order["side"] == "buy" else "buy"
                    close_order = {**order, "side": close_side, "price": tp, "type": "limit", "tp": None, "sl": None}
                    orders_to_fill.append((close_order, tp, MAKER_FEE))

            # 止损
            if order.get("sl"):
                sl = order["sl"]
                if (order["side"] == "buy" and low <= sl) or \
                   (order["side"] == "sell" and high >= sl):
                    close_side = "sell" if order["side"] == "buy" else "buy"
                    close_order = {**order, "side": close_side, "price": sl, "type": "market", "tp": None, "sl": None}
                    fill_price = self._apply_slippage(sl, close_side, order["size"])
                    orders_to_fill.append((close_order, fill_price, TAKER_FEE))

        # 执行成交
        for order, fill_price, fee_rate in orders_to_fill:
            success, result = self.account.fill_order(order, fill_price, fee_rate)
            if success:
                self._notify_fill(result)

    def _apply_slippage(self, price, side, size):
        """
        滑点模拟：根据订单大小计算滑点
        size越大，滑点越大
        """
        # 基础滑点 + 规模滑点（每10BTC多0.01%）
        impact = SLIPPAGE_RATE + (size / 10) * 0.0001
        if side == "buy":
            return price * (1 + impact)
        else:
            return price * (1 - impact)

    def _notify_fill(self, fill_record):
        ts = time.strftime("%H:%M:%S", time.localtime(fill_record["time"]))
        msg = (f"\n[FILL] [{ts}] {fill_record['symbol']} "
               f"{fill_record['side'].upper()} "
               f"{fill_record['size']} @ ${fill_record['fill_price']:,.2f} "
               f"fee: ${fill_record['fee']:.4f}")
        print(msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        for cb in self.callbacks:
            cb(fill_record)

    def reset_tick_data(self, symbol):
        """每秒重置高低点（用于新K线）"""
        price = self.current_prices.get(symbol, 0)
        self.tick_highs[symbol] = price
        self.tick_lows[symbol] = price
