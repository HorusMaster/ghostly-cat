import sys
import asyncio

sys.path.append("/usr/lib/python3/dist-packages")

from adafruit_servokit import ServoKit

# Definición de canales para los servos
LEFT_RIGHT = 0
UP_DOWN = 1

# Inicialización del controlador de servos
kit = ServoKit(channels=16, address=0x40)


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
            LEFT_RIGHT, target_angle=100, cycles=5
        ),  # Mover el servo del canal 0 (izquierda/derecha)
        routine_servo_cycles(
            UP_DOWN, target_angle=30, cycles=5, steps=100
        ),  # Mover el servo del canal 1 (arriba/abajo)
    )

    # Regresar a la posición predeterminada
    await default_position()


# Ejecutar la función principal con asyncio
asyncio.run(main())
