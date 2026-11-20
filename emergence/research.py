"""Bounded optional two-role AI dialogue; JSON-only proposals, no code execution."""
from __future__ import annotations

import json
import os
from urllib import request, error
from typing import Any

from emergence.core import configuration_from_proposal

DIRECTOR = """You are Research Director for Project Emergence, an artificial cognitive architecture research prototype.
Be scientifically skeptical: no experimental result proves subjective experience. Propose ONE testable
controlled intervention on a fixed synthetic benchmark. Answer ONLY JSON with keys: hypothesis,
parameter, value, prediction. Parameter must be exactly one of memory_capacity (4,8,12,16,24,32),
workspace_slots (1,2,3,4,5), or goal_weight (0,1,2,3,4,5). No code, commands, links or personal data.
Do not claim knowledge of real-world results. The benchmark will independently test your proposal."""

CRITIC = """You are an independent Research Critic. Evaluate an experiment proposal and its observed
synthetic ablation results. Do not claim these results show consciousness. Reply ONLY JSON with
keys: critique, conclusion, next_question. Be succinct, describe limitations and confounds,
and distinguish tested results from speculation. No code, commands, links or personal data."""


def _endpoint() -> tuple[str, str, str] | None:
    key = os.environ.get("EMERGENCE_API_KEY", "").strip()
    base = os.environ.get("EMERGENCE_API_BASE", "").strip()
    model = os.environ.get("EMERGENCE_MODEL", "").strip()
    if not (key and base and model):
        return None
    if not base.startswith("https://"):
        raise ValueError("EMERGENCE_API_BASE must use HTTPS")
    return key, base.rstrip("/"), model


def _json_from_response(value: str) -> dict[str, Any]:
    value = value.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        value = "\n".join(lines[1:-1]) if len(lines) > 2 else value
    result = json.loads(value)
    if not isinstance(result, dict):
        raise ValueError("API answer must be a JSON object")
    return result


def _ask(system: str, user: str) -> dict[str, Any]:
    config = _endpoint()
    if not config:
        raise RuntimeError("No model configured")
    key, base, model = config
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user[:8000]}],
        "temperature": 0.2,
        "max_tokens": 350,
    }).encode("utf-8")
    # Owner-configured OpenAI-compatible endpoint. Hard call-count and time bounds.
    req = request.Request(base + "/chat/completions", data=payload, headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "User-Agent": "Project-Emergence-Autonomous-Lab/2",
    }, method="POST")
    with request.urlopen(req, timeout=25) as response:
        raw = response.read(32_000)
    parsed = json.loads(raw)
    content = parsed["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("No textual response")
    return _json_from_response(content)


def propose(benchmark_summary: dict[str, Any]) -> dict[str, Any]:
    result = _ask(DIRECTOR, "Baseline synthetic scores:\n" + json.dumps(benchmark_summary, sort_keys=True))
    configuration_from_proposal(result)  # Strict allowlist validation, never run model-provided code.
    return {
        "hypothesis": str(result.get("hypothesis", ""))[:400],
        "parameter": result["parameter"],
        "value": result["value"],
        "prediction": str(result.get("prediction", ""))[:300],
        "origin": "AI Research Director (API)",
    }


def critique(proposal: dict[str, Any], observed: dict[str, Any]) -> dict[str, str]:
    result = _ask(CRITIC, "Proposed intervention:\n" + json.dumps(proposal) + "\nObserved metrics:\n" + json.dumps(observed))
    return {key: str(result.get(key, ""))[:500] for key in ("critique", "conclusion", "next_question")}


def enabled() -> bool:
    try:
        return _endpoint() is not None
    except ValueError:
        return False
