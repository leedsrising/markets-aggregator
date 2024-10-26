import os
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from kalshiUtils import initialize_kalshi_client, fetch_kalshi_markets
from polymarketUtils import initialize_polymarket_clob_client, fetch_polymarket_markets
from polymarketUtils import fetch_polymarket_markets
from utils import query_recent, upsert_markets, find_duplicate_markets
from database import supabase

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
        
        logging.info(f'sending {len(all_markets)} markets to frontend')

        return jsonify(all_markets)
    except Exception as e:
        logging.error(f'Error fetching markets: {e}', exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/deduplicate_markets', methods=['POST'])
def deduplicate_markets():
    try:
        all_markets = []
        for table_name in SOURCE_TABLES.values():
            response = supabase.table(table_name).select('*').execute()
            all_markets.extend(response.data)

        if not all_markets:
            return jsonify({"error": "No markets found in any source table"}), 400

        deduplicated_markets = find_duplicate_markets(all_markets)

        return jsonify({"deduplicated_markets": deduplicated_markets})
    except Exception as e:
        logging.error(f'Error during deduplication: {e}', exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/get_deduplicated_markets')
def get_deduplicated_markets():
    try:
        # Fetch deduplicated markets
        response = supabase.table('duplicate_markets').select('*').execute()
        deduplicated_markets = response.data

        # Fetch full market data for each deduplicated pair
        full_markets = []
        for pair in deduplicated_markets:
            kalshi_response = supabase.table('kalshi_markets').select('*').eq('ticker', pair['kalshi_market_id']).execute()
            polymarket_response = supabase.table('polymarket_markets').select('*').eq('id', pair['polymarket_market_id']).execute()

            try:
                kalshi_market = kalshi_response.data[0]
                polymarket_market = polymarket_response.data[0]
            
            except Exception as e:
                logging.info(f"Error fetching market data: {e}")
                logging.info(f"Kalshi response: {kalshi_response}")
                logging.info(f"Polymarket response: {polymarket_response}")

            combined_market = {
                'title': kalshi_market['title'],
                'description': kalshi_market['description'],
                'kalshi_yes_price': kalshi_market['yes_price'],
                'kalshi_no_price': kalshi_market['no_price'],
                'polymarket_yes_price': polymarket_market['yes_price'],
                'polymarket_no_price': polymarket_market['no_price'],
                'kalshi_volume': kalshi_market['volume'],
                'polymarket_volume': polymarket_market['volume'],
                'kalshi_volume_24h': kalshi_market['volume_24h'],
                'polymarket_volume_24h': polymarket_market['volume_24h'],
                'close_time': kalshi_market['close_time'],
                'kalshi_ticker': kalshi_market['ticker'],
                'polymarket_id': polymarket_market['id']
            }
            full_markets.append(combined_market)

        return jsonify(full_markets)
    except Exception as e:
        logging.error(f'Error fetching deduplicated markets: {e}', exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

def scheduled_deduplication():
    with app.app_context():
        deduplicate_markets()

scheduler = BackgroundScheduler()
scheduler.add_job(
    scheduled_deduplication,
    trigger=CronTrigger(minute='*/5'),  # Run every 5 minutes
    id='deduplication_task',
    name='Deduplicate markets every 5 minutes',
    replace_existing=True)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)
