import os
from dotenv import load_dotenv
from google.cloud import storage, bigquery

def must(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise ValueError(f"Missing env var: {name}")
    return v

def ensure_bucket(project_id: str, bucket_name: str, region: str):
    client = storage.Client(project=project_id)
    try:
        client.get_bucket(bucket_name)
        print(f"Bucket exists: gs://{bucket_name}")
    except Exception:
        bucket = client.bucket(bucket_name)
        bucket.location = region
        bucket.iam_configuration.uniform_bucket_level_access_enabled = True
        client.create_bucket(bucket, project=project_id)
        print(f"Created bucket: gs://{bucket_name} ({region})")

def ensure_dataset(project_id: str, dataset_id: str, location: str, description: str):
    client = bigquery.Client(project=project_id)
    ds_ref = bigquery.Dataset(f"{project_id}.{dataset_id}")
    ds_ref.location = location
    ds_ref.description = description
    try:
        client.get_dataset(ds_ref)
        print(f"Dataset exists: {project_id}:{dataset_id}")
    except Exception:
        client.create_dataset(ds_ref, exists_ok=True)
        print(f"Created dataset: {project_id}:{dataset_id} ({location})")

def main():
    load_dotenv()

    project_id = must("PROJECT_ID")
    bucket_name = must("GCS_BUCKET")
    region = os.getenv("GCS_REGION", "europe-west1")
    bq_location = os.getenv("BQ_LOCATION", "EU")
    raw_ds = os.getenv("BQ_RAW_DATASET", "vertexops_raw")
    analytics_ds = os.getenv("BQ_ANALYTICS_DATASET", "vertexops_analytics")

    ensure_bucket(project_id, bucket_name, region)
    ensure_dataset(project_id, raw_ds, bq_location, "VertexOps raw")
    ensure_dataset(project_id, analytics_ds, bq_location, "VertexOps analytics")

    print("Bootstrap OK ✅")

if __name__ == "__main__":
    main()
