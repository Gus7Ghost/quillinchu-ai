# 002 · Módulo de Control MAVLink y Guiado

**Estado:** completado

## Qué hace

El sistema recibe de forma continua los datos espaciales (`TargetState`) generados por el pipeline de visión asíncrono. Utilizando esta información, calcula el error de píxeles respecto al centro de la imagen mediante leyes de control Proporcional y traduce estos errores en comandos de velocidad espacial que son enviados de regreso para controlar la navegación de la aeronave. Todo esto operando de forma paralela y no bloqueante.

## Por qué

Es el "músculo" del sistema Quillinchu AI. Sin este módulo, el procesamiento visual carece de utilidad física. Debe implementarse con un nivel de seguridad física absoluta, garantizando que el hilo de conexión con el dron jamás colapse catastróficamente en pleno vuelo.

## Criterios de aceptación

### Comportamiento observable y comprobable
- [x] ¿El controlador establece conexión MAVLink y emite un Heartbeat constante (1 Hz) hacia ArduPilot sin interrumpirse?
- [x] ¿La ley de guiado convierte correctamente el error de píxeles en coordenadas de velocidad lineal y angular?
- [x] ¿Los comandos de velocidad se envían utilizando exclusivamente el marco de referencia relativo a la aeronave (`BODY_NED`)?

### Caso límite o de error contemplado
- [x] ¿El sistema aplica saturación (clamping) física a las velocidades para evitar que el dron ejecute movimientos bruscos ante saltos súbitos de la caja delimitadora?
- [x] ¿El hilo de telemetría sobrevive e intenta reconectar gracefully si ArduPilot deja de responder temporalmente?

### Requisito de calidad
- [x] ¿El módulo respeta el desacoplamiento computacional estricto, asegurando que la latencia de la red no bloquee el pipeline de visión?
- [x] ¿Se asegura la ausencia total de dependencias prohibidas, como DroneKit?

## Fuera de alcance

- Lógicas de Geofencing 3D y detención automática (Hovering) en el aire. (Se implementarán en la capa de Seguridad y Contingencias en `src/safety/`[cite: 1, 3]).
- Reportes automáticos de la latencia del lazo de control. (Se abordará en el Sistema de Métricas Científicas `src/metrics/`[cite: 1]).