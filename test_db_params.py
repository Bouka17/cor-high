import psycopg2
try:
    conn = psycopg2.connect(
        database="cortexm",
        user="cortexm",
        password="cortexm",
        host="127.0.0.1",
        port="5432"
    )
    print("Connection success with parameters!")
    conn.close()
except Exception as e:
    print(f"Failed: {e}")
