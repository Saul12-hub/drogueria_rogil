# db_connection.py

import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool

dbconfig = {
    "host": "switchyard.proxy.rlwy.net",
    "port": 58888,
    "user": "root",
    "password": "urlUFRMSbyIgEKvZEgKfGJTCXavRBroo",
    "database": "railway",
    "autocommit": True,
    "ssl_disabled": False,
    "connection_timeout": 30
}

pool = MySQLConnectionPool(
    pool_name="rogil_pool",
    pool_size=5,
    **dbconfig
)

def get_connection():
    return pool.get_connection()