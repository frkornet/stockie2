import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_daily_config():
    return {
        "console": True,
        "log_level": "INFO",
        "log_filename": "/tmp/daily.log",
        "load_stock_prices": True,
        "calculate_indicators": True
    }

@pytest.fixture
def mock_config_loader(mock_daily_config):
    class MockConfigLoader:
        def get(self):
            return {
                "daily_job": mock_daily_config,
                "db": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "stockie",
                    "user": "test_user"
                }
            }
    return MockConfigLoader()

def test_run_daily_job_all_steps(monkeypatch, mock_config_loader, mock_daily_config):
    """Test that all enabled steps are executed"""
    mock_logger = MagicMock()
    mock_load_stock_prices = MagicMock()
    mock_calculate_indicators = MagicMock()
    mock_conn = MagicMock()
    mock_db_facade = MagicMock()

    with patch("stockie.jobs.daily.ConfigLoader", return_value=mock_config_loader), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.load_stock_prices", mock_load_stock_prices), \
         patch("stockie.jobs.daily.calculate_indicators", mock_calculate_indicators), \
         patch("stockie.jobs.daily.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.jobs.daily.DatabaseFacade", return_value=mock_db_facade), \
         patch("os.getenv", return_value="test_password"):

        mock_logger_class.return_value.get_logger.return_value = mock_logger
        mock_conn.get_dsn_parameters.return_value = {"dbname": "test_db"}

        from stockie.jobs.daily import run_daily_job
        run_daily_job("/tmp/configdir")

        # Verify both functions were called with correct parameters
        mock_load_stock_prices.assert_called_once()
        mock_calculate_indicators.assert_called_once()
        
        # Verify they were called with the database facade
        load_args = mock_load_stock_prices.call_args[0]
        calc_args = mock_calculate_indicators.call_args[0]
        assert load_args[0] == mock_db_facade
        assert calc_args[0] == mock_db_facade
        
        # Verify logging
        mock_logger.info.assert_called()
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        
        # Check for key log messages from new phase-based workflow
        assert any("Starting daily job" in call for call in info_calls)
        assert any("Phase 2: Loading stock prices" in call for call in info_calls)
        assert any("Phase 3: Calculating technical indicators" in call for call in info_calls)
        assert any("Phase 4: Performing atomic table swap" in call for call in info_calls)
        assert any("Finished daily job" in call for call in info_calls)
        
        # Verify the new helper methods were called on db_facade
        mock_db_facade.drop_stockie_tables.assert_called_once()
        mock_db_facade.create_temp_tables.assert_called_once()
        mock_db_facade.atomic_table_swap.assert_called_once()

def test_run_daily_job_skip_steps(monkeypatch, mock_daily_config):
    # Only load_stock_prices is True
    config = mock_daily_config.copy()
    config["calculate_indicators"] = False

    class MockConfigLoader:
        def get(self):
            return {
                "daily_job": config,
                "db": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "stockie",
                    "user": "test_user"
                }
            }

    mock_logger = MagicMock()
    mock_load_stock_prices = MagicMock()
    mock_calculate_indicators = MagicMock()
    mock_conn = MagicMock()
    mock_db_facade = MagicMock()

    with patch("stockie.jobs.daily.ConfigLoader", return_value=MockConfigLoader()), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.load_stock_prices", mock_load_stock_prices), \
         patch("stockie.jobs.daily.calculate_indicators", mock_calculate_indicators), \
         patch("stockie.jobs.daily.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.jobs.daily.DatabaseFacade", return_value=mock_db_facade), \
         patch("os.getenv", return_value="test_password"):

        mock_logger_class.return_value.get_logger.return_value = mock_logger
        mock_conn.get_dsn_parameters.return_value = {"dbname": "test_db"}

        from stockie.jobs.daily import run_daily_job
        run_daily_job("/tmp/configdir")

        # Only load_stock_prices should be called
        mock_load_stock_prices.assert_called_once()
        mock_calculate_indicators.assert_not_called()
        
        # Verify appropriate log messages
        assert any("Finished daily job" in str(call.args[0]) for call in mock_logger.info.call_args_list)

