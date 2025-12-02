FROM python:3.12-slim

WORKDIR /ott_scraper_bot

# Install dependencies for Playwright + GCC for TgCrypto
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates \
    build-essential \
    gcc \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libasound2 libpangocairo-1.0-0 libgtk-3-0 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium for Playwright
RUN python3 -m playwright install chromium

COPY . .

CMD ["python3", "poster.py"]
