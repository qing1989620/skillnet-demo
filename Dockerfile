FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home --uid 10001 skillnet \
    && mkdir -p /app/data /app/out \
    && chown -R skillnet:skillnet /app
USER skillnet
EXPOSE 8848
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8848/api/health', timeout=3)"
CMD ["python", "run.py", "--host", "0.0.0.0", "--no-browser"]
