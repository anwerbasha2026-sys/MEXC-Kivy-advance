"""Public MEXC market-data scanner. No authenticated trading endpoints."""
import re
import time
import requests

BASE = "https://api.mexc.com/api/v3"
EXCLUDED_BASE_ASSETS = {"USDC","FDUSD","USDE","TUSD","DAI","USDP","BUSD","PYUSD","USDD","USD1","USDS","USDJ","USDR","USN","UST","USTC","FRAX","LUSD","GUSD","MIM","CRVUSD","GHO","USDB","USDY","USD0","USYC","USDTB","USDQ","USDV","EURC","EURS","EURI","EUROC","EUR","GBP","EURT","AEUR","WBTC","WETH","STETH","CBETH","BETH"}
EXCLUDED_SUFFIXES = ("3L","3S","5L","5S","2L","2S","4L","4S","UP","DOWN","BULL","BEAR")
TOKENIZED_STOCK_BASES = {"REGNON","TXNON","XOMON","AAPLON","TSLAON","NVDAON","MSFTON","AMZNON","METAON","GOOGLON","AMDON","NFLXON","COINON","MSTRON","SPYON","QQQON","BRKAON","LLYON","AVGOON","JPMON","VON","WMTON","KOON","PEPON","PGON","JNJON","UNHON","HDON","MAON","DISON"}


def is_clean_pair(symbol, full_name=""):
    if not symbol.endswith("USDT"): return False
    base = symbol[:-4].upper()
    if not base or base in EXCLUDED_BASE_ASSETS or base in TOKENIZED_STOCK_BASES: return False
    if base.endswith(EXCLUDED_SUFFIXES): return False
    if any(k in str(full_name).lower() for k in ("tokenized","ondo","leveraged","3x","5x","etf","stock","shares")): return False
    return bool(re.match(r"^[A-Z0-9]+$", base))


