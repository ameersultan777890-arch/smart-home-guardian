# Devpost submission notes: Smart Home Guardian

**Deadline: Oct 23, 2026, 12:00 PM PT (19:00 UTC).**

## Thumbnail
Upload `thumbnail.png` (1500×1000, 3:2, under 5 MB) with "Edit thumbnail" on the Project overview page.

## Project overview
- **Project name:** Smart Home Guardian
- **Elevator pitch (max 200):** Secure your smart home by talking to Alexa. Smart Home Guardian audits connected devices, explains weak spots in plain language, fixes them by voice, and locks every entry point on command.

## Built with (tags)
Keep: alexa-skills-kit-(ask), python, flask, security-&-privacy, internet-of-things-(iot), conversational.
Add if the tag exists: mcp / model-context-protocol, cryptography, pillow.

## Edits I recommend to your written story so it matches the code exactly
- **How we built it, Backend:** say "Python (Flask) web service, deployable to AWS Lambda-style or any HTTPS host" and mention the Alexa request verification (certificate chain, signature, timestamp).
- **Security Engine:** "password-entropy scoring, firmware version comparison against a catalogue, port-risk rules, and matching against a sample threat-intelligence feed (fictional IDs, simulated)".
- **Add a line:** "The same engine is also exposed as an MCP server (6 tools), so any MCP-capable assistant can use it."
- **Keep the word "simulated" visible.** Judges respect honesty, and the rules allow simulated experiences.
- **What it does, item 1:** it says "real-time". Change to "an on-demand audit of a simulated home".
- **Roadmap "AI-Powered Anomaly Detection":** fine as a future goal; do not claim it exists.

## Demo video (under 3 minutes)
1. 0:00–0:25: Problem: smart homes have many devices and no security expert. Show the thumbnail.
2. 0:25–0:50: Architecture slide (Alexa → verified Flask endpoint → security engine; plus MCP).
3. 0:50–2:15: Alexa developer console Test tab (or `python simulate_alexa.py --inprocess` in a terminal): audit → "yes" → "fix the camera" → "lock all entry points" → summary. Narrate the score going from 10 up to 100.
4. 2:15–2:40: Show `pytest` passing and the code layout.
5. 2:40–2:55: Roadmap and call to action.

## Checklist
- [ ] Thumbnail uploaded
- [ ] Public GitHub repo with this folder, plus a LICENSE file (MIT)
- [ ] Skill deployed to a public HTTPS endpoint and tested in the Alexa console (or clearly labeled simulated path if you can't)
- [ ] Video under 3 minutes, public link
- [ ] Friction Log filled in honestly (what actually went wrong for you; up to 10% bonus)
- [ ] Press Submit and confirm the status is not "Draft"
