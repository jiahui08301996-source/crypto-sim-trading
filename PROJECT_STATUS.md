# 虚拟币模拟交易平台 — 项目进度

## 项目目标
做一个对标 OKX/Binance 实时行情的模拟交易平台，核心要求：
- 实时行情与真实交易所数据一致
- 支持1秒级穿针成交（K线影线触碰挂单即成交）
- 滑点模拟（基于订单规模）
- 最终做成可供用户使用的 Web App 或 Bot

---

## ✅ 已完成

### Phase 1 — 核心引擎（命令行MVP）
- [x] `config.py` — 配置文件（交易对、手续费、滑点参数）
- [x] `account.py` — 账户系统（余额、持仓、挂单、成交历史，JSON持久化）
- [x] `engine.py` — 撮合引擎（穿针检测、滑点计算、止盈止损自动触发）
- [x] `exchange.py` — Binance WebSocket 实时行情（逐笔成交 + 1秒K线）
- [x] `main.py` — 命令行交互界面（下单、查价、查仓、撤单、历史）
- [x] `requirements.txt` — 依赖：websocket-client
- [x] 单元测试通过（穿针成交、滑点、余额扣除 均正常）

### 已验证功能
- 挂限价单 → 价格触碰 → 穿针成交 ✅
- 滑点自动计算（规模越大滑点越大）✅
- 止盈止损自动触发 ✅
- 账户数据持久化到 `data/` 目录 ✅
- 支持 BTC ETH SOL BNB ✅

---

## 🚧 待完成

### Phase 2 — Web 前端（优先级：高）
- [ ] 用 FastAPI 做后端 API（RESTful + WebSocket推送）
- [ ] TradingView Lightweight Charts 接入（K线图）
- [ ] 下单面板（限价/市价/止盈止损）
- [ ] 账户面板（余额、持仓、挂单、成交历史）
- [ ] 响应式 UI（PC + 手机）

### Phase 3 — 多用户系统
- [ ] 用户注册/登录（JWT认证）
- [ ] 每个用户独立账户
- [ ] 排行榜（按盈亏排名）
- [ ] 账户重置功能

### Phase 4 — 进阶功能
- [ ] OKX 行情接入（双源对比）
- [ ] 更多交易对（DOGE、XRP、AVAX 等）
- [ ] 合约杠杆模拟
- [ ] 回测功能（用历史K线测试策略）
- [ ] 邀请码/分享功能

---

## 技术栈
- **后端**: Python + FastAPI + WebSocket
- **前端**: HTML/JS + TradingView Lightweight Charts
- **数据库**: SQLite（本地）→ PostgreSQL（上线后）
- **部署**: 服务器 $10-20/月（Vultr/Hetzner）

---

## 如何启动当前版本

```bash
cd E:\CryptoSimTrading
pip install -r requirements.txt
python main.py
```

初始资金 $100,000 USDT，实时对标 Binance。

### 常用命令
```
price                              # 查看实时价格
buy BTC 60000 0.1 tp=65000 sl=58000  # 挂买单（带止盈止损）
sell ETH 3500 1.0                  # 挂卖单
mbuy SOL 10                        # 市价买
status                             # 账户状态
orders                             # 查看挂单
history                            # 成交记录
```

---

## 下一步（下次对话继续）
**建议从 Phase 2 Web前端开始**，步骤：
1. 用 FastAPI 包装现有 engine/account 为 HTTP API
2. 做简单的 HTML 前端（K线图 + 下单面板）
3. WebSocket 推送实时价格到浏览器

---

*最后更新: 2026-04-18*
*项目路径: E:\CryptoSimTrading*
