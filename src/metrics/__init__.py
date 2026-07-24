"""
Módulo de Métricas Científicas — Quillinchu AI.

Recolección pasiva de telemetría de rendimiento y generación
de reportes académicos para la validación cuantitativa del
sistema de seguimiento autónomo.

El módulo expone:
    - ``MetricsLogger``: Recolector en RAM de latencia, error
      de posición y velocidad comandada durante el vuelo.

El generador de reportes (``report_generator.py``) se ejecuta
como script CLI independiente y no se importa a nivel de módulo
para evitar dependencias pesadas (``matplotlib``) en el lazo
de vuelo.

References:
    - spec/features/004 - metricas cientificas/spec.md
    - spec/features/004 - metricas cientificas/plan.md
"""

from __future__ import annotations

from src.metrics.logger import MetricsLogger

__all__: list[str] = [
    "MetricsLogger",
]
