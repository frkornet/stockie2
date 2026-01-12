import pytest
from unittest.mock import MagicMock, patch
from stockie.db.database_connection import DatabaseConnection
from stockie.db.database_facade import DatabaseFacade
import psycopg2


class TestDatabaseConnection:

    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def mock_psycopg2_connect(self):
        """Mock psycopg2.connect to avoid actual database connections."""
        with patch('stockie.db.database_connection.psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = MagicMock()
            mock_connect.return_value = mock_conn
            yield mock_connect

    def test_init_and_connect(self, mock_psycopg2_connect, mock_logger):
        """Test initialization creates connection and database facade."""
        db_conn = DatabaseConnection(
            host='localhost',
            port=5432,
            user='test_user',
            password='test_password',
            dbname='test_db',
            logger=mock_logger
        )
        
        assert db_conn.conn is not None
        assert isinstance(db_conn.db_facade, DatabaseFacade)
        mock_psycopg2_connect.assert_called_once()
        mock_logger.info.assert_called_once()

    def test_connect_with_postgres_dbname(self, mock_psycopg2_connect, mock_logger):
        """Test initialization with postgres dbname."""
        db_conn = DatabaseConnection(
            host='localhost',
            port=5432,
            user='test_user',
            password='test_password',
            dbname='postgres',
            logger=mock_logger
        )
        
        assert db_conn.dbname == 'postgres'

    def test_connect_error_raises(self, mock_logger):
        """Test that connection errors are raised."""
        with patch('stockie.db.database_connection.psycopg2.connect') as mock_connect:
            mock_connect.side_effect = psycopg2.OperationalError("Connection failed")
            
            with pytest.raises(psycopg2.OperationalError):
                DatabaseConnection(
                    host='localhost',
                    port=5432,
                    user='test_user',
                    password='test_password',
                    dbname='test_db',
                    logger=mock_logger
                )
            
            mock_logger.error.assert_called_once()

    def test_disconnect(self, mock_psycopg2_connect, mock_logger):
        """Test disconnect closes connection."""
        db_conn = DatabaseConnection(
            host='localhost',
            port=5432,
            user='test_user',
            password='test_password',
            dbname='test_db',
            logger=mock_logger
        )
        
        db_conn.disconnect()
        
        mock_psycopg2_connect.return_value.close.assert_called_once()
        assert mock_logger.info.call_count == 2  # Once for connect, once for disconnect
