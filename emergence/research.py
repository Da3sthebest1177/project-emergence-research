"""Bounded optional two-role AI dialogue with schema-constrained JSON outputs.

Drop-in replacement for Project Emergence Autonomous Research Lab v2:
  emergence/research.py

This module never executes model-generated code, never logs credentials, and
preserves the validated proposal allowlist in emergence.core.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib import request
from urllib.parse import urlsplit

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
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Model returned empty content; a completed JSON object is required")
    text = value.strip()
    # Tolerate code fences from providers without schema-constrained decoding.
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        # Do not echo response bodies into logs: they may contain untrusted data.
        raise ValueError("Model response was not a complete JSON object") from exc
    if not isinstance(result, dict):
        raise ValueError("API answer must be a JSON object")
    return result


def _schema(role: str) -> dict[str, Any]:
    if role == "director":
        fields: dict[str, dict[str, Any]] = {
            "hypothesis": {"type": "string"},
            "parameter": {"type": "string", "enum": ["memory_capacity", "workspace_slots", "goal_weight"]},
            "value": {"type": "integer", "enum": [0, 1, 2, 3, 4, 5, 8, 12, 16, 24, 32]},
            "prediction": {"type": "string"},
        }
    elif role == "critic":
        fields = {
            "critique": {"type": "string"},
            "conclusion": {"type": "string"},
            "next_question": {"type": "string"},
        }
    else:
        raise ValueError("Invalid AI role")
    return {"type": "object", "properties": fields,
            "required": list(fields.keys()), "additionalProperties": False}


def _ask(system: str, user: str) -> dict[str, Any]:
    config = _endpoint()
    if not config:
        raise RuntimeError("No model configured")
    key, base, model = config
    role = "director" if system == DIRECTOR else "critic"
    # Groq GPT-OSS supports strict JSON Schema outputs. On other compatible APIs,
    # JSON Object Mode still substantially reduces response-format failures.
    is_groq = urlsplit(base).hostname == "api.groq.com"
    strict_groq = is_groq and model in ("openai/gpt-oss-20b", "openai/gpt-oss-120b")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user[:8000]}],
        "temperature": 0.2,
        "max_completion_tokens": 1600,
    }
    if strict_groq:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "emergence_" + role,
                            "strict": True, "schema": _schema(role)},
        }
        # Fewer reasoning tokens for this narrow classification/parameter task.
        payload["reasoning_effort"] = "low"
    else:
        payload["response_format"] = {"type": "json_object"}

    req = request.Request(base + "/chat/completions",
                          data=json.dumps(payload).encode("utf-8"),
                          headers={"Authorization": "Bearer " + key,
                                   "Content-Type": "application/json",
                                   "User-Agent": "Project-Emergence-Autonomous-Lab/2.1"},
                          method="POST")
    with request.urlopen(req, timeout=35) as response:
        raw = response.read(64_000)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("API returned invalid transport JSON") from exc
    choices = parsed.get("choices") if isinstance(parsed, dict) else None
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ValueError("API returned no completion choices")
    choice = choices[0]
    message = choice.get("message", {})
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        finish = choice.get("finish_reason", "unknown")
        raise ValueError(f"Model response had no final JSON content (finish_reason={finish})")
    if choice.get("finish_reason") == "length":
        raise ValueError("Model reached its completion limit before finalizing JSON")
    return _json_from_response(content)


def propose(benchmark_summary: dict[str, Any]) -> dict[str, Any]:
    result = _ask(DIRECTOR, "Baseline synthetic scores:\n" + json.dumps(benchmark_summary, sort_keys=True))
    configuration_from_proposal(result)  # Strict allowlist validation: never run model-provided code.
    return {
        "hypothesis": str(result.get("hypothesis", ""))[:400],
        "parameter": result["parameter"],
        "value": result["value"],
        "prediction": str(result.get("prediction", ""))[:300],
        "origin": "AI Research Director (API)",
    }


def critique(proposal: dict[str, Any], observed: dict[str, Any]) -> dict[str, str]:
    result = _ask(CRITIC, "Proposed intervention:\n" + json.dumps(proposal) +
                  "\nObserved metrics:\n" + json.dumps(observed))
    return {key: str(result.get(key, ""))[:500]
            for key in ("critique", "conclusion", "next_question")}


def enabled() -> bool:
    try:
        return _endpoint() is not None
    except ValueError:
        return False
