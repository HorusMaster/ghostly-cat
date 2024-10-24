import paho.mqtt.client as mqtt
from dataclasses import dataclass
import json
import threading
import queue

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "cat/telemetry"
MQTT_FACE_TOPIC = "cat/recognized"


@dataclass(frozen=True)
class CatTelemetry:
    centroid_x: int
    centroid_y: int

    def to_dict(self):
        """Convierte los datos en un diccionario, asegurando que sean de tipo int."""
        return {
            "centroid_x": int(self.centroid_x),  # Asegurarse de que sea un int
            "centroid_y": int(self.centroid_y)
        }

    def to_bytes(self):
        """Convierte el diccionario a JSON y luego a bytes con codificación UTF-8."""
        return bytes(json.dumps(self.to_dict()), "utf-8")

    @staticmethod
    def from_bytes(binary_data):
        """Convierte los datos en bytes (JSON) a una instancia de CatTelemetry."""
        data = json.loads(binary_data.decode("utf-8"))
        return CatTelemetry(centroid_x=data["centroid_x"], centroid_y=data["centroid_y"])


class MQTTClient:
    QOS = 0

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

    def publish(self, topic, payload):
        self.client.publish(topic, payload, qos=self.QOS)

    def on_connect(self, client, userdata, flags, rc):       
        message = f"Conectado a MQTT Broker con código {str(rc)}"
        try:
            print(message)  # Simplemente imprime el mensaje directamente
        except UnicodeEncodeError:
            # En caso de error con la codificación ASCII, se reemplazan los caracteres especiales.
            print(message.encode('ascii', 'replace').decode('ascii'))
        client.subscribe(MQTT_TOPIC)
        #client.subscribe(MQTT_FACE_TOPIC)

    def disconnect(self):       
        self.client.loop_stop()  # Detiene el loop_start
        self.client.disconnect()  # Desconecta el cliente del broker
        print("Cliente MQTT desconectado")

    
    def on_message(self, client, userdata, msg):
        """Manda a la cola tanto el topic como el payload recibido"""
        try:
            # Colocar en la cola una tupla con el topic y el payload
            self.mqtt_queue.put((msg.topic, msg.payload))
        except Exception as e:
            print(f"Error procesando el mensaje: {e}")
