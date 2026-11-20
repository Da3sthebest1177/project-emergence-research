"""Emergence Autonomous Lab: bounded cognitive architectures and controlled ablations.

This is a functional cognition testbed, not a consciousness detector.
All observations are synthetic, seeded, and publicly reproducible.
"""
from __future__ import annotations

import dataclasses
import math
import random
from collections import defaultdict
from typing import Any


@dataclasses.dataclass(frozen=True)
class Event:
    subject: str
    relation: str
    value: str
    salience: float = 0.2


@dataclasses.dataclass(frozen=True)
class Trial:
    task: str
    cue: str
    events: tuple[Event, ...]
    answer: str | None
    trial_id: int


@dataclasses.dataclass(frozen=True)
class Configuration:
    architecture: str = "workspace"
    memory_capacity: int = 16
    workspace_slots: int = 3
    goal_weight: float = 3.0

    def __post_init__(self):
        if self.architecture not in ("reactive", "memory", "workspace"):
            raise ValueError("invalid architecture")
        if not (2 <= self.memory_capacity <= 32):
            raise ValueError("memory capacity out of bounds")
        if not (1 <= self.workspace_slots <= 5):
            raise ValueError("workspace slots out of bounds")
        if not (0.0 <= self.goal_weight <= 5.0):
            raise ValueError("goal weight out of bounds")


def generate_trials(seed: int, n: int = 96) -> list[Trial]:
    """Held-out synthetic cases; no data from the user's actual browser memories."""
    rng = random.Random(seed)
    trials: list[Trial] = []
    modes = ("direct", "relational", "revision", "unknown")
    for i in range(n):
        mode = modes[i % len(modes)]
        entity = f"entity_{i}_{rng.randrange(100000)}"
        container = f"container_{i}_{rng.randrange(100000)}"
        loc1 = f"zone_{i}_{rng.randrange(100000)}"
        loc2 = f"zone_{i}_{rng.randrange(100000)}"
        events: list[Event] = []
        if mode == "direct":
            events.append(Event(entity, "located_in", loc1, 0.65))
            answer = loc1
        elif mode == "relational":
            events.extend((Event(entity, "inside", container, 0.6), Event(container, "located_in", loc1, 0.55)))
            answer = loc1
        elif mode == "revision":
            events.extend((Event(entity, "located_in", loc1, 0.5), Event(entity, "located_in", loc2, 0.6)))
            answer = loc2
        else:
            answer = None
        distractors = [
            Event(f"irrelevant_{i}_{j}", "located_in", f"noise_zone_{j}", rng.uniform(0.3, 1.0))
            for j in range(rng.randint(3, 25))
        ]
        # Randomized interleaving; for revision, temporal order is preserved.
        insert_index = rng.randint(0, len(distractors))
        events = distractors[:insert_index] + events + distractors[insert_index:]
        trials.append(Trial(mode, entity, tuple(events), answer, i))
    rng.shuffle(trials)
    return trials


class CognitiveAgent:
    """Simplified recurrent state with attention/broadcast and episodic memory."""

    def __init__(self, config: Configuration):
        self.config = config
        self.memory: list[Event] = []
        self.goal: str = ""
        self.workspace: list[Event] = []
        self.self_model: dict[str, Any] = {"last_reason": "none", "evidence_count": 0, "confidence": 0.0}

    def observe(self, event: Event):
        if self.config.architecture == "reactive":
            return
        self.memory.append(event)
        self.memory = self.memory[-self.config.memory_capacity:]

    def deliberate(self, goal: str) -> tuple[str | None, float, str]:
        self.goal = goal
        self.workspace = []
        if self.config.architecture == "reactive":
            return self._record(None, 0.0, "No recurrent memory")
        # Direct episodic retrieval with recency-based belief revision.
        direct = next((e for e in reversed(self.memory) if e.subject == goal and e.relation == "located_in"), None)
        if self.config.architecture == "memory":
            if direct:
                return self._record(direct.value, 0.85, "Latest direct episodic fact")
            return self._record(None, 0.0, "No matching direct fact")
        # Bounded goal-dependent broadcast. Candidate event relevance is determined
        # by a reachability search through remembered `inside` facts. Only the
        # chosen events may be used to form an answer; reachability is a selection
        # heuristic, not a hidden reasoning path.
        reachable = {goal}
        for _ in range(3):
            reachable |= {e.value for e in self.memory
                          if e.subject in reachable and e.relation == "inside"}
        scores = []
        for ix, e in enumerate(self.memory):
            relevant = float(e.subject in reachable)
            strength = self.config.goal_weight * relevant + e.salience + (ix + 1) / (4 * max(1, len(self.memory)))
            scores.append((strength, ix, e))
        chosen = sorted(scores, key=lambda s: (-s[0], -s[1]))[:self.config.workspace_slots]
        self.workspace = [item[2] for item in chosen]
        # Direct facts take precedence over derived paths; newest direct wins.
        direct = next((e for e in reversed(self.memory)
                       if e in self.workspace and e.subject == goal and e.relation == "located_in"), None)
        if direct:
            return self._record(direct.value, 0.85, "Goal-selected direct fact in workspace")
        node = goal
        seen = set()
        for hops in range(1, 5):
            if node in seen:
                break
            seen.add(node)
            edge = next((e for e in reversed(self.workspace)
                         if e.subject == node and e.relation == "inside"), None)
            if edge is None:
                break
            node = edge.value
            end = next((e for e in reversed(self.workspace)
                        if e.subject == node and e.relation == "located_in"), None)
            if end is not None:
                return self._record(end.value, 0.7, f"{hops + 1}-fact relation broadcast into workspace")
        return self._record(None, 0.0, "Insufficient goal-linked evidence in workspace")

    def _record(self, answer: str | None, confidence: float, reason: str):
        self.self_model = {
            "last_reason": reason,
            "evidence_count": len(self.workspace),
            "confidence": confidence,
            "abstained": answer is None,
        }
        return answer, confidence, reason


