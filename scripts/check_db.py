import os
import psycopg2
from psycopg2.extras import DictCursor

def test_conn():
    db_url = os.environ.get('DB_URL')
    if not db_url:
        print("DB_URL not set")
        return
    
    print(f"Testing connection to {db_url[:20]}...")
    try:
        conn = psycopg2.connect(db_url, connect_timeout=5)
        print("✅ Connection successful!")
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print(f"Postgres Version: {cur.fetchone()[0]}")
        
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        tables = cur.fetchall()
        print(f"Tables found: {[t[0] for t in tables]}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Connection FAILED: {e}")

if __name__ == "__main__":
    test_conn()
