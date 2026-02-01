"""
FlowAI v5.2 Complete - VPS Edition
功能：
- 價格分析：BTC/ETH/SOL/GOLD
- AI 分析：Grok 情緒解讀
- 交易功能：Long/Short/Close
- Order Flow：CVD/Liquidation 追蹤
- 資金費率套利計算
"""
import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import aiohttp

from bybit_trader_hmac_fixed import BybitTrader

# ==================== 配置 ====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
trader = BybitTrader()

# ==================== 輔助函數 ====================

async def get_fear_greed():
    """獲取恐懼貪婪指數"""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.alternative.me/fng/", timeout=10) as r:
                if r.status == 200:
                    d = await r.json()
                    return d.get("data", [{}])[0]
    except:
        pass
    return None

async def call_grok(prompt):
    """呼叫 Grok AI"""
    if not GROK_API_KEY:
        return "Grok API not set"
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": "Bearer " + GROK_API_KEY, "Content-Type": "application/json"}
    payload = {
        "model": "grok-4-1-fast-reasoning", 
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.7
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers=headers, json=payload, timeout=90) as r:
                if r.status == 200:
                    d = await r.json()
                    return d["choices"][0]["message"]["content"]
                return "API Error: " + str(r.status)
    except Exception as e:
        return "Error: " + str(e)

def is_admin(update: Update) -> bool:
    """檢查是否為管理員"""
    return str(update.effective_chat.id) == ADMIN_CHAT_ID

# ==================== 指令處理 ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """開始選單"""
    msg = "🎯 FlowAI v5.2 Complete\n"
    msg += "━━━━━━━━━━━━━━━━\n"
    msg += "📊 市場分析\n"
    msg += "/btc - BTC 深度分析\n"
    msg += "/eth - ETH 分析\n"
    msg += "/sol - SOL 分析\n"
    msg += "/gold - 黃金分析\n"
    msg += "/radar - 全景報告\n\n"
    msg += "📈 交易工具\n"
    msg += "/flow - Order Flow 分析\n"
    msg += "/signal - 交易信號\n"
    msg += "/funding - 資金費率\n"
    msg += "/arb - 套利計算\n"
    msg += "/calendar - 財經日曆\n\n"
    msg += "💹 交易執行（管理員）\n"
    msg += "/balance - 查餘額\n"
    msg += "/position - 查持倉\n"
    msg += "/long <幣種> <數量> - 做多\n"
    msg += "/short <幣種> <數量> - 做空\n"
    msg += "/close <幣種> - 平倉\n\n"
    msg += "/status - 系統狀態\n"
    msg += "━━━━━━━━━━━━━━━━"
    await update.message.reply_text(msg)

async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """BTC 深度分析"""
    await update.message.reply_text("🔶 獲取BTC數據...")
    
    ticker = await trader.get_ticker(symbol="BTCUSDT")
    fng = await get_fear_greed()
    funding = await trader.get_funding_rate("BTCUSDT")
    
    if ticker and ticker.get("retCode") == 0:
        d = ticker["result"]["list"][0]
        price = float(d["lastPrice"])
        change = float(d["price24hPcnt"]) * 100
        fv = fng.get("value", "N/A") if fng else "N/A"
        
        # 獲取資金費率
        rate_str = "N/A"
        if funding and funding.get("retCode") == 0:
            rate = float(funding["result"]["list"][0]["fundingRate"])
            rate_str = f"{rate*100:.4f}%"
        
        # Grok 深度分析
        prompt = f"""BTC 即時數據：
- 價格: ${price:,.2f}
- 24h漲跌: {change:+.2f}%
- 恐懼貪婪指數: {fv}
- 資金費率: {rate_str}

作為專業交易員，用繁體中文分析：
1. 市場情緒（極度恐懼/恐懼/中性/貪婪/極度貪婪）
2. 技術面（支撐/阻力位）
3. 資金流向（資金費率解讀）
4. 短線建議（做多/做空/觀望）
限 120 字內。"""
        
        analysis = await call_grok(prompt)
        
        result = "🔶 BTC/USDT 深度分析\n"
        result += "━━━━━━━━━━━━━━━━\n"
        result += "💰 價格: $" + format(price, ",.2f") + "\n"
        result += "📊 24h: " + str(round(change, 2)) + "%\n"
        result += "😱 恐懼貪婪: " + str(fv) + "\n"
        result += "💸 資金費率: " + rate_str + "\n"
        result += "━━━━━━━━━━━━━━━━\n"
        result += "📝 " + analysis
    else:
        result = "❌ 獲取失敗"
    
    await update.message.reply_text(result)

