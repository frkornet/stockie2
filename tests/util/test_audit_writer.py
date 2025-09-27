import pytest
from unittest.mock import MagicMock, patch
from stockie.util import AuditWriter

class TestAuditWriter:

    @pytest.fixture
    def mock_db_util(self):
        return MagicMock()

    @pytest.fixture
    def mock_conn(self):
        return MagicMock()

    @pytest.fixture
    def writer(self, mock_conn, mock_db_util):
        with patch("stockie.util.audit_writer.DatabaseUtilities", return_value=mock_db_util):
            return AuditWriter(mock_conn)

    def test_log_change_summary_with_columns(self, writer, mock_db_util):
        writer.log_change_summary(
            ticker="MSFT",
            reason="column_value_mismatch",
            columns_changed=["Adj Close", "Volume"]
        )

        mock_db_util.write_audit_message.assert_called_once()
        args, kwargs = mock_db_util.write_audit_message.call_args
        assert args[0] == "MSFT"
        assert args[1].startswith("column_value_mismatch")
        assert "Adj Close" in args[1]
        assert "Volume" in args[1]

    def test_log_change_summary_without_columns(self, writer, mock_db_util):
        writer.log_change_summary(
            ticker="TSLA",
            reason="row_count_mismatch",
            columns_changed=[]
        )

        mock_db_util.write_audit_message.assert_called_once()
        args, kwargs = mock_db_util.write_audit_message.call_args
        assert args[0] == "TSLA"
        assert args[1] == "row_count_mismatch"

    def test_log_change_summary_none_columns(self, writer, mock_db_util):
        writer.log_change_summary(
            ticker="AAPL",
            reason="no_columns",
            columns_changed=None
        )

        mock_db_util.write_audit_message.assert_called_once()
        args, kwargs = mock_db_util.write_audit_message.call_args
        assert args[0] == "AAPL"
        assert args[1] == "no_columns"

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))