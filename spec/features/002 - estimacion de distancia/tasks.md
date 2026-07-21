# 002 · Módulo de Control MAVLink y Guiado — Tareas

- [ ] Implementar la clase `MavlinkController` en `src/control/mavlink_controller.py` para la gestión de sockets de telemetría y emisión de comandos `BODY_NED`[cite: 3].
- [ ] Configurar el bucle secundario (`daemon=True`) dentro de `MavlinkController` para enviar ininterrumpidamente la señal de Heartbeat a 1 Hz.
- [ ] Implementar la clase `GuidanceLaw` en `src/control/guidance_law.py` con el algoritmo Proporcional, zonas muertas y límites físicos de saturación de velocidad.
- [ ] Desarrollar la suite simétrica de pruebas en `tests/test_control.py` para verificar el envío de tramas MAVLink mockeadas y validar la matemática del controlador sin drones físicos[cite: 3].
- [ ] Verificar exhaustivamente el cumplimiento de tipado estricto (Type Hints) y formato PEP 8 mediante las herramientas `black` y `flake8`[cite: 3].
- [ ] Validar contra los criterios de aceptación de `spec.md`.
- [ ] Actualizar el estado de la feature en `../../constitution/roadmap.md`.

## Mantenimiento (checklist recurrente)

- [ ] Recalibrar las ganancias Proporcionales (Kp) en `GuidanceLaw` ante cambios físicos en el dron (peso adicional, cambio de hélices).
- [ ] Verificar la compatibilidad de los mensajes `SET_POSITION_TARGET_LOCAL_NED` si se actualiza el firmware de ArduPilot en el hardware.