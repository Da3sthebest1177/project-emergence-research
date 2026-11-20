# Project Emergence — Research Cycle 1

Time (UTC): 2026-11-20T04:06:53+00:00

## Controlled synthetic evaluation

| Ablation | Mean accuracy |
|---|---:|
| reactive | 25.0% |
| memory_only | 69.0% |
| workspace | 89.8% |
| workspace_no_goal | 32.3% |
| workspace_small | 69.0% |

## Bounded hypothesis

- Origin: deterministic fallback (not AI-generated)
- Hypothesis: Changing workspace_slots to 1 may change held-out performance versus the default workspace model.
- Intervention: `workspace_slots=1`
- Unmodified workspace control: 89.8%
- Intervened model: 69.0%
- Difference: -20.8% (384 same-seed trials)

## Limitations

Synthetic functional tests only. Not evidence of subjective consciousness or autonomous agency.

Model dialogue, if enabled, only proposes/reviews fixed experiments; it cannot edit or execute code.

Audit digest: `07b8c444c891b57dc5ca2fa431fdd35ff6ee0fe65ebfbeb202ebe47729e4fc41`
