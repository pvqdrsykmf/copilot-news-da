"""Configurazione centrale del bot, caricata da env."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Tutte le impostazioni del bot. Caricate da .env o variabili d'ambiente."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Alpaca
    alpaca_api_key: SecretStr = Field(default=SecretStr(""))
    alpaca_api_secret: SecretStr = Field(default=SecretStr(""))
    alpaca_live: bool = False
    live_confirm: str = ""

    # Risk
    max_position_pct: float = 0.10
    max_gross_exposure: float = 1.0
    daily_loss_limit_pct: float = 0.03
    max_drawdown_pct: float = 0.15

    # Infra
    log_level: str = "INFO"
    log_dir: Path = Path("./logs")
    db_path: Path = Path("./data/trading.db")

    @field_validator("max_position_pct", "daily_loss_limit_pct", "max_drawdown_pct")
    @classmethod
    def _pct_in_range(cls, v: float) -> float:
        if not 0 < v <= 1:
            raise ValueError("percentuale deve essere in (0, 1]")
        return v

    @property
    def is_live(self) -> bool:
        """Vero solo se ENTRAMBI i flag sono espliciti. Sicurezza by design."""
        return self.alpaca_live and self.live_confirm == "I_KNOW_WHAT_I_AM_DOING"

    @property
    def alpaca_paper(self) -> bool:
        return not self.is_live

    def ensure_dirs(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Singleton delle settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_dirs()
    return _settings
