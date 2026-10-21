"""Smart Home Guardian as an MCP server (Streamable HTTP), reusing the same security engine as the Alexa skill.
Run:  python mcp_server.py        ->  http://localhost:8001/mcp     (stdio: python mcp_server.py --stdio)"""
import os
import sys

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from guardian.engine import Home

home = Home(log_path=os.environ.get("GUARDIAN_LOG"))
mcp = FastMCP(
    "SmartHomeGuardian",
    instructions="Audits a SIMULATED smart home, explains weaknesses in plain language, fixes them, and locks entry "
                 "points. Reply to the user in one or two short spoken sentences.",
    host="0.0.0.0", port=int(os.environ.get("PORT", "8001")), stateless_http=False,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
def run_security_audit() -> str:
    """Audit every device: weak passwords, outdated firmware, open ports, threat-intel matches. Returns score and top issues."""
    f = home.audit()
    sc = home.score(f)
    if not f:
        return "No issues found. Security score is 100."
    top = " ".join(x.spoken for x in f[:3])
    return f"Score {sc} out of 100, grade {home.grade(sc)}, {len(f)} issues. Most urgent: {top}"


@mcp.tool()
def fix_device(device: str) -> str:
    """Fix a device by spoken name, e.g. 'camera', 'front door lock', 'router'. Rotates password, updates firmware, closes ports."""
    d = home.find_device(device)
    if not d:
        return f"I couldn't find a device called {device}."
    r = home.apply_fix(d["id"])
    if not r["actions"]:
        return f"The {d['name']} already looks secure."
    return f"On the {d['name']} I " + ", and ".join(r["actions"]) + f". Score is now {home.score(home.audit())}."


@mcp.tool()
def fix_everything() -> str:
    """Fix every device with an issue."""
    r = home.fix_all()
    return f"Secured {r['fixed_devices']} devices. Score is now {home.score(home.audit())}."


@mcp.tool()
def lock_all_entry_points() -> str:
    """Lock every door and garage entry point immediately."""
    r = home.lock_all_entry_points()
    if not r["newly_locked"]:
        return f"All {r['total']} entry points were already locked."
    return "Locked: " + ", ".join(r["newly_locked"]) + "."


@mcp.tool()
def security_summary() -> str:
    """Spoken summary of the home's security posture and what was fixed this session."""
    return home.summary()


@mcp.tool()
def audit_log(limit: int = 5) -> str:
    """Read back the most recent security events."""
    ev = home.recent_log(max(1, min(limit, 20)))
    if not ev:
        return "No events yet."
    return " ".join(f"{e['event']}." for e in ev)


if __name__ == "__main__":
    mcp.run(transport="stdio" if "--stdio" in sys.argv else "streamable-http")
