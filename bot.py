import ccxt
import requests
import time
import json
import os
import math
from datetime import datetime

# Configuración de KuCoin Futures con ccxt [web:24][web:27]
KUCOIN_FUTURES_KEY = os.getenv('KUCOIN_FUTURES_KEY')
KUCOIN_FUTURES_SECRET = os.getenv('KUCOIN_FUTURES_SECRET')
KUCOIN_FUTURES_PASSPHRASE = os.getenv('KUCOIN_FUTURES_PASSPHRASE')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Validación de variables de entorno para Railway [web:35]
if not all([KUCOIN_FUTURES_KEY, KUCOIN_FUTURES_SECRET, KUCOIN_FUTURES_PASSPHRASE, TELEGRAM_TOKEN, CHAT_ID]):
    print("❌ FALTA CONFIGURAR VARIABLES en Railway: KUCOIN_FUTURES_* y TELEGRAM_*")
    print(f"DEBUG: KEY={KUCOIN_FUTURES_KEY[:8] or 'NONE'} SECRET={KUCOIN_FUTURES_SECRET[:8] or 'NONE'} PASS={KUCOIN_FUTURES_PASSPHRASE[:8] or 'NONE'}")
    exit(1)

exchange = ccxt.kucoinfutures({
    'apiKey': KUCOIN_FUTURES_KEY,
    'secret': KUCOIN_FUTURES_SECRET,
    'password': KUCOIN_FUTURES_PASSPHRASE,
    'sandbox': False,  # Cambia a True para testnet
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

def enviar_telegram(msg):
    """Envía mensaje a Telegram [web:38]"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print(f"⚠️ Sin Telegram: {msg[:50]}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': msg}, timeout=10)
        print(f"📱 Telegram OK: {msg[:50]}...")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

async def analizar_mercados():
    """Analiza mercados KuCoin Futures principales"""
    try:
        enviar_telegram("🔥 KuCoin BOT v16 LIVE - Analizando mercados...")
        markets = exchange.load_markets()
        usdt_pairs = [symbol for symbol in markets if symbol.endswith('USDT:USDT')][:20]  # Top 20 USDT perpetual
        
        balance = exchange.fetch_balance()
        usdt_balance = balance['USDT']['free']
        enviar_telegram(f"💰 Balance USDT: ${usdt_balance:.2f}\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        top_oportunidad = None
        max_score = 0
        
        for symbol in usdt_pairs[:10]:  # Analiza top 10 para eficiencia
            try:
                ticker = exchange.fetch_ticker(symbol)
                ohlcv = exchange.fetch_ohlcv(symbol, '1m', limit=60)
                
                # Momentum simple (ROC 5min) + volumen score [web:23]
                close_prices = [c[4] for c in ohlcv[-5:]]
                roc = (close_prices[-1] - close_prices[0]) / close_prices[0] * 100
                vol_score = ticker['quoteVolume'] / 1e9  # Vol en billones USDT
                
                score = abs(roc) * 10 + min(vol_score * 10, 30)  # Score 0-100 aprox
                direccion = "🟢 LONG" if roc > 0 else "🔴 SHORT"
                
                if score > max_score:
                    max_score = score
                    top_oportunidad = f"{symbol} {direccion} Score:{score:.1f}% Vol:${ticker['quoteVolume']/1e6:.0f}M"
                
                enviar_telegram(f"📊 {symbol}: ROC {roc:.2f}% Vol:${ticker['quoteVolume']/1e6:.0f}M Score:{score:.1f}%")
                
            except Exception as e:
                print(f"Error {symbol}: {e}")
                continue
        
        if top_oportunidad and max_score > 65:  # Umbral ajustable, seguro para scalping [memory:1]
            enviar_telegram(f"🎯 TOP OPORTUNIDAD: {top_oportunidad}")
            # Aquí lógica de trade: descomenta para LIVE
            # order = exchange.create_market_buy_order(symbol.split(':')[0], 1, params={'leverage': 10})
            # enviar_telegram(f"✅ TRADE EJECUTADO: {order['id']}")
        else:
            enviar_telegram("⏳ Sideways market - Esperando >65% score")
            
    except Exception as e:
        enviar_telegram(f"❌ Error mercados: {str(e)}")
        print(e)

def main_loop():
    """Loop principal cada 5min"""
    enviar_telegram("🚀 KuCoin IA BOT v16 iniciado! Análisis cada 5min 24/7")
    while True:
        try:
            import asyncio
            asyncio.run(analizar_mercados())
        except KeyboardInterrupt:
            print("🛑 Parado manual")
            break
        except Exception as e:
            print(f"Error loop: {e}")
            enviar_telegram(f"❌ {str(e)}")
        
        time.sleep(300)  # 5min

if __name__ == "__main__":
    main_loop()

