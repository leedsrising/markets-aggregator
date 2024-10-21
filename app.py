from flask import Flask, jsonify
from dotenv import load_dotenv
import os
import requests
import time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import base64
import kalshi_python

app = Flask(__name__)
load_dotenv()
config = kalshi_python.Configuration()
kalshi_api = kalshi_python.ApiInstance(
    email=os.getenv('KALSHI_EMAIL'),
    password=os.getenv('KALSHI_PASSWORD'),
    configuration=config,
)

def load_private_key():
    KALSHI_RSA_PRIVATE_KEY = os.getenv('KALSHI_RSA_PRIVATE_KEY')
    private_key = load_pem_private_key(KALSHI_RSA_PRIVATE_KEY.encode(), password=None)
    return private_key

def sign_pss_text(private_key, text):
    message = text.encode('utf-8')
    try:
        signature = private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        raise Exception(f"RSA sign PSS failed: {str(e)}")

def send_request():
    current_time_milliseconds = int(time.time() * 1000)
    timestamp_str = str(current_time_milliseconds)

    private_key = load_private_key()

    method = "POST"
    base_url = 'https://demo-api.kalshi.co'
    path = '/trade-api/v2/portfolio/orders'
    body = {
        "action": "buy",
        "client_order_id": "1fa1be86-3f8e-49be-8c1e-1e46ea490d59",
        "count": 3,
        "side": "yes",
        "ticker": "HOMEUSY-24-T4",
        "type": "limit",
        "yes_price": 30
    }

    msg_string = timestamp_str + method + path
    print(msg_string)

    sig = sign_pss_text(private_key, msg_string)

    headers = {
        'KALSHI-ACCESS-KEY': os.getenv('KALSHI_API_KEY_ID'),
        'KALSHI-ACCESS-SIGNATURE': sig,
        'KALSHI-ACCESS-TIMESTAMP': timestamp_str,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(base_url + path, json=body, headers=headers)
        print("Status Code:", response.status_code)
        print("Response Body:", response.json())
    except requests.exceptions.RequestException as e:
        print("Error:", str(e))
        if hasattr(e, 'response'):
            print("Error Response Data:", e.response.json())

@app.route('/api/markets')
def get_markets():
    try:
        markets = kalshi_api.get_markets()
        formatted_markets = []
        for market in markets.markets:
            formatted_market = {
                "name": market.title,
                "yes_contract": {"price": market.yes_bid / 100 if market.yes_bid else None},
                "no_contract": {"price": market.no_bid / 100 if market.no_bid else None},
                "ticker": market.ticker,
                "volume": market.volume,
                "close_time": market.close_time
            }
            formatted_markets.append(formatted_market)
        return jsonify({"markets": formatted_markets})
    except Exception as e:
        print('Error fetching markets:', str(e))
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
