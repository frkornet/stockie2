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
            return {"daily_job": mock_daily_config}
    return MockConfigLoader()

def test_run_daily_job_all_steps(monkeypatch, mock_config_loader, mock_daily_config):
    mock_logger = MagicMock()
    mock_load_stock_prices = MagicMock()
    mock_calculate_indicators = MagicMock()
    mock_load_technical_indicators = MagicMock()

    with patch("stockie.jobs.daily.ConfigLoader", return_value=mock_config_loader), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.load_stock_prices", mock_load_stock_prices), \
         patch("stockie.jobs.daily.calculate_indicators", mock_calculate_indicators), \
         patch("stockie.jobs.daily.load_technical_indicators", mock_load_technical_indicators):

        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.jobs.daily import run_daily_job
        run_daily_job("/tmp/configdir")

        mock_load_stock_prices.assert_called_once_with("/tmp/configdir")
        mock_calculate_indicators.assert_called_once_with("/tmp/configdir")
        mock_load_technical_indicators.assert_called_once_with("/tmp/configdir")
        assert any("Starting daily job" in str(call.args[0]) for call in mock_logger.info.call_args_list)
        assert any("Finished daily job" in str(call.args[0]) for call in mock_logger.info.call_args_list)

def test_run_daily_job_skip_steps(monkeypatch, mock_daily_config):
    # Only load_stock_prices is True
    config = mock_daily_config.copy()
    config["calculate_indicators"] = False
    config["load_indicators"] = False

    class MockConfigLoader:
        def get(self):
            return {"daily_job": config}

    mock_logger = MagicMock()
    mock_load_stock_prices = MagicMock()
    mock_calculate_indicators = MagicMock()
    mock_load_technical_indicators = MagicMock()

    with patch("stockie.jobs.daily.ConfigLoader", return_value=MockConfigLoader()), \
         patch("stockie.jobs.daily.CustomLogger") as mock_logger_class, \
         patch("stockie.jobs.daily.load_stock_prices", mock_load_stock_prices), \
         patch("stockie.jobs.daily.calculate_indicators", mock_calculate_indicators), \
         patch("stockie.jobs.daily.load_technical_indicators", mock_load_technical_indicators):

        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.jobs.daily import run_daily_job
        run_daily_job("/tmp/configdir")

        mock_load_stock_prices.assert_called_once_with("/tmp/configdir")
        mock_calculate_indicators.assert_not_called()
        mock_load_technical_indicators.assert_not_called()
        assert any("Starting daily job" in str(call.args[0]) for call in mock_logger.info.call_args_list)
        assert any("Finished daily job" in str(call.args[0]) for call in mock_logger.info.call_args_list)

def test_main_calls_run_daily_job(monkeypatch):
    mock_run_daily_job = MagicMock()
    with patch("stockie.jobs.daily.run_daily_job", mock_run_daily_job):
        import sys
        sys_argv_backup = sys.argv
        sys.argv = ["daily.py", "--config-dir", "/tmp/configdir"]
        from stockie.jobs import daily
        daily.main()
        mock_run_daily_job.assert_called_once_with("/tmp/configdir")
        sys.argv = sys_argv_backup