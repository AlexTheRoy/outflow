# Deploy to the cloud (Render)

This gets your backend running 24/7 at a real URL. The `render.yaml` blueprint
provisions the API, a Postgres database, and Redis together. Migrations run
automatically on every deploy (via `entrypoint.sh`).

Estimated time: ~20 minutes. Estimated cost: ~$7–25/mo for the starter tiers
(verify current Render pricing — it changes).

---

## What unlocks each feature

| Feature | What you must provide |
|---|---|
| Analyze + all content (research, posts, scripts, outreach copy) | `ANTHROPIC_API_KEY` (console.anthropic.com) |
| Real leads | `APOLLO_API_KEY` (paid Apollo plan) |
| Actually send email | `INSTANTLY_API_KEY` + `INSTANTLY_CAMPAIGN_ID` (or Smartlead), **plus warmed mailboxes** |
| Place real calls | `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` + `TWILIO_FROM_NUMBER` |

You can deploy with just the Anthropic key and add the rest later — each is independent.

---

## Step 1 — Put the code on GitHub

1. Create a new GitHub repo (private is fine).
2. Push the `backend/` folder so that `Dockerfile` and `render.yaml` sit at the repo root
   (or note the subfolder; you'll set "Root Directory" in Render if it's nested).

## Step 2 — Create the Render Blueprint

1. Sign up at render.com and click **New → Blueprint**.
2. Connect your GitHub repo. Render reads `render.yaml` and shows the services it will
   create (outflow-api, outflow-db, outflow-redis).
3. Click **Apply**. Postgres + Redis come up; the API builds from the Dockerfile.

## Step 3 — Set your secrets

In the **outflow-api** service → **Environment**, fill the `sync:false` values:

- `API_KEYS` — invent a long random string; clients must send it (see below). Required in production.
- `CORS_ORIGINS` — the URL where your frontend is hosted (e.g. `https://app.yourdomain.com`). No `*` in production.
- `ANTHROPIC_API_KEY` — your Claude key.
- Add `APOLLO_API_KEY`, `INSTANTLY_*`, `TWILIO_*` as you enable those features.

`DATABASE_URL` and `REDIS_URL` are wired automatically — don't set them by hand.

Save → Render redeploys. When the deploy is green, visit `https://<your-api>.onrender.com/health`.

## Step 4 — Point the frontend at it

Open `app.html` → **Settings**:

- **API base URL**: `https://<your-api>.onrender.com`
- **API key**: the `API_KEYS` value you set

The sidebar badge flips to green "live". You can host `app.html` anywhere static
(Render Static Site, Netlify, Vercel, GitHub Pages) — just make sure its URL is in
`CORS_ORIGINS`.

---

## Sending email — the part people skip

Setting `INSTANTLY_API_KEY` is not enough to land in inboxes. You must, in Instantly
(or Smartlead) first:

1. Connect sending mailboxes (dedicated domains, not your main one).
2. Configure **SPF, DKIM, DMARC** for those domains.
3. Run **warming** for 2–4 weeks before real sends.
4. Create a campaign whose sequence body references `{{subject}}` / `{{body}}` (the
   variables this app sends), and put its ID in `INSTANTLY_CAMPAIGN_ID`.

Then `/outreach/send` enrolls leads into that campaign and they send on the warmed
schedule. Skipping warming = landing in spam.

## Calls — Twilio setup

1. Buy a Twilio number → set `TWILIO_FROM_NUMBER`.
2. Set `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN`.
3. Optionally set `TWILIO_TWIML_URL` (a TwiML Bin) to control what happens on answer —
   e.g. bridge the call to your phone. Without it, the callee hears a hold message.
4. Trial Twilio accounts can only call verified numbers; upgrade for arbitrary dialing.
5. Mind TCPA / consent / call-recording laws before dialing real prospects.

The live teleprompter (real-time transcription + AI coaching during the call) is a
separate websocket/media-streaming service — not included in this deploy.

---

## Compliance reminder

Cold email (CAN-SPAM/GDPR/CASL), cold calling (TCPA/DNC), and LinkedIn automation
(ToS) all carry legal/account risk. Wire suppression + unsubscribe + DNC handling
before you run real volume.
