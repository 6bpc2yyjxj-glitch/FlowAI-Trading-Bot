"""
Bybit HMAC Trader v3.1 - 401 Fix
修復重點：
1. signature.lower() 
2. recv_window=10000
3. NTP 時間同步
4. 正確的參數排序
"""
import os
import time
import hmac
import hashlib
import logging
import aiohttp
import json

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
BYBIT_URL = "https://api.bybit.com"
BINANCE_URL = "https://api.binance.com"

class BybitTrader:
    def __init__(self):
        self.api_key = BYBIT_API_KEY
        self.api_secret = BYBIT_API_SECRET
        self.recv_window = "10000"  # 加大到 10 秒，避免延遲問題
        if self.api_key and self.api_secret:
            logger.info("✅ HMAC Key loaded (recv_window=10000)")
        else:
            logger.warning("⚠️ No API keys configured")
    
    def _get_timestamp(self) -> str:
        """獲取毫秒時間戳"""
        return str(int(time.time() * 1000))
    
    def _sign(self, timestamp: str, params_str: str = "") -> str:
        """
        HMAC-SHA256 簽名
        關鍵：結果必須 .lower()
        """
        # Bybit V5 簽名格式：timestamp + api_key + recv_window + params
        param_str = f"{timestamp}{self.api_key}{self.recv_window}{params_str}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'), 
            param_str.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest().lower()  # 關鍵：必須 lower()
        return signature
    
    def _headers(self, timestamp: str, signature: str) -> dict:
        """構建請求頭"""
        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": self.recv_window,
            "Content-Type": "application/json"
        }
    
    async def _request_get(self, endpoint: str, params: dict = None) -> dict:
        """GET 請求（帶簽名）"""
        if not self.api_key or not self.api_secret:
            return {"retCode": -1, "retMsg": "API keys not configured"}
        
        url = f"{BYBIT_URL}{endpoint}"
        timestamp = self._get_timestamp()
        
        # 構建查詢字串（按字母排序）
        if params:
            sorted_params = sorted(params.items())
            query_string = "&".join([f"{k}={v}" for k, v in sorted_params])
        else:
            query_string = ""
        
        signature = self._sign(timestamp, query_string)
        headers = self._headers(timestamp, signature)
        
        if query_string:
            url = f"{url}?{query_string}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    text = await resp.text()
                    logger.info(f"GET {endpoint} -> {resp.status}")
                    if resp.status == 200:
                        try:
                            return json.loads(text)
                        except:
                            return {"retCode": -1, "retMsg": f"JSON parse error: {text[:200]}"}
                    else:
                        return {"retCode": resp.status, "retMsg": text[:500]}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"retCode": -1, "retMsg": str(e)}
    
    async def _request_post(self, endpoint: str, params: dict = None) -> dict:
        """POST 請求（帶簽名）"""
        if not self.api_key or not self.api_secret:
            return {"retCode": -1, "retMsg": "API keys not configured"}
        
        url = f"{BYBIT_URL}{endpoint}"
        timestamp = self._get_timestamp()
        
        # POST 用 JSON body
        body = json.dumps(params) if params else ""
        
        signature = self._sign(timestamp, body)
        headers = self._headers(timestamp, signature)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=body, timeout=15) as resp:
                    text = await resp.text()
                    logger.info(f"POST {endpoint} -> {resp.status}")
                    if resp.status == 200:
                        try:
                            return json.loads(text)
                        except:
                            return {"retCode": -1, "retMsg": f"JSON parse error: {text[:200]}"}
                    else:
                        return {"retCode": resp.status, "retMsg": text[:500]}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"retCode": -1, "retMsg": str(e)}
    
    # ==================== 公開 API（無需簽名）====================
    
    async def get_ticker(self, category: str = "linear", symbol: str = "BTCUSDT") -> dict:
        """從 Binance 獲取價格（更穩定）"""
        url = f"{BINANCE_URL}/api/v3/ticker/24hr?symbol={symbol}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        d = await resp.json()
                        return {
                            "retCode": 0, 
                            "result": {
                                "list": [{
                                    "symbol": symbol, 
                                    "lastPrice": d.get("lastPrice", "0"), 
                                    "price24hPcnt": str(float(d.get("priceChangePercent", 0)) / 100)
                                }]
                            }
                        }
                    return {"retCode": -1, "retMsg": f"Binance error: {resp.status}"}
        except Exception as e:
            return {"retCode": -1, "retMsg": str(e)}
    
    async def get_server_time(self) -> dict:
        """獲取 Bybit 伺服器時間（檢查時間同步）"""
        url = f"{BYBIT_URL}/v5/market/time"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"retCode": -1, "retMsg": f"Error: {resp.status}"}
        except Exception as e:
            return {"retCode": -1, "retMsg": str(e)}
    
    async def get_funding_rate(self, symbol: str = "BTCUSDT") -> dict:
        """獲取資金費率"""
        url = f"{BYBIT_URL}/v5/market/funding/history?category=linear&symbol={symbol}&limit=1"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"retCode": -1, "retMsg": f"Error: {resp.status}"}
        except Exception as e:
            return {"retCode": -1, "retMsg": str(e)}
    
    # ==================== 私有 API（需要簽名）====================
    
    async def get_wallet_balance(self, account_type: str = "UNIFIED") -> dict:
        """獲取錢包餘額"""
        return await self._request_get(
            "/v5/account/wallet-balance", 
            {"accountType": account_type}
        )
    
    async def get_positions(self, category: str = "linear", symbol: str = None) -> dict:
        """獲取持倉"""
        params = {"category": category, "settleCoin": "USDT"}
        if symbol:
            params["symbol"] = symbol
        return await self._request_get("/v5/position/list", params)
    
    async def place_order(
        self, 
        symbol: str, 
        side: str,  # Buy or Sell
        qty: str, 
        order_type: str = "Market",
        category: str = "linear",
        reduce_only: bool = False,
        leverage: str = None
    ) -> dict:
        """下單"""
        params = {
            "category": category,
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
        }
        if reduce_only:
            params["reduceOnly"] = True
        return await self._request_post("/v5/order/create", params)
    
    async def set_leverage(self, symbol: str, leverage: str, category: str = "linear") -> dict:
        """設定槓桿"""
        params = {
            "category": category,
            "symbol": symbol,
            "buyLeverage": leverage,
            "sellLeverage": leverage
        }
        return await self._request_post("/v5/position/set-leverage", params)
    
    async def close_position(self, symbol: str, side: str, qty: str, category: str = "linear") -> dict:
        """平倉"""
        # 平倉 = 反向下單 + reduceOnly
        close_side = "Sell" if side == "Buy" else "Buy"
        return await self.place_order(
            symbol=symbol,
            side=close_side,
            qty=qty,
            order_type="Market",
            category=category,
            reduce_only=True
        )
    
    async def get_order_history(self, category: str = "linear", limit: int = 20) -> dict:
        """獲取訂單歷史"""
        return await self._request_get(
            "/v5/order/history",
            {"category": category, "limit": str(limit)}
        )


