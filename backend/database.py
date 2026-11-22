import mysql.connector
from dotenv import load_dotenv
import os

# Load database settings
load_dotenv()

# Connect to MySQL
def get_db_connection():

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "LostAndFound")
    )

    return connection