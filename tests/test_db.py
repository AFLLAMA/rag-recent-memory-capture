import psycopg2
from pgvector.psycopg2 import register_vector

conn = psycopg2.connect(host="localhost", port=5432, user="de_user", password="de_password", dbname="de_assist")
try:
    register_vector(conn)
except psycopg2.ProgrammingError:
    print("Caught ProgrammingError")

cur = conn.cursor()
cur.execute("SELECT 1;")
print(cur.fetchone())
