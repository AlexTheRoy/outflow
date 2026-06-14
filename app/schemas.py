"""Pydantic request/response models shared across routers."""
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


# ---- Step 1: analyze ----
class AnalyzeRequest(BaseModel):
    url: HttpUrl


class ICP(BaseModel):
    titles: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    company_size: str = ""
    geographies: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class CampaignProfile(BaseModel):
    url: str
    product: str = ""
    value_prop: str = ""
    pricing: str = ""
    icp: ICP = Field(default_factory=ICP)
    source: str = "heuristic"  # "llm" when OPENAI_API_KEY is set
    campaign_id: Optional[str] = None  # set when the result was persisted


# ---- Step 2: leads ----
class FindLeadsRequest(BaseModel):
    icp: ICP
    limit: int = 25


class Lead(BaseModel):
    name: str
    title: str
    company: str
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    fit_score: float = 0.0
    intent_score: float = 0.0
    source: str = "stub"


# ---- Step 3: outreach ----
class GenerateOutreachRequest(BaseModel):
    profile: CampaignProfile
    lead: Lead
    channel: str = "email"  # email | linkedin


class OutreachMessage(BaseModel):
    channel: str
    subject: Optional[str] = None
    body: str
    status: str = "draft"


class SendOutreachRequest(BaseModel):
    lead: "Lead"
    message: OutreachMessage


class SendResult(BaseModel):
    status: str  # sent | queued | not_sent | error
    provider: str = "none"
    detail: str = ""
    provider_id: Optional[str] = None


# ---- Content generation ----
class ResearchRequest(BaseModel):
    lead: "Lead"
    profile: Optional["CampaignProfile"] = None


class ResearchReport(BaseModel):
    company: str
    summary: str
    pain_points: list[str] = Field(default_factory=list)
    why_now: str = ""
    talking_points: list[str] = Field(default_factory=list)
    source: str = "template"


class SocialPostRequest(BaseModel):
    profile: "CampaignProfile"
    platform: str = "linkedin"  # linkedin | blog | twitter
    topic: Optional[str] = None
    tone: str = "professional"


class SocialPost(BaseModel):
    platform: str
    title: Optional[str] = None
    body: str
    hashtags: list[str] = Field(default_factory=list)
    source: str = "template"


class CallScriptRequest(BaseModel):
    lead: "Lead"
    profile: Optional["CampaignProfile"] = None


class CallScript(BaseModel):
    opener: str
    discovery_questions: list[str] = Field(default_factory=list)
    value_pitch: str = ""
    objection_handling: list[str] = Field(default_factory=list)
    close: str = ""
    source: str = "template"


# ---- Step 4: dialer ----
class DialRequest(BaseModel):
    lead: Lead


class DialResponse(BaseModel):
    call_id: str
    status: str
    note: str
