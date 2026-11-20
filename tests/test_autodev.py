import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from emergence.autodev import run, validate, deterministic_proposal, _render_candidate
from emergence.core import CognitiveAgent, Configuration, evaluate, generate_trials
from emergence.policy_lab import PolicyAgent, PolicySpec, evaluate_policy

class AutoDevTests(unittest.TestCase):
    def test_policy_validation(self):
        for bad in [
            {"memory_policy": "shell"},
            {"memory_policy": "fifo", "attention_policy": "goal_recency", "memory_capacity": 16, "workspace_slots": 3, "goal_weight": 3,
             "hypothesis": "A fallback baseline.", "prediction": "No change predicted."},
        ]:
            with self.assertRaises(ValueError):
                validate(bad)

    def test_model_never_supplies_python_code(self):
        input_data = deterministic_proposal(9)
        input_data["hypothesis"] = "__import__('os').system('whoami')"
        spec, _, _ = validate(input_data)
        source = _render_candidate(spec)
        self.assertNotIn("__import__", source)
        self.assertNotIn("system(", source)

    def test_baseline_policy_equivalent_to_existing_agent(self):
        trials = generate_trials(5128, 96)
        expected = evaluate(Configuration(), trials)
        actual = evaluate_policy(trials, lambda: PolicyAgent(PolicySpec()))
        self.assertEqual(expected["accuracy"], actual["accuracy"])
        self.assertEqual(expected["by_task"], actual["by_task"])

    def test_valid_alternatives(self):
        for memory in ("fifo", "salience", "novelty"):
            for attention in ("goal_recency", "goal_salience", "goal_diversity"):
                spec = PolicySpec(memory_policy=memory, attention_policy=attention)
                r = evaluate_policy(generate_trials(17, 24), lambda: PolicyAgent(spec))
                self.assertTrue(0 <= r["accuracy"] <= 1)

    def test_fallback_never_baseline(self):
        for cycle in range(50):
            self.assertFalse(validate(deterministic_proposal(cycle))[0].baseline_equivalent())

    def test_no_credentials_in_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "data").mkdir()
            (root / "data" / "latest.json").write_text(json.dumps({"cycle": 9}))
            with patch.dict(os.environ, {"EMERGENCE_API_KEY": "SECRET_SHOULD_NOT_APPEAR"}):
                result = run(root / "data", root / "proposals", offline=True, timestamp="2026-11-20T00:00:00Z")
            self.assertEqual(result["research_cycle_evaluated"], 9)
            self.assertEqual(result["origin"], "deterministic offline fallback (not AI)")
            for f in (root / "proposals").iterdir():
                self.assertNotIn("SECRET_SHOULD_NOT_APPEAR", f.read_text())
            self.assertIn("Human review", (root / "proposals" / "development_report.md").read_text())

    def test_api_failure_uses_labelled_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("emergence.autodev._model_proposal", side_effect=ValueError("fail")):
                r = run(root / "data", root / "out", timestamp="2026-11-20T00:00:00Z")
            self.assertEqual(r["origin"], "deterministic fallback (not AI)")
            self.assertIn("ValueError", r["warnings"][0])

    def test_api_success_keeps_source_allowlisted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model_raw = deterministic_proposal(1)
            with patch("emergence.autodev._model_proposal", return_value=model_raw):
                r = run(root / "data", root / "out", timestamp="2026-11-20T00:00:00Z")
            self.assertEqual(r["origin"], "AI design proposal (API)")
            candidate_path = root / "out" / "active_candidate.py"
            spec = importlib.util.spec_from_file_location("proposed_candidate", candidate_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertIsInstance(mod.make_agent(), PolicyAgent)
            self.assertEqual(mod.SPEC.memory_policy, r["candidate_spec"]["memory_policy"])

if __name__ == "__main__":
    unittest.main()

class MergedCandidateTests(unittest.TestCase):
    def test_merged_policy_visible_in_future_cycles(self):
        from emergence.runner import run_cycle
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            root.joinpath('proposals').mkdir()
            report = run(root/'data',root/'proposals',offline=True)
            with patch.dict(os.environ, {"EMERGENCE_API_KEY":"", "EMERGENCE_API_BASE":"", "EMERGENCE_MODEL":""}):
                cycle = run_cycle(root/'data')
            self.assertIsNotNone(cycle['reviewed_policy'])
            self.assertIn('Owner-reviewed experimental policy', (root/'data'/'latest_report.md').read_text())
            self.assertEqual(cycle['reviewed_policy']['configuration'], report['candidate_spec'])
