from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from kalshiUtils import initialize_kalshi_client, fetch_kalshi_markets
from polymarketUtils import initialize_polymarket_clob_client, fetch_polymarket_markets
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from polymarketUtils import fetch_polymarket_markets
from models import Market
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Suppress httpx logs
logging.getLogger('httpx').setLevel(logging.WARNING)

# Suppress werkzeug logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
CORS(app)

load_dotenv()
kalshi_client = initialize_kalshi_client()
polygon_client = initialize_polymarket_clob_client()

@app.route('/api/markets')
def get_markets():
    try:
        current_time = datetime.now(datetime_timezone.utc)
        kalshi_markets = get_or_fetch_markets('kalshi', current_time)
        polymarket_markets = get_or_fetch_markets('polymarket', current_time)

        all_markets = {
            "kalshi": kalshi_markets,
            "polymarket": polymarket_markets,
        }
        return jsonify(all_markets)
    except Exception as e:
        logging.error(f'Error fetching markets: {e}', exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

def get_or_fetch_markets(source, current_time):
    # Check if we have markets as of the last 5 minutes
    recent_markets = Market.query_recent(
        source, 
        current_time - timedelta(seconds=5)
    )

    if recent_markets:
        logging.info(f'Markets not fetched. Already have market data as of 5min ago.')
        return recent_markets

    # If not, fetch new data
    if source == 'kalshi':
        markets = fetch_kalshi_markets(kalshi_client)
    else:
        markets = fetch_polymarket_markets(polygon_client)

    # Update database
    Market.delete_by_source(source)
    
    # Prepare all market data for batch insert
    market_data_list = [{
        'source': source,
        'title': market['title'],
        'description': market['description'],
        'yes_price': market['yes_contract']['price'] if isinstance(market['yes_contract'], dict) else market['yes_contract'],
        'no_price': market['no_contract']['price'] if isinstance(market['no_contract'], dict) else market['no_contract'],
        'volume': str(market.get('volume', '0')),
        'volume_24h': str(market.get('volume_24h', '0')),
        'close_time': market['close_time'],
        'last_updated': current_time.isoformat()
    } for market in markets]

    # Batch insert all markets
    Market.batch_insert(market_data_list)

    return markets

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
