from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from kalshiUtils import initialize_kalshi_api, fetch_kalshi_markets

app = Flask(__name__)
CORS(app)  # enables CORS for all routes

load_dotenv()
kalshi_api = initialize_kalshi_api()

@app.route('/api/markets')
def get_markets():
    try:
        kalshi_markets = fetch_kalshi_markets(kalshi_api)
        
        all_markets = {
            "kalshi": kalshi_markets,
            # "polymarket": polymarket_markets,  # Uncomment when implemented
        }
        return jsonify(all_markets)
    except Exception as e:
        print('Error fetching markets:', str(e))
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
