FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

COPY pyproject.toml README.md ETL_QUICKSTART.md ./
COPY src ./src
COPY scripts ./scripts
COPY sql ./sql
COPY data ./data
COPY exploration ./exploration

RUN mkdir -p /tmp/matplotlib && pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "molecular_similarity.api:app", "--host", "0.0.0.0", "--port", "8000"]
