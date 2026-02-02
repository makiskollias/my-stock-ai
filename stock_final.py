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
    
    # Αυστηρό Prompt για να μην αποκαλύπτεται η πηγή
    system_instruction = (
        "Είσαι ένας κορυφαίος οικονομικός αναλυτής με ειδίκευση στις αγορές των ΗΠΑ. "
        "Μην αναφέρεις ΠΟΤΕ ότι είσαι τεχνητή νοημοσύνη, μοντέλο γλώσσας ή το όνομα Gemini. "
        "Η ανάλυσή σου πρέπει να είναι αυστηρή, επαγγελματική και να εστιάζει στα νούμερα."
    )
    
    prompt = (
        f"{system_instruction}\n\n"
        f"Ανάλυσε τη μετοχή {ticker} με τα εξής δεδομένα:\n"
        f"- Τιμή: ${data['price']}\n"
        f"- RSI: {data['rsi']}\n"
        f"- P/E Ratio: {data['pe']}\n"
        f"- Περιθώρια Κέρδους: {data['margins']}\n"
        f"- Τεχνικό Σήμα: {data['signal']}\n\n"
        f"Δώσε μια σύντομη ανάλυση 2-3 προτάσεων στα Ελληνικά, ξεκινώντας απευθείας με την ουσία."
    )

    # Η διαδικασία Auto-Discovery παραμένει ίδια για να μην έχουμε πάλι 404
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        models_resp = requests.get(list_url)
        models_data = models_resp.json()
        target_model = next((m['name'] for m in models_data.get('models', []) 
                            if 'generateContent' in m.get('supportedGenerationMethods', []) 
                            and 'flash' in m['name']), None)

        if not target_model: return "Ανάλυση μη διαθέσιμη προσωρινά."

        analyze_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        resp = requests.post(analyze_url, json=payload, timeout=30)
        result = resp.json()

        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return "Σφάλμα κατά την επεξεργασία της ανάλυσης."


















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
