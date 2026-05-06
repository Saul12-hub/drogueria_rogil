import mysql.connector
from dotenv import load_dotenv
import os
# db_connection.py
import mysql.connector.pooling

pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="rogil_pool",
    pool_size=5,
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=int(os.getenv("DB_PORT", 58888)),
    database=os.getenv("DB_NAME")
)

def get_connection():
    return pool.get_connection()