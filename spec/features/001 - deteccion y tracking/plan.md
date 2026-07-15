# 001 · Detección y Tracking — Plan

_Cómo se implementa lo descrito en `spec.md`. Debe respetar la `constitution/`._

## Enfoque

Se implementará un pipeline de visión asíncrono e independiente del lazo de control utilizando el patrón Productor-Consumidor. El Productor (captura de video, inferencia YOLOv8 y tracking con Deep SORT) se ejecutará en un hilo o proceso dedicado utilizando `asyncio` y colas compartidas (`multiprocessing.Queue` o similar). Esto garantiza que la carga computacional del procesamiento de imágenes no introduzca latencia ni bloquee la ejecución de los comandos de vuelo en tiempo real (MAVSDK). La captura de video leerá de manera asíncrona el flujo de red UDP de Rosetta Drone (puerto 5600) o RTSP del DJI Air 2S sin asumir una cámara local (webcam).

## Implementación

_Pasos técnicos concretos, en orden. Indica los archivos/módulos que se tocan._

1. **Captura asíncrona de video** — `src/vision/camera.py`. Implementación de la captura del stream de red `udp://127.0.0.1:5600` en un hilo separado para desechar frames antiguos y asegurar el acceso al frame más reciente.
2. **Detección de cabezas** — `src/vision/detector.py`. Integración de YOLOv8 de Ultralytics cargando los pesos personalizados `HeadDetect.pt` para la predicción de cajas delimitadoras.
3. **Seguimiento continuo** — `src/vision/tracker.py`. Integración de Deep SORT para asociar detecciones y asignar IDs únicos estables entre frames.
4. **Orquestación y Comunicación** — `src/vision/pipeline.py`. Acoplamiento de cámara, detector y tracker en un pipeline unificado que publique de forma asíncrona la información del objetivo (ID, bbox, timestamp) a una cola compartida.
5. **Pruebas de Validación** — `tests/test_vision.py`. Suite de pruebas unitarias que simulan la captura de video y verifican la consistencia de los IDs de tracking y que la velocidad de procesamiento supere los 15 Hz.

## Decisiones

_Elecciones de diseño relevantes y su justificación. Alternativas descartadas y por qué._

- **Pipeline de visión desacoplado en hilo/proceso independiente** — Se elige este patrón debido al alto consumo computacional de YOLOv8 y Deep SORT. Ejecutar la inferencia secuencialmente en el mismo hilo de control asíncrono de MAVSDK provocaría retrasos inaceptables y peligrosos en los comandos de vuelo. Se descartó el flujo síncrono tradicional.
- **Captura nativa de stream UDP** — Se diseña la cámara para conectarse directamente a la retransmisión de Rosetta Drone en lugar de una webcam por ID de dispositivo (`cv2.VideoCapture(0)`). Se descartó asumir cámara local ya que el dron físico DJI Air 2S transmite exclusivamente por red.
- **Uso de modelo enfocado en la cabeza (`HeadDetect.pt`)** — Se utiliza detección de cabezas para dar sustento geométrico a la posterior estimación de distancia (~0.23 m de diámetro), descartando el uso de cuerpo completo (1.68 m) que genera distorsiones severas desde ángulos de visión cenitales u oblicuos.

## Riesgos

_Qué puede salir mal o requerir cuidado, y cómo se mitiga._

- **Latencia acumulada por buffering de OpenCV en red** — OpenCV acumula frames en su cola interna si la lectura es más lenta que la tasa de transmisión del stream. **Mitigación**: Implementar una lectura en hilo dedicado que descarte activamente los frames no procesados para asegurar que el detector siempre reciba el frame en tiempo real más actual.
- **Sobrecarga de CPU/GPU que degrade los FPS de visión** — La inferencia de IA puede reducir la tasa de procesamiento por debajo del límite de control de vuelo. **Mitigación**: Utilizar un modelo YOLOv8 ligero (nano/segmento optimizado) y medir la latencia de inferencia en el generador de métricas científicas, asegurando mantener la tasa > 15 Hz.
