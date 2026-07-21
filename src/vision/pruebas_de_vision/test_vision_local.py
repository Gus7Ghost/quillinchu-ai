"""
Script de simulación local de visión — Quillinchu AI (Modo Casa).

Lee desde la cámara del celular (IP Webcam) o video simulado,
usa YOLOv8n como fallback y rastrea objetivos con Deep SORT.

Uso:
    python test_vision_local.py
"""

import logging
import time
import cv2
import sys
import os
import threading

# Asegurar importación de módulos en src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.vision.detector import HeadDetector
from src.vision.tracker import DeepSortTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestVisionLocal")

# ⚠️ Cambia esta IP por la que te da la app IP Webcam en tu Redmi 13
CAM_URL = "http://192.168.0.77:8080/video"

class ThreadedCamera:
    def __init__(self, src):
        self.cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
        self.ret = False
        self.frame = None
        if self.cap.isOpened():
            self.ret, self.frame = self.cap.read()
        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while self.running:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.ret = ret
                        self.frame = frame.copy()
            else:
                time.sleep(0.01)

    def read(self):
        with self.lock:
            return self.ret, self.frame

    def isOpened(self):
        return self.cap.isOpened()

    def release(self):
        self.running = False
        self.thread.join(timeout=1.0)
        self.cap.release()

def main():
    logger.info("Iniciando simulación de visión local...")

    # 1. Fallback Inteligente para el Detector
    weights_file = "HeadDetect.pt" if os.path.exists("HeadDetect.pt") else "yolov8n.pt"
    logger.info(f"Cargando detector con pesos: {weights_file}")
    
    try:
        detector = HeadDetector(weights_path=weights_file, confidence=0.5)
    except Exception as e:
        logger.error(f"Error inicializando el detector: {e}")
        return

    # 2. Configurar Tracker (Misma clase que usaremos en el dron)
    try:
        tracker = DeepSortTracker(max_age=30)
    except Exception as e:
        logger.error(f"Error inicializando Deep SORT: {e}")
        return

    # 3. Conexión a la Fuente de Video (IP Webcam)
    logger.info(f"Conectando al stream de video: {CAM_URL} (con Threading para cero latencia)")
    cap = ThreadedCamera(CAM_URL)

    if not cap.isOpened():
        logger.error("No se pudo abrir el stream de video. Verifica la IP de tu celular y la red WiFi.")
        return

    logger.info("¡Flujo enganchado! Presiona 'q' en la ventana para salir.\n")

    frame_count = 0
    start_time = time.perf_counter()
    fps = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                logger.warning("Error: No se pudo capturar el frame del celular. (ret=False)")
                time.sleep(0.5)
                continue

            # --- 1. Detección ---
            detections = detector.detect(frame)

            # --- 2. Tracking (Deep SORT) ---
            targets = tracker.update(detections, frame)

            # --- 3. Dibujo de cajas e IDs persistentes ---
            for target in targets:
                x_min, y_min, x_max, y_max = target.bbox
                track_id = target.track_id

                # Dibujar rectángulo verde alrededor del objetivo
                cv2.rectangle(
                    frame,
                    (int(x_min), int(y_min)),
                    (int(x_max), int(y_max)),
                    (0, 255, 0), 2
                )

                # Dibujar ID asignado por Deep SORT
                cv2.putText(
                    frame,
                    f"ID: {track_id}",
                    (int(x_min), max(int(y_min) - 10, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 0), 2
                )

            # --- 4. Cálculo y despliegue de FPS ---
            frame_count += 1
            elapsed = time.perf_counter() - start_time
            if elapsed >= 1.0:
                fps = frame_count / elapsed
                frame_count = 0
                start_time = time.perf_counter()

            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (0, 0, 255), 2
            )

            cv2.imshow("Validacion Local - Quillinchu AI", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("Prueba de visión local finalizada.")

if __name__ == "__main__":
    main()