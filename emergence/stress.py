"""Synthetic paired workspace and memory capacity stress studies.

These test known software limits and do not establish general intelligence,
consciousness, independent agency, or generalization outside generated cases.
No external services, personal memories, or empirical world data are used.
"""
from __future__ import annotations

from collections import defaultdict
import random
from typing import Any

from emergence.core import CognitiveAgent, Configuration, Event, Trial


WORKSPACE_CAPACITIES = (1, 2, 3, 4, 5)
MEMORY_CAPACITIES = (4, 8, 16, 24, 32)
LAGS = (0, 2, 6, 12, 20, 28)


def workspace_trials(seed: int, n: int = 480) -> list[Trial]:
    """Same cases for every architecture; never write synthetic claims to ECS memory."""
    rng = random.Random(seed)
    modes = ('chain1', 'chain2', 'chain3', 'chain4', 'revision', 'unknown')
    trials = []
    for i in range(n):
        mode = modes[i % len(modes)]
        cue = f'ws_entity_{seed}_{i}'
        place = f'ws_place_{seed}_{i}'
        events = []
        if mode.startswith('chain'):
            length = int(mode[-1])
            node = cue
            for hop in range(length - 1):
                next_node = f'ws_container_{i}_{hop}'
                events.append(Event(node, 'inside', next_node, 0.6))
                node = next_node
            events.append(Event(node, 'located_in', place, 0.6))
            answer = place
        elif mode == 'revision':
            events = [Event(cue, 'located_in', place + '_old', 0.6),
                      Event(cue, 'located_in', place, 0.6)]
            answer = place
        else:
            answer = None
        # Keep real links before the unrelated noise to avoid hidden temporal cues.
        events += [Event(f'ws_noise_{i}_{j}', 'located_in', f'ws_noise_place_{j}',
                         rng.uniform(0.2, 0.8)) for j in range(rng.randint(2, 7))]
        trials.append(Trial(mode, cue, tuple(events), answer, i))
    rng.shuffle(trials)
    return trials


def _trial_correct(trial: Trial, config: Configuration) -> int:
    agent = CognitiveAgent(config)
    for event in trial.events:
        agent.observe(event)
    return int(agent.deliberate(trial.cue)[0] == trial.answer)


def _paired_ci(a: list[int], b: list[int], seed: int, repeats: int = 500) -> list[float]:
    """Percentile bootstrap interval for a-b, conditional on generated tasks."""
    if len(a) != len(b) or not a:
        raise ValueError('paired samples must be non-empty and equal-length')
    diffs = [x - y for x, y in zip(a, b)]
    rng = random.Random(seed ^ 99451)
    n = len(diffs)
    samples = []
    for _ in range(repeats):
        samples.append(sum(diffs[rng.randrange(n)] for _ in range(n)) / n)
    samples.sort()
    return [round(samples[int(.025 * (repeats-1))], 4),
            round(samples[int(.975 * (repeats-1))], 4)]


def workspace_stress(seed: int, n: int = 480) -> dict[str, Any]:
    trials = workspace_trials(seed, n)
    out: dict[str, Any] = {}
    raw: dict[int, list[int]] = {}
    for slots in WORKSPACE_CAPACITIES:
        cfg = Configuration(memory_capacity=32, workspace_slots=slots)
        hits = [_trial_correct(t, cfg) for t in trials]
        groups: dict[str, list[int]] = defaultdict(list)
        for trial, hit in zip(trials, hits):
            groups[trial.task].append(hit)
        out[str(slots)] = {
            'accuracy': round(sum(hits) / len(hits), 4),
            'by_task': {key: round(sum(values) / len(values), 4) for key, values in sorted(groups.items())},
        }
        raw[slots] = hits
    return {
        'n_cases': len(trials),
        'seed': seed,
        'capacities': out,
        'paired_slots_5_minus_3': round((sum(raw[5])-sum(raw[3]))/len(trials), 4),
        'paired_95pct_bootstrap_ci_5_minus_3': _paired_ci(raw[5], raw[3], seed),
        'limitation': 'Capacity effects are expected on synthetically constructed multi-fact chains.',
    }


def memory_trials(seed: int, n: int = 480) -> list[Trial]:
    rng = random.Random(seed)
    trials = []
    for i in range(n):
        lag = LAGS[i % len(LAGS)]
        cue = f'mem_entity_{i}_{seed}'
        answer = f'mem_zone_{i}_{seed}'
        events = [Event(cue, 'located_in', answer, 0.75)]
        events.extend(Event(f'mem_distractor_{i}_{j}', 'located_in',
                            f'mem_noise_zone_{i}_{j}', rng.uniform(.2, .9))
                      for j in range(lag))
        trials.append(Trial(f'lag_{lag}', cue, tuple(events), answer, i))
    rng.shuffle(trials)
    return trials


def memory_stress(seed: int, n: int = 480) -> dict[str, Any]:
    trials = memory_trials(seed, n)
    out: dict[str, Any] = {}
    for capacity in MEMORY_CAPACITIES:
        cfg = Configuration(memory_capacity=capacity, workspace_slots=3)
        hits = [_trial_correct(t, cfg) for t in trials]
        by_lag: dict[str, list[int]] = defaultdict(list)
        for trial, hit in zip(trials, hits):
            by_lag[trial.task].append(hit)
        out[str(capacity)] = {'accuracy': round(sum(hits) / len(hits), 4),
                              'by_lag': {k: round(sum(v)/len(v), 4) for k, v in sorted(by_lag.items())}}
    return {
        'n_cases': len(trials), 'seed': seed, 'capacities': out,
        'limitation': 'An event falling out of a bounded FIFO memory is a designed capacity limit, not real-world evidence.',
    }
