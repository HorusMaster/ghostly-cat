import paho.mqtt.client as mqtt
import json

MQTT_BROKER = "localhost"  # Cambia esto por la IP del contenedor con el broker Mosquitto
MQTT_PORT = 1883
MQTT_TOPIC = "cat/telemetry"


class MQTTClient():
    def __init__(self):
        client = mqtt.Client()
        # Conectar el cliente al broker
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(MQTT_BROKER, MQTT_PORT, 60)       
        client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        print(f"Conectado a MQTT Broker con código {rc}")     
        client.subscribe(MQTT_TOPIC)

    def on_message(self, client, userdata, msg):       
        try:          
            msg = msg.payload.decode()
            print(msg)        
        #     payload = json.loads(msg.payload.decode())
        #     centroid_x = payload.get("centroid_x")
        #     centroid_y = payload.get("centroid_y")
        #     print(f"Centroid recibido: X={centroid_x}, Y={centroid_y}")       
        
        except Exception as e:
            print(f"Error procesando el mensaje: {e}")



