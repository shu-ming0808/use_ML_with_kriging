from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    db_server: str = os.getenv("DB_SERVER", os.getenv("DB_HOST", "127.0.0.1"))
    db_port: int = int(os.getenv("DB_PORT", "3306"))
    db_user: str = os.getenv("DB_USER", "sammy")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_name: str = os.getenv("DB_NAME", "homework")
    db_charset: str = os.getenv("DB_CHARSET", "utf8")
    forecast_variable: str = os.getenv("FORECAST_VARIABLE", "temperature")
    forecast_hours: int = int(os.getenv("FORECAST_HOURS", "24"))
    training_hours: int = int(os.getenv("TRAINING_HOURS", "168"))
    ar_max_lag: int = int(os.getenv("AR_MAX_LAG", "24"))


settings = Settings()

db_settings = {
    "server": settings.db_server,
    "port": settings.db_port,
    "user": settings.db_user,
    "password": settings.db_password,
    "database": settings.db_name,
    "charset": settings.db_charset,
}
