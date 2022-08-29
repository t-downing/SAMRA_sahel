import psycopg2
import os
from dotenv import load_dotenv

print("running root sandbox")

load_dotenv('.env')

conn = psycopg2.connect(
    dbname="d446lmk1hkk665",
    user=os.environ.get("PSQL_USER"),
    password=os.environ.get("PSQL_PASSWORD"),
    host="ec2-18-204-142-254.compute-1.amazonaws.com",
    port="5432",
)

cursor = conn.cursor()
cursor.execute("select relname from pg_class where relkind='r' and relname !~ '^(pg_|sql_)';")
print(cursor.fetchall())

print(conn)