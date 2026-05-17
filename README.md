# streamlit_rag_model
Retrieval Augmented Generative Project with UI using streamlit

## CI/CD

- CI runs on pull requests and pushes to `dev` and `main`
- CD is configured to trigger a Render deploy only after CI succeeds on `dev`
- Automatic deployment requires the GitHub Actions secret `RENDER_DEPLOY_HOOK_URL`

### Configure Render deployment secret

1. In GitHub, open `Settings -> Secrets and variables -> Actions`
2. Create a new repository secret named `RENDER_DEPLOY_HOOK_URL`
3. In Render, open your web service and copy its deploy hook URL
4. Paste that full hook URL into the GitHub secret value
5. Merge PRs into `dev` only after CI is green
6. After merge, the CD workflow will trigger Render automatically

## Local quality checks

```bash
python -m ruff format --check .
python -m ruff check .
python -m pytest
python -m py_compile main.py ui.py
```
