"""One research cycle: seeded benchmark, bounded proposal, ablation, critic, audit log.

No arbitrary code execution, network browsing, automatic software changes or paid
resources without owner-provided API configuration. Public repository data only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

from emergence.core import Configuration, benchmark, configuration_from_proposal, deterministic_proposal
from emergence.research import enabled, propose, critique
from emergence.stress import workspace_stress, memory_stress

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SEEDS_PER_RUN = 4
TRIALS_PER_SEED = 96


def _read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def avg_accuracy(rows: list[dict], name: str) -> float:
    return round(sum(row[name]["accuracy"] for row in rows) / len(rows), 4)


def _not_noop(proposal: dict) -> bool:
    """A parameter change must create a configuration different from the control."""
    return configuration_from_proposal(proposal) != Configuration()


def _fallback_that_changes_control(cycle: int) -> dict:
    # Avoid publishing a fake experiment that compares a default to itself.
    for offset in range(100):
        candidate = deterministic_proposal(cycle + offset)
        if _not_noop(candidate):
            return candidate
    raise RuntimeError("No non-default fallback configurations available")


def _safe_error(exc: Exception) -> str:
    """Disclose HTTP status where known; never echo provider bodies or credentials."""
    code = getattr(exc, 'code', None)
    if isinstance(code, int):
        return f"HTTP {code}"
    return type(exc).__name__


def run_cycle(data_dir: Path = DATA) -> dict:
    data_dir.mkdir(parents=True, exist_ok=True)
    state_file = data_dir / 'state.json'
    old = _read_json(state_file, {'cycle': 0, 'previous_digest': 'genesis'})
    cycle = int(old.get('cycle', 0)) + 1
    seeds = [20261119 + cycle * 1049 + k * 137 for k in range(SEEDS_PER_RUN)]
    base_rows = [benchmark(seed, TRIALS_PER_SEED) for seed in seeds]
    base_summary = {
        name: {'mean_accuracy': avg_accuracy(base_rows, name),
               'per_seed_accuracy': [row[name]['accuracy'] for row in base_rows],
               'task_accuracy': {task: round(sum(row[name]['by_task'][task] for row in base_rows) / SEEDS_PER_RUN, 4)
                                 for task in sorted(base_rows[0][name]['by_task'])}}
        for name in ('reactive', 'memory_only', 'workspace', 'workspace_no_goal', 'workspace_small')
    }
    ws = workspace_stress(seeds[0] ^ 1881)
    mem = memory_stress(seeds[0] ^ 3113)
    stress_overview = {
        'workspace_capacity_accuracy': {k: v['accuracy'] for k, v in ws['capacities'].items()},
        'memory_capacity_accuracy': {k: v['accuracy'] for k, v in mem['capacities'].items()},
        'workspace_stress_n_cases': ws['n_cases'], 'memory_stress_n_cases': mem['n_cases'],
    }
    api_mode = 'disabled (no valid API configuration)'
    errors = []
    proposal_rejections = []
    if enabled():
        try:
            proposal = propose(base_summary, stress_overview)
            api_mode = 'AI director and critic enabled'
            if not _not_noop(proposal):
                proposal_rejections.append('AI Director proposed a baseline-equivalent parameter; rejected')
                proposal = _fallback_that_changes_control(cycle)
                api_mode = 'AI Director rejected; deterministic fallback used'
        except Exception as exc:
            errors.append('Director unavailable: ' + _safe_error(exc) + '; used deterministic fallback')
            proposal = _fallback_that_changes_control(cycle)
            api_mode = 'API configured but unavailable; deterministic fallback'
    else:
        proposal = _fallback_that_changes_control(cycle)
    if not _not_noop(proposal):
        raise AssertionError('No-op intervention escaped safeguards')
    config = configuration_from_proposal(proposal)
    candidate_rows = [benchmark(seed, TRIALS_PER_SEED, override=config)['candidate'] for seed in seeds]
    candidate_accuracy = round(sum(row['accuracy'] for row in candidate_rows) / SEEDS_PER_RUN, 4)
    control_accuracy = base_summary['workspace']['mean_accuracy']
    intervention = {
        'parameter': proposal['parameter'], 'value': proposal['value'],
        'control_config': {'memory_capacity': 16, 'workspace_slots': 3, 'goal_weight': 3.0},
        'control_accuracy': control_accuracy, 'candidate_accuracy': candidate_accuracy,
        'difference': round(candidate_accuracy - control_accuracy, 4),
        'candidate_per_seed': [row['accuracy'] for row in candidate_rows],
        'n_trials': len(seeds) * TRIALS_PER_SEED,
    }
    critic = None
    if api_mode == 'AI director and critic enabled':
        try:
            critic = critique(proposal, {**intervention, 'stress_suite': stress_overview})
        except Exception as exc:
            errors.append('Critic unavailable: ' + _safe_error(exc) + '; metrics still valid')
            api_mode = 'AI director enabled; critic unavailable'
    record = {
        'version': '2.3.1',
        'cycle': cycle,
        'date_utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'project': 'Project Emergence: bounded functional cognitive architecture testbed',
        'scientific_caveat': 'Synthetic functional tests only. Not evidence of subjective consciousness or autonomous agency.',
        'seed_design': {'seeds': seeds, 'trials_per_seed': TRIALS_PER_SEED, 'seed_rule_fixed_in_source': True},
        'base_models': base_summary, 'proposal': proposal, 'intervention': intervention,
        'workspace_stress': ws, 'memory_stress': mem,
        'proposal_rejections': proposal_rejections,
        'critic': critic, 'ai_mode': api_mode,
        'error': '; '.join(errors) if errors else None,
        'previous_digest': old.get('previous_digest', 'genesis'),
    }
    digest = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    record['record_digest'] = digest
    history = data_dir / 'history.jsonl'
    with history.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
    _write_json(data_dir / 'latest.json', record)
    _write_json(state_file, {'cycle': cycle, 'previous_digest': digest, 'last_run_utc': record['date_utc']})
    (data_dir / 'latest_report.md').write_text(report_markdown(record), encoding='utf-8')
    return record


def report_markdown(rec: dict) -> str:
    b = rec['base_models']
    i = rec['intervention']
    ws = rec['workspace_stress']
    mem = rec['memory_stress']
    lines = [
        f"# Project Emergence — Research Cycle {rec['cycle']}", '',
        f"Time (UTC): {rec['date_utc']}", '',
        f"Engine version: {rec['version']}", '',
        '## Controlled synthetic evaluation', '',
        '| Ablation | Mean accuracy |', '|---|---:|',
    ]
    lines += [f"| {k} | {v['mean_accuracy']:.1%} |" for k, v in b.items()]
    lines += [
        '', '## Bounded hypothesis', '',
        f"- Origin: {rec['proposal']['origin']}",
        f"- Hypothesis: {rec['proposal']['hypothesis']}",
        f"- Intervention: `{i['parameter']}={i['value']}`",
        f"- Unmodified workspace control: {i['control_accuracy']:.1%}",
        f"- Intervened model: {i['candidate_accuracy']:.1%}",
        f"- Difference: {i['difference']:+.1%} ({i['n_trials']} same-seed trials)",
        '', '### Default workspace settings', '',
        f"`memory_capacity=16`, `workspace_slots=3`, `goal_weight=3.0`",
    ]
    if rec.get('proposal_rejections'):
        lines += ['', '### Rejected no-op proposal', ''] + [f'- {x}' for x in rec['proposal_rejections']]
    lines += [
        '', '## Workspace capacity stress test (new)', '',
        f"{ws['n_cases']} same-seed synthetic cases with multi-fact chains; all capacities use memory_capacity=32.", '',
        '| Workspace slots | Mean accuracy |', '|---:|---:|',
    ]
    lines += [f"| {k} | {v['accuracy']:.1%} |" for k, v in ws['capacities'].items()]
    ci = ws['paired_95pct_bootstrap_ci_5_minus_3']
    lines += ['', f"- Paired slots 5 minus slots 3: {ws['paired_slots_5_minus_3']:+.1%}",
              f"- Synthetic-case bootstrap 95% interval: [{ci[0]:+.1%}, {ci[1]:+.1%}]",
              f"- Caveat: {ws['limitation']}",
              '', '## Memory retention stress test (new)', '',
              f"{mem['n_cases']} same-seed cases with evidence followed by 0–28 distractors.", '',
              '| Memory capacity | Mean accuracy |', '|---:|---:|']
    lines += [f"| {k} | {v['accuracy']:.1%} |" for k, v in mem['capacities'].items()]
    lines += ['', f"- Caveat: {mem['limitation']}"]
    if rec.get('critic'):
        lines += ['', '## AI Critic', '', rec['critic'].get('critique', ''), '',
                  'Conclusion: ' + rec['critic'].get('conclusion', ''), '',
                  'Next question: ' + rec['critic'].get('next_question', '')]
    if rec.get('error'):
        lines += ['', '## Provider warning', '', rec['error']]
    lines += ['', '## Limitations', '', rec['scientific_caveat'], '',
              'Generated benchmarks are capacity probes, not independent intelligence assessments.',
              'Model dialogue, if enabled, only proposes/reviews fixed experiments; it cannot edit or execute code.', '',
              f"Audit digest: `{rec['record_digest']}`", '']
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=DATA)
    args = p.parse_args()
    record = run_cycle(args.data_dir)
    i = record["intervention"]
    print(f"Cycle {record['cycle']}: control={i['control_accuracy']:.3f}, candidate={i['candidate_accuracy']:.3f}, delta={i['difference']:+.3f}")
    print(f"Research mode: {record['ai_mode']}")
    print(f"Report: {args.data_dir / 'latest_report.md'}")


if __name__ == "__main__":
    main()
