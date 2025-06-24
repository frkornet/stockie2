from psycopg2 import sql
from collections.abc import Iterable

class DatabaseUtilities:
    def __init__(self, conn):
        self.conn = conn
        self.cur = conn.cursor()

    def table_exists(self, table_names):
        if isinstance(table_names, str):
            table_names = [table_names]
        elif not isinstance(table_names, Iterable):
            raise TypeError("Expected a string or an iterable of strings for table_names")

        if not all(isinstance(name, str) for name in table_names):
            raise ValueError("All table names must be strings")

        placeholders = ','.join(['%s'] * len(table_names))
        self.cur.execute(f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ({placeholders})
        """, table_names)

        existing = {row[0] for row in self.cur.fetchall()}
        return all(name in existing for name in table_names)