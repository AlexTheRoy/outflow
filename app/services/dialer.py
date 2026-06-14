"""Step 4 — AI dialer.

What works now: placing a REAL outbound call via Twilio when credentials are set.
Twilio dials the lead and, on answer, fetches your TwiML URL to control the call
(e.g. bridge to the rep's phone/softphone, or play a message).

What's still a follow-up: the live, real-time teleprompter. That needs a stateful
media stream (Twilio Media Streams over websocket) piped to a realtime STT
(Deepgram) and an LLM, pushing suggestions to the UI over a websocket — a separate
service from this request/response API. See ARCHITECTURE.md.

With no credentials, returns a simulated response so the app stays usable.
"""
from __future__ import annotations

import logging
import uuid

from ..config import settings
from ..schemas import DialResponse, Lead

logger = logging.getLogger("outflow")


def _ready() -> bool:
    return bool(
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from_number
    )


async def dial(lead: Lead) -> DialResponse:
    if not _ready():
        return DialResponse(
            call_id=str(uuid.uuid4()),
            status="simulated",
            note=(
                "No Twilio credentials/number set. In production this places a real "
                f"call to {lead.phone or 'the lead'} and (next phase) streams a live "
                "teleprompter."
            ),
        )
    if not lead.phone:
        return DialResponse(
            call_id=str(uuid.uuid4()),
            status="error",
            note="Lead has no phone number to dial.",
        )

    try:
        from twilio.rest import Client  # lazy import; optional dependency

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        # If you have a TwiML URL, Twilio fetches it on answer to control the call.
        # Otherwise we fall back to a minimal spoken message so the call still works.
        twiml_url = settings.twilio_twiml_url
        kwargs = {"to": lead.phone, "from_": settings.twilio_from_number}
        if twiml_url:
            kwargs["url"] = twiml_url
        else:
            kwargs["twiml"] = (
                "<Response><Say>Connecting you now. Please hold.</Say></Response>"
            )
        call = client.calls.create(**kwargs)
        return DialResponse(
            call_id=call.sid,
            status=call.status or "queued",
            note=f"Calling {lead.name} at {lead.phone} via Twilio.",
        )
    except Exception as e:
        logger.warning("twilio dial failed: %s", e, exc_info=True)
        return DialResponse(
            call_id=str(uuid.uuid4()),
            status="error",
            note=f"Twilio call failed: {e}",
        )
