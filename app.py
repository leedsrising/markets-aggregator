from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from kalshiUtils import initialize_kalshi_client, fetch_kalshi_markets
from polymarketUtils import initialize_polymarket_client, fetch_polymarket_markets
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

app = Flask(__name__)
CORS(app)  # enables CORS for all routes
logging.basicConfig(level=logging.INFO)

load_dotenv()
kalshi_client = initialize_kalshi_client()
polygon_client = initialize_polymarket_client()

def similar_market_names(name1, name2):
    # Vectorize the two market names
    vectorizer = CountVectorizer().fit_transform([name1, name2])
    vectors = vectorizer.toarray()
    similarity = cosine_similarity(vectors)[0][1]
    
    # You can adjust this threshold as needed
    return similarity > 0.7  # 70% similarity threshold

def match_markets(kalshi_markets, polymarket_markets):
    matched_markets = []
    logging.info("matching markets")
    for kalshi_market in kalshi_markets:
        for polymarket_market in polymarket_markets:
            if similar_market_names(kalshi_market['description'], polymarket_market['description']):
                matched_market = {
                    'description': kalshi_market['description'],
                    'kalshi_yes_price': kalshi_market['yes_contract']['price'],
                    'kalshi_no_price': kalshi_market['no_contract']['price'],
                    'polymarket_yes_price': polymarket_market['yes_contract']['price'],
                    'polymarket_no_price': polymarket_market['no_contract']['price'],
                    'volume': kalshi_market['volume'],
                    'volume_24h': kalshi_market['volume_24h'],
                    'close_time': kalshi_market['close_time']
                }
                matched_markets.append(matched_market)
                break
    return matched_markets

@app.route('/api/markets')
def get_markets():
    try:
        kalshi_markets = fetch_kalshi_markets(kalshi_client)
        polymarket_markets = fetch_polymarket_markets(polygon_client)

        # all_markets = {
        #     "kalshi": kalshi_markets,
        #     "polymarket": polymarket_markets,
        # }
        # return jsonify(all_markets)
        
        matched_markets = match_markets(kalshi_markets, polymarket_markets)
        
        return jsonify(matched_markets)
    except Exception as e:
        print('Error fetching markets:', str(e))
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
