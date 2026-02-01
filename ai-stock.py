import os
import google.generativeai as genai  # Η εναλλακτική βιβλιοθήκη

# Ρύθμιση του API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_ai_opinion(ticker, data):
    prompt = (f"Ανάλυσε τη μετοχή {ticker}: Τιμή ${data['price']}, RSI {data['rsi']}, "
              f"P/E {data['pe']}, Margins {data['margins']}. Σήμα: {data['signal']}. "
              f"Δώσε μια σύντομη ανάλυση 2 προτάσεων στα Ελληνικά.")
    
    try:
        # Αυτή η βιβλιοθήκη χρησιμοποιεί το 'GenerativeModel'
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"






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
