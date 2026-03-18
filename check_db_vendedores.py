import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DB_URL')
if not db_url:
    print("DB_URL not found")
    exit(1)

try:
    conn = psycopg2.connect(db_url, cursor_factory=DictCursor)
    cur = conn.cursor()
    
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = cur.fetchall()
    print("Tables:", [t['table_name'] for t in tables])
    
    if 'vendedores' in [t['table_name'] for t in tables]:
        cur.execute("SELECT * FROM vendedores")
        vendedores = cur.fetchall()
        print("Vendedores count:", len(vendedores))
        for v in vendedores:
            print(dict(v))
    else:
        print("Table 'vendedores' NOT FOUND")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
