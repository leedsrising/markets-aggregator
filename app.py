from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from kalshiUtils import initialize_kalshi_client, fetch_kalshi_markets
from polymarketUtils import initialize_polymarket_client, fetch_polymarket_markets

app = Flask(__name__)
CORS(app)  # enables CORS for all routes

load_dotenv()
kalshi_client = initialize_kalshi_client()
polygon_client = initialize_polymarket_client()

@app.route('/api/markets')
def get_markets():
    try:
        kalshi_markets = fetch_kalshi_markets(kalshi_client)
        polymarket_markets = fetch_polymarket_markets(polygon_client)
        
        all_markets = {
            "kalshi": kalshi_markets,
            "polymarket": polymarket_markets,
        }
        return jsonify(all_markets)
    except Exception as e:
        print('Error fetching markets:', str(e))
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
