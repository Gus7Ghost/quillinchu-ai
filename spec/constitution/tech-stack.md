# Stack Tecnológico y Límites Fundamentales

## Stack de Software
- **Lenguaje**: Python 3.10+ (Tipado estricto con Type Hints)
- **IA y Visión**: OpenCV, YOLOv8 (Ultralytics), Deep SORT
- **Control y Navegación**: MAVSDK-Python (Asíncrono), MAVLink
- **Cálculo Científico**: NumPy, SciPy
- **Pruebas**: Pytest / Unittest
- **Estilo**: PEP 8 (Black, Flake8)

## Restricciones y Límites
- Prohibido el uso de DroneKit.
- Prohibido subir archivos de pesos pesados (`*.pt`, `*.onnx`) o entornos virtuales (`.venv`).
- El pipeline de visión debe estar desacoplado del lazo de control principal (patrón Productor-Consumidor).
- Toda velocidad enviada al dron debe filtrarse mediante controles de saturación en `src/safety/`.
