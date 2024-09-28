# ghostly-cat

# Piggy Counter

To Build the container
```
docker build -t cat_video . 
```

To run the container
```
docker run -it  --rm \
                --privileged \
                --runtime nvidia \
                --network host \
                --ipc host \
                --device /dev/video0 \
                --volume /tmp/argus_socket:/tmp/argus_socket \
                cat_video
```

# Detect devices
sudo i2cdetect -y -r 1