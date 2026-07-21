# Roadmap

_Orden y estado de las features. Es la vista de "qué hay hecho, qué toca ahora y qué viene". Cada entrada apunta a su carpeta en `features/`._

## Hecho ✅

_Features completadas, en orden de implementación._

1. **[001 · Detección y Tracking](../features/001%20-%20deteccion%20y%20tracking/)** — Implementación de la captura asíncrona de video (Rosetta Drone), inferencia YOLOv8 (`HeadDetect.pt`) y seguimiento continuo mediante Deep SORT.
2. **[002 · Módulo de Control MAVLink y Guiado](../features/002%20-%20estimacion%20de%20distancia/)** — Comunicación asíncrona mediante MAVSDK-Python (`MavlinkController`), activación del modo Offboard, y ley de guiado proporcional (`GuidanceLaw`) con deadband y clamping de seguridad en el marco BODY_NED.

## Siguiente 🔜

_Lo próximo a abordar. Idealmente una sola feature "en curso" a la vez._

1. **[003 · Control de Vuelo PID](../features/003%20-%20control%20de%20vuelo%20pid/)** — Implementación de controladores PID independientes y sintonización de la respuesta dinámica del dron.

## Backlog / ideas 💡

_Sin comprometer ni ordenar del todo. Ideas que respetan la constitución._

- **[004 · Métricas Científicas](../features/004%20-%20metricas%20cientificas/)** — Reportes automatizados de rendimiento del sistema (Hz, latencia y RMSE).
- **[005 · Contingencias de Seguridad](../features/005%20-%20contingencias%20de%20seguridad/)** — Limitadores de velocidad, geofencing 3D y lógica de hovering autónomo por pérdida de tracking.

> Cada feature nueva se crea como `features/NNN-nombre-feature/` con `spec.md`, `plan.md` y `tasks.md` antes de tocar código.
