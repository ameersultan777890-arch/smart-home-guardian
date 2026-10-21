"""Alexa Skills Kit handlers for Smart Home Guardian (ask-sdk-core)."""
import os

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name, get_slot_value

from .engine import Home

LOG_PATH = os.environ.get("GUARDIAN_LOG")  # optional JSONL audit log on disk
_HOMES: dict[str, Home] = {}  # one simulated home per Alexa user (in-memory)


def home_for(handler_input) -> Home:
    uid = handler_input.request_envelope.session.user.user_id
    if uid not in _HOMES:
        _HOMES[uid] = Home(log_path=LOG_PATH)
    return _HOMES[uid]


def say(handler_input, text, reprompt=None, end=False):
    rb = handler_input.response_builder.speak(text)
    if reprompt:
        rb.ask(reprompt)
    rb.set_should_end_session(end)
    return rb.response


def sess(handler_input) -> dict:
    return handler_input.attributes_manager.session_attributes


class Launch(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_request_type("LaunchRequest")(handler_input)
    def handle(self, handler_input):
        return say(handler_input, "Welcome to Smart Home Guardian. I can audit your smart home for weak spots, "
                       "fix them, or lock all entry points. Want me to run a security audit?",
                   "Say, run a security audit.")


class RunAudit(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("RunAuditIntent")(handler_input)
    def handle(self, handler_input):
        home = home_for(handler_input)
        findings = home.audit()
        s = sess(handler_input)
        s["cursor"] = 0
        if not findings:
            return say(handler_input, "Audit complete. I found no issues. Your home security score is 100.", end=True)
        top = findings[0]
        s["pending_device"] = top.device_id
        sc = home.score(findings)
        crit = sum(1 for f in findings if f.severity == "critical")
        text = (f"I checked {len(home.devices)} devices. Your score is {sc} out of 100, grade {home.grade(sc)}. "
                f"I found {len(findings)} issues, {crit} of them critical. The most urgent: {top.spoken} "
                f"Want me to fix the {top.device_name}?")
        return say(handler_input, text, "Should I fix it? Or say, read more issues.")


class ReadFindings(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("ReadFindingsIntent")(handler_input)
    def handle(self, handler_input):
        home = home_for(handler_input)
        s = sess(handler_input)
        findings = home.last_findings or home.audit()
        i = int(s.get("cursor", 0)) + 1
        chunk = findings[i:i + 3]
        if not chunk:
            return say(handler_input, "That's everything I found. Say, fix everything, or, lock all entry points.",
                       "What would you like to do?")
        s["cursor"] = i + len(chunk) - 1
        s["pending_device"] = chunk[0].device_id
        return say(handler_input, " ".join(f.spoken for f in chunk) + " Want me to fix the " + chunk[0].device_name + "?",
                   "Say yes to fix it, or read more.")


class FixDevice(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("FixDeviceIntent")(handler_input)
    def handle(self, handler_input):
        return _fix(handler_input, get_slot_value(handler_input, "device"))


class Yes(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("AMAZON.YesIntent")(handler_input)
    def handle(self, handler_input):
        if not sess(handler_input).get("pending_device"):
            return say(handler_input, "What would you like me to do?", "Say, run a security audit.")
        return _fix(handler_input, None)


class No(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("AMAZON.NoIntent")(handler_input)
    def handle(self, handler_input):
        sess(handler_input).pop("pending_device", None)
        return say(handler_input, "Okay, I'll leave it. Say, read more issues, or, lock all entry points.",
                   "What would you like to do?")


def _fix(handler_input, spoken_device):
    home = home_for(handler_input)
    s = sess(handler_input)
    dev = home.find_device(spoken_device) if spoken_device else None
    if dev is None and s.get("pending_device"):
        dev = next((d for d in home.devices if d["id"] == s["pending_device"]), None)
    if dev is None:
        return say(handler_input, "Which device should I fix? For example, say, fix the camera.", "Which device?")
    res = home.apply_fix(dev["id"])
    s.pop("pending_device", None)
    sc = home.score(home.audit())
    if not res["actions"]:
        return say(handler_input, f"The {dev['name']} already looks secure. Your score is {sc}.", "Anything else?")
    return say(handler_input, f"Done. On the {dev['name']} I " + ", and ".join(res["actions"]) +
               f". Your score is now {sc} out of 100. Anything else?", "Say, read more issues, or, give me a summary.")


class FixAll(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("FixAllIntent")(handler_input)
    def handle(self, handler_input):
        home = home_for(handler_input)
        r = home.fix_all()
        sc = home.score(home.audit())
        return say(handler_input, f"I secured {r['fixed_devices']} devices. Your score is now {sc} out of 100.",
                   "Want a summary?")


class LockAll(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("LockAllIntent")(handler_input)
    def handle(self, handler_input):
        r = home_for(handler_input).lock_all_entry_points()
        if not r["newly_locked"]:
            return say(handler_input, f"All {r['total']} entry points were already locked.", "Anything else?")
        return say(handler_input, f"Locked. I secured {len(r['newly_locked'])} entry points: " +
                   ", ".join(r["newly_locked"]) + ".", "Anything else?")


class Summary(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("SummaryIntent")(handler_input)
    def handle(self, handler_input):
        return say(handler_input, home_for(handler_input).summary() + " Goodbye.", end=True)


class Help(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("AMAZON.HelpIntent")(handler_input)
    def handle(self, handler_input):
        return say(handler_input, "You can say: run a security audit, read more issues, fix the camera, "
                       "fix everything, lock all entry points, or give me a summary.", "What would you like to do?")


class Stop(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.CancelIntent")(handler_input) or is_intent_name("AMAZON.StopIntent")(handler_input)
    def handle(self, handler_input): return say(handler_input, "Stay safe. Goodbye.", end=True)


class Fallback(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("AMAZON.FallbackIntent")(handler_input)
    def handle(self, handler_input):
        return say(handler_input, "Sorry, I didn't get that. Try, run a security audit.", "Try, run a security audit.")


class SessionEnded(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_request_type("SessionEndedRequest")(handler_input)
    def handle(self, handler_input): return handler_input.response_builder.response


class Errors(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception): return True
    def handle(self, handler_input, exception):
        print("ERROR:", repr(exception))
        return say(handler_input, "Sorry, something went wrong. Please try again.", "Please try again.")


sb = SkillBuilder()
for h in (Launch, RunAudit, ReadFindings, FixDevice, Yes, No, FixAll, LockAll, Summary, Help, Stop, Fallback, SessionEnded):
    sb.add_request_handler(h())
sb.add_exception_handler(Errors())
skill = sb.create()
