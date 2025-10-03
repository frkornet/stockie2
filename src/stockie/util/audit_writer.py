from stockie.db.database_facade import DatabaseFacade
from typing import List, Optional
import psycopg2

class AuditWriter:
    """
    Utility to write structured audit summaries to the stock_price_audit table.
    """

    def __init__(self, conn: psycopg2.extensions.connection) -> None:
        self.db_util = DatabaseFacade(conn)

    def log_change_summary(self, ticker: str, reason: str, columns_changed: Optional[List[str]]) -> None:
        """
        Inserts a summary audit entry indicating a reconciliation cause.

        Parameters:
        - ticker (str): Stock symbol
        - reason (str): One of ['row_count_mismatch', 'date_join_mismatch', 'column_value_mismatch']
        - columns_changed (list of str): List of affected columns, if applicable
        """
        summary = f"{reason}: {', '.join(columns_changed)}" if columns_changed else reason
        self.db_util.write_audit_message(ticker, summary)