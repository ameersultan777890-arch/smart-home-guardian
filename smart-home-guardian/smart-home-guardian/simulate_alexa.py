"""Simulated Alexa conversation: sends real Alexa-format JSON requests to the Flask app and prints what Alexa would say.
Run the server first:  GUARDIAN_SKIP_VERIFY=1 python app.py      then:  python simulate_alexa.py [url]
(Or run with --inprocess to use Flask's test client with no server.)"""
import json, os, re, sys, uuid
from datetime import datetime, timezone

URL = next((a for a in sys.argv[1:] if a.startswith("http")), "http://localhost:5000/alexa")
INPROC = "--inprocess" in sys.argv
APP_ID, USER, SESSION = "amzn1.ask.skill.demo", "amzn1.ask.account.DEMO", "amzn1.echo-api.session." + uuid.uuid4().hex
attrs: dict = {}


def envelope(req):
    return {"version": "1.0",
            "session": {"new": not attrs, "sessionId": SESSION, "application": {"applicationId": APP_ID},
                        "attributes": attrs, "user": {"userId": USER}},
            "context": {"System": {"application": {"applicationId": APP_ID}, "user": {"userId": USER},
                                   "device": {"deviceId": "dev1", "supportedInterfaces": {}}}},
            "request": {"requestId": "amzn1.echo-api.request." + uuid.uuid4().hex,
                        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "locale": "en-US", **req}}


def intent(name, **slots):
    return {"type": "IntentRequest", "intent": {"name": name, "confirmationStatus": "NONE",
            "slots": {k: {"name": k, "value": v, "confirmationStatus": "NONE"} for k, v in slots.items()}}}


if INPROC:
    os.environ["GUARDIAN_SKIP_VERIFY"] = "1"
    from app import app as flask_app
    client = flask_app.test_client()
    def post(body): return client.post("/alexa", json=body).get_json()
else:
    import requests
    def post(body): return requests.post(URL, json=body, timeout=10).json()

SCRIPT = [
    ("Alexa, open Smart Home Guardian", {"type": "LaunchRequest"}),
    ("run a security audit", intent("RunAuditIntent")),
    ("yes", intent("AMAZON.YesIntent")),
    ("fix the camera", intent("FixDeviceIntent", device="camera")),
    ("lock all entry points", intent("LockAllIntent")),
    ("fix everything", intent("FixAllIntent")),
    ("give me a summary", intent("SummaryIntent")),
]

for said, req in SCRIPT:
    out = post(envelope(req))
    attrs = out.get("sessionAttributes", {}) or {}
    sp = out["response"].get("outputSpeech") or {}
    speech = sp.get("text") or re.sub(r"</?speak>", "", sp.get("ssml", "")) or "(no speech)"
    print(f"YOU    : {said}\nALEXA  : {speech}\n")
