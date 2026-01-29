from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from google.cloud import aiplatform
from google.cloud import storage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", default="europe-west1")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--bq_table", required=True)
    parser.add_argument("--label", default="is_shortlisted")
    parser.add_argument("--display_name", default="resume-ml")
    parser.add_argument("--training_image", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    aiplatform.init(project=args.project, location=args.region, staging_bucket=args.bucket)

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    model_dir = f"gs://{args.bucket}/ml/models/{timestamp}"

    job = aiplatform.CustomContainerTrainingJob(
        display_name=f"{args.display_name}-train",
        container_uri=args.training_image,
    )

    model = job.run(
        args=[
            f"--bq_table={args.bq_table}",
            f"--label={args.label}",
            f"--model_dir={model_dir}",
        ],
        replica_count=1,
        machine_type="n1-standard-4",
        sync=True,
    )

    uploaded_model = aiplatform.Model.upload(
        display_name=f"{args.display_name}-model",
        artifact_uri=model_dir,
        serving_container_image_uri=(
            "us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-2:latest"
        ),
    )

    storage_client = storage.Client(project=args.project)
    bucket = storage_client.bucket(args.bucket)
    metrics_blob = bucket.blob(f"ml/models/{timestamp}/metrics.json")
    metrics = json.loads(metrics_blob.download_as_text())
    new_f1 = metrics.get("f1", 0.0)

    endpoints = aiplatform.Endpoint.list(
        filter=f'display_name="{args.display_name}-endpoint"'
    )
    if endpoints:
        endpoint = endpoints[0]
    else:
        endpoint = aiplatform.Endpoint.create(
            display_name=f"{args.display_name}-endpoint"
        )

    deployed_models = endpoint.list_models()
    current_f1 = None
    if deployed_models:
        current_model_id = deployed_models[0].model
        current_model = aiplatform.Model(current_model_id)
        current_metrics_path = current_model.artifact_uri
        if current_metrics_path:
            bucket_name, blob_path = current_metrics_path.replace("gs://", "").split("/", 1)
            current_blob = storage_client.bucket(bucket_name).blob(f"{blob_path}/metrics.json")
            if current_blob.exists():
                current_metrics = json.loads(current_blob.download_as_text())
                current_f1 = current_metrics.get("f1")

    should_deploy = current_f1 is None or new_f1 > float(current_f1)

    if should_deploy:
        endpoint.deploy(
            model=uploaded_model,
            deployed_model_display_name=f"{args.display_name}-deploy",
            machine_type="n1-standard-2",
            traffic_split={"0": 100},
        )
        print(f"Deployed new model (F1={new_f1}).")
    else:
        print(f"Skipped deploy. New F1={new_f1} <= current F1={current_f1}.")


if __name__ == "__main__":
    main()