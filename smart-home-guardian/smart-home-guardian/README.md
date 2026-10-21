# Smart Home Guardian

Voice-first smart-home security for **Alexa+** (Amazon Developer Hackathon). Talk to Alexa to audit your connected
devices, hear weak spots explained in plain language, fix them, and lock every entry point.

> **Simulation notice:** devices and the "threat intelligence" feed are sample data (fictional IDs like `SIM-2026-001`).
> The checking logic is real (password entropy, firmware comparison, port risk, intel matching) and `Home.devices`
> is the seam where SmartThings / Hue / router APIs would plug in.

## What you can say
| Say | What happens |
|---|---|
| "Alexa, open Smart Home Guardian" | greeting and offer to audit |
| "Run a security audit" | scores 7 devices, reads the most urgent issue, offers to fix it |
| "Yes" / "Fix the camera" | rotates password, updates firmware, closes ports; new score is read back |
| "Read more issues" | next three findings (dialogue state kept in session attributes) |
| "Lock all entry points" | locks front door, back door, garage |
| "Fix everything" | secures every device |
| "Give me a summary" | score, grade, open issues, entry points locked, fixes this session |

## Architecture
```
Alexa+ ──HTTPS──> Flask /alexa ──> request verification (cert chain, signature, timestamp)
                                └─> ask-sdk-core handlers ──> security engine (guardian/engine.py)
Alexa+ ──MCP────> mcp_server.py ───────────────────────────> same security engine
```
- `guardian/engine.py`: password strength, firmware checks, port risk, threat-intel matching, scoring, fixes, audit log
- `guardian/skill.py`: Alexa intent handlers and dialogue state
- `guardian/verify.py`: Amazon's required request verification
- `mcp_server.py`: the same engine exposed as 6 MCP tools
- `skill-package/`: interaction model (`en-US.json`) and manifest (`skill.json`)

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q tests                              # 10 tests
python simulate_alexa.py --inprocess                   # simulated conversation, no server needed
GUARDIAN_SKIP_VERIFY=1 python app.py                   # local server on :5000 (skip verification for local tests ONLY)
python mcp_server.py                                   # MCP server on :8001/mcp
```

## Deploy the Alexa skill
1. Host `app.py` on any public HTTPS URL (Render, Railway, AWS App Runner/EC2, or `cloudflared tunnel --url http://localhost:5000`).
   Start command: `gunicorn app:app`. **Do not** set `GUARDIAN_SKIP_VERIFY` in production.
2. In the [Alexa developer console](https://developer.amazon.com/alexa/console/ask): Create skill → Custom → Provision your own.
3. Build → JSON Editor → paste `skill-package/interactionModels/custom/en-US.json` → Save and Build model.
4. Endpoint → HTTPS → paste `https://YOUR-HOST/alexa` → certificate type: "My development endpoint is a sub-domain that has a wildcard certificate" (or the option matching your host).
5. Optional hardening: set env `ALEXA_SKILL_ID` to your skill id so only your skill is accepted.
6. Test tab → enable testing (Development) → type or speak the phrases above.

## Honest limitations
- Device data is simulated; no real network scanning is performed.
- Request signature verification follows Amazon's documented rules, but was unit-tested only for URL and timestamp rules offline; verify it live with the Alexa console's test tab.
- Home state is in memory per Alexa user and resets on restart (the audit log can be written to disk with `GUARDIAN_LOG=audit.jsonl`).
