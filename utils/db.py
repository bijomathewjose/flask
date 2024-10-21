import os
import mysql 
from mysql.connector import Error
def create_connection():
    try:
        print('Connecting to the database')
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        if connection.is_connected():
            print('Database connection successful!')
            return connection
    except Error as e:
        raise Exception(f"Database connection error: '{e}'")
    
def close_connection(connection):
    print('Checking if the connection is still open')
    if not connection:
        print('Connection not created')
        return
    elif connection.is_connected():
        print('Closing the connection')
        connection.close()
        print('Connection closed')
    else:
        print('Connection already closed')

def execute_query(connection, query, params=None):
    cursor = connection.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        connection.commit()
        print("Query executed and committed successfully")
    except Error as e:
        connection.rollback()  # Rollback in case of error
        raise Exception(f"Database connection error: '{e}'")
    finally:
        cursor.close()

def fetch_data(connection, query, params=None):
    cursor = connection.cursor(dictionary=True)
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchall()
        return result
    except Error as e:
        raise Exception(f"Database connection error: '{e}'")
    finally:
        cursor.close()