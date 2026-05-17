# streamlit_rag_model
Retrieval Augmented Generative Project with UI using streamlit

## CI/CD

- CI runs on pull requests and pushes to `dev` and `main`
- CD is configured to trigger a Render deploy on pushes to `dev`
- Automatic deployment requires the GitHub Actions secret `RENDER_DEPLOY_HOOK_URL`

## Local quality checks

```bash
python -m ruff format --check .
python -m ruff check .
python -m pytest
python -m py_compile main.py ui.py
```
