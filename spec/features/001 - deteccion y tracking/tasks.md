# 001 · Detección y Tracking — Tareas

_Checklist accionable derivada del `plan.md`. Tareas pequeñas y concretas; marca `[x]` al completarlas._

- [x] Implementar la clase `CameraReader` en `src/vision/camera_reader.py` utilizando un pipeline de GStreamer para capturar el stream RTP/H.264 de Rosetta Drone en el puerto UDP 5600.
- [x] Diseñar el método de lectura asíncrona de frames para descartar activamente el buffer antiguo de OpenCV y garantizar el acceso al frame más reciente en tiempo real.
- [x] Implementar la clase `HeadDetector` en `src/vision/detector.py` cargando los pesos personalizados `HeadDetect.pt` mediante la biblioteca `ultralytics` para la inferencia de cajas delimitadoras.
- [x] Implementar el wrapper `DeepSortTracker` en `src/vision/tracker.py` para asociar detecciones y mantener identificadores únicos (IDs) estables ante oclusiones temporales.
- [x] Construir la clase `VisionPipeline` en `src/vision/pipeline.py` implementando el patrón Productor-Consumidor para publicar asíncronamente la información del objetivo (ID, bbox, timestamp) en una cola compartida.
- [x] Implementar pruebas unitarias en `tests/test_vision.py` utilizando generadores de frames simulados (mocks) para validar la consistencia de los IDs de tracking y descartar fugas de memoria.
- [x] Validar experimentalmente en la laptop de desarrollo del laboratorio que la tasa de procesamiento del pipeline de visión supere holgadamente la meta científica de los 15 Hz.
- [ ] Validar contra los criterios de aceptación de `spec.md`.
- [ ] Mover la feature a "Hecho" en `../../constitution/roadmap.md`.

## Mantenimiento (checklist recurrente)

_Opcional. Pasos a repetir cada vez que se toque esta feature en el futuro (revisar datos, regenerar algo, etc.). Borra esta sección si no aplica._

- [ ] Re-verificar la compatibilidad y configuración del pipeline de GStreamer/OpenCV ante cualquier cambio en el direccionamiento IP de la tablet o restricciones del cortafuegos de Ubuntu.
- [ ] Volver a perfilar el rendimiento computacional (Hz) y latencia del pipeline de visión si se actualizan los pesos de `HeadDetect.pt` o se realiza un cambio de hardware base en el laboratorio.