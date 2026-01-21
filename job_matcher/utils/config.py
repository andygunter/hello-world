"""
Configuration management for Job Matcher.
"""

from pathlib import Path
from typing import Optional
import json
import os


class Config:
    """Manages application configuration and API keys."""

    DEFAULT_CONFIG = {
        "api_keys": {
            "linkedin": "",
            "indeed": "",
            "glassdoor": "",
            "anthropic": "",
            "openai": "",
        },
        "search": {
            "default_limit": 50,
            "providers": ["greenhouse", "lever", "indeed", "linkedin", "glassdoor"],
            "parallel_search": True,
        },
        "generation": {
            "output_dir": "./generated_documents",
            "use_ai": True,
            "default_format": "markdown",
        },
        "application": {
            "auto_apply": False,
            "dry_run": True,
            "require_confirmation": True,
            "rate_limit": 10,
            "data_dir": "./application_data",
        },
        "profile": {
            "default_profile_path": "./profile.json",
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config file (default: ~/.job_matcher/config.json)
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path.home() / ".job_matcher" / "config.json"

        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                user_config = json.load(f)

            # Merge with defaults
            return self._deep_merge(self.DEFAULT_CONFIG.copy(), user_config)

        return self.DEFAULT_CONFIG.copy()

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def save(self) -> None:
        """Save current configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get(self, key: str, default=None):
        """
        Get a configuration value using dot notation.

        Args:
            key: Configuration key (e.g., "api_keys.linkedin")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value) -> None:
        """
        Set a configuration value using dot notation.

        Args:
            key: Configuration key (e.g., "api_keys.linkedin")
            value: Value to set
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_api_key(self, provider: str) -> str:
        """
        Get API key for a provider.

        Checks both config file and environment variables.
        Environment variables take precedence.

        Args:
            provider: Provider name (linkedin, indeed, anthropic, etc.)

        Returns:
            API key string
        """
        # Check environment variable first
        env_var = f"{provider.upper()}_API_KEY"
        env_value = os.environ.get(env_var)

        if env_value:
            return env_value

        # Fall back to config file
        return self.get(f"api_keys.{provider}", "")

    def set_api_key(self, provider: str, key: str) -> None:
        """Set API key for a provider."""
        self.set(f"api_keys.{provider}", key)
        self.save()

    def get_providers_config(self) -> dict:
        """Get configuration for all job search providers."""
        return {
            "indeed_api_key": self.get_api_key("indeed"),
            "linkedin_api_key": self.get_api_key("linkedin"),
            "glassdoor_api_key": self.get_api_key("glassdoor"),
        }

    def get_output_dir(self) -> str:
        """Get the document output directory."""
        return self.get("generation.output_dir", "./generated_documents")

    def get_data_dir(self) -> str:
        """Get the application data directory."""
        return self.get("application.data_dir", "./application_data")

    def is_dry_run(self) -> bool:
        """Check if auto-apply is in dry run mode."""
        return self.get("application.dry_run", True)

    def print_config(self) -> None:
        """Print current configuration (with API keys masked)."""
        masked_config = self._mask_sensitive(self.config)
        print(json.dumps(masked_config, indent=2))

    def _mask_sensitive(self, data: dict, sensitive_keys: set = None) -> dict:
        """Mask sensitive values in configuration."""
        if sensitive_keys is None:
            sensitive_keys = {"api_key", "api_keys", "key", "secret", "password", "token"}

        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self._mask_sensitive(value, sensitive_keys)
            elif any(s in key.lower() for s in sensitive_keys):
                if value:
                    result[key] = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "****"
                else:
                    result[key] = "(not set)"
            else:
                result[key] = value
        return result

    @classmethod
    def create_default_config(cls, path: str = None) -> 'Config':
        """Create a new config file with default values."""
        config = cls(path)
        config.save()
        return config
