# Especificación: Detección y Tracking (001)

## Objetivo
Implementar la detección en tiempo real de personas mediante YOLOv8 utilizando el modelo personalizado `HeadDetect.pt`, y realizar el seguimiento continuo mediante IDs únicos asignados por Deep SORT.

## Requisitos de Diseño
- **Entrada**: Frames de video de la cámara del dron.
- **Salida**: Bounding box de la detección de cabeza con ID único de tracking.
- **Modelo**: Inferencia ligera optimizada para ejecución en tiempo real a > 15 Hz.
- **Desacoplamiento**: El procesamiento de frames debe correr en un proceso o hilo separado (productor) para no bloquear el control de vuelo (consumidor).
