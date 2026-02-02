# VertexOps Pipeline

## Overview
End-to-end data + ML pipeline using **Airflow**, **dbt**, **BigQuery**, **Vertex AI**, and **Looker**.

---

## Architecture — Data + MLOps (End-to-End)

```mermaid
flowchart LR
  U["User"] --> UI["PC / Streamlit UI"];

  %% CI/CD container build
  GH["GitHub Actions\nBuild & Push Image"] --> AR["Artifact Registry"];

  subgraph MED["Medallion Architecture (Ingestion + ELT)"]
    K["Kaggle API\nResume Dataset"] --> G["GCS Bucket (Raw)"];
    G --> AQ["Airflow Ingestion"];
    AQ --> BQ1["BigQuery Bronze (raw)"];
    BQ1 --> DBT1["dbt Staging (Silver)"];
    DBT1 --> DBT2["dbt Marts (Gold)"];
  end

  %% Two downstream tables
  DBT2 --> BQ_LOOK["Looker Table (BigQuery)"];
  DBT2 --> BQ_ML["ML Training Table (BigQuery)"];

  subgraph MLS["ML Training + Serving"]
    BQ_ML --> LOCAL["Local Training"];
    LOCAL --> VTX["Vertex AI Training"];
    AR --> VTX;
    VTX --> REG["Model Registry"];
    REG --> EP["Vertex AI Endpoint"];
    EP --> UI;
  end

  subgraph CONS["Consumption"]
    BQ_LOOK --> LOOK["Looker Dashboard"];
    UI --> LOOK;
  end

  %% Styling
  classDef gcp fill:#E8F0FE,stroke:#1A73E8,stroke-width:1px,color:#174EA6;
  classDef dbt fill:#FFF3E0,stroke:#F57C00,stroke-width:1px,color:#E65100;
  classDef airflow fill:#E3F2FD,stroke:#1E88E5,stroke-width:1px,color:#0D47A1;
  classDef ui fill:#FCE4EC,stroke:#D81B60,stroke-width:1px,color:#880E4F;
  classDef neutral fill:#F5F5F5,stroke:#9E9E9E,stroke-width:1px,color:#424242;

  class G,BQ1,BQ_LOOK,BQ_ML,VTX,REG,EP,AR gcp;
  class DBT1,DBT2 dbt;
  class AQ airflow;
  class UI,LOOK ui;
  class U,LOCAL,GH,K neutral;
```

### Medallion Layers
- **Bronze (raw)**: `raw_resume_screening`
- **Silver (staging)**: `stg_resume_screening`
- **Gold (marts)**: `mart_resume_features`

---

## CI/CD — GitHub Actions
- Build & push training image to Artifact Registry.
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

---

## Orchestration — Airflow
Pipeline:
```
ingest → dbt build → vertexai train/deploy
```

The training task uses the pre-built image from Artifact Registry.

---

## Training + Deployment — Vertex AI
`ml/training/vertex_launcher.py`:
- launches a Custom Container training job
- uploads model to Model Registry
- deploys the model to an endpoint

**Promotion rule:** deploy only if the new model is better (F1).

---

## Streamlit Demo (coming)
Run the app to test predictions:

```powershell
uv sync
uv run streamlit run app/streamlit_app.py
```

Set environment variables (optional):
```
PROJECT_ID=vertexops-pipeline
REGION=europe-west1
VERTEX_ENDPOINT_ID=<your-endpoint-id>
```

---

## Diagram as interactive image
You can render Mermaid diagrams into images with:
- [Mermaid Live Editor](https://mermaid.live/)
- VS Code extension: **Mermaid Preview**

---

If you need WIF setup commands or the promotion logic, ask and I’ll provide them.