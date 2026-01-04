import ccxt
import requests
import time
import json
import os
import math
from datetime import datetime

KUCOIN_FUTURES_KEY = os.getenv('KUCOIN_FUTURES_KEY')
KUCOIN_FUTURES_SECRET = os.getenv('KUCOIN_FUTURES_SECRET')
KUCOIN_FUTURES_PASSPHRASE = os.getenv('KUCOIN_FUTURES_PASSPHRASE')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not all([KUCOIN_FUTURES_KEY, KUCOIN_FUTURES_SECRET, KUCOIN_FUTURES_PASSPHRASE]):
    print("❌ FALTA .env")
    exit()

exchange = ccxt.kucoinfutures({
    'apiKey': KUCOIN_FUTURES_KEY,
    'secret': KUCOIN_FUTURES_SECRET,
    'password': KUCOIN_FUTURES_PASSPHRASE,
    'sandbox': False,  # REAL
    'enableRateLimit': True,
    'options': {'defaultType': 'swap'},
})

markets = exchange.load_markets()
pairs = [s for s in markets if 'USDT:USDT' in s and markets[s]['active']]
print(f"🔥 {len(pairs)} mercados")

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': msg}, timeout=5)
    except: pass

def get_lunarcrush_social(symbol):
    try:
        coins = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana'}
        coin = coins.get(symbol.replace('/USDT:USDT', ''), 'bitcoin')
        resp = requests.get(f"https://lunarcrush.com/api4/public/coins/{coin}", timeout=10)
        return min(resp.json().get('data', [{}])[0].get('social_score', 50)/100, 1.0)
    except: return 0.5

def calcular_score(symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        ohlcv = exchange.fetch_ohlcv(symbol, '5m', limit=20)
        change = ticker['percentage']
        volume = ticker['quoteVolume']
        price = ticker['last']
        closes = [c[4] for c in ohlcv]
        momentum = (price - sum(closes[-5:])/5) / (sum(closes[-5:])/5)
        vol_score = min(volume/3e8, 1.0) if volume else 0.5
        social = get_lunarcrush_social(symbol)
        trend = max(min(change/5, 1.0), 0)
        score = social*0.25 + abs(momentum)*0.4 + vol_score*0.2 + trend*0.1 + 0.05
        return score, {'score': score*100, 'momentum': momentum}
    except: return 0, {'error': 'fail'}

def get_trade_amount(symbol):
    market = markets[symbol]
    contract_size = market['contractSize']
    price = exchange.fetch_ticker(symbol)['last']
    value_per_contract = contract_size * price
    return max(1, math.floor(100 / value_per_contract))

def main_loop():
    tickers = exchange.fetch_tickers()
    sorted_pairs = sorted(pairs, key=lambda s: tickers[s]['quoteVolume'] if s in tickers else 0, reverse=True)[:20]
    
    enviar_telegram("🚀 v15 KuCoin BOT CORREGIDO live! $290 OK | Score>65%")
    
    while True:
        try:
            balance = exchange.fetch_balance()
            usdt = balance['USDT']['free']
            enviar_telegram(f"💰 USDT: ${usdt:.2f}")
            
            best_pair, best_score, best_data = None, 0, {}
            for symbol in sorted_pairs[:15]:
                score, data = calcular_score(symbol)
                if score > best_score:
                    best_score, best_pair, best_data = score, symbol, data
            
            msg = f"🎯 TOP: {best_pair} {best_score*100:.0f}%"
            
            if best_score > 0.65 and usdt > 100 and best_pair:
                side = 'buy' if best_data.get('momentum', 0) > 0 else 'sell'
                amount = get_trade_amount(best_pair)
                
                try:
                    exchange.set_leverage(20, best_pair)
                    order = exchange.create_market_order(best_pair, side, amount)
                    msg += f" ✅ {side.upper()} {amount}ct! {order['id']}"
                except Exception as e:
                    msg += f" ⚠️ {str(e)[:30]}"
            
            enviar_telegram(msg)
            print(f"{datetime.now()}: {msg}")
            
        except KeyboardInterrupt:
            print("🛑 Parado")
            break
        except Exception as e:
            print(e)
            enviar_telegram(f"❌ {str(e)}")
        
        time.sleep(300)

if __name__ == "__main__":
    main_loop()
