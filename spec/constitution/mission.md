# Misión Científica del LabIAR - Quillinchu AI

Este documento define la razón de ser del proyecto. Es la referencia que decide si una nueva característica (feature) o módulo "encaja" o no en el desarrollo del sistema de seguimiento autónomo.

## Qué construimos

Quillinchu AI es una plataforma de software modular y asíncrona para el seguimiento autónomo y en tiempo real de personas mediante drones comerciales de código cerrado. El sistema procesa de forma remota un stream de video de alta definición, detecta y rastrea el objetivo en tierra, calcula dinámicamente comandos de velocidad espacial y los envía de regreso para controlar la navegación de la aeronave de manera segura y robusta.

### Piezas principales del producto:

1. **Módulo de Percepción Asíncrona (`src/vision/`)** — Captura el flujo de video H.264 del dron por red, ejecuta inferencia de IA con YOLOv8 (`HeadDetect.pt`) y realiza el seguimiento continuo asignando identificadores únicos mediante Deep SORT.
2. **Lazo de Control de Vuelo (`src/control/` & `src/navigation/`)** — Calcula los errores espaciales en la imagen mediante controladores PID independientes y traduce las salidas en comandos de velocidad asíncronos (`BODY_NED`) enviados a la aeronave vía MAVSDK-Python.
3. **Capa de Seguridad y Contingencias (`src/safety/`)** — Filtra las señales de velocidad bajo límites físicos de saturación, restringe el vuelo mediante Geofencing y activa la detención automática en el aire (Hovering) ante la pérdida del objetivo.
4. **Sistema de Métricas Científicas (`src/metrics/`)** — Registra logs con marcas de tiempo de alta precisión y genera automáticamente reportes científicos de desempeño (Frequency Update en Hz, Latencia del pipeline en ms y RMSE de trayectoria).

## Para quién

- **Investigadores y tesistas del LabIAR - UNI** que buscan una arquitectura de software modular, limpia y reproducible para experimentar con algoritmos de visión y control en aeronaves no tripuladas.
- **Desarrolladores de robótica autónoma** que requieran integrar sistemas aéreos comerciales y cerrados (como el DJI Air 2S) con potentes pipelines externos de Inteligencia Artificial en estaciones terrestres.
- **El jurado académico evaluador**, que necesita validar cuantitativa y rigurosamente los resultados de estabilidad, retraso temporal y precisión en la sustentación de la tesis.

## Principios

- **Concurrencia y Asincronía Nativa** — El pesado pipeline de procesamiento de imagen (OpenCV, YOLO, Deep SORT) jamás debe bloquear ni ralentizar el lazo crítico de control de vuelo. La arquitectura debe descansar firmemente sobre programación no bloqueante (`asyncio`).
- **Seguridad Física Absoluta** — La integridad de la aeronave, los operadores y el entorno de prueba del laboratorio es prioritaria. Todo comando enviado debe ser validado por la capa de seguridad en milisegundos; el software jamás debe colapsar catastróficamente en pleno vuelo.
- **Rigor Matemático y Sustento Científico** — Cada algoritmo implementado (sintonización PID, estimación de distancia mediante diámetro cefálico promedio de 0.23 m, métricas estadísticas) debe contar con respaldo teórico sólido y formal. Queda prohibido el uso de aproximaciones empíricas sin justificación física.
- **Reproducibilidad y Código Limpio** — El repositorio debe ser completamente reproducible. Esto exige un estilo estructurado (PEP 8), uso obligatorio de tipado estricto (Type Hints) y pruebas unitarias automáticas en espejo (`tests/`) para garantizar que cualquier miembro del laboratorio pueda replicar el sistema.

## Qué NO es

- **No es una aplicación comercial de pilotaje o entretenimiento** — No está diseñada para vuelo recreativo, captura fotográfica o cinematografía; es un entorno estrictamente enfocado en la investigación científica de la robótica autónoma.
- **No es un sistema de control de motores a bajo nivel** — Quillinchu AI no implementa el firmware del piloto automático ni interactúa directamente con los ESCs (Electronic Speed Controllers); delega la estabilidad de actitud básica en el hardware del dron y se concentra en enviar consignas de velocidad de alto nivel.
- **No es una solución dependiente exclusivamente de pilotos automáticos de código abierto (PX4/ArduPilot)** — El sistema está diseñado específicamente para ser agnóstico y tolerar la integración con ecosistemas propietarios cerrados utilizando traductores de protocolo de red intermedios (como Rosetta Drone).