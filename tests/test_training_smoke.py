import json

import pandas as pd
from ml.training.train import build_pipeline, save_metrics, save_model


def test_training_pipeline_smoke(tmp_path):
    X = pd.DataFrame(
        {
            "education_level": ["bachelors", "masters", "phd", "bachelors"],
            "years_experience": [2, 5, 8, 3],
            "github_activity": [10, 30, 55, 15],
        }
    )
    y = pd.Series([0, 1, 1, 0], name="is_shortlisted")

    feature_order = list(X.columns)
    pipeline = build_pipeline(
        categorical_cols=["education_level"],
        numeric_cols=["years_experience", "github_activity"],
        feature_order=feature_order,
    )

    pipeline.fit(X, y)
    predictions = pipeline.predict(X)

    save_model(pipeline, str(tmp_path))
    save_metrics({"f1": 1.0, "accuracy": 1.0}, str(tmp_path))

    assert len(predictions) == len(X)
    assert (tmp_path / "model.joblib").exists()
    assert json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))["f1"] == 1.0
