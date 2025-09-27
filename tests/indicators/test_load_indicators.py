import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_config():
    return {
        "load_indicators": {
            "load_processes": 2,
            "cvs_directory": "/tmp/",
            "log_filename": "/tmp/test.log",
            "log_level": "INFO",
            "console": True,
        }
    }

def test_load_file_batch_success(tmp_path):
    fake_file = tmp_path / "indicators_part1.csv"
    fake_file.write_text("header1,header2\n1,2\n")
    file_list = [str(fake_file)]
    log_path = "/tmp/test.log"

    mock_logger = MagicMock()
    mock_db_util = MagicMock()
    mock_conn = MagicMock()

    with patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.loaders.load_indicators.DatabaseUtilities", return_value=mock_db_util), \
         patch("stockie.loaders.load_indicators.load_dotenv"):
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_file_batch
        load_file_batch(file_list, log_path)

        mock_db_util.copy_from_file.assert_called_once_with(str(fake_file))
        mock_conn.close.assert_called_once()
        mock_logger.info.assert_any_call(f"Loading file: {str(fake_file)}")

def test_load_file_batch_db_failure():
    file_list = ["dummy.csv"]
    log_path = "/tmp/test.log"
    mock_logger = MagicMock()

    with patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.psycopg2.connect", side_effect=Exception("fail")), \
         patch("stockie.loaders.load_indicators.load_dotenv"):
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_file_batch
        load_file_batch(file_list, log_path)
        mock_logger.exception.assert_any_call("Database connection failed: fail")

def test_load_file_batch_file_failure(tmp_path):
    fake_file = tmp_path / "indicators_part1.csv"
    fake_file.write_text("header1,header2\n1,2\n")
    file_list = [str(fake_file)]
    log_path = "/tmp/test.log"

    mock_logger = MagicMock()
    mock_db_util = MagicMock()
    mock_db_util.copy_from_file.side_effect = Exception("file error")
    mock_conn = MagicMock()

    with patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.loaders.load_indicators.DatabaseUtilities", return_value=mock_db_util), \
         patch("stockie.loaders.load_indicators.load_dotenv"):
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_file_batch
        load_file_batch(file_list, log_path)
        assert any(
            "Error loading" in str(call.args[0])
            for call in mock_logger.error.call_args_list
        )

def test_load_technical_indicators_no_files(monkeypatch, mock_config):
    mock_logger = MagicMock()
    with patch("stockie.loaders.load_indicators.ConfigLoader") as mock_loader, \
         patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.glob", return_value=[]):
        mock_loader.return_value.get.return_value = mock_config
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_technical_indicators
        load_technical_indicators("/temp")
        mock_logger.warning.assert_any_call("No CSV files found for ingestion.")

def test_load_technical_indicators_truncate_failure(monkeypatch, mock_config):
    # Simulate failure in truncate_table
    mock_logger = MagicMock()
    mock_conn = MagicMock()
    mock_db_util = MagicMock()
    mock_db_util.truncate_table.side_effect = Exception("truncate fail")

    with patch("stockie.loaders.load_indicators.ConfigLoader") as mock_loader, \
         patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.glob", return_value=["/tmp/indicators_part1.csv"]), \
         patch("stockie.loaders.load_indicators.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.loaders.load_indicators.DatabaseUtilities", return_value=mock_db_util), \
         patch("stockie.loaders.load_indicators.load_dotenv"):
        mock_loader.return_value.get.return_value = mock_config
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_technical_indicators
        load_technical_indicators("/temp/")
        mock_logger.exception.assert_any_call("Failed to truncate table: truncate fail")

def test_load_technical_indicators_success(monkeypatch, mock_config):
    # Simulate successful run with 2 files and 2 processes
    mock_logger = MagicMock()
    mock_conn = MagicMock()
    mock_db_util = MagicMock()
    mock_process = MagicMock()

    with patch("stockie.loaders.load_indicators.ConfigLoader") as mock_loader, \
         patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.glob", return_value=["/tmp/indicators_part1.csv", "/tmp/indicators_part2.csv"]), \
         patch("stockie.loaders.load_indicators.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.loaders.load_indicators.DatabaseUtilities", return_value=mock_db_util), \
         patch("stockie.loaders.load_indicators.Process", return_value=mock_process), \
         patch("stockie.loaders.load_indicators.load_dotenv"):
        mock_loader.return_value.get.return_value = mock_config
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_technical_indicators
        load_technical_indicators("/temp/")
        assert mock_process.start.call_count == 2
        assert mock_process.join.call_count == 2
        mock_logger.info.assert_any_call('*** Finished load technical indicators job.')