"""
ArtFlow Studio - Configuration Manager
"""

import os
import json
from pathlib import Path
from typing import Any, Optional
import yaml

class Config:
    """Application configuration manager with persistence."""
    
    _instance: Optional['Config'] = None
    
    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._config: dict = {}
        self._config_path: Path = self._get_config_path()
        self._load_config()
    
    def _get_config_path(self) -> Path:
        """Get the configuration file path."""
        if os.name == 'nt':  # Windows
            app_data = Path(os.environ.get('APPDATA', ''))
            config_dir = app_data / 'ArtFlowStudio'
        else:  # Linux/Mac
            config_dir = Path.home() / '.config' / 'artflow-studio'
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / 'config.yaml'
    
    def _load_config(self):
        """Load configuration from file."""
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error loading config: {e}")
                self._config = {}
        else:
            self._config = self._get_default_config()
            self._save_config()
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def _get_default_config(self) -> dict:
        """Get default configuration values."""
        return {
            'window': {
                'width': 1600,
                'height': 900,
                'maximized': False,
                'x': None,
                'y': None
            },
            'canvas': {
                'default_width': 2048,
                'default_height': 2048,
                'background_color': '#ffffff',
                'grid_enabled': False,
                'grid_size': 32
            },
            'brush': {
                'default_size': 20,
                'default_opacity': 100,
                'stabilizer_enabled': True,
                'stabilizer_strength': 50,
                'pressure_sensitivity': True
            },
            'ui': {
                'theme': 'dark',
                'language': 'es',
                'sidebar_position': 'left',
                'toolbar_visible': True,
                'panels_visible': {
                    'layers': True,
                    'colors': True,
                    'brushes': True,
                    'navigator': True
                }
            },
            'performance': {
                'hardware_acceleration': True,
                'max_undo_steps': 50,
                'auto_save_interval': 300,  # seconds
                'cache_size_mb': 500
            },
            'paths': {
                'brushes': None,  # Will use default
                'projects': None,
                'exports': None
            },
            'youtube': {
                'api_key': None,
                'autoplay': False,
                'quality': '720p'
            },
            'recent_files': [],
            'recent_brushes': []
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, save: bool = True):
        """Set a configuration value using dot notation."""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        if save:
            self._save_config()
    
    def reset(self):
        """Reset configuration to defaults."""
        self._config = self._get_default_config()
        self._save_config()
    
    @property
    def config_path(self) -> Path:
        """Get the configuration file path."""
        return self._config_path
    
    @property
    def data_path(self) -> Path:
        """Get the application data directory path."""
        return self._config_path.parent
    
    @property
    def brushes_path(self) -> Path:
        """Get the brushes directory path."""
        custom_path = self.get('paths.brushes')
        if custom_path:
            return Path(custom_path)
        return self.data_path / 'brushes'
    
    @property
    def cache_path(self) -> Path:
        """Get the cache directory path."""
        cache_dir = self.data_path / 'cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir


# Global config instance
config = Config()
