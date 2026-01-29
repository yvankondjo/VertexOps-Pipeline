# VertexOps Pipeline

## MLOps flow (GitHub Actions + Airflow + Vertex AI)

### 1) CI/CD — GitHub Actions
- Build & push the training image to Artifact Registry.
- Workflow: `.github/workflows/build-training-image.yml`

Reproducible setup (run once):
```powershell
pwsh scripts/bootstrap_mlops_ci_cd.ps1 -ProjectId vertexops-pipeline
```

Image URI (example):
```
europe-west1-docker.pkg.dev/vertexops-pipeline/ml-training/resume-ml-trainer:latest
```

Required GitHub secrets:
- `GCP_WIF_PROVIDER`
- `GCP_SERVICE_ACCOUNT`

### 2) Orchestration — Airflow
Airflow runs:
```
ingest → dbt build → vertexai train/deploy
```

The training task uses the pre-built image from Artifact Registry.

### 3) Training + Deployment — Vertex AI
`ml/training/vertex_launcher.py`:
- launches a Custom Container training job
- uploads model to Model Registry
- deploys the model to an endpoint

### 4) Best practice (model promotion)
For production:
- store metrics from each training run
- deploy **only if better** than the current model

---

If you need WIF setup commands or the promotion logic, ask and I’ll provide them.