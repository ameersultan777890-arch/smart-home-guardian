"""
Smart Home Guardian: security engine.

IMPORTANT: this is a SIMULATION. It audits a virtual smart home (see DEFAULT_HOME) with real
checking logic (password strength, firmware comparison, port risk, threat-intel matching), but
the devices and the "threat intelligence" feed are sample data, not live network scans.
The Home class is the integration seam: replace `Home.devices` with data from SmartThings,
Hue, or a router API to audit a real network.
"""
from __future__ import annotations

import copy
import json
import math
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

# ----------------------------------------------------------------- sample data
DEFAULT_HOME = [
    {"id": "front_door", "name": "front door lock", "type": "lock", "entry_point": True, "locked": False,
     "firmware": "2.1.0", "password": "1234", "open_ports": []},
    {"id": "back_door", "name": "back door lock", "type": "lock", "entry_point": True, "locked": False,
     "firmware": "2.4.0", "password": "Tr1cky-Gr@pe-Lamp-88", "open_ports": []},
    {"id": "garage", "name": "garage door", "type": "garage", "entry_point": True, "locked": False,
     "firmware": "1.0.2", "password": "garage", "open_ports": [80]},
    {"id": "living_cam", "name": "living room camera", "type": "camera", "entry_point": False, "locked": None,
     "firmware": "4.2.1", "password": "admin", "open_ports": [554, 23]},
    {"id": "router", "name": "router", "type": "router", "entry_point": False, "locked": None,
     "firmware": "7.3.0", "password": "admin", "open_ports": [80, 8080]},
    {"id": "thermostat", "name": "thermostat", "type": "thermostat", "entry_point": False, "locked": None,
     "firmware": "3.0.5", "password": "Kettle#Cloud#Seven#41", "open_ports": []},
    {"id": "motion", "name": "motion sensor", "type": "sensor", "entry_point": False, "locked": None,
     "firmware": "1.2.0", "password": "Sunny-Delta-Echo-515", "open_ports": []},
]

# Latest known-good firmware per device type (sample catalogue).
LATEST_FIRMWARE = {"lock": "2.4.0", "garage": "1.3.0", "camera": "5.0.0",
                   "router": "8.1.2", "thermostat": "3.0.5", "sensor": "1.2.0"}

# Sample "threat intelligence": firmware versions flagged as vulnerable. IDs are fictional.
THREAT_INTEL = [
    {"id": "SIM-2026-001", "type": "lock", "max_version": "2.2.9",
     "summary": "lock accepts replayed unlock commands"},
    {"id": "SIM-2026-002", "type": "camera", "max_version": "4.9.9",
     "summary": "camera stream can be viewed without logging in"},
    {"id": "SIM-2026-003", "type": "router", "max_version": "7.9.9",
     "summary": "router admin page vulnerable to remote takeover"},
]

COMMON_PASSWORDS = {"admin", "password", "1234", "12345", "123456", "0000", "root", "guest",
                    "default", "garage", "qwerty", "letmein", "welcome"}

PORT_RISK = {  # port -> (severity, plain-English description)
    23: ("critical", "the unencrypted telnet port is open"),
    21: ("high", "the file transfer port is open"),
    554: ("high", "the video stream port is open to the network"),
    80: ("medium", "the admin page is served without encryption"),
    8080: ("medium", "an alternate unencrypted admin port is open"),
}

SEVERITY_WEIGHT = {"critical": 8, "high": 5, "medium": 3, "low": 1}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ------------------------------------------------------------------ primitives
def version_tuple(v: str) -> tuple:
    return tuple(int(p) for p in re.findall(r"\d+", v))


def password_strength(pw: str) -> tuple[str, float]:
    """Return ('weak'|'fair'|'strong', estimated entropy bits)."""
    if not pw or pw.lower() in COMMON_PASSWORDS:
        return "weak", 0.0
    pool = 0
    pool += 26 if re.search(r"[a-z]", pw) else 0
    pool += 26 if re.search(r"[A-Z]", pw) else 0
    pool += 10 if re.search(r"\d", pw) else 0
    pool += 32 if re.search(r"[^A-Za-z0-9]", pw) else 0
    bits = len(pw) * math.log2(pool) if pool else 0.0
    if len(set(pw)) <= 2:
        bits /= 4
    return ("weak" if bits < 40 else "fair" if bits < 60 else "strong"), round(bits, 1)


@dataclass
class Finding:
    device_id: str
    device_name: str
    kind: str          # weak_password | outdated_firmware | open_port | known_vulnerability
    severity: str
    spoken: str        # one voice-friendly sentence
    fix: str           # what the fix will do
    detail: dict = field(default_factory=dict)


