This repo includes a GitHub Actions CI workflow to run tests in `collab/` automatically when you push or create PRs.

How to use:
1. Push this repo to GitHub under your account/repo.
2. Navigate to the Actions tab to see the CI runs.
3. Download `pytest-report.xml` and `pytest-report.html` artifacts from the Action summary.

If you'd like a one-off run, use the workflow_dispatch option to start a run manually from Actions -> Run workflow.
