
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
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
        required=True,
        help="Output directory for model artifacts (local or GCS path).",
    )
    parser.add_argument(
        "--test_size",
        type=float,
        default=0.2,
        help="Test split ratio.",
    )
    return parser.parse_args()


def load_training_data(table: str) -> pd.DataFrame:
    client = bigquery.Client()
    query = f"SELECT * FROM `{table}`"
    return client.query(query).to_dataframe()


def build_pipeline(categorical_cols: list[str], numeric_cols: list[str]) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                categorical_cols,
            ),
            (
                "numeric",
                StandardScaler(),
                numeric_cols,
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


def save_metrics(metrics: dict[str, float], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "metrics.json"
    with metrics_path.open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)


def main() -> None:
    args = parse_args()
    df = load_training_data(args.bq_table)

    if args.label not in df.columns:
        raise ValueError(f"Label column '{args.label}' not found in training data")

    df = df.dropna(subset=[args.label]).copy()

    X = df.drop(columns=[args.label])
    y = df[args.label]

    categorical_cols = [
        col for col in X.columns if X[col].dtype == "object" or X[col].dtype.name == "category"
    ]
    numeric_cols = [col for col in X.columns if col not in categorical_cols]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=args.test_size,
        stratify=y,
        random_state=42,
    )

    pipeline = build_pipeline(categorical_cols, numeric_cols)

    param_grid = {
        "model__n_estimators": [100, 200, 300],
        "model__max_depth": [None, 10, 20],
        "model__min_samples_split": [2, 5, 10],
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    grid_search = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        cv=cv,
        scoring="f1",
        n_jobs=-1,
    )
    grid_search.fit(X_train, y_train)

    best_model = grid_search.best_estimator_
    preds = best_model.predict(X_test)
    metrics = {
        "accuracy": accuracy_score(y_test, preds),
        "f1": f1_score(y_test, preds),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "best_params": grid_search.best_params_,
        "cv_best_score": grid_search.best_score_,
    }

    output_dir = Path(args.model_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.joblib"
    joblib.dump(best_model, model_path)
    save_metrics(metrics, output_dir)

    print("Training complete. Metrics:")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()