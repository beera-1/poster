FROM python:3.12.7

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /ott_scraper_bot

# ---------- System dependencies ----------
RUN apt-get update && apt-get install -y \
    mediainfo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---------- Python dependencies ----------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- App files ----------
COPY . .

CMD ["python3", "poster.py"]
