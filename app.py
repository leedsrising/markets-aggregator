from flask import Flask, jsonify, request
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
import time
from sentence_transformers import SentenceTransformer
import numpy as np

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

        # Combine all markets
        all_markets = kalshi_markets + polymarket_markets

        # Deduplicate and merge markets
        deduplicated_markets = deduplicate_markets(all_markets)

        # Separate deduplicated markets by source
        result = {
            "kalshi": [m for m in deduplicated_markets if 'kalshi' in m['sources']],
            "polymarket": [m for m in deduplicated_markets if 'polymarket' in m['sources']],
        }
        return jsonify(result)
    except Exception as e:
        logging.error(f'Error fetching markets: {e}', exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/deduplicate_markets', methods=['POST'])
def deduplicate_markets_endpoint():
    try:
        markets = request.json.get('markets', [])
        if not markets:
            return jsonify({"error": "No markets provided"}), 400
        
        deduplicated_markets = deduplicate_markets(markets)
        
        return jsonify({"deduplicated_markets": deduplicated_markets})
    except Exception as e:
        logging.error(f'Error during deduplication: {e}', exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

def get_or_fetch_markets(source, current_time):
    start_time = time.time()
    
    # Check if we have markets as of the last 5 minutes
    recent_markets = Market.query_recent(
        source, 
        current_time - timedelta(seconds=5)
    )

    if recent_markets:
        logging.info(f'Markets not fetched. Already have market data as of 5min ago.')
        return [dict(market, source=source) for market in recent_markets]

    # If not, fetch new data
    if source == 'kalshi':
        markets = fetch_kalshi_markets(kalshi_client)
    else:
        markets = fetch_polymarket_markets(polygon_client)

    # Add source to each market
    markets = [dict(market, source=source) for market in markets]

    existing_markets = Market.get_existing_markets(source)
    
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

    Market.upsert_markets(market_data_list)

    end_time = time.time()
    logging.info(f"Time taken to fetch and process {source} markets: {end_time - start_time:.2f} seconds")
    return markets

def deduplicate_markets(markets):
    # Load pre-trained model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Encode market titles
    titles = [market['title'] for market in markets]
    embeddings = model.encode(titles)

    # Compute similarity matrix
    similarity_matrix = cosine_similarity(embeddings)

    # Find duplicate pairs
    duplicate_pairs = []
    for market_index in range(len(markets)):
        for comparison_index in range(market_index + 1, len(markets)):
            if similarity_matrix[market_index][comparison_index] > 0.5:
                duplicate_pairs.append((market_index, comparison_index))

    # Merge and deduplicate markets
    merged_markets = []
    used_indices = set()

    for market_index, market in enumerate(markets):
        if market_index not in used_indices:
            # Check for duplicates
            duplicates = [comparison_index for comparison_index in range(len(markets)) 
                          if (market_index, comparison_index) in duplicate_pairs or 
                          (comparison_index, market_index) in duplicate_pairs]
            
            for comparison_index in duplicates:
                kalshi_market = markets[market_index] if markets[market_index]['source'] == 'kalshi' else markets[comparison_index]
                polymarket_market = markets[comparison_index] if markets[comparison_index]['source'] == 'polymarket' else markets[market_index]

                if kalshi_market and polymarket_market:
                    # Insert into duplicate_markets table
                    Market.insert_duplicate_market(
                        kalshi_market['id'],
                        polymarket_market['id']
                    )

            used_indices.update(duplicates)
        else:
            merged_markets.append(market)

    logging.info(f'Found {len(merged_markets)} duplicate markets out of {len(markets)} total')

    return merged_markets

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
