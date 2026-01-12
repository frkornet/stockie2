import logging
import psycopg2

from stockie.db.database_facade import DatabaseFacade
from typing import cast

class DatabaseConnection:
    """User database connection."""
    def __init__(self, host: str, port: int, user: str, password: str, dbname: str = 'postgres') -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.dbname = dbname
        self.conn = None
        self.db_facade = None
        self.connect()
        
    def connect(self) -> None:
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password
            )
            self.db_facade = DatabaseFacade(self.conn)
            logging.info(f"Connected to database {self.dbname} on {self.host}:{self.port}")
        except psycopg2.Error as e:
            logging.error(f"Failed to connect to database: {e}")
            raise
            
    def disconnect(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed")
