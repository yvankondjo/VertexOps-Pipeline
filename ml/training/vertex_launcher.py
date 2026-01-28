from __future__ import annotations

import argparse
import os
from datetime import datetime

from google.cloud import aiplatform


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

    endpoint = aiplatform.Endpoint.create(
        display_name=f"{args.display_name}-endpoint"
    )
    endpoint.deploy(
        model=uploaded_model,
        deployed_model_display_name=f"{args.display_name}-deploy",
        machine_type="n1-standard-2",
        traffic_split={"0": 100},
    )


if __name__ == "__main__":
    main()