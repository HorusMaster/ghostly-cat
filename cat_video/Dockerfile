ARG BASE_IMAGE=nvcr.io/nvidia/dli/dli-nano-ai:v2.0.1-r32.6.1

FROM ${BASE_IMAGE} as base

# Install required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git  `# For developer container` \
    python3-pip \
    python3-dev \
    gcc \
    gstreamer1.0-tools \
    && apt-get clean

# Upgrade pip
RUN pip3 install --upgrade pip

# Clone YOLOv5 v6.2 from GitHub
RUN git clone --branch v6.2 https://github.com/ultralytics/yolov5.git /code/yolov5

# Install your additional project dependencies
COPY requirements.txt /code/requirements.txt
RUN pip3 install --no-deps -r /code/requirements.txt

# Copy your project code to the container
COPY . /code/cat_video/

# Set the working directory
WORKDIR /code/cat_video

# Optionally, set PYTHONPATH to include YOLOv5 directory
ENV PYTHONPATH="${PYTHONPATH}:/code/yolov5"
