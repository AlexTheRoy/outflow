"""Central config. Reads from environment / .env.

The /analyze demo still runs with zero keys, but production knobs (CORS, API keys,
rate limits, log level) are now first-class so you can lock things down per-env.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Runtime ---
    environment: str = "development"  # development | staging | production
    log_level: str = "INFO"

    # --- Security ---
    # Comma-separated API keys accepted by the API. Empty in development = auth off.
    api_keys: str = ""
    # Comma-separated allowed CORS origins. "*" only honored outside production.
    cors_origins: str = "*"
    # Simple per-IP rate limit (requests per window).
    rate_limit_per_minute: int = 120

    # LLM providers (Anthropic preferred when both set). Optional.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Step 2 — lead data
    apollo_api_key: str = ""
    zoominfo_api_key: str = ""
    clay_api_key: str = ""

    # Step 3 — outreach sending
    instantly_api_key: str = ""
    instantly_campaign_id: str = ""
    smartlead_api_key: str = ""
    smartlead_campaign_id: str = ""

    # Step 4 — dialer
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    # Public TwiML URL Twilio fetches when the call connects (what the callee hears /
    # how the call is bridged). Use a TwiML Bin or your own endpoint.
    twilio_twiml_url: str = ""
    deepgram_api_key: str = ""

    @property
    def email_provider(self) -> str:
        if self.instantly_api_key:
            return "instantly"
        if self.smartlead_api_key:
            return "smartlead"
        return "none"

    # Infra
    database_url: str = "postgresql://localhost:5432/outflow"
    redis_url: str = "redis://localhost:6379/0"

    # ----- Derived helpers -----
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key or self.openai_api_key)

    @property
    def llm_provider(self) -> str:
        if self.anthropic_api_key:
            return "anthropic"
        if self.openai_api_key:
            return "openai"
        return "none"

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def auth_enabled(self) -> bool:
        # Auth is required in production; optional elsewhere unless keys are set.
        return self.is_production or bool(self.api_key_set)

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.is_production and "*" in origins:
            # Never allow wildcard CORS in production.
            return [o for o in origins if o != "*"]
        return origins or ["*"]

    def validate_for_production(self) -> list[str]:
        """Return a list of misconfigurations that are unsafe in production."""
        problems: list[str] = []
        if not self.is_production:
            return problems
        if not self.api_key_set:
            problems.append("API_KEYS must be set in production.")
        if "*" in [o.strip() for o in self.cors_origins.split(",")]:
            problems.append("CORS_ORIGINS must not include '*' in production.")
        if self.database_url.startswith("sqlite"):
            problems.append("Use Postgres (not sqlite) in production.")
        return problems


settings = Settings()
