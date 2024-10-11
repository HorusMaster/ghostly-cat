import cv2
import os
import numpy as np
from pathlib import Path
import json
import random

class FaceTrainer:
    def __init__(self, encodings_path: Path, prototxt_path: Path, model_path: Path):
        self.encodings_path = encodings_path
        self.known_face_encodings = []
        self.known_face_names = []
        self.prototxt_path = prototxt_path
        self.model_path = model_path
        self.net = cv2.dnn.readNetFromCaffe(str(prototxt_path), str(model_path))

        # GStreamer pipeline
        self.gst_pipeline = (
            "nvarguscamerasrc sensor-id=0 ! "
            "video/x-raw(memory:NVMM), width=1920, height=1080, format=NV12, framerate=30/1 ! "
            "nvvidconv ! video/x-raw, format=BGRx ! videoconvert ! appsink max-buffers=1 drop=true"
        )

        # Cargar encodings previos si existen
        if self.encodings_path.exists():
            self.load_encodings()

    def load_encodings(self):
        """Cargar los encodings almacenados en un archivo JSON"""
        with open(self.encodings_path, 'r') as f:
            data = json.load(f)
            self.known_face_encodings = data['encodings']  # Ya es una lista
            self.known_face_names = data['names']
    
    def save_encodings(self):
        """Guardar los encodings en un archivo JSON"""
        with open(self.encodings_path, 'w') as f:
            data = {
                'encodings': self.known_face_encodings,  # No usar tolist() aquí
                'names': self.known_face_names
            }
            json.dump(data, f)

    def augment_image(self, image):
        """Aumentar una imagen aplicando pequeñas transformaciones"""
        augmented_images = []
        
        # Rotar la imagen
        rows, cols, _ = image.shape
        for angle in [15, -15]:  # Rotar 15 grados en ambas direcciones
            M = cv2.getRotationMatrix2D((cols / 2, rows / 2), angle, 1)
            rotated = cv2.warpAffine(image, M, (cols, rows))
            augmented_images.append(rotated)
        
        # Cambiar el brillo
        bright = cv2.convertScaleAbs(image, alpha=1.2, beta=30)  # Aumentar brillo
        dark = cv2.convertScaleAbs(image, alpha=0.8, beta=-30)   # Reducir brillo
        augmented_images.append(bright)
        augmented_images.append(dark)

        return augmented_images

    def get_face_encoding(self, image):
        """Obtener encoding facial usando OpenCV DNN"""
        blob = cv2.dnn.blobFromImage(image, 1.0, (300, 300), (104.0, 177.0, 123.0))
        self.net.setInput(blob)
        detections = self.net.forward()

        # Si encontramos una detección válida, retornamos el encoding (el mismo cuadro detectado)
        if detections.shape[2] > 0:
            return detections[0, 0, 0, 3:7]  # Solo la primera detección
        return None

    def train(self, images_folder: Path, epochs: int = 1):
        """Generar encodings a partir de imágenes en una carpeta con augmentation y epochs"""
        for epoch in range(epochs):
            print(f"Epoch {epoch+1}/{epochs}")
            for image_file in images_folder.glob("*.png"):  # Ajustar para tus tipos de archivo
                # Extraer solo el nombre de la persona (antes del número)
                name = ''.join([i for i in image_file.stem if not i.isdigit()])  # Esto extrae "Jose" o "Yare"
                print(f"Procesando {image_file} como {name}")

                # Cargar la imagen y generar su encoding
                image = cv2.imread(str(image_file))
                face_encoding = self.get_face_encoding(image)

                if face_encoding is not None:
                    self.known_face_encodings.append(face_encoding.tolist())  # Convertir a lista si es NumPy array
                    self.known_face_names.append(name)

                    # Aplicar augmentación de datos
                    augmented_images = self.augment_image(image)
                    for aug_img in augmented_images:
                        aug_encoding = self.get_face_encoding(aug_img)
                        if aug_encoding is not None:
                            self.known_face_encodings.append(aug_encoding.tolist())
                            self.known_face_names.append(name)
                else:
                    print(f"No se encontró rostro en {image_file}")

        self.save_encodings()

    def compare_encodings(self, detected_encoding):
        """Comparar encodings detectados con los entrenados"""
        min_dist = float("inf")
        best_match = None

        for i, encoding in enumerate(self.known_face_encodings):
            # Comparar mediante distancia euclidiana
            dist = np.linalg.norm(np.array(encoding) - np.array(detected_encoding))
            if dist < min_dist:
                min_dist = dist
                best_match = i

        if min_dist < 0.6:  # Umbral de similitud
            return self.known_face_names[best_match]
        return "Desconocido"

    def recognize(self, image):
        """Reconocer rostros en una imagen"""
        face_encoding = self.get_face_encoding(image)
        if face_encoding is not None:
            name = self.compare_encodings(face_encoding)
            print(f"Rostro reconocido: {name}")
        else:
            print("No se detectó ningún rostro.")

    def process_video(self):
        """Procesar video en tiempo real para reconocimiento facial usando GStreamer"""
        cap = cv2.VideoCapture(self.gst_pipeline, cv2.CAP_GSTREAMER)

        if not cap.isOpened():
            print("Error: No se pudo abrir el pipeline de video.")
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: No se pudo capturar el frame.")
                break

            # Reconocer rostros en el frame actual
            self.recognize(frame)

            # Mostrar el video en tiempo real
            #cv2.imshow('Video', frame)

            # Presionar 'q' para salir del bucle
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    MODEL_PATH = Path("models/res10_300x300_ssd_iter_140000.caffemodel")
    PROTOTXT_PATH = Path("models/deploy.prototxt.txt")
    ENCODINGS_PATH = Path("/var/ghostlycat/face_encodings/encodings.json")
    IMAGES_FOLDER = Path("/var/ghostlycat/face_images/")

    trainer = FaceTrainer(ENCODINGS_PATH, PROTOTXT_PATH, MODEL_PATH)

    # Entrenar los rostros (cargar imágenes de la carpeta)
    trainer.train(IMAGES_FOLDER, epochs=1)  # Aquí puedes especificar las epochs

    # Procesar video en tiempo real usando GStreamer
    trainer.process_video()
