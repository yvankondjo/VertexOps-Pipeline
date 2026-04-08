import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery, storage

DATASET_SLUG = "sonalshinde123/ai-driven-resume-screening-dataset"

def choose_source() -> str:
    kaggle_key = Path("secrets/kaggle/kaggle.json")
    return "kaggle" if kaggle_key.exists() else "sample"


def download_kaggle_dataset(dataset: str, kaggle_json_path: Path, download_path: Path) -> Path:
    if not kaggle_json_path.exists():
        raise FileNotFoundError(f"Missing Kaggle key: {kaggle_json_path}")

    os.environ["KAGGLE_CONFIG_DIR"] = str(kaggle_json_path.parent.resolve())
    from kaggle.api.kaggle_api_extended import KaggleApi

    download_path.mkdir(parents=True, exist_ok=True)

    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files(dataset, path=str(download_path), unzip=True)

    csvs = list(download_path.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError("No CSV found after Kaggle download.")

    largest = max(csvs, key=lambda p: p.stat().st_size)
    final = Path("data/tmp/resume_screening.csv")
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(largest, final)
    return final


def upload_to_gcs(project_id: str, bucket_name: str, local_file: Path, gcs_path: str) -> str:
    if not local_file.exists():
        raise FileNotFoundError(f"Local file not found: {local_file}")

    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(str(local_file)) 
    return f"gs://{bucket_name}/{gcs_path}"


def ingest_in_bigquery(
    project_id: str,
    dataset_id: str,
    table_name: str,
    gcs_uri: str,
    location: str = "EU",
) -> int:
    client = bigquery.Client(project=project_id)

    table_id = f"{project_id}.{dataset_id}.{table_name}"  
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    load_job = client.load_table_from_uri(
        gcs_uri,
        table_id,
        job_config=job_config,
        location=location,
    )
    load_job.result()

    return client.get_table(table_id).num_rows


def make_run_context() -> tuple[str, str]:
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ts_nodash = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = f"run_{ts_nodash}"
    return run_date, run_id
