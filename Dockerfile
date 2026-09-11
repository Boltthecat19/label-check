FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng libgl1 libglib2.0-0 fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 labelcheck
WORKDIR /srv/labelcheck

COPY pyproject.toml ./
COPY labelcheck ./labelcheck
COPY app ./app
COPY tools ./tools
RUN pip install --no-cache-dir . \
 && chown -R labelcheck:labelcheck /srv/labelcheck

USER labelcheck
EXPOSE 8081
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
