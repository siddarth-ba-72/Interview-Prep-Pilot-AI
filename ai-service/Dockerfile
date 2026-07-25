FROM python:3.12-slim
WORKDIR /app

# Install dependencies from pyproject.toml (no dev extras)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application source
COPY app/ ./app

# Allow intra-package imports (e.g. `from config import settings`) to resolve
ENV PYTHONPATH=/app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