async def eth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ETH 分析"""
    await update.message.reply_text("🔷 獲取ETH數據...")
    ticker = await trader.get_ticker(symbol="ETHUSDT")
    if ticker and ticker.get("retCode") == 0:
        d = ticker["result"]["list"][0]
        price = float(d["lastPrice"])
        change = float(d["price24hPcnt"]) * 100
        result = "🔷 ETH/USDT\n━━━━━━━━━━━━━━━━\n"
        result += "💰 $" + format(price, ",.2f") + "\n"
        result += "📊 " + str(round(change, 2)) + "%"
    else:
        result = "❌ 獲取失敗"
    await update.message.reply_text(result)

async def sol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SOL 分析"""
    await update.message.reply_text("🟣 獲取SOL數據...")
    ticker = await trader.get_ticker(symbol="SOLUSDT")
    if ticker and ticker.get("retCode") == 0:
        d = ticker["result"]["list"][0]
        price = float(d["lastPrice"])
        change = float(d["price24hPcnt"]) * 100
        result = "🟣 SOL/USDT\n━━━━━━━━━━━━━━━━\n"
        result += "💰 $" + format(price, ",.2f") + "\n"
        result += "📊 " + str(round(change, 2)) + "%"
    else:
        result = "❌ 獲取失敗"
    await update.message.reply_text(result)

async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """黃金分析"""
    await update.message.reply_text("🥇 分析黃金...")
    
    # 最新黃金價格：$4,865.35（根據 Grok 資訊）
    prompt = """查詢 XAUUSD 黃金最新數據，用繁體中文分析：
1. 即時價格和今日漲跌
2. 地緣政治避險需求
3. 美元走勢影響
4. 短線方向建議（支撐/阻力位）
限 100 字內。"""
    
    analysis = await call_grok(prompt)
    result = "🥇 黃金分析\n━━━━━━━━━━━━━━━━\n" + analysis
    await update.message.reply_text(result)

async def radar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """全景報告"""
    await update.message.reply_text("🌐 生成全景報告...")
    
    btc_t = await trader.get_ticker(symbol="BTCUSDT")
    eth_t = await trader.get_ticker(symbol="ETHUSDT")
    sol_t = await trader.get_ticker(symbol="SOLUSDT")
    fng = await get_fear_greed()
    
    msg = "🌐 FlowAI 全景報告\n━━━━━━━━━━━━━━━━\n"
    
    if fng:
        v = int(fng.get("value", 50))
        status = "極度恐懼" if v <= 25 else "恐懼" if v <= 45 else "中性" if v <= 55 else "貪婪" if v <= 75 else "極度貪婪"
        msg += "😱 恐懼貪婪: " + str(v) + " (" + status + ")\n\n"
    
    for name, t in [("BTC", btc_t), ("ETH", eth_t), ("SOL", sol_t)]:
        if t and t.get("retCode") == 0:
            d = t["result"]["list"][0]
            p = float(d["lastPrice"])
            c = float(d["price24hPcnt"]) * 100
            e = "🟢" if c >= 0 else "🔴"
            msg += e + " " + name + ": $" + format(p, ",.2f") + " (" + str(round(c, 1)) + "%)\n"
    
    msg += "\n⏰ " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await update.message.reply_text(msg)

async def flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Order Flow 分析"""
    await update.message.reply_text("📊 分析 Order Flow...")
    
    ticker = await trader.get_ticker(symbol="BTCUSDT")
    if ticker and ticker.get("retCode") == 0:
        d = ticker["result"]["list"][0]
        price = float(d["lastPrice"])
        
        prompt = f"""BTC 當前價格 ${price:,.2f}
