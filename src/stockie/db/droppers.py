"""
Database drop classes for stockie application.

This module contains classes for dropping database infrastructure components:
- DropDatabase: Drops stockie database and application user  
- DropTablespaces: Drops stockie tablespaces
- DropSchema: Drops stockie tables and indexes

Uses database facade to carry out the actual work (i.e. the SQL statements). The above listed
classes are a layer on top of database facade to make the interface easier to use and provide
consistency in the interface.
"""

import logging

from stockie.db.database_facade import DatabaseFacade
from stockie.db.database_connection import DatabaseConnection
from typing import cast


class DropDatabase:
    """Drops database for stockie application."""
    
    def __init__(self, database_connection: DatabaseConnection, database: str, user: str):
        self.database = database
        self.user = user
        self.db_facade: DatabaseFacade = cast(DatabaseFacade, database_connection.db_facade)
        self.drop_database()
        self.drop_user()
                    
    def drop_database(self) -> None:
        """Drop the database."""
        logging.info(f"Dropping database: {self.database}")
        self.db_facade.drop_database(self.database)
        logging.info(f"Database {self.database} dropped successfully")
            
    def drop_user(self) -> None:
        """Drop the user if requested."""
        logging.info(f"Dropping user: {self.user}")
        self.db_facade.drop_user(self.user)
        logging.info(f"User {self.user} dropped successfully")


class DropTablespaces:
    """Drops tablespaces for stockie application."""
    
    def __init__(self, database_connection: DatabaseConnection, owner: str):
        self.db_facade: DatabaseFacade = cast(DatabaseFacade, database_connection.db_facade)
        self.owner = owner
        self.drop_tablespaces()
           
    def drop_tablespaces(self) -> None:
        """Drop a specific tablespace."""
        logging.info(f"Dropping Stockie tablespaces")
        self.db_facade.drop_stockie_tablespaces(owner=self.owner)
        logging.info(f"Stockie tablespace dropped successfully")


class DropSchema:
    """Drops database schema for stockie application."""
    
    def __init__(self, database_connection: DatabaseConnection):
        self.db_facade: DatabaseFacade = cast(DatabaseFacade, database_connection.db_facade)
        self.drop_tables()
            
    def drop_tables(self) -> None:
        """Drop all tables (CASCADE will drop dependent indexes)."""
        logging.info("Dropping tables...")
        self.db_facade.drop_stockie_tables()
        logging.info("Tables dropped successfully")
