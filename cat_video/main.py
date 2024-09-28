import cv2
import multiprocessing
import time
import torch
from models.experimental import attempt_load

def load_model(weights, device):
    model = attempt_load(weights, map_location=device)  # load FP32 model
    return model


def capture_video():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device is using: ", device)
    # Definir el pipeline GStreamer para utilizar nvarguscamerasrc
    gst_pipeline = (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), width=1920, height=1080, framerate=30/1, format=NV12 ! "
        "nvvidconv ! video/x-raw, format=BGRx ! "
        "videoconvert ! video/x-raw, format=BGR ! appsink"
    )

    # Abrir la cámara con el pipeline GStreamer
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

    # Comprobar si la cámara se abrió correctamente
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara.")
        return

    while True:
        # Capturar frame por frame
        try:
            ret, frame = cap.read()
        except Exception as exc:
            print(exc)

        # Si no se pudo capturar un frame, salir del bucle
        if not ret:
            print("Error: No se pudo recibir el frame.")
            break

        orgimg = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)      
        cv2.imshow("Video de la cámara", orgimg)

        # Salir del bucle si se presiona la tecla 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Liberar la cámara y cerrar las ventanas
    cap.release()
    cv2.destroyAllWindows()


def start_video_capture():
    # Crear un proceso para la captura de video
    process = multiprocessing.Process(target=capture_video)
    process.start()

    # Esperar a que el proceso termine
    try:
        while process.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Interrupción detectada, cerrando proceso.")
    finally:
        if process.is_alive():
            process.terminate()
            process.join()

if __name__ == "__main__":
    start_video_capture()
