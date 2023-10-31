FROM python:3.11.3-slim-buster

ARG $PORT=5000
ARG API_KEY="DEMO_KEY"
ARG $CACHE_TIMEOUT=24*60*60
ARG $WORKERS=4

ENV PORT=$PORT
ENV API_KEY=$API_KEY
ENV CACHE_TIMEOUT=$CACHE_TIMEOUT
ENV WORKERS=$WORKERS

EXPOSE $PORT

COPY . /app

WORKDIR /app

RUN pip install -r requirements.txt

CMD ["gunicorn", "-w", "$WORKERS", "-b", "0.0.0.0:$PORT", "apod_service:app"]
