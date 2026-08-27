# Root convenience Dockerfile -- mirrors deployment/docker/Dockerfile.api
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY src/ src/
COPY api/ api/
COPY configs/ configs/
ENV PYTHONPATH=/app/src
EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
