"""
FlowAI Order Flow Module v2.0
升級功能:
- CVD (Cumulative Volume Delta) 計算
- Liquidation 追蹤
- Grok X Semantic Search API 整合
- 鯨魚活動偵測
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
import logging

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== 配置 ====================

BYBIT_WS_URL = "wss://stream.bybit.com/v5/public/linear"
BYBIT_REST_URL = "https://api.bybit.com"
GROK_API_KEY = ""  # 環境變數設定

# ==================== CVD 計算器 ====================

class CVDCalculator:
    """
    Cumulative Volume Delta 計算器
    CVD = 累積(買入量 - 賣出量)
    正值 = 買盤主導
    負值 = 賣盤主導
    """
    
    def __init__(self, window_size: int = 1000):
        self.trades = deque(maxlen=window_size)
        self.cvd = 0.0
        self.buy_volume = 0.0
        self.sell_volume = 0.0
    
    def add_trade(self, trade: Dict):
        """
        添加交易
        trade: {side: 'Buy'/'Sell', qty: float, price: float, timestamp: int}
        """
        self.trades.append(trade)
        
        qty = float(trade.get('qty', 0))
        side = trade.get('side', '')
        
        if side == 'Buy':
            self.buy_volume += qty
            self.cvd += qty
        elif side == 'Sell':
            self.sell_volume += qty
            self.cvd -= qty
    
    def get_cvd(self) -> float:
        """獲取當前 CVD"""
        return self.cvd
    
    def get_delta(self) -> float:
        """獲取 Delta（買賣量差）"""
        return self.buy_volume - self.sell_volume
    
    def get_ratio(self) -> float:
        """獲取買賣比"""
        total = self.buy_volume + self.sell_volume
        if total == 0:
            return 0.5
        return self.buy_volume / total
    
    def get_stats(self) -> Dict:
        """獲取統計數據"""
        return {
            "cvd": self.cvd,
            "buy_volume": self.buy_volume,
            "sell_volume": self.sell_volume,
            "delta": self.get_delta(),
            "buy_ratio": self.get_ratio(),
            "trade_count": len(self.trades)
        }
    
    def reset(self):
        """重置"""
        self.trades.clear()
        self.cvd = 0.0
        self.buy_volume = 0.0
        self.sell_volume = 0.0


# ==================== 清算追蹤器 ====================

class LiquidationTracker:
    """
    清算追蹤器
    追蹤多空爆倉數據
    """
    
    def __init__(self, window_minutes: int = 60):
        self.liquidations = deque()
        self.window = timedelta(minutes=window_minutes)
        self.long_liquidations = 0.0  # 多頭爆倉金額
        self.short_liquidations = 0.0  # 空頭爆倉金額
    
    def add_liquidation(self, liq: Dict):
        """
        添加清算
        liq: {side: 'Buy'/'Sell', qty: float, price: float, timestamp: int}
        """
        now = datetime.now()
        liq['datetime'] = now
        self.liquidations.append(liq)
        
        value = float(liq.get('qty', 0)) * float(liq.get('price', 0))
        side = liq.get('side', '')
        
        # Buy = 空頭被清算（價格上漲）
        # Sell = 多頭被清算（價格下跌）
        if side == 'Buy':
            self.short_liquidations += value
        elif side == 'Sell':
            self.long_liquidations += value
        
        self._cleanup()
    
    def _cleanup(self):
        """清理過期數據"""
        cutoff = datetime.now() - self.window
        while self.liquidations and self.liquidations[0].get('datetime', datetime.now()) < cutoff:
            old = self.liquidations.popleft()
            value = float(old.get('qty', 0)) * float(old.get('price', 0))
            if old.get('side') == 'Buy':
                self.short_liquidations -= value
            else:
                self.long_liquidations -= value
    
    def get_stats(self) -> Dict:
        """獲取統計數據"""
        self._cleanup()
        total = self.long_liquidations + self.short_liquidations
        
        return {
            "long_liquidations_usd": self.long_liquidations,
            "short_liquidations_usd": self.short_liquidations,
            "total_liquidations_usd": total,
            "long_ratio": self.long_liquidations / total if total > 0 else 0.5,
            "count": len(self.liquidations),
            "window_minutes": self.window.total_seconds() / 60
        }
    
    def get_bias(self) -> str:
        """
        獲取市場偏向
        多頭爆倉多 → 市場偏空
        空頭爆倉多 → 市場偏多
        """
        if self.long_liquidations > self.short_liquidations * 1.5:
            return "BEARISH"  # 多頭被獵殺
        elif self.short_liquidations > self.long_liquidations * 1.5:
            return "BULLISH"  # 空頭被獵殺
        return "NEUTRAL"


# ==================== 鯨魚偵測器 ====================

class WhaleDetector:
    """
    鯨魚偵測器
    偵測大單交易和大倉位變動
    """
    
    def __init__(self, whale_threshold_usd: float = 100000):
        self.threshold = whale_threshold_usd
        self.whale_trades = deque(maxlen=100)
    
    def check_trade(self, trade: Dict) -> Optional[Dict]:
        """
        檢查是否為鯨魚交易
        返回 None 或 鯨魚交易詳情
        """
        qty = float(trade.get('qty', 0))
        price = float(trade.get('price', 0))
        value = qty * price
        
        if value >= self.threshold:
            whale_trade = {
                "side": trade.get('side'),
                "qty": qty,
                "price": price,
                "value_usd": value,
                "timestamp": trade.get('timestamp'),
                "datetime": datetime.now().isoformat()
            }
            self.whale_trades.append(whale_trade)
            return whale_trade
        
        return None
    
    def get_recent_whales(self, limit: int = 10) -> List[Dict]:
        """獲取最近的鯨魚交易"""
        return list(self.whale_trades)[-limit:]
    
    def get_whale_bias(self) -> Tuple[str, float]:
        """
        獲取鯨魚偏向
        返回: (偏向, 信心度)
        """
        if not self.whale_trades:
            return "NEUTRAL", 0.0
        
        buy_value = sum(w['value_usd'] for w in self.whale_trades if w['side'] == 'Buy')
        sell_value = sum(w['value_usd'] for w in self.whale_trades if w['side'] == 'Sell')
        total = buy_value + sell_value
        
        if total == 0:
            return "NEUTRAL", 0.0
        
        buy_ratio = buy_value / total
        
        if buy_ratio > 0.6:
            return "BULLISH", buy_ratio
        elif buy_ratio < 0.4:
            return "BEARISH", 1 - buy_ratio
        return "NEUTRAL", 0.5


# ==================== Grok 整合 ====================

class GrokSentimentAnalyzer:
    """
    Grok X Semantic Search 整合
    分析 X/Twitter 上的市場情緒
    """
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or GROK_API_KEY
        self.api_url = "https://api.x.ai/v1/chat/completions"
    
    async def analyze_sentiment(self, symbol: str, context: Dict = None) -> Dict:
        """
        分析市場情緒
        使用 Grok 的 X 語義搜索能力
        """
        if not self.api_key:
            return {"error": "API key not configured"}
        
        # 構建分析提示
        context_str = ""
        if context:
            context_str = f"""
