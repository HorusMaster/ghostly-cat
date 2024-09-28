ARG BASE_IMAGE=nvcr.io/nvidia/l4t-ml:r32.7.1-py3

FROM ${BASE_IMAGE} as base

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git  `# For developer container` \
    python3-pip \
    python3.6-dev \
    gcc \
    gstreamer1.0-tools \
    libfreetype6-dev \
    python3-setuptools \
    python3.6-venv \
    python3-tk \
    && apt-get clean

RUN apt-get remove -y python3-yaml

RUN pip3 install --upgrade pip

COPY requirements.txt /code/requirements.txt
RUN pip3 install --no-deps -r /code/requirements.txt

RUN git clone https://github.com/deepcam-cn/yolov5-face.git /code/yolov5
ENV PYTHONPATH="${PYTHONPATH}:/code/yolov5"

COPY . /code/cat_video/
WORKDIR /code/cat_video


