import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import google.generativeai as genai
from google.generativeai.types import RequestOptions

# 1. Αρχικοποίηση Flask & CORS
app = Flask(__name__)
CORS(app)

# 2. Ρύθμιση της βιβλιοθήκης Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_ai_opinion(ticker, data):
    prompt = (f"Ανάλυσε τη μετοχή {ticker}: Τιμή ${data['price']}, RSI {data['rsi']}, "
              f"P/E {data['pe']}, Margins {data['margins']}. Σήμα: {data['signal']}. "
              f"Δώσε μια σύντομη ανάλυση 2 προτάσεων στα Ελληνικά.")
    
    try:
        # Δημιουργούμε το μοντέλο χρησιμοποιώντας απευθείας το όνομα 
        # που δείχνει στη σταθερή έκδοση v1
        model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')
        
        # Απλή κλήση χωρίς RequestOptions που μπερδεύουν τη βιβλιοθήκη
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"

@app.route('/analyze', methods=['GET'])
def analyze():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "No symbol provided"}), 400

    try:
        # Λήψη δεδομένων από το Yahoo Finance
        stock = yf.Ticker(symbol)
        df = stock.history(period="1y")
        info = stock.info

        if df.empty:
            return jsonify({"error": f"No data found for symbol {symbol}"}), 404

        # Υπολογισμός RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        current_rsi = round(100 - (100 / (1 + rs)).iloc[-1], 2)
        
        # Θεμελιώδη Μεγέθη
        pe_ratio = info.get('forwardPE', 'N/A')
        profit_margins = info.get('profitMargins', 0) * 100
        
        # Προετοιμασία των δεδομένων
        current_data = {
            "ticker": symbol,
            "price": round(df['Close'].iloc[-1], 2),
            "rsi": current_rsi,
            "pe": pe_ratio,
            "margins": f"{round(profit_margins, 2)}%",
            "signal": "Overbought" if current_rsi > 70 else ("Oversold" if current_rsi < 30 else "Neutral")
        }

        # Προσθήκη της AI ανάλυσης
        current_data["ai_analysis"] = get_ai_opinion(symbol, current_data)
        
        return jsonify(current_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 3. Εκκίνηση του Server
if __name__ == '__main__':
    # Το Render παρέχει τη θύρα μέσω της μεταβλητής περιβάλλοντος PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