def request_json(path, params=None, timeout=8):
    response = requests.get(f"{BASE}/{path}", params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_price(symbol):
    try:
        data = request_json("ticker/price", {"symbol": symbol}, timeout=5)
        return float(data["price"])
    except Exception:
        return None


def get_symbols():
    info = request_json("exchangeInfo", timeout=20)
    allowed = set()
    for item in info.get("symbols", []):
        symbol = str(item.get("symbol", "")).upper()
        if item.get("quoteAsset") != "USDT": continue
        if str(item.get("status", "")).upper() not in ("1", "ENABLED"): continue
        if not bool(item.get("isSpotTradingAllowed", True)): continue
        types = [str(x).upper() for x in item.get("orderTypes", [])]
        if types and "MARKET" not in types: continue
        perms = [str(x).upper() for x in item.get("permissions", [])]
        if perms and "SPOT" not in perms: continue
        if is_clean_pair(symbol, item.get("fullName", "")): allowed.add(symbol)
    tickers = request_json("ticker/24hr", timeout=15)
    ranked = []
    for item in tickers:
        sym = str(item.get("symbol", "")).upper()
        if sym not in allowed: continue
        try:
            if float(item.get("quoteVolume", 0)) >= 50000:
                ranked.append((float(item.get("quoteVolume", 0)), sym))
        except (TypeError, ValueError): pass
    ranked.sort(reverse=True)
    return [sym for _, sym in ranked[:100]]


def ema(data, period):
    if len(data) < period: return []
    mult = 2 / (period + 1)
    values = [sum(data[:period]) / period]
    for value in data[period:]: values.append((value-values[-1])*mult+values[-1])
    return values


def rsi(closes, period=14):
    if len(closes) < period + 1: return []
    gains=[]; losses=[]
    for i in range(1,len(closes)):
        d=closes[i]-closes[i-1]; gains.append(max(d,0)); losses.append(max(-d,0))
    ag=sum(gains[:period])/period; al=sum(losses[:period])/period
    out=[100.0 if al==0 else 100-(100/(1+ag/al))]
    for i in range(period,len(gains)):
        ag=((ag*(period-1))+gains[i])/period; al=((al*(period-1))+losses[i])/period
        out.append(100.0 if al==0 else 100-(100/(1+ag/al)))
    return out


def macd(closes):
    if len(closes)<35: return [],[],[]
    fast=ema(closes,12); slow=ema(closes,26)
    line=[a-b for a,b in zip(fast[14:],slow)]
    signal=ema(line,9)
    if not signal: return [],[],[]
    aligned=line[8:]
    hist=[a-b for a,b in zip(aligned,signal)]
    return aligned,signal,hist


def candles(symbol, interval, limit=300):
    return request_json("klines", {"symbol":symbol,"interval":interval,"limit":limit}, timeout=8)


def trend(symbol, interval):
    data=candles(symbol,interval,300)
    if len(data)<202: return False
    closes=[float(x[4]) for x in data[:-1]]
    e9=ema(closes,9); e21=ema(closes,21); e200=ema(closes,200)
    return bool(e9 and e21 and e200 and closes[-1]>e200[-1] and e9[-1]>e21[-1]>e200[-1])


def order_book_ok(symbol):
    book=request_json("depth", {"symbol":symbol,"limit":20}, timeout=5)
    bids=book.get("bids") or []; asks=book.get("asks") or []
    if not bids or not asks: return False
    buy=sum(float(p)*float(q) for p,q in bids)
    sell=sum(float(p)*float(q) for p,q in asks)
    return buy>sell>0


def check_symbol(symbol, cfg):
    data=candles(symbol,"5m",300)
    if len(data)<202: return False,0.0,"بيانات غير كافية"
    closed=data[:-1]
    op=[float(x[1]) for x in closed]; hi=[float(x[2]) for x in closed]
    lo=[float(x[3]) for x in closed]; cl=[float(x[4]) for x in closed]
    vol=[float(x[5]) for x in closed]; price=cl[-1]
    e9=ema(cl,9); e21=ema(cl,21); e200=ema(cl,200)
    if not (e9 and e21 and e200 and e9[-1]>e21[-1]>e200[-1] and price>e9[-1]):
        return False,price,"اتجاه EMA غير صاعد"
    if cfg["enable_rsi_filter"]:
        values=rsi(cl)
        if not values or not min(cfg["rsi_min"],cfg["rsi_max"])<=values[-1]<=max(cfg["rsi_min"],cfg["rsi_max"]):
            return False,price,"فلتر RSI لم يتحقق"
    if cfg["enable_macd_filter"]:
        line,sig,hist=macd(cl)
        if not hist or not (line[-1]>sig[-1] and hist[-1]>0): return False,price,"فلتر MACD لم يتحقق"
    avg=sum(vol[-10:-1])/9
    if avg<=0 or vol[-1]<=avg*cfg["vol_multiplier"]: return False,price,"حجم التداول ضعيف"
    total=sum(vol[-20:])
    vwap=sum(((hi[i]+lo[i]+cl[i])/3)*vol[i] for i in range(-20,0))/total if total else price
    if price<vwap: return False,price,"السعر دون VWAP"
    if cfg["enable_low_price_change_filter"]:
        limit=abs(cfg["max_price_change_pct"])
        body=abs(price-op[-1])/op[-1]*100 if op[-1]>0 else 999
        change=abs(price-cl[-2])/cl[-2]*100 if cl[-2]>0 else 999
        spread=(hi[-1]-lo[-1])/lo[-1]*100 if lo[-1]>0 else 999
        if max(body,change)>limit or spread>limit*1.6: return False,price,"التغير السعري مرتفع"
    if not trend(symbol,"15m") or not trend(symbol,"60m"): return False,price,"تأكيد الاتجاه على الأطر الأعلى لم يتحقق"
    if cfg["enable_order_book_filter"] and not order_book_ok(symbol): return False,price,"ضغط دفتر الأوامر غير مناسب"
    return True,price,f"EMA + VWAP + Volume {vol[-1]/avg:.2f}x"


def scan_market(cfg, logger, should_stop=lambda: False):
    symbols=get_symbols()
    if not symbols: raise RuntimeError("لم يتم جلب أزواج Spot من MEXC")
    logger(f"تم تحميل {len(symbols)} زوج Spot. الفحص يبدأ الآن.")
    for index,symbol in enumerate(symbols,1):
        if should_stop():
            logger("تم إيقاف الفحص.")
            return None
        try:
            ok,price,reason=check_symbol(symbol,cfg)
            if ok: return symbol,price,reason
            if index%5==0: logger(f"[{index}/{len(symbols)}] {symbol}: {reason}")
        except Exception as exc:
            logger(f"[{index}/{len(symbols)}] {symbol}: تعذر الفحص ({exc})")
        time.sleep(.12)
    return None
