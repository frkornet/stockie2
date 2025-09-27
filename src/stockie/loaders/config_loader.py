import yaml
import os
from dotenv import load_dotenv

class ConfigLoader:
    def __init__(self, config_path, dotenv_path):
        # Load .env file (for DB_PASSWORD and other secure values)
        load_dotenv(dotenv_path)

        # Load YAML file (structured configuration)
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Inject sensitive secrets from environment
        self.config["db"]["password"] = os.getenv("DB_PASSWORD")

    def get(self):
        return self.config