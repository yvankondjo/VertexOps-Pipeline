import re
from types import SimpleNamespace

import jobs.ingest_resume_screening as ingest


def test_choose_source_switches_between_sample_and_kaggle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert ingest.choose_source() == "sample"

    kaggle_dir = tmp_path / "secrets" / "kaggle"
    kaggle_dir.mkdir(parents=True)
    (kaggle_dir / "kaggle.json").write_text("{}", encoding="utf-8")

    assert ingest.choose_source() == "kaggle"


def test_upload_and_bigquery_ingest_use_expected_clients(tmp_path, monkeypatch):
    local_file = tmp_path / "resume_screening.csv"
    local_file.write_text("candidate_id,score\n1,0.9\n", encoding="utf-8")

    uploaded = {}
    load_calls = {}

    class FakeBlob:
        def __init__(self, gcs_path: str):
            self.gcs_path = gcs_path

        def upload_from_filename(self, filename: str) -> None:
            uploaded["filename"] = filename
            uploaded["gcs_path"] = self.gcs_path

    class FakeBucket:
        def blob(self, gcs_path: str) -> FakeBlob:
            return FakeBlob(gcs_path)

    class FakeStorageClient:
        def bucket(self, bucket_name: str) -> FakeBucket:
            uploaded["bucket_name"] = bucket_name
            return FakeBucket()

    class FakeLoadJob:
        def result(self) -> None:
            load_calls["completed"] = True

    class FakeBigQueryClient:
        def load_table_from_uri(self, gcs_uri, table_id, job_config=None, location=None):
            load_calls["gcs_uri"] = gcs_uri
            load_calls["table_id"] = table_id
            load_calls["location"] = location
            load_calls["job_config"] = job_config
            return FakeLoadJob()

        def get_table(self, table_id):
            load_calls["get_table"] = table_id
            return SimpleNamespace(num_rows=17)

    fake_bigquery = SimpleNamespace(
        Client=lambda project=None: FakeBigQueryClient(),
        LoadJobConfig=lambda **kwargs: kwargs,
        SourceFormat=SimpleNamespace(CSV="CSV"),
        WriteDisposition=SimpleNamespace(WRITE_TRUNCATE="WRITE_TRUNCATE"),
    )

    monkeypatch.setattr(
        ingest,
        "storage",
        SimpleNamespace(Client=lambda project=None: FakeStorageClient()),
    )
    monkeypatch.setattr(ingest, "bigquery", fake_bigquery)

    gcs_uri = ingest.upload_to_gcs("vertexops", "bucket-demo", local_file, "raw/demo.csv")
    rows = ingest.ingest_in_bigquery(
        project_id="vertexops",
        dataset_id="vertexops_raw",
        table_name="raw_resume_screening",
        gcs_uri=gcs_uri,
        location="EU",
    )

    assert gcs_uri == "gs://bucket-demo/raw/demo.csv"
    assert uploaded["filename"] == str(local_file)
    assert uploaded["bucket_name"] == "bucket-demo"
    assert rows == 17
    assert load_calls["table_id"] == "vertexops.vertexops_raw.raw_resume_screening"


def test_make_run_context_returns_expected_format():
    run_date, run_id = ingest.make_run_context()

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", run_date)
    assert re.fullmatch(r"run_\d{8}T\d{6}", run_id)
