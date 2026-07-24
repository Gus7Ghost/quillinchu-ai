"""
Módulo de Seguridad — Quillinchu AI.

Provee la capa middleware obligatoria de contingencias que intercepta
y valida todos los comandos de velocidad generados por los
controladores PID antes de ser enviados al piloto automático.

Componentes públicos:
    - ``SafetyParams``: Configuración inmutable de límites de
      saturación y timeout de failsafe.
    - ``SafetyFilter``: Filtro de seguridad que aplica clamping
      simétrico y Hovering Autónomo por pérdida de tracking.

References:
    - spec.md §005: Contingencias de Seguridad.
    - tech-stack.md §Límites duros: «NINGÚN comando de velocidad
      puede enviarse directamente a MAVSDK sin ser previamente
      validado por src/safety/».
"""

from __future__ import annotations

from src.safety.filter import SafetyFilter, SafetyParams

__all__: list[str] = [
    "SafetyFilter",
    "SafetyParams",
]
