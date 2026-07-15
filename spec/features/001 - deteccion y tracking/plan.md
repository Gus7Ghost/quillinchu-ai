# Plan de Implementación: Detección y Tracking (001)

## Arquitectura Propuesta

1. **Captura de Video (VideoCapture Async)**:
   - Crear una clase/módulo para conectarse al stream UDP (`udp://@:5600` o la URL configurada).
   - Implementar la lectura en un hilo o proceso separado para asegurar que siempre se tenga el frame más reciente sin latencia acumulada (limpiar el buffer del stream).

2. **Procesamiento e Inferencia (Visión Pipeline)**:
   - Instanciar el modelo YOLOv8 cargando `HeadDetect.pt`.
   - Por cada frame recibido, ejecutar la predicción.
   - Pasar los bounding boxes y confianzas generadas a Deep SORT para actualizar el estado de los tracks y obtener los IDs asignados.

3. **Mecanismo de Desacoplamiento (Productor-Consumidor)**:
   - Crear una cola (`multiprocessing.Queue` o `asyncio.Queue` si todo es asíncrono, dado que MAVSDK es asíncrono, se evaluará el mejor enfoque según el costo computacional de YOLO).
   - El productor (Visión) insertará el último estado del target (Bounding box, ID, timestamp) en la cola.
   - El consumidor (Control/Navegación, a desarrollarse posteriormente) leerá siempre el dato más reciente sin bloquearse.

## Archivos a Crear/Modificar
- `src/vision/camera.py`: Manejo de la conexión UDP/RTSP y extracción de frames (Productor de frames).
- `src/vision/detector.py`: Wrapper para YOLOv8 y carga de pesos.
- `src/vision/tracker.py`: Integración de Deep SORT.
- `src/vision/pipeline.py`: Orquestador que une cámara, detector y tracker, y publica los resultados en una cola compartida.
- `tests/test_vision.py`: Pruebas unitarias simulando un stream de video y verificando la lógica de tracking.
