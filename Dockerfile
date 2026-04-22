FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /app

COPY pyproject.toml README.md ETL_QUICKSTART.md ./
COPY src ./src
COPY scripts ./scripts
COPY sql ./sql
COPY data ./data
COPY exploration ./exploration

RUN pip install --no-cache-dir .

CMD ["molecular-similarity-sql-activity-model", "./data/chembl_modeling.csv", "--reports-dir", "./exploration/reports"]
