import pytest
from unittest.mock import MagicMock
from stockie.audit_writer import AuditWriter

class TestAuditWriter:

    @pytest.fixture
    def mock_cursor(self):
        return MagicMock()

    @pytest.fixture
    def writer(self, mock_cursor):
        return AuditWriter(mock_cursor)

    def test_log_change_summary_with_columns(self, writer, mock_cursor):
        writer.log_change_summary(
            ticker="MSFT",
            reason="column_value_mismatch",
            columns_changed=["Adj Close", "Volume"]
        )

        mock_cursor.execute.assert_called_once()
        query, params = mock_cursor.execute.call_args[0]
        assert "INSERT INTO stock_price_audit" in query
        assert params == ("MSFT", "column_value_mismatch: Adj Close, Volume")

    def test_log_change_summary_without_columns(self, writer, mock_cursor):
        writer.log_change_summary(
            ticker="TSLA",
            reason="row_count_mismatch",
            columns_changed=[]
        )

        mock_cursor.execute.assert_called_once()
        query, params = mock_cursor.execute.call_args[0]
        assert "INSERT INTO stock_price_audit" in query
        assert params == ("TSLA", "row_count_mismatch")

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))