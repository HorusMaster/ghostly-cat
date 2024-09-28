import cv2
import multiprocessing
import time
import torch
from models.experimental import attempt_load
import copy
from utils.datasets import letterbox
from utils.general import check_img_size


def load_model(weights, device):
    model = attempt_load(weights, map_location=device)  # load FP32 model
    return model


def capture_video():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model("models/yolov5n-face.pt", device)
    img_size = 640
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
        img0 = copy.deepcopy(orgimg)
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
        cv2.imshow("Video de la cámara", orgimg)

        # Salir del bucle si se presiona la tecla 'q'
        if cv2.waitKey(1) & 0xFF == ord("q"):
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
