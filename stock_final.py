import os
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd

app = Flask(__name__)
CORS(app)

def get_ai_opinion(ticker, data):
    api_key = os.environ.get("GEMINI_API_KEY")
    # Χτυπάμε ΑΠΕΥΘΕΙΑΣ το σταθερό endpoint v1
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = (f"Ανάλυσε τη μετοχή {ticker}: Τιμή ${data['price']}, RSI {data['rsi']}, "
              f"P/E {data['pe']}, Margins {data['margins']}. Σήμα: {data['signal']}. "
              f"Δώσε μια σύντομη ανάλυση 2 προτάσεων στα Ελληνικά.")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        result = response.json()
        
        # Εξαγωγή κειμένου από το JSON response της Google
        if 'candidates' in result:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            error_msg = result.get('error', {}).get('message', 'Unknown API Error')
            return f"AI Error: {error_msg}"
    except Exception as e:
        return f"Connection Error: {str(e)}"

@app.route('/analyze', methods=['GET'])
def analyze():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "No symbol"}), 400

    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1y")
        info = stock.info

        if df.empty:
            return jsonify({"error": "No data"}), 404

        # RSI Calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        current_rsi = round(100 - (100 / (1 + rs)).iloc[-1], 2)
        
        current_data = {
            "ticker": symbol,
            "price": round(df['Close'].iloc[-1], 2),
            "rsi": current_rsi,
            "pe": info.get('forwardPE', 'N/A'),
            "margins": f"{round(info.get('profitMargins', 0) * 100, 2)}%",
            "signal": "Overbought" if current_rsi > 70 else ("Oversold" if current_rsi < 30 else "Neutral")
        }

        current_data["ai_analysis"] = get_ai_opinion(symbol, current_data)
        return jsonify(current_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
