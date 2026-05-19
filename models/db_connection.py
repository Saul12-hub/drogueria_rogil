# db_connection.py
import mysql.connector.pooling

pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="rogil_pool",
    pool_size=5,
    host="switchyard.proxy.rlwy.net",
    port=58888,
    user="root",
    password="urlUFRMSbyIgEKvZEgKfGJTCXavRBroo",
    database="railway",
    use_pure=True
)

def get_connection():
    return pool.get_connection()