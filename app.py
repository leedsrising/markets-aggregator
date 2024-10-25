import os
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
import logging

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from kalshiUtils import initialize_kalshi_client, fetch_kalshi_markets
from polymarketUtils import initialize_polymarket_clob_client, fetch_polymarket_markets
from polymarketUtils import fetch_polymarket_markets
from utils import query_recent, upsert_markets, find_duplicate_markets

from config import SOURCES, SOURCE_TABLES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Suppress httpx logs
logging.getLogger('httpx').setLevel(logging.WARNING)
# Suppress werkzeug logs
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
CORS(app)

load_dotenv()
kalshi_client = initialize_kalshi_client()
polygon_client = initialize_polymarket_clob_client()

@app.route('/api/markets')
def get_markets():
    try:
        current_time = datetime.now(datetime_timezone.utc)
        all_markets = []

        for source in SOURCES:
            recent_markets = query_recent(current_time - timedelta(seconds=5))
            #if there are recently pulled markets for [source], just return them
            if recent_markets:
                logging.info(f'Markets not fetched for {source}. Already have source data updated <5min ago.')
                markets = [dict(market, source=source) for market in recent_markets]
            #otherwise, fetch updated marketes for [source]
            else:
                if source == 'kalshi': markets = fetch_kalshi_markets(kalshi_client)
                elif source == 'polymarket': markets = fetch_polymarket_markets(polygon_client)
                else: logging.error(f'Unknown source: {source}')
                upsert_markets(markets, SOURCE_TABLES[source])
                
            all_markets.extend(markets)

        return jsonify(markets)
    except Exception as e:
        logging.error(f'Error fetching markets: {e}', exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/deduplicate_markets', methods=['POST'])
def deduplicate_markets():
    try:
        markets = request.json.get('markets', [])
        if not markets:
            return jsonify({"error": "No markets provided"}), 400
        
        deduplicated_markets = find_duplicate_markets(markets)
        
        return jsonify({"deduplicated_markets": deduplicated_markets})
    except Exception as e:
        logging.error(f'Error during deduplication: {e}', exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