當前市場數據:
- CVD: {context.get('cvd', 'N/A')}
- 買賣比: {context.get('buy_ratio', 'N/A')}
- 清算偏向: {context.get('liquidation_bias', 'N/A')}
- 鯨魚偏向: {context.get('whale_bias', 'N/A')}
"""
        
        prompt = f"""搜索並分析 X/Twitter 上關於 {symbol} 的最新情緒:

{context_str}

請分析:
1. 社群整體情緒 (極度恐懼/恐懼/中性/貪婪/極度貪婪)
2. KOL 觀點摘要 (頂級交易員在說什麼)
3. 熱門話題標籤
4. 情緒分數 (0-100, 50=中性)
5. 短線建議 (做多/做空/觀望)

用繁體中文回答，限 150 字內。"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "grok-4-1-fast-reasoning",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, 
                    headers=headers, 
                    json=payload, 
                    timeout=60
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        analysis = data["choices"][0]["message"]["content"]
                        return {
                            "symbol": symbol,
                            "analysis": analysis,
                            "timestamp": datetime.now().isoformat()
                        }
                    return {"error": f"API error: {resp.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def search_kol_positions(self, symbol: str) -> Dict:
        """
        搜索 KOL 倉位
        """
        if not self.api_key:
            return {"error": "API key not configured"}
        
        prompt = f"""搜索 X/Twitter 上頂級加密貨幣交易員關於 {symbol} 的最新倉位聲明:

找出:
1. 公開做多的 KOL
2. 公開做空的 KOL  
3. 觀望/減倉的 KOL
4. 整體 KOL 共識

用繁體中文回答，列出具體帳號名稱（如果找到）。"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "grok-4-1-fast-reasoning",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, 
                    headers=headers, 
                    json=payload, 
                    timeout=60
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "symbol": symbol,
                            "kol_positions": data["choices"][0]["message"]["content"],
                            "timestamp": datetime.now().isoformat()
                        }
                    return {"error": f"API error: {resp.status}"}
        except Exception as e:
            return {"error": str(e)}


# ==================== Order Flow 引擎 ====================

class OrderFlowEngine:
    """
    Order Flow 主引擎
    整合所有分析組件
    """
    
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.cvd = CVDCalculator()
        self.liquidations = LiquidationTracker()
        self.whales = WhaleDetector()
        self.grok = GrokSentimentAnalyzer()
    
    async def get_recent_trades(self, limit: int = 1000) -> List[Dict]:
        """從 Bybit 獲取最近交易"""
        url = f"{BYBIT_REST_URL}/v5/market/recent-trade?category=linear&symbol={self.symbol}&limit={limit}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("retCode") == 0:
                            return data["result"]["list"]
        except Exception as e:
            logger.error(f"Get trades error: {e}")
        return []
    
    async def analyze(self) -> Dict:
        """
        執行完整分析
        返回 Order Flow 報告
        """
        # 1. 獲取最近交易
        trades = await self.get_recent_trades()
        
        # 2. 處理交易數據
        self.cvd.reset()
        for trade in trades:
            self.cvd.add_trade(trade)
            whale = self.whales.check_trade(trade)
        
        # 3. 獲取 CVD 統計
        cvd_stats = self.cvd.get_stats()
        
        # 4. 獲取清算統計
        liq_stats = self.liquidations.get_stats()
        liq_bias = self.liquidations.get_bias()
        
        # 5. 獲取鯨魚統計
        whale_bias, whale_confidence = self.whales.get_whale_bias()
        recent_whales = self.whales.get_recent_whales(5)
        
        # 6. Grok 情緒分析
        context = {
            "cvd": cvd_stats["cvd"],
            "buy_ratio": cvd_stats["buy_ratio"],
            "liquidation_bias": liq_bias,
            "whale_bias": whale_bias
        }
        sentiment = await self.grok.analyze_sentiment(self.symbol, context)
        
        # 7. 綜合判斷
        signals = []
        if cvd_stats["buy_ratio"] > 0.55:
            signals.append("CVD_BULLISH")
        elif cvd_stats["buy_ratio"] < 0.45:
            signals.append("CVD_BEARISH")
        
        if whale_bias == "BULLISH":
            signals.append("WHALE_BULLISH")
        elif whale_bias == "BEARISH":
            signals.append("WHALE_BEARISH")
        
        if liq_bias == "BULLISH":
            signals.append("LIQ_BULLISH")
        elif liq_bias == "BEARISH":
            signals.append("LIQ_BEARISH")
        
        # 計算整體偏向
        bullish_count = sum(1 for s in signals if "BULLISH" in s)
        bearish_count = sum(1 for s in signals if "BEARISH" in s)
        
        if bullish_count > bearish_count:
            overall_bias = "BULLISH"
            confidence = bullish_count / max(len(signals), 1)
        elif bearish_count > bullish_count:
            overall_bias = "BEARISH"
            confidence = bearish_count / max(len(signals), 1)
        else:
            overall_bias = "NEUTRAL"
            confidence = 0.5
        
        return {
            "symbol": self.symbol,
            "timestamp": datetime.now().isoformat(),
            "cvd": cvd_stats,
            "liquidations": liq_stats,
            "liquidation_bias": liq_bias,
            "whale_bias": whale_bias,
            "whale_confidence": whale_confidence,
            "recent_whales": recent_whales,
            "signals": signals,
            "overall_bias": overall_bias,
            "overall_confidence": confidence,
            "sentiment_analysis": sentiment
        }
    
    def format_report(self, analysis: Dict) -> str:
        """格式化報告"""
        cvd = analysis.get("cvd", {})
        liq = analysis.get("liquidations", {})
        
        report = f"""
📊 FlowAI Order Flow 報告
━━━━━━━━━━━━━━━━━━━━━━━
🎯 {analysis['symbol']} @ {analysis['timestamp'][:19]}

💹 CVD 分析
├── CVD: {cvd.get('cvd', 0):,.0f}
├── 買入量: {cvd.get('buy_volume', 0):,.2f}
├── 賣出量: {cvd.get('sell_volume', 0):,.2f}
└── 買賣比: {cvd.get('buy_ratio', 0.5)*100:.1f}%

💥 清算數據（1小時）
├── 多頭爆倉: ${liq.get('long_liquidations_usd', 0):,.0f}
├── 空頭爆倉: ${liq.get('short_liquidations_usd', 0):,.0f}
└── 偏向: {analysis.get('liquidation_bias', 'N/A')}

🐋 鯨魚活動
├── 偏向: {analysis.get('whale_bias', 'N/A')}
└── 信心: {analysis.get('whale_confidence', 0)*100:.0f}%

🎯 綜合判斷
├── 信號: {', '.join(analysis.get('signals', []))}
├── 偏向: {analysis.get('overall_bias', 'N/A')}
└── 信心: {analysis.get('overall_confidence', 0)*100:.0f}%

📝 AI 情緒分析
{analysis.get('sentiment_analysis', {}).get('analysis', 'N/A')}
━━━━━━━━━━━━━━━━━━━━━━━
"""
        return report


# ==================== 主程式 ====================

async def main():
    """測試 Order Flow 引擎"""
    print("🚀 FlowAI Order Flow Engine v2.0")
    print("="*50)
    
    # 初始化引擎
    engine = OrderFlowEngine("BTCUSDT")
    
    # 執行分析
    print("\n📊 Analyzing BTCUSDT Order Flow...")
    analysis = await engine.analyze()
    
    # 輸出報告
    report = engine.format_report(analysis)
    print(report)
    
    # 輸出 JSON（供 API 使用）
    print("\n📦 JSON Output:")
    print(json.dumps(analysis, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
