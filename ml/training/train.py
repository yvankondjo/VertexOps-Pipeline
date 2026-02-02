
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import joblib
import pandas as pd
from google.cloud import storage
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier

from google.cloud import bigquery


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bq_table",
        required=True,
        help=(
            "BigQuery table to train from in the form project.dataset.table."
        ),
    )
    parser.add_argument(
        "--label",
        default="is_shortlisted",
        help="Target column name.",
    )
    parser.add_argument(
        "--model_dir",
        default=os.getenv("AIP_MODEL_DIR", "/opt/airflow/project/artifacts"),
        help="Output directory for model artifacts (local or GCS path).",
    )
    parser.add_argument(
        "--test_size",
        type=float,
        default=0.2,
        help="Test split ratio.",
    )
    parser.add_argument(
        "--bq_location",
        default=os.getenv("BQ_LOCATION", "EU"),
        help="BigQuery dataset location (EU/US).",
    )
    return parser.parse_args()


def load_training_data(table: str, location: str) -> pd.DataFrame:
    client = bigquery.Client()
    query = f"SELECT * FROM `{table}`"
    job = client.query(query, location=location)
    return job.to_dataframe(create_bqstorage_client=False)


def build_pipeline(
    categorical_cols: list[str],
    numeric_cols: list[str],
    feature_order: list[str],
) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                [feature_order.index(col) for col in categorical_cols],
            ),
            (
                "numeric",
                StandardScaler(),
                [feature_order.index(col) for col in numeric_cols],
            ),
        ]
    )

    model = RandomForestClassifier(
        random_state=42,
        class_weight="balanced",
    )

    return Pipeline(
        steps=[
            ("preprocess", preprocess),
            ("model", model),
        ]
    )


def save_metrics(metrics: dict[str, float], output_dir: str) -> None:
    if output_dir.startswith("gs://"):
        bucket_name, blob_path = output_dir[5:].split("/", 1)
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(f"{blob_path}/metrics.json")
        blob.upload_from_string(json.dumps(metrics, indent=2), content_type="application/json")
    else:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        metrics_path = path / "metrics.json"
        with metrics_path.open("w", encoding="utf-8") as handle:
            json.dump(metrics, handle, indent=2)


def save_model(model: Pipeline, output_dir: str) -> None:
    if output_dir.startswith("gs://"):
        bucket_name, blob_path = output_dir[5:].split("/", 1)
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(f"{blob_path}/model.joblib")
        blob.upload_from_string(joblib.dumps(model))
    else:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        model_path = path / "model.joblib"
        joblib.dump(model, model_path)


def main() -> None:
    args = parse_args()
    if not args.model_dir:
        raise ValueError("model_dir is required (or set AIP_MODEL_DIR)")

    df = load_training_data(args.bq_table, args.bq_location)

    if args.label not in df.columns:
        raise ValueError(f"Label column '{args.label}' not found in training data")

    if df.empty:
        raise ValueError(
            "Training data is empty. Check that mart_resume_features has rows "
            "and that the dataset/table name is correct."
        )

    df = df.dropna(subset=[args.label]).copy()

    X = df.drop(columns=[args.label])
    y = df[args.label]

    feature_order = list(X.columns)
    categorical_cols = [
        col for col in feature_order if X[col].dtype == "object" or X[col].dtype.name == "category"
    ]
    numeric_cols = [col for col in feature_order if col not in categorical_cols]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=args.test_size,
        stratify=y,
        random_state=42,
    )

    pipeline = build_pipeline(categorical_cols, numeric_cols, feature_order)

    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    metrics = {
        "accuracy": accuracy_score(y_test, preds),
        "f1": f1_score(y_test, preds),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "best_params": None,
        "cv_best_score": None,
    }

    save_model(pipeline, args.model_dir)
    save_metrics({"feature_order": feature_order}, args.model_dir)
    save_metrics(metrics, args.model_dir)

    print("Training complete. Metrics:")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()