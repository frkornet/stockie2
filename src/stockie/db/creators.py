"""
Database creation classes for stockie application.

This module contains classes for creating database infrastructure components:
- CreateDatabase: Creates database and application user
- CreateTablespaces: Creates PostgreSQL tablespaces
- CreateSchema: Creates tables and indexes
"""

import logging
import os
import stat
import psycopg2

from stockie.db.database_facade import DatabaseFacade
from stockie.db.database_connection import DatabaseConnection
from typing import cast

class CreateDatabase:
    """
    Creates stockie PostgreSQL database and user.

    NB: to create the database and user, this class connects to the 'postgres' database. 
    So, the code assumes that the postgres database exists. If it doesn't, the connection will fail.
    """
    
    def __init__(self, database_connection: DatabaseConnection, database: str, user: str, password: str):
        self.database = database
        self.user = user
        self.password = password
        self.db_facade: DatabaseFacade = cast(DatabaseFacade, database_connection.db_facade)
        self.create_user()
        self.create_database()

    def create_user(self) -> None:
        """Create application user."""
        logging.info(f"Creating user: {self.user}")
        self.db_facade.create_user(self.user, self.password)
        logging.info(f"User {self.user} created successfully")
        
    def create_database(self) -> None:
        """Create application database."""
        logging.info(f"Creating database: {self.database}")
        self.db_facade.create_database(self.database, owner=self.user)
        logging.info(f"Database {self.database} created successfully")


class CreateTablespaces:
    """Creates stockie PostgreSQL tablespaces."""
    
    def __init__(
            self, database_connection: DatabaseConnection, user: str,
            data_path: str, index_path: str
        ):
        self.user = user
        self.data_path = data_path
        self.index_path = index_path
        self.db_facade: DatabaseFacade = cast(DatabaseFacade, database_connection.db_facade)
        self.create_tablespaces()
    
    def create_tablespaces(self) -> None:
        """
        Create tablespaces for stockie. Code assumes that the paths provided are valid and
        PostgreSQL has permission to read/write to them.
        """
        try:
            logging.info("Starting tablespace creation...")
            self.db_facade.create_stockie_tablespaces(self.data_path, self.index_path, self.user)
            logging.info("Tablespace creation completed successfully!")
        
        except Exception as e:
            logging.error(f"Tablespace creation failed: {e}")
            raise

class CreateSchema:
    """Creates database schema for stockie application."""
    
    def __init__(self, database_connection: DatabaseConnection, owner: str):
        self.owner = owner
        self.db_facade: DatabaseFacade = cast(DatabaseFacade, database_connection.db_facade)
        self.create_schema()
                   
    def create_schema(self) -> None:
        """Create the complete database schema."""
        try:            
            logging.info("Creating tables and indexes...")
            self.db_facade.create_stockie_tables(self.owner)
            logging.info("Schema creation completed successfully!")
            
        except Exception as e:
            logging.error(f"Schema creation failed: {e}")
            raise