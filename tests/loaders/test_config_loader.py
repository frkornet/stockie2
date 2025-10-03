import pytest
import os
import tempfile
import yaml
from unittest.mock import patch
from stockie.loaders.config_loader import ConfigLoader

@pytest.fixture
def temp_config_dir():
    """Create a temporary directory with test config files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create .env file
        env_content = "ENVIRONMENT=dev\nDB_PASSWORD=test_password\n"
        with open(os.path.join(temp_dir, '.env'), 'w') as f:
            f.write(env_content)
        
        # Create settings-dev.yaml
        dev_config = {
            'start_date': '2020-01-01',
            'load_stock_prices': {
                'batch_size': 100,
                'log_level': 'INFO'
            },
            'db': {
                'host': 'localhost',
                'port': 5432
            }
        }
        with open(os.path.join(temp_dir, 'settings-dev.yaml'), 'w') as f:
            yaml.dump(dev_config, f)
        
        # Create settings-prod.yaml
        prod_config = {
            'start_date': '2020-01-01',
            'load_stock_prices': {
                'batch_size': 200,
                'log_level': 'WARNING'
            },
            'db': {
                'host': 'prod-server',
                'port': 5432
            }
        }
        with open(os.path.join(temp_dir, 'settings-prod.yaml'), 'w') as f:
            yaml.dump(prod_config, f)
        
        yield temp_dir

@patch.dict(os.environ, {}, clear=True)
def test_config_loader_loads_dev_environment_by_default(temp_config_dir):
    """Test that ConfigLoader loads dev environment by default"""
    config_loader = ConfigLoader(temp_config_dir)
    config = config_loader.get()
    
    assert config_loader.get_environment() == 'dev'
    assert config['load_stock_prices']['batch_size'] == 100
    assert config['load_stock_prices']['log_level'] == 'INFO'
    assert config['db']['host'] == 'localhost'

@patch.dict(os.environ, {}, clear=True)
def test_config_loader_loads_prod_environment(temp_config_dir):
    """Test that ConfigLoader loads prod environment when ENVIRONMENT=prod"""
    # Update .env to use prod environment
    env_content = "ENVIRONMENT=prod\nDB_PASSWORD=test_password\n"
    with open(os.path.join(temp_config_dir, '.env'), 'w') as f:
        f.write(env_content)
    
    config_loader = ConfigLoader(temp_config_dir)
    config = config_loader.get()
    
    assert config_loader.get_environment() == 'prod'
    assert config['load_stock_prices']['batch_size'] == 200
    assert config['load_stock_prices']['log_level'] == 'WARNING'
    assert config['db']['host'] == 'prod-server'

def test_config_loader_missing_dotenv_file():
    """Test that ConfigLoader raises error when .env file is missing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Don't create .env file
        with pytest.raises(FileNotFoundError) as exc_info:
            ConfigLoader(temp_dir)
        
        assert ".env file not found" in str(exc_info.value)
        assert temp_dir in str(exc_info.value)

@patch.dict(os.environ, {}, clear=True)
def test_config_loader_missing_settings_file(temp_config_dir):
    """Test that ConfigLoader raises error when settings file is missing"""
    # Update .env to use staging environment (no settings-staging.yaml exists)
    env_content = "ENVIRONMENT=staging\nDB_PASSWORD=test_password\n"
    with open(os.path.join(temp_config_dir, '.env'), 'w') as f:
        f.write(env_content)
    
    with pytest.raises(FileNotFoundError) as exc_info:
        ConfigLoader(temp_config_dir)
    
    assert "Configuration file not found" in str(exc_info.value)
    assert "settings-staging.yaml" in str(exc_info.value)

def test_config_loader_invalid_yaml(temp_config_dir):
    """Test that ConfigLoader raises error for invalid YAML"""
    # Create invalid YAML file
    invalid_yaml = "invalid: yaml: content: [unclosed"
    with open(os.path.join(temp_config_dir, 'settings-dev.yaml'), 'w') as f:
        f.write(invalid_yaml)
    
    config_loader = ConfigLoader(temp_config_dir)
    
    with pytest.raises(ValueError) as exc_info:
        config_loader.get()
    
    assert "Invalid YAML in configuration file" in str(exc_info.value)

def test_config_loader_empty_yaml_file(temp_config_dir):
    """Test that ConfigLoader raises error for empty YAML file"""
    # Create empty YAML file
    with open(os.path.join(temp_config_dir, 'settings-dev.yaml'), 'w') as f:
        f.write("")
    
    config_loader = ConfigLoader(temp_config_dir)
    
    with pytest.raises(ValueError) as exc_info:
        config_loader.get()
    
    assert "Configuration file is empty" in str(exc_info.value)

def test_config_loader_get_config_path(temp_config_dir):
    """Test that get_config_path returns correct path"""
    config_loader = ConfigLoader(temp_config_dir)
    
    expected_path = os.path.join(temp_config_dir, 'settings-dev.yaml')
    assert config_loader.get_config_path() == expected_path

@patch.dict(os.environ, {}, clear=True)
def test_config_loader_fallback_to_dev_environment():
    """Test that ConfigLoader falls back to dev when ENVIRONMENT is not set"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create .env without ENVIRONMENT variable
        env_content = "DB_PASSWORD=test_password\n"
        with open(os.path.join(temp_dir, '.env'), 'w') as f:
            f.write(env_content)
        
        # Create settings-dev.yaml
        dev_config = {'start_date': '2020-01-01'}
        with open(os.path.join(temp_dir, 'settings-dev.yaml'), 'w') as f:
            yaml.dump(dev_config, f)
        
        config_loader = ConfigLoader(temp_dir)
        
        assert config_loader.get_environment() == 'dev'
        assert 'settings-dev.yaml' in config_loader.get_config_path()

@patch.dict(os.environ, {}, clear=True)
def test_config_loader_with_environment_variable_override(temp_config_dir):
    """Test that ConfigLoader respects ENVIRONMENT variable even if set outside .env"""
    # Set environment variable directly (simulating container/system env var)
    with patch.dict(os.environ, {'ENVIRONMENT': 'prod'}):
        # Note: .env still has ENVIRONMENT=dev, but os.environ takes precedence
        config_loader = ConfigLoader(temp_config_dir)
        config = config_loader.get()
        
        # Should load prod config due to environment variable override
        assert config_loader.get_environment() == 'prod'
        assert config['load_stock_prices']['batch_size'] == 200

def test_config_loader_handles_nonexistent_directory():
    """Test that ConfigLoader handles non-existent config directory"""
    with pytest.raises(FileNotFoundError):
        ConfigLoader("/nonexistent/directory")

def test_config_loader_loads_complex_config_structure(temp_config_dir):
    """Test that ConfigLoader properly loads complex nested configuration"""
    config_loader = ConfigLoader(temp_config_dir)
    config = config_loader.get()
    
    # Verify nested structure is preserved
    assert 'load_stock_prices' in config
    assert 'batch_size' in config['load_stock_prices']
    assert 'db' in config
    assert 'host' in config['db']
    assert isinstance(config['db']['port'], int)

def test_config_loader_multiple_instances_same_directory(temp_config_dir):
    """Test that multiple ConfigLoader instances work correctly"""
    config_loader1 = ConfigLoader(temp_config_dir)
    config_loader2 = ConfigLoader(temp_config_dir)
    
    config1 = config_loader1.get()
    config2 = config_loader2.get()
    
    assert config1 == config2
    assert config_loader1.get_environment() == config_loader2.get_environment()
    assert config_loader1.get_config_path() == config_loader2.get_config_path()