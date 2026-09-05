FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user - the previous image ran as root by default,
# which is unnecessary privilege for a process that only needs to read
# its own code and talk to the database over the network.
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# No --reload here: file-watching and auto-restart are a development
# convenience, not something a production container should do (it adds
# overhead and can mask crashes as "just reloading"). Local dev can
# still get hot-reload by overriding this command in docker-compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
