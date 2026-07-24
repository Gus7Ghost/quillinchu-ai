# 006 · Orquestador Central — Tareas

- [x] Crear el archivo `src/main.py`.
- [x] Implementar la configuración de logs básicos usando el módulo `logging` de Python.
- [x] Instanciar todos los parámetros y clases principales (Vision, Mavlink, Guidance, Safety, Metrics).
- [x] Programar la tarea principal `async def main()` que lance el pipeline de visión e inicie la conexión MAVLink.
- [x] Desarrollar el bucle `while True:` del consumidor que integra Visión → Control → Seguridad → Telemetría → Métricas.
- [x] Implementar el bloque de manejo de excepciones para atrapar `KeyboardInterrupt` (Ctrl+C).
- [x] Asegurar que el bloque `finally` cierre conexiones, detenga el dron y ejecute `export_to_csv()`.
- [x] Validar formato con `black` y Type Hints (requiere entorno Ubuntu del laboratorio).
- [x] Ejecutar prueba de integración completa en SITL (Feature 007).
- [x] Actualizar el estado de la feature en `../../constitution/roadmap.md`.