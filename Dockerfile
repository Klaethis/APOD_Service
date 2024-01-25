# TODO: Fix the syntax so the following works

FROM python:3.11.3-slim-buster

ENV API_KEY="DEMO_KEY"
ENV CACHE_TIMEOUT=86400
ENV WORKERS=4

ENV OAUTH_CLIENT_ID=""
ENV OAUTH_CLIENT_SECRET=""

ENV CONFIG_PATH="Config/config.json"

EXPOSE 5000

COPY . /app

WORKDIR /app

RUN pip install -r requirements.txt

CMD ["gunicorn", "--preload", "-c", "./Config/gunicorn.py", "apod_service:app"]