from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    mcp_config_path: str = "app/mcp/config/mcp_config.json"
    PPLX_API_KEY: str
    GOOGLE_CREDENTIALS_PATH: str
    GOOGLE_TOKEN_PATH: str

    # Database configuration (PostgreSQL)
    DB_CONNECTION: str = "pgsql"  # expected to be 'pgsql' or 'postgresql'
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_DATABASE: str
    DB_USERNAME: str
    DB_PASSWORD: str
    
    # slack configuration
    SLACK_BOT_TOKEN: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Be tolerant to extra env keys so unknown vars don't break startup
        extra = "ignore"

    def sqlalchemy_driver(self) -> str:
        """Map DB_CONNECTION to a SQLAlchemy driver prefix."""
        conn = self.DB_CONNECTION.lower()
        # Accept common variants
        if conn in {"pgsql", "postgres", "postgresql"}:
            return "postgresql+psycopg2"
        raise ValueError(f"Unsupported DB_CONNECTION value: {self.DB_CONNECTION}")

    def database_url(self, hide_password: bool = False) -> str:
        """Construct the SQLAlchemy Database URL.

        Parameters
        ----------
        hide_password: If True, returns a URL with password redacted (for logs).
        """
        driver = self.sqlalchemy_driver()
        pwd = "***" if hide_password else self.DB_PASSWORD
        return f"{driver}://{self.DB_USERNAME}:{pwd}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}"  # nosec B105


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton style)."""
    return Settings()  # type: ignore


# Backwards compatibility for code importing `settings`
settings = get_settings()