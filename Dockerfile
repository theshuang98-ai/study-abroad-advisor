FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH=/app/.venv/bin:$PATH \
    EMBEDDING_DEVICE=cpu

RUN pip install --no-cache-dir uv==0.11.23

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra local-embeddings

COPY README.md ./
COPY src ./src
COPY data ./data
COPY docs ./docs

EXPOSE 8501

CMD ["streamlit", "run", "src/study_abroad/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
