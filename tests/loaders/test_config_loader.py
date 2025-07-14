import pytest
from unittest.mock import mock_open, patch
from stockie.loaders import ConfigLoader

class TestConfigLoader:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.yaml_data = """
db:
  host: localhost
  port: 5432
  user: test_user
reconciliation_days: 30
delta_threshold: 0.0001
log:
  dir: logs/
  filename: app.log
"""
        # Patch open(), dotenv, and getenv
        self.patcher_open = patch("builtins.open", mock_open(read_data=self.yaml_data))
        self.patcher_load_dotenv = patch("dotenv.load_dotenv", lambda *args, **kwargs: None)
        self.patcher_getenv = patch("os.getenv", side_effect=lambda key, default=None: "secret123" if key == "DB_PASSWORD" else default)

        self.patcher_open.start()
        self.patcher_load_dotenv.start()
        self.patcher_getenv.start()

        yield  # Run the test

        self.patcher_open.stop()
        self.patcher_load_dotenv.stop()
        self.patcher_getenv.stop()

    def test_config_loader(self):
        loader = ConfigLoader(config_path="config/settings.yaml", dotenv_path="config/.env")
        config = loader.get()

        assert config["db"]["host"] == "localhost"
        assert config["db"]["port"] == 5432
        assert config["db"]["user"] == "test_user"
        assert config["db"]["password"] == "secret123"
        assert config["reconciliation_days"] == 30
        assert config["delta_threshold"] == 0.0001
        assert config["log"]["filename"] == "app.log"

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))