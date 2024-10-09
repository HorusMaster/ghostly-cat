import cv2
import multiprocessing
import time
import json
from cat_common.mqtt_messages import CatTelemetry, MQTTClient


HAAR_CASCADE_PATH = "models/haarcascade_frontalface_default.xml"
VIDEO_OUTPUT_PATH = "/var/ghostlycat/videos/output.avi"

mqtt_client = MQTTClient()
mqtt_client.client_start()


def publish_centroid(telemetry: CatTelemetry):
    """Publica los centroides en formato JSON a través de MQTT."""
    payload = json.dumps(telemetry.to_dict())
    mqtt_client.publish(payload)
    print(f"Published Centroids {payload}")


def calculate_centroid(xyxy, min_area=500):
    """
    Calcula el centroide de los bounding boxes y filtra por tamaño.

    Parámetros:
    - xyxy: Lista de coordenadas [x1, y1, x2, y2] que definen el bounding box.
    - min_area: Área mínima requerida para considerar el bounding box.

    Retorna:
    - centroid: Una tupla con las coordenadas (centroid_x, centroid_y) del centroide si pasa el filtro.
    - None: Si el bounding box es demasiado pequeño.
    """
    x1 = int(xyxy[0])
    y1 = int(xyxy[1])
    x2 = int(xyxy[2])
    y2 = int(xyxy[3])

    # Calcular el área del bounding box
    bbox_width = x2 - x1
    bbox_height = y2 - y1
    bbox_area = bbox_width * bbox_height

    # Filtrar bounding boxes que no cumplan con el tamaño mínimo
    if bbox_area < min_area:
        return None  # No retornar nada si el área es menor al umbral

    # Calcular el centroide
    centroid_x = (x1 + x2) / 2
    centroid_y = (y1 + y2) / 2

    # Retornar el centroide
    return (centroid_x, centroid_y)


def show_results(img, xyxy, min_area=500):
    h, w, c = img.shape
    tl = 1 or round(0.002 * (h + w) / 2) + 1  # line/font thickness
    x1 = int(xyxy[0])
    y1 = int(xyxy[1])
    x2 = int(xyxy[2])
    y2 = int(xyxy[3])
    
    # Calcular el área del bounding box
    bbox_width = x2 - x1
    bbox_height = y2 - y1
    bbox_area = bbox_width * bbox_height

    # Filtrar bounding boxes que no cumplan con el tamaño mínimo
    if bbox_area < min_area:
        return img, None  # No retornamos el centroide si el área es menor al umbral
    
    img = img.copy()

    # Dibujar la caja alrededor de la cara
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), thickness=tl, lineType=cv2.LINE_AA)

    # Calcular el centroide
    centroid_x = (x1 + x2) / 2
    centroid_y = (y1 + y2) / 2

    # Dibujar el centroide como un círculo rojo
    cv2.circle(img, (int(centroid_x), int(centroid_y)), tl + 2, (0, 0, 255), -1)

    # Retornar la imagen y el centroide si pasa el filtro de área
    return img, (centroid_x, centroid_y)


def capture_video(centroid_queue):
    # Cargar el clasificador de Haar para detección de rostros
    face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)

    last_processed_time = time.monotonic()
    fps_interval = 0.2
    min_area = 500  # Ajusta según lo necesario

    # Definir el pipeline GStreamer para utilizar nvarguscamerasrc
    gst_pipeline = (
        "nvarguscamerasrc sensor-id=0 ! "
        "video/x-raw(memory:NVMM), width=1920, height=1080, format=NV12, framerate=30/1 ! "
        "nvvidconv ! video/x-raw, format=BGRx ! "
        "videoconvert ! video/x-raw, format=BGR ! "
        "appsink max-buffers=1 drop=true"
    )

    # Abrir la cámara con el pipeline GStreamer
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    

    # Comprobar si la cámara se abrió correctamente
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara.")
        return
    
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Codec para AVI (también puedes usar 'MJPG', 'MP4V', etc.)
    out = cv2.VideoWriter(VIDEO_OUTPUT_PATH, fourcc, 10.0, (frame_width, frame_height))

    while True:
        # Capturar frame por frame
        ret, frame = cap.read()

        # Si no se pudo capturar un frame, salir del bucle
        if not ret:
            print("Error: No se pudo recibir el frame.")
            break
        
       
        # Esperar hasta que se cumpla el intervalo de FPS
        # current_time = time.monotonic()
        # if current_time - last_processed_time >= fps_interval:
        #     last_processed_time = current_time

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            xyxy = [x, y, x + w, y + h]
            centroid = calculate_centroid(xyxy, min_area)
            if centroid:
                centroid_x, centroid_y = centroid
                telemetry = CatTelemetry(centroid_x=centroid_x, centroid_y=centroid_y)
                centroid_queue.put(telemetry)

            # Procesar solo un rostro
            frame, _ = show_results(frame, xyxy, min_area=min_area)
            #break  # Detenemos el loop después de procesar el primer rostro
        
        out.write(frame)
        # Si se presiona la tecla 'q', salir del loop
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    out.write(frame)
    # Liberar la cámara y cerrar las ventanas
    cap.release()
    out.release()
    cv2.destroyAllWindows()


def start_video_capture():
    # Crear un proceso para la captura de video
    centroid_queue = multiprocessing.Queue()

    process = multiprocessing.Process(target=capture_video, args=(centroid_queue,))
    process.start()

    # Esperar a que el proceso termine
    try:
        while process.is_alive():
            if not centroid_queue.empty():
                telemetry = centroid_queue.get()
                publish_centroid(telemetry)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Interrupcion detectada, cerrando proceso.")
    finally:
        if process.is_alive():
            process.terminate()
            process.join()


if __name__ == "__main__":
    start_video_capture()