# ------------------------------------------------------------------------ home
class Home:
    """Holds device state, runs audits, applies fixes, keeps an audit log."""

    def __init__(self, devices=None, log_path: str | None = None):
        self.devices = copy.deepcopy(devices or DEFAULT_HOME)
        self.log_path = log_path
        self.log: list[dict] = []
        self.last_findings: list[Finding] = []
        self._lock = threading.RLock()

    # -- logging
    def _log(self, event: str, **data):
        entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": event, **data}
        self.log.append(entry)
        if self.log_path:
            try:
                with open(self.log_path, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except OSError:
                pass

    # -- lookup
    def find_device(self, text: str):
        """Fuzzy-match spoken device names ('the camera', 'front lock', 'router')."""
        t = re.sub(r"\b(the|my|a)\b", "", (text or "").lower()).strip()
        if not t:
            return None
        for d in self.devices:
            if t == d["name"] or t == d["id"].replace("_", " "):
                return d
        words = set(t.split())
        best, score = None, 0
        for d in self.devices:
            dw = set(d["name"].split()) | {d["type"]}
            s = len(words & dw)
            if s > score:
                best, score = d, s
        return best if score else None

    # -- audit
    def audit(self) -> list[Finding]:
        with self._lock:
            findings: list[Finding] = []
            for d in self.devices:
                name = d["name"]
                strength, _ = password_strength(d["password"])
                if strength == "weak":
                    findings.append(Finding(d["id"], name, "weak_password", "critical",
                        f"The {name} is using a default or weak password.",
                        "set a new strong password"))
                elif strength == "fair":
                    findings.append(Finding(d["id"], name, "weak_password", "low",
                        f"The {name} password could be stronger.", "set a new strong password"))
                latest = LATEST_FIRMWARE.get(d["type"])
                if latest and version_tuple(d["firmware"]) < version_tuple(latest):
                    findings.append(Finding(d["id"], name, "outdated_firmware", "medium",
                        f"The {name} firmware is out of date.", f"update firmware to {latest}",
                        {"current": d["firmware"], "latest": latest}))
                for port in d["open_ports"]:
                    sev, why = PORT_RISK.get(port, ("low", "an unneeded port is open"))
                    findings.append(Finding(d["id"], name, "open_port", sev,
                        f"On the {name}, {why}.", f"close port {port}", {"port": port}))
                for t in THREAT_INTEL:
                    if t["type"] == d["type"] and version_tuple(d["firmware"]) <= version_tuple(t["max_version"]):
                        findings.append(Finding(d["id"], name, "known_vulnerability", "critical",
                            f"Threat intelligence matched the {name}: {t['summary']}.",
                            f"update firmware to {LATEST_FIRMWARE[d['type']]}", {"intel_id": t["id"]}))
            findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.device_name))
            self.last_findings = findings
            self._log("audit", devices=len(self.devices), findings=len(findings), score=self.score(findings))
            return findings

    @staticmethod
    def score(findings: list[Finding]) -> int:
        return max(0, 100 - sum(SEVERITY_WEIGHT[f.severity] for f in findings))

    @staticmethod
    def grade(score: int) -> str:
        return "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 55 else "D" if score >= 35 else "F"

    # -- fixes ("secure overrides")
    def apply_fix(self, device_id: str) -> dict:
        with self._lock:
            d = next((x for x in self.devices if x["id"] == device_id), None)
            if not d:
                return {"ok": False, "actions": []}
            actions = []
            if password_strength(d["password"])[0] != "strong":
                d["password"] = "Gd!" + os.urandom(9).hex() + "Zq"  # simulated rotation; never spoken aloud
                actions.append("changed the password")
            latest = LATEST_FIRMWARE.get(d["type"])
            if latest and version_tuple(d["firmware"]) < version_tuple(latest):
                d["firmware"] = latest
                actions.append(f"updated the firmware to {latest}")
            if d["open_ports"]:
                n = len(d["open_ports"])
                actions.append(f"closed {n} open port{'s' if n != 1 else ''}")
                d["open_ports"] = []
            if actions:
                self._log("fix", device=d["id"], actions=actions)
            return {"ok": True, "device": d["name"], "actions": actions}

    def fix_all(self) -> dict:
        with self._lock:
            done = [r for r in (self.apply_fix(d["id"]) for d in self.devices) if r.get("actions")]
            return {"fixed_devices": len(done)}

    def lock_all_entry_points(self) -> dict:
        with self._lock:
            changed = []
            for d in self.devices:
                if d["entry_point"] and not d["locked"]:
                    d["locked"] = True
                    changed.append(d["name"])
            total = sum(1 for d in self.devices if d["entry_point"])
            self._log("lock_all", newly_locked=changed, total=total)
            return {"total": total, "newly_locked": changed}

    # -- summaries
    def summary(self) -> str:
        findings = self.audit()
        sc = self.score(findings)
        crit = sum(1 for f in findings if f.severity == "critical")
        entry = [d for d in self.devices if d["entry_point"]]
        locked = sum(1 for d in entry if d["locked"])
        fixes = sum(1 for e in self.log if e["event"] == "fix")
        parts = [f"Your home security score is {sc} out of 100, grade {self.grade(sc)}."]
        parts.append("No open issues." if not findings else
                     f"{len(findings)} open issue{'s' if len(findings) != 1 else ''}, {crit} critical.")
        parts.append(f"{locked} of {len(entry)} entry points are locked.")
        if fixes:
            parts.append(f"You fixed {fixes} device{'s' if fixes != 1 else ''} this session.")
        return " ".join(parts)

    def recent_log(self, n: int = 5):
        return self.log[-n:]
