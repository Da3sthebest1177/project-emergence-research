# Project Emergence — Autonomous Research Lab v2.2

## What this release changes

v2.2 adds a **capacity stress test** to the existing AI-directed, daily GitHub research cycle. It answers the Cycle 4 critic's question: can a harder, longer-chain task show a functional effect of workspace capacity that is hidden by an easy benchmark?

- Adds seeded relation chains requiring 1–4 facts in the workspace, plus revision and unknown cases.
- Runs same-trial comparisons for workspace slots 1–5 on 480 new synthetic trials per cycle.
- Reports performance by case type and a paired bootstrap interval for slots 5 minus 3.
- Adds bounded multi-step relationship traversal to the experimental cognitive agent.
- Supplies stress-suite data to the AI Research Director and Critic.
- Raises the AI Critic's saved text limit and asks it to avoid inventing predictions and baselines.
- Preserves **all** existing `data/` research history and the scheduled GitHub workflow.
- Does not alter API settings, secrets, or your Hugging Face ECS browser data.
- Does not allow model-generated code execution, spending, or autonomous repository changes.

## Interpret scores carefully

The synthetic stress test is **deliberately designed** to require more than three pieces of information for some cases. A capacity effect on those cases is an expected software sanity check, not evidence of unexpected general intelligence, independent agency, or subjective consciousness. The bootstrap interval is conditional on this generated test population; no claim of external validity is made.

## Installation (Android, existing GitHub Lab)

1. In your GitHub repository's **Code** tab choose **Add file → Upload files**.
2. Upload the supplied file `emergence-lab.zip` **at the repository root**, without unzipping it.
3. Commit with message `Install Project Emergence v2.2 capacity stress lab`.
4. Open **Actions → Project Emergence - Install and Autonomous Research → Run workflow**.
5. Wait for the green checkmark. The existing workflow will unpack the files, test them, run the research cycle, and commit the updated report.
6. Open `data/latest_report.md` and find **Workspace capacity stress test (new)**.

No other settings should need changing. The `emergence-lab.zip` file must be at the repository root, and your corrected workflow must still include the step `Unpack installation without extra workflows`. Do not upload the ZIP into the `emergence` subfolder.

## Verification performed

- 35/35 Python tests passed in a local test environment (existing tests + four new stress tests).
- Two different seeded trial populations give deterministic results; task and reasoning outputs preserve evidence ordering.
- No real observations are created: generated trials are in memory only and only aggregate results are written to `data/`.
- The GitHub API and Groq endpoint were **not** called in these tests; live API operation still depends on your configured GitHub secret and provider availability.

## Subsequent scientific milestone

Separate from these controlled capacity diagnostics, the next experiment class should use **partially observable interactive environments**, persistent beliefs updated over time, and counterfactual interventions. Those would still only measure specific functional properties associated with cognitive theories—not subjectivity itself.
