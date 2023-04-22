import os
import json
from dataclasses import dataclass

@dataclass
class AppConfig:
    DEBUG: bool
    SECRET_KEY: str

def load_config(environment: str) -> AppConfig:
    config_file = f"appsettings.{environment.lower()}.json"
    config_file_path = os.path.join(os.path.dirname(__file__), config_file)
    with open(config_file_path, "r") as file:
        config_data = json.load(file)

    return AppConfig(**config_data)

# Load configuration on import, so it's available globally
environment = os.environ.get("APP_ENV", "development")
app_config = load_config(environment)
