ARG BASE_IMAGE=nvcr.io/nvidia/l4t-ml:r32.7.1-py3

FROM ${BASE_IMAGE} as base

# Install required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git  `# For developer container` \
    python3-pip \
    python3.6-dev \
    gcc \
    gstreamer1.0-tools \
    python3-setuptools \
    python3.6-venv \
    python3-tk \
    && apt-get clean

RUN pip3 install --upgrade pip

COPY requirements.txt /code/requirements.txt
RUN pip3 install --no-deps -r /code/requirements.txt

RUN git clone --branch v6.2 https://github.com/ultralytics/yolov5.git /code/yolov5

COPY . /code/cat_video/
WORKDIR /code/cat_video

ENV PYTHONPATH="${PYTHONPATH}:/code/yolov5"
