# 005 · Contingencias de Seguridad

**Estado:** en curso

## Qué hace

El sistema implementa una capa middleware (`SafetyFilter`) obligatoria e independiente que intercepta todos los comandos de velocidad generados por los controladores PID antes de enviarlos al dron. Su responsabilidad incluye tres mecanismos:
1. **Saturación Física (Hard Clamping):** Restringe las velocidades lineales y angulares a límites máximos seguros.
2. **Hovering Autónomo (Failsafe):** Si el pipeline de visión pierde a la persona por un tiempo superior a un umbral configurable (ej. 1.5 segundos), el filtro sobrescribe el comando del PID y obliga al dron a frenar y flotar en su lugar (`VelocityCommand(0,0,0,0)`).
3. **Geofencing Básico:** Límites lógicos para evitar que el dron exceda altitudes o distancias peligrosas en el entorno de pruebas.

## Por qué

Para garantizar la integridad física de la aeronave, los operadores y el entorno del LabIAR. Un controlador PID puro, ante una detección errónea o un frame corrupto, podría generar un pico de velocidad (esfuerzo de control) matemáticamente correcto pero físicamente destructivo. Extraer esta responsabilidad del módulo de control y aislarla en `src/safety/` respeta el principio de responsabilidad única de la arquitectura de software.

## Criterios de aceptación

### Comportamiento observable y comprobable
- [ ] ¿El `SafetyFilter` intercepta y recorta (clamp) de forma estricta cualquier velocidad que supere los umbrales máximos configurados?
- [ ] ¿El sistema implementa un temporizador que monitorea el último `timestamp` válido del objetivo?
- [ ] ¿Si el temporizador supera el `failsafe_timeout`, el filtro emite automáticamente un comando de velocidades nulas (Hovering) ignorando al PID?

### Caso límite o de error contemplado
- [ ] ¿El filtro de seguridad es capaz de recuperarse fluidamente y devolverle el control al PID una vez que el pipeline de visión recupera el tracking de la persona?

### Requisito de calidad
- [ ] ¿Se eliminó completamente la lógica temporal de saturación (clamping) que residía dentro de `src/control/guidance_law.py` en la Feature 002/003?
- [ ] ¿La suite de pruebas en `tests/test_safety.py` verifica de forma aislada las mutaciones de los comandos seguros, inseguros y de emergencia?

## Fuera de alcance

- Evasión de obstáculos automatizada (Collision Avoidance), ya que requeriría sensores de profundidad o LiDAR, no disponibles actualmente.
- Modos de retorno a casa (RTL) automáticos por pérdida visual (en entornos de laboratorio/interiores, un RTL automático suele causar colisiones con el techo; el hovering es más seguro).