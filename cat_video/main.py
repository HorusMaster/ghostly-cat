import cv2
import numpy as np
import time
from pathlib import Path
from cat_common.mqtt_messages import CatTelemetry, MQTTClient
from modules.face_manager import FaceTrainer


class CatFaceDetector:
    def __init__(self, model_path: Path, prototxt_path:Path, mqtt_client: MQTTClient, face_trainer:FaceTrainer, video_output_path: Path=None, draw_boxes:bool=False, fps_limit:int=10):
        self.model_path = str(model_path)
        self.prototxt_path = str(prototxt_path)
        self.mqtt_client = mqtt_client
        self.draw_boxes = draw_boxes
        self.fps_limit = 1 / fps_limit
        self.last_processed_time = time.monotonic()
        self.face_trainer = face_trainer
       

        self.net = cv2.dnn.readNetFromCaffe(self.prototxt_path, self.model_path)

        self.gst_pipeline = (
            "nvarguscamerasrc sensor-id=0 ! "
            "video/x-raw(memory:NVMM), width=1920, height=1080, format=NV12, framerate=30/1 ! "
            "nvvidconv ! video/x-raw, format=BGRx ! videoconvert ! appsink max-buffers=1 drop=true"
        )

        self.cap = cv2.VideoCapture(self.gst_pipeline, cv2.CAP_GSTREAMER)

        if not self.cap.isOpened():
            print("Error: No se pudo abrir la cámara.")
            exit()

        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if video_output_path:
            video_output_path.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.out = cv2.VideoWriter(str(video_output_path), fourcc, 10.0, (self.frame_width, self.frame_height))
        else:
            self.out = None

    def publish_centroid(self, telemetry: CatTelemetry):
        self.mqtt_client.publish(telemetry.to_bytes())

    def process_frame(self):
        ret, frame = self.cap.read()

        if not ret:
            print("Error: No se pudo capturar el frame.")
            return False

        current_time = time.monotonic()

        if (current_time - self.last_processed_time) < self.fps_limit:
            return True

        self.last_processed_time = current_time

        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0), swapRB=False, crop=False)

        self.net.setInput(blob)
        detections = self.net.forward()

        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]

            if confidence > 0.5:
                box = detections[0, 0, i, 3:7] * np.array([self.frame_width, self.frame_height, self.frame_width, self.frame_height])
                (startX, startY, endX, endY) = box.astype("int")

                if self.draw_boxes:
                    cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
                    text = f"{confidence * 100:.2f}%"
                    y = startY - 10 if startY - 10 > 10 else startY + 10
                    cv2.putText(frame, text, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)

                centroid_x = (startX + endX) // 2
                centroid_y = (startY + endY) // 2

                self.publish_centroid(CatTelemetry(centroid_x, centroid_y))

                face_encoding = detections[0, 0, i, 3:7]

                # Comparar con encodings entrenados                
                name = self.face_trainer.compare_encodings(face_encoding)
                print(name)
                # Publicar el nombre reconocido
                #self.publish_recognized_name(name)

        if self.out:
            self.out.write(frame)

        return True

    def release_resources(self):
        self.cap.release()
        if self.out:
            self.out.release()
        cv2.destroyAllWindows()

    def run(self):
        while True:
            if not self.process_frame():
                break

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.release_resources()


if __name__ == "__main__":
    MODEL_PATH = Path("models/res10_300x300_ssd_iter_140000.caffemodel")
    PROTOTXT_PATH = Path("models/deploy.prototxt.txt")
    VIDEO_OUTPUT_PATH = Path("/var/ghostlycat/videos/output.avi")
    ENCODINGS_PATH = Path("/var/ghostlycat/face_encodings/encodings.json")
    
    mqtt_client = MQTTClient()
    mqtt_client.client_start()

    face_trainer = FaceTrainer(ENCODINGS_PATH, PROTOTXT_PATH, MODEL_PATH)

    detector = CatFaceDetector(
        model_path=MODEL_PATH,
        prototxt_path=PROTOTXT_PATH,
        mqtt_client=mqtt_client,
        face_trainer=face_trainer,
        fps_limit=10
       
    )
    detector.run()