def test_run_daily_job_exception_in_load_stock_prices(monkeypatch, mock_daily_config):
    """Test exception handling when load_stock_prices fails"""
    
    class MockConfigLoader:
        def get(self):
            return {
                "daily_job": mock_daily_config,
                "db": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "stockie",
                    "user": "test_user"
                }
            }
    
    mock_logger = MagicMock()
    mock_load_stock_prices = MagicMock(side_effect=Exception("Database connection failed"))
    mock_calculate = MagicMock()
    mock_conn = MagicMock()
    mock_db_facade = MagicMock()
    
    mock_times = [1000.0, 1060.0]
    mock_datetime = MagicMock()
    mock_datetime.fromtimestamp.return_value = "2023-01-01 12:00:00"
    mock_exit = MagicMock()
    
    with patch("stockie.jobs.daily.ConfigLoader", return_value=MockConfigLoader()), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.load_stock_prices", mock_load_stock_prices), \
         patch("stockie.jobs.daily.calculate_indicators", mock_calculate), \
         patch("stockie.jobs.daily.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.jobs.daily.DatabaseFacade", return_value=mock_db_facade), \
         patch("os.getenv", return_value="test_password"), \
         patch("time.time", side_effect=mock_times), \
         patch("stockie.jobs.daily.datetime", mock_datetime), \
         patch("sys.exit", mock_exit):
        
        mock_logger_class.return_value.get_logger.return_value = mock_logger
        mock_conn.get_dsn_parameters.return_value = {"dbname": "test_db"}
        
        from stockie.jobs.daily import run_daily_job
        run_daily_job('/tmp/config')
    
        mock_logger.error.assert_called()
        error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
        
        assert any("Database connection failed" in call for call in error_calls)
        assert mock_logger.error.call_count >= 1
        mock_exit.assert_called_once_with(1)
        mock_calculate.assert_not_called()


def test_run_daily_job_exception_in_calculate_indicators(monkeypatch, mock_daily_config):
    """Test exception handling when calculate_indicators fails"""
    
    class MockConfigLoader:
        def get(self):
            return {
                "daily_job": mock_daily_config,
                "db": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "stockie",
                    "user": "test_user"
                }
            }
    
    mock_logger = MagicMock()
    mock_load_stock_prices = MagicMock()
    mock_calculate_indicators = MagicMock(side_effect=Exception("Calculation failed"))
    mock_conn = MagicMock()
    mock_db_facade = MagicMock()
    
    mock_times = [1000.0, 1030.0, 1060.0, 1090.0, 1120.0]
    mock_datetime = MagicMock()
    mock_datetime.fromtimestamp.return_value = "2023-01-01 12:00:00"
    mock_exit = MagicMock()
    
    with patch("stockie.jobs.daily.ConfigLoader", return_value=MockConfigLoader()), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.load_stock_prices", mock_load_stock_prices), \
         patch("stockie.jobs.daily.calculate_indicators", mock_calculate_indicators), \
         patch("stockie.jobs.daily.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.jobs.daily.DatabaseFacade", return_value=mock_db_facade), \
         patch("os.getenv", return_value="test_password"), \
         patch("time.time", side_effect=mock_times), \
         patch("stockie.jobs.daily.datetime", mock_datetime), \
         patch("sys.exit", mock_exit):
        
        mock_logger_class.return_value.get_logger.return_value = mock_logger
        mock_conn.get_dsn_parameters.return_value = {"dbname": "test_db"}
        
        from stockie.jobs.daily import run_daily_job
        run_daily_job('/tmp/config')
    
        # Verify load_stock_prices was called before calculate_indicators fails
        mock_load_stock_prices.assert_called_once()
        
        mock_logger.error.assert_called()
        error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
        assert any("Calculation failed" in call for call in error_calls)
        
        mock_exit.assert_called_once_with(1)

def test_run_daily_job_config_loader_failure():
    """Test handling of ConfigLoader initialization failure"""
    mock_exit = MagicMock(side_effect=SystemExit(1))  # Make it actually exit
    
    with patch("stockie.jobs.daily.ConfigLoader", side_effect=Exception("Config load failed")), \
         patch("sys.exit", mock_exit), \
         patch("builtins.print") as mock_print:
        
        from stockie.jobs.daily import run_daily_job
        
        with pytest.raises(SystemExit):
            run_daily_job("/tmp/config")
        
        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once_with("FATAL: Failed to load configuration, initialize logger, or connect to database: Config load failed")


