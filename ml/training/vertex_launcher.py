from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
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
    parser.add_argument(
        "--force_deploy",
        action="store_true",
        help="Force deployment even if metrics are unchanged.",
    )
    parser.add_argument(
        "--deploy_timeout",
        type=int,
        default=int(os.getenv("VERTEX_DEPLOY_TIMEOUT", "1800")),
        help="Timeout in seconds for Vertex AI endpoint deploy operation.",
    )
    return parser.parse_args()


def _upload_directory_to_gcs(local_dir: Path, gcs_uri: str) -> None:
    bucket_name, prefix = gcs_uri.replace("gs://", "").split("/", 1)
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    for file_path in local_dir.rglob("*"):
        if not file_path.is_file():
            continue
        relative_path = file_path.relative_to(local_dir)
        blob = bucket.blob(f"{prefix}/{relative_path.as_posix()}")
        blob.upload_from_filename(file_path)


def main() -> None:
    args = parse_args()
    aiplatform.init(project=args.project, location=args.region, staging_bucket=args.bucket)

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    local_model_dir = Path(
        os.getenv("LOCAL_MODEL_DIR", "/opt/airflow/project/artifacts")
    ) / timestamp
    local_model_dir.mkdir(parents=True, exist_ok=True)
    gcs_model_dir = f"gs://{args.bucket}/ml/models/{timestamp}"

    train_script = Path(__file__).parent / "train.py"
    subprocess.run(
        [
            sys.executable,
            str(train_script),
            f"--bq_table={args.bq_table}",
            f"--label={args.label}",
            f"--model_dir={local_model_dir}",
            f"--bq_location={os.getenv('BQ_LOCATION', 'EU')}",
        ],
        check=True,
    )

    _upload_directory_to_gcs(local_model_dir, gcs_model_dir)

    uploaded_model = aiplatform.Model.upload(
        display_name=f"{args.display_name}-model",
        artifact_uri=gcs_model_dir,
        serving_container_image_uri=(
            "us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-2:latest"
        ),
    )

    metrics_path = local_model_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
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
        current_metrics_path = getattr(current_model, "artifact_uri", None)
        if current_metrics_path is None and getattr(current_model, "_gca_resource", None):
            current_metrics_path = getattr(current_model._gca_resource, "artifact_uri", None)
        if current_metrics_path:
            bucket_name, blob_path = current_metrics_path.replace("gs://", "").split("/", 1)
            current_blob = storage.Client().bucket(bucket_name).blob(
                f"{blob_path}/metrics.json"
            )
            if current_blob.exists():
                current_metrics = json.loads(current_blob.download_as_text())
                current_f1 = current_metrics.get("f1")

    should_deploy = args.force_deploy or current_f1 is None or new_f1 > float(current_f1)

    if should_deploy:
        deploy_op = endpoint.deploy(
            model=uploaded_model,
            deployed_model_display_name=f"{args.display_name}-deploy",
            machine_type="n1-standard-2",
            traffic_split={"0": 100},
            sync=False,
        )
        operation_name = None
        if deploy_op is not None and getattr(deploy_op, "operation", None):
            operation_name = deploy_op.operation.name
            print(
                "Deploy operation started. "
                f"Operation: {operation_name} | "
                f"Endpoint: {endpoint.resource_name}"
            )
        else:
            print(
                "Deploy operation started (async). "
                "Operation name not available from SDK response. "
                f"Endpoint: {endpoint.resource_name}"
            )
        try:
            if deploy_op is not None:
                deploy_op.wait(timeout=args.deploy_timeout)
            else:
                print(
                    "No deploy operation handle returned by SDK; "
                    "unable to wait programmatically."
                )
        except TimeoutError as exc:
            guidance = ""
            if operation_name:
                guidance = (
                    " You can inspect it with: "
                    f"gcloud ai operations describe {operation_name.split('/')[-1]} "
                    f"--project={args.project} --region={args.region}"
                )
            print(
                "Deploy operation timed out after "
                f"{args.deploy_timeout}s.{guidance}"
            )
            raise TimeoutError(
                "Vertex AI deploy still running after timeout."
            ) from exc
        print(f"Deployed new model (F1={new_f1}).")
    else:
        print(f"Skipped deploy. New F1={new_f1} <= current F1={current_f1}.")


if __name__ == "__main__":
    main()