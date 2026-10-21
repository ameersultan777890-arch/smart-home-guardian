"""Flask web service: Alexa endpoint + health check.  Run: python app.py  (or gunicorn app:app)"""
import json
import os

from flask import Flask, request, jsonify
from ask_sdk_model import RequestEnvelope
from ask_sdk_core.serialize import DefaultSerializer

from guardian.skill import skill
from guardian.verify import verify_request, VerificationError

app = Flask(__name__)
ser = DefaultSerializer()


@app.get("/health")
def health():
    return jsonify(ok=True, service="smart-home-guardian")


@app.post("/alexa")
def alexa():
    raw = request.get_data()
    try:
        verify_request(request.headers, raw)
    except VerificationError as e:
        return jsonify(error=str(e)), 400
    envelope = ser.deserialize(raw.decode("utf-8"), RequestEnvelope)
    expected = os.environ.get("ALEXA_SKILL_ID")  # set this once you have your skill id
    if expected and envelope.session and envelope.session.application.application_id != expected:
        return jsonify(error="wrong skill id"), 403
    response = skill.invoke(request_envelope=envelope, context=None)
    return jsonify(ser.serialize(response))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
