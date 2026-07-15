# 001 · Detección y Tracking — Tareas

_Checklist accionable derivada del `plan.md`. Tareas pequeñas y concretas; marca `[x]` al completarlas._

- [ ] Implementar clase `CameraStream` en `src/vision/camera.py` con lectura asíncrona (stream UDP `udp://127.0.0.1:5600`).
- [ ] Implementar clase `HeadDetector` en `src/vision/detector.py` integrando YOLOv8 y el modelo `HeadDetect.pt`.
- [ ] Implementar wrapper `SortTracker` en `src/vision/tracker.py` conectando las inferencias de YOLOv8 para mantener IDs únicos.
- [ ] Construir clase `VisionPipeline` en `src/vision/pipeline.py` implementando el patrón Productor-Consumidor con colas no bloqueantes.
- [ ] Implementar pruebas unitarias en `tests/test_vision.py` validando la lógica de tracking y persistencia de IDs.
- [ ] Validar experimentalmente el rendimiento del pipeline (> 15 Hz) para asegurar que no hay latencia acumulada.
- [ ] Validar contra los criterios de aceptación y restricciones de red/concurrencia de `spec.md`.
- [ ] Mover la feature a "Hecho" en `../../constitution/roadmap.md`.

## Mantenimiento (checklist recurrente)

_Opcional. Pasos a repetir cada vez que se toque esta feature en el futuro (revisar datos, regenerar algo, etc.). Borra esta sección si no aplica._

- [ ] Re-verificar la compatibilidad del pipeline GStreamer/OpenCV ante cualquier cambio de entorno o red.
- [ ] Perfilar el rendimiento (> 15 Hz) si se actualizan los pesos de `HeadDetect.pt` o se cambia de hardware base.
