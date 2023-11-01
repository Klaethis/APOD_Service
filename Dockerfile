# TODO: Fix the syntax so the following works

FROM python:3.11.3-slim-buster

ARG A_PORT=5000
ARG A_API_KEY="DEMO_KEY"
ARG A_CACHE_TIMEOUT=86400
ARG A_WORKERS=4

ENV PORT=${A_PORT}
ENV API_KEY=${A_API_KEY}
ENV CACHE_TIMEOUT=${A_CACHE_TIMEOUT}
ENV WORKERS=${A_WORKERS}

EXPOSE $PORT

COPY . /app

WORKDIR /app

RUN pip install -r requirements.txt

CMD ["gunicorn", "-b", "0.0.0.0:${PORT}", "apod_service:app"]