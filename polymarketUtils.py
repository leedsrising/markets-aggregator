import os
from dotenv import load_dotenv
from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY
from py_clob_client.clob_types import ApiCreds

load_dotenv()

def initialize_polymarket_client():

    host = "https://clob.polymarket.com"
    key = os.getenv("WEB3_WALLET_PK")
    chain_id = POLYGON

    return ClobClient(host, key=key, chain_id=chain_id)

def fetch_polymarket_markets(client):
    return client.get_markets()
