import ccxt
import requests
import time
import json
import os
import math
from datetime import datetime

# Configuración KuCoin Futures [web:24]
KUCOIN_FUTURES_KEY = os.getenv('KUCOIN_FUTURES_KEY')
KUCOIN_FUTURES_SECRET = os.getenv('KUCOIN_FUTURES_SECRET')
KUCOIN_FUTURES_PASSPHRASE = os.getenv('KUCOIN_FUTURES_PASSPHRASE')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# FIX: Safe debug para None (evita TypeError [:8]) [web:35]
def safe_slice(key, length=8):
    return (key[:length] if key else 'NONE')

# Validación + debug SAFE
missing_vars = []
if not KUCOIN_FUTURES_KEY: missing_vars.append('KUCOIN_FUTURES_KEY')
if not KUCOIN_FUTURES_SECRET: missing_vars.append('KUCOIN_FUTURES_SECRET')
if not KUCOIN_FUTURES_PASSPHRASE: missing_vars.append('KUCOIN_FUTURES_PASSPHRASE')
if not TELEGRAM_TOKEN: missing_vars.append('TELEGRAM_TOKEN')
if not CHAT_ID: missing_vars.append('CHAT_ID')

if missing_vars:
    print(f"❌ FALTAN VARIABLES en Railway: {', '.join(missing_vars)}")
    print(f"DEBUG SAFE: KEY={safe_slice(KUCOIN_FUTURES_KEY)} SECRET={safe_slice(KUCOIN_FUTURES_SECRET)} PASS={safe_slice(KUCOIN_FUTURES_PASSPHRASE)} TG_TOKEN={safe_slice(TELEGRAM_TOKEN)}")
    exit(1)

print("✅ Todas las variables OK - Iniciando KuCoin Futures...")

exchange = ccxt.kucoinfutures({
    'apiKey': KUCOIN_FUTURES_KEY,
    'secret': KUCOIN_FUTURES_SECRET,
    'password': KUCOIN_FUTURES_PASSPHRASE,
    'sandbox': False,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': msg}, timeout=10)
        print(f"📱 Telegram: {msg[:50]}...")
    except Exception as e:
        print(f"❌ Telegram: {e}")

async def analizar_mercados():
    try:
        enviar_telegram("🔥 KuCoin v16.1 LIVE - Analizando TOP markets...")
        markets = exchange.load_markets()
        usdt_pairs = [s for s in markets if ':USDT' in s][:15]
        
        balance = exchange.fetch_balance()
        usdt = balance.get('USDT', {}).get('free', 0)
        enviar_telegram(f"💰 USDT Futures: ${usdt:.2f}")
        
        best = {'symbol': '', 'score': 0, 'dir': ''}
        for symbol in usdt_pairs[:8]:
            ticker = exchange.fetch_ticker(symbol)
            ohlcv = exchange.fetch_ohlcv(symbol, '1m', limit=20)
            closes = [c[4] for c in ohlcv[-6:]]
            roc = (closes[-1] - closes[0]) / closes[0] * 100
            vol_m = ticker['quoteVolume'] / 1e6
            score = abs(roc)*8 + min(vol_m/10, 25)
            
            dir_ = "🟢 LONG" if roc > 0.3 else "🔴 SHORT" if roc < -0.3 else "➡️ NEUTRAL"
            if score > best['score']:
                best = {'symbol': symbol.replace(':USDT', '/USDT'), 'score': score, 'dir': dir_, 'roc': roc}
        
        msg = f"📊 TOP: {best['symbol']} {best['dir']} {best['score']:.1f}% ROC:{best['roc']:.2f}%"
        enviar_telegram(msg)
        
        if best['score'] > 70:
            enviar_telegram(f"🎯 ALERTA TRADE: {best['symbol']} {best['dir']}!")
            # order = exchange.create_market_buy_order(best['symbol'], 5)  # 5 contratos test
    except Exception as e:
        enviar_telegram(f"❌ Error análisis: {str(e)[:100]}")

def main_loop():
    enviar_telegram("🚀 KuCoin v16.1 FIXED - 24/7 scalping iniciado!")
    while True:
        try:
            import asyncio
            asyncio.run(analizar_mercados())
        except KeyboardInterrupt:
            print("🛑 Stop")
            break
        except Exception as e:
            print(e)
            enviar_telegram(f"❌ Loop: {str(e)}")
        time.sleep(300)

if __name__ == "__main__":
    main_loop()
