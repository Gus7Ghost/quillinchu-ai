# 001 · Detección y Tracking — Plan

_Cómo se implementa lo descrito en `spec.md`. Debe respetar la `constitution/`._

## Enfoque

Se implementará un pipeline de visión asíncrono e independiente del lazo de control utilizando el patrón Productor-Consumidor. El Productor (captura de video, inferencia YOLOv8 y tracking con Deep SORT) se ejecutará en un hilo o proceso dedicado utilizando `asyncio` y colas compartidas (`multiprocessing.Queue` o similar). Esto garantiza que la alta carga computacional de la inferencia de Inteligencia Artificial no introduzca latencia ni bloquee la ejecución de los comandos de vuelo en tiempo real administrados por MAVSDK. La captura de video leerá de manera asíncrona la retransmisión de red local H.264 de Rosetta Drone (puerto UDP 5600) proveniente del DJI Air 2S, descartando cámaras web locales.

## Implementación

_Pasos técnicos concretos, en orden. Indica los archivos/módulos que se tocan._

1. **Configuración de la captura de video por red (GStreamer)** — `src/vision/camera_reader.py`. Implementar una clase asíncrona que inicialice la captura de OpenCV utilizando un pipeline de GStreamer para escuchar el puerto UDP 5600, gestionando la decodificación del flujo RTP/H.264.
2. **Implementación de la detección de cabezas (YOLOv8)** — `src/vision/detector.py`. Diseñar la clase detector encargada de cargar los pesos personalizados `HeadDetect.pt` mediante la biblioteca `ultralytics` y realizar la inferencia sobre los frames recibidos, devolviendo tensores con coordenadas de cajas delimitadoras.
3. **Configuración de seguimiento multiobjetivo (Deep SORT)** — `src/vision/tracker.py`. Integrar el algoritmo de asociación temporal Deep SORT para registrar los identificadores únicos (IDs) estables de las cabezas detectadas y mitigar el efecto de oclusiones temporales.
4. **Orquestación del pipeline de visión (Productor-Consumidor)** — `src/vision/pipeline.py`. Acoplar la lectura de video, inferencia y tracking en un orquestador que publique asíncronamente el estado del objetivo (ID, bbox, timestamp) en una cola de multiprocesamiento para el consumo no bloqueante del módulo de control de vuelo.
5. **Suite de pruebas unitarias y validación de Hz** — `tests/test_vision.py`. Desarrollar pruebas unitarias utilizando mocks de video para validar la consistencia del asignador de IDs de tracking, descartar fugas de memoria y certificar que la tasa de procesamiento supere el mínimo científico de 15 Hz.

## Decisiones

_Elecciones de diseño relevantes y su justificación. Alternativas descartadas y por qué._

- **Pipeline de visión asíncrono y desacoplado** — Se decide procesar la visión en un hilo o proceso independiente mediante colas compartidas para evitar retrasos en el lazo de control de MAVSDK; se descartó el enfoque síncrono secuencial tradicional debido a que el alto costo computacional del pipeline de IA congelaría el envío constante de comandos de vuelo.
- **Captura nativa mediante GStreamer UDP** — Se implementa la decodificación de red local RTP/H.264 por el puerto 5600; se descartó asumir una cámara física local o webcam (ID 0) dado que el dron físico DJI Air 2S transmite inalámbricamente su video a la tablet, la cual es retransmitida por red local usando Rosetta Drone.
- **Uso de modelo enfocado en el diámetro cefálico (`HeadDetect.pt`)** — Se utiliza la detección de cabezas con un diámetro de $\approx 0.23$ m para calcular distancias relativas; se descartó la detección de cuerpo completo (altura promedio de 1.68 m) porque la perspectiva aérea y los cambios de actitud del dron generan graves distorsiones ópticas en la estimación de altura.

## Riesgos

_Qué puede salir mal o requerir cuidado, y cómo se mitiga._

- **Latencia acumulada por buffering de OpenCV en red** — Implementar un lector de video asíncrono en un hilo dedicado (thread de captura continua) que descarte los frames que no puedan procesarse a tiempo, garantizando que YOLOv8 siempre evalúe el frame en tiempo real más reciente.
- **Sobrecarga computacional y caída de FPS de visión** — Optimizar la inferencia del modelo YOLOv8 utilizando arquitecturas ligeras o formatos compilados (ONNX) para correr en la CPU i7-1165G7 de la laptop del laboratorio de manera holgada por encima de la meta mínima de 15 Hz, monitoreando continuamente su rendimiento con el módulo de métricas científicas.