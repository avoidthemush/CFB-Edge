import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

db_url = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print("Connected successfully!")
    print(cur.fetchone()[0])
    cur.close()
    conn.close()
except Exception as e:
    print("Connection failed:")
    print(e)