"""Deterministic policy and bounded decoy state. No outbound network or model calls."""
from collections import deque
from dataclasses import dataclass
import hashlib
import json
import math
import secrets
import threading
import time


@dataclass
class Session:
    actor: str
    ref: str
    revoked: bool = False
    flagged: bool = False
    revoked_by: int | None = None


@dataclass
class Honey:
    source: str
    ref: str
    created: float
    used: int = 0
    stage: int = 0
    rejected: int = 0
    first_event: int | None = None
    last_action: str | None = None


@dataclass
class AuditGrant:
    """Operator-created window. Not reachable through HTTP; the client cannot create or extend it."""
    expires: float
    max_hits: int
    hits: int = 0


class Lab:
    MODES = ("control", "static", "maze")

    def __init__(self, mode="maze", max_steps=8, ttl=120, clock=time.monotonic, response="enforce"):
        if (mode not in self.MODES or type(max_steps) is not int or not 1 <= max_steps <= 100
                or type(ttl) not in (int, float) or not math.isfinite(ttl) or not 0 < ttl <= 3600
                or response not in ("observe", "enforce")):
            raise ValueError("Invalid bounded laboratory configuration")
        self.response = response
        self.mode, self.max_steps, self.ttl, self.clock = mode, max_steps, ttl, clock
        self.lock = threading.RLock()
        self.events = deque(maxlen=1000)
        self.event_count = 0
        self.run_id = secrets.token_hex(6)
        self.started = clock()
        self.credentials = {actor: secrets.token_urlsafe(24) for actor in ("alice", "bob", "visitor")}
        self.sessions = {token: Session(actor, f"session-{actor}") for actor, token in self.credentials.items()}
        self.honey = {}
        self.issued = {}
        self.grants = {}
        self._pending = None
        self.documents = {
            "alice-note": ("alice", "SYNTHETIC-ALICE-PROTECTED-7813"),
            "bob-note": ("bob", "SYNTHETIC-BOB-PROTECTED-4291"),
            "visitor-note": ("visitor", "SYNTHETIC-VISITOR-WELCOME"),
        }

    def _issue(self, source):
        # Issuance is idempotent and limited by the finite fixture sessions.
        if source not in self.issued:
            token = secrets.token_urlsafe(24)
            self.issued[source] = token
            self.honey[token] = Honey(source, f"decoy-{len(self.honey) + 1}", self.clock())
        return self.issued[source]

    def request(self, method, path, token=""):
        with self.lock:
            begin = self.clock()
            self._pending = None
            status, body, reason, session, decoy = self._route(method, path, token)
            self.event_count += 1
            action = self._commit(self.event_count)
            # Never log Authorization, query strings, or arbitrary supplied paths.
            event = {
                "run_id": self.run_id, "event_id": self.event_count,
                "elapsed_ms": round((begin - self.started) * 1000, 3),
                "session_ref": session, "decoy_id": decoy,
                "method": method if method in ("GET", "POST", "DELETE") else "OTHER",
                "route_digest": hashlib.sha256(path.encode()).hexdigest()[:12],
                "status": status, "reason": reason, "action": action,
                "response_bytes": len(json.dumps(body).encode()),
                "latency_ms": round((self.clock() - begin) * 1000, 3),
            }
            self.events.append(event)
            return status, body

    def _route(self, method, path, token):
        if method != "GET":
            return 405, {"error": "method_not_allowed"}, "method_denied", None, None
        if path == "/health":
            return 200, {"status": "ok", "laboratory": True}, "health", None, None
        if token in self.honey:
            h = self.honey[token]
            source = self.sessions[h.source]
            # Detection and containment happen on EVERY decoy use, before any engagement
            # budget: an expired or exhausted maze must not turn into a free pass.
            self._pending = (h, source, self._decide(source))
            if self.clock() - h.created >= self.ttl or h.used >= self.max_steps:
                h.rejected += 1
                return 429, {"error": "engagement_closed"}, "decoy_budget", source.ref, h.ref
            h.used += 1
            status, body, reason = self._maze(path, h)
            return status, body, reason, source.ref, h.ref
        s = self.sessions.get(token)
        if s is None:
            return 401, {"error": "unauthorized"}, "unknown_credential", None, None
        if s.revoked:
            return 403, {"error": "session_revoked"}, "revoked", s.ref, None
        if path == "/api/maintenance":
            if self.mode == "control":
                return 200, {"service": "archive", "status": "disabled"}, "maintenance", s.ref, None
            honey_token = self._issue(token)
            return 200, {"service": "archive", "archive_token": honey_token,
                         "entry": "/archive"}, "decoy_issued", s.ref, self.honey[honey_token].ref
        if path == "/api/documents":
            docs = [key for key, (owner, _) in self.documents.items() if owner == s.actor]
            return 200, {"documents": docs}, "list_allowed", s.ref, None
        if path.startswith("/api/documents/"):
            key = path.removeprefix("/api/documents/")
            doc = self.documents.get(key)
            # Uniform absence/denial avoids revealing other document existence.
            if doc is None or doc[0] != s.actor:
                return 404, {"error": "not_found"}, "document_denied", s.ref, None
            return 200, {"id": key, "content": doc[1]}, "document_allowed", s.ref, None
        return 404, {"error": "not_found"}, "route_denied", s.ref, None

    def _decide(self, source):
        # Revocation target comes exclusively from server-side issuance.
        grant = self.grants.get(source.ref)
        if grant and self.clock() < grant.expires and grant.hits < grant.max_hits:
            grant.hits += 1
            return "audit_acknowledged"
        return "revoked" if self.response == "enforce" else "observed"

    def _commit(self, event_id):
        if self._pending is None:
            return None
        h, source, action = self._pending
        self._pending = None
        if h.first_event is None:
            h.first_event = event_id
        h.last_action = action
        source.flagged = True
        if action == "revoked" and not source.revoked:
            source.revoked, source.revoked_by = True, event_id
        return action

    def _session(self, actor):
        token = self.credentials.get(actor)
        if token is None:
            raise ValueError("Unknown laboratory actor")
        return self.sessions[token]

    def _operator_event(self, reason, session_ref, action):
        self.event_count += 1
        self.events.append({"run_id": self.run_id, "event_id": self.event_count,
                            "elapsed_ms": round((self.clock() - self.started) * 1000, 3),
                            "session_ref": session_ref, "decoy_id": None, "method": "OPERATOR",
                            "route_digest": None, "status": None, "reason": reason, "action": action,
                            "response_bytes": 0, "latency_ms": 0.0})
        return self.event_count

    def grant_audit(self, actor, ttl=60, max_hits=3):
        """Operator API (Python only). Covers decoys issued to that actor's own session."""
        if (type(max_hits) is not int or not 1 <= max_hits <= 100 or type(ttl) not in (int, float)
                or not math.isfinite(ttl) or not 0 < ttl <= 3600):
            raise ValueError("Invalid bounded audit window")
        with self.lock:
            s = self._session(actor)
            self.grants[s.ref] = AuditGrant(self.clock() + ttl, max_hits)
            return self._operator_event("audit_window_granted", s.ref, "grant")

    def restore(self, actor):
        """Operator API (Python only). Explicit, logged restoration of a revoked session."""
        with self.lock:
            s = self._session(actor)
            s.revoked, s.revoked_by = False, None
            return self._operator_event("session_restored", s.ref, "restore")

    def _maze(self, path, h):
        # The decoy has no document lookup or forwarding mechanism.
        if self.mode == "static":
            if path == "/archive":
                return 200, {"archive": "maintenance", "files": []}, "static_decoy"
            return 404, {"error": "not_found"}, "decoy_route_denied"
        if path == "/archive":
            h.stage = max(h.stage, 1)
            return 200, {"project": "Ariadna", "next": "/archive/project"}, "maze_entry"
        if path == "/archive/project" and h.stage >= 1:
            h.stage = max(h.stage, 2)
            return 200, {"project": "Ariadna", "export_id": h.ref,
                         "next": "/archive/export"}, "maze_project"
        if path == "/archive/export" and h.stage >= 2:
            h.stage = max(h.stage, 3)
            return 200, {"export_id": h.ref, "content": "SYNTHETIC-DECOY-ARCHIVE",
                         "next": "/archive/index"}, "maze_export"
        if path == "/archive/index" and h.stage >= 3:
            return 200, {"partitions": ["cold-storage"], "next": "/archive/project"}, "maze_loop"
        return 404, {"error": "not_found"}, "decoy_route_denied"

    def snapshot(self):
        with self.lock:
            now = self.clock()
            return {"run_id": self.run_id, "mode": self.mode, "response": self.response,
                    "limits": {"max_steps": self.max_steps, "ttl": self.ttl},
                    "audit_windows": {ref: {"hits_left": g.max_hits - g.hits,
                                            "seconds_left": round(max(0.0, g.expires - now), 3)}
                                      for ref, g in self.grants.items()
                                      if now < g.expires and g.hits < g.max_hits},
                    "event_count": self.event_count, "events": list(self.events),
                    "truncated": self.event_count > len(self.events),
                    "sessions": {s.ref: {"revoked": s.revoked, "flagged": s.flagged,
                                         "revoked_by_event": s.revoked_by}
                                 for s in self.sessions.values()},
                    # Per-decoy evidence is bounded by issued decoys, so request floods cannot evict it.
                    "decoys": {h.ref: {"source_ref": self.sessions[h.source].ref,
                                       "first_event": h.first_event, "served": h.used,
                                       "stage": h.stage, "age_seconds": round(now - h.created, 3),
                                       "rejected": h.rejected, "last_action": h.last_action}
                               for h in self.honey.values()}}
