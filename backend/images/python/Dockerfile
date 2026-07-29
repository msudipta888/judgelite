FROM python:3.8-slim

RUN useradd -m -u 1001 -s /bin/bash sandboxuser

RUN mkdir -p /code && chown sandboxuser:sandboxuser /code

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    numpy \
    pandas \
    requests \
    python-dotenv

WORKDIR /code

USER sandboxuser