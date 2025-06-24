import pytest
import logging
from unittest.mock import patch, MagicMock
from stockie.custom_logger import CustomLogger

class TestCustomLogger:

    @pytest.fixture(autouse=True)
    def reset_logging(self):
        logging.shutdown()
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        yield
        logging.shutdown()

    @patch("os.makedirs")
    @patch("logging.FileHandler")
    @patch("logging.StreamHandler")
    def test_logger_sets_handlers(self, mock_stream, mock_file, mock_makedirs):
        file_handler = MagicMock()
        stream_handler = MagicMock()
        mock_file.return_value = file_handler
        mock_stream.return_value = stream_handler

        logger = CustomLogger(
            name="test_logger",
            log_to_console=True,
            log_filename="unit_test.log"
        ).get_logger()

        assert file_handler.setFormatter.called
        assert stream_handler.setFormatter.called
        assert any(isinstance(h, MagicMock) for h in logger.handlers)

    @patch("logging.FileHandler")
    def test_logger_respects_log_level(self, mock_file):
        file_handler = MagicMock()
        mock_file.return_value = file_handler

        logger = CustomLogger(name="level_test", log_level=logging.DEBUG).get_logger()
        assert logger.level == logging.DEBUG

    @patch("logging.FileHandler")
    @patch("logging.StreamHandler")
    def test_logger_skips_console_if_disabled(self, mock_stream, mock_file):
        logger = CustomLogger(name="no_console", log_to_console=False).get_logger()
        mock_stream.assert_not_called()

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))