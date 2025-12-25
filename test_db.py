import psycopg2
import os
from environ import Env

env = Env()
env_file = ".env"
if os.path.exists(env_file):
    env.read_env(env_file)

db_url = env("DATABASE_URL")
print(f"Testing connection to: {db_url}")

try:
    conn = psycopg2.connect(db_url)
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
    try:
        # Try to see if there's a raw message
        print(f"Raw error: {e.args}")
    except:
        pass
