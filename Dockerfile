FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .
COPY CHANGELOG.md .

# Leserechte für alle App-Dateien sicherstellen, egal mit welchen Rechten sie auf dem Host liegen
RUN chmod -R a+rX /app \
 && useradd --system --uid 1000 --home /app uvv \
 && mkdir -p /data && chown uvv:uvv /data
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Commit, aus dem das Image gebaut wurde (setzt der GitHub-Workflow, erscheint auf der Seite „Über“)
ARG APP_COMMIT=""
ENV APP_COMMIT=${APP_COMMIT}

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--no-control-socket", "app:app"]
