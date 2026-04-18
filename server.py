# server.py - FastAPI 后端
# 提供 REST API + WebSocket 实时推送

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from account import Account
from engine import MatchingEngine
from exchange import BinanceStream
from config import SYMBOLS, INITIAL_BALANCE

# ── 全局状态 ──────────────────────────────────────────────
account = Account("web_player")
engine = MatchingEngine(account)
stream = None

# WebSocket 连接池（广播实时价格给所有浏览器）
ws_clients: Set[WebSocket] = set()

def on_tick(symbol, price, high, low):
    """行情回调：更新引擎 + 异步广播给所有浏览器"""
    engine.on_tick(symbol, price, high, low)
    # 非阻塞广播
    asyncio.run_coroutine_threadsafe(
        broadcast_price(symbol, price, high, low),
        main_loop
    )

async def broadcast_price(symbol, price, high, low):
    msg = json.dumps({
        "type": "tick",
        "symbol": symbol,
        "price": price,
        "high": high,
        "low": low,
        "ts": int(time.time() * 1000)
    })
    dead = set()
    for ws in ws_clients.copy():
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    ws_clients -= dead

main_loop = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global stream, main_loop
    main_loop = asyncio.get_event_loop()
    stream = BinanceStream(on_tick_callback=on_tick)
    stream.start()
    yield
    stream.stop()

# ── FastAPI App ───────────────────────────────────────────
app = FastAPI(title="CryptoSimTrading", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ── REST API ──────────────────────────────────────────────

@app.get("/")
async def index():
    return FileResponse("static/index.html")

@app.get("/api/prices")
async def get_prices():
    return {sym: stream.get_price(sym) for sym in SYMBOLS} if stream else {}

@app.get("/api/account")
async def get_account():
    prices = {sym: stream.get_price(sym) for sym in SYMBOLS} if stream else {}
    pnl = account.get_pnl(prices)
    return {
        "balance": round(account.balance, 4),
        "initial": INITIAL_BALANCE,
        "pnl": round(pnl, 4),
        "total_equity": round(account.balance + pnl, 4),
        "positions": account.positions,
        "orders": account.orders,
    }

@app.post("/api/order")
async def place_order(body: dict):
    symbol = body.get("symbol", "").upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"
    side = body.get("side")          # buy / sell
    order_type = body.get("type", "limit")   # limit / market
    price = float(body.get("price", 0))
    size = float(body.get("size", 0))
    tp = body.get("tp")
    sl = body.get("sl")

    if not symbol or not side or size <= 0:
        return {"ok": False, "error": "Invalid parameters"}
    if symbol not in SYMBOLS:
        return {"ok": False, "error": f"Symbol {symbol} not supported"}

    tp = float(tp) if tp else None
    sl = float(sl) if sl else None

    order = account.place_order(symbol, side, order_type, price, size, tp=tp, sl=sl)

    # 市价单立即触发
    if order_type == "market" and stream:
        cur = stream.get_price(symbol)
        if cur:
            engine.on_tick(symbol, cur, cur, cur)

    return {"ok": True, "order": order}

@app.delete("/api/order/{order_id}")
async def cancel_order(order_id: str):
    before = len(account.orders)
    account.orders = [o for o in account.orders if o["id"] != order_id]
    account._save()
    if len(account.orders) < before:
        return {"ok": True}
    return {"ok": False, "error": "Order not found"}

@app.get("/api/history")
async def get_history():
    return {"history": account.history[-50:]}

@app.post("/api/reset")
async def reset_account():
    import os
    if os.path.exists(account.filepath):
        os.remove(account.filepath)
    account._load()
    return {"ok": True, "balance": account.balance}

# ── WebSocket ─────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    try:
        # 立即推送当前价格
        if stream:
            for sym in SYMBOLS:
                price = stream.get_price(sym)
                if price:
                    await ws.send_text(json.dumps({
                        "type": "tick",
                        "symbol": sym,
                        "price": price,
                        "high": price,
                        "low": price,
                        "ts": int(time.time() * 1000)
                    }))
        while True:
            await asyncio.sleep(30)   # 保持连接
    except WebSocketDisconnect:
        ws_clients.discard(ws)
    except Exception:
        ws_clients.discard(ws)
