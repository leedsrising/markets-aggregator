import os
from dotenv import load_dotenv
from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY
from py_clob_client.clob_types import ApiCreds
import logging
from py_clob_client.clob_types import BookParams
import requests
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

logging.basicConfig(level=logging.INFO)

load_dotenv()

def initialize_polymarket_clob_client():

    host = "https://clob.polymarket.com"
    key = os.getenv("WEB3_WALLET_PK")
    chain_id = POLYGON

    return ClobClient(host, key=key, chain_id=chain_id)

def fetch_polymarket_markets(client, limit=100, total_markets=1000, volume_num_min=100000):
    all_markets = []
    offset = 0
    
    while len(all_markets) < total_markets:
        try:
            url = f"https://gamma-api.polymarket.com/markets?limit={limit}&offset={offset}&volume_num_min={volume_num_min}"
            response = requests.get(url)
            response.raise_for_status()
            markets_data = response.json()

            if not markets_data:
                break  # No more markets to fetch

            logging.info(f"Fetched {len(markets_data)} markets from Polymarket (offset: {offset})")
            
            normalized_markets = massage_polymarket_data(markets_data)
            all_markets.extend(normalized_markets)
            
            offset += limit
            
            if len(markets_data) < limit:
                break  # Less than 'limit' markets returned, we've reached the end
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching Polymarket markets: {e}")
            break

    logging.info(f"Total markets fetched from Polymarket: {len(all_markets)}")
    return all_markets[:total_markets]  # Return only the top 'total_markets' markets

def massage_polymarket_data(markets_data):
    normalized_data = []
    if isinstance(markets_data, list):
        pass
    else:
        logging.error(f"Unexpected markets data structure: {type(markets_data)}")
        return []

    for market in markets_data:
        try:
            outcome_prices = json.loads(market['outcomePrices'])
            yes_price = float(outcome_prices[0])
            no_price = float(outcome_prices[1])
            
            normalized_market = {
                'title': market['question'],
                'description': market.get('description', ''),
                'yes_contract': {'price': yes_price},
                'no_contract': {'price': no_price},
                'volume': market.get('volume', 'N/A'),
                'volume_24h': market.get('volume24Hr', 'N/A'),
                'close_time': market['endDateIso']
            }
            normalized_data.append(normalized_market)
        except Exception as e:
            logging.error(f"Error processing market: {e}")
            logging.error(f"Market data: {market}")

    logging.info(f"normalized_data length: {len(normalized_data)}")
    return normalized_data
