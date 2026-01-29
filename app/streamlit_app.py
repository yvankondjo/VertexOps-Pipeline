"""Simple Streamlit UI to query Vertex AI endpoint."""
from __future__ import annotations

import os
import streamlit as st
from google.cloud import aiplatform


def predict(endpoint_id: str, project: str, region: str, payload: dict) -> dict:
    aiplatform.init(project=project, location=region)
    endpoint = aiplatform.Endpoint(endpoint_id)
    response = endpoint.predict(instances=[payload])
    return response.predictions[0]


def main() -> None:
    st.title("Resume Screening Prediction")
    st.write("Enter the resume features and get a prediction from Vertex AI.")

    project = st.text_input("GCP Project", value=os.getenv("PROJECT_ID", "vertexops-pipeline"))
    region = st.text_input("Region", value=os.getenv("REGION", "europe-west1"))
    endpoint_id = st.text_input("Endpoint ID", value=os.getenv("VERTEX_ENDPOINT_ID", ""))

    st.subheader("Features")
    years_experience = st.number_input("Years of Experience", min_value=0, value=5)
    skills_match_score = st.number_input("Skills Match Score", min_value=0.0, max_value=100.0, value=75.0)
    education_level = st.selectbox("Education Level", ["High School", "Bachelors", "Masters", "PhD"])
    project_count = st.number_input("Project Count", min_value=0, value=5)
    resume_length = st.number_input("Resume Length", min_value=0, value=400)
    github_activity = st.number_input("GitHub Activity", min_value=0, value=120)

    if st.button("Predict"):
        if not endpoint_id:
            st.error("Please provide a Vertex AI Endpoint ID.")
            return

        payload = {
            "years_experience": years_experience,
            "skills_match_score": skills_match_score,
            "education_level": education_level,
            "project_count": project_count,
            "resume_length": resume_length,
            "github_activity": github_activity,
        }

        try:
            prediction = predict(endpoint_id, project, region, payload)
            st.success("Prediction received")
            st.json(prediction)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Prediction failed: {exc}")


if __name__ == "__main__":
    main()