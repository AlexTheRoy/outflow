"""Step 2 — find buyers.

Live Apollo integration when APOLLO_API_KEY is set; mock leads otherwise so the
pipeline is testable end to end without a paid account.

Apollo endpoint used: POST https://api.apollo.io/v1/mixed_people/search
Docs: https://docs.apollo.io/reference/people-search
Note: search returns people but often masks emails. Revealing a verified email is a
second, credit-consuming call (people/match) — sketched in `_reveal_email` and left
off by default so you don't burn credits unintentionally.
"""
from __future__ import annotations

import httpx

from ..config import settings
from ..schemas import ICP, Lead

_APOLLO_SEARCH = "https://api.apollo.io/v1/mixed_people/search"
_APOLLO_MATCH = "https://api.apollo.io/v1/people/match"

_MOCK = [
    ("Dana Lee", "VP Sales", "Cascade GTM"),
    ("Priya Nair", "Head of Growth", "Fieldstack"),
    ("Marcus Cole", "Founder", "SideQuest"),
    ("Ana Ruiz", "RevOps Manager", "Outpost HQ"),
]


def _score(icp: ICP, title: str) -> tuple[float, float]:
    """Crude fit/intent scoring. Replace intent with real signal data later."""
    title_l = title.lower()
    fit = 0.9 if any(t.lower() in title_l for t in icp.titles) else 0.5
    intent = 0.7  # placeholder: derive from job-post / competitor-follower signals
    return fit, intent


# --------------------------------------------------------------------------- #
# Mock path
# --------------------------------------------------------------------------- #
def _mock_leads(icp: ICP, limit: int) -> list[Lead]:
    out: list[Lead] = []
    for i in range(min(limit, len(_MOCK))):
        name, title, company = _MOCK[i % len(_MOCK)]
        fit, intent = _score(icp, title)
        slug = company.lower().replace(" ", "")
        out.append(
            Lead(
                name=name,
                title=title,
                company=company,
                email=f"{name.split()[0].lower()}@{slug}.com",
                linkedin_url=f"https://linkedin.com/in/{name.split()[0].lower()}",
                fit_score=fit,
                intent_score=intent,
                source="stub",
            )
        )
    return out


# --------------------------------------------------------------------------- #
# Apollo path
# --------------------------------------------------------------------------- #
def _map_apollo(person: dict, icp: ICP) -> Lead:
    org = person.get("organization") or {}
    title = person.get("title") or ""
    fit, intent = _score(icp, title)
    return Lead(
        name=(person.get("name") or "").strip()
        or f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
        title=title,
        company=org.get("name", ""),
        # Apollo masks emails in search; this is the unmasked value when present.
        email=person.get("email"),
        linkedin_url=person.get("linkedin_url"),
        phone=(org.get("phone") or person.get("phone")),
        fit_score=fit,
        intent_score=intent,
        source="apollo",
    )


def _build_payload(icp: ICP, limit: int) -> dict:
    payload: dict = {"page": 1, "per_page": min(limit, 100)}
    if icp.titles:
        payload["person_titles"] = icp.titles
    if icp.geographies:
        payload["person_locations"] = icp.geographies
    if icp.keywords:
        payload["q_keywords"] = " ".join(icp.keywords[:10])
    # Apollo expects employee ranges like "1,10" / "11,50". Pass through if it
    # already looks range-shaped; otherwise omit and filter client-side later.
    if icp.company_size and "," in icp.company_size:
        payload["organization_num_employees_ranges"] = [icp.company_size]
    return payload


async def _apollo_leads(icp: ICP, limit: int) -> list[Lead]:
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": settings.apollo_api_key,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            _APOLLO_SEARCH, headers=headers, json=_build_payload(icp, limit)
        )
        resp.raise_for_status()
        people = resp.json().get("people", [])
    return [_map_apollo(p, icp) for p in people[:limit]]


async def _reveal_email(client: httpx.AsyncClient, person_id: str) -> str | None:
    """Optional: spend a credit to reveal a verified email. Off by default."""
    resp = await client.post(
        _APOLLO_MATCH,
        headers={"X-Api-Key": settings.apollo_api_key},
        json={"id": person_id, "reveal_personal_emails": False},
    )
    if resp.status_code == 200:
        return (resp.json().get("person") or {}).get("email")
    return None


# --------------------------------------------------------------------------- #
# Public entrypoint
# --------------------------------------------------------------------------- #
async def find_leads(icp: ICP, limit: int = 25) -> list[Lead]:
    if not settings.apollo_api_key:
        return _mock_leads(icp, limit)
    try:
        return await _apollo_leads(icp, limit)
    except httpx.HTTPError:
        # Don't hard-fail the pipeline on a vendor hiccup; fall back to mock.
        return _mock_leads(icp, limit)
