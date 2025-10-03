import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_config():
    return {
        "load_indicators": {
            "load_processes": 2,
            "csv_directory": "/tmp/",
            "log_filename": "/tmp/test.log",
            "log_level": "INFO",
            "console": True,
        },
        "db": {
            "host": "localhost",
            "port": 5432,
            "dbname": "test_db",
            "user": "test_user"
        }
    }

def test_load_file_batch_success(tmp_path, mock_config):
    fake_file = tmp_path / "indicators_part1.csv"
    fake_file.write_text("header1,header2\n1,2\n")
    file_list = [str(fake_file)]

    mock_logger = MagicMock()
    mock_db_util = MagicMock()
    mock_conn = MagicMock()

    with patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.loaders.load_indicators.DatabaseFacade", return_value=mock_db_util), \
         patch("stockie.loaders.load_indicators.load_dotenv"):
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_file_batch
        load_file_batch(file_list, mock_logger, mock_config["db"])

        mock_db_util.copy_from_file.assert_called_once_with(str(fake_file))
        mock_conn.close.assert_called_once()
        mock_logger.info.assert_any_call(f"Loading file: {str(fake_file)}")

def test_load_file_batch_db_failure(mock_config):
    file_list = ["dummy.csv"]
    mock_logger = MagicMock()

    with patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.psycopg2.connect", side_effect=Exception("fail")), \
         patch("stockie.loaders.load_indicators.load_dotenv"):
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_file_batch
        load_file_batch(file_list, mock_logger, mock_config["db"])
        mock_logger.exception.assert_any_call("Database connection failed: fail")

def test_load_file_batch_file_failure(tmp_path, mock_config):
    fake_file = tmp_path / "indicators_part1.csv"
    fake_file.write_text("header1,header2\n1,2\n")
    file_list = [str(fake_file)]

    mock_logger = MagicMock()
    mock_db_util = MagicMock()
    mock_db_util.copy_from_file.side_effect = Exception("file error")
    mock_conn = MagicMock()

    with patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.psycopg2.connect", return_value=mock_conn), \
         patch("stockie.loaders.load_indicators.DatabaseFacade", return_value=mock_db_util), \
         patch("stockie.loaders.load_indicators.load_dotenv"):
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_file_batch
        load_file_batch(file_list, mock_logger, mock_config["db"])
        assert any(
            "Error loading" in str(call.args[0])
            for call in mock_logger.error.call_args_list
        )

def test_load_technical_indicators_no_files(monkeypatch, mock_config):
    mock_logger = MagicMock()
    mock_db_facade = MagicMock()
    
    with patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.glob", return_value=[]):
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_technical_indicators
        load_technical_indicators(mock_db_facade, mock_config)
        mock_logger.warning.assert_any_call("No CSV files found for ingestion.")

def test_load_technical_indicators_truncate_failure(monkeypatch, mock_config):
    mock_logger = MagicMock()
    mock_db_facade = MagicMock()
    mock_db_facade.truncate_table.side_effect = Exception("truncate fail")

    with patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.glob", return_value=["/tmp/indicators_part1.csv"]):
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_technical_indicators
        load_technical_indicators(mock_db_facade, mock_config)
        mock_logger.exception.assert_any_call("Failed to truncate table: truncate fail")

def test_load_technical_indicators_success(monkeypatch, mock_config):
    mock_logger = MagicMock()
    mock_db_facade = MagicMock()
    mock_process = MagicMock()

    with patch("stockie.loaders.load_indicators.CustomLogger") as mock_logger_class, \
         patch("stockie.loaders.load_indicators.glob", return_value=["/tmp/indicators_part1.csv", "/tmp/indicators_part2.csv"]), \
         patch("stockie.loaders.load_indicators.Process", return_value=mock_process):
        mock_logger_class.return_value.get_logger.return_value = mock_logger

        from stockie.loaders.load_indicators import load_technical_indicators
        load_technical_indicators(mock_db_facade, mock_config)
        assert mock_process.start.call_count == 2
        assert mock_process.join.call_count == 2
        mock_logger.info.assert_any_call('*** Finished load technical indicators job.')