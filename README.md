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

## 📋 Requisitos del Sistema

### Hardware de Desarrollo (Target LabIAR)
- **Estación Terrena (Laptop)**: CPU Intel i7 (11ª Gen o superior), 16 GB de RAM, con sistema operativo **Ubuntu 22.04 LTS** o **Ubuntu 24.04 LTS**.
- **Aeronave**: Dron **DJI Air 2S** con control remoto conectado a tablet que ejecute **Rosetta Drone**.

### Dependencias del Sistema (Esenciales para GStreamer + OpenCV)
Para que OpenCV pueda capturar y decodificar el flujo de video RTP/H.264 que transmite Rosetta Drone por la red local, es obligatorio instalar las librerías de GStreamer en Ubuntu. Ejecuta en tu terminal:

```bash
sudo apt update && sudo apt install -y \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev

## 🔧 Instalación y Configuración del Entorno

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/Gus7Ghost/quillinchu-ai.git](https://github.com/Gus7Ghost/quillinchu-ai.git)
   cd quillinchu-ai
  
2. **Crear y activar el entorno virtual de Python:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate

3. **Instalar las dependencias de Python:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt


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
