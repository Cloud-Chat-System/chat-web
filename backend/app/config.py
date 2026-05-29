import os
from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    """Load the first .env file found when walking up from this file."""
    for parent in Path(__file__).resolve().parents:
        env_path = parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            break


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_list_env(name: str) -> list[str]:
    value = get_env(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


load_project_env()

DATABASE_URL = get_env("DATABASE_URL", "sqlite:///./tsmc_messenger.db")
JWT_SECRET = get_env("JWT_SECRET", "tsmc_messenger_jwt_secret_key_2024_very_secure")
JWT_ALGORITHM = get_env("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = int(get_env("JWT_EXPIRE_HOURS", "24"))
BACKEND_HOST = get_env("BACKEND_HOST", "0.0.0.0")
BACKEND_CONTAINER_PORT = int(get_env("BACKEND_CONTAINER_PORT", "8000"))
FRONTEND_URL = get_env("FRONTEND_URL", "")
CORS_ALLOWED_ORIGINS = get_list_env("CORS_ALLOWED_ORIGINS")
