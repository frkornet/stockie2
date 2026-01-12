import pytest
import sys
from unittest.mock import MagicMock, patch, call
from argparse import Namespace
from stockie.cli.__main__ import (
    parse_arguments,
    validate_arguments,
    create_stockie_database,
    drop_stockie_database,
    cli_processor
)


class TestParseArguments:

    def test_parse_arguments_create_database(self):
        """Test parsing create database command."""
        test_args = [
            'create', 'database',
            '--host', 'testhost',
            '--port', '5433',
            '--database', 'test_db',
            '--admin-user', 'admin',
            '--admin-password', 'admin_pass',
            '--user', 'testuser',
            '--password', 'testpass',
            '--data-path', '/data',
            '--index-path', '/index'
        ]
        
        with patch('sys.argv', ['stockie'] + test_args):
            args = parse_arguments()
            
        assert args.action == 'create'
        assert args.action_object == 'database'
        assert args.host == 'testhost'
        assert args.port == 5433
        assert args.database == 'test_db'
        assert args.admin_user == 'admin'
        assert args.admin_password == 'admin_pass'
        assert args.user == 'testuser'
        assert args.password == 'testpass'
        assert args.data_path == '/data'
        assert args.index_path == '/index'


class TestValidateArguments:

    def test_validate_create_database_with_paths(self):
        """Test validation passes for create database with paths."""
        args = Namespace(data_path='/data', index_path='/index')
        
        # Should not raise or exit
        validate_arguments('create', 'database', args)

    def test_validate_create_database_missing_paths(self):
        """Test validation fails for create database without paths."""
        args = Namespace(data_path=None, index_path=None)
        
        with pytest.raises(SystemExit):
            validate_arguments('create', 'database', args)

    def test_validate_drop_database_no_path_required(self):
        """Test validation passes for drop database without paths."""
        args = Namespace(data_path=None, index_path=None)
        
        # Should not raise or exit
        validate_arguments('drop', 'database', args)


class TestCreateStockieDatabase:

    @patch('stockie.cli.__main__.DatabaseConnection')
    @patch('stockie.cli.__main__.CreateDatabase')
    @patch('stockie.cli.__main__.CreateTablespaces')
    @patch('stockie.cli.__main__.CreateSchema')
    def test_create_stockie_database(self, mock_schema, mock_tablespaces, 
                                     mock_create_db, mock_db_conn):
        """Test create_stockie_database calls all creator classes."""
        mock_admin_conn = MagicMock()
        mock_user_conn = MagicMock()
        mock_db_conn.side_effect = [mock_admin_conn, mock_user_conn]
        
        args = Namespace(
            host='localhost',
            port=5432,
            database='test_db',
            admin_user='admin',
            admin_password='admin_pass',
            user='testuser',
            password='testpass',
            data_path='/data',
            index_path='/index'
        )
        
        create_stockie_database(args)
        
        # Verify connections created
        assert mock_db_conn.call_count == 2
        mock_db_conn.assert_any_call(
            host='localhost', port=5432, dbname='postgres',
            user='admin', password='admin_pass'
        )
        mock_db_conn.assert_any_call(
            host='localhost', port=5432, dbname='test_db',
            user='testuser', password='testpass'
        )
        
        # Verify creator classes called
        mock_create_db.assert_called_once_with(
            database_connection=mock_admin_conn,
            database='test_db',
            user='testuser',
            password='testpass'
        )
        mock_tablespaces.assert_called_once_with(
            database_connection=mock_admin_conn,
            user='testuser',
            data_path='/data',
            index_path='/index'
        )
        mock_schema.assert_called_once_with(
            database_connection=mock_user_conn,
            owner='testuser'
        )
        
        # Verify connections disconnected
        assert mock_admin_conn.disconnect.call_count == 1
        assert mock_user_conn.disconnect.call_count == 1


class TestDropStockieDatabase:

    @patch('stockie.cli.__main__.DatabaseConnection')
    @patch('stockie.cli.__main__.DropSchema')
    @patch('stockie.cli.__main__.DropTablespaces')
    @patch('stockie.cli.__main__.DropDatabase')
    def test_drop_stockie_database(self, mock_drop_db, mock_drop_tablespaces,
                                   mock_drop_schema, mock_db_conn):
        """Test drop_stockie_database calls all dropper classes."""
        mock_user_conn = MagicMock()
        mock_admin_conn = MagicMock()
        mock_db_conn.side_effect = [mock_user_conn, mock_admin_conn]
        
        args = Namespace(
            host='localhost',
            port=5432,
            database='test_db',
            admin_user='admin',
            admin_password='admin_pass',
            user='testuser',
            password='testpass'
        )
        
        drop_stockie_database(args)
        
        # Verify connections created
        assert mock_db_conn.call_count == 2
        mock_db_conn.assert_any_call(
            host='localhost', port=5432, dbname='test_db',
            user='testuser', password='testpass'
        )
        mock_db_conn.assert_any_call(
            host='localhost', port=5432, dbname='postgres',
            user='admin', password='admin_pass'
        )
        
        # Verify dropper classes called
        mock_drop_schema.assert_called_once_with(
            database_connection=mock_user_conn
        )
        mock_drop_tablespaces.assert_called_once_with(
            database_connection=mock_admin_conn,
            owner='testuser'
        )
        mock_drop_db.assert_called_once_with(
            database_connection=mock_admin_conn,
            database='test_db',
            user='testuser'
        )
        
        # Verify connections disconnected
        assert mock_user_conn.disconnect.call_count == 1
        assert mock_admin_conn.disconnect.call_count == 1


class TestCliProcessor:

    @patch('stockie.cli.__main__.parse_arguments')
    @patch('stockie.cli.__main__.validate_arguments')
    @patch('stockie.cli.__main__.create_stockie_database')
    def test_cli_processor_create_database(self, mock_create, mock_validate, mock_parse):
        """Test cli_processor calls create_stockie_database."""
        mock_args = Namespace(
            action='create',
            action_object='database',
            data_path='/data',
            index_path='/index'
        )
        mock_parse.return_value = mock_args
        
        cli_processor()
        
        mock_parse.assert_called_once()
        mock_validate.assert_called_once_with('create', 'database', mock_args)
        mock_create.assert_called_once_with(mock_args)

    @patch('stockie.cli.__main__.parse_arguments')
    @patch('stockie.cli.__main__.validate_arguments')
    @patch('stockie.cli.__main__.drop_stockie_database')
    def test_cli_processor_drop_database(self, mock_drop, mock_validate, mock_parse):
        """Test cli_processor calls drop_stockie_database."""
        mock_args = Namespace(
            action='drop',
            action_object='database'
        )
        mock_parse.return_value = mock_args
        
        cli_processor()
        
        mock_parse.assert_called_once()
        mock_validate.assert_called_once_with('drop', 'database', mock_args)
        mock_drop.assert_called_once_with(mock_args)

    @patch('stockie.cli.__main__.parse_arguments')
    @patch('stockie.cli.__main__.validate_arguments')
    def test_cli_processor_invalid_action(self, mock_validate, mock_parse):
        """Test cli_processor exits on invalid action."""
        mock_args = Namespace(
            action='invalid',
            action_object='database'
        )
        mock_parse.return_value = mock_args
        
        with pytest.raises(SystemExit):
            cli_processor()
