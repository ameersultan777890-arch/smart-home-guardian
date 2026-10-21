"""Alexa request verification (required for any HTTPS endpoint skill; skills fail certification without it).

Implements Amazon's documented checks:
  1. SignatureCertChainUrl is https://s3.amazonaws.com[:443]/echo.api/...
  2. The certificate is currently valid and lists echo-api.amazon.com in its SAN
  3. The Signature-256 header is a valid RSA-SHA256 signature of the raw request body
  4. The request timestamp is within 150 seconds of now
Set GUARDIAN_SKIP_VERIFY=1 ONLY for local testing.
"""
import base64
import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

_CERT_CACHE: dict[str, x509.Certificate] = {}


class VerificationError(Exception):
    pass


def valid_cert_url(url: str) -> bool:
    try:
        u = urlparse(url)
    except ValueError:
        return False
    return (u.scheme.lower() == "https" and (u.hostname or "").lower() == "s3.amazonaws.com"
            and u.path.startswith("/echo.api/") and ".." not in u.path and u.port in (None, 443))


def fresh_timestamp(ts: str, tolerance: int = 150) -> bool:
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return False
    return abs(time.time() - t.timestamp()) <= tolerance


def _load_cert(url: str) -> x509.Certificate:
    if url in _CERT_CACHE:
        return _CERT_CACHE[url]
    pem = requests.get(url, timeout=5).content
    cert = x509.load_pem_x509_certificate(pem)
    _CERT_CACHE[url] = cert
    return cert


def verify_request(headers, raw_body: bytes) -> None:
    if os.environ.get("GUARDIAN_SKIP_VERIFY") == "1":
        return
    url = headers.get("SignatureCertChainUrl", "")
    if not valid_cert_url(url):
        raise VerificationError("bad certificate URL")
    cert = _load_cert(url)
    now = datetime.now(timezone.utc)
    if not (cert.not_valid_before_utc <= now <= cert.not_valid_after_utc):
        raise VerificationError("certificate expired")
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    if "echo-api.amazon.com" not in san.get_values_for_type(x509.DNSName):
        raise VerificationError("certificate SAN mismatch")
    sig_b64 = headers.get("Signature-256")
    algo = hashes.SHA256()
    if not sig_b64:
        sig_b64, algo = headers.get("Signature", ""), hashes.SHA1()
    try:
        cert.public_key().verify(base64.b64decode(sig_b64), raw_body, padding.PKCS1v15(), algo)
    except Exception as e:
        raise VerificationError("signature mismatch") from e
    ts = json.loads(raw_body).get("request", {}).get("timestamp", "")
    if not fresh_timestamp(ts):
        raise VerificationError("stale timestamp")
