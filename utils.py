from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from database import supabase

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
                    insert_duplicate_market(
                        kalshi_market['id'],
                        polymarket_market['id']
                    )

            used_indices.update(duplicates)

    return merged_markets


def insert_duplicate_market(kalshi_market_id, polymarket_market_id):
    supabase.table('duplicate_markets').insert({
        'kalshi_market_id': kalshi_market_id,
        'polymarket_market_id': polymarket_market_id
    }).execute()

def insert_data(data, table_name):
    supabase.table(table_name).insert(data).execute()

def query_recent(source, current_time):
        response = supabase.table('markets').select('*')\
            .eq('source', source)\
            .gt('last_updated', current_time.isoformat())\
            .execute()
        return [Market.from_row(row) for row in response.data]

def upsert_markets(market_data_list):
    if market_data_list:
        supabase.table('markets').upsert(market_data_list).execute()

def get_existing_markets(source):
    response = supabase.table('markets').select('title, source').eq('source', source).execute()
    return {(row['title'], row['source']) for row in response.data}

def delete_by_source(source):
    supabase.table('markets').delete().eq('source', source).execute()

def batch_insert(market_data_list):
    # Insert all markets in a single request
    if market_data_list:
        supabase.table('markets').insert(market_data_list).execute()

def from_row(row):
    return {
        'title': row['title'],
        'description': row['description'],
        'yes_contract': {'price': row['yes_price']},
        'no_contract': {'price': row['no_price']},
        'volume': row['volume'],
        'volume_24h': row['volume_24h'],
        'close_time': row['close_time']
    }

def insert_duplicate_market(kalshi_market_id, polymarket_market_id):
    supabase.table('duplicate_markets').insert({
        'kalshi_market_id': kalshi_market_id,
        'polymarket_market_id': polymarket_market_id
    }).execute()

def insert_data(data, table_name):
    supabase.table(table_name).insert(data).execute()
