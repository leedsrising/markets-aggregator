import os

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from database import supabase, create_client
from config import SOURCES, SOURCE_TABLES

import logging

# database util functions

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

# get the schema of a table in supabase
def get_table_schema(table_name):
    query = f"""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = '{table_name}';
    """
    response = supabase.rpc('execute_sql', {'sql': query}).execute()
    return response.data

# create a record in the duplicate market table with the kalshi and polymarket market ids
def insert_duplicate_market(kalshi_market_id, polymarket_market_id):
    supabase.table('duplicate_markets').insert({
        'kalshi_market_id': kalshi_market_id,
        'polymarket_market_id': polymarket_market_id
    }).execute()

# query the markets tables (only polymarket_markets for now) to verify that records have
# recently been updated. If not, we fetch new records.
def query_recent(current_time):
    response = supabase.table('polymarket_markets').select('*')\
        .gt('last_updated', current_time.isoformat())\
        .execute()
    return [from_row(row) for row in response.data]

# upsert (insert, and replace on conflict) market data to the specified table_name
def upsert_markets(market_data_list, table_name):
    try:
        supabase.table(table_name).upsert(market_data_list).execute()
    except Exception as e:
        logging.error(f'Error upserting markets to {table_name}: {e}', exc_info=True)

# get all markets from all source market tables
def get_all_markets():
    all_markets = []
    
    for source in SOURCES:
        response = supabase.table(SOURCE_TABLES[source]).select('*').execute()
        markets = [from_row(row) for row in response.data]
        all_markets.extend(markets)
    
    return all_markets

# convert a row from the database into a market object
# q: is this really necessary as a util function?
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

## Other util functions

def find_duplicate_markets(markets):
    # Load pre-trained model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Encode market titles
    titles = [market['title'] for market in markets] ## should maybe encode other info too
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
                        kalshi_market['kalshi_id'],
                        polymarket_market['id']
                    )

            used_indices.update(duplicates)
        else:
            merged_markets.append(market)

    logging.info(f'Found {len(merged_markets)} duplicate markets out of {len(markets)} total')

    return merged_markets