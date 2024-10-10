import asyncio
import time
from adafruit_servokit import ServoKit
from cat_common.mqtt_messages import CatTelemetry, MQTTClient
from abc import ABC
import random
import queue
import signal

IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080
MIN_PIXELS_TO_PROCESS = 100

class AbstractServo(ABC):
    current_angle: int 
    min_angle: int 
    max_angle: int 
    pulse_min: int 
    pulse_max: int 

    def __init__(self, servo_channel, kit):
        self.servo_channel = servo_channel
        self.kit = kit      
        # Configurar el rango de pulso
        self.kit.servo[self.servo_channel].set_pulse_width_range(self.pulse_min, self.pulse_max)

    async def move_servo(self, target_angle):
        """ Mueve el servo directamente a un ángulo específico y espera 1 segundo. """
        target_angle = max(self.min_angle, min(self.max_angle, target_angle))
        self.kit.servo[self.servo_channel].angle = target_angle
        self.current_angle = target_angle
        #print(f"Servo {self.__class__.__name__} movido directamente a {target_angle}°")
        await asyncio.sleep(1)

    async def move_servo_with_steps(self, target_angle, steps=20):
        """ Mueve el servo suavemente desde el ángulo actual hacia el ángulo objetivo en pasos. """
        step_size = (target_angle - self.current_angle) / steps
        total_time = abs(target_angle - self.current_angle) * 0.005
        step_delay = total_time / steps

        for _ in range(steps):
            self.current_angle += step_size
            self.current_angle = max(self.min_angle, min(self.max_angle, self.current_angle))
            self.kit.servo[self.servo_channel].angle = self.current_angle
            await asyncio.sleep(step_delay)

        #print(f"Servo {self.__class__.__name__} movido en pasos a {target_angle}° en {total_time:.2f} segundos")
        self.current_angle = target_angle

    async def move_naturally(self, stop_flag = None):
        while True:
            if stop_flag is not None and stop_flag.is_set():
                await asyncio.sleep(0.1)
                continue            
            pattern_type = random.choice(["oscillation", "hold", "small_variation"])

            if pattern_type == "oscillation":
                for _ in range(random.randint(2, 5)):
                    if stop_flag is not None and stop_flag.is_set():
                        break
                    await self.move_servo_with_steps(self.max_angle, steps=random.randint(10, 30))
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    await self.move_servo_with_steps(self.min_angle, steps=random.randint(10, 30))
                    await asyncio.sleep(random.uniform(0.5, 1.5))

            elif pattern_type == "hold":
                target_angle = random.choice([self.min_angle, self.max_angle])
                await self.move_servo(target_angle)
                await asyncio.sleep(random.uniform(2, 5))

            elif pattern_type == "small_variation":
                for _ in range(random.randint(3, 6)):
                    if stop_flag is not None and stop_flag.is_set():
                        break
                    current_angle = self.current_angle
                    small_variation = random.randint(-10, 10)
                    target_angle = max(self.min_angle, min(self.max_angle, current_angle + small_variation))
                    await self.move_servo_with_steps(target_angle, steps=random.randint(5, 15))
                    await asyncio.sleep(random.uniform(0.2, 0.5))

class TailServo(AbstractServo):
    ADDRESS = 0  # Dirección del servo para la cola
    current_angle = 120
    min_angle = 0
    max_angle = 120
    pulse_min = 600
    pulse_max = 2500

    def __init__(self, kit):
        super().__init__(TailServo.ADDRESS, kit)


class MouthServo(AbstractServo):
    ADDRESS = 12  # Dirección del servo para la boca
    current_angle = 40
    min_angle = 0
    max_angle = 40
    pulse_min = 600
    pulse_max = 2500

    def __init__(self, kit):
        super().__init__(MouthServo.ADDRESS, kit)


class LeftRightServo(AbstractServo):
    ADDRESS = 10  # Dirección del servo para el movimiento izquierda/derecha
    current_angle = 50
    min_angle = 0
    max_angle = 140
    pulse_min = 700
    pulse_max = 2300

    def __init__(self, kit):
        super().__init__(LeftRightServo.ADDRESS, kit)


class UpDownServo(AbstractServo):
    ADDRESS = 6  # Dirección del servo para el movimiento arriba/abajo
    current_angle = 120
    min_angle = 60
    max_angle = 130
    pulse_min = 1000
    pulse_max = 2500

    def __init__(self, kit):
        super().__init__(UpDownServo.ADDRESS, kit)

class EyeBrightnessControl(AbstractServo):
    ADDRESS = 15
    current_angle = 120
    min_angle = 0
    max_angle = 180
    pulse_min = 600
    pulse_max = 2500

    def __init__(self, kit):
        super().__init__(EyeBrightnessControl.ADDRESS, kit)


