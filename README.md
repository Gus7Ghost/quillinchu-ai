# Quillinchu AI

Plataforma modular de investigación para el seguimiento autónomo de personas mediante drones utilizando visión artificial e Inteligencia Artificial en tiempo real. Desarrollado para el **Laboratorio de Inteligencia Artificial y Robótica (LabIAR)** de la **Universidad Nacional de Ingeniería (UNI)**, Perú.

## 🚀 Arquitectura del Proyecto

El proyecto está diseñado bajo un enfoque modular y asíncrono, estructurado de la siguiente manera:

*   **`spec/`**: Especificaciones del sistema y flujo Spec-Driven Development (SDD).
*   **`src/vision/`**: Detección de objetivos mediante YOLOv8 (`HeadDetect.pt`) y tracking mediante Deep SORT.
*   **`src/control/`**: Controladores PID y algoritmos de estabilización.
*   **`src/navigation/`**: Navegación autónoma y comunicación con el dron vía MAVSDK (sistema de coordenadas BODY_NED).
*   **`src/metrics/`**: Registro y cálculo de métricas científicas (Hz, Latencia, RMSE).
*   **`src/safety/`**: Control de contingencias de seguridad, geofencing y Hovering autónomo.
*   **`tests/`**: Suite de pruebas unitarias que replican la estructura del código fuente.

## 🛠️ Stack Tecnológico

*   **Lenguaje**: Python 3.10+ (Tipado estricto con Type Hints)
*   **Visión e IA**: OpenCV, YOLOv8 (Ultralytics), Deep SORT
*   **Navegación**: MAVSDK-Python (Asyncio nativo)
*   **Procesamiento Numérico**: NumPy, SciPy
*   **Pruebas**: Pytest / Unittest

## 💻 Comandos Básicos

### Ejecución del Sistema
```bash
python src/main.py
```

### Ejecutar Pruebas Unitarias
```bash
pytest
# o bien:
python -m unittest discover tests
```

### Formateo y Estilo de Código (PEP 8)
```bash
black --check src/
flake8 src/
```

### Generación de Reportes
```bash
python src/metrics/report_generator.py
```

---
Desarrollado con fines de investigación científica en LabIAR - UNI.
