import paho.mqtt.client as mqtt
from dataclasses import dataclass
import json
import threading
import queue

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "cat/telemetry"


@dataclass(frozen=True)
class CatTelemetry:
    centroid_x: float
    centroid_y: float

    def to_dict(self):
        return {"centroid_x": self.centroid_x, "centroid_y": self.centroid_y}


class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.mqtt_queue = queue.Queue()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message       
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)

    def client_start(self):
        self.client.loop_start()

    def run(self):     
        thread = threading.Thread(target=self.client.loop_forever)
        thread.daemon = True
        thread.start()

    def publish(self, payload):
        self.client.publish(MQTT_TOPIC, payload)

    def on_connect(self, client, userdata, flags, rc):       
        message = f"Conectado a MQTT Broker con código {str(rc)}"
        try:
            print(message)  # Simplemente imprime el mensaje directamente
        except UnicodeEncodeError:
            # En caso de error con la codificación ASCII, se reemplazan los caracteres especiales.
            print(message.encode('ascii', 'replace').decode('ascii'))
        client.subscribe(MQTT_TOPIC)

    def disconnect(self):       
        self.client.loop_stop()  # Detiene el loop_start
        self.client.disconnect()  # Desconecta el cliente del broker
        print("Cliente MQTT desconectado")

    def on_message(self, client, userdata, msg):
        try:
            msg = msg.payload.decode()
            self.mqtt_queue.put(msg)
            #print(msg)
        #     payload = json.loads(msg.payload.decode())
        #     centroid_x = payload.get("centroid_x")
        #     centroid_y = payload.get("centroid_y")
        #     print(f"Centroid recibido: X={centroid_x}, Y={centroid_y}")

        except Exception as e:
            print(f"Error procesando el mensaje: {e}")
