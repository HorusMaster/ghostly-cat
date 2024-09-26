import time

import sys
sys.path.append('/usr/lib/python3/dist-packages')

from adafruit_servokit import ServoKit

kit = ServoKit(channels=16, address=0x40) 
kit.frequency = 50


def move_servo_with_delay(servo_channel, target_angle, current_angle):
    # Calcula la diferencia de ángulo
    angle_difference = abs(target_angle - current_angle)
    
    # Calcula el tiempo de espera en base a la velocidad del servo MG995
    time_to_wait = (angle_difference / 60) * 0.22  # 0.2 segundos por 60 grados
    
    # Mueve el servo al ángulo objetivo
    kit.servo[servo_channel].angle = target_angle
    
    # Espera el tiempo calculado
    time.sleep(time_to_wait)
    
    print(f"Servo {servo_channel} movido de {current_angle}° a {target_angle}° en {time_to_wait:.2f} segundos")

# Ejemplo: Mover el servo en el canal 0 de 0° a 90°
current_angle = 0
target_angle = 180
kit.servo[8].angle = 0
time.sleep(1)
move_servo_with_delay(8, target_angle, current_angle)

# Luego puedes actualizar la posición actual después del movimiento
current_angle = target_angle