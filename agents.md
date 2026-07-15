# Quillinchu AI
Plataforma modular de investigación para el seguimiento autónomo de personas mediante drones utilizando visión artificial e Inteligencia Artificial en tiempo real. Desarrollado para el Laboratorio de Inteligencia Artificial y Robótica (LabIAR) de la Universidad Nacional de Ingeniería (UNI), Perú.

## Stack
- Lenguaje: Python 3.10+ estructurado, modular y con tipado estricto (Type Hints).
- Frameworks / Libs de IA: OpenCV, YOLOv8 (Ultralytics) y Deep SORT.
- Control y Navegación: MAVSDK-Python (programación asíncrona nativa con asyncio) y MAVLink.
- Procesamiento Numérico: NumPy y SciPy (para optimización matemática y cálculo de métricas).
- Tests: Pytest o Unittest.

## Comandos
- `python src/main.py` — Arranca el sistema completo en modo simulación (SITL) o ejecución real.
- `pytest` o `python -m unittest discover tests` — Ejecuta las pruebas unitarias (deben pasar antes de cada commit).
- `black --check src/` o `flake8 src/` — Revisa que el estilo de código cumpla estrictamente con PEP 8 antes de un Pull Request.
- `python src/metrics/report_generator.py` — Procesa los logs CSV/JSON y calcula automáticamente el reporte de métricas científicas (Hz, Latencia, RMSE).

## Estructura del proyecto
- `spec/` — Contiene la constitución y las carpetas de características para el flujo Spec-Driven Development (SDD).
- `src/vision/` — Gestión de cámara, inferencia de YOLOv8 (usando HeadDetect.pt) y tracking con IDs únicos de Deep SORT.
- `src/control/` — Implementación de controladores PID independientes y algoritmos de estabilización espacial.
- `src/navigation/` — Gestión del estado del dron, misiones y traducción de comandos de velocidad al sistema BODY_NED vía MAVSDK.
- `src/metrics/` — Módulo encargado de calcular automáticamente Frequency Update (Hz), Latencia y RMSE (Posición/Velocidad).
- `src/safety/` — Capa crítica de contingencias: Geofencing, límites de saturación física y hovering automático por pérdida de objetivo.
- `tests/` — Suites de pruebas unitarias organizadas de forma espejo con respecto a la carpeta `src/`.

## Convenciones
- Estilo de código: PEP 8 estricto. Variables y funciones en `snake_case`, clases en `PascalCase`. Es obligatorio el uso de Type Hints en todas las funciones (ej. `def calcular_error(pos: float) -> float:`).
- Ubicación de pruebas: Todos los tests deben vivir en la carpeta raíz `tests/` replicando la estructura del módulo que validan (ej. `tests/test_control.py`).
- Manejo de errores: Diseñar excepciones personalizadas controladas (ej. `TrackingLostError`) en lugar de bloques genéricos. El software jamás debe colapsar catastróficamente en pleno vuelo.
- Patrón de Concurrencia: Desacoplar el pipeline pesado de visión del lazo de control en tiempo real mediante un enfoque Productor-Consumidor usando `asyncio` o `multiprocessing.Queue`. El procesamiento de imagen no debe ralentizar los comandos de vuelo.

## No hagas
- Prohibido utilizar `DroneKit`. Toda la abstracción de vuelo de la tesis debe usar la arquitectura asíncrona moderna de `MAVSDK-Python`.
- No subas archivos de pesos binarios (`*.pt`, `*.onnx`) ni entornos virtuales (`.venv/`) al repositorio de GitHub. Valida siempre que estén activos en el `.gitignore`.
- No calcules la estimación de distancia asumiendo que el cuadro delimitador de la cabeza equivale a la altura total de la persona (1.68 m). Si usas `HeadDetect.pt`, calibra el modelo para el diámetro promedio de una cabeza humana (~0.23 m).
- No envíes comandos de velocidad directamente a MAVSDK sin pasar primero por los filtros de saturación y validación del módulo `src/safety/`.
- Prohibido asumir que la cámara es local (webcam / ID 0). El flujo de video proviene del DJI Air 2S mediante la retransmisión UDP de Rosetta Drone (puerto 5600) o RTSP. Todo código de captura de imagen debe configurarse para recibir este stream de red de manera asíncrona.

## Flujo de trabajo
- Antes de escribir una sola línea de código para un componente, lee y alíneate con su archivo de especificación en `spec/features/`. Si el archivo no existe, pide al usuario redactarlo.
- Diseña una tarea a la vez. Al finalizar un módulo, describe qué cambiaste a nivel de arquitectura y confirma que los tests unitarios pasen con éxito.
- Si no estás seguro al 80% sobre un problema de modelamiento matemático o de control (ej. sintonización de ganancias PID, corrección de distorsión geométrica de la cámara), propón un plan teórico y pregunta. No inventes aproximaciones empíricas sin sustento científico.

## Documentación
- `spec/constitution/mission.md` — Misión científica del LabIAR.
- `spec/constitution/tech-stack.md` — Stack tecnológico y límites fundamentales del software.
- `spec/features/001 - deteccion y tracking/spec.md` — Especificación de Visión y Tracking.