"""Step 1a — fetch a website and reduce it to clean, useful text.

This works on static and server-rendered sites. For heavily JS-rendered SPAs you
would swap httpx for Playwright or a scraping API (Firecrawl/ScrapingBee) — the
return shape stays the same so nothing downstream changes.
"""
from __future__ import annotations

import httpx
from selectolax.parser import HTMLParser

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OutflowBot/0.1; +https://example.com/bot)"
}
_DROP_TAGS = ("script", "style", "noscript", "svg", "nav", "footer", "header", "form")


class ScrapeResult(dict):
    """dict with keys: url, title, description, headings, text."""


async def scrape(url: str, timeout: float = 15.0) -> ScrapeResult:
    async with httpx.AsyncClient(
        follow_redirects=True, headers=_HEADERS, timeout=timeout
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    tree = HTMLParser(html)

    title = tree.css_first("title")
    title = title.text(strip=True) if title else ""

    desc = ""
    meta = tree.css_first('meta[name="description"]') or tree.css_first(
        'meta[property="og:description"]'
    )
    if meta:
        desc = meta.attributes.get("content", "") or ""

    headings = [
        h.text(strip=True)
        for sel in ("h1", "h2")
        for h in tree.css(sel)
        if h.text(strip=True)
    ][:25]

    for node in tree.css(",".join(_DROP_TAGS)):
        node.decompose()
    body = tree.body or tree
    text = " ".join(body.text(separator=" ", strip=True).split())
    text = text[:8000]  # cap tokens sent to the LLM

    return ScrapeResult(
        url=url, title=title, description=desc, headings=headings, text=text
    )
