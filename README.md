# Project Emergence — Autonomous Research Lab v2.0

A **separate cloud research service** for the Project Emergence Cognitive System. It does not replace the existing Hugging Face ECS v1.4 browser prototype or automatically read its private `localStorage` data.

## What this actually does

- Executes controlled, seeded experiments comparing a reactive baseline, episodic memory, a goal-weighted global workspace, and two ablations.
- Measures delayed retrieval, two-step relations, belief revision, and appropriate abstention on *synthetic data*.
- Keeps append-only JSONL experiments, timestamps, digest-chained records and readable scientific summaries in GitHub.
- Runs once daily and on demand through GitHub Actions; no server has to stay alive between runs.
- Optionally conducts an **AI Research Director → controlled experiment → AI Research Critic** exchange, using an owner-provided OpenAI-compatible API.
- Enforces an allowlist of permitted experimental parameters. Model output cannot run code, rewrite source, spend money, contact outsiders or approve itself.
- Leaves code changes to human-reviewed contributions. It does not autonomously develop new modules; that is a later workflow requiring sandboxed PR validation.

**This is not me—the ChatGPT conversation—running in the background, and it is not a demonstration of consciousness.** The two roles can use one API model with different system instructions; they are not necessarily independent models. Tests on synthetic tasks measure functional behavior, not subjective experience.

## Cost and privacy

GitHub Actions standard hosted runners are currently free in public repositories, subject to GitHub terms and limits. GitHub may delay or drop scheduled jobs; public-repository schedules may be disabled after 60 days of inactivity. No cloud billing account is needed for the default test-only mode.

The optional AI dialogue consumes **at most two model API requests per research cycle**. It requires separate service credentials and may incur charges. This repository does **not** provide an AI model, an API account, or free unlimited inference. Do not configure the optional provider unless you confirm its billing limits, availability, and pricing. Your ChatGPT subscription alone does not automatically cover API use.

**Public GitHub repositories expose all committed research records.** Do not upload personal conversations, unredacted ECS memory backups, secrets, names, or identifying information. This lab uses synthetic cases by default.

## Android-friendly setup (single ZIP installer)

1. Create a **public** GitHub repository called `project-emergence-research` with an initial README. The name can differ; use the default `main` branch.
2. On its main page, **Add file → Upload files** and upload the supplied `emergence-lab.zip` file as an intact ZIP, then commit. Do *not* unzip on your phone.
3. **Add file → Create new file**. Set the *filename* to `.github/workflows/install-emergence.yml` (typing slashes creates the directories). Paste the small workflow from `INSTALL_WORKFLOW.txt` in this release, then commit.
4. Go to **Actions → Install Project Emergence Lab → Run workflow**. It unpacks the ZIP, runs tests, removes the ZIP and commits the complete project into your own repo.
5. Under **Actions → Project Emergence - Scheduled Research Cycle → Run workflow**, initiate a cycle. Open `data/latest_report.md` or `data/latest.json` to view results. Further cycles are scheduled daily.
6. Optional dashboard: upload `research-dashboard.html` to your existing **Hugging Face Static Space** without replacing `index.html`. Open that page and enter `YOUR_GITHUB_NAME/project-emergence-research` to see public results. Not needed for automation.

### If the GitHub workflow cannot commit

In your repository **Settings → Actions → General → Workflow permissions**, check whether Actions can use a write-permission token. The installer needs `contents: write` to commit the generated files. No personal access token is required. Repo/organization policy may block writes.

### If a schedule stops

Open **Actions** and re-enable the workflow if it was disabled. Scheduled runs are not 24/7 execution and are not guaranteed exactly on time. Pause the cycles by disabling the workflow, or set repo variable `EMERGENCE_PAUSED` to `true` (Settings → Secrets and variables → Actions → Variables).

## Enable optional AI-to-AI research (later; not required for $0 startup)

In GitHub repository **Settings → Secrets and variables → Actions**:

- Under **Secrets**, create `EMERGENCE_API_KEY` with the key from your chosen provider. **Never paste it in the HTML dashboard or a committed file.**
- Under **Variables**, create `EMERGENCE_API_BASE` (example for Hugging Face: `https://router.huggingface.co/v1`).
- Under **Variables**, create `EMERGENCE_MODEL` with an *actually available* compatible chat model ID for your provider. Example model IDs may change; confirm in the provider's model catalog.

With all three configured, each scheduled run makes one Director request and, if successful, one Critic request. The system archives both the proposed experiment and assessment. If a provider call fails, the run falls back to deterministic testing, reporting the failure type without printing credentials. The same underlying model can play both roles; use two model providers in a future version for stronger independence.

Provider credits and limits change, so **do not assume the Hugging Face API is free**. Start with no API key while testing the automated workflow.

## Scientific limitations and roadmap

The built-in test world is simple. Its questions and labels are generated by the code, so ceiling effects, implicit benchmarks and implementation-specific assumptions are unavoidable. No result here constitutes evidence of phenomenal consciousness.

The roadmap is empirical: (1) external, held-out challenge sets from human authors; (2) richer recurrent workspace dynamics and task-switching; (3) metacognitive calibration under distribution shift; (4) causal interventions and lesion tests; (5) independently reviewed experimental protocols; (6) only then guarded model-assisted code-proposal workflows through GitHub pull requests. Cross-world generalization and spontaneous goal persistence remain unverified.

## Commands (desktop or automated GitHub environment)

```bash
python -m unittest discover -s tests -v
python -m emergence.runner
```

See `data/latest_report.md` after the first run. The record digest connects consecutive logs by the previous-record hash, but this is **not** tamper-proof security; GitHub git history provides additional accountability.

## Security design

- Model interactions: fixed prompts; no arbitrary command execution, filesystem modifications, shell code or code-generated workflows.
- A small validated list of experimental parameter values; no write access outside `data/` in the scheduled workflow's git commit.
- API tokens appear only in GitHub secrets and job environment, not public frontend JavaScript.
- Bounded runtime (8 minutes), bounded calls (2), bounded output (~350 tokens each).
- GitHub access is controlled by you; code updates are not self-approved.