def test_run_daily_job_database_connection_failure():
    """Test handling of database connection failure"""
    mock_config_loader = MagicMock()
    mock_config_loader.get.return_value = {
        "daily_job": {
            "console": True,
            "log_level": "INFO",
            "log_filename": "/tmp/daily.log",
            "load_stock_prices": True,
            "calculate_indicators": True
        },
        "db": {
            "host": "localhost",
            "port": 5432,
            "database": "stockie",
            "user": "test_user"
        }
    }
    
    mock_exit = MagicMock(side_effect=SystemExit(1))  # Make it actually exit
    
    with patch("stockie.jobs.daily.ConfigLoader", return_value=mock_config_loader), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.psycopg2.connect", side_effect=Exception("DB connection failed")), \
         patch("os.getenv", return_value="test_password"), \
         patch("sys.exit", mock_exit), \
         patch("builtins.print") as mock_print:
        
        mock_logger_class.return_value.get_logger.return_value = MagicMock()
        
        from stockie.jobs.daily import run_daily_job
        
        with pytest.raises(SystemExit):
            run_daily_job("/tmp/config")
        
        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once_with("FATAL: Failed to load configuration, initialize logger, or connect to database: DB connection failed")


def test_run_daily_job_connection_close_error():
    """Test handling of database connection close error"""
    mock_config_loader = MagicMock()
    mock_config_loader.get.return_value = {
        "daily_job": {
            "console": True,
            "log_level": "INFO", 
            "log_filename": "/tmp/daily.log",
            "load_stock_prices": True,
            "calculate_indicators": False
        },
        "db": {
            "host": "localhost",
            "port": 5432,
            "database": "stockie",
            "user": "test_user"
        }
    }
    
    mock_logger = MagicMock()
    mock_conn = MagicMock()
    mock_db_facade = MagicMock()
    mock_load_stock_prices = MagicMock()
    
    # Make connection.close() raise an exception
    mock_conn.close.side_effect = Exception("Close failed")
    
    with patch("stockie.jobs.daily.ConfigLoader", return_value=mock_config_loader), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.load_stock_prices", mock_load_stock_prices), \
         patch("stockie.jobs.daily.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.jobs.daily.DatabaseFacade", return_value=mock_db_facade), \
         patch("os.getenv", return_value="test_password"):
        
        mock_logger_class.return_value.get_logger.return_value = mock_logger
        mock_conn.get_dsn_parameters.return_value = {"dbname": "test_db"}
        
        from stockie.jobs.daily import run_daily_job
        run_daily_job("/tmp/config")
    
    # Verify the close error was logged
    mock_logger.error.assert_called_with("Error closing database connection: Close failed")


def test_initialize_components_success():
    """Test successful initialization of components"""
    mock_config_loader = MagicMock()
    mock_config_loader.get.return_value = {
        "daily_job": {
            "console": True,
            "log_level": "INFO",
            "log_filename": "/tmp/logs/daily.log"
        },
        "db": {
            "host": "localhost",
            "port": 5432,
            "database": "stockie",
            "user": "test_user"
        }
    }
    
    mock_logger = MagicMock()
    mock_conn = MagicMock()
    mock_db_facade = MagicMock()
    
    with patch("stockie.jobs.daily.ConfigLoader", return_value=mock_config_loader), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.jobs.daily.DatabaseFacade", return_value=mock_db_facade), \
         patch("os.getenv", return_value="test_password"):
        
        mock_logger_class.return_value.get_logger.return_value = mock_logger
        mock_conn.get_dsn_parameters.return_value = {"dbname": "stockie"}
        
        from stockie.jobs.daily import _initialize_components
        logger, conn, db_facade, full_config = _initialize_components("/tmp/config")
        
        assert logger == mock_logger
        assert conn == mock_conn
        assert db_facade == mock_db_facade
        assert "daily_job" in full_config
        assert "db" in full_config
        
        # Verify logger was initialized correctly
        mock_logger_class.assert_called_once()
        
        # Verify database connection was established
        mock_logger.info.assert_called_with("Connected to database: stockie")


def test_initialize_components_failure():
    """Test initialization failure handling"""
    mock_exit = MagicMock(side_effect=SystemExit(1))
    
    with patch("stockie.jobs.daily.ConfigLoader", side_effect=Exception("Config error")), \
         patch("sys.exit", mock_exit), \
         patch("builtins.print") as mock_print:
        
        from stockie.jobs.daily import _initialize_components
        
        with pytest.raises(SystemExit):
            _initialize_components("/tmp/config")
        
        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once_with(
            "FATAL: Failed to load configuration, initialize logger, or connect to database: Config error"
        )


