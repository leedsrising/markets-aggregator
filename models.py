from datetime import datetime
from database import supabase

class Market:
    @staticmethod
    def query_recent(source, current_time):
        response = supabase.table('markets').select('*')\
            .eq('source', source)\
            .gt('last_updated', current_time.isoformat())\
            .execute()
        return [Market.from_row(row) for row in response.data]

    @staticmethod
    def delete_by_source(source):
        supabase.table('markets').delete().eq('source', source).execute()

    @staticmethod
    def batch_insert(market_data_list):
        # Insert all markets in a single request
        if market_data_list:
            supabase.table('markets').insert(market_data_list).execute()

    @staticmethod
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
