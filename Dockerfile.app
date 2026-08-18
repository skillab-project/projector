FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /workspace

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

COPY app ./app
COPY complementary_data ./complementary_data
COPY pyproject.toml README.md ./

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
