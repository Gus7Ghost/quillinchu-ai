# 002 · Módulo de Control MAVLink y Guiado — Plan

## Enfoque

Se implementará un lazo de control de vuelo desacoplado, basándose firmemente sobre programación no bloqueante y concurrencia[cite: 1]. El módulo consumirá la cola de salida del `VisionPipeline` (patrón Productor-Consumidor)[cite: 3]. Se utilizará `pymavlink` para interactuar con ArduPilot, instanciando un hilo de fondo (daemon) exclusivo para emitir la señal de vida (Heartbeat) requerida por el protocolo.

## Implementación

1. **Gestión de telemetría y conexión (`MavlinkController`)** — `src/control/mavlink_controller.py`. Implementar una clase que administre el socket de red, lance el hilo asíncrono para el Heartbeat a 1 Hz y despache comandos mediante `SET_POSITION_TARGET_LOCAL_NED`.
2. **Cálculo de Leyes de Guiado (`GuidanceLaw`)** — `src/control/guidance_law.py`. Implementar los algoritmos matemáticos que toman el error en píxeles $(e_x, e_y)$ y calculan comandos de velocidad empleando controladores con zonas muertas (deadband) y saturación de seguridad.
3. **Pruebas simétricas y unitarias** — `tests/test_control.py`. Desarrollar pruebas automáticas en espejo[cite: 1, 3] utilizando `unittest.mock` para validar la emisión MAVLink y el cálculo matemático de velocidades sin requerir hardware físico ni el simulador SITL activo.

## Decisiones

- **Uso de pymavlink nativo en lugar de abstracciones pesadas** — Se optó por `pymavlink` para tener control absoluto a bajo nivel sobre el envío de tramas asíncronas MAVLink; se descartó expresamente el uso de DroneKit por ser una dependencia prohibida[cite: 3].
- **Patrón de concurrencia de Hilo Dedicado (Daemon) para Heartbeat** — Garantiza que aunque el lazo de visión sufra una caída temporal de FPS, el dron no interprete una pérdida de conexión de la estación terrena y active un *Failsafe* no deseado.

## Riesgos

- **Bloqueos asíncronos por pérdida de red** — El manejo de errores asíncronos debe encapsular los envíos a la controladora en bloques `try-except` para evitar que la pérdida de telemetría congele el sistema completo[cite: 3].
- **Respuestas inestables del controlador** — El uso de aproximaciones empíricas está prohibido[cite: 1]. Los parámetros proporcionales del guiado deben poder tunearse y sustentarse matemáticamente.