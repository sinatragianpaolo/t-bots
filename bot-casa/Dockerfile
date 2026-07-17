FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libxt6 \
    libxss1 \
    libx11-xcb1 \
    libxcb-shm0 \
    libxcb1 \
    libasound2 \
    libpci3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Chrome refuses to run as root without --no-sandbox, and --no-sandbox is
# itself a giveaway to immobiliare.it's anti-bot check — so run as a normal
# user, matching the host UID that owns the bind-mounted volumes.
RUN useradd -m -u 1000 appuser
ENV HOME=/home/appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m camoufox fetch \
    && python -m playwright install --with-deps chrome \
    && chown -R appuser:appuser "$HOME"

COPY . .
RUN mkdir -p data browser_profile_chrome && chown -R appuser:appuser /app

USER appuser
CMD ["python", "main.py"]
