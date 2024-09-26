import sys
import time
import asyncio

sys.path.append("/usr/lib/python3/dist-packages")

from adafruit_servokit import ServoKit

kit = ServoKit(channels=16, address=0x40)


async def move_servo_with_delay(servo_channel, target_angle, current_angle):
    # Calcula la diferencia de ángulo
    angle_difference = abs(target_angle - current_angle)

    # Calcula el tiempo de espera en base a la velocidad del servo MG995
    time_to_wait = (angle_difference / 60) * 0.22  # 0.22 segundos por 60 grados

    # Mueve el servo al ángulo objetivo
    kit.servo[servo_channel].angle = target_angle

    # Espera el tiempo calculado de manera asíncrona
    await asyncio.sleep(time_to_wait)

    print(
        f"Servo {servo_channel} movido de {current_angle}° a {target_angle}° en {time_to_wait:.2f} segundos"
    )


async def routine_servo_5_cycles(servo_channel):
    current_angle = 0
    kit.servo[servo_channel].angle = 0
    await asyncio.sleep(1)
    for _ in range(5):
        # Mover de 0° a 180°
        target_angle = 180
        await move_servo_with_delay(servo_channel, target_angle, current_angle)
        current_angle = target_angle

        # Mover de 180° a 0°
        target_angle = 0
        await move_servo_with_delay(servo_channel, target_angle, current_angle)
        current_angle = target_angle


async def main():
    # Ejecutar las rutinas de dos servos al mismo tiempo usando asyncio.gather
    await asyncio.gather(
        routine_servo_5_cycles(0),  # Mover el servo del canal 0
        routine_servo_5_cycles(1),  # Mover el servo del canal 1
    )


# Ejecutar la función principal con asyncio
asyncio.run(main())
