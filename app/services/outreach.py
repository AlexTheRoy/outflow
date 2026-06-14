"""Step 3 — generate + (eventually) send outreach.

Copy generation uses the unified LLM layer (Claude or OpenAI) when a key is set,
with a templated fallback otherwise. Sending is a stub: in production you hand the
message to Instantly/Smartlead (email) or a per-account LinkedIn runner, and record
provider message IDs + webhook events.
"""
from __future__ import annotations

import logging

import httpx

from ..config import settings
from ..schemas import CampaignProfile, Lead, OutreachMessage, SendResult
from . import llm

logger = logging.getLogger("outflow")


def _template(profile: CampaignProfile, lead: Lead, channel: str) -> OutreachMessage:
    first = lead.name.split()[0]
    hook = profile.value_prop or profile.product
    if channel == "linkedin":
        body = (
            f"Hi {first} — saw you lead {lead.title.lower()} at {lead.company}. "
            f"We help teams like yours with {hook[:80]}. Worth a quick chat?"
        )
        return OutreachMessage(channel="linkedin", body=body, status="draft")
    body = (
        f"Hi {first},\n\nNoticed {lead.company} is scaling its {lead.title.lower()} "
        f"function. {hook[:120]}\n\nWorth 15 minutes this week?\n\nBest,\nYour Name"
    )
    return OutreachMessage(
        channel="email",
        subject=f"{lead.company} + {profile.product[:40]}",
        body=body,
        status="draft",
    )


def _llm(profile: CampaignProfile, lead: Lead, channel: str) -> OutreachMessage | None:
    prompt = (
        f"Write a short, non-spammy {channel} outreach message.\n"
        f"Our product: {profile.product} — {profile.value_prop}\n"
        f"Recipient: {lead.name}, {lead.title} at {lead.company}.\n"
        "Be specific, under 90 words, one clear CTA. "
        + (
            'Return JSON {"subject": "...", "body": "..."}.'
            if channel == "email"
            else 'Return JSON {"body": "..."}.'
        )
    )
    data = llm.complete_json(prompt, temperature=0.7)
    if not data:
        return None
    return OutreachMessage(
        channel=channel,
        subject=data.get("subject"),
        body=data.get("body", ""),
        status="draft",
    )


def generate(profile: CampaignProfile, lead: Lead, channel: str) -> OutreachMessage:
    if llm.enabled():
        result = _llm(profile, lead, channel)
        if result is not None and result.body:
            return result
    return _template(profile, lead, channel)


async def send(lead: Lead, message: OutreachMessage) -> SendResult:
    """Send an email by enrolling the lead into a configured sending campaign.

    Email providers (Instantly/Smartlead) send on a warmed schedule rather than
    one-off, so "send" = add the lead (with the generated copy as variables) to the
    campaign you configured. The campaign's sequence template should reference those
    variables ({{subject}}, {{body}} / custom fields).

    LinkedIn sending is intentionally not automated here (ToS/ban risk) — generate
    the copy and send it from your own account, or plug in a per-account runner.
    """
    if message.channel == "linkedin":
        return SendResult(
            status="not_sent",
            provider="none",
            detail="LinkedIn auto-send is disabled (ToS risk). Copy generated for manual send.",
        )
    if not lead.email:
        return SendResult(status="error", detail="Lead has no email address.")

    provider = settings.email_provider
    try:
        if provider == "instantly":
            return await _send_instantly(lead, message)
        if provider == "smartlead":
            return await _send_smartlead(lead, message)
    except httpx.HTTPError as e:
        logger.warning("send failed via %s: %s", provider, e)
        return SendResult(status="error", provider=provider, detail=str(e))

    return SendResult(
        status="not_sent",
        provider="none",
        detail="No sending provider configured. Set INSTANTLY_API_KEY or SMARTLEAD_API_KEY.",
    )


async def _send_instantly(lead: Lead, message: OutreachMessage) -> SendResult:
    """Instantly v2 — add a lead to a campaign with personalization variables.
    Docs: https://developer.instantly.ai (Leads / Add lead to campaign)."""
    if not settings.instantly_campaign_id:
        return SendResult(status="error", provider="instantly", detail="INSTANTLY_CAMPAIGN_ID not set.")
    first, _, last = (lead.name or "").partition(" ")
    payload = {
        "campaign": settings.instantly_campaign_id,
        "email": lead.email,
        "first_name": first,
        "last_name": last,
        "company_name": lead.company,
        "personalization": message.body,
        "custom_variables": {
            "subject": message.subject or "",
            "body": message.body,
            "title": lead.title,
        },
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.instantly.ai/api/v2/leads",
            headers={"Authorization": f"Bearer {settings.instantly_api_key}"},
            json=payload,
        )
        r.raise_for_status()
        data = r.json() if r.content else {}
    return SendResult(
        status="queued",
        provider="instantly",
        detail="Lead enrolled in Instantly campaign; will send on the warmed schedule.",
        provider_id=str(data.get("id", "")),
    )


async def _send_smartlead(lead: Lead, message: OutreachMessage) -> SendResult:
    """Smartlead — add a lead to a campaign.
    Docs: https://api.smartlead.ai (Add leads to a campaign)."""
    if not settings.smartlead_campaign_id:
        return SendResult(status="error", provider="smartlead", detail="SMARTLEAD_CAMPAIGN_ID not set.")
    first, _, last = (lead.name or "").partition(" ")
    url = (
        f"https://server.smartlead.ai/api/v1/campaigns/{settings.smartlead_campaign_id}"
        f"/leads?api_key={settings.smartlead_api_key}"
    )
    payload = {
        "lead_list": [
            {
                "email": lead.email,
                "first_name": first,
                "last_name": last,
                "company_name": lead.company,
                "custom_fields": {
                    "subject": message.subject or "",
                    "body": message.body,
                    "title": lead.title,
                },
            }
        ]
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
    return SendResult(
        status="queued",
        provider="smartlead",
        detail="Lead added to Smartlead campaign; will send on the warmed schedule.",
    )
