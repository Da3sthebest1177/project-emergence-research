import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from emergence.core import Configuration, Event, CognitiveAgent
from emergence.runner import _fallback_that_changes_control, _not_noop, run_cycle
from emergence.stress import workspace_stress, memory_stress, workspace_trials, memory_trials

class UpgradeTests(unittest.TestCase):
    def test_workspace_cases_deterministic(self):
        self.assertEqual(workspace_trials(9, 60), workspace_trials(9, 60))

    def test_memory_cases_deterministic(self):
        self.assertEqual(memory_trials(9, 60), memory_trials(9, 60))

    def test_workspace_capacity_sensitivity(self):
        scores=workspace_stress(15, 120)
        self.assertGreater(scores['capacities']['5']['accuracy'], scores['capacities']['3']['accuracy'])
        self.assertGreater(scores['capacities']['3']['accuracy'], scores['capacities']['1']['accuracy'])
        self.assertEqual(scores['n_cases'],120)

    def test_workspace_bootstrap_interval_deterministic(self):
        a=workspace_stress(23,120)
        b=workspace_stress(23,120)
        self.assertEqual(a,b)
        self.assertGreater(a['paired_95pct_bootstrap_ci_5_minus_3'][0], 0)

    def test_memory_capacity_sensitivity(self):
        scores=memory_stress(17, 120)
        self.assertGreater(scores['capacities']['32']['accuracy'], scores['capacities']['16']['accuracy'])
        self.assertGreater(scores['capacities']['16']['accuracy'], scores['capacities']['4']['accuracy'])

    def test_three_hop_relation(self):
        a=CognitiveAgent(Configuration(workspace_slots=3))
        for e in [Event('orb','inside','box'),Event('box','inside','cabinet'),Event('cabinet','located_in','house')]:a.observe(e)
        self.assertEqual(a.deliberate('orb')[0],'house')

    def test_abstain_with_insufficient_slots(self):
        a=CognitiveAgent(Configuration(workspace_slots=2))
        for e in [Event('orb','inside','box'),Event('box','inside','cabinet'),Event('cabinet','located_in','house')]:a.observe(e)
        self.assertIsNone(a.deliberate('orb')[0])

    def test_detect_noop(self):
        self.assertFalse(_not_noop({'parameter':'memory_capacity','value':16}))
        self.assertFalse(_not_noop({'parameter':'workspace_slots','value':3}))
        self.assertTrue(_not_noop({'parameter':'workspace_slots','value':5}))

    def test_fallback_never_noop(self):
        self.assertTrue(all(_not_noop(_fallback_that_changes_control(c)) for c in range(60)))

    def test_reject_api_noop_and_keep_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            with patch('emergence.runner.enabled', return_value=True), \
                 patch('emergence.runner.propose',return_value={'parameter':'memory_capacity','value':16,'hypothesis':'none','prediction':'none','origin':'AI Research Director (API)'}), \
                 patch('emergence.runner.critique') as critic:
                a=run_cycle(folder)
            self.assertTrue(a['proposal_rejections'])
            self.assertTrue(_not_noop(a['proposal']))
            critic.assert_not_called()
            self.assertIn('Rejected no-op proposal', (folder/'latest_report.md').read_text())
            self.assertIn('Workspace capacity stress test (new)',(folder/'latest_report.md').read_text())
            self.assertIn('Memory retention stress test (new)',(folder/'latest_report.md').read_text())
            with patch.dict(os.environ,{'EMERGENCE_API_KEY':'','EMERGENCE_API_BASE':'','EMERGENCE_MODEL':''}):
                b=run_cycle(folder)
            self.assertEqual(b['previous_digest'],a['record_digest'])
            self.assertEqual(b['cycle'],2)
            self.assertEqual(len((folder/'history.jsonl').read_text().splitlines()),2)

    def test_provider_status_safe(self):
        from urllib.error import HTTPError
        from emergence.runner import _safe_error
        self.assertEqual(_safe_error(HTTPError('https://example.com',429,'Rate limited',None,None)),'HTTP 429')

if __name__ == '__main__':unittest.main()
