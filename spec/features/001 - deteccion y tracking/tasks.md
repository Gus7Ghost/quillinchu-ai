# Tareas: Detección y Tracking (001)

- [ ] **1. Captura de Stream de Red**
  - [ ] Implementar la clase `CameraStream` en `src/vision/camera.py`.
  - [ ] Configurar OpenCV (con GStreamer si es necesario) para capturar el stream UDP de Rosetta Drone (`udp://127.0.0.1:5600`).
  - [ ] Implementar lectura asíncrona/multihilo para evitar latencia por acumulación en el buffer.

- [ ] **2. Detección con YOLOv8**
  - [ ] Implementar la clase `HeadDetector` en `src/vision/detector.py`.
  - [ ] Integrar el modelo pre-entrenado personalizado `HeadDetect.pt`.
  - [ ] Crear pruebas unitarias con frames estáticos de validación.

- [ ] **3. Tracking con Deep SORT**
  - [ ] Implementar el wrapper `SortTracker` en `src/vision/tracker.py`.
  - [ ] Conectar los resultados de YOLOv8 (bboxes) para actualizar los tracks.
  - [ ] Asegurar que los IDs se mantengan de manera persistente entre frames sucesivos.

- [ ] **4. Pipeline y Concurrencia**
  - [ ] Construir la clase `VisionPipeline` en `src/vision/pipeline.py`.
  - [ ] Implementar el patrón Productor-Consumidor con colas no bloqueantes (`multiprocessing.Queue` o similar).
  - [ ] Validar experimentalmente que el pipeline funcione al menos a 15 Hz sin bloquear el hilo principal.
