from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "XHS Analysis"
    database_url: str = Field(
        default="mysql+pymysql://xhs:xhs_password@127.0.0.1:3306/xhs_analysis",
        alias="DATABASE_URL",
    )
    adb_serial: str = Field(default="127.0.0.1:15555", alias="ADB_SERIAL")
    ui_dump_dir: str = Field(default="/tmp/xhs-ui-tags", alias="UI_DUMP_DIR")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
