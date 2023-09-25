# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

RUN --mount=type=cache,target=/var/cache/apt \
    apt update \
    && apt install --yes binutils build-essential \
      pkg-config ca-certificates libssl-dev libpq-dev wget jq curl clang lld git vim \
    && rm -rf /var/lib/{apt,dpkg,cache,log}