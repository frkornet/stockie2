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
        
        # Check for key log messages
        assert any("Starting daily job" in call for call in info_calls)
        assert any("Running load stock prices" in call for call in info_calls)
        assert any("Running calculate technical indicators" in call for call in info_calls)
        assert any("Finished daily job" in call for call in info_calls)

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