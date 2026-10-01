FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-install-project

COPY ingestion ./ingestion

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "ingestion.entsoe_generation"]