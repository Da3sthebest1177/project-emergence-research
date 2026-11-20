# Project Emergence — v2.3.1 recovery upgrade

This patch repairs the actual GitHub repository snapshot of Project Emergence after a mis-uploaded repository-download ZIP. It upgrades the research ENGINE from v2.0.0 to v2.3.1, without changing the existing GitHub workflow or committed research data.

- Rejects no-op interventions equal to the default config.
- Adds a deterministic workspace capacity study for slots 1–5 with paired seed-controlled comparisons and a synthetic-sample bootstrap interval.
- Adds a separate lagged-memory stress study for capacities 4, 8, 16, 24, 32.
- Adds bounded 1–4-fact relational traversal and tests.
- Passes full baseline regression suite and new stress/no-op/migration tests (see test run).
- Prints provider HTTP status code when a request fails, without printing credentials.
- Sends fixed baseline settings and stress-summary data to the Director and Critic when configured.

## IMPORTANT: data safety

The package deliberately does NOT contain `data/`, any GitHub workflows, any API keys or credentials, or a repository clone. The one permanent workflow `.github/workflows/install-emergence.yml` is already present. Uploaded at repository ROOT under the exact name `emergence-lab.zip`, this archive is unpacked by the existing workflow and then removed; it does not overwrite history.

GitHub workflow: Actions -> Project Emergence - Install and Autonomous Research -> Run workflow.

Successful new report includes `Engine version: 2.3.1`, `Workspace capacity stress test (new)` and `Memory retention stress test (new)`. Given repository state with Cycle 8, it should progress to Cycle 9 (unless another scheduled run occurs first).

Interpretation: all tests are synthetic software capacity probes designed to produce capacity effects. These results cannot establish general intelligence or subjective consciousness.
