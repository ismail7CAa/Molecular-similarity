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

CMD ["python", "scripts/generate_pipeline_figure.py"]
