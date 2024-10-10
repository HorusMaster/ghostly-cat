import pyttsx3

import os
import time

os.system('aplay -D hw:2,0 /usr/share/sounds/alsa/Front_Center_stereo.wav')
time.sleep(1) 

class SpeechSynthesizer:
    def __init__(self):
        # Inicializar el motor de texto a voz con espeak
        self.engine = pyttsx3.init(driverName='espeak')

        # Configurar propiedades del motor
        self.engine.setProperty('rate', 150)  # Velocidad del habla
        self.engine.setProperty('volume', 1)  # Volumen (de 0.0 a 1.0)

    def speak(self, text):
        """ Convierte el texto a audio y lo reproduce. """
        self.engine.say(text)
        self.engine.runAndWait()