def test_cleanup_temp_tables():
    """Test cleanup of temporary tables"""
    mock_db_facade = MagicMock()
    mock_logger = MagicMock()
    
    from stockie.jobs.daily import _cleanup_temp_tables
    _cleanup_temp_tables(mock_db_facade, "test_user", mock_logger)
    
    # Verify drop_stockie_tables was called with correct parameters
    mock_db_facade.drop_stockie_tables.assert_called_once_with(
        table_filter=['stock_prices', 'technical_indicators'],
        name_suffix='_temp'
    )
    
    # Verify logging
    assert mock_logger.info.call_count == 2
    info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
    assert any("Phase 0: Cleaning up" in call for call in info_calls)
    assert any("Cleanup complete" in call for call in info_calls)


def test_create_temp_tables():
    """Test creation of temporary tables"""
    mock_db_facade = MagicMock()
    mock_logger = MagicMock()
    
    from stockie.jobs.daily import _create_temp_tables
    _create_temp_tables(mock_db_facade, "test_user", mock_logger)
    
    # Verify create_temp_tables was called with owner
    mock_db_facade.create_temp_tables.assert_called_once_with("test_user")
    
    # Verify logging
    assert mock_logger.info.call_count == 2
    info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
    assert any("Phase 1: Creating temporary tables" in call for call in info_calls)
    assert any("Temporary tables created" in call for call in info_calls)


def test_load_prices_to_temp_enabled():
    """Test loading stock prices when enabled"""
    mock_db_facade = MagicMock()
    mock_logger = MagicMock()
    full_config = {
        "daily_job": {
            "load_stock_prices": True
        }
    }
    
    with patch("stockie.jobs.daily.load_stock_prices") as mock_load, \
         patch("time.time", side_effect=[1000.0, 1060.0]), \
         patch("stockie.jobs.daily.datetime") as mock_datetime:
        
        mock_datetime.fromtimestamp.return_value = "2023-01-01 12:00:00"
        
        from stockie.jobs.daily import _load_prices_to_temp
        _load_prices_to_temp(mock_db_facade, full_config, mock_logger)
        
        # Verify load_stock_prices was called
        mock_load.assert_called_once_with(mock_db_facade, full_config)
        
        # Verify logging includes phase and duration
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Phase 2: Loading stock prices" in call for call in info_calls)
        assert any("loaded into temp table in" in call and "minutes" in call for call in info_calls)


def test_load_prices_to_temp_disabled():
    """Test loading stock prices when disabled"""
    mock_db_facade = MagicMock()
    mock_logger = MagicMock()
    full_config = {
        "daily_job": {
            "load_stock_prices": False
        }
    }
    
    with patch("stockie.jobs.daily.load_stock_prices") as mock_load:
        from stockie.jobs.daily import _load_prices_to_temp
        _load_prices_to_temp(mock_db_facade, full_config, mock_logger)
        
        # Verify load_stock_prices was NOT called
        mock_load.assert_not_called()
        
        # Verify skip message was logged
        mock_logger.info.assert_called_once_with(
            "Phase 2: Stock price loading skipped (disabled in config)"
        )


def test_calculate_indicators_to_temp_enabled():
    """Test calculating indicators when enabled"""
    mock_db_facade = MagicMock()
    mock_logger = MagicMock()
    full_config = {
        "daily_job": {
            "calculate_indicators": True
        }
    }
    
    with patch("stockie.jobs.daily.calculate_indicators") as mock_calc, \
         patch("time.time", side_effect=[1000.0, 1120.0]), \
         patch("stockie.jobs.daily.datetime") as mock_datetime:
        
        mock_datetime.fromtimestamp.return_value = "2023-01-01 12:00:00"
        
        from stockie.jobs.daily import _calculate_indicators_to_temp
        _calculate_indicators_to_temp(mock_db_facade, full_config, mock_logger)
        
        # Verify calculate_indicators was called with source_table parameter
        mock_calc.assert_called_once_with(mock_db_facade, full_config, source_table='stock_prices_temp')
        
        # Verify logging includes phase and duration
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Phase 3: Calculating technical indicators" in call for call in info_calls)
        assert any("calculated in" in call and "minutes" in call for call in info_calls)


def test_calculate_indicators_to_temp_disabled():
    """Test calculating indicators when disabled"""
    mock_db_facade = MagicMock()
    mock_logger = MagicMock()
    full_config = {
        "daily_job": {
            "calculate_indicators": False
        }
    }
    
    with patch("stockie.jobs.daily.calculate_indicators") as mock_calc:
        from stockie.jobs.daily import _calculate_indicators_to_temp
        _calculate_indicators_to_temp(mock_db_facade, full_config, mock_logger)
        
        # Verify calculate_indicators was NOT called
        mock_calc.assert_not_called()
        
        # Verify skip message was logged
        mock_logger.info.assert_called_once_with(
            "Phase 3: Indicator calculation skipped (disabled in config)"
        )


