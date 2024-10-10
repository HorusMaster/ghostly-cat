import pyttsx3
import os

def speak_test():
    try:
        # Inicializar el motor de texto a voz con espeak
        engine = pyttsx3.init(driverName='espeak')

        # Configurar propiedades del motor
        engine.setProperty('rate', 130)  # Ajustar la velocidad del habla (puedes ajustar este valor según tu preferencia)
        engine.setProperty('volume', 1)  # Volumen (de 0.0 a 1.0)

        # Obtener las voces disponibles
        voices = engine.getProperty('voices')

        # Seleccionar la voz 'Spanish (Latin America)' que está en el índice 27
        engine.setProperty('voice', voices[27].id)

        # Guardar la salida de pyttsx3 como un archivo temporal en mono
        output_file = "output.wav"
        engine.say("Estoy hablando en español.")
        engine.runAndWait()
        engine.save_to_file("Hola, esto es una prueba de síntesis de voz en español latinoamericano.", output_file)
        engine.runAndWait()

        # Convertir el archivo de audio de mono a estéreo y ajustar la frecuencia de muestreo a 48,000 Hz
        output_stereo = "output_stereo.wav"
        os.system(f"sox {output_file} {output_stereo} channels 2 rate 48000 dither")

        # Reproducir el archivo estéreo con aplay, especificando el dispositivo de salida
        os.system(f'aplay -D hw:2,0 {output_stereo}')
        
    except Exception as e:
        print(f"Error durante la síntesis de voz: {e}")

# Ejecutar la función
speak_test()
