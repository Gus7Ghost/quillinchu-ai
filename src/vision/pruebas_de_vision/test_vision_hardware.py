"""
Script de validación visual de hardware — Quillinchu AI.

Ejecuta los módulos de visión en vivo leyendo desde Rosetta Drone
y dibuja las cajas delimitadoras y los IDs en una ventana de OpenCV
para validar los criterios de aceptación en el laboratorio.

Uso:
    python src/test_vision_hardware.py
"""

import logging
import time
import cv2
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.vision.camera_reader import CameraReader
from src.vision.detector import HeadDetector
from src.vision.tracker import DeepSortTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestHardware")

def main():
    logger.info("Iniciando componentes de visión...")
    
    # 1. Configurar Cámara (Asegúrate de que Rosetta Drone envíe a UDP 5600)
    camera = CameraReader(port=5600)
    
    # 2. Configurar Detector (Requiere tener HeadDetect.pt en la raíz del proyecto)
    try:
        detector = HeadDetector(weights_path="HeadDetect.pt", confidence=0.5)
    except Exception as e:
        logger.error(f"Error cargando YOLO (¿Falta HeadDetect.pt?): {e}")
        return

    # 3. Configurar Tracker
    tracker = DeepSortTracker(max_age=30)
    
    # Iniciar captura
    try:
        camera.start()
    except RuntimeError as e:
        logger.error(e)
        return

    logger.info("Esperando flujo de video... (Presiona 'q' en la ventana para salir)")
    
    frame_count = 0
    start_time = time.perf_counter()
    fps = 0.0

    try:
        while True:
            ret, frame = camera.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue
            
            # --- Procesamiento ---
            detections = detector.detect(frame)
            targets = tracker.update(detections, frame)
            
            # --- Dibujo para Validación ---
            for target in targets:
                x_min, y_min, x_max, y_max = target.bbox
                track_id = target.track_id
                
                # Dibujar rectángulo
                cv2.rectangle(
                    frame, 
                    (int(x_min), int(y_min)), 
                    (int(x_max), int(y_max)), 
                    (0, 255, 0), 2
                )
                # Dibujar ID
                cv2.putText(
                    frame, 
                    f"ID: {track_id}", 
                    (int(x_min), int(y_min) - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, (0, 255, 0), 2
                )

            # --- Calcular y Mostrar FPS ---
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

            cv2.imshow("Validacion LabIAR - Vision", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        camera.stop()
        cv2.destroyAllWindows()
        logger.info("Prueba de hardware finalizada.")

if __name__ == "__main__":
    main()
