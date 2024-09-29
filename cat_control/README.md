# ghostly-cat

# Piggy Counter

To Build the container
```
docker build -f ./Dockerfile ../ -t cat_control
```

To run the container
```
docker run -it cat_control -e BLINKA_FORCEBOARD=JETSON_NANO
```

# Detect devices
sudo i2cdetect -y -r 1

# Mosquitto needs to be installed in the host os
```
sudo apt install mosquitto mosquitto-clients
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto
sudo systemctl status mosquitto
mosquitto_sub -h localhost -t cat/telemetry
mosquitto_pub -h localhost -t cat/telemetry -m "{'centroid_x': 600, 'centroid_y': 600.0}"
```
