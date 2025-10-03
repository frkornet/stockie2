import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_daily_config():
    return {
        "console": True,
        "log_level": "INFO",
        "log_filename": "/tmp/daily.log",
        "load_stock_prices": True,
        "calculate_indicators": True,
        "load_indicators": True
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
    mock_logger = MagicMock()
    mock_load_stock_prices = MagicMock()
    mock_calculate_indicators = MagicMock()
    mock_load_technical_indicators = MagicMock()
    mock_conn = MagicMock()
    mock_db_facade = MagicMock()

    with patch("stockie.jobs.daily.ConfigLoader", return_value=mock_config_loader), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.load_stock_prices", mock_load_stock_prices), \
         patch("stockie.jobs.daily.calculate_indicators", mock_calculate_indicators), \
         patch("stockie.jobs.daily.load_technical_indicators", mock_load_technical_indicators), \
         patch("stockie.jobs.daily.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.jobs.daily.DatabaseFacade", return_value=mock_db_facade), \
         patch("os.getenv", return_value="test_password"):

        mock_logger_class.return_value.get_logger.return_value = mock_logger
        mock_conn.get_dsn_parameters.return_value = {"dbname": "test_db"}

        from stockie.jobs.daily import run_daily_job
        run_daily_job("/tmp/configdir")

        # Verify function calls with correct parameters (db_facade and full_config)
        mock_load_stock_prices.assert_called_once()
        mock_calculate_indicators.assert_called_once()
        mock_load_technical_indicators.assert_called_once()
        
        # Verify logger messages
        assert any("Starting daily job" in str(call.args[0]) for call in mock_logger.info.call_args_list)
        assert any("Finished daily job" in str(call.args[0]) for call in mock_logger.info.call_args_list)

def test_run_daily_job_skip_steps(monkeypatch, mock_daily_config):
    # Only load_stock_prices is True
    config = mock_daily_config.copy()
    config["calculate_indicators"] = False
    config["load_indicators"] = False

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
    mock_load_technical_indicators = MagicMock()
    mock_conn = MagicMock()
    mock_db_facade = MagicMock()

    with patch("stockie.jobs.daily.ConfigLoader", return_value=MockConfigLoader()), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.load_stock_prices", mock_load_stock_prices), \
         patch("stockie.jobs.daily.calculate_indicators", mock_calculate_indicators), \
         patch("stockie.jobs.daily.load_technical_indicators", mock_load_technical_indicators), \
         patch("stockie.jobs.daily.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.jobs.daily.DatabaseFacade", return_value=mock_db_facade), \
         patch("os.getenv", return_value="test_password"):

        mock_logger_class.return_value.get_logger.return_value = mock_logger
        mock_conn.get_dsn_parameters.return_value = {"dbname": "test_db"}

        from stockie.jobs.daily import run_daily_job
        run_daily_job("/tmp/configdir")

        # Verify function calls
        mock_load_stock_prices.assert_called_once()
        mock_calculate_indicators.assert_not_called()
        mock_load_technical_indicators.assert_not_called()
        
        # Verify logger messages
        assert any("Starting daily job" in str(call.args[0]) for call in mock_logger.info.call_args_list)
        assert any("Finished daily job" in str(call.args[0]) for call in mock_logger.info.call_args_list)

def test_main_calls_run_daily_job(monkeypatch):
    monkeypatch.setattr('os.path.isdir', lambda x: True)
    
    test_args = ['daily.py', '--config-dir', '/tmp/configdir']
    monkeypatch.setattr('sys.argv', test_args)
    
    mock_run_daily_job = MagicMock()
    with patch("stockie.jobs.daily.run_daily_job", mock_run_daily_job):
        from stockie.jobs import daily
        daily.main()
        
        mock_run_daily_job.assert_called_once_with("/tmp/configdir")

def test_main_exits_when_config_dir_missing(monkeypatch, capsys):
    monkeypatch.setattr('os.path.isdir', lambda x: False)
    
    test_args = ['daily.py', '--config-dir', '/nonexistent/dir']
    monkeypatch.setattr('sys.argv', test_args)
    
    with pytest.raises(SystemExit) as exc_info:
        from stockie.jobs import daily
        daily.main()
    
    assert exc_info.value.code == 1
    
    # Check error message was printed
    captured = capsys.readouterr()
    assert "does not exist" in captured.out

def test_run_daily_job_handles_exception(monkeypatch, mock_daily_config):
    """Test that run_daily_job handles exceptions properly and logs them"""
    
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
    mock_load_indicators = MagicMock()
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
         patch("stockie.jobs.daily.load_technical_indicators", mock_load_indicators), \
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
    # Check for the actual error message format from daily.py
    assert mock_logger.error.call_count >= 1
    mock_exit.assert_called_once_with(1)
    mock_calculate.assert_not_called()
    mock_load_indicators.assert_not_called()


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
    mock_calculate_indicators = MagicMock(side_effect=Exception("Indicator calculation failed"))
    mock_load_indicators = MagicMock()
    mock_conn = MagicMock()
    mock_db_facade = MagicMock()
    
    mock_times = [1000.0, 1030.0, 1060.0, 1090.0]
    mock_datetime = MagicMock()
    mock_datetime.fromtimestamp.return_value = "2023-01-01 12:00:00"
    mock_exit = MagicMock()
    
    with patch("stockie.jobs.daily.ConfigLoader", return_value=MockConfigLoader()), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.load_stock_prices", mock_load_stock_prices), \
         patch("stockie.jobs.daily.calculate_indicators", mock_calculate_indicators), \
         patch("stockie.jobs.daily.load_technical_indicators", mock_load_indicators), \
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
    
    # Verify load_stock_prices was called (it should succeed before calculate_indicators fails)
    mock_load_stock_prices.assert_called_once()
    
    mock_logger.error.assert_called()
    error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
    assert any("Indicator calculation failed" in call for call in error_calls)
    
    mock_exit.assert_called_once_with(1)
    mock_load_indicators.assert_not_called()


def test_run_daily_job_exception_in_load_indicators(monkeypatch, mock_daily_config):
    """Test exception handling when load_technical_indicators fails"""
    
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
    mock_calculate_indicators = MagicMock()
    mock_load_indicators = MagicMock(side_effect=Exception("Failed to load indicators"))
    mock_conn = MagicMock()
    mock_db_facade = MagicMock()
    
    mock_times = [1000.0, 1030.0, 1060.0, 1090.0, 1120.0, 1150.0]
    mock_datetime = MagicMock()
    mock_datetime.fromtimestamp.return_value = "2023-01-01 12:00:00"
    mock_exit = MagicMock()
    
    with patch("stockie.jobs.daily.ConfigLoader", return_value=MockConfigLoader()), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.load_stock_prices", mock_load_stock_prices), \
         patch("stockie.jobs.daily.calculate_indicators", mock_calculate_indicators), \
         patch("stockie.jobs.daily.load_technical_indicators", mock_load_indicators), \
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
    
    # Verify both previous steps were called before load_indicators fails
    mock_load_stock_prices.assert_called_once()
    mock_calculate_indicators.assert_called_once()
    
    mock_logger.error.assert_called()
    error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
    assert any("Failed to load indicators" in call for call in error_calls)
    
    mock_exit.assert_called_once_with(1)