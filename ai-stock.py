import yfinance as yf
from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai

# Ρύθμιση Gemini (Χρησιμοποιώντας τη νέα βιβλιοθήκη google-genai)
client = genai.Client(api_key="AIzaSyACAn--HpeMIDQGZ90RnGe1-VXkcEHtzn0")

app = Flask(__name__)
CORS(app)


def get_ai_opinion(ticker, price, rsi, signal):
    prompt = f"Η μετοχή {ticker} έχει τιμή {price} και RSI {rsi}. Το σήμα είναι {signal}. Δώσε μια σύντομη ανάλυση 2 προτάσεων στα Ελληνικά για το τι πρέπει να προσέξει ένας επενδυτής."
    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    return response.text


@app.route('/analyze', methods=['GET'])
def analyze():
    symbol = request.args.get('symbol', 'TSLA').upper()
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="3mo")

        if hist.empty:
            return jsonify({"error": "No data found"}), 404

        # Υπολογισμός Δεδομένων
        price = round(float(hist['Close'].iloc[-1]), 2)

        # Υπολογισμός RSI
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_val = 100 - (100 / (1 + rs))
        rsi = round(float(rsi_val.iloc[-1]), 2)

        signal = "Hold"
        if rsi > 70:
            signal = "Sell (Overbought)"
        elif rsi < 30:
            signal = "Buy (Oversold)"

        # Τώρα που έχουμε τις μεταβλητές, καλούμε το AI
        ai_text = get_ai_opinion(symbol, price, rsi, signal)

        return jsonify({
            "ticker": symbol,
            "price": price,
            "rsi": rsi,
            "signal": signal,
            "ai_analysis": ai_text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)