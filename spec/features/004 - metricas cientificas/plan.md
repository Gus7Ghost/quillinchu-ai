# 004 · Métricas Científicas — Plan

## Enfoque

Se implementará un recolector pasivo (`MetricsLogger`) optimizado para no generar latencia de I/O. Los datos se acumularán en listas de memoria durante la ejecución y se volcarán asíncronamente a un CSV al cerrarse el programa. Para cumplir con las directrices académicas, el nombre del archivo CSV se generará dinámicamente inyectando la fecha actual y las ganancias del PID principal. 

El análisis *offline* (`report_generator.py`) calculará el $RMSE = \sqrt{\frac{1}{n}\sum_{i=1}^{n} e_i^2}$ tanto para los errores de posición como para las magnitudes de velocidad, y exportará los gráficos de evolución exigidos, imprimiendo además la tabla de reporte final.

## Implementación

1. **Recolector de Rendimiento (`MetricsLogger`)** — `src/metrics/logger.py`. Clase que reciba el `dt` (para Hz y latencia), el error de posición en píxeles ($e_x, e_y$) y la velocidad comandada, almacenándolos en memoria.
2. **Exportador Dinámico** — Implementar `export_to_csv(params: GuidanceParams)` dentro del logger. Este método construirá el nombre del archivo (ej. `logs/exp_YYYY-MM-DD_KpX_KdY.csv`) para asegurar la trazabilidad experimental.
3. **Generador de Reportes Offline (`report_generator.py`)** — `src/metrics/report_generator.py`. Script CLI que:
    * Lea un CSV específico.
    * Calcule el RMSE de Posición y RMSE de Velocidad.
    * Calcule los Hz promedio.
    * Genere y guarde gráficos PNG (Latencia vs Tiempo, Error vs Tiempo).
    * Imprima una tabla Markdown emulando la plantilla del curso (Configuración | Dataset | Métrica | Valor).
4. **Pruebas y Acoplamiento** — `tests/test_metrics.py`. Pruebas que validen el cálculo exacto del RMSE. Acoplar el `MetricsLogger` en la futura ejecución del consumidor principal.

## Decisiones

- **RMSE dual (Posición y Velocidad)** — Siguiendo las notas de la pizarra del curso, se calcularán métricas de error y varianza tanto para el desfase espacial (píxeles) como para el esfuerzo de control (velocidad), demostrando la suavidad del PID.
- **Diferimiento absoluto de I/O** — Se prohíbe el uso de librerías como `pandas` dentro del lazo de vuelo en tiempo real. La recolección será con tipos de datos nativos rápidos (tuplas/diccionarios).

## Riesgos

- **Pérdida de datos en RAM por apagado abrupto** — *Mitigación:* Capturar de manera robusta las señales de interrupción (`KeyboardInterrupt`) en el script principal para forzar la ejecución del método `export_to_csv()` antes de que el proceso muera.