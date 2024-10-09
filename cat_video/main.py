import cv2
import numpy as np
import os

# Ruta al archivo de modelo Caffe
MODEL_PATH = "models/res10_300x300_ssd_iter_140000.caffemodel"
PROTOTXT_PATH = "models/deploy.prototxt.txt"
VIDEO_OUTPUT_PATH = "/var/ghostlycat/videos/output.avi"  # Ruta de salida para el video

# Asegúrate de que la carpeta de salida exista
os.makedirs(os.path.dirname(VIDEO_OUTPUT_PATH), exist_ok=True)

# Cargar el modelo preentrenado
net = cv2.dnn.readNetFromCaffe(PROTOTXT_PATH, MODEL_PATH)

# Pipeline GStreamer para usar nvarguscamerasrc en Jetson Nano con aceleración de hardware
gst_pipeline = (
    "nvarguscamerasrc sensor-id=0 ! "
    "video/x-raw(memory:NVMM), width=1920, height=1080, format=NV12, framerate=30/1 ! "
    "nvvidconv ! video/x-raw, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink"
)

# Iniciar la captura de video desde la cámara usando el pipeline de GStreamer
cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

# Verificar que la cámara se haya abierto correctamente
if not cap.isOpened():
    print("Error: No se pudo abrir la cámara.")
    exit()

# Obtener las dimensiones del video
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Configurar el VideoWriter para guardar el video
fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Codec para AVI, también puedes usar 'MP4V'
out = cv2.VideoWriter(VIDEO_OUTPUT_PATH, fourcc, 10.0, (frame_width, frame_height))

while True:
    ret, frame = cap.read()

    if not ret:
        print("Error: No se pudo capturar el frame.")
        break

    # Obtener las dimensiones del frame
    frame_height, frame_width = frame.shape[:2]

    # Preparar la imagen para la detección de rostros
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0), swapRB=False, crop=False)

    # Realizar la detección de rostros
    net.setInput(blob)
    detections = net.forward()

    # Recorrer las detecciones
    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]  # Confianza de la detección (probabilidad)

        # Solo dibujar si la confianza es mayor a un umbral (por ejemplo, 0.5)
        if confidence > 0.5:
            # Obtener las coordenadas del bounding box
            box = detections[0, 0, i, 3:7] * np.array([frame_width, frame_height, frame_width, frame_height])
            (startX, startY, endX, endY) = box.astype("int")

            # Dibujar el bounding box alrededor del rostro
            cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)

            # Mostrar el nivel de confianza encima del bounding box
            text = f"{confidence * 100:.2f}%"
            y = startY - 10 if startY - 10 > 10 else startY + 10
            cv2.putText(frame, text, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)

    # Escribir el frame en el archivo de video
    out.write(frame)

    # Salir si se presiona la tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Liberar la cámara, cerrar el VideoWriter y destruir ventanas
cap.release()
out.release()
cv2.destroyAllWindows()
