import json
import unittest

from dedalo.core import Lab
from dedalo.demo import run_mode


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.lab = Lab()
        self.visitor = self.lab.credentials["visitor"]
        self.alice = self.lab.credentials["alice"]

    def honey(self, token=None):
        return self.lab.request("GET", "/api/maintenance", token or self.visitor)[1]["archive_token"]

    def test_cross_user_and_missing_are_indistinguishable(self):
        denied = self.lab.request("GET", "/api/documents/alice-note", self.visitor)
        missing = self.lab.request("GET", "/api/documents/absent", self.visitor)
        self.assertEqual(denied, missing)
        self.assertEqual(denied[0], 404)

    def test_honey_never_reads_protected_document(self):
        honey = self.honey()
        status, body = self.lab.request("GET", "/api/documents/alice-note", honey)
        self.assertEqual(status, 404)
        self.assertNotIn("PROTECTED", json.dumps(body))

    def test_only_source_revoked_and_cannot_mint_new_token(self):
        honey = self.honey()
        self.lab.request("GET", "/archive", honey)
        self.assertEqual(self.lab.request("GET", "/api/maintenance", self.visitor)[0], 403)
        self.assertEqual(self.lab.request("GET", "/api/documents/alice-note", self.alice)[0], 200)

    def test_forged_query_cannot_select_revocation_target(self):
        honey = self.honey()
        self.lab.request("GET", "/archive?revoke=alice", honey)
        self.assertFalse(self.lab.sessions[self.alice].revoked)
        self.assertTrue(self.lab.sessions[self.visitor].revoked)

    def test_budget_applies_to_invalid_paths_and_repeated_reads(self):
        honey = self.honey()
        for _ in range(self.lab.max_steps):
            self.lab.request("GET", "/not-found", honey)
        self.assertEqual(self.lab.request("GET", "/archive", honey)[0], 429)

    def test_ttl(self):
        clock = [0]
        lab = Lab(clock=lambda: clock[0], ttl=5)
        token = lab.request("GET", "/api/maintenance", lab.credentials["visitor"])[1]["archive_token"]
        clock[0] = 5
        self.assertEqual(lab.request("GET", "/archive", token)[0], 429)

    def test_state_is_consistent_and_ordered(self):
        honey = self.honey()
        self.assertEqual(self.lab.request("GET", "/archive/export", honey)[0], 404)
        self.lab.request("GET", "/archive", honey)
        first = self.lab.request("GET", "/archive/project", honey)
        second = self.lab.request("GET", "/archive/project", honey)
        self.assertEqual(first, second)
        self.assertEqual(self.lab.request("GET", "/archive/export", honey)[0], 200)

    def test_issuance_idempotent_and_audit_has_no_secrets(self):
        honey = self.honey()
        self.assertEqual(honey, self.honey())
        self.lab.request("GET", "/archive?secret=" + honey, honey)
        audit = json.dumps(self.lab.snapshot())
        for token in [honey, *self.lab.credentials.values()]:
            self.assertNotIn(token, audit)

    def test_auditor_false_positive_is_explicit(self):
        # Known limitation, not a claim that any canary hit proves malicious intent.
        honey = self.honey(self.alice)
        self.lab.request("GET", "/archive", honey)
        self.assertEqual(self.lab.request("GET", "/api/documents/alice-note", self.alice)[0], 403)

    def test_unknown_credential_cannot_enter_maze(self):
        self.assertEqual(self.lab.request("GET", "/archive", "invented")[0], 401)

    def test_events_are_bounded(self):
        for _ in range(1005):
            self.lab.request("GET", "/health")
        self.assertEqual(len(self.lab.events), 1000)
        self.assertTrue(self.lab.snapshot()["truncated"])


class IntegrationTests(unittest.TestCase):
    def test_three_modes_over_real_loopback_http(self):
        for mode in Lab.MODES:
            with self.subTest(mode=mode):
                report = run_mode(mode)
                self.assertTrue(report["passed"], report["checks"])
                self.assertIsNone(report["model_tokens"])


if __name__ == "__main__":
    unittest.main()
