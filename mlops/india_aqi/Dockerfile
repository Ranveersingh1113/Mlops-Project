FROM python:3.12-slim
WORKDIR /app
COPY requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt && useradd --uid 10001 --create-home appuser
COPY app.py pipeline.py observations.py dashboard.html ./
ARG MODEL_RUN
COPY artifacts/${MODEL_RUN}/ /app/model/
ENV MODEL_DIR=/app/model PORT=8080 PYTHONUNBUFFERED=1
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=4)"
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
