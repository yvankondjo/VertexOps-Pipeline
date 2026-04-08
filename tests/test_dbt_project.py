from pathlib import Path

import yaml


def test_dbt_project_structure_is_consistent():
    root = Path(__file__).resolve().parents[1]
    dbt_root = root / "dbt"

    project_config = yaml.safe_load(
        (dbt_root / "dbt_project.yml").read_text(encoding="utf-8")
    )
    staging_schema = yaml.safe_load(
        (dbt_root / "models" / "staging" / "schema.yml").read_text(encoding="utf-8")
    )
    marts_schema = yaml.safe_load(
        (dbt_root / "models" / "marts" / "schema.yml").read_text(encoding="utf-8")
    )

    assert project_config["name"] == "vertexops"
    assert (dbt_root / "models" / "staging" / "stg_resume_screening.sql").exists()
    assert (dbt_root / "models" / "marts" / "mart_resume_features.sql").exists()
    assert staging_schema["models"][0]["name"] == "stg_resume_screening"
    assert marts_schema["models"][0]["name"] == "mart_resume_features"
