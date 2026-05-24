import mysql.connector.pooling

pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="rogil_pool",
    pool_size=5,
    host="localhost",
    user="root",
    password="",
    port=3306,
    database="drogueria_rogil"
)

def get_connection():
    return pool.get_connection()