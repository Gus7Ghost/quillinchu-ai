# 005 · Contingencias de Seguridad — Plan

## Enfoque

Se utilizará el patrón de diseño Middleware. Se creará una clase `SafetyFilter` que actuará como un embudo entre la salida del `GuidanceLaw` (Capa de Control) y la entrada del `MavlinkController` (Capa de Navegación). 

Este filtro mantendrá un registro del tiempo exacto en que se detectó a la persona por última vez. En cada ciclo del lazo de vuelo, evaluará el tiempo transcurrido; si el tiempo excede el límite (pérdida de tracking por oclusión severa o latencia), mutará el comando a ceros absolutos para detener la aeronave. Adicionalmente, asumirá la responsabilidad del "clamping", dejando al `GuidanceLaw` como un módulo de cálculo puramente matemático y abstracto.

## Implementación

1. **Filtro de Seguridad (`SafetyFilter`)** — `src/safety/filter.py`. Desarrollar la clase principal con el método `apply(cmd: VelocityCommand, last_target_time: float, current_time: float) -> VelocityCommand`.
2. **Configuración de Límites (`SafetyParams`)** — Implementar un dataclass inmutable que almacene el `max_linear_speed`, `max_yaw_rate` y `failsafe_timeout_s`.
3. **Refactorización de Control (`GuidanceLaw`)** — Modificar `src/control/guidance_law.py` para eliminar la saturación física (clamping). El `GuidanceLaw` ahora escupirá el esfuerzo de control en crudo.
4. **Suite de Pruebas de Seguridad** — `tests/test_safety.py`. Pruebas unitarias que validen la saturación simétrica de velocidades positivas/negativas y la activación exacta del modo Hovering.

## Decisiones

- **Hovering sobre Return-to-Launch (RTL)** — Ante la pérdida del objetivo, ordenamos ceros (`VelocityCommand(0,0,0,0)`). Se descarta activar comandos nativos de MAVLink como RTL porque en un laboratorio techado, el dron intentaría subir a una altitud de seguridad predefinida y chocaría.
- **Desacoplamiento total** — El `SafetyFilter` no importará a MAVSDK ni a OpenCV. Es una función puramente lógica que recibe un comando y devuelve un comando mutado o intacto.

## Riesgos

- **Falsos positivos del Failsafe (Micro-cortes)** — Si el timeout es muy estricto (ej. 0.1s), latencias normales de red causarán que el dron frene a tirones. *Mitigación:* Establecer un `failsafe_timeout_s` predeterminado conservador de $1.0$ a $1.5$ segundos, dando tiempo a Deep SORT (Feature 001) para recuperar oclusiones rápidas.