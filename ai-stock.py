import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
from google import genai

app = Flask(__name__)
CORS(app)  # Επιτρέπει στο WordPress να "μιλάει" με τον server

# Ρύθμιση του Gemini API μέσω Environment Variable για ασφάλεια
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def get_ai_opinion(ticker, price, rsi, signal):
    """Στέλνει τα δεδομένα στο Gemini για ανάλυση στα Ελληνικά"""
    prompt = (f"Είσαι έμπειρος οικονομικός αναλυτής. Η μετοχή {ticker} έχει τιμή {price} "
              f"και δείκτη RSI {rsi}. Το τεχνικό σήμα είναι {signal}. "
              f"Δώσε μια σύντομη ανάλυση 2-3 προτάσεων στα Ελληνικά για την τάση.")
    
    try:
        # Διορθωμένη κλήση μοντέλου χωρίς το πρόθεμα "models/"
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Η ανάλυση AI δεν είναι διαθέσιμη προσωρινά. (Error: {str(e)})"

@app.route('/analyze', methods=['GET'])
def analyze():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "No symbol provided"}), 400

    try:
        # Λήψη δεδομένων από Yahoo Finance
        stock = yf.Ticker(symbol)
        df = stock.history(period="1y")

        if df.empty:
            return jsonify({"error": "Symbol not found"}), 404

        # Υπολογισμός RSI (Relative Strength Index)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = round(rsi.iloc[-1], 2)
        current_price = round(df['Close'].iloc[-1], 2)

        # Βασικό τεχνικό σήμα
        if current_rsi > 70:
            signal = "Overbought (Sell Signal)"
        elif current_rsi < 30:
            signal = "Oversold (Buy Signal)"
        else:
            signal = "Neutral (Wait)"

        # Λήψη ανάλυσης από το Gemini
        ai_analysis = get_ai_opinion(symbol, current_price, current_rsi, signal)

        return jsonify({
            "ticker": symbol,
            "price": current_price,
            "rsi": current_rsi,
            "signal": signal,
            "ai_analysis": ai_analysis
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ο Render απαιτεί τη χρήση της PORT από το περιβάλλον
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
