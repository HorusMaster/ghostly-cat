ARG BASE_IMAGE=arm64v8/ubuntu:jammy

FROM ${BASE_IMAGE} as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    DEBCONF_NOWARNINGS=yes \
    TZ="America/Mexico_City" \
    ENV="dev" \
    BLINKA_FORCEBOARD="JETSON_NANO" \
    SERVICE_NAME="cat_control"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    software-properties-common

# See "Theory" notes above about why we use the deadsnakes package
RUN apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-distutils \
    python3.10-venv \
    build-essential python3-dev gcc \
    git  `# For developer container` \
    make `# For Makefile usage` \
    && apt-get clean


ENV VIRTUAL_ENV=/code/cat_control/.venv
RUN python3.10 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY cat_control/requirements.txt /code/cat_control/requirements.txt
RUN pip3 install -r /code/cat_control/requirements.txt

#COPY ./.flake8 ./pyproject.toml /code/

COPY cat_common /code/cat_common
RUN pip3 install /code/cat_common

COPY cat_control /code/cat_control/
WORKDIR /code/cat_control

CMD ["python3", "main.py"]