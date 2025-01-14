import os
import requests
import time
import base64
import json

import pprint
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key

import kalshi_python
import logging


load_dotenv()
logging.basicConfig(level=logging.INFO)

def initialize_kalshi_client():
    config = kalshi_python.Configuration()
    return kalshi_python.ApiInstance(
        email=os.getenv('KALSHI_EMAIL'),
        password=os.getenv('KALSHI_PASSWORD'),
        configuration=config,
    )

def fetch_kalshi_markets(kalshi_api, limit=1000, status='open'):
    try:
        # Fetch both regular and election markets
        regular_markets = fetch_non_election_kalshi_markets(kalshi_api, limit=limit, status=status)
        election_markets = fetch_kalshi_election_markets(kalshi_api)
        
        logging.info(f"Fetched {len(regular_markets)} regular markets and {len(election_markets)} election markets from Kalshi")

        # Combine both types of markets
        return regular_markets + election_markets
    except Exception as e:
        logging.error(f'Error fetching Kalshi markets: {e}')
        return []

def fetch_non_election_kalshi_markets(kalshi_api, limit=1000, status='open', num_markets=10000):
    try:
        all_markets = []
        cursor = None
        
        while len(all_markets) < num_markets:
            # Get next batch of markets using cursor if available
            markets_response = kalshi_api.get_markets(
                limit=limit,
                cursor=cursor,
                status=status
            )
            
            if not markets_response.markets:
                break  # No more markets available
                
            # Format the current batch
            for market in markets_response.markets:
                
                try:
                    formatted_market = {
                        "kalshi_id": 'N/A', # non-election markets dont have an ID field
                        "source": "kalshi",
                        "title": market.title,
                        "description": '',
                        # "description": (market['underlying'] if market['underlying'] else '') + (market['description_context'] if market['description_context'] else ''),
                        "yes_price": market.yes_ask / 100 if hasattr(market, 'yes_ask') else 0,
                        "no_price": market.no_ask / 100 if hasattr(market, 'no_ask') else 0,
                        "ticker": market.ticker,
                        "volume": market.volume,
                        "volume_24h": market.volume_24h,
                        "close_time": market.close_time
                    }
                    all_markets.append(formatted_market)
                except Exception as e:
                    logging.error(f'Error formatting Kalshi non-election market: {e}', exc_info=True)
                    logging.error(f"Pretty printed non-election market: {pprint.pformat(market)}")
                    raise  # Re-raise the exception to propagate it up

            cursor = markets_response.cursor
            
            # If no cursor returned, we've reached the end
            if not cursor:
                break
                
            logging.info(f"Progress: Fetched {len(all_markets)} markets")
            
        return all_markets
        
    except Exception as e:
        logging.error(f'Error fetching regular Kalshi markets: {e}', exc_info=True)
        return []

def fetch_kalshi_election_markets(kalshi_api):
    #for temporary use while kalshi has two different endpoints for election vs other markets
    #Election Markets: api.elections.kalshi.com/trade-api/v2
    #Other Markets: trading-api.kalshi.com/trade-api/v2

    try:
        response = requests.get('https://api.elections.kalshi.com/v1/events')
        response.raise_for_status()
        election_data = response.json()
        
        # # Log the structure of the first event and market
        # if election_data['events']:
        #     logging.info("Sample Event Structure:")
        #     logging.info(json.dumps(election_data['events'][0], indent=2))
        #     if election_data['events'][0]['markets']:
        #         logging.info("Sample Market Structure:")
        #         logging.info(json.dumps(election_data['events'][0]['markets'][0], indent=2))
        
        formatted_markets = []
        # an event can have multiple markets within it. ie event: price of ethereum, markets: price above 1k, 2k, 3k
        for event in election_data['events']:
            logging.debug(f"Formatted Kalshi election market: {pprint.pformat(event)}")
            for market in event['markets']:
                try:
                    formatted_market = {
                        "kalshi_id": market['id'],
                        "source": "kalshi",
                        "title": market['title'],
                        "description": event['underlying'] + event['description_context'],
                        "yes_price": market['yes_ask'],
                        "no_price": 1 - market['yes_ask'], # kalshi election markets dont have a no_ask value
                        "ticker": market['ticker_name'],
                        "volume": market['volume'],
                        "volume_24h": market.get('volume_24h', 'N/A'),
                        "close_time": market['close_date']
                    }
                    formatted_markets.append(formatted_market)
                except Exception as e:
                    logging.error(f'Error formatting Kalshi election market: {e}', exc_info=True)
                    logging.debug(f"Formatted Kalshi election market: {pprint.pformat(market)}")
                    raise e

        return formatted_markets
    except Exception as e:
        logging.error(f'Error fetching Kalshi election markets: {e}', exc_info=True)
        return []
