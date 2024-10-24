import asyncio
import time
from adafruit_servokit import ServoKit
from cat_common.mqtt_messages import CatTelemetry, MQTTClient, MQTT_TOPIC, MQTT_FACE_TOPIC
from abc import ABC
import random
import queue
import signal
import os
from pathlib import Path
IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080
MIN_PIXELS_TO_PROCESS = 100


def convert_audio(target_path: Path, current_audio: Path):
    output_stereo = target_path/"output_stereo.wav"
    os.system(f"sox {current_audio} {output_stereo} channels 2 rate 48000 dither")
    

async def speak_async(audio_path: Path, audio_playing_event):
    """Reproduce el audio de forma asíncrona."""
    process = await asyncio.create_subprocess_exec(
        'aplay', '-D', 'hw:2,0', str(audio_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    audio_playing_event.clear()
    


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

    async def move_quickly(self, audio_playing_event: asyncio.Event):
        """Mueve el servo rápidamente mientras el evento está activo (reproduciendo audio)."""
        #while audio_playing_event.is_set():  # Cambiamos la condición para que se mueva mientras el evento está activo
            # Mover rápidamente la boca simulando hablar
        while audio_playing_event.is_set():
            await self.just_move(self.max_angle)
            await asyncio.sleep(0.2)
            await self.just_move(self.min_angle)        
            await asyncio.sleep(0.2)

    async def just_move(self, angle):
        self.kit.servo[self.servo_channel].angle = angle

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

    async def move_naturally(self, stop_flag = None, audio_playing_event=None):
        while True:
            if stop_flag is not None and stop_flag.is_set():
                await asyncio.sleep(0.1)
                continue            

            if audio_playing_event is not None and audio_playing_event.is_set():
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
    ADDRESS = 12
    current_angle = 85
    min_angle = 60
    max_angle = 90
    pulse_min = 400
    pulse_max = 2400

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
    current_angle = 90
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
        while True:
            try:
                self.kit = ServoKit(channels=16, address=0x40)
                self.kit.frequency = 50
                break
            except Exception:
                print("Failed to load PCA Servocontroller Trying in 10 seconds")
            time.sleep(10)

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
        self.audio_playing_event = asyncio.Event()
        self.last_message_time = time.time()
        self.time_without_messages = 5 
        self.audio_queue = asyncio.Queue()
        self.last_audio_played = None  

        # self.audio_files = {
        #     "yare": YARE_AUDIO,
        #     "pepe": PEPE_AUDIO,
        #     "tita": TITA_AUDIO,
        #     "vale": VALE_AUDIO,
        #     "hola": HOLA_AUDIO
        # }
 

    # async def play_face_audio(self, face_detected):
    #     """Limpia la cola de audios anteriores y coloca el audio del último rostro detectado si no es el mismo."""
    #     if face_detected in self.audio_files:
    #         audio_path = self.audio_files[face_detected]

    #         # Verifica si es el mismo audio que ya está en la cola
    #         if audio_path != self.last_audio_played:
    #             # Vacía la cola antes de agregar el nuevo audio
    #             while not self.audio_queue.empty():
    #                 try:
    #                     self.audio_queue.get_nowait()
    #                     self.audio_queue.task_done()
    #                 except queue.Empty:
    #                     break

    #             # Agregar el nuevo audio a la cola
    #             await self.audio_queue.put(audio_path)
    #             self.last_audio_played = audio_path

    async def audio_player(self):
        """Reproduce audios de la cola de manera secuencial y mueve la boca rápidamente mientras se reproduce."""
        while True:
            try:
                audio_path = await self.audio_queue.get()

                # Inicia el movimiento rápido al reproducir el audio
                self.audio_playing_event.set()
                
                # Reproduce el audio mientras mueve la boca rápidamente
                await asyncio.gather(
                    speak_async(audio_path, self.audio_playing_event),
                    self.mouth_servo.move_quickly(self.audio_playing_event)
                )

                # Al terminar, desactiva el evento para detener el movimiento rápido
                self.audio_playing_event.clear()

                self.audio_queue.task_done()
            except Exception as exc:
                print(exc)

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
                topic, payload = self.mqtt_client.mqtt_queue.get_nowait()
                if topic == MQTT_TOPIC:
                    telemetry = CatTelemetry.from_bytes(payload)
                    self.stop_natural_movement.set()   
                    await self.control_servos(telemetry)   
                    self.last_message_time = time.time()
                elif topic == MQTT_FACE_TOPIC:
                    face_detected = payload.decode("utf-8")
                    #print(face_detected)
                    #print(f"Rostro detectado: {face_detected}")
                    #await self.play_face_audio(face_detected)
                #print(f"Centroid recibido: X={centroid_x}, Y={centroid_y}")     
                #if self.should_process_telemetry(telemetry):      
               
                
                                
            except queue.Empty:
                await asyncio.sleep(0.01)
                if time.time() - self.last_message_time > self.time_without_messages:
                    self.stop_natural_movement.clear()
            except Exception as exc:
                print(exc)


    async def main(self):
        await self.default_position()
        #await self.play_face_audio("hola")
        # Ejecutar los movimientos naturales de cada servo
        await asyncio.gather(
            self.process_mqtt_messages(),
            self.tail_servo.move_naturally(),      
            self.mouth_servo.move_naturally(audio_playing_event=self.audio_playing_event),
            self.eye_brightness.move_naturally(),  
            self.left_right_servo.move_naturally(self.stop_natural_movement),
            #self.audio_player()                 
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
    # PEPE_AUDIO = Path("audios/pepe_stereo.wav")
    # YARE_AUDIO = Path("audios/yare_stereo.wav")
    # TITA_AUDIO = Path("audios/tita_stereo.wav")
    # VALE_AUDIO = Path("audios/vale_stereo.wav") 
    # HOLA_AUDIO = Path("audios/hola_stereo.wav")
    
    #AUDIOS = Path("/var/ghostlycat/audios")
    #convert_audio(AUDIOS, HOLA_AUDIO)
   
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
