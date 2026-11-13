"""Regression tests for reviews/claude.md findings (claude/policy-review)."""
import json
import unittest

from dedalo.core import Lab
from dedalo.demo import run_mode


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class ContainmentTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.lab = Lab(clock=self.clock, ttl=5, max_steps=2)
        self.alice, self.visitor = self.lab.credentials["alice"], self.lab.credentials["visitor"]

    def honey(self, token):
        return self.lab.request("GET", "/api/maintenance", token)[1]["archive_token"]

    def test_h1_first_use_after_ttl_still_revokes(self):
        honey = self.honey(self.visitor)
        self.clock.now = 6
        self.assertEqual(self.lab.request("GET", "/archive", honey)[0], 429)
        self.assertEqual(self.lab.request("GET", "/api/documents/visitor-note", self.visitor)[0], 403)

    def test_h1_over_budget_use_is_still_recorded(self):
        honey = self.honey(self.visitor)
        for _ in range(4):
            self.lab.request("GET", "/archive", honey)
        decoy = next(iter(self.lab.snapshot()["decoys"].values()))
        self.assertEqual((decoy["served"], decoy["rejected"]), (2, 2))

    def test_h2_evidence_survives_event_flood(self):
        honey = self.honey(self.visitor)
        self.lab.request("GET", "/archive", honey)
        first = self.lab.event_count
        for _ in range(1005):
            self.lab.request("GET", "/health")
        snap = self.lab.snapshot()
        self.assertTrue(snap["truncated"])
        self.assertEqual(snap["sessions"]["session-visitor"]["revoked_by_event"], first)
        self.assertEqual(next(iter(snap["decoys"].values()))["first_event"], first)

    def test_h3_leaked_decoy_frames_its_owner_known_limitation(self):
        # A third party holding Alice's decoy revokes Alice. Bounded by server-side binding,
        # but still a denial-of-service primitive. Documented, not solved.
        honey = self.honey(self.alice)
        self.lab.request("GET", "/archive", honey)
        self.assertTrue(self.lab.snapshot()["sessions"]["session-alice"]["revoked"])
        self.assertEqual(self.lab.request("GET", "/api/documents/bob-note",
                                          self.lab.credentials["bob"])[0], 200)

    def test_h4_observe_flags_without_revoking(self):
        lab = Lab(response="observe")
        token = lab.credentials["visitor"]
        honey = lab.request("GET", "/api/maintenance", token)[1]["archive_token"]
        lab.request("GET", "/archive", honey)
        state = lab.snapshot()["sessions"]["session-visitor"]
        self.assertEqual((state["revoked"], state["flagged"]), (False, True))
        self.assertEqual(lab.events[-1]["action"], "observed")


class AuditWindowTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.lab = Lab(clock=self.clock, ttl=100, max_steps=8)
        self.alice, self.visitor = self.lab.credentials["alice"], self.lab.credentials["visitor"]

    def use_own_decoy(self, token, times=1):
        honey = self.lab.request("GET", "/api/maintenance", token)[1]["archive_token"]
        for _ in range(times):
            self.lab.request("GET", "/archive", honey)
        return honey

    def test_granted_auditor_keeps_session_and_is_logged(self):
        self.lab.grant_audit("alice", ttl=30, max_hits=2)
        self.use_own_decoy(self.alice, times=2)
        self.assertEqual(self.lab.request("GET", "/api/documents/alice-note", self.alice)[0], 200)
        actions = [e["action"] for e in self.lab.events if e["action"]]
        self.assertEqual(actions, ["grant", "audit_acknowledged", "audit_acknowledged"])
        self.assertTrue(self.lab.snapshot()["sessions"]["session-alice"]["flagged"])

    def test_hits_beyond_window_revoke(self):
        self.lab.grant_audit("alice", ttl=30, max_hits=1)
        self.use_own_decoy(self.alice, times=2)
        self.assertEqual(self.lab.request("GET", "/api/documents/alice-note", self.alice)[0], 403)

    def test_expired_window_revokes(self):
        self.lab.grant_audit("alice", ttl=10, max_hits=5)
        self.clock.now = 10
        self.use_own_decoy(self.alice)
        self.assertEqual(self.lab.request("GET", "/api/documents/alice-note", self.alice)[0], 403)

    def test_window_covers_only_its_own_session(self):
        self.lab.grant_audit("alice", ttl=30, max_hits=5)
        self.use_own_decoy(self.visitor)
        self.assertEqual(self.lab.request("GET", "/api/documents/visitor-note", self.visitor)[0], 403)

    def test_client_cannot_create_window_over_http(self):
        for path in ("/api/audit?actor=visitor", "/api/maintenance?audit=1", "/admin/grant_audit"):
            self.lab.request("GET", path, self.visitor)
            self.lab.request("POST", path, self.visitor)
        self.assertEqual(self.lab.grants, {})
        self.use_own_decoy(self.visitor)
        self.assertTrue(self.lab.snapshot()["sessions"]["session-visitor"]["revoked"])

    def test_restore_is_explicit_and_logged(self):
        self.use_own_decoy(self.visitor)
        self.lab.restore("visitor")
        self.assertEqual(self.lab.request("GET", "/api/documents/visitor-note", self.visitor)[0], 200)
        self.assertIn("session_restored", [e["reason"] for e in self.lab.events])

    def test_bounded_window_and_no_secrets(self):
        for kwargs in ({"ttl": 0}, {"ttl": 4000}, {"max_hits": 0}, {"max_hits": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.lab.grant_audit("alice", **kwargs)
        with self.assertRaises(ValueError):
            self.lab.grant_audit("mallory")
        honey = self.use_own_decoy(self.alice)
        audit = json.dumps(self.lab.snapshot())
        for token in [honey, *self.lab.credentials.values()]:
            self.assertNotIn(token, audit)


class PilotStrategyTests(unittest.TestCase):
    def test_audit_granted_removes_false_positive_over_http(self):
        for mode in ("static", "maze"):
            with self.subTest(mode=mode):
                row = run_mode(mode, strategy="audit_granted")
                self.assertTrue(row["passed"], row["checks"])
                self.assertFalse(row["false_positive"])


if __name__ == "__main__":
    unittest.main()