class ServoController:
    def __init__(self):
        self.kit = ServoKit(channels=16, address=0x40)

        # Instanciar servos con sus valores constantes definidos en cada subclase
        self.tail_servo = TailServo(self.kit)
        self.mouth_servo = MouthServo(self.kit)
        self.left_right_servo = LeftRightServo(self.kit)
        self.up_down_servo = UpDownServo(self.kit)
        self.eye_brightness = EyeBrightnessControl(self.kit)
        self.mqtt_client = MQTTClient()
        self.mqtt_client.run()
        self.last_telemetry_time = 0
        self.min_time_between_updates = 0.4  # Tiempo mínimo entre movimientos (200ms)
        self.last_centroid = None  # Último centroide procesado
        self.stop_natural_movement = asyncio.Event()
        self.last_message_time = time.time()
        self.time_without_messages = 5 


    async def default_position(self):
        """ Coloca todos los servos en su posición predeterminada usando `move_servo`. """
        await self.tail_servo.move_servo(self.tail_servo.current_angle)
        await self.mouth_servo.move_servo(self.mouth_servo.current_angle)
        await self.left_right_servo.move_servo(self.left_right_servo.current_angle)
        await self.up_down_servo.move_servo(self.up_down_servo.current_angle)
        await self.eye_brightness.move_servo(self.eye_brightness.current_angle)

    def map_value(self, value, input_min, input_max, output_min, output_max):
        return (value - input_min) * (output_max - output_min) / (input_max - input_min) + output_min
    
    def should_process_telemetry(self, telemetry):
        """ Decide si procesar el mensaje basado en la diferencia con el último y el tiempo. """
        current_time = time.time()

        # Descartar si la diferencia de tiempo es muy pequeña
        if current_time - self.last_telemetry_time < self.min_time_between_updates:
            return False

        # Descartar si la diferencia en el centroide es muy pequeña
        if self.last_centroid:
            delta_x = abs(telemetry.centroid_x - self.last_centroid.centroid_x)
            delta_y = abs(telemetry.centroid_y - self.last_centroid.centroid_y)
            if delta_x < MIN_PIXELS_TO_PROCESS and delta_y < MIN_PIXELS_TO_PROCESS:  # Umbral de diferencia mínima
                return False

        self.last_telemetry_time = current_time
        self.last_centroid = telemetry
        return True

    async def control_servos(self, telemetry: CatTelemetry):
        """ Mapea las coordenadas del centroide a los ángulos de los servos y los mueve suavemente. """
        servo_left_right_mapped_angle = self.map_value(telemetry.centroid_x, 0, IMAGE_WIDTH, self.left_right_servo.max_angle, self.left_right_servo.min_angle)
        servo_up_down_mapped_angle = self.map_value(telemetry.centroid_y, 0, IMAGE_HEIGHT, self.up_down_servo.max_angle, self.up_down_servo.min_angle)

        # Mover los servos suavemente a los ángulos calculados
        await self.left_right_servo.move_servo_with_steps(servo_left_right_mapped_angle, 50)
        await self.up_down_servo.move_servo_with_steps(servo_up_down_mapped_angle, 50)

    async def process_mqtt_messages(self):
        while True:
            try:
                data_binary = self.mqtt_client.mqtt_queue.get_nowait()
                telemetry = CatTelemetry.from_bytes(data_binary)
                #print(f"Centroid recibido: X={centroid_x}, Y={centroid_y}")     
                #if self.should_process_telemetry(telemetry):      
                self.stop_natural_movement.set()   
                await self.control_servos(telemetry)    
                self.last_message_time = time.time()                    
            except queue.Empty:
                await asyncio.sleep(0.01)
                if time.time() - self.last_message_time > self.time_without_messages:
                    self.stop_natural_movement.clear()
            except Exception as exc:
                print(exc)


    async def main(self):
        await self.default_position()

        # Ejecutar los movimientos naturales de cada servo
        await asyncio.gather(
            self.process_mqtt_messages(),
            self.tail_servo.move_naturally(),      
            self.mouth_servo.move_naturally(),     
            self.eye_brightness.move_naturally(),  
            self.left_right_servo.move_naturally(self.stop_natural_movement)
                       
        )

    async def shutdown(self):
        """Cancel all tasks and gracefully stop the loop."""
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        print("Tasks have been cancelled.")

def shutdown_handler(loop, servo_controller):
    asyncio.create_task(servo_controller.shutdown())

if __name__ == '__main__':
    servo_controller = ServoController()
    loop = asyncio.get_event_loop()

    # Handle signals for graceful shutdown
    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, signame), shutdown_handler, loop, servo_controller)

    try:
        loop.run_until_complete(servo_controller.main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Shutting down gracefully...")
    finally:
        loop.close()
