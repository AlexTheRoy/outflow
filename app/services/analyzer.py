"""Step 1b — turn scraped text into a structured CampaignProfile (product, value
prop, pricing, ICP).

Two paths:
  * LLM path  — used when OPENAI_API_KEY is set. Asks for strict JSON.
  * Heuristic — zero-dependency fallback so the endpoint always returns something
                useful in the demo without any API keys.
"""
from __future__ import annotations

import re

from ..schemas import CampaignProfile, ICP
from . import llm
from .scraper import ScrapeResult

_PRICE_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?(?:\s?/\s?\w+)?")
_TITLE_HINTS = [
    "founder", "ceo", "cto", "vp sales", "head of sales", "sales", "marketing",
    "revops", "growth", "recruiter", "engineer", "product", "operations",
]


def _heuristic(scr: ScrapeResult) -> CampaignProfile:
    text = scr["text"]
    lowered = text.lower()

    product = scr["title"] or (scr["headings"][0] if scr["headings"] else scr["url"])
    value_prop = scr["description"] or (
        scr["headings"][1] if len(scr["headings"]) > 1 else text[:160]
    )
    prices = _PRICE_RE.findall(text)
    pricing = ", ".join(dict.fromkeys(prices[:6])) if prices else "not detected"

    keywords = [
        w for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{4,}", lowered)
    ]
    # crude keyword frequency
    freq: dict[str, int] = {}
    for w in keywords:
        freq[w] = freq.get(w, 0) + 1
    stop = {"about", "their", "these", "which", "there", "other", "using", "needs"}
    top = [
        w for w, _ in sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
        if w not in stop
    ][:8]

    guessed_titles = [t for t in _TITLE_HINTS if t in lowered][:6] or ["Founder", "VP Sales"]

    return CampaignProfile(
        url=scr["url"],
        product=product[:140],
        value_prop=value_prop[:240],
        pricing=pricing,
        icp=ICP(
            titles=[t.title() for t in guessed_titles],
            industries=["(infer from keywords)"],
            company_size="11-200",
            geographies=["United States"],
            keywords=top,
        ),
        source="heuristic",
    )


def _llm(scr: ScrapeResult) -> CampaignProfile | None:
    prompt = (
        "You are a GTM analyst. From this website content, return JSON with keys: "
        "product, value_prop, pricing, icp. icp is an object with keys "
        "titles[], industries[], company_size, geographies[], keywords[]. "
        "Infer the ideal customer profile of who would BUY this product.\n\n"
        f"URL: {scr['url']}\nTITLE: {scr['title']}\n"
        f"DESCRIPTION: {scr['description']}\n"
        f"HEADINGS: {scr['headings']}\n\nCONTENT:\n{scr['text']}"
    )
    data = llm.complete_json(prompt, temperature=0.2)
    if not data:
        return None
    icp = data.get("icp", {}) or {}
    return CampaignProfile(
        url=scr["url"],
        product=data.get("product", ""),
        value_prop=data.get("value_prop", ""),
        pricing=str(data.get("pricing", "")),
        icp=ICP(
            titles=icp.get("titles", []),
            industries=icp.get("industries", []),
            company_size=str(icp.get("company_size", "")),
            geographies=icp.get("geographies", []),
            keywords=icp.get("keywords", []),
        ),
        source="llm",
    )


def analyze(scr: ScrapeResult) -> CampaignProfile:
    if llm.enabled():
        result = _llm(scr)
        if result is not None:
            return result
    # Never fail the request just because the LLM is off or hiccuped.
    return _heuristic(scr)
