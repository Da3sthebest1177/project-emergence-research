# Project Emergence — Research Cycle 2

Time (UTC): 2026-11-20T04:16:40+00:00

## Controlled synthetic evaluation

| Ablation | Mean accuracy |
|---|---:|
| reactive | 25.0% |
| memory_only | 71.4% |
| workspace | 93.0% |
| workspace_no_goal | 30.7% |
| workspace_small | 71.4% |

## Bounded hypothesis

- Origin: AI Research Director (API)
- Hypothesis: Increasing the system’s memory capacity will enable it to retain more contextual information, thereby improving performance on relational reasoning tasks.
- Intervention: `memory_capacity=16`
- Unmodified workspace control: 93.0%
- Intervened model: 93.0%
- Difference: +0.0% (384 same-seed trials)

## Provider warning

Critic unavailable: JSONDecodeError; metrics still valid

## Limitations

Synthetic functional tests only. Not evidence of subjective consciousness or autonomous agency.

Model dialogue, if enabled, only proposes/reviews fixed experiments; it cannot edit or execute code.

Audit digest: `5f28aec295b7d360942f3157eaaf9370eeb07747661285a98afeb20ac7d5eb9a`
