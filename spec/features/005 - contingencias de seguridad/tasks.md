# 005 · Contingencias de Seguridad — Tareas

- [ ] Crear la estructura del módulo `src/safety/` con su archivo `__init__.py`.
- [ ] Definir el dataclass `SafetyParams` en `src/safety/filter.py` con los límites de velocidad y el tiempo de tolerancia de pérdida visual.
- [ ] Implementar la clase `SafetyFilter` y su método `apply()` para realizar el *clamping* estricto de las velocidades `forward`, `right`, `down` y `yawspeed`.
- [ ] Integrar la lógica del *Hovering Autónomo* en `apply()`: retornar ceros absolutos si `current_time - last_target_time > failsafe_timeout_s`.
- [ ] Refactorizar `src/control/guidance_law.py`: Eliminar el método interno `_clamp` y transferir los atributos de límite (`max_yaw_rate`, `max_linear_speed`) al nuevo módulo de seguridad.
- [ ] Actualizar los tests rotos en `tests/test_control.py` derivados de la eliminación del clamping interno del PID.
- [ ] Desarrollar la nueva suite `tests/test_safety.py` para verificar todas las fronteras de recorte matemático y la activación del failsafe.
- [ ] Ejecutar `black`, `flake8` y comprobación de `mypy` (Type Hints) en el nuevo módulo.
- [ ] Validar contra los criterios de aceptación de `spec.md`.
- [ ] Actualizar el estado de la feature en `../../constitution/roadmap.md`.

## Mantenimiento (checklist recurrente)

- [ ] Antes de cualquier prueba en exteriores (campus de la UNI), revisar y ajustar los umbrales de seguridad en `SafetyParams` según las condiciones del viento y el perímetro disponible.