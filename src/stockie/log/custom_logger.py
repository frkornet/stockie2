import logging
import os

class CustomLogger:
    def __init__(
        self,
        name=__name__,
        log_to_console=True,
        log_level=logging.INFO,
        log_dir='',
        log_filename="stock_price_ingestor.log"
    ):
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, log_filename)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        self.logger.propagate = False

        if not self.logger.handlers:
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s"
            ))
            self.logger.addHandler(file_handler)

            if log_to_console:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(message)s"
                ))
                self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger