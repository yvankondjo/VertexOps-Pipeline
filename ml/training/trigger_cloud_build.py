"""Trigger Cloud Build to build/push the training image.

Uploads the repo snapshot to GCS then invokes Cloud Build with a config file.
"""
from __future__ import annotations

import argparse
import io
import tarfile
from datetime import datetime
from pathlib import Path

from google.cloud import storage
from google.cloud.devtools import cloudbuild_v1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--image_uri", required=True)
    parser.add_argument("--staging_bucket", required=True)
    parser.add_argument(
        "--config",
        default="ml/training/cloudbuild.yaml",
        help="Path to cloudbuild.yaml in the repo.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = cloudbuild_v1.CloudBuildClient()

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    object_name = f"ml/source/source-{timestamp}.tar.gz"

    storage_client = storage.Client(project=args.project)
    bucket = storage_client.bucket(args.staging_bucket)
    blob = bucket.blob(object_name)

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        root = Path(".").resolve()
        for path in root.rglob("*"):
            if ".venv" in path.parts or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            tar.add(path, arcname=path.relative_to(root))
    buffer.seek(0)
    blob.upload_from_file(buffer, content_type="application/gzip")

    build = cloudbuild_v1.Build(
        source=cloudbuild_v1.Source(
            storage_source=cloudbuild_v1.StorageSource(
                bucket=args.staging_bucket,
                object_=object_name,
            )
        ),
        substitutions={"_IMAGE_URI": args.image_uri},
    )

    operation = client.create_build(
        project_id=args.project,
        build=build,
        parent=f"projects/{args.project}/locations/global",
        build_id=None,
    )
    operation.result()


if __name__ == "__main__":
    main()