作為 Order Flow 專家，用繁體中文分析：
1. 大單動向（鯨魚買/賣力道）
2. CVD（累積成交量差）趨勢
3. 清算數據（多空爆倉比）
4. 關鍵價位（支撐/阻力）
5. 短線操作建議
限 120 字內。"""
        
        analysis = await call_grok(prompt)
        result = "📊 Order Flow 分析\n━━━━━━━━━━━━━━━━\n"
        result += "💰 BTC: $" + format(price, ",.2f") + "\n\n"
        result += analysis
    else:
        result = "❌ 獲取失敗"
    
    await update.message.reply_text(result)

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """交易信號"""
    await update.message.reply_text("🎯 生成交易信號...")
    
    ticker = await trader.get_ticker(symbol="BTCUSDT")
    fng = await get_fear_greed()
    
    if ticker and ticker.get("retCode") == 0:
        d = ticker["result"]["list"][0]
        price = float(d["lastPrice"])
        fv = int(fng.get("value", 50)) if fng else 50
        
        prompt = f"""BTC ${price:,.2f}，恐懼貪婪指數 {fv}
給出明確交易信號：
- 方向：做多 / 做空 / 觀望
- 進場價位
- 止損價位
- 目標價位
- 信心指數（1-10）
- 簡短理由（30字內）
用繁體中文回答。"""
        
        analysis = await call_grok(prompt)
        result = "🎯 交易信號\n━━━━━━━━━━━━━━━━\n" + analysis + "\n\n⚠️ 僅供參考，風險自負"
    else:
        result = "❌ 獲取失敗"
    
    await update.message.reply_text(result)

async def funding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """資金費率"""
    await update.message.reply_text("💸 查詢資金費率...")
    
    btc_funding = await trader.get_funding_rate("BTCUSDT")
    eth_funding = await trader.get_funding_rate("ETHUSDT")
    sol_funding = await trader.get_funding_rate("SOLUSDT")
    
    msg = "💸 資金費率（8小時結算）\n━━━━━━━━━━━━━━━━\n"
    
    for name, f in [("BTC", btc_funding), ("ETH", eth_funding), ("SOL", sol_funding)]:
        if f and f.get("retCode") == 0:
            rate = float(f["result"]["list"][0]["fundingRate"])
            annual = rate * 3 * 365 * 100
            e = "🟢" if rate >= 0 else "🔴"
            msg += e + " " + name + ": " + str(round(rate*100, 4)) + "% (年化" + str(round(annual, 1)) + "%)\n"
    
    msg += "\n📈 正費率 = 多頭付空頭（看多情緒）\n"
    msg += "📉 負費率 = 空頭付多頭（看空情緒）\n"
    msg += "\n💡 用 /arb 計算套利收益"
    
    await update.message.reply_text(msg)

async def arb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """套利計算"""
    principal = 300000
    if context.args:
        try:
            principal = float(context.args[0])
        except:
            pass
    
    # 獲取實際費率
    btc_funding = await trader.get_funding_rate("BTCUSDT")
    rate = 0.01  # 預設 0.01%
    if btc_funding and btc_funding.get("retCode") == 0:
        rate = abs(float(btc_funding["result"]["list"][0]["fundingRate"]) * 100)
    
    daily = principal * (rate * 3 / 100)
    monthly = daily * 30
    annual = daily * 365
    annual_rate = rate * 3 * 365
    
    result = "💰 資金費率套利計算\n━━━━━━━━━━━━━━━━\n"
    result += "本金: NT$" + format(principal, ",.0f") + "\n"
    result += "當前費率: " + str(round(rate, 4)) + "%/8h\n\n"
    result += "📈 預估收益\n"
    result += "日收益: NT$" + format(daily, ",.0f") + "\n"
    result += "月收益: NT$" + format(monthly, ",.0f") + "\n"
    result += "年收益: NT$" + format(annual, ",.0f") + "\n"
    result += "年化: " + str(round(annual_rate, 1)) + "%\n\n"
    result += "📝 策略：現貨買入 + 永續做空\n"
    result += "💡 /arb 500000 - 計算不同本金"
    
    await update.message.reply_text(result)

async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """財經日曆"""
    await update.message.reply_text("📅 獲取財經日曆...")
    
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""今天是 {today}，列出本週重要財經事件：
1. 美國經濟數據（CPI/GDP/非農）
2. 聯準會相關（FOMC/官員講話）
3. 加密貨幣事件（ETF/期貨到期）

格式：日期 | 事件 | 重要性（1-5顆星）
用繁體中文，最多列 8 個事件。"""
    
    analysis = await call_grok(prompt)
    result = "📅 財經日曆\n━━━━━━━━━━━━━━━━\n" + analysis
    
    await update.message.reply_text(result)

