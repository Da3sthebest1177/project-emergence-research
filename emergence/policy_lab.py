"""Auditable *bounded* algorithm alternatives for Project Emergence.

Only fixed algorithm choices are allowed. No LLM-generated source is evaluated.
This benchmark is synthetic and does not test subjective consciousness.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Callable

from emergence.core import CognitiveAgent, Configuration, Event, Trial

MEMORY_POLICIES = ("fifo", "salience", "novelty")
ATTENTION_POLICIES = ("goal_recency", "goal_salience", "goal_diversity")


@dataclass(frozen=True)
class PolicySpec:
    memory_policy: str = "fifo"
    attention_policy: str = "goal_recency"
    memory_capacity: int = 16
    workspace_slots: int = 3
    goal_weight: float = 3.0

    def __post_init__(self):
        if self.memory_policy not in MEMORY_POLICIES:
            raise ValueError("Unsupported memory policy")
        if self.attention_policy not in ATTENTION_POLICIES:
            raise ValueError("Unsupported attention policy")
        if self.memory_capacity not in (4, 8, 12, 16, 24, 32):
            raise ValueError("Unsupported memory capacity")
        if self.workspace_slots not in (1, 2, 3, 4, 5):
            raise ValueError("Unsupported workspace slots")
        if type(self.goal_weight) not in (float, int) or self.goal_weight not in (0, 1, 2, 3, 4, 5):
            raise ValueError("Unsupported goal weight")

    def baseline_equivalent(self) -> bool:
        return self == PolicySpec()


class PolicyAgent(CognitiveAgent):
    """Small, inspectable set of memory and attention policies."""

    def __init__(self, policy: PolicySpec):
        super().__init__(Configuration(memory_capacity=policy.memory_capacity,
                                       workspace_slots=policy.workspace_slots,
                                       goal_weight=float(policy.goal_weight)))
        self.policy = policy

    def observe(self, event: Event):
        if self.policy.memory_policy == "fifo":
            super().observe(event)
        elif self.policy.memory_policy == "novelty":
            # A later observation of the same subject/relation supersedes the earlier
            # one; may help revision, but loses conflicting historical evidence.
            self.memory = [e for e in self.memory
                           if not (e.subject == event.subject and e.relation == event.relation)]
            self.memory.append(event)
            self.memory = self.memory[-self.policy.memory_capacity:]
        else:
            # A salience-biased buffer; preserves chronological order of survivors.
            self.memory.append(event)
            if len(self.memory) > self.policy.memory_capacity:
                victim = min(range(len(self.memory)),
                             key=lambda i: (self.memory[i].salience, i))
                self.memory.pop(victim)

    def deliberate(self, goal: str) -> tuple[str | None, float, str]:
        if self.policy.attention_policy == "goal_recency":
            return super().deliberate(goal)
        self.goal = goal
        self.workspace = []
        reachable = {goal}
        for _ in range(3):
            reachable |= {e.value for e in self.memory
                          if e.subject in reachable and e.relation == "inside"}
        ranking = []
        for i, e in enumerate(self.memory):
            relevance = self.policy.goal_weight * float(e.subject in reachable)
            recency = (i + 1) / (4 * max(1, len(self.memory)))
            salience = e.salience * (2.0 if self.policy.attention_policy == "goal_salience" else 1.0)
            ranking.append((relevance + recency + salience, i, e))
        ranking.sort(key=lambda row: (-row[0], -row[1]))
        if self.policy.attention_policy == "goal_diversity":
            chosen = []
            remaining = ranking[:]
            while remaining and len(chosen) < self.policy.workspace_slots:
                best = max(range(len(remaining)),
                           key=lambda j: (remaining[j][0] +
                                          0.5 * (remaining[j][2].subject not in {x[2].subject for x in chosen}),
                                          remaining[j][1]))
                chosen.append(remaining.pop(best))
        else:
            chosen = ranking[:self.policy.workspace_slots]
        self.workspace = [item[2] for item in chosen]
        direct = next((e for e in reversed(self.memory)
                       if e in self.workspace and e.subject == goal and e.relation == "located_in"), None)
        if direct:
            return self._record(direct.value, 0.85, "Policy-selected direct memory")
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
            if end:
                return self._record(end.value, 0.7, f"{hops + 1}-fact policy reasoning")
        return self._record(None, 0.0, "Insufficient policy-selected evidence")


def evaluate_policy(trials: list[Trial], factory: Callable[[], CognitiveAgent]) -> dict:
    correct = 0
    asserted = 0
    false_assertions = 0
    by_task: dict[str, list[int]] = defaultdict(list)
    for trial in trials:
        agent = factory()
        for event in trial.events:
            agent.observe(event)
        answer, _, _ = agent.deliberate(trial.cue)
        hit = answer == trial.answer
        correct += int(hit)
        by_task[trial.task].append(int(hit))
        if answer is not None:
            asserted += 1
            false_assertions += int(not hit)
    n = len(trials)
    return {
        "accuracy": round(correct / n, 4) if n else 0,
        "coverage": round(asserted / n, 4) if n else 0,
        "false_assertions": false_assertions,
        "by_task": {k: round(sum(v) / len(v), 4) for k, v in sorted(by_task.items())},
    }
