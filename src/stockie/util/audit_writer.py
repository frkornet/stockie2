class AuditWriter:
    """
    Utility to write structured audit summaries to the stock_price_audit table.
    """

    def __init__(self, cursor):
        self.cur = cursor

    def log_change_summary(self, ticker, reason, columns_changed):
        """
        Inserts a summary audit entry indicating a reconciliation cause.

        Parameters:
        - ticker (str): Stock symbol
        - reason (str): One of ['row_count_mismatch', 'date_join_mismatch', 'column_value_mismatch']
        - columns_changed (list of str): List of affected columns, if applicable
        """
        summary = f"{reason}: {', '.join(columns_changed)}" if columns_changed else reason

        self.cur.execute("""
            INSERT INTO stock_price_audit (ticker, date, column_changed, old_value, new_value)
            VALUES (%s, CURRENT_DATE, %s, NULL, NULL)
        """, (ticker, summary))