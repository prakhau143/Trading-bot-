import os
from functools import lru_cache
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    binance_api_key: str = Field(default="", alias="BINANCE_API_KEY")
    binance_secret_key: str = Field(default="", alias="BINANCE_SECRET_KEY")
    environment: str = Field(default="testnet", alias="ENVIRONMENT")
    max_order_size: float = Field(default=1000.0, alias="MAX_ORDER_SIZE")
    max_leverage: int = Field(default=10, alias="MAX_LEVERAGE")
    default_retries: int = Field(default=3, alias="DEFAULT_RETRIES")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "populate_by_name": True}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def load_yaml_config(env: Optional[str] = None) -> dict:
    if env is None:
        env = get_settings().environment
    config_path = f"config/{env}.yaml"
    if os.path.exists(config_path):
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}
