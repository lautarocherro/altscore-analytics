FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code (no credentials!)
COPY analysis/ analysis/
COPY pages/ pages/
COPY .streamlit/config.toml .streamlit/config.toml
COPY streamlit_app.py .

# Streamlit config: headless, port 8080, no CORS (Cloud Run terminates TLS)
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8080

CMD ["streamlit", "run", "streamlit_app.py"]
