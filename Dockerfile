# Use Python 3.12 slim as the base
FROM python:3.12.7-slim

# Install system dependencies
# We add build-essential and python3-dev to fix the 'gcc' error
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    wget \
    ca-certificates \
    # Compilers needed for tgcrypto
    build-essential \
    python3-dev \
    # Chrome/Puppeteer dependencies
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    --no-install-recommends \
    # Install Node.js 20.x
    && curl -sL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ott_scraper_bot

# 1. Install Python requirements (gcc is now available to build tgcrypto)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Install Node requirements for your link fetcher
COPY package*.json ./
RUN npm install

# 3. Copy the rest of your files
COPY . .

# 4. Create a startup script to run the Python bot and Node API together
RUN echo "#!/bin/bash\npython3 poster.py &\nnode index.js" > start.sh
RUN chmod +x start.sh

# Expose the port used by index.js
EXPOSE 8000
CMD ["./start.sh"]
