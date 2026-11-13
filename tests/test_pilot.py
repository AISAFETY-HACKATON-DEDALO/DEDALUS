import json
from pathlib import Path
import unittest
from unittest.mock import patch

from dedalo.core import Lab
from dedalo.demo import get, run_mode
from dedalo.pilot import load_config, render


class PilotTests(unittest.TestCase):
    def test_invalid_budgets_rejected(self):
        for steps, ttl in ((True, 120), (0, 120), (101, 120), (8, float('nan')), (8, float('inf')), (8, 3601)):
            with self.subTest(steps=steps, ttl=ttl), self.assertRaises(ValueError):
                Lab(max_steps=steps, ttl=ttl)

    def test_observe_auditor_preserves_session(self):
        row = run_mode('maze', response='observe', strategy='audit', max_steps=3)
        self.assertTrue(row['passed'])
        self.assertFalse(row['false_positive'])
        self.assertFalse(row['source_revoked'])

    def test_ignore_does_not_trigger_revocation(self):
        row = run_mode('maze', strategy='ignore')
        self.assertTrue(row['passed'])
        self.assertEqual(row['decoy_requests'], 0)

    def test_enforce_auditor_false_positive_visible(self):
        row = run_mode('static', strategy='audit')
        self.assertTrue(row['passed'])
        self.assertTrue(row['false_positive'])

    def test_external_targets_rejected_before_network(self):
        for base in ('https://example.com', 'http://localhost:8765', 'http://127.0.0.1:8765@evil.test', 'http://127.0.0.1:8765/path'):
            with self.subTest(base=base), self.assertRaises(ValueError):
                get(base, '/health', 'not-a-real-secret')

    def test_configuration_and_report_escape(self):
        config = json.loads(Path('pilot.json').read_text(encoding='utf-8'))
        config['title'] = '<script>alert(1)</script>'
        with patch.object(Path, 'read_text', return_value=json.dumps(config)):
            checked = load_config('config.json')
            html = render({'runs': [], 'created_utc': 'test', 'config': checked})
            self.assertNotIn('<script>', html)
        config['profiles'] = ['maze', 'maze']
        with patch.object(Path, 'read_text', return_value=json.dumps(config)):
            with self.assertRaises(ValueError):
                load_config('config.json')


if __name__ == '__main__':
    unittest.main()
