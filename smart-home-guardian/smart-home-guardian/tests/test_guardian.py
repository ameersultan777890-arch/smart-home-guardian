import json, os, time
os.environ["GUARDIAN_SKIP_VERIFY"] = "0"
import pytest
from guardian.engine import Home, password_strength, version_tuple
from guardian.verify import valid_cert_url, fresh_timestamp, verify_request, VerificationError


def test_password_strength():
    assert password_strength("admin")[0] == "weak"
    assert password_strength("1234")[0] == "weak"
    assert password_strength("Tr1cky-Gr@pe-Lamp-88")[0] == "strong"


def test_version_compare():
    assert version_tuple("2.10.0") > version_tuple("2.9.9")


def test_audit_finds_and_fix_improves_score():
    h = Home()
    before = h.score(h.audit())
    h.apply_fix("living_cam")
    assert h.score(h.audit()) > before
    assert not any(f.device_id == "living_cam" for f in h.audit())


def test_lock_all_is_idempotent():
    h = Home()
    assert len(h.lock_all_entry_points()["newly_locked"]) == 3
    assert h.lock_all_entry_points()["newly_locked"] == []


def test_find_device_fuzzy():
    h = Home()
    assert h.find_device("the camera")["id"] == "living_cam"
    assert h.find_device("front lock")["id"] == "front_door"
    assert h.find_device("toaster") is None


def test_clean_home_has_no_findings():
    h = Home()
    h.fix_all()
    assert h.audit() == []
    assert h.score([]) == 100


def test_cert_url_rules():
    assert valid_cert_url("https://s3.amazonaws.com/echo.api/echo-api-cert.pem")
    assert valid_cert_url("https://s3.amazonaws.com:443/echo.api/x.pem")
    assert not valid_cert_url("http://s3.amazonaws.com/echo.api/x.pem")
    assert not valid_cert_url("https://s3.amazonaws.com.evil.com/echo.api/x.pem")
    assert not valid_cert_url("https://s3.amazonaws.com/EcHo.api/x.pem")
    assert not valid_cert_url("https://s3.amazonaws.com:8443/echo.api/x.pem")


def test_timestamp_window():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    assert fresh_timestamp(now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    assert not fresh_timestamp((now - timedelta(seconds=400)).strftime("%Y-%m-%dT%H:%M:%SZ"))


def test_unverified_request_rejected():
    with pytest.raises(VerificationError):
        verify_request({}, b"{}")


def test_endpoint_rejects_unsigned():
    from app import app
    r = app.test_client().post("/alexa", data="{}", content_type="application/json")
    assert r.status_code == 400
