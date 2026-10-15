# Runs the whole portal - website, scraper and mailer - in one container.
#   docker build -t internradar .
#   docker run -p 8700:8700 -v internradar-data:/app/data internradar
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORTAL_HOST=0.0.0.0 \
    PORTAL_PORT=8700

WORKDIR /app

# Dependencies first, so a code change does not reinstall them every build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# data/ holds the database; mount a volume over it or the students disappear
# when the container is replaced.
RUN mkdir -p data && \
    adduser --disabled-password --gecos "" portal && \
    chown -R portal:portal /app
USER portal

EXPOSE 8700
HEALTHCHECK --interval=60s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8700/healthz', timeout=4).status==200 else 1)"

CMD ["python", "app.py"]
