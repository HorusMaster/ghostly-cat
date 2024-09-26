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

# Rutina para hacer girar el servo de 0° a 180° 5 veces
def routine_servo_5_cycles(servo_channel):
    current_angle = 0
    kit.servo[servo_channel].angle = 0
    time.sleep(1)
    for _ in range(5):
        # Mover de 0° a 180°
        target_angle = 180
        move_servo_with_delay(servo_channel, target_angle, current_angle)
        current_angle = target_angle
        
        # Mover de 180° a 0°
        target_angle = 0
        move_servo_with_delay(servo_channel, target_angle, current_angle)
        current_angle = target_angle

# Ejecuta la rutina para el canal 8
routine_servo_5_cycles(0)

