"""Content generators: per-lead research reports, social/blog posts, and call
scripts. Each uses the unified LLM layer (Claude/OpenAI) when a key is set and
falls back to a sensible template otherwise, so the app always returns something.
"""
from __future__ import annotations

from ..schemas import (
    CallScript,
    CampaignProfile,
    Lead,
    ResearchReport,
    SocialPost,
)
from . import llm


# --------------------------------------------------------------------------- #
# Research report
# --------------------------------------------------------------------------- #
def research(lead: Lead, profile: CampaignProfile | None) -> ResearchReport:
    prod = profile.product if profile else "our product"
    if llm.enabled():
        prompt = (
            f"Produce concise sales research on a prospect.\n"
            f"Prospect: {lead.name}, {lead.title} at {lead.company}.\n"
            f"We sell: {prod}"
            + (f" — {profile.value_prop}" if profile else "")
            + "\nReturn JSON with keys: company, summary (2-3 sentences), "
            "pain_points (3 bullet strings), why_now (1 sentence), "
            "talking_points (3 bullet strings)."
        )
        data = llm.complete_json(prompt, temperature=0.4)
        if data:
            return ResearchReport(
                company=data.get("company", lead.company),
                summary=data.get("summary", ""),
                pain_points=data.get("pain_points", []) or [],
                why_now=data.get("why_now", ""),
                talking_points=data.get("talking_points", []) or [],
                source="llm",
            )
    return ResearchReport(
        company=lead.company,
        summary=(
            f"{lead.company} is a company where {lead.name} leads "
            f"{lead.title.lower()}. Likely evaluating tools to scale that function."
        ),
        pain_points=[
            "Manual, time-consuming prospecting",
            "Inconsistent outreach across channels",
            "Limited visibility into buying signals",
        ],
        why_now=f"{lead.title} hiring and growth suggest active investment in the function.",
        talking_points=[
            f"How {lead.company} currently sources pipeline",
            f"Where {prod} removes manual work",
            "Quantify time saved per rep per week",
        ],
        source="template",
    )


# --------------------------------------------------------------------------- #
# Social / blog post
# --------------------------------------------------------------------------- #
def social_post(profile: CampaignProfile, platform: str, topic: str | None, tone: str) -> SocialPost:
    subject = topic or profile.value_prop or profile.product
    if llm.enabled():
        prompt = (
            f"Write a {tone} {platform} post for the product below.\n"
            f"Product: {profile.product} — {profile.value_prop}\n"
            f"Topic/angle: {subject}\n"
            + (
                "Make it a 120-200 word post with a strong hook. "
                if platform != "blog"
                else "Make it a short blog section (~250 words) with a title. "
            )
            + 'Return JSON with keys: title, body, hashtags (array of 3-5 strings without the # symbol).'
        )
        data = llm.complete_json(prompt, temperature=0.8)
        if data and data.get("body"):
            return SocialPost(
                platform=platform,
                title=data.get("title"),
                body=data.get("body", ""),
                hashtags=data.get("hashtags", []) or [],
                source="llm",
            )
    return SocialPost(
        platform=platform,
        title=f"{profile.product}: stop guessing who to sell to",
        body=(
            f"Most teams burn hours hunting for buyers. {profile.product} flips that: "
            f"{subject}. Paste your site, get a target list, and reach people across "
            "email, LinkedIn, and phone — automatically. What would your team do with "
            "the hours back?"
        ),
        hashtags=["sales", "gtm", "outbound", "ai"],
        source="template",
    )


# --------------------------------------------------------------------------- #
# Call script
# --------------------------------------------------------------------------- #
def call_script(lead: Lead, profile: CampaignProfile | None) -> CallScript:
    prod = profile.product if profile else "our product"
    if llm.enabled():
        prompt = (
            f"Write a cold-call script for calling {lead.name}, {lead.title} at "
            f"{lead.company}, selling {prod}"
            + (f" ({profile.value_prop})" if profile else "")
            + ".\nReturn JSON with keys: opener (1-2 sentences), discovery_questions "
            "(3 strings), value_pitch (2 sentences), objection_handling (3 strings "
            "formatted 'Objection -> response'), close (1 sentence)."
        )
        data = llm.complete_json(prompt, temperature=0.6)
        if data:
            return CallScript(
                opener=data.get("opener", ""),
                discovery_questions=data.get("discovery_questions", []) or [],
                value_pitch=data.get("value_pitch", ""),
                objection_handling=data.get("objection_handling", []) or [],
                close=data.get("close", ""),
                source="llm",
            )
    first = lead.name.split()[0]
    return CallScript(
        opener=f"Hi {first}, it's [name] — I'll be quick. I work with {lead.title.lower()}s on outbound and had one idea for {lead.company}.",
        discovery_questions=[
            "How are you generating pipeline today?",
            "What's the biggest bottleneck in your outbound?",
            "If you could automate one part, what would it be?",
        ],
        value_pitch=f"{prod} finds companies that need you and reaches them across email, LinkedIn, and phone. Most teams see live conversations in week one.",
        objection_handling=[
            "We already have a tool -> Happy to benchmark against it; takes 10 minutes.",
            "No budget -> Starts at $99/mo with a free trial, no commitment.",
            "Send me an email -> Of course — what's the best address, and can I grab 15 min next week?",
        ],
        close=f"Worth a 15-minute look later this week, {first}?",
        source="template",
    )
