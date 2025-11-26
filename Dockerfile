# Simple Dockerfile for collaborative editor
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

EXPOSE 5000
VOLUME ["/data"]

CMD ["python", "app.py"]
