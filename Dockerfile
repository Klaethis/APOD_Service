# TODO: Fix the syntax so the following works

FROM python:3.11.3-slim-buster

ENV API_KEY="DEMO_KEY"
ENV CACHE_TIMEOUT=86400
ENV WORKERS=4
ENV ENABLE_CONFIG="false"

EXPOSE 5000

COPY . /app

WORKDIR /app

RUN pip install -r requirements.txt

CMD ["gunicorn", "-c", "./Config/gunicorn.py", "apod_service:app"]