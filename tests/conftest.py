"""Test fixtures. Uses an in-memory sqlite DB and stubs the network scraper so
tests run offline and deterministically."""
import os

# Configure env BEFORE importing the app so settings pick it up.
# File-based sqlite (not :memory:) so every connection shares the same DB.
os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = "sqlite:///./test_outflow.db"
os.environ["API_KEYS"] = ""  # auth off for the default client
os.environ["RATE_LIMIT_PER_MINUTE"] = "0"  # disable limiter in tests

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.services import scraper


@pytest.fixture(autouse=True)
def _create_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _stub_scraper(monkeypatch):
    async def fake_scrape(url, timeout=15.0):
        return scraper.ScrapeResult(
            url=url,
            title="Acme Billing",
            description="Usage-based billing for SaaS. Plans from $99/mo.",
            headings=["Acme Billing", "Stop leaking revenue"],
            text="Acme Billing helps finance and revops teams automate invoicing. $99/mo.",
        )

    monkeypatch.setattr(scraper, "scrape", fake_scrape)


@pytest.fixture
def client():
    return TestClient(app)
