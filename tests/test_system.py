import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from emergence.core import (
    CognitiveAgent, Configuration, Event, benchmark, configuration_from_proposal,
    deterministic_proposal, evaluate, generate_trials, Trial,
)
from emergence.runner import run_cycle
from emergence.research import _json_from_response, enabled


class CognitiveCoreTests(unittest.TestCase):
    def test_deterministic_trials(self):
        self.assertEqual(generate_trials(42), generate_trials(42))
    def test_seed_changes_trials(self):
        self.assertNotEqual(generate_trials(42), generate_trials(43))
    def test_each_trial_has_correct_answer(self):
        for t in generate_trials(77):
            if t.task == "unknown":
                self.assertIsNone(t.answer)
            else:
                self.assertIsNotNone(t.answer)
    def test_direct_retrieval(self):
        a = CognitiveAgent(Configuration())
        a.observe(Event("orb", "located_in", "room"))
        self.assertEqual(a.deliberate("orb")[0], "room")
    def test_revision_prefers_newer(self):
        a = CognitiveAgent(Configuration())
        a.observe(Event("orb", "located_in", "old"))
        a.observe(Event("orb", "located_in", "new"))
        self.assertEqual(a.deliberate("orb")[0], "new")
    def test_relational_inference(self):
        a = CognitiveAgent(Configuration())
        a.observe(Event("orb", "inside", "box"))
        a.observe(Event("box", "located_in", "room"))
        self.assertEqual(a.deliberate("orb")[0], "room")
    def test_memory_only_cannot_two_hop(self):
        a = CognitiveAgent(Configuration(architecture="memory"))
        a.observe(Event("orb", "inside", "box"))
        a.observe(Event("box", "located_in", "room"))
        self.assertIsNone(a.deliberate("orb")[0])
    def test_no_evidence_abstention(self):
        a = CognitiveAgent(Configuration())
        self.assertIsNone(a.deliberate("unknown")[0])
        self.assertTrue(a.self_model["abstained"])
    def test_reactive_has_no_memory(self):
        a = CognitiveAgent(Configuration(architecture="reactive"))
        a.observe(Event("orb", "located_in", "room"))
        self.assertEqual(a.memory, [])
    def test_small_workspace_limits_inference(self):
        a = CognitiveAgent(Configuration(workspace_slots=1))
        a.observe(Event("orb", "inside", "box"))
        a.observe(Event("box", "located_in", "room"))
        self.assertIsNone(a.deliberate("orb")[0])
    def test_memory_capacity_enforced(self):
        a = CognitiveAgent(Configuration(memory_capacity=2))
        for i in range(10):
            a.observe(Event(str(i), "x", "y"))
        self.assertEqual(len(a.memory), 2)
    def test_no_goal_attention_changes_workspace(self):
        a = CognitiveAgent(Configuration(goal_weight=0, workspace_slots=1))
        a.observe(Event("orb", "located_in", "room", 0.1))
        a.observe(Event("distractor", "located_in", "noise", 1.0))
        self.assertIsNone(a.deliberate("orb")[0])
    def test_benchmark_reproducible(self):
        self.assertEqual(benchmark(88), benchmark(88))
    def test_benchmark_contains_ablations(self):
        self.assertEqual(len(benchmark(88)), 5)
    def test_all_accuracies_bounded(self):
        for value in benchmark(88).values():
            self.assertGreaterEqual(value["accuracy"], 0)
            self.assertLessEqual(value["accuracy"], 1)
    def test_workspace_outperforms_reactive(self):
        b = benchmark(88)
        self.assertGreater(b["workspace"]["accuracy"], b["reactive"]["accuracy"])
    def test_workspace_relational_outperforms_memory(self):
        b = benchmark(88)
        self.assertGreater(b["workspace"]["by_task"]["relational"], b["memory_only"]["by_task"]["relational"])
    def test_invalid_parameters_rejected(self):
        for p in ({"parameter": "shell", "value": 0}, {"parameter": "workspace_slots", "value": 999},
                  {"parameter": "workspace_slots", "value": "2"}):
            with self.assertRaises(ValueError):
                configuration_from_proposal(p)
    def test_valid_parameter(self):
        self.assertEqual(configuration_from_proposal({"parameter": "workspace_slots", "value": 2}).workspace_slots, 2)
    def test_fallback_marked_non_ai(self):
        self.assertIn("not AI", deterministic_proposal(2)["origin"])
    def test_llm_response_parser(self):
        self.assertEqual(_json_from_response('```json\n{"parameter":"memory_capacity","value":8}\n```')["value"], 8)
    def test_api_disabled_without_three_config(self):
        with patch.dict(os.environ, {"EMERGENCE_API_KEY":"", "EMERGENCE_API_BASE":"", "EMERGENCE_MODEL":""}):
            self.assertFalse(enabled())
    def test_no_overwriting_history_on_cycle(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with patch.dict(os.environ, {"EMERGENCE_API_KEY":"", "EMERGENCE_API_BASE":"", "EMERGENCE_MODEL":""}):
                a = run_cycle(folder)
                b = run_cycle(folder)
            self.assertEqual(a["cycle"], 1)
            self.assertEqual(b["cycle"], 2)
            self.assertEqual(b["previous_digest"], a["record_digest"])
            self.assertEqual(len((folder/"history.jsonl").read_text().strip().splitlines()), 2)
            self.assertEqual(json.loads((folder/"state.json").read_text())["cycle"], 2)
            self.assertIn("bounded hypothesis", (folder/"latest_report.md").read_text().lower())
    def test_synthetic_only(self):
        t = generate_trials(17, 6)
        self.assertTrue(all(e.subject.startswith(("entity_", "container_", "irrelevant_")) for x in t for e in x.events))


if __name__ == "__main__":
    unittest.main()
