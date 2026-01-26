# Step 1: Use Python as the base
FROM python:3.12.7-slim

# Step 2: Install Node.js, NPM, and Chrome dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -sL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y \
    nodejs \
    wget \
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
    && rm -rf /var/lib/apt/lists/*

# Step 3: Setup Work Directory
WORKDIR /ott_scraper_bot

# Step 4: Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Install Node.js Dependencies for Puppeteer
COPY package*.json ./
RUN npm install

# Step 6: Copy all files
COPY . .

# Step 7: Expose Port (for the Express API)
EXPOSE 3000

# Step 8: Start the App
# Note: Since you have both, you might need a process manager like PM2 
# or a shell script to run both poster.py and index.js at once.
CMD ["node", "index.js"]
