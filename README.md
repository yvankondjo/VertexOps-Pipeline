# VertexOps Pipeline

End-to-end MLOps demo that connects Airflow orchestration, dbt transformations, BigQuery storage, Vertex AI training and deployment, and a Streamlit inference UI.

![Architecture Diagram](images/Architecture.jpeg)

## What this repo demonstrates

The pipeline ingests a resume-screening dataset, transforms it into analytics and ML-ready tables, trains a scikit-learn model, and exposes predictions through a Streamlit interface backed by Vertex AI.

## Main entrypoints

```powershell
uv sync --group dev
uv run python scripts/test_ingest_e2e.py
uv run python ml/training/vertex_launcher.py --project <project> --bucket <bucket> --bq_table <project.dataset.table>
uv run streamlit run app/streamlit_app.py
```

## Environment variables

```env
PROJECT_ID=vertexops-pipeline
REGION=europe-west1
GCS_BUCKET=<bucket-name>
BQ_RAW_DATASET=vertexops_raw
BQ_LOCATION=EU
VERTEX_AI_ENDPOINT=<endpoint-id>
```

The Streamlit app also accepts `VERTEX_ENDPOINT_ID` for backward compatibility.

## Quality gates

```powershell
uv run pytest
uv run ruff check app jobs ml tests
uv run mypy
```

The CI workflow in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs:

- import and smoke tests for the Airflow DAG
- ingestion job tests with mocked GCS and BigQuery clients
- local training smoke tests
- Streamlit prediction smoke tests without cloud calls
- dbt project structure validation

## What is intentionally not claimed

This repository does not currently ship a production image-build workflow or a cloud deployment pipeline in GitHub Actions. The committed CI focuses on code quality and smoke validation that can run reliably on every push.

## Project layout

```text
airflow/         DAG and local Airflow assets
app/             Streamlit UI
dbt/             dbt project and schema contracts
jobs/            ingestion helpers for GCS and BigQuery
ml/training/     local training and Vertex AI deployment scripts
scripts/         bootstrap and end-to-end helper scripts
tests/           smoke tests and repo validation
```

## Notes

- `app/streamlit_app.py` now logs prediction events instead of printing debug payloads.
- `pyproject.toml` includes dev tooling for `pytest`, `ruff`, and `mypy`.
- The README only documents workflows that exist in the repository today.
