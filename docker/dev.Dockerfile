# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

RUN --mount=type=cache,target=/var/cache/apt \
    apt update \
    && apt install --yes binutils build-essential \
      pkg-config ca-certificates libssl-dev libpq-dev clang lld git \
      nodejs npm vim curl \
    && rm -rf /var/lib/{apt,dpkg,cache,log}

RUN --mount=type=cache,target=/root/.cache/pip pip install poetry
RUN pip install poetry
RUN poetry config virtualenvs.create false

ENV APP_HOME /reframe

RUN npm install -g nodemon

RUN git clone https://github.com/peterwnjenga/reframe.git --depth 1

WORKDIR $APP_HOME

RUN poetry install --no-dev

# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
CMD uvicorn reframe.server.main:app