# ==================== 交易功能（管理員限定）====================

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查詢餘額"""
    if not is_admin(update):
        await update.message.reply_text("⛔ 僅管理員可用")
        return
    
    await update.message.reply_text("💰 查詢餘額...")
    
    try:
        result = await trader.get_wallet_balance()
        if result and result.get("retCode") == 0:
            coins = result.get("result", {}).get("list", [{}])[0].get("coin", [])
            msg = "💰 Bybit 餘額\n━━━━━━━━━━━━━━━━\n"
            total = 0
            for c in coins:
                bal = float(c.get("walletBalance", 0))
                if bal > 0:
                    usd = float(c.get("usdValue", 0))
                    total += usd
                    msg += "💎 " + c["coin"] + ": " + str(round(bal, 4)) + " ($" + format(usd, ",.2f") + ")\n"
            if total == 0:
                msg += "📭 帳戶無餘額\n"
            msg += "\n💵 總資產: $" + format(total, ",.2f")
        else:
            err = result.get("retMsg", "未知錯誤") if result else "連接失敗"
            msg = "❌ " + err
    except Exception as e:
        msg = "❌ 錯誤: " + str(e)
    
    await update.message.reply_text(msg)

async def position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查詢持倉"""
    if not is_admin(update):
        await update.message.reply_text("⛔ 僅管理員可用")
        return
    
    await update.message.reply_text("📊 查詢持倉...")
    
    try:
        result = await trader.get_positions()
        if result and result.get("retCode") == 0:
            positions = result.get("result", {}).get("list", [])
            msg = "📊 當前持倉\n━━━━━━━━━━━━━━━━\n"
            has_pos = False
            for p in positions:
                size = float(p.get("size", 0))
                if size > 0:
                    has_pos = True
                    pnl = float(p.get("unrealisedPnl", 0))
                    entry = float(p.get("avgPrice", 0))
                    liq = p.get("liqPrice", "N/A")
                    e = "🟢" if pnl >= 0 else "🔴"
                    msg += e + " " + p["symbol"] + " " + p["side"] + "\n"
                    msg += "   數量: " + str(size) + "\n"
                    msg += "   進場: $" + format(entry, ",.2f") + "\n"
                    msg += "   盈虧: $" + format(pnl, ",.2f") + "\n"
                    msg += "   清算: " + str(liq) + "\n\n"
            if not has_pos:
                msg += "📭 無持倉"
        else:
            err = result.get("retMsg", "未知錯誤") if result else "連接失敗"
            msg = "❌ " + err
    except Exception as e:
        msg = "❌ 錯誤: " + str(e)
    
    await update.message.reply_text(msg)

async def long_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """做多"""
    if not is_admin(update):
        await update.message.reply_text("⛔ 僅管理員可用")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("📝 用法: /long BTC 0.001\n（幣種 數量）")
        return
    
    symbol = context.args[0].upper() + "USDT"
    qty = context.args[1]
    
    await update.message.reply_text(f"📈 開多 {symbol} 數量 {qty}...")
    
    try:
        result = await trader.place_order(symbol=symbol, side="Buy", qty=qty)
        if result and result.get("retCode") == 0:
            order_id = result["result"].get("orderId", "")
            msg = "✅ 做多成功！\n"
            msg += "幣種: " + symbol + "\n"
            msg += "數量: " + qty + "\n"
            msg += "訂單ID: " + order_id
        else:
            err = result.get("retMsg", "未知錯誤") if result else "連接失敗"
            msg = "❌ 下單失敗: " + err
    except Exception as e:
        msg = "❌ 錯誤: " + str(e)
    
    await update.message.reply_text(msg)

