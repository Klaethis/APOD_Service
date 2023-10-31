FROM python:3.11.3-slim-buster

ENV PORT=5000 $PORT
ENV API_KEY="DEMO_KEY" $API_KEY
ENV CACHE_TIMEOUT=86400 $CACHE_TIMEOUT
ENV WORKERS=4 $WORKERS

EXPOSE $PORT

COPY . /app

WORKDIR /app

RUN pip install -r requirements.txt

CMD ["gunicorn", "-w", "$WORKERS", "-b", "0.0.0.0:$PORT", "apod_service:app"]
