from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EduConnect AI"
    app_env: str = "development"
    database_url: SecretStr
    cors_origins: str = "http://localhost:5000"
    clerk_publishable_key: SecretStr | None = None
    clerk_secret_key: SecretStr | None = None
    replit_dev_domain: str | None = None
    replit_domains: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url.get_secret_value().strip()
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def allowed_origins(self) -> list[str]:
        configured = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        domains = [self.replit_dev_domain or ""]
        domains.extend((self.replit_domains or "").split(","))

        for domain in domains:
            domain = domain.strip()
            if not domain:
                continue
            parsed = urlsplit(domain if "://" in domain else f"https://{domain}")
            if parsed.netloc:
                configured.append(f"{parsed.scheme}://{parsed.netloc}")

        return list(dict.fromkeys(configured))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()