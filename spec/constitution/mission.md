# Misión

_Define la razón de ser del proyecto. Es la referencia que decide si una feature "encaja" o no._

## Qué construimos

Construimos **Quillinchu AI**, una plataforma de software modular estructurada para la investigación científica, que dota a los drones (como el DJI Air 2S) de la capacidad de seguir autónomamente a una persona utilizando visión artificial en tiempo real. Resuelve el problema de la dependencia de hardware externo de telemetría, permitiendo autonomía de vuelo basada únicamente en el análisis visual a través de redes locales (Rosetta Drone).

_Si ayuda, enumera las piezas principales del producto:_

1. **Visión Desacoplada** — Captura streams de red (UDP/RTSP), detecta cabezas mediante inferencia rápida con YOLOv8 y ejecuta el tracking persistente (Deep SORT).
2. **Control Autónomo (PID)** — Estima distancias, estabiliza el dron y traduce la información visual en comandos de velocidad (`BODY_NED`) usando la API moderna de MAVSDK.
3. **Capa de Contingencia y Métricas** — Garantiza la seguridad física mediante geofencing y algoritmos de hovering seguro. Simultáneamente extrae data científica como Hz, latencia y error (RMSE).

## Para quién

- **Investigadores del LabIAR (UNI):** Su público principal. Proveerá la base empírica, robusta y con pruebas unitarias para investigar y desarrollar mejoras en robótica aérea y visión artificial.
- **Estudiantes y Contribuidores Técnicos:** Ingenieros que busquen entender cómo orquestar arquitecturas complejas asíncronas con Python, MAVSDK y modelos de Inteligencia Artificial en hardware real.
- **Comunidad Científica:** Interesados en la lectura directa de telemetría y métricas rigurosas generadas automáticamente para la formulación y validación de _papers_.

## Principios

_Las ideas rectoras que guían las decisiones de producto y técnicas. 3-5 puntos._

- **Sustento Científico antes que Empírico** — Ninguna función se implementará al azar. Los modelos matemáticos (como la calibración geométrica de la cámara o sintonización PID) requieren fundamento técnico demostrable.
- **Seguridad Inquebrantable (Safety-First)** — El dron opera en el mundo físico. Cualquier fallo en la cámara o excepción del código derivará siempre en una detención segura (hovering). El software jamás colapsará en vuelo.
- **Desacoplamiento Estricto (Concurrencia)** — El pesado análisis de visión y el delicado lazo de control deben vivir en procesos concurrentes aislados (Productor-Consumidor). Un retraso en la cámara no debe afectar la estabilización de vuelo.
- **Excelencia de Software** — El código será legible, modular, rigurosamente tipado (Type Hints) bajo estándar PEP 8, y validado sistemáticamente mediante pruebas automatizadas.

## Qué NO es

_Acota el alcance: lo que el proyecto deliberadamente no pretende ser. Evita malentendidos y feature creep._

- **NO es una app comercial plug-and-play.** Es una base de investigación de laboratorio, no un producto empaquetado para el consumidor final de drones de uso recreativo.
- **NO soporta ni usará frameworks obsoletos (ej. DroneKit).** La arquitectura se limitará estrictamente al ecosistema moderno de `MAVSDK-Python` con `asyncio`.
- **NO hace estimaciones ingenuas de posición.** La estimación de distancia nunca usará algoritmos que asuman proporciones de cuerpo completo (1.68 m) para evitar los conocidos errores de perspectiva por ángulo cenital; se basa estrictamente en la detección de la cabeza.