async def short_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """做空"""
    if not is_admin(update):
        await update.message.reply_text("⛔ 僅管理員可用")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("📝 用法: /short BTC 0.001\n（幣種 數量）")
        return
    
    symbol = context.args[0].upper() + "USDT"
    qty = context.args[1]
    
    await update.message.reply_text(f"📉 開空 {symbol} 數量 {qty}...")
    
    try:
        result = await trader.place_order(symbol=symbol, side="Sell", qty=qty)
        if result and result.get("retCode") == 0:
            order_id = result["result"].get("orderId", "")
            msg = "✅ 做空成功！\n"
            msg += "幣種: " + symbol + "\n"
            msg += "數量: " + qty + "\n"
            msg += "訂單ID: " + order_id
        else:
            err = result.get("retMsg", "未知錯誤") if result else "連接失敗"
            msg = "❌ 下單失敗: " + err
    except Exception as e:
        msg = "❌ 錯誤: " + str(e)
    
    await update.message.reply_text(msg)

async def close_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """平倉"""
    if not is_admin(update):
        await update.message.reply_text("⛔ 僅管理員可用")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("📝 用法: /close BTC\n（自動平掉該幣種所有持倉）")
        return
    
    symbol = context.args[0].upper() + "USDT"
    
    await update.message.reply_text(f"🔄 平倉 {symbol}...")
    
    try:
        # 先查詢持倉
        positions = await trader.get_positions(symbol=symbol)
        if positions and positions.get("retCode") == 0:
            pos_list = positions.get("result", {}).get("list", [])
            closed = False
            for p in pos_list:
                if p.get("symbol") == symbol and float(p.get("size", 0)) > 0:
                    size = p.get("size")
                    side = p.get("side")
                    result = await trader.close_position(symbol, side, size)
                    if result and result.get("retCode") == 0:
                        msg = "✅ 平倉成功！\n"
                        msg += "幣種: " + symbol + "\n"
                        msg += "方向: " + side + "\n"
                        msg += "數量: " + size
                        closed = True
                    else:
                        msg = "❌ 平倉失敗: " + result.get("retMsg", "未知")
            if not closed:
                msg = "📭 該幣種無持倉"
        else:
            msg = "❌ 查詢持倉失敗"
    except Exception as e:
        msg = "❌ 錯誤: " + str(e)
    
    await update.message.reply_text(msg)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """系統狀態"""
    grok_status = "✅" if GROK_API_KEY else "❌"
    bybit_status = "✅" if trader.api_key else "❌"
    
    # 測試連接
    server_time = await trader.get_server_time()
    time_status = "✅" if server_time.get("retCode") == 0 else "❌"
    
    msg = "⚙️ FlowAI 系統狀態\n━━━━━━━━━━━━━━━━\n"
    msg += "🤖 Grok AI: " + grok_status + "\n"
    msg += "💹 Bybit API: " + bybit_status + "\n"
    msg += "⏰ 時間同步: " + time_status + "\n"
    msg += "📊 價格源: Binance\n"
    msg += "👤 Admin: " + ADMIN_CHAT_ID + "\n"
    msg += "⏰ " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n"
    msg += "版本: v5.2 Complete VPS"
    
    await update.message.reply_text(msg)

# ==================== 主程式 ====================

def main():
    if not TELEGRAM_TOKEN:
        print("❌ No TELEGRAM_TOKEN")
        return
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 基本指令
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("status", status))
    
    # 市場分析
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("eth", eth))
    app.add_handler(CommandHandler("sol", sol))
    app.add_handler(CommandHandler("gold", gold))
    app.add_handler(CommandHandler("radar", radar))
    
    # 交易工具
    app.add_handler(CommandHandler("flow", flow))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("funding", funding))
    app.add_handler(CommandHandler("arb", arb))
    app.add_handler(CommandHandler("calendar", calendar))
    
    # 交易執行
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("position", position))
    app.add_handler(CommandHandler("long", long_cmd))
    app.add_handler(CommandHandler("short", short_cmd))
    app.add_handler(CommandHandler("close", close_cmd))
    
    print("🚀 FlowAI v5.2 Complete 啟動!")
    print("="*40)
    print("Grok AI:", "✅" if GROK_API_KEY else "❌")
    print("Bybit API:", "✅" if trader.api_key else "❌")
    print("Admin:", ADMIN_CHAT_ID)
    print("="*40)
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
