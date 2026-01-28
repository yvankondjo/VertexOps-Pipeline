import os
from pathlib import Path
from dotenv import load_dotenv

from jobs.ingest_resume_screening import (
    choose_source,
    download_kaggle_dataset,
    upload_to_gcs,
    ingest_in_bigquery,
    make_run_context,
    DATASET_SLUG,
)

def main():
    load_dotenv()

    project = os.environ["PROJECT_ID"]
    bucket = os.environ["GCS_BUCKET"]
    raw_ds = os.environ["BQ_RAW_DATASET"]
    bq_location = os.getenv("BQ_LOCATION", "EU")

    run_date, run_id = make_run_context()

    source = choose_source()
    if source == "kaggle":
        local_csv = download_kaggle_dataset(
            dataset=DATASET_SLUG,
            kaggle_json_path=Path("secrets/kaggle/kaggle.json"),
            download_path=Path("data/kaggle/_dl"),
        )
    else:
        local_csv = Path("data/sample/resume_screening_sample.csv")

    gcs_path = f"raw/resume_screening/{run_date}/{run_id}/resume_screening.csv"
    gcs_uri = upload_to_gcs(project, bucket, local_csv, gcs_path)
    print("GCS:", gcs_uri)

    rows = ingest_in_bigquery(
        project_id=project,
        dataset_id=raw_ds,
        table_name="raw_resume_screening",
        gcs_uri=gcs_uri,
        location=bq_location,
    )
    print("BQ rows:", rows)
    print("DONE ✅")

if __name__ == "__main__":
    main()
