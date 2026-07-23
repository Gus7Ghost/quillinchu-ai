# 003 · Control de Vuelo PID — Especificación

## Objetivo
Refactorizar la ley de guiado inicial (puramente Proporcional) para utilizar un controlador PID (Proporcional-Integral-Derivativo) completo, mejorando la estabilidad del dron y eliminando el error en estado estacionario durante el seguimiento.

## Descripción
La Feature 002 implementó una ley de guiado proporcional. Aunque funcional, un control puramente proporcional es propenso a oscilaciones y errores en estado estacionario. Esta feature añade los términos Integral y Derivativo para lograr un control más suave, preciso y estable. Se requieren implementaciones independientes para los ejes de Yaw (guiñada) y Forward (avance longitudinal).

## Criterios de Aceptación (Acceptance Criteria)

- **Controlador PID Abstracto**: Debe existir una clase matemática pura `PIDController` independiente del dron, que reciba un error y un diferencial de tiempo (`dt`), y retorne una señal de control.
- **Anti-Windup**: El término integral del `PIDController` debe contar con un límite de saturación simétrico (`integral_limit`) para evitar el efecto de windup.
- **Filtro Paso-Bajo Derivativo**: El cálculo del término derivativo debe incorporar un filtro paso-bajo (aproximación de Tustin/bilineal) para mitigar la amplificación de ruido de alta frecuencia (píxeles ruidosos o vibración del bounding box).
- **Protección de Primer Frame**: El sistema no debe generar picos derivativos o integrales (spikes) en el primer frame procesado (cuando `dt=0` o no hay un timestamp previo válido).
- **Integración Dual**: La ley de guiado (`GuidanceLaw`) debe instanciar y utilizar dos controladores PID separados (uno para Yaw, otro para Forward).
- **Manejo del Tiempo (`dt`)**: El diferencial de tiempo (`dt`) suministrado al controlador PID debe calcularse rigurosamente comparando el `timestamp` exacto provisto por el `TargetState` del pipeline de visión, en lugar de asumir un tiempo de ciclo fijo.
- **Mantenimiento de Seguridad**: Se deben preservar las zonas muertas (deadband) y la saturación física final (clamping) de velocidades como medidas de seguridad base.
- **Cobertura de Pruebas**: Deben existir pruebas unitarias puramente matemáticas verificando cada aspecto del PID (Proporcional, acumulación Integral, Anti-Windup, filtro Derivativo de Tustin y comportamiento ante `dt=0`).

## Dependencias
- Feature 002: Ley de guiado proporcional base (completado).
- Integración con la estructura asíncrona de MAVSDK-Python (completado).