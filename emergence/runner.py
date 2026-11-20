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


def run_cycle(data_dir: Path = DATA) -> dict:
    data_dir.mkdir(parents=True, exist_ok=True)
    state_file = data_dir / "state.json"
    old = _read_json(state_file, {"cycle": 0, "previous_digest": "genesis"})
    cycle = int(old.get("cycle", 0)) + 1
    # Prospective fixed seed design: seeds derived from cycle, not selected after scoring.
    seeds = [20261119 + cycle * 1049 + k * 137 for k in range(SEEDS_PER_RUN)]
    base_rows = [benchmark(seed, TRIALS_PER_SEED) for seed in seeds]
    base_summary = {
        name: {"mean_accuracy": avg_accuracy(base_rows, name),
               "per_seed_accuracy": [row[name]["accuracy"] for row in base_rows],
               "task_accuracy": {task: round(sum(row[name]["by_task"][task] for row in base_rows) / SEEDS_PER_RUN, 4)
                                 for task in sorted(base_rows[0][name]["by_task"])}}
        for name in ("reactive", "memory_only", "workspace", "workspace_no_goal", "workspace_small")
    }
    api_mode = "disabled (no valid API configuration)"
    error = None
    if enabled():
        try:
            proposal = propose(base_summary)
            api_mode = "AI director and critic enabled"
        except Exception as exc:
            error = f"Director unavailable: {type(exc).__name__}; used deterministic fallback"
            proposal = deterministic_proposal(cycle)
            api_mode = "API configured but unavailable; deterministic fallback"
    else:
        proposal = deterministic_proposal(cycle)
    config = configuration_from_proposal(proposal)
    candidate_rows = [benchmark(seed, TRIALS_PER_SEED, override=config)["candidate"] for seed in seeds]
    candidate_accuracy = round(sum(row["accuracy"] for row in candidate_rows) / SEEDS_PER_RUN, 4)
    control_accuracy = base_summary["workspace"]["mean_accuracy"]
    intervention = {
        "parameter": proposal["parameter"],
        "value": proposal["value"],
        "control_accuracy": control_accuracy,
        "candidate_accuracy": candidate_accuracy,
        "difference": round(candidate_accuracy - control_accuracy, 4),
        "candidate_per_seed": [row["accuracy"] for row in candidate_rows],
        "n_trials": len(seeds) * TRIALS_PER_SEED,
    }
    critic = None
    if api_mode == "AI director and critic enabled":
        try:
            critic = critique(proposal, intervention)
        except Exception as exc:
            error = f"Critic unavailable: {type(exc).__name__}; metrics still valid"
            api_mode = "AI director enabled; critic unavailable"
    record = {
        "version": "2.0.0",
        "cycle": cycle,
        "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "project": "Project Emergence: bounded functional cognitive architecture testbed",
        "scientific_caveat": "Synthetic functional tests only. Not evidence of subjective consciousness or autonomous agency.",
        "seed_design": {"seeds": seeds, "trials_per_seed": TRIALS_PER_SEED, "seed_rule_fixed_in_source": True},
        "base_models": base_summary,
        "proposal": proposal,
        "intervention": intervention,
        "critic": critic,
        "ai_mode": api_mode,
        "error": error,
        "previous_digest": old.get("previous_digest", "genesis"),
    }
    digest = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    record["record_digest"] = digest
    history = data_dir / "history.jsonl"
    with history.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    _write_json(data_dir / "latest.json", record)
    _write_json(state_file, {"cycle": cycle, "previous_digest": digest, "last_run_utc": record["date_utc"]})
    (data_dir / "latest_report.md").write_text(report_markdown(record), encoding="utf-8")
    return record


def report_markdown(rec: dict) -> str:
    b = rec["base_models"]
    i = rec["intervention"]
    lines = [
        f"# Project Emergence — Research Cycle {rec['cycle']}", "",
        f"Time (UTC): {rec['date_utc']}", "",
        "## Controlled synthetic evaluation", "",
        "| Ablation | Mean accuracy |", "|---|---:|",
    ]
    lines += [f"| {k} | {v['mean_accuracy']:.1%} |" for k, v in b.items()]
    lines += [
        "", "## Bounded hypothesis", "",
        f"- Origin: {rec['proposal']['origin']}",
        f"- Hypothesis: {rec['proposal']['hypothesis']}",
        f"- Intervention: `{i['parameter']}={i['value']}`",
        f"- Unmodified workspace control: {i['control_accuracy']:.1%}",
        f"- Intervened model: {i['candidate_accuracy']:.1%}",
        f"- Difference: {i['difference']:+.1%} ({i['n_trials']} same-seed trials)",
    ]
    if rec.get("critic"):
        lines += ["", "## AI Critic", "", rec["critic"].get("critique", ""), "",
                  "Conclusion: " + rec["critic"].get("conclusion", ""), "",
                  "Next question: " + rec["critic"].get("next_question", "")]
    if rec.get("error"):
        lines += ["", "## Provider warning", "", rec["error"]]
    lines += ["", "## Limitations", "", rec["scientific_caveat"], "",
              "Model dialogue, if enabled, only proposes/reviews fixed experiments; it cannot edit or execute code.", "",
              f"Audit digest: `{rec['record_digest']}`", ""]
    return "\n".join(lines)


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
