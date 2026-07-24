# 006 · Orquestador Central

**Estado:** en curso

## Qué hace

Crea el punto de entrada principal del sistema (`src/main.py`). Se encarga de instanciar todos los subsistemas (Visión, Control, Seguridad, Métricas y Comunicación) y conectarlos mediante el patrón Productor-Consumidor. Gestiona el ciclo de vida completo de la aeronave: conexión inicial, activación del modo Offboard, lazo infinito de control a más de 15 Hz y, lo más importante, el apagado seguro y exportación de telemetría al interceptar la señal de cancelación del usuario (Ctrl+C).

## Por qué

Actualmente, Quillinchu AI es un conjunto de piezas de software de alta calidad (PID, YOLOv8, filtros de seguridad), pero están aisladas. El orquestador es el "sistema nervioso" que permite que los datos fluyan de la cámara a los motores en tiempo real. 

## Arquitectura de datos

```
┌─────────────────────────────┐
│  VisionPipeline (hilo daemon) │
│  CameraReader → HeadDetector  │
│  → DeepSortTracker             │
└──────────┬──────────────────┘
           │ queue.Queue[List[TargetState]]
           ▼  (no bloqueante, maxsize=1)
┌─────────────────────────────┐
│  Lazo asyncio (main)         │
│  ┌─ GuidanceLaw.compute() ─┐ │
│  │  → VelocityCommand (raw) │ │
│  └──────────┬───────────────┘ │
│             ▼                 │
│  ┌─ SafetyFilter.apply() ──┐ │
│  │  → VelocityCommand (safe)│ │
│  └──────────┬───────────────┘ │
│             ▼                 │
│  MavlinkController            │
│  .send_velocity_cmd(safe)     │
│             │                 │
│  MetricsLogger.log_iteration()│
└─────────────────────────────┘
```

## Criterios de aceptación

### Comportamiento observable y comprobable
- [x] ¿El script `main.py` se ejecuta sin errores de sintaxis o importación?
- [ ] ¿El sistema logra iniciar la captura de video asíncrona y la telemetría MAVSDK de forma simultánea?
- [ ] ¿Al presionar `Ctrl+C` (KeyboardInterrupt), el dron detiene el modo Offboard, cierra la conexión asíncrona y exporta el archivo CSV de métricas exitosamente?

### Caso límite o de error contemplado
- [x] ¿El bucle principal maneja correctamente los instantes donde la cola de visión está vacía (sin saturar la CPU)?
- [x] ¿El apagado seguro se ejecuta incluso si ocurre una excepción inesperada durante el vuelo?

### Requisito de calidad
- [x] ¿El archivo cumple con PEP 8 y Type Hints?
- [x] ¿Se evita instanciar dependencias o lógicas pesadas directamente en el `main.py` (manteniéndolo solo como un inyector de dependencias)?

## Fuera de alcance
- Implementación de Interfaz Gráfica (GUI). El orquestador se ejecutará netamente desde la terminal de comandos para ahorrar recursos de CPU.