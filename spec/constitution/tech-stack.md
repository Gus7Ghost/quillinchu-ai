# Tech stack y convenciones

_Cómo está construido el proyecto y las reglas que todo el código debe respetar. Es la referencia técnica que ningún plan de feature debería contradecir._

---

## Tecnologías

- **Lenguaje:** Python 3.10+ con tipado estricto (`Type Hints`) y programación concurrente/asíncrona nativa (`asyncio`).
- **Framework / runtime:** Ninguno (Arquitectura basada en scripts puros con ejecución multiproceso y concurrencia).
- **Base de datos:** No aplica (Se utiliza persistencia local en archivos JSON y CSV administrada en `src/metrics/` para métricas científicas).
- **Tests:** `pytest` y `unittest` para verificar de forma robusta la suite de visión, control y seguridad.
- **Despliegue:** Ejecución en estación terrena física (laptop de desarrollo del laboratorio con Ubuntu 22.04 LTS o Ubuntu 24.04 LTS) conectada a la red de telemetría del dron DJI Air 2S.

---

## Archivos / módulos clave

_Mapa breve de dónde vive cada cosa. Solo lo que un recién llegado necesita para orientarse._

- `spec/` — Especificaciones del sistema y flujo Spec-Driven Development (SDD).
- `src/vision/` — Lector de GStreamer, detector YOLOv8 (`HeadDetect.pt`) y seguimiento con Deep SORT.
- `src/control/` — Implementación de algoritmos PID independientes para el control de errores espaciales.
- `src/navigation/` — Gestión de telemetría asíncrona y envío de comandos de velocidad `BODY_NED` vía MAVSDK.
- `src/safety/` — Controladores de saturación física, barreras lógicas (Geofencing) y maniobras de Hovering autónomo.
- `src/metrics/` — Registro automático en archivos CSV/JSON de la latencia, Hz y RMSE para la sustentación científica.
- `tests/` — Conjunto de pruebas unitarias que replica de forma simétrica la estructura de directorios del código fuente.

---

## Comandos

- `python src/main.py` — Arranca la ejecución de la estación terrena local, iniciando el lazo de visión y navegación.
- `pytest` — Ejecuta de manera integral la suite de pruebas unitarias del sistema (o bien: `python -m unittest discover tests`).
- `black --check src/ && flake8 src/` — Ejecuta las herramientas de formateo y validación de estilo bajo estándares PEP 8.
- `python src/metrics/report_generator.py` — Compila y genera los informes y gráficos científicos de desempeño del vuelo.

---

## Modelo de datos / dominio

_Las entidades o estructuras centrales y sus campos/reglas. Documenta solo lo no obvio: invariantes, mecánicas especiales, qué campo controla qué. Omite esta sección si no aplica._

- `TargetState` — Estructura compartida que representa el estado actual del objetivo de seguimiento:
  - `id` (int): Identificador único persistente asignado por Deep SORT.
  - `bbox` (tuple): Tupla de 4 flotantes $(x_{min}, y_{min}, x_{max}, y_{max})$ que delimita la cabeza en la imagen.
  - `timestamp` (float): Marca de tiempo epoch en microsegundos para cálculos asíncronos de latencia.
- `VelocityBody` — Objeto que emite consignas de velocidad directa a MAVSDK:
  - `forward_m_s` (float): Velocidad lineal longitudinal (+ adelante, - atrás) en el plano local.
  - `right_m_s` (float): Velocidad lineal lateral (+ derecha, - izquierda).
  - `down_m_s` (float): Velocidad lineal vertical (+ descender, - ascender).
  - `yaw_deg_s` (float): Velocidad angular de rotación sobre el eje yaw.

---

## Convenciones

_Reglas de estilo y patrones a seguir. Nombres, organización, manejo de errores, validación, idioma del contenido, etc._

- **Estilo de código:** Uso estricto de `snake_case` para variables, funciones, atributos y módulos, y `PascalCase` para definir clases (siguiendo los lineamientos de PEP 8).
- **Ubicación de pruebas:** La suite de pruebas se aloja de forma simétrica en la raíz del proyecto. Por ejemplo, el módulo `src/vision/detector.py` cuenta con su contraparte de pruebas en `tests/test_vision/test_detector.py`.
- **Manejo de errores asíncronos:** Toda llamada o suscripción MAVSDK debe realizarse dentro de bloques `try-except` asíncronos para evitar que la desconexión o pérdida de señal de telemetría congele el pipeline de visión.
- **Patrón de concurrencia:** Se implementa estrictamente el patrón Productor-Consumidor. El pipeline de visión publica resultados a través de colas multiproceso de forma no bloqueante hacia el planificador de control.

---

## Límites duros

_Lo que NUNCA se debe hacer. Reglas de seguridad, dependencias prohibidas, zonas congeladas._

- **Prohibido el uso de DroneKit:** Toda la API de comunicación con el piloto automático se gestiona mediante MAVSDK-Python y protocolos nativos asíncronos.
- **Prohibido subir binarios pesados al repositorio:** Queda estrictamente prohibido rastrear en Git archivos de pesos pesados (`*.pt`, `*.onnx`) o carpetas de entornos locales (`.venv`). Estos se configuran localmente en el laboratorio.
- **Desacoplamiento computacional estricto:** El procesamiento gráfico del pipeline de visión jamás debe ser síncrono o ejecutarse en el mismo hilo que el bucle de envío de telemetría principal para evitar bloqueos del dron en vuelo.
- **Filtro obligatorio de seguridad:** NINGÚN comando de velocidad generado por los controladores PID puede enviarse directamente a MAVSDK sin ser previamente validado y saturado por la capa de seguridad en `src/safety/`.