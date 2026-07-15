# Especificación: Detección y Tracking (001)

## Objetivo
Implementar la captura, detección y seguimiento en tiempo real de personas mediante visión artificial. Se utilizará YOLOv8 con el modelo personalizado `HeadDetect.pt` para la detección de cabezas y Deep SORT para mantener el seguimiento continuo con IDs únicos.

## Requisitos y Restricciones
- **Fuente de Video**: El flujo de video no es local. Proviene del DJI Air 2S mediante la retransmisión UDP de Rosetta Drone (puerto 5600) o RTSP. La captura debe configurarse para recibir este stream de red.
- **Modelo de IA**: YOLOv8 inferenciando con pesos personalizados (`HeadDetect.pt`).
- **Tracking**: Deep SORT para la asignación persistente de IDs únicos.
- **Rendimiento**: La inferencia debe estar optimizada para ejecutarse en tiempo real (> 15 Hz).
- **Concurrencia**: Obligatorio implementar un patrón Productor-Consumidor (usando `asyncio` o `multiprocessing.Queue`). El procesamiento de imagen pesado (productor) debe estar totalmente desacoplado del lazo de control de vuelo (consumidor) para no ralentizar la emisión de comandos MAVSDK.

## Entradas y Salidas
- **Entrada**: Frames obtenidos asíncronamente del stream UDP/RTSP.
- **Salida**: Bounding boxes (cajas delimitadoras) correspondientes a las detecciones de cabezas, asociadas a un ID único de tracking temporal y la marca de tiempo (timestamp).
