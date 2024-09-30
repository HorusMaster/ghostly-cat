# ghostly-cat

# Piggy Counter

To Build the container
```
cd ~/ghostly-cat/cat_video
docker build -f ./Dockerfile ../ -t cat_video
```

To run the container
```
docker run -it  --rm \
                --privileged \
                --shm-size 16gb \
                --runtime nvidia \
                --network host \
                --gpus=all \
                --ipc=host \
                --device /dev/video0 \
                --volume /tmp/argus_socket:/tmp/argus_socket \
                cat_video
```


# Detect devices
sudo i2cdetect -y -r 1


# Dev container
python3 detect_face.py --weights "models/yolov5n-face.pt"
python3 detect_face.py --weights "models/yolov5n-face.pt" --source "images/zidane.jpg" --view-img


gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! 'video/x-raw(memory:NVMM), width=1920, height=1080, format=NV12, framerate=30/1' ! nvoverlaysink


Failed to add /run/systemd/ask-password to directory watch: No space left on device

sudo -i
echo 1048576 > /proc/sys/fs/inotify/max_user_watches
exit

# notes

Check /code/yolov5/detect_face.py for more details