def evaluate(config: Configuration, trials: list[Trial]) -> dict[str, Any]:
    correct = 0
    asserted = 0
    false_assertions = 0
    brier_sum = 0.0
    by_task: dict[str, list[int]] = defaultdict(list)
    for trial in trials:
        agent = CognitiveAgent(config)
        for event in trial.events:
            agent.observe(event)
        prediction, confidence, _ = agent.deliberate(trial.cue)
        hit = prediction == trial.answer
        correct += int(hit)
        by_task[trial.task].append(int(hit))
        if prediction is not None:
            asserted += 1
            if not hit:
                false_assertions += 1
            brier_sum += (confidence - int(hit)) ** 2
    total = len(trials)
    return {
        "n": total,
        "accuracy": round(correct / total, 4) if total else 0,
        "coverage": round(asserted / total, 4) if total else 0,
        "false_assertion_rate": round(false_assertions / asserted, 4) if asserted else 0,
        "brier_asserted": round(brier_sum / asserted, 4) if asserted else None,
        "by_task": {k: round(sum(v) / len(v), 4) for k, v in sorted(by_task.items())},
    }


def benchmark(seed: int, n: int = 96, override: Configuration | None = None) -> dict[str, Any]:
    trials = generate_trials(seed, n)
    variants = {
        "reactive": Configuration(architecture="reactive"),
        "memory_only": Configuration(architecture="memory"),
        "workspace": Configuration(architecture="workspace"),
        "workspace_no_goal": Configuration(architecture="workspace", goal_weight=0),
        "workspace_small": Configuration(architecture="workspace", workspace_slots=1),
    }
    if override is not None:
        variants["candidate"] = override
    return {name: evaluate(cfg, trials) for name, cfg in variants.items()}


ALLOWED_PARAMETERS = {
    "memory_capacity": (4, 8, 12, 16, 24, 32),
    "workspace_slots": (1, 2, 3, 4, 5),
    "goal_weight": (0.0, 1.0, 2.0, 3.0, 4.0, 5.0),
}


def configuration_from_proposal(proposal: dict[str, Any]) -> Configuration:
    name = proposal.get("parameter")
    value = proposal.get("value")
    if name not in ALLOWED_PARAMETERS or type(value) not in (int, float) or value not in ALLOWED_PARAMETERS[name]:
        raise ValueError("invalid or unsupported experiment parameter")
    params: dict[str, Any] = {"architecture": "workspace", name: value}
    return Configuration(**params)


def deterministic_proposal(seed: int) -> dict[str, Any]:
    # Free fallback: experiments continue without an API, but NO AI conversation occurs.
    name = list(ALLOWED_PARAMETERS)[seed % len(ALLOWED_PARAMETERS)]
    choices = ALLOWED_PARAMETERS[name]
    value = choices[(seed // len(ALLOWED_PARAMETERS)) % len(choices)]
    return {
        "hypothesis": f"Changing {name} to {value} may change held-out performance versus the default workspace model.",
        "parameter": name,
        "value": value,
        "prediction": "difference versus workspace baseline; direction unknown",
        "origin": "deterministic fallback (not AI-generated)",
    }
