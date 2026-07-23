# 003 · Control de Vuelo PID — Tareas

- [x] Crear el módulo `src/control/pid.py` definiendo la clase abstracta/matemática `PIDController`.
- [x] Implementar la protección *Anti-Windup* en el acumulador del término Integral dentro de `PIDController`.
- [x] Implementar el filtro paso-bajo (Low-Pass Filter) en el cálculo del término Derivativo.
- [x] Actualizar el dataclass `GuidanceParams` en `src/control/guidance_law.py` para incluir parámetros $K_i$, $K_d$ y configuración del filtro.
- [x] Refactorizar la clase `GuidanceLaw` para instanciar y utilizar un `PIDController` para el eje Yaw y otro para el eje Forward.
- [x] Modificar el método `compute()` de `GuidanceLaw` para calcular el $dt$ real utilizando los `timestamp` de `TargetState`.
- [x] Desarrollar la suite de pruebas unitarias matemáticas en `tests/test_pid.py`.
- [x] Actualizar los tests rotos en `tests/test_control.py` derivados de la refactorización de `GuidanceLaw`.
- [x] Verificar el cumplimiento de tipado estricto (Type Hints) y ejecutar `black` y `flake8`.
- [x] Validar contra los criterios de aceptación de `spec.md`.
- [x] Actualizar el estado de la feature a "Hecho" y reordenar en `../../constitution/roadmap.md`.

## Mantenimiento (checklist recurrente)

- [ ] Utilizar métodos rigurosos de sintonización (ej. Ziegler-Nichols o simulaciones paso a paso en SITL) para encontrar los valores óptimos de $K_p$, $K_i$ y $K_d$ antes de cualquier prueba en vuelo real.