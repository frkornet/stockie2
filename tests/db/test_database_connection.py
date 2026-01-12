import pytest
from unittest.mock import MagicMock, patch
from stockie.db.database_connection import DatabaseConnection
from stockie.db.database_facade import DatabaseFacade
import psycopg2


class TestDatabaseConnection:

    @pytest.fixture
    def mock_psycopg2_connect(self):
        """Mock psycopg2.connect to avoid actual database connections."""
        with patch('stockie.db.database_connection.psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = MagicMock()
            mock_connect.return_value = mock_conn
            yield mock_connect

    def test_init_and_connect(self, mock_psycopg2_connect):
        """Test initialization creates connection and database facade."""
        db_conn = DatabaseConnection(
            host='localhost',
            port=5432,
            user='test_user',
            password='test_password',
            dbname='test_db'
        )
        
        assert db_conn.conn is not None
        assert isinstance(db_conn.db_facade, DatabaseFacade)
        mock_psycopg2_connect.assert_called_once()

    def test_init_with_default_dbname(self, mock_psycopg2_connect):
        """Test initialization with default dbname."""
        db_conn = DatabaseConnection(
            host='localhost',
            port=5432,
            user='test_user',
            password='test_password'
        )
        
        assert db_conn.dbname == 'postgres'

    def test_connect_error_raises(self):
        """Test that connection errors are raised."""
        with patch('stockie.db.database_connection.psycopg2.connect') as mock_connect:
            mock_connect.side_effect = psycopg2.OperationalError("Connection failed")
            
            with pytest.raises(psycopg2.OperationalError):
                DatabaseConnection(
                    host='localhost',
                    port=5432,
                    user='test_user',
                    password='test_password'
                )

    def test_disconnect(self, mock_psycopg2_connect):
        """Test disconnect closes connection."""
        db_conn = DatabaseConnection(
            host='localhost',
            port=5432,
            user='test_user',
            password='test_password'
        )
        
        db_conn.disconnect()
        
        mock_psycopg2_connect.return_value.close.assert_called_once()
