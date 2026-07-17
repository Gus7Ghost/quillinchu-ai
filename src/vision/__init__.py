"""
Módulo de Visión — Quillinchu AI.

Define las estructuras de datos compartidas del dominio de percepción
y exporta los componentes públicos del pipeline de visión.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import NamedTuple


class Detection(NamedTuple):
    """Detección cruda producida por el modelo YOLOv8.

    Attributes:
        bbox: Coordenadas (x_min, y_min, x_max, y_max) de la caja delimitadora.
        confidence: Nivel de confianza de la detección [0.0, 1.0].
    """

    bbox: tuple[float, float, float, float]
    confidence: float


@dataclass(frozen=True, slots=True)
class TargetState:
    """Estado instantáneo de un objetivo rastreado por Deep SORT.

    Estructura compartida publicada por el pipeline de visión (Productor)
    para su consumo no bloqueante por el lazo de control (Consumidor).

    Attributes:
        track_id: Identificador único persistente asignado por Deep SORT.
        bbox: Coordenadas (x_min, y_min, x_max, y_max) del bounding box.
        confidence: Confianza de la detección asociada al track.
        timestamp: Marca de tiempo epoch en segundos (alta precisión).
    """

    track_id: int
    bbox: tuple[float, float, float, float]
    confidence: float
    timestamp: float = field(default_factory=time.perf_counter)


__all__: list[str] = [
    "Detection",
    "TargetState",
]
