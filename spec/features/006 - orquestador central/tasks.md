# 006 · Orquestador Central — Tareas

- [ ] Crear el archivo `src/main.py`.
- [ ] Implementar la configuración de logs básicos usando el módulo `logging` de Python.
- [ ] Instanciar todos los parámetros y clases principales (Vision, Mavlink, Guidance, Safety, Metrics).
- [ ] Programar la tarea principal `async def main()` que lance el pipeline de visión e inicie la conexión MAVLink.
- [ ] Desarrollar el bucle `while True:` del consumidor que integra Visión -> Control -> Seguridad -> Telemetría -> Métricas.
- [ ] Implementar el bloque de manejo de excepciones para atrapar `KeyboardInterrupt` (Ctrl+C).
- [ ] Asegurar que el bloque `finally` cierre conexiones, detenga el dron y ejecute `export_to_csv()`.
- [ ] Validar formato con `black` y Type Hints.
- [ ] Actualizar el estado de la feature en `../../constitution/roadmap.md`.