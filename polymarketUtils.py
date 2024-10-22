import os
from dotenv import load_dotenv
from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY
from py_clob_client.clob_types import ApiCreds
import logging
from py_clob_client.clob_types import BookParams

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO)

load_dotenv()

def initialize_polymarket_client():

    host = "https://clob.polymarket.com"
    key = os.getenv("WEB3_WALLET_PK")
    chain_id = POLYGON

    return ClobClient(host, key=key, chain_id=chain_id)

def fetch_polymarket_markets(client):
    try:
        markets_data = client.get_markets()
        logging.info(f"Fetched {len(markets_data)} markets from Polymarket")
        normalized_markets = []
        for market in markets_data['data']:
            try:
                # cant use volume because of polymarket rate limiting
                # book_params = [BookParams(token_id=token['token_id']) for token in market['tokens']]
                # orderbooks = client.get_order_books(book_params)
                
                # volume = sum(sum(order['size'] for order in ob['bids']) + sum(order['size'] for order in ob['asks']) for ob in orderbooks)
                
                yes_price = next((token['price'] for token in market['tokens'] if token['outcome'] == 'Yes'), 0)
                no_price = next((token['price'] for token in market['tokens'] if token['outcome'] == 'No'), 0)
                
                normalized_market = {
                    'description': market['question'],
                    'yes_contract': {'price': yes_price},
                    'no_contract': {'price': no_price},
                    # 'volume': volume,
                    'volume': 'N/A',
                    'volume_24h': 'N/A',
                    'close_time': market['end_date_iso']
                }
                normalized_markets.append(normalized_market)
            except Exception as e:
                logging.error(f"Error processing market: {e}")
        return normalized_markets
    except Exception as e:
        logging.error(f"Error fetching Polymarket markets: {e}")
        return []

def massage_polymarket_data(markets_data):
    normalized_data = []
    if isinstance(markets_data, dict):
        markets = markets_data['data']
    else:
        logging.error(f"Unexpected markets data structure: {type(markets_data)}")
        return []

    for market in markets:
        try:
            yes_price = next((token['price'] for token in market['tokens'] if token['outcome'] == 'Yes'), 0)
            no_price = next((token['price'] for token in market['tokens'] if token['outcome'] == 'No'), 0)
            
            normalized_market = {
                'description': market['question'],
                'yes_contract': {'price': yes_price},
                'no_contract': {'price': no_price},
                'volume': 'N/A',
                'volume_24h': 'N/A',
                'close_time': market['end_date_iso']
            }
            normalized_data.append(normalized_market)
        except Exception as e:
            logging.error(f"Error processing market: {e}")
            logging.error(f"Market data: {market}")

    return normalized_data
