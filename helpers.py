import pandas as pd 
from datetime import datetime, timedelta

def get_last_transaction_date(conn):
    query = "SELECT MAX(date) AS latest_date FROM transactions"
    latest_date_str = pd.read_sql(query, conn).iloc[0]["latest_date"]
    
    if latest_date_str:
        latest_date = datetime.fromisoformat(latest_date_str)
        updated_date = latest_date + timedelta(seconds=1)
        return updated_date.isoformat()
    else:
        return None
    
def update_entry(row, cursor):
    query = "UPDATE transactions SET description = ?, amount = ?, category = ? WHERE id = ?"
    cursor.execute(query, (row['description'], row['amount'], row['category'], row['id']))

