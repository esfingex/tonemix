"""
Configuration loader for ToneMix
"""
import os
import yaml
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration manager for ToneMix"""
    
    _instance = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from config.yaml and environment variables"""
        # Load environment variables
        load_dotenv()
        
        # Get config file path
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        
        # Load YAML config
        if config_path.exists():
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Replace environment variable placeholders
        self._replace_env_vars(self._config)
    
    def _replace_env_vars(self, config: Dict[str, Any]):
        """Recursively replace ${VAR} with environment variables"""
        for key, value in config.items():
            if isinstance(value, dict):
                self._replace_env_vars(value)
            elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                config[key] = os.getenv(env_var, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'database.host')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    @property
    def database(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self._config.get('database', {})
    
    @property
    def audio(self) -> Dict[str, Any]:
        """Get audio configuration"""
        return self._config.get('audio', {})
    
    @property
    def transcoding(self) -> Dict[str, Any]:
        """Get transcoding configuration"""
        return self._config.get('transcoding', {})
    
    @property
    def ui(self) -> Dict[str, Any]:
        """Get UI configuration"""
        return self._config.get('ui', {})
    
    @property
    def analysis(self) -> Dict[str, Any]:
        """Get analysis configuration"""
        return self._config.get('analysis', {})
    
    @property
    def export(self) -> Dict[str, Any]:
        """Get export configuration"""
        return self._config.get('export', {})


# Singleton instance
config = Config()
