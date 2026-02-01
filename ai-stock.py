import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
from google import genai

app = Flask(__name__)
CORS(app)


# Ορίζουμε τον client χωρίς να επιβάλλουμε έκδοση χειροκίνητα
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def get_ai_opinion(ticker, data):
    prompt = (f"Ανάλυσε τη μετοχή {ticker}: Τιμή ${data['price']}, RSI {data['rsi']}, "
              f"P/E {data['pe']}, Margins {data['margins']}. Σήμα: {data['signal']}. "
              f"Δώσε μια σύντομη ανάλυση 2 προτάσεων στα Ελληνικά.")
    
    # Δοκιμάζουμε τις 3 πιο πιθανές ονομασίες μοντέλου σε σειρά
    model_names = ["gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-pro"]
    
    for model_name in model_names:
        try:
            response = client.models.generate_content(
                model=model_name, 
                contents=prompt
            )
            return response.text
        except Exception as e:
            last_error = str(e)
            continue # Δοκίμασε το επόμενο μοντέλο αν το τωρινό βγάλει 404
            
    return f"AI Error: Όλα τα μοντέλα απέτυχαν. Τελευταίο σφάλμα: {last_error}"










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

        # Τεχνικά (RSI)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        current_rsi = round(100 - (100 / (1 + rs)).iloc[-1], 2)
        
        # Θεμελιώδη (Fundamentals)
        pe_ratio = info.get('forwardPE', 'N/A')
        profit_margins = info.get('profitMargins', 0) * 100
        
        current_data = {
            "ticker": symbol,
            "price": round(df['Close'].iloc[-1], 2),
            "rsi": current_rsi,
            "pe": pe_ratio,
            "margins": f"{round(profit_margins, 2)}%",
            "signal": "Overbought" if current_rsi > 70 else ("Oversold" if current_rsi < 30 else "Neutral")
        }

        current_data["ai_analysis"] = get_ai_opinion(symbol, current_data)
        return jsonify(current_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
