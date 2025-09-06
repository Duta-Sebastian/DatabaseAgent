import os

import dotenv


def get_database_url():
    """Simple function to build database URL from environment variables"""
    dotenv.load_dotenv(override=True)
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "mydb")
    username = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "password")
    
    return f"postgresql://{username}:{password}@{host}:{port}/{database}"