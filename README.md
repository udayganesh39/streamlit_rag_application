# streamlit_rag_model
Retrieval Augmented Generative Project with UI using streamlit

## CI/CD

- CI runs on pull requests and pushes to `dev` and `main`
- CD is configured to trigger a Render deploy only after CI succeeds on `dev`
- Automatic deployment requires the GitHub Actions secret `RENDER_DEPLOY_HOOK_URL`
- Optional post-deploy smoke testing uses the repository variable `RENDER_SERVICE_URL`

### Configure Render deployment secret

1. In GitHub, open `Settings -> Secrets and variables -> Actions`
2. Create a new repository secret named `RENDER_DEPLOY_HOOK_URL`
3. In Render, open your web service and copy its deploy hook URL
4. Paste that full hook URL into the GitHub secret value
5. Optionally create a repository variable named `RENDER_SERVICE_URL`
6. Set `RENDER_SERVICE_URL` to your live Render service URL, for example `https://your-service.onrender.com`
7. Merge PRs into `dev` only after CI is green
8. After merge, the CD workflow will trigger Render automatically and run a smoke test when `RENDER_SERVICE_URL` is set

## Local quality checks

```bash
python -m ruff format --check .
python -m ruff check .
python -m pytest
python -m py_compile main.py ui.py
```

## Pre-commit hooks

Install the hooks once per clone:

```bash
python -m pre_commit install
```

Run the hooks manually across the repository:

```bash
python -m pre_commit run --all-files
```

The pre-commit setup mirrors the local quality gate for formatting, linting, type-checking, and Python entrypoint validation before changes are committed.
