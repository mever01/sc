FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HEADLESS=true

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY main.py ./

RUN pip install --no-cache-dir .

ENTRYPOINT ["sc"]
CMD ["run"]
