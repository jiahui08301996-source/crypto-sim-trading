# 虚拟币模拟交易平台 v1.0

实时对标 Binance 行情，支持穿针成交、滑点模拟。

## 快速启动

```bash
cd E:\CryptoSimTrading
pip install -r requirements.txt
python main.py
```

## 功能

- ✅ 实时 Binance 行情（WebSocket，逐笔成交）
- ✅ 穿针成交（K线影线触碰挂单价即成交）
- ✅ 滑点模拟（基础滑点 + 规模冲击）
- ✅ 止盈止损（自动触发）
- ✅ 市价单 / 限价单
- ✅ 账户持久化（data/ 目录）
- ✅ 支持 BTC ETH SOL BNB

## 命令示例

```
buy BTC 60000 0.1 tp=65000 sl=58000   # 挂买单，带止盈止损
sell ETH 3500 1.0                      # 挂卖单
mbuy SOL 10                            # 市价买10个SOL
price                                  # 查看实时价格
status                                 # 查看账户状态
history                                # 成交记录
```

## 文件结构

```
CryptoSimTrading/
├── main.py         # 主程序（命令行交互）
├── engine.py       # 撮合引擎（穿针+滑点）
├── exchange.py     # Binance WebSocket
├── account.py      # 账户系统
├── config.py       # 配置
├── data/           # 账户数据（自动生成）
└── logs/           # 日志（预留）
```
