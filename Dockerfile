FROM python:3.12.7

# -----------------------------
# System packages for Playwright
# -----------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        libnss3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpangocairo-1.0-0 \
        libpango-1.0-0 \
        libcairo2 \
        libatspi2.0-0 \
        libx11-6 \
        libxshmfence1 \
        libxext6 \
        libxfixes3 \
        libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /ott_scraper_bot

COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium
RUN playwright install --with-deps chromium

COPY . .

CMD ["python3", "poster.py"]
