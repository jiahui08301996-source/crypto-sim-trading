# exchange.py - Binance WebSocket 实时行情接入
# 保证每个交易对至少 5Hz 刷新（200ms 保底）

import json
import time
import threading
import websocket
from config import BINANCE_WS_URL, SYMBOLS

# 最低刷新间隔：200ms = 5Hz
MIN_REFRESH_INTERVAL = 0.2


class BinanceStream:
    def __init__(self, on_tick_callback):
        """
        on_tick_callback(symbol, price, high, low) 每次行情更新时调用
        """
        self.on_tick = on_tick_callback
        self.ws = None
        self.running = False

        # 实时价格和K线高低点
        self.prices = {}          # symbol -> last_price
        self.tick_highs = {}      # symbol -> 当前秒内最高价
        self.tick_lows = {}       # symbol -> 当前秒内最低价

        # 上次推送时间（用于保底刷新）
        self._last_push = {}      # symbol -> timestamp

        # 刷新频率统计
        self._tick_count = {}     # symbol -> count in last second
        self._count_reset = time.time()

    def _build_stream_url(self):
        streams = []
        for sym in SYMBOLS:
            s = sym.lower()
            streams.append(f"{s}@trade")       # 逐笔成交（最高精度，BTC可达50+次/秒）
            streams.append(f"{s}@kline_1s")    # 1秒K线（提供精准高低点，用于穿针）
        return f"{BINANCE_WS_URL}?streams=" + "/".join(streams)

    def _push_tick(self, symbol, price, high, low):
        """统一推送入口，记录统计"""
        now = time.time()
        self._last_push[symbol] = now
        self._tick_count[symbol] = self._tick_count.get(symbol, 0) + 1
        self.on_tick(symbol, price, high, low)

    def _on_message(self, ws, raw):
        try:
            msg = json.loads(raw)
            data = msg.get("data", {})
            stream = msg.get("stream", "")

            if "@trade" in stream:
                symbol = data["s"]
                price = float(data["p"])
                self.prices[symbol] = price
                # 更新高低点
                if symbol not in self.tick_highs:
                    self.tick_highs[symbol] = price
                    self.tick_lows[symbol] = price
                else:
                    self.tick_highs[symbol] = max(self.tick_highs[symbol], price)
                    self.tick_lows[symbol] = min(self.tick_lows[symbol], price)
                self._push_tick(symbol, price, self.tick_highs[symbol], self.tick_lows[symbol])

            elif "@kline" in stream:
                k = data["k"]
                symbol = k["s"]
                high = float(k["h"])
                low = float(k["l"])
                close = float(k["c"])
                # 更新高低点（K线数据更准确）
                self.tick_highs[symbol] = high
                self.tick_lows[symbol] = low
                self.prices[symbol] = close
                self._push_tick(symbol, close, high, low)

        except Exception as e:
            print(f"[parse error] {e}")

    def _on_error(self, ws, error):
        print(f"[WS error] {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        print("[WS closed] reconnecting in 3s...")
        if self.running:
            threading.Timer(3.0, self.start).start()

    def _on_open(self, ws):
        syms = ", ".join(SYMBOLS)
        print(f"[Binance WS] Connected | Symbols: {syms}")

    def _heartbeat_loop(self):
        """
        保底5Hz刷新线程：
        如果某个交易对超过200ms没收到tick，用上次价格强制推一次
        确保撮合引擎持续运转
        """
        while self.running:
            time.sleep(MIN_REFRESH_INTERVAL)
            now = time.time()
            for sym in SYMBOLS:
                if sym not in self.prices:
                    continue
                last = self._last_push.get(sym, 0)
                if now - last >= MIN_REFRESH_INTERVAL:
                    # 超过200ms没新tick，强制推一次（维持5Hz保底）
                    price = self.prices[sym]
                    self._push_tick(
                        sym, price,
                        self.tick_highs.get(sym, price),
                        self.tick_lows.get(sym, price)
                    )

    def _stats_loop(self):
        """每5秒打印一次刷新频率统计"""
        while self.running:
            time.sleep(5)
            now = time.time()
            elapsed = now - self._count_reset
            parts = []
            for sym in SYMBOLS:
                count = self._tick_count.get(sym, 0)
                hz = count / elapsed if elapsed > 0 else 0
                parts.append(f"{sym}:{hz:.1f}Hz")
            print(f"[Rate] {' | '.join(parts)}")
            # 重置计数
            self._tick_count = {}
            self._count_reset = now

    def start(self):
        self.running = True
        url = self._build_stream_url()
        self.ws = websocket.WebSocketApp(
            url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        # WS主线程
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
        # 保底5Hz线程
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        # 频率统计线程
        threading.Thread(target=self._stats_loop, daemon=True).start()
        print("[Binance] Connecting... (5Hz guaranteed refresh)")

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()

    def get_price(self, symbol):
        return self.prices.get(symbol)

    def get_rate(self, symbol):
        """返回该交易对当前刷新频率（Hz）"""
        count = self._tick_count.get(symbol, 0)
        elapsed = time.time() - self._count_reset
        return count / elapsed if elapsed > 0 else 0
