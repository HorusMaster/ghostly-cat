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
IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080


def move_servo_x(angle):
    """ Controla el servo X (ejemplo, ajusta según el control de tu servo). """
    print(f"Moviendo servo X a {angle} grados")
    kit.servo[LEFT_RIGHT].angle = angle


def move_servo_y(angle):
    """ Controla el servo Y (ejemplo, ajusta según el control de tu servo). """
    print(f"Moviendo servo Y a {angle} grados")
    kit.servo[UP_DOWN].angle = angle

def map_value(value, input_min, input_max, output_min, output_max):
    return (value - input_min) * (output_max - output_min) / (input_max - input_min) + output_min

def control_servos(centroid_x, centroid_y):
    """ Mapea las coordenadas del centroide a los ángulos de los servos y los mueve. """
    servo_x_angle = map_value(centroid_x, 0, IMAGE_WIDTH, SERVO_X_MIN, SERVO_X_MAX)
    servo_y_angle = map_value(centroid_y, 0, IMAGE_HEIGHT, SERVO_Y_MIN, SERVO_Y_MAX)

    # Mover los servos a los ángulos calculados
    move_servo_x(servo_x_angle)
    move_servo_y(servo_y_angle)


async def process_mqtt_messages():
    while True:
        try:
            # Espera a que llegue un mensaje en la cola
            data_str = mqtt_client.mqtt_queue.get_nowait()          
            json_str = data_str.replace("'", '"')   # Remplazar por binary
            payload = json.loads(json_str)           
            centroid_x = payload.get("centroid_x")
            centroid_y = payload.get("centroid_y")            
            print(f"Centroid recibido: X={centroid_x}, Y={centroid_y}")
          
            control_servos(centroid_x, centroid_y)
           
        except queue.Empty:
            await asyncio.sleep(0.1)
        except Exception as exc:
            print(exc)


async def move_servo_with_steps(servo_channel, target_angle, current_angle, steps=10):
    # Calcula el tamaño del paso
    step_size = (target_angle - current_angle) / steps

    # Calcula el tiempo total estimado para el movimiento y lo divide entre los pasos
    total_angle_difference = abs(target_angle - current_angle)
    total_time = (total_angle_difference / 60) * 0.32  # 0.32 segundos por cada 60 grados
    step_delay = total_time / steps  # Tiempo de espera por cada paso

    # Mueve el servo gradualmente en pequeños pasos
    for step in range(steps):
        current_angle += step_size
        current_angle = max(
            0, min(180, current_angle)
        )  # Asegúrate de que el ángulo esté en el rango permitido
        kit.servo[servo_channel].angle = current_angle
        await asyncio.sleep(step_delay)

    print(f"Servo {servo_channel} movido suavemente a {target_angle}° en {total_time:.2f} segundos")


async def routine_servo_cycles(servo_channel, target_angle, cycles=5, steps=20):
    """
    Función genérica para mover un servo en múltiples ciclos entre 0 y el ángulo objetivo.
    """
    current_angle = 0
    kit.servo[servo_channel].angle = current_angle
    await asyncio.sleep(1)

    for _ in range(cycles):
        # Mover de 0° a target_angle
        await move_servo_with_steps(servo_channel, target_angle, current_angle, steps=steps)
        current_angle = target_angle

        # Mover de target_angle a 0°
        await move_servo_with_steps(servo_channel, 0, current_angle, steps=steps)
        current_angle = 0
        await asyncio.sleep(1)


async def default_position():
    # Configura los servos en la posición predeterminada
    kit.servo[LEFT_RIGHT].angle = 50
    kit.servo[UP_DOWN].angle = 0
    await asyncio.sleep(1)


async def configure_servos():
    # Configura los rangos de ancho de pulso para cada servo
    kit.servo[LEFT_RIGHT].set_pulse_width_range(800, 2500)
    kit.servo[UP_DOWN].set_pulse_width_range(600, 2250)


async def main():
    # Configurar servos y establecer posición predeterminada
    await configure_servos()
    await default_position()

    # Ejecutar las rutinas de los servos al mismo tiempo usando asyncio.gather
    await asyncio.gather(
        routine_servo_cycles(
            LEFT_RIGHT, target_angle=100, cycles=2
        ),  # Mover el servo del canal 0 (izquierda/derecha)
        routine_servo_cycles(
            UP_DOWN, target_angle=30, cycles=2, steps=100
        ),  # Mover el servo del canal 1 (arriba/abajo)
        process_mqtt_messages()
    )

    # Regresar a la posición predeterminada
    await default_position()


# Ejecutar la función principal con asyncio
if __name__ == '__main__':
    # Inicialización del controlador de servos
    kit = ServoKit(channels=16, address=0x40)
    mqtt_client = MQTTClient()   
    mqtt_client.run()
    try:
        asyncio.run(main())
    except Exception:
        print("Terminated")
    finally:
        mqtt_client.disconnect()

