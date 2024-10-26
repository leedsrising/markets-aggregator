import json
import requests
from config import SOURCE_TABLES
from database import supabase

def run_deduplication():
    # Make a request to the endpoint
    response = requests.post('http://localhost:3000/api/deduplicate_markets')
    
    # Check the response
    if response.status_code == 200:
        data = response.json()
        print("Deduplication successful")
        print(f"Deduplicated markets: {len(data['deduplicated_markets'])}")
        
        # Log the number of markets before deduplication
        total_markets = sum(len(supabase.table(table).select('*').execute().data) for table in SOURCE_TABLES.values())
        print(f"Total markets before deduplication: {total_markets}")

if __name__ == '__main__':
    run_deduplication()
