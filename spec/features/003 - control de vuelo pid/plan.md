# 003 · Control de Vuelo PID — Plan de Implementación

## 1. Módulo PID Abstracto (`src/control/pid.py`)
- Crear el dataclass inmutable `PIDParams` para configurar las ganancias ($K_p$, $K_i$, $K_d$), el límite integral (`integral_limit`) y la constante de tiempo del filtro (`tau`).
- Crear la clase `PIDController` con estado interno mutable (`_integral`, `_prev_error`, `_prev_derivative_filtered`).
- Implementar el método `compute(error, dt)`:
  - **Proporcional**: $P = K_p \cdot e$
  - **Integral**: Acumular $\Delta I = K_i \cdot e \cdot dt$ y saturar inmediatamente (Anti-Windup) en el rango `[-integral_limit, +integral_limit]`.
  - **Derivativo (Tustin)**: Calcular la derivada aplicando un filtro paso-bajo de primer orden discreto (transformada bilineal) para evitar que el ruido del bounding box genere comandos de control agresivos.
  - **Seguridad dt**: Si $dt \le 0$, suprimir los cálculos I y D devolviendo únicamente el término P.
- Implementar un método `reset()` para purgar el historial interno.

## 2. Refactorización de la Ley de Guiado (`src/control/guidance_law.py`)
- Ampliar el dataclass `GuidanceParams` para incluir las ganancias $K_i$ y $K_d$ separadas para `yaw` y `forward`, así como los parámetros `integral_limit` y `tau`.
- En `GuidanceLaw.__init__`, reemplazar los cálculos estáticos por dos instancias de `PIDController` (una para `yaw` y otra para `forward`).
- En `GuidanceLaw.compute()`, introducir el estado `_last_timestamp` para calcular el verdadero $dt$ entre fotogramas.
  - Si el timestamp retrocede (anomalía temporal no monótona), hacer un reset del controlador PID de forma segura e informar mediante un warning en el logger.
- Mantener los comportamientos críticos previos: selección del mejor target, aplicación de la zona muerta (deadband) sobre los errores de píxeles, y saturación general de salida (clamping).

## 3. Suite de Pruebas Unitarias
- **Matemáticas puras (`tests/test_pid.py`)**:
  - Verificar que el término proporcional actúe en aislamiento.
  - Validar la acumulación del término integral y el bloqueo en sus límites (Anti-Windup).
  - Comprobar la atenuación del filtro derivativo ajustando la constante de tiempo $\tau$.
  - Confirmar el comportamiento seguro cuando $dt = 0$.
- **Integración (`tests/test_control.py`)**:
  - Modificar los mocks/fixtures para añadir el campo `timestamp` al `TargetState`.
  - Asegurar la retrocompatibilidad: con $K_i = K_d = 0$, el controlador debe superar exactamente los mismos tests que el proporcional puro de la Feature 002.
  - Agregar tests para verificar el cálculo del dt y la propagación a lo largo del tiempo.
