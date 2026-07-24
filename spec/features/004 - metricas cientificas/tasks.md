# 004 · Métricas Científicas — Tareas

- [x] Crear la estructura base del módulo `src/metrics/` con su respectivo `__init__.py`.
- [x] Implementar la clase `MetricsLogger` en `src/metrics/logger.py` usando almacenamiento temporal en memoria (listas de diccionarios o tuplas).
- [x] Desarrollar el método `export_to_csv(params)` que genere nombres de archivo consistentes basados en fecha y configuración PID (ej. `exp_YYYY-MM-DD_Kp...csv`).
- [x] Crear el script `src/metrics/report_generator.py` para calcular el RMSE de posición y velocidad, y la frecuencia de actualización (Hz).
- [x] Implementar en `report_generator.py` la exportación de gráficas de evolución usando `matplotlib` (Error vs Frames, Latencia vs Frames).
- [x] Añadir a `report_generator.py` la impresión en consola de la "Tabla de Resultados" en formato Markdown.
- [x] Desarrollar la suite de pruebas matemáticas en `tests/test_metrics.py` para validar la exactitud de los cálculos RMSE y la correcta nomenclatura del logger.
- [x] Verificar el cumplimiento de tipado estricto (Type Hints) y ejecutar `black` y `flake8`.
- [x] Validar contra los criterios de aceptación de `spec.md`.
- [x] Actualizar el estado de la feature en `../../constitution/roadmap.md`.

## Mantenimiento (checklist recurrente)

- [ ] Respaldar los archivos generados en `logs/` tras sesiones de validación importantes y documentar hallazgos cualitativos en la tabla final del informe.