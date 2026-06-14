"""API tests. Run with: pytest -q"""
from app.config import settings


def test_auth_enforced_when_keys_set(client, monkeypatch):
    monkeypatch.setattr(settings, "api_keys", "secret-key")
    # No key -> rejected
    r = client.post("/leads/find", json={"icp": {"titles": ["VP Sales"]}, "limit": 1})
    assert r.status_code == 401
    # Correct key -> accepted
    r = client.post(
        "/leads/find",
        json={"icp": {"titles": ["VP Sales"]}, "limit": 1},
        headers={"Authorization": "Bearer secret-key"},
    )
    assert r.status_code == 200


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_reports_db(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["database"] is True


def test_analyze_returns_profile_and_persists(client):
    r = client.post("/analyze", json={"url": "https://acme.example"})
    assert r.status_code == 200
    body = r.json()
    assert body["product"]  # heuristic extracted something
    assert "icp" in body
    # Persistence wired the campaign id back onto the response.
    assert body["campaign_id"]


def test_analyze_rejects_bad_url(client):
    r = client.post("/analyze", json={"url": "not-a-url"})
    assert r.status_code == 422  # pydantic HttpUrl validation


def test_leads_find_returns_mock(client):
    r = client.post("/leads/find", json={"icp": {"titles": ["VP Sales"]}, "limit": 3})
    assert r.status_code == 200
    leads = r.json()
    assert len(leads) == 3
    assert leads[0]["fit_score"] >= 0.5


def test_outreach_generate(client):
    payload = {
        "profile": {"url": "x", "product": "Outflow"},
        "lead": {"name": "Dana Lee", "title": "VP Sales", "company": "Cascade"},
        "channel": "email",
    }
    r = client.post("/outreach/generate", json=payload)
    assert r.status_code == 200
    assert r.json()["body"]


def test_content_research(client):
    payload = {"lead": {"name": "Dana Lee", "title": "VP Sales", "company": "Cascade GTM"}}
    r = client.post("/content/research", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["company"] == "Cascade GTM"
    assert body["pain_points"]


def test_content_social(client):
    payload = {
        "profile": {"url": "x", "product": "Outflow", "value_prop": "Find buyers fast."},
        "platform": "linkedin",
    }
    r = client.post("/content/social", json=payload)
    assert r.status_code == 200
    assert r.json()["body"]


def test_content_script(client):
    payload = {"lead": {"name": "Dana Lee", "title": "VP Sales", "company": "Cascade GTM"}}
    r = client.post("/content/script", json=payload)
    assert r.status_code == 200
    assert r.json()["opener"]


def test_dial_simulated(client):
    r = client.post(
        "/dial",
        json={"lead": {"name": "Dana Lee", "title": "VP Sales", "company": "Cascade"}},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "simulated"


def test_send_without_provider_is_not_sent(client):
    payload = {
        "lead": {"name": "Dana Lee", "title": "VP Sales", "company": "Cascade", "email": "dana@cascade.com"},
        "message": {"channel": "email", "subject": "Hi", "body": "Hello there"},
    }
    r = client.post("/outreach/send", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "not_sent"  # no provider configured in tests


def test_send_linkedin_is_blocked(client):
    payload = {
        "lead": {"name": "Dana Lee", "title": "VP Sales", "company": "Cascade"},
        "message": {"channel": "linkedin", "body": "Hi Dana"},
    }
    r = client.post("/outreach/send", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "not_sent"