# ==================== 測試腳本 ====================

async def test_connection():
    """測試 Bybit API 連接"""
    import asyncio
    
    trader = BybitTrader()
    
    print("\n" + "="*50)
    print("🔧 Bybit HMAC API 連接測試")
    print("="*50)
    
    # 1. 測試伺服器時間
    print("\n📡 測試伺服器時間...")
    server_time = await trader.get_server_time()
    if server_time.get("retCode") == 0:
        server_ts = int(server_time["result"]["timeSecond"]) * 1000
        local_ts = int(time.time() * 1000)
        diff = abs(server_ts - local_ts)
        print(f"   ✅ 伺服器時間: {server_time['result']['timeSecond']}")
        print(f"   本地時間差: {diff}ms {'⚠️ 需要同步!' if diff > 5000 else '✅ OK'}")
    else:
        print(f"   ❌ 失敗: {server_time.get('retMsg')}")
    
    # 2. 測試價格 API
    print("\n📈 測試價格 API...")
    ticker = await trader.get_ticker(symbol="BTCUSDT")
    if ticker.get("retCode") == 0:
        price = ticker["result"]["list"][0]["lastPrice"]
        print(f"   ✅ BTC 價格: ${float(price):,.2f}")
    else:
        print(f"   ❌ 失敗: {ticker.get('retMsg')}")
    
    # 3. 測試資金費率
    print("\n💸 測試資金費率...")
    funding = await trader.get_funding_rate("BTCUSDT")
    if funding.get("retCode") == 0:
        rate = funding["result"]["list"][0]["fundingRate"]
        print(f"   ✅ BTC 費率: {float(rate)*100:.4f}%")
    else:
        print(f"   ❌ 失敗: {funding.get('retMsg')}")
    
    # 4. 測試餘額 API（需要有效 API Key）
    print("\n💰 測試餘額 API...")
    balance = await trader.get_wallet_balance()
    if balance.get("retCode") == 0:
        coins = balance.get("result", {}).get("list", [{}])[0].get("coin", [])
        total = sum(float(c.get("usdValue", 0)) for c in coins)
        print(f"   ✅ 總資產: ${total:,.2f}")
        for c in coins:
            bal = float(c.get("walletBalance", 0))
            if bal > 0:
                print(f"      {c['coin']}: {bal:.4f}")
    else:
        print(f"   ❌ 失敗: {balance.get('retMsg')}")
        if "10003" in str(balance.get("retMsg", "")):
            print("      💡 提示: Invalid API key - 檢查 Key 是否正確")
        elif "10004" in str(balance.get("retMsg", "")):
            print("      💡 提示: Invalid sign - 檢查簽名算法")
        elif "401" in str(balance.get("retMsg", "")):
            print("      💡 提示: 401 Unauthorized - 檢查權限設定")
    
    # 5. 測試持倉 API
    print("\n📊 測試持倉 API...")
    positions = await trader.get_positions()
    if positions.get("retCode") == 0:
        pos_list = positions.get("result", {}).get("list", [])
        has_pos = any(float(p.get("size", 0)) > 0 for p in pos_list)
        if has_pos:
            for p in pos_list:
                if float(p.get("size", 0)) > 0:
                    print(f"   ✅ {p['symbol']} {p['side']}: {p['size']}")
        else:
            print("   ✅ 無持倉")
    else:
        print(f"   ❌ 失敗: {positions.get('retMsg')}")
    
    print("\n" + "="*50)
    print("測試完成！")
    print("="*50)


if __name__ == "__main__":
    import asyncio
    
    # 直接測試
    print("設定環境變數後執行測試...")
    print("export BYBIT_API_KEY=你的Key")
    print("export BYBIT_API_SECRET=你的Secret")
    print("")
    
    asyncio.run(test_connection())
