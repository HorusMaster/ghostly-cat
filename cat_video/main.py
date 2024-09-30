import cv2
import multiprocessing
import time
import torch
from models.experimental import attempt_load
import copy
from utils.datasets import letterbox
from utils.general import check_img_size, non_max_suppression_face, scale_coords
import json
from cat_common.mqtt_messages import CatTelemetry, MQTTClient


mqtt_client = MQTTClient()
mqtt_client.client_start()


def load_model(weights, device):
    model = attempt_load(weights, map_location=device)  # load FP32 model
    return model


def publish_centroid(telemetry: CatTelemetry):
    """Publica los centroides en formato JSON a través de MQTT."""
    payload = json.dumps(telemetry.to_dict())
    mqtt_client.publish(payload)
    print(f"Published Centroids {payload}")


def scale_coords_landmarks(img1_shape, coords, img0_shape, ratio_pad=None):
    # Rescale coords (xyxy) from img1_shape to img0_shape
    if ratio_pad is None:  # calculate from img0_shape
        gain = min(
            img1_shape[0] / img0_shape[0], img1_shape[1] / img0_shape[1]
        )  # gain  = old / new
        pad = (img1_shape[1] - img0_shape[1] * gain) / 2, (
            img1_shape[0] - img0_shape[0] * gain
        ) / 2  # wh padding
    else:
        gain = ratio_pad[0][0]
        pad = ratio_pad[1]

    coords[:, [0, 2, 4, 6, 8]] -= pad[0]  # x padding
    coords[:, [1, 3, 5, 7, 9]] -= pad[1]  # y padding
    coords[:, :10] /= gain
    # clip_coords(coords, img0_shape)
    coords[:, 0].clamp_(0, img0_shape[1])  # x1
    coords[:, 1].clamp_(0, img0_shape[0])  # y1
    coords[:, 2].clamp_(0, img0_shape[1])  # x2
    coords[:, 3].clamp_(0, img0_shape[0])  # y2
    coords[:, 4].clamp_(0, img0_shape[1])  # x3
    coords[:, 5].clamp_(0, img0_shape[0])  # y3
    coords[:, 6].clamp_(0, img0_shape[1])  # x4
    coords[:, 7].clamp_(0, img0_shape[0])  # y4
    coords[:, 8].clamp_(0, img0_shape[1])  # x5
    coords[:, 9].clamp_(0, img0_shape[0])  # y5
    return coords

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



def show_results(img, xyxy, conf, landmarks, class_num, min_area=500):
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

    # Dibujar los landmarks (puntos de referencia de la cara)
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255)]

    for i in range(5):
        point_x = int(landmarks[2 * i])
        point_y = int(landmarks[2 * i + 1])
        cv2.circle(img, (point_x, point_y), tl + 1, colors[i], -1)

    # Mostrar el nivel de confianza
    tf = max(tl - 1, 1)  # font thickness
    label = str(conf)[:5]
    cv2.putText(
        img, label, (x1, y1 - 2), 0, tl / 3, [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA
    )

    # Retornar la imagen y el centroide si pasa el filtro de área
    return img, (centroid_x, centroid_y)

def capture_video(centroid_queue):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")    
    print("Device is using: ", device)
    img_size = 640
    conf_thres = 0.6
    iou_thres = 0.5  
    last_processed_time = time.monotonic()
    fps_interval = 0.5
    min_area=500
    # Definir el pipeline GStreamer para utilizar nvarguscamerasrc
    gst_pipeline = (
        "nvarguscamerasrc sensor-id=0 sensor-mode=4 ! "
        "video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! "
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
    
    print("OPENCV and camera loaded, loading model..")
    model = load_model("models/yolov5n-0.5.pt", device)
    print("Model Loaded")

  
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

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        current_time = time.monotonic()
        if current_time - last_processed_time < fps_interval:
            continue  # Si no ha pasado 1 segundo, continuar sin procesar
        last_processed_time = current_time
        
        orgimg = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img0 = copy.deepcopy(orgimg)
        im0 = copy.deepcopy(frame)
        h0, w0 = orgimg.shape[:2]  # orig hw
        r = img_size / max(h0, w0)  # resize image to img_size
        if r != 1:  # always resize down, only resize up if training with augmentation
            interp = cv2.INTER_AREA if r < 1 else cv2.INTER_LINEAR
            img0 = cv2.resize(img0, (int(w0 * r), int(h0 * r)), interpolation=interp)

        imgsz = check_img_size(img_size, s=model.stride.max())  # check img_size

        img = letterbox(img0, new_shape=imgsz)[0]
        # Convert from w,h,c to c,w,h
        img = img.transpose(2, 0, 1).copy()

        img = torch.from_numpy(img).to(device)
        img = img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Inference
        pred = model(img)[0]
        pred = non_max_suppression_face(pred, conf_thres, iou_thres)
        #print(len(pred[0]), "face" if len(pred[0]) == 1 else "faces")

        for i, det in enumerate(pred):  # detections per image
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class

                det[:, 5:15] = scale_coords_landmarks(
                    img.shape[2:], det[:, 5:15], im0.shape
                ).round()

                for j in range(det.size()[0]):
                    xyxy = det[j, :4].view(-1).tolist()
                    #conf = det[j, 4].cpu().numpy()
                    #landmarks = det[j, 5:15].view(-1).tolist()
                    #class_num = det[j, 15].cpu().numpy()

                    #im0, centroid = show_results(im0, xyxy, conf, landmarks, class_num, min_area=min_area)
                    centroids = calculate_centroid(xyxy, 500)
                    if centroids:
                        centroid_x, centroid_y = centroids
                        telemetry = CatTelemetry(centroid_x=centroid_x, centroid_y=centroid_y)
                        centroid_queue.put(telemetry)

        #cv2.imshow("Video de la cámara", im0)

        # Salir del bucle si se presiona la tecla 'q'

    # Liberar la cámara y cerrar las ventanas
    cap.release()
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
