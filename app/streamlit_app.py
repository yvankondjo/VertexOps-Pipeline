"""Simple Streamlit UI to query Vertex AI endpoint."""
from __future__ import annotations

import logging
import os
from typing import cast

import streamlit as st
from dotenv import load_dotenv
from google.cloud import aiplatform

logger = logging.getLogger(__name__)


def predict(
    endpoint_id: str,
    project: str,
    region: str,
    payload: list[object],
) -> float | int | str:
    aiplatform.init(project=project, location=region)
    endpoint = aiplatform.Endpoint(endpoint_id)
    response = endpoint.predict(instances=[payload])
    return cast(float | int | str, response.predictions[0])


def main() -> None:
    load_dotenv()
    st.set_page_config(page_title="VertexOps Resume Screening", page_icon="🧠", layout="centered")
    st.title("🧠 VertexOps Resume Screening")
    st.caption("✨ Predict candidate fit with Vertex AI")
    st.write("Enter the resume features below to get a live prediction.")

    project = os.getenv("PROJECT_ID", "vertexops-pipeline")
    region = os.getenv("REGION", "europe-west1")
    endpoint_id = os.getenv("VERTEX_AI_ENDPOINT") or os.getenv("VERTEX_ENDPOINT_ID", "")

    st.subheader("📄 Resume Features")
    col1, col2 = st.columns(2)
    with col1:
        years_experience = st.number_input("Years of Experience", min_value=0, value=5)
        skills_match_score = st.number_input(
            "Skills Match Score",
            min_value=0.0,
            max_value=100.0,
            value=75.0,
        )
        education_level = st.selectbox(
            "Education Level",
            ["High School", "Bachelors", "Masters", "PhD"],
        )
    with col2:
        project_count = st.number_input("Project Count", min_value=0, value=5)
        resume_length = st.number_input("Resume Length", min_value=0, value=400)
        github_activity = st.number_input("GitHub Activity", min_value=0, value=120)

    if st.button("🚀 Predict"):
        if not endpoint_id:
            st.error("Missing Vertex AI endpoint. Set VERTEX_AI_ENDPOINT in .env.")
            return

        payload = [
            years_experience,
            skills_match_score,
            education_level.lower(),
            project_count,
            resume_length,
            github_activity,
        ]

        try:
            prediction = predict(endpoint_id, project, region, payload)
            logger.info("Received prediction from Vertex AI endpoint %s", endpoint_id)
            st.success("✅ Prediction received")
            label = "✅ Shortlisted" if float(prediction) >= 0.5 else "❌ Not Shortlisted"
            st.metric("Prediction", prediction)
            st.write(label)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Prediction failed: {exc}")


if __name__ == "__main__":
    main()
