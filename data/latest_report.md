# Project Emergence — Research Cycle 3

Time (UTC): 2026-11-20T04:18:51+00:00

## Controlled synthetic evaluation

| Ablation | Mean accuracy |
|---|---:|
| reactive | 25.0% |
| memory_only | 69.5% |
| workspace | 91.4% |
| workspace_no_goal | 32.8% |
| workspace_small | 69.5% |

## Bounded hypothesis

- Origin: deterministic fallback (not AI-generated)
- Hypothesis: Changing memory_capacity to 8 may change held-out performance versus the default workspace model.
- Intervention: `memory_capacity=8`
- Unmodified workspace control: 91.4%
- Intervened model: 70.6%
- Difference: -20.8% (384 same-seed trials)

## Provider warning

Director unavailable: JSONDecodeError; used deterministic fallback

## Limitations

Synthetic functional tests only. Not evidence of subjective consciousness or autonomous agency.

Model dialogue, if enabled, only proposes/reviews fixed experiments; it cannot edit or execute code.

Audit digest: `a5c6a85eda7d6a143d90aeb9ff4d7ffc86e8b95a01ed38dcf98191c7ee61f329`