def test_atomic_table_swap():
    """Test atomic table swap operation"""
    mock_db_facade = MagicMock()
    mock_logger = MagicMock()
    
    with patch("time.time", side_effect=[1000.0, 1005.5]):
        from stockie.jobs.daily import _atomic_table_swap
        _atomic_table_swap(mock_db_facade, "test_user", mock_logger)
        
        # Verify atomic_table_swap was called
        mock_db_facade.atomic_table_swap.assert_called_once()
        
        # Verify logging includes phase and duration
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Phase 4: Performing atomic table swap" in call for call in info_calls)
        assert any("Atomic swap completed in" in call and "seconds" in call for call in info_calls)
        assert any("New data is now live" in call for call in info_calls)


def test_handle_job_failure():
    """Test job failure handling"""
    mock_logger = MagicMock()
    mock_exit = MagicMock(side_effect=SystemExit(1))
    
    with patch("sys.exit", mock_exit), \
         patch("builtins.print") as mock_print:
        
        from stockie.jobs.daily import _handle_job_failure
        
        with pytest.raises(SystemExit):
            _handle_job_failure(Exception("Test error"), mock_logger)
        
        # Verify error logging
        assert mock_logger.error.call_count == 5
        error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
        assert any("DAILY JOB FAILED: Test error" in call for call in error_calls)
        assert any("Temp tables preserved" in call for call in error_calls)
        assert any("stock_prices_temp" in call for call in error_calls)
        assert any("technical_indicators_temp" in call for call in error_calls)
        
        # Verify console output
        assert mock_print.call_count == 2
        print_calls = [call.args[0] for call in mock_print.call_args_list]
        assert any("DAILY JOB FAILED" in call for call in print_calls)
        assert any("Temp tables preserved" in call for call in print_calls)
        
        # Verify exit was called
        mock_exit.assert_called_once_with(1)


def test_cleanup_database_connection_success():
    """Test successful database connection cleanup"""
    mock_conn = MagicMock()
    mock_logger = MagicMock()
    
    from stockie.jobs.daily import _cleanup_database_connection
    _cleanup_database_connection(mock_conn, mock_logger)
    
    # Verify connection was closed
    mock_conn.close.assert_called_once()
    
    # Verify logging
    mock_logger.info.assert_called_once_with("Database connection closed")
    mock_logger.error.assert_not_called()


def test_cleanup_database_connection_failure():
    """Test database connection cleanup with error"""
    mock_conn = MagicMock()
    mock_conn.close.side_effect = Exception("Close error")
    mock_logger = MagicMock()
    
    from stockie.jobs.daily import _cleanup_database_connection
    _cleanup_database_connection(mock_conn, mock_logger)
    
    # Verify connection.close was attempted
    mock_conn.close.assert_called_once()
    
    # Verify error was logged
    mock_logger.error.assert_called_once_with("Error closing database connection: Close error")
    mock_logger.info.assert_not_called()


def test_cleanup_database_connection_none():
    """Test database connection cleanup with None connection"""
    mock_logger = MagicMock()
    
    from stockie.jobs.daily import _cleanup_database_connection
    _cleanup_database_connection(None, mock_logger)
    
    # Verify no logging occurred (connection was None)
    mock_logger.info.assert_not_called()
    mock_logger.error.assert_not_called()


def test_main_function_with_valid_directory():
    """Test main function with valid config directory"""
    with patch("stockie.jobs.daily.run_daily_job") as mock_run_daily, \
         patch("os.path.isdir", return_value=True), \
         patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
        
        mock_parse_args.return_value.config_dir = "/tmp/config"
        
        from stockie.jobs.daily import main
        main()
        
        mock_run_daily.assert_called_once_with("/tmp/config")


def test_main_function_with_invalid_directory():
    """Test main function with invalid config directory"""
    mock_exit = MagicMock(side_effect=SystemExit(1))  # Make it actually exit
    
    with patch("os.path.isdir", return_value=False), \
         patch("argparse.ArgumentParser.parse_args") as mock_parse_args, \
         patch("sys.exit", mock_exit), \
         patch("builtins.print") as mock_print:
        
        mock_parse_args.return_value.config_dir = "/nonexistent"
        
        from stockie.jobs.daily import main
        
        with pytest.raises(SystemExit):
            main()
            
        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once_with("Error: Configuration directory '/nonexistent' does not exist")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))