# config.py - 配置文件

# 交易所 WebSocket
BINANCE_WS_URL = "wss://stream.binance.com:9443/stream"
OKX_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"

# 支持的交易对
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

# 模拟账户初始资金 (USDT)
INITIAL_BALANCE = 100_000.0

# 滑点模拟参数
SLIPPAGE_RATE = 0.0005       # 0.05% 基础滑点
TAKER_FEE = 0.0005           # 0.05% Taker手续费
MAKER_FEE = 0.0002           # 0.02% Maker手续费

# 数据存储
DATA_DIR = "data"
LOG_DIR = "logs"
