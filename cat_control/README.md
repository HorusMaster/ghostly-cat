# ghostly-cat

# Piggy Counter

To Build the container
```
docker build -f ./Dockerfile ../ -t cat_control
```

To run the container
```
docker run -it cat_control
```

# Detect devices
sudo i2cdetect -y -r 1

# Mosquitto needs to be installed in the host os
```
sudo apt install mosquitto mosquitto-clients
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto
sudo systemctl status mosquitto
mosquitto_sub -h localhost -t test/topic
mosquitto_pub -h localhost -t test/topic -m "Hola desde MQTT"
```
