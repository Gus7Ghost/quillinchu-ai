# 004 · Métricas Científicas

**Estado:** en curso

## Qué hace

El sistema recolecta, almacena y procesa los datos de rendimiento en tiempo real generados durante el vuelo. Registra silenciosamente la latencia del pipeline, la frecuencia (Hz), el error absoluto de posición en píxeles ($e_x, e_y$) y los comandos de velocidad generados. Al finalizar, exporta esta información a un archivo CSV **nombrado dinámicamente según la fecha y los parámetros de control utilizados**. Finalmente, provee un script independiente que genera los gráficos de evolución y una tabla de resultados académicos con el RMSE de posición y velocidad.

## Por qué

Es el pilar de la validación académica del proyecto frente al jurado de la UNI. El sistema de control requiere evidencia cuantitativa irrefutable. Adaptando las directrices del curso, registrar el RMSE, la latencia y la frecuencia en un formato estandarizado (y pre-formateado en tablas y gráficos) elimina el trabajo manual y garantiza la trazabilidad rigurosa de cada experimento.

## Criterios de aceptación

### Comportamiento observable y comprobable
- [ ] ¿El sistema exporta un archivo CSV utilizando nomenclatura consistente y trazable (ej. `exp_2026-07-23_Kp0.1_Kd0.01.csv`)?
- [ ] ¿El archivo CSV incluye columnas explícitas para el Timestamp, Latencia, Error de Posición (X, Y) y Velocidad (Forward, Yaw)?
- [ ] ¿Existe un script autónomo (`report_generator.py`) capaz de leer el CSV y generar gráficos de "Error vs Tiempo" (por época/iteración)?
- [ ] ¿El generador de reportes imprime en consola una tabla de resultados formateada que incluye Configuración, Métrica Principal (RMSE, Hz) y Valor, lista para anexar al informe de avance?

### Caso límite o de error contemplado
- [ ] ¿El mecanismo de registro (logging) almacena la telemetría en memoria RAM y solo la escribe en el disco (I/O) al cerrarse el programa, garantizando cero micro-bloqueos en el lazo de vuelo?
- [ ] ¿El script protege las métricas antiguas evitando sobrescribir experimentos pasados?

### Requisito de calidad
- [ ] ¿El diseño del recolector es puramente pasivo y no interfiere con el `VisionPipeline` ni el `MavlinkController`?
- [ ] ¿Las fórmulas estadísticas aplicadas (RMSE absoluto) están respaldadas por pruebas unitarias?

## Fuera de alcance

- Visualización de gráficas dinámicas en vivo durante el vuelo.
