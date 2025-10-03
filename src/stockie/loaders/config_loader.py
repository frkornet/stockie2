import os
import yaml
from dotenv import load_dotenv

class ConfigLoader:
    """
    Configuration loader that automatically selects environment-specific settings files
    based on ENVIRONMENT variable in .env file.
    
    File naming convention: settings-{environment}.yaml
    - settings-dev.yaml
    - settings-staging.yaml  
    - settings-prod.yaml
    """
    
    def __init__(self, config_dir: str) -> None:
        """
        Initialize ConfigLoader with config directory path
        
        Args:
            config_dir: Path to configuration directory containing .env and settings-*.yaml files
        """
        self.config_dir = config_dir
        self.dotenv_path = os.path.join(config_dir, '.env')
        
        # Load environment variables from .env
        if os.path.exists(self.dotenv_path):
            load_dotenv(self.dotenv_path)
        else:
            raise FileNotFoundError(f".env file not found: {self.dotenv_path}")
        
        # Get environment and construct config file path
        self.environment = os.getenv('ENVIRONMENT', 'dev')
        self.config_path = os.path.join(config_dir, f'settings-{self.environment}.yaml')
        
        # Validate config file exists
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

    def get(self) -> dict:
        """
        Load and return configuration from the selected settings file
        
        Returns:
            dict: Configuration dictionary
        """
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
                
            if config is None:
                raise ValueError(f"Configuration file is empty: {self.config_path}")
                
            return config
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file {self.config_path}: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except PermissionError:
            raise PermissionError(f"Permission denied reading configuration file: {self.config_path}")
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Unexpected error loading configuration from {self.config_path}: {e}")

    def get_environment(self) -> str:
        """Get the current environment"""
        return self.environment

    def get_config_path(self) -> str:
        """Get the path to the configuration file being used"""
        return self.config_path