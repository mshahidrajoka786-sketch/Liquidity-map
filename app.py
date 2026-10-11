from flask import Flask, jsonify
import ccxt
import pandas as pd
import numpy as np

app = Flask(__name__)

def fetch_and_calculate_smc(symbol='BTC/USDT', timeframe='1h', limit=100):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        swing_len = 5
        int_len = 2

        df['ext_high'] = df['high'].rolling(window=2 * swing_len + 1, center=True).apply(
            lambda x: x[swing_len] if x[swing_len] == max(x) else np.nan, raw=True
        )
        df['ext_low'] = df['low'].rolling(window=2 * swing_len + 1, center=True).apply(
            lambda x: x[swing_len] if x[swing_len] == min(x) else np.nan, raw=True
        )

        df['last_ext_high'] = df['ext_high'].ffill()
        df['last_ext_low'] = df['ext_low'].ffill()

        df['sweep_high'] = (df['high'] > df['last_ext_high'].shift(1)) & (df['close'] < df['last_ext_high'].shift(1))
        df['sweep_low'] = (df['low'] < df['last_ext_low'].shift(1)) & (df['close'] > df['last_ext_low'].shift(1))

        df['bullish_fvg'] = df['low'] > df['high'].shift(2)
        df['bearish_fvg'] = df['high'] < df['low'].shift(2)

        return df
    except Exception as e:
        return None

@app.route('/')
def index():
    df = fetch_and_calculate_smc('BTC/USDT', '1h', 100)
    
    if df is None or df.empty:
        return jsonify({"status": "error", "message": "Failed to fetch data from exchange"})

    latest = df.iloc[-1]

    result = {
        "status": "success",
        "symbol": "BTC/USDT",
        "time": str(latest['timestamp']),
        "close_price": float(latest['close']),
        "last_external_high": float(latest['last_ext_high']) if not np.isnan(latest['last_ext_high']) else None,
        "last_external_low": float(latest['last_ext_low']) if not np.isnan(latest['last_ext_low']) else None,
        "sweep_high_detected": bool(latest['sweep_high']),
        "sweep_low_detected": bool(latest['sweep_low']),
        "bullish_fvg": bool(latest['bullish_fvg']),
        "bearish_fvg": bool(latest['bearish_fvg'])
    }

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
