FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Numeric UID so runAsNonRoot can be verified
RUN useradd --uid 10001 --no-create-home appuser

# Dependencies before code for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

USER 10001

EXPOSE 8000

# Exec form so uvicorn runs as PID 1 and receives SIGTERM
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
