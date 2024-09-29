import asyncio
import json
from adafruit_servokit import ServoKit
from cat_common.mqtt_messages import CatTelemetry, MQTTClient
from threading import Thread
import queue
# Definición de canales para los servos
LEFT_RIGHT = 0
UP_DOWN = 1


SERVO_X_MIN = 0
SERVO_X_MAX = 100
SERVO_Y_MIN = 0
SERVO_Y_MAX = 30
IMAGE_WIDTH = 1280
IMAGE_HEIGHT = 720

class ServoController:
    def __init__(self):
        self.kit = ServoKit(channels=16, address=0x40)
        self.mqtt_client = MQTTClient()
        self.mqtt_client.run()
        self.current_angle_x = 50  # Ángulo inicial del servo X
        self.current_angle_y = 0   # Ángulo inicial del servo Y

    async def move_servo_x(self, target_angle):
        """ Controla el servo X suavemente. """
        print(f"Moviendo servo X suavemente a {target_angle} grados")
        await self.move_servo_with_steps(LEFT_RIGHT, target_angle, self.current_angle_x)
        self.current_angle_x = target_angle  # Actualiza el ángulo actual

    async def move_servo_y(self, target_angle):
        """ Controla el servo Y suavemente. """
        print(f"Moviendo servo Y suavemente a {target_angle} grados")
        await self.move_servo_with_steps(UP_DOWN, target_angle, self.current_angle_y)
        self.current_angle_y = target_angle  # Actualiza el ángulo actual

    def map_value(self, value, input_min, input_max, output_min, output_max):
        return (value - input_min) * (output_max - output_min) / (input_max - input_min) + output_min

    async def control_servos(self, centroid_x, centroid_y):
        """ Mapea las coordenadas del centroide a los ángulos de los servos y los mueve suavemente. """
        servo_x_angle = self.map_value(centroid_x, 0, IMAGE_WIDTH, SERVO_X_MAX, SERVO_X_MIN)
        servo_y_angle = self.map_value(centroid_y, 0, IMAGE_HEIGHT, SERVO_Y_MAX, SERVO_Y_MIN)

        # Mover los servos suavemente a los ángulos calculados
        await self.move_servo_x(servo_x_angle)
        await self.move_servo_y(servo_y_angle)

    async def move_servo_with_steps(self, servo_channel, target_angle, current_angle, steps=20):
        # Calcula el tamaño del paso
        step_size = (target_angle - current_angle) / steps

        # Calcula el tiempo total estimado para el movimiento y lo divide entre los pasos
        total_angle_difference = abs(target_angle - current_angle)
        total_time = (total_angle_difference / 60) * 0.32  # 0.32 segundos por cada 60 grados
        step_delay = total_time / steps  # Tiempo de espera por cada paso

        # Mueve el servo gradualmente en pequeños pasos
        for step in range(steps):
            current_angle += step_size
            current_angle = max(0, min(180, current_angle))  # Asegúrate de que el ángulo esté en el rango permitido
            self.kit.servo[servo_channel].angle = current_angle
            await asyncio.sleep(step_delay)

        print(f"Servo {servo_channel} movido suavemente a {target_angle}° en {total_time:.2f} segundos")

    async def process_mqtt_messages(self):
        while True:
            try:
                # Espera a que llegue un mensaje en la cola
                data_str = self.mqtt_client.mqtt_queue.get_nowait()          
                json_str = data_str.replace("'", '"')   # Remplazar por binary
                payload = json.loads(json_str)           
                centroid_x = payload.get("centroid_x")
                centroid_y = payload.get("centroid_y")            
                print(f"Centroid recibido: X={centroid_x}, Y={centroid_y}")
              
                await self.control_servos(centroid_x, centroid_y)
               
            except queue.Empty:
                await asyncio.sleep(0.1)
            except Exception as exc:
                print(exc)

    async def routine_servo_cycles(self, servo_channel, target_angle, cycles=5, steps=20):
        """
        Función genérica para mover un servo en múltiples ciclos entre 0 y el ángulo objetivo.
        """
        current_angle = 0
        self.kit.servo[servo_channel].angle = current_angle
        await asyncio.sleep(1)

        for _ in range(cycles):
            # Mover de 0° a target_angle
            await self.move_servo_with_steps(servo_channel, target_angle, current_angle, steps=steps)
            current_angle = target_angle

            # Mover de target_angle a 0°
            await self.move_servo_with_steps(servo_channel, 0, current_angle, steps=steps)
            current_angle = 0
            await asyncio.sleep(1)

    async def default_position(self):
        # Configura los servos en la posición predeterminada
        await self.move_servo_x(50)
        await self.move_servo_y(0)
        await asyncio.sleep(1)

    async def configure_servos(self):
        # Configura los rangos de ancho de pulso para cada servo
        self.kit.servo[LEFT_RIGHT].set_pulse_width_range(800, 2500)
        self.kit.servo[UP_DOWN].set_pulse_width_range(600, 2250)

    async def main(self):
        # Configurar servos y establecer posición predeterminada
        await self.configure_servos()
        await self.default_position()

        # # Ejecutar las rutinas de los servos al mismo tiempo usando asyncio.gather
        # await self.routine_servo_cycles(
        #         LEFT_RIGHT, target_angle=100, cycles=1
        #     ),  # Mover el servo del canal 0 (izquierda/derecha)
        # await self.routine_servo_cycles(
        #         UP_DOWN, target_angle=30, cycles=1, steps=100
        #     ),  # Mover el servo del canal 1 (arriba/abajo)
        await asyncio.gather(           
            self.process_mqtt_messages()
        )

        # Regresar a la posición predeterminada
        await self.default_position()

# Ejecutar la clase ServoController
if __name__ == '__main__':
    servo_controller = ServoController()
    try:
        asyncio.run(servo_controller.main())
    except Exception:
        print("Terminated")
    finally:
        servo_controller.mqtt_client.disconnect()
