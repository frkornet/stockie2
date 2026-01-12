import pytest
from unittest.mock import MagicMock, patch
from stockie.db.creators import CreateDatabase, CreateTablespaces, CreateSchema
from stockie.db.database_connection import DatabaseConnection
from stockie.db.database_facade import DatabaseFacade


class TestCreateDatabase:

    @pytest.fixture
    def mock_db_connection(self):
        """Mock DatabaseConnection with mocked DatabaseFacade."""
        mock_conn = MagicMock(spec=DatabaseConnection)
        mock_facade = MagicMock(spec=DatabaseFacade)
        mock_conn.db_facade = mock_facade
        return mock_conn

    def test_create_database_calls_facade_methods(self, mock_db_connection):
        """Test that CreateDatabase calls create_user and create_database on facade."""
        creator = CreateDatabase(
            database_connection=mock_db_connection,
            database='test_db',
            user='test_user',
            password='test_pass'
        )
        
        mock_db_connection.db_facade.create_user.assert_called_once_with('test_user', 'test_pass')
        mock_db_connection.db_facade.create_database.assert_called_once_with('test_db', owner='test_user')
        assert creator.database == 'test_db'
        assert creator.user == 'test_user'
        assert creator.password == 'test_pass'

    def test_create_database_raises_on_error(self, mock_db_connection):
        """Test that errors from facade are propagated."""
        mock_db_connection.db_facade.create_user.side_effect = Exception("User creation failed")
        
        with pytest.raises(Exception, match="User creation failed"):
            CreateDatabase(
                database_connection=mock_db_connection,
                database='test_db',
                user='test_user',
                password='test_pass'
            )


class TestCreateTablespaces:

    @pytest.fixture
    def mock_db_connection(self):
        """Mock DatabaseConnection with mocked DatabaseFacade."""
        mock_conn = MagicMock(spec=DatabaseConnection)
        mock_facade = MagicMock(spec=DatabaseFacade)
        mock_conn.db_facade = mock_facade
        return mock_conn

    def test_create_tablespaces_calls_facade(self, mock_db_connection):
        """Test that CreateTablespaces calls create_stockie_tablespaces on facade."""
        creator = CreateTablespaces(
            database_connection=mock_db_connection,
            user='test_user',
            data_path='/data/path',
            index_path='/index/path'
        )
        
        mock_db_connection.db_facade.create_stockie_tablespaces.assert_called_once_with(
            '/data/path', '/index/path', 'test_user'
        )
        assert creator.user == 'test_user'
        assert creator.data_path == '/data/path'
        assert creator.index_path == '/index/path'

    def test_create_tablespaces_raises_on_error(self, mock_db_connection):
        """Test that errors from facade are propagated."""
        mock_db_connection.db_facade.create_stockie_tablespaces.side_effect = Exception("Tablespace creation failed")
        
        with pytest.raises(Exception, match="Tablespace creation failed"):
            CreateTablespaces(
                database_connection=mock_db_connection,
                user='test_user',
                data_path='/data/path',
                index_path='/index/path'
            )


class TestCreateSchema:

    @pytest.fixture
    def mock_db_connection(self):
        """Mock DatabaseConnection with mocked DatabaseFacade."""
        mock_conn = MagicMock(spec=DatabaseConnection)
        mock_facade = MagicMock(spec=DatabaseFacade)
        mock_conn.db_facade = mock_facade
        return mock_conn

    def test_create_schema_calls_facade(self, mock_db_connection):
        """Test that CreateSchema calls create_stockie_tables on facade."""
        creator = CreateSchema(
            database_connection=mock_db_connection,
            owner='test_owner'
        )
        
        mock_db_connection.db_facade.create_stockie_tables.assert_called_once_with('test_owner')
        assert creator.owner == 'test_owner'

    def test_create_schema_raises_on_error(self, mock_db_connection):
        """Test that errors from facade are propagated."""
        mock_db_connection.db_facade.create_stockie_tables.side_effect = Exception("Schema creation failed")
        
        with pytest.raises(Exception, match="Schema creation failed"):
            CreateSchema(
                database_connection=mock_db_connection,
                owner='test_owner'
            )
