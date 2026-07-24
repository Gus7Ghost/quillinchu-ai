# 006 · Orquestador Central — Plan

## Enfoque

Se desarrollará un script de entrada (`src/main.py`) basado puramente en la biblioteca `asyncio`. El hilo del `VisionPipeline` (Productor, Feature 001) publica `List[TargetState]` en una `queue.Queue` thread-safe. El lazo principal (Consumidor) corre sobre `asyncio`, consumiendo los frames detectados con `get_nowait()`, calculando el esfuerzo de control con `GuidanceLaw`, pasándolo por la aduana del `SafetyFilter`, enviándolo al dron vía `MavlinkController` y registrando el rendimiento en el `MetricsLogger`.

## Implementación

1. **Configuración Inicial:** Configurar el sistema de `logging` (nivel INFO) en consola con formato `%(asctime)s [%(levelname)s] %(name)s — %(message)s` para monitorizar el estado en vivo.
2. **Inyección de Dependencias:** Instanciar todos los componentes dentro de `async def main()`:
    - `GuidanceParams` y `SafetyParams` (dataclasses inmutables con defaults conservadores).
    - `CameraReader(port=5600, width=1280, height=720)`.
    - `HeadDetector(weights_path="HeadDetect.pt", confidence=0.5, device="cpu")`.
    - `DeepSortTracker(max_age=30, n_init=3, max_cosine_distance=0.3)`.
    - `queue.Queue[List[TargetState]](maxsize=1)` — cola thread-safe.
    - `VisionPipeline(camera, detector, tracker, output_queue, max_queue_size=1)`.
    - `MavlinkController(system_address="udp://:14540", connection_timeout_s=15.0)`.
    - `GuidanceLaw(params=guidance_params)`.
    - `SafetyFilter(params=safety_params)`.
    - `MetricsLogger()`.
3. **Arranque:**
    - `camera.start()` y `vision_pipeline.start()` — lanzan hilos daemon.
    - `await mavlink.connect()` — conexión asíncrona MAVSDK.
    - `await mavlink.start_offboard()` — setpoint cero inicial + activación.
4. **Lazo de Control (Consumer, `while True`):**
    - `detection_queue.get_nowait()` con `except queue.Empty: pass` — no bloqueante.
    - Si hay detecciones → actualizar `last_target_time = time.time()` y calcular errores (eₓ, eᵧ).
    - `guidance.compute(targets)` → `VelocityCommand` crudo (o `None` → hover default).
    - `safety.apply(cmd, last_target_time, current_time)` → comando validado y saturado.
    - `await mavlink.send_velocity_cmd(safe_cmd)` — envío asíncrono.
    - `metrics.log_iteration(dt, error_x, error_y, vel_forward, vel_yaw)` — registro en RAM.
    - `await asyncio.sleep(0.033)` — ~30 Hz.
5. **Cierre Seguro (Graceful Shutdown):** Bloque `try…except…finally`:
    - `except asyncio.CancelledError` — captura cancelación limpia.
    - `except Exception` — captura errores inesperados con `exc_info=True`.
    - `finally`:
        - `await mavlink.close()` — Offboard stop + cancelar monitor.
        - `vision_pipeline.stop()` y `camera.stop()` — terminar hilos.
        - `metrics.export_to_csv(params=guidance_params)` — exportar CSV.
    - Cada paso del `finally` envuelto en su propio `try/except` para garantizar que un fallo parcial no impida los demás.

## Decisiones

- **`time.time()` para SafetyFilter:** Aunque `TargetState.timestamp` usa `perf_counter` (interno de `GuidanceLaw` para dt del PID), el `SafetyFilter.apply()` documenta sus argumentos como "epoch, segundos". Se usa `time.time()` para `last_target_time` y `current_time`, que son una pareja independiente y consistente para el cálculo del timeout de failsafe.
- **Un solo hilo asíncrono para el Consumidor:** Para evitar condiciones de carrera, la lectura de la cámara se ejecuta en su hilo daemon (como fue diseñado en la Feature 001), mientras que todo el lazo de control PID y telemetría corre en el hilo principal de `asyncio`.
- **`queue.Queue` (threading), no `asyncio.Queue`:** La cola conecta un hilo de OS (VisionPipeline) con el event loop de asyncio. Se usa `get_nowait()` + `asyncio.sleep()` para evitar bloquear el event loop.
- **Shutdown resiliente:** Cada recurso se libera en su propio bloque `try/except` para que una falla al cerrar MAVLink no impida exportar las métricas.

## Riesgos

- **Bloqueo del lazo principal:** Si alguna función matemática tarda más de 66 ms (15 Hz), el dron se volverá inestable. *Mitigación:* Ya hemos verificado en tests anteriores que las funciones matemáticas puras (PID, Safety) tardan fracciones de milisegundo.
- **Consistencia de relojes:** El `GuidanceLaw` usa `perf_counter` para el dt del PID (vía `TargetState.timestamp`), mientras el `SafetyFilter` usa `time.time()`. Ambos pares son internamente consistentes y no se mezclan entre sí.