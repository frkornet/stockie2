import pytest
from unittest.mock import MagicMock
from stockie.db.droppers import DropDatabase, DropTablespaces, DropSchema
from stockie.db.database_connection import DatabaseConnection
from stockie.db.database_facade import DatabaseFacade


class TestDropDatabase:

    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def mock_db_connection(self):
        """Mock DatabaseConnection with mocked DatabaseFacade."""
        mock_conn = MagicMock(spec=DatabaseConnection)
        mock_facade = MagicMock(spec=DatabaseFacade)
        mock_conn.db_facade = mock_facade
        return mock_conn

    def test_drop_database_calls_facade_methods(self, mock_db_connection, mock_logger):
        """Test that DropDatabase calls drop_database and drop_user on facade."""
        dropper = DropDatabase(
            database_connection=mock_db_connection,
            database='test_db',
            user='test_user',
            logger=mock_logger
        )
        
        mock_db_connection.db_facade.drop_database.assert_called_once_with('test_db')
        mock_db_connection.db_facade.drop_user.assert_called_once_with('test_user')
        assert dropper.database == 'test_db'
        assert dropper.user == 'test_user'
        assert mock_logger.info.call_count == 4  # Two info calls for database, two for user

    def test_drop_database_raises_on_error(self, mock_db_connection, mock_logger):
        """Test that errors from facade are propagated."""
        mock_db_connection.db_facade.drop_database.side_effect = Exception("Drop database failed")
        
        with pytest.raises(Exception, match="Drop database failed"):
            DropDatabase(
                database_connection=mock_db_connection,
                database='test_db',
                user='test_user',
                logger=mock_logger
            )


class TestDropTablespaces:

    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def mock_db_connection(self):
        """Mock DatabaseConnection with mocked DatabaseFacade."""
        mock_conn = MagicMock(spec=DatabaseConnection)
        mock_facade = MagicMock(spec=DatabaseFacade)
        mock_conn.db_facade = mock_facade
        return mock_conn

    def test_drop_tablespaces_calls_facade(self, mock_db_connection, mock_logger):
        """Test that DropTablespaces calls drop_stockie_tablespaces on facade."""
        dropper = DropTablespaces(
            database_connection=mock_db_connection,
            owner='test_owner',
            logger=mock_logger
        )
        
        mock_db_connection.db_facade.drop_stockie_tablespaces.assert_called_once_with(owner='test_owner')
        assert dropper.owner == 'test_owner'
        assert mock_logger.info.call_count == 2  # Starting and completion messages

    def test_drop_tablespaces_raises_on_error(self, mock_db_connection, mock_logger):
        """Test that errors from facade are propagated."""
        mock_db_connection.db_facade.drop_stockie_tablespaces.side_effect = Exception("Drop tablespaces failed")
        
        with pytest.raises(Exception, match="Drop tablespaces failed"):
            DropTablespaces(
                database_connection=mock_db_connection,
                owner='test_owner',
                logger=mock_logger
            )


class TestDropSchema:

    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def mock_db_connection(self):
        """Mock DatabaseConnection with mocked DatabaseFacade."""
        mock_conn = MagicMock(spec=DatabaseConnection)
        mock_facade = MagicMock(spec=DatabaseFacade)
        mock_conn.db_facade = mock_facade
        return mock_conn

    def test_drop_schema_calls_facade(self, mock_db_connection, mock_logger):
        """Test that DropSchema calls drop_stockie_tables on facade."""
        dropper = DropSchema(
            database_connection=mock_db_connection,
            logger=mock_logger
        )
        
        mock_db_connection.db_facade.drop_stockie_tables.assert_called_once()
        assert mock_logger.info.call_count == 2  # Starting and completion messages

    def test_drop_schema_raises_on_error(self, mock_db_connection, mock_logger):
        """Test that errors from facade are propagated."""
        mock_db_connection.db_facade.drop_stockie_tables.side_effect = Exception("Drop tables failed")
        
        with pytest.raises(Exception, match="Drop tables failed"):
            DropSchema(
                database_connection=mock_db_connection,
                logger=mock_logger
            )
