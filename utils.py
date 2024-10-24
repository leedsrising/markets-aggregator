from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from models import Market

import logging

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

    return merged_markets

