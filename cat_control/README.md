# ghostly-cat

# Piggy Counter

To Build the container
```
docker build -f ./Dockerfile ../ -t cat_control
```

To run the container
```
docker run  -it --rm \
            --privileged \
            --network host \
            -e BLINKA_FORCEBOARD=JETSON_NANO \
            --device /dev/i2c-1 \
            cat_control

docker run -it --rm \
    --privileged \
    --network host \
    -e BLINKA_FORCEBOARD=JETSON_NANO \
    --device /dev/i2c-1 \
    --device /dev/snd \
    -v /run/user/1003/pulse:/run/user/1003/pulse \
    -v /usr/share/sounds/alsa:/usr/share/sounds/alsa \
    -e PULSE_SERVER=unix:/run/user/1003/pulse/native \
    -v /etc/machine-id:/etc/machine-id \
    cat_control
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

# Audio

apt-get install espeak espeak-ng

pactl list short sources
 /etc/pulse/default.pa
 aplay -l

ps aux | grep pulseaudio
matar si ha otro 
sdc       5645 
sudo kill 5645
systemctl --user restart pulseaudio.service
systemctl --user status pulseaudio.service
debe de estar funcionando

para probar:
aplay /usr/share/sounds/alsa/Front_Center.wav
paplay /usr/share/sounds/alsa/Front_Center.wav
aplay -D hw:2,0 /usr/share/sounds/alsa/Front_Center_stereo.wav

