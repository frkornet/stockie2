import yaml
import os
from dotenv import load_dotenv

CONFIG_DIR='/home/frkornet/repos/stockie2/config/'

class ConfigLoader:
    def __init__(self, config_path=CONFIG_DIR+"settings.yaml", dotenv_path=CONFIG_DIR+".env"):
        # Load .env file (for DB_PASSWORD and other secure values)
        load_dotenv(dotenv_path)

        # Load YAML file (structured configuration)
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Inject sensitive secrets from environment
        self.config["db"]["password"] = os.getenv("DB_PASSWORD")

    def get(self):
        return self.config