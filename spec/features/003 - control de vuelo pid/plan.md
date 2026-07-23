# 003 · Control de Vuelo PID — Plan

## Enfoque

Se adoptará un diseño modular. Se creará una entidad puramente matemática (`PIDController`) separada de la lógica de guiado visual. Esto permite instanciar múltiples controladores para distintos ejes sin duplicar código. El controlador utilizará la ecuación estándar del PID de tiempo discreto:
$$u(t) = K_p e(t) + K_i \int e(t) dt + K_d \frac{de}{dt}$$

El orquestador `GuidanceLaw` (Feature 002) será refactorizado internamente para sustituir la ganancia estática $K_p$ por instancias completas de este nuevo controlador PID, extrayendo el `dt` a partir de los `timestamp` que envía la cola de visión.

## Implementación

1. **Motor Matemático PID (`PIDController`)** — `src/control/pid.py`. Implementar una clase aislada que maneje el estado de un PID discreto, incluyendo historial de errores, acumulación integral con *anti-windup* y cálculo derivativo filtrado.
2. **Refactorización del Guiado (`GuidanceLaw`)** — `src/control/guidance_law.py`. Sustituir las multiplicaciones simples por llamadas al método `update()` de las instancias de `PIDController`. Actualizar los `GuidanceParams` para incluir $K_i$, $K_d$ y coeficientes de filtro.
3. **Suite de Pruebas Matemáticas** — `tests/test_pid.py`. Desarrollar pruebas unitarias inyectando valores de error artificiales con $dt$ fijos para comprobar que los sumatorios y divisiones matemáticas sean exactos a nivel de flotante. Actualizar `test_control.py` para reflejar la nueva firma del guiado.

## Decisiones

- **Filtro paso-bajo obligatorio en la Derivada** — Se decide aplicar un filtro exponencial al término derivativo. Dado que las redes neuronales como YOLOv8 tienen ruido inherente (la caja "vibra" píxel a píxel entre frames), una derivada pura amplificaría este ruido y destruiría los motores.
- **Uso estricto de `timestamp` real** — Se descarta asumir un $dt$ fijo (ej. $1/15 \text{ Hz}$). Como el pipeline de visión es asíncrono y sujeto a latencias de red impredecibles, el PID debe usar la marca de tiempo originada en el momento exacto de la captura del frame.

## Riesgos

- **Inestabilidad por *Windup* Integral** — Si el objetivo se mueve muy rápido y el dron no puede alcanzarlo debido a los límites de saturación, el término $I$ crecerá descontroladamente. *Mitigación:* Implementar clamping condicional en el acumulador integral (Anti-Windup) acoplado a la saturación general.