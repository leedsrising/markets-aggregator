import os
from dotenv import load_dotenv
import requests
import time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import base64
import kalshi_python

load_dotenv()

def initialize_kalshi_client():
    config = kalshi_python.Configuration()
    return kalshi_python.ApiInstance(
        email=os.getenv('KALSHI_EMAIL'),
        password=os.getenv('KALSHI_PASSWORD'),
        configuration=config,
    )

def fetch_kalshi_markets(kalshi_api, limit=1000):
    try:
        markets = kalshi_api.get_markets(limit=limit)
        formatted_markets = []
        for market in markets.markets:
            formatted_market = {
                "description": market.title,
                "yes_contract": {"price": market.yes_bid / 100 if market.yes_bid else None},
                "no_contract": {"price": market.no_bid / 100 if market.no_bid else None},
                "ticker": market.ticker,
                "volume": market.volume,
                "volume_24h": market.volume_24h,
                "close_time": market.close_time
            }
            formatted_markets.append(formatted_market)
        return formatted_markets
    except Exception as e:
        print('Error fetching Kalshi markets:', str(e))
        return []

