from __future__ import annotations
from airflow import DAG
from airflow.decorators import task
from datetime import datetime, timezone
from airflow.operators.bash import BashOperator
from jobs.ingest_resume_screening import (
    choose_source,
    download_kaggle_dataset,
    upload_to_gcs,
    ingest_in_bigquery,
    DATASET_SLUG,
)
from pathlib import Path
import os

def _run_date_and_id():
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ts_nodash = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return run_date, f"run_{ts_nodash}"

with DAG(
    dag_id="vertexops_ingest_resume_screening",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["vertexops", "ingest"],
) as dag:
    @task
    def download()->str:
        source = choose_source()
        if source == "kaggle":
            local_csv = download_kaggle_dataset(
                dataset=DATASET_SLUG,
                kaggle_json_path=Path("secrets/kaggle/kaggle.json"),
                download_path=Path("data/kaggle/_dl"),
            )
        else:
            local_csv = Path("data/sample/resume_screening_sample.csv")
        return str(local_csv)
    @task
    def upload(local_csv: str) -> str:
        project = os.environ["PROJECT_ID"]
        bucket = os.environ["GCS_BUCKET"]

        run_date, run_id = _run_date_and_id()
        gcs_path = f"raw/resume_screening/{run_date}/{run_id}/resume_screening.csv"
        gcs_uri = upload_to_gcs(project, bucket, Path(local_csv), gcs_path)
        return gcs_uri
    @task
    def load_to_bq(gcs_uri: str) -> int:
        project = os.environ["PROJECT_ID"]
        raw_ds = os.environ["BQ_RAW_DATASET"]
        bq_location = os.getenv("BQ_LOCATION", "EU")

        rows = ingest_in_bigquery(
            project_id=project,
            dataset_id=raw_ds,
            table_name="raw_resume_screening",
            gcs_uri=gcs_uri,
            location=bq_location,
        )
        return rows

    rows = load_to_bq(upload(download()))
    
    dbt_run = BashOperator(
    task_id="dbt_build_after_ingest",
    bash_command=(
        "cd /opt/airflow/project && "
        "dbt deps --project-dir dbt --profiles-dir dbt && "
        "dbt build --project-dir dbt --profiles-dir dbt"
    ),
    )

    vertex_train = BashOperator(
        task_id="vertexai_train_deploy",
        bash_command=(
            "python /opt/airflow/project/ml/training/vertex_launcher.py "
            "--project ${PROJECT_ID} "
            "--region europe-west1 "
            "--bucket ${GCS_BUCKET} "
            "--bq_table ${PROJECT_ID}.vertexops_analytics.mart_resume_features "
            "--label is_shortlisted "
            "--force_deploy"
        ),
    )


    rows >> dbt_run >> vertex_train