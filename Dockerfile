FROM python:3.12-slim

LABEL org.opencontainers.image.title="Diskoteket" \
      org.opencontainers.image.description="Egen film-, serie- och musiksamling med streckkodsskanning (vibecodat – skrivet av Claude AI)" \
      org.opencontainers.image.source="https://github.com/claudemicro222-cmd/diskoteket"

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY entrypoint.sh /entrypoint.sh
# Ta bort ev. Windows-radslut så att skriptet alltid går att köra
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

ENV CONFIG_DIR=/config \
    PUID=99 \
    PGID=100 \
    UMASK=002 \
    HOME=/tmp \
    PYTHONUNBUFFERED=1
VOLUME /config
EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=4)" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
