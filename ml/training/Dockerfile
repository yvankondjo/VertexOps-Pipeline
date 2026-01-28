FROM python:3.11-slim

WORKDIR /app

COPY ml/training/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ml /app/ml

ENTRYPOINT ["python", "-m", "ml.training.train"]