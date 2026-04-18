#!/usr/bin/env python3
# main.py - 虚拟币模拟交易平台 MVP
# 对标 Binance 实时行情，支持穿针成交、滑点模拟

import time
import sys
import os
from account import Account
from engine import MatchingEngine
from exchange import BinanceStream
from config import SYMBOLS

def print_banner():
    print("""
╔══════════════════════════════════════════════╗
║       虚拟币模拟交易平台 v1.0                ║
║       实时对标 Binance | 穿针撮合            ║
╚══════════════════════════════════════════════╝
""")

def print_help():
    print("""
命令列表:
  p / price           查看当前价格
  s / status          查看账户状态
  buy  <品种> <价格> <数量> [tp] [sl]   挂买单
  sell <品种> <价格> <数量> [tp] [sl]   挂卖单
  mbuy  <品种> <数量>                   市价买
  msell <品种> <数量>                   市价卖
  orders              查看所有挂单
  cancel <订单id>     撤销挂单
  history             查看成交记录
  reset               重置账户（清空所有数据）
  help                显示帮助
  quit / exit         退出

品种代码: BTC ETH SOL BNB (自动加USDT)
示例:
  buy BTC 60000 0.1 tp=65000 sl=58000
  sell ETH 3500 1.0
  mbuy SOL 10
""")

def normalize_symbol(sym):
    sym = sym.upper()
    if not sym.endswith("USDT"):
        sym += "USDT"
    return sym

def parse_tp_sl(args):
    tp = sl = None
    for arg in args:
        if arg.startswith("tp="):
            tp = float(arg.split("=")[1])
        elif arg.startswith("sl="):
            sl = float(arg.split("=")[1])
    return tp, sl

def main():
    print_banner()

    # 初始化账户和引擎
    account = Account("player1")
    engine = MatchingEngine(account)

    # 启动 Binance 行情
    stream = BinanceStream(on_tick_callback=engine.on_tick)
    stream.start()

    print("等待行情连接...")
    time.sleep(2)
    print_help()

    while True:
        try:
            raw = input("\n> ").strip()
            if not raw:
                continue

            parts = raw.split()
            cmd = parts[0].lower()

            # ── 价格查询 ──
            if cmd in ("p", "price"):
                print("\n[Price] Live prices (Binance):")
                for sym in SYMBOLS:
                    price = stream.get_price(sym)
                    hz = stream.get_rate(sym)
                    if price:
                        print(f"  {sym}: ${price:,.2f}  [{hz:.1f} Hz]")
                    else:
                        print(f"  {sym}: connecting...")

            # ── 账户状态 ──
            elif cmd in ("s", "status"):
                account.show_status(stream.prices)

            # ── 挂买单 ──
            elif cmd == "buy" and len(parts) >= 4:
                sym = normalize_symbol(parts[1])
                price = float(parts[2])
                size = float(parts[3])
                tp, sl = parse_tp_sl(parts[4:])
                order = account.place_order(sym, "buy", "limit", price, size, tp=tp, sl=sl)
                print(f"✅ 买单已挂: {sym} {size} @ ${price:,.2f} | TP:{tp} SL:{sl} | ID:{order['id'][-8:]}")

            # ── 挂卖单 ──
            elif cmd == "sell" and len(parts) >= 4:
                sym = normalize_symbol(parts[1])
                price = float(parts[2])
                size = float(parts[3])
                tp, sl = parse_tp_sl(parts[4:])
                order = account.place_order(sym, "sell", "limit", price, size, tp=tp, sl=sl)
                print(f"✅ 卖单已挂: {sym} {size} @ ${price:,.2f} | TP:{tp} SL:{sl} | ID:{order['id'][-8:]}")

            # ── 市价买 ──
            elif cmd == "mbuy" and len(parts) >= 3:
                sym = normalize_symbol(parts[1])
                size = float(parts[2])
                order = account.place_order(sym, "buy", "market", 0, size)
                # 市价单立即触发
                price = stream.get_price(sym)
                if price:
                    engine.on_tick(sym, price, price, price)
                    print(f"✅ 市价买单已提交: {sym} {size}")
                else:
                    print("❌ 无法获取当前价格")

            # ── 市价卖 ──
            elif cmd == "msell" and len(parts) >= 3:
                sym = normalize_symbol(parts[1])
                size = float(parts[2])
                order = account.place_order(sym, "sell", "market", 0, size)
                price = stream.get_price(sym)
                if price:
                    engine.on_tick(sym, price, price, price)
                    print(f"✅ 市价卖单已提交: {sym} {size}")
                else:
                    print("❌ 无法获取当前价格")

            # ── 查看挂单 ──
            elif cmd == "orders":
                if account.orders:
                    print(f"\n📋 当前挂单 ({len(account.orders)} 笔):")
                    for o in account.orders:
                        print(f"  [{o['id'][-8:]}] {o['symbol']} {o['side'].upper()} "
                              f"{o['size']} @ ${o['price']:,.2f} | TP:{o.get('tp','无')} SL:{o.get('sl','无')}")
                else:
                    print("暂无挂单")

            # ── 撤销挂单 ──
            elif cmd == "cancel" and len(parts) >= 2:
                order_id_suffix = parts[1]
                before = len(account.orders)
                account.orders = [o for o in account.orders if not o["id"].endswith(order_id_suffix)]
                account._save()
                if len(account.orders) < before:
                    print(f"✅ 订单 {order_id_suffix} 已撤销")
                else:
                    print(f"❌ 未找到订单 {order_id_suffix}")

            # ── 成交历史 ──
            elif cmd == "history":
                if account.history:
                    print(f"\n📜 成交记录 (最近20笔):")
                    for h in account.history[-20:]:
                        ts = time.strftime("%m-%d %H:%M:%S", time.localtime(h["time"]))
                        print(f"  [{ts}] {h['symbol']} {h['side'].upper()} "
                              f"{h['size']} @ ${h['fill_price']:,.2f} 手续费:${h['fee']:.4f}")
                else:
                    print("暂无成交记录")

            # ── 重置账户 ──
            elif cmd == "reset":
                confirm = input("⚠️  确认重置账户？所有数据将清空 (yes/no): ")
                if confirm.lower() == "yes":
                    filepath = account.filepath
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    account._load()
                    print("✅ 账户已重置")

            # ── 帮助 ──
            elif cmd == "help":
                print_help()

            # ── 退出 ──
            elif cmd in ("quit", "exit", "q"):
                print("👋 退出模拟交易平台")
                stream.stop()
                break

            else:
                print(f"❓ 未知命令: {cmd}  (输入 help 查看命令列表)")

        except KeyboardInterrupt:
            print("\n👋 退出")
            stream.stop()
            break
        except ValueError as e:
            print(f"❌ 参数错误: {e}")
        except Exception as e:
            print(f"❌ 错误: {e}")

if __name__ == "__main__":
    main()
