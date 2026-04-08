from types import SimpleNamespace

import app.streamlit_app as streamlit_app


def test_predict_uses_vertex_endpoint(monkeypatch):
    captured = {}

    class FakeEndpoint:
        def __init__(self, endpoint_id: str):
            captured["endpoint_id"] = endpoint_id

        def predict(self, instances):
            captured["instances"] = instances
            return SimpleNamespace(predictions=[0.87])

    fake_aiplatform = SimpleNamespace(
        init=lambda project, location: captured.update({"project": project, "region": location}),
        Endpoint=FakeEndpoint,
    )

    monkeypatch.setattr(streamlit_app, "aiplatform", fake_aiplatform)

    prediction = streamlit_app.predict(
        endpoint_id="endpoint-123",
        project="vertexops",
        region="europe-west1",
        payload=[5, 80.0, "masters", 4, 500, 200],
    )

    assert prediction == 0.87
    assert captured["project"] == "vertexops"
    assert captured["region"] == "europe-west1"
    assert captured["endpoint_id"] == "endpoint-123"
    assert captured["instances"] == [[5, 80.0, "masters", 4, 500, 200